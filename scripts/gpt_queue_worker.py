#!/usr/bin/env python3
"""One queue tick: short DB claims, one foreground GPT stream, guarded publication."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / 'myblog_backend', ROOT / 'myblog_shared_db' / 'src'):
    sys.path.insert(0, str(path))

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from myblog_shared_db.lyrics_demand import LyricsDemandStore, StaleDiscovery
from scripts.gpt_plan_auth import DEFAULT_DIR, PlanAccount, PlanUnavailable, PrivateState
from scripts.gpt_translation_store import GPTTranslationStore, VERSIONS, _source

log = logging.getLogger(__name__)
LIVE = """NOT j.cancelled AND EXISTS (SELECT 1 FROM lyrics_album_demands d
JOIN lyrics_discovery_scopes s ON s.id=d.scope_id AND s.active WHERE d.job_id=j.id)"""
# Stable composite keys + persistent cursor keep a poison row from monopolizing scans.
CANDIDATES = f"""
WITH candidates AS (
 SELECT 'lyrics:' || t.id::text AS key, t.spotify_id, 'lyrics' AS kind,
 NULL::bigint AS annotation_id, true AS manual_requested, NULL::uuid AS job_id,
 t.id AS track_id FROM tracks t JOIN track_lyrics_translations x ON x.track_id=t.id
 WHERE x.status='requested'
 UNION ALL
 SELECT 'album:' || lat.job_id::text || ':' || lat.track_id::text,
 t.spotify_id, 'lyrics', NULL::bigint, false, lat.job_id, lat.track_id
 FROM lyrics_album_tracks lat JOIN lyrics_album_jobs j ON j.id=lat.job_id
 JOIN tracks t ON t.id=lat.track_id JOIN track_lyrics l ON l.track_id=t.id
 WHERE {LIVE} AND lat.source_state IN ('source_pending','linked')
 AND (lat.next_attempt_at IS NULL OR lat.next_attempt_at<=now())
 AND l.match_status='matched' AND (length(coalesce(l.lyric_plain,''))>0 OR length(coalesce(l.lyric_synced,''))>0)
 UNION ALL
 SELECT 'genius:' || a.genius_annotation_id::text, t.spotify_id, 'genius',
 a.genius_annotation_id, true, NULL::uuid, t.id
 FROM track_genius_annotations a JOIN tracks t ON t.id=a.track_id
 JOIN track_genius_songs g ON g.track_id=a.track_id
 WHERE a.translation_status='pending' AND g.match_status='matched'
 AND btrim(coalesce(a.body_source,''))<>''
) SELECT * FROM candidates WHERE key>:cursor AND spotify_id IS NOT NULL ORDER BY key LIMIT 30
"""


def bind_album(db, row):
    """Job -> work lock order, committed separately BEFORE inference admission."""
    store = LyricsDemandStore(db.connection())
    snapshot = store.track_snapshot(row['job_id'], row['track_id'])
    active = db.execute(text(f'SELECT ({LIVE}) FROM lyrics_album_jobs j WHERE j.id=:id'),
                        {'id': row['job_id']}).scalar_one()
    if not active:
        raise StaleDiscovery('Album demand was withdrawn')
    source, fingerprint, _ = _source(db, row['track_id'], 'lyrics', lock=True)
    existing = db.execute(text('SELECT * FROM track_lyrics_translations WHERE track_id=:id'),
                          {'id': row['track_id']}).mappings().one_or_none()
    chars = [c for s in source for c in s['text'] if c.isalpha()]
    reason = None
    if existing and existing['status'] == 'done':
        if existing['origin'] == 'manual':
            reason = 'manual_translation'
        elif existing['source_fingerprint'] == fingerprint and existing['segments']:
            reason = 'already_translated'
    if chars and sum('\uac00' <= c <= '\ud7a3' for c in chars) / len(chars) >= .5:
        reason = 'already_korean'
    expected = dict(expected_work_id=snapshot['work_id'], expected_source_revision=snapshot['source_revision'])
    if reason:
        store.set_source_state(row['job_id'], row['track_id'], 'not_required', reason, **expected)
        return False
    store.ensure_work(row['job_id'], row['track_id'], fingerprint, 'ko', VERSIONS['lyrics'], **expected)
    return True


class QueueWorker:
    def __init__(self, engine, state, client, daily_cap=10):
        self.engine, self.state, self.client = engine, state, client
        self.store = GPTTranslationStore(daily_cap)

    def tick(self, model):
        from scripts.gpt_plan_client import PlanInferenceError
        scan = self.state.read('scan.json', {'cursor': ''})
        with Session(self.engine) as db:
            rows = list(db.execute(text(CANDIDATES), {'cursor': scan['cursor']}).mappings())
        if not rows and scan['cursor']:
            scan['cursor'] = ''
            self.state.write('scan.json', scan)
            return 'scan_wrap'
        for row in rows:
            scan['cursor'] = row['key']
            self.state.write('scan.json', scan)
            try:
                if row['job_id']:
                    with Session(self.engine) as db:
                        needed = bind_album(db, row)
                        db.commit()
                    if not needed:
                        continue
                with Session(self.engine) as db:
                    claim = self.store.prepare(db, row['spotify_id'], row['kind'], row['annotation_id'],
                                               manual_requested=row['manual_requested'])
                    db.commit()
            except StaleDiscovery:
                continue
            except HTTPException as error:
                if error.status_code == 429:
                    return 'daily_budget'
                if error.status_code not in (404, 409, 422):
                    raise
                continue
            if claim['status'] != 'ready':
                # Korean explicit requests need a visible terminal status; never inference.
                if row['manual_requested'] and row['kind'] == 'lyrics' and claim.get('reason') == 'already_korean':
                    with self.engine.begin() as connection:
                        connection.execute(text("""UPDATE track_lyrics_translations SET status='failed',
                            error='korean_source',updated_at=now() WHERE track_id=:id AND status='requested'"""), {'id': row['track_id']})
                continue
            # A stop from the setup screen takes effect before a new inference starts.
            # Tests call tick directly; installed ticks additionally verify account/model.
            controls = self.state.settings()
            if controls.get('pause_reason') or (controls.get('model') and controls['model'] != model):
                with Session(self.engine) as db:
                    self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), 'user_cancelled')
                    db.commit()
                return 'owner_paused'
            # No DB connection/transaction remains open at this point.
            try:
                segments, actual_model = self.client.translate(claim, model)
            except (PlanInferenceError, PlanUnavailable) as error:
                reason = error.reason if isinstance(error, PlanInferenceError) else 'authentication_required'
                if isinstance(error, PlanUnavailable) or error.pause:
                    # A plan rejection MUST stop consumption even when DB cleanup fails.
                    with self.state.lock('control.lock'):
                        settings = self.state.settings()
                        settings.update(enabled=False, pause_reason=reason)
                        self.state.write('settings.json', settings)
                try:
                    with Session(self.engine) as db:
                        self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), reason)
                        db.commit()
                except Exception:
                    log.warning('GPT claim cleanup unavailable; lease will expire')
                return reason
            try:
                with Session(self.engine) as db:
                    result = self.store.submit(db, UUID(claim['work_id']), UUID(claim['claim_token']),
                                               segments, row['annotation_id'], model=actual_model)
                    db.commit()
                return result['status']
            except HTTPException:
                # Source/claim/edit races never publish. Stop this version, not the whole queue.
                with Session(self.engine) as db:
                    try:
                        self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), 'superseded_result')
                        db.commit()
                    except HTTPException:
                        db.rollback()
                return 'superseded_result'
        return 'idle' if not rows else 'scanned'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--smoke', action='store_true', help='One owner-authorized queue tick while scheduler stays disabled')
    args = parser.parse_args(argv)
    state = PrivateState(args.state_dir)
    try:
        with state.lock('worker.lock', blocking=False):
            settings = state.settings()
            if not settings.get('model') or (not args.smoke and not settings.get('enabled')):
                return 0
            from scripts.gpt_plan_client import GPTPlanClient
            from scripts.lyrics_translate_poller import database_url
            url = database_url().replace('postgresql://', 'postgresql+psycopg://', 1)
            engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 30})
            try:
                outcome = QueueWorker(engine, state, GPTPlanClient(PlanAccount(state)), settings['daily_cap']).tick(settings['model'])
                state.write('status.json', {'outcome': outcome})
                log.info('GPT queue tick: %s', outcome)
            finally:
                engine.dispose()
    except BlockingIOError:
        return 0
    except Exception as error:
        # Credential/DB library exception text can include secrets; log only the type.
        log.error('GPT queue tick stopped (%s)', type(error).__name__)
        return 1
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
