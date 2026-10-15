#!/usr/bin/env python3
"""Queue run: short DB claims, up to PARALLEL GPT streams at once, guarded publication.

Each slot repeats one-item ticks until it reaches a FINAL outcome. Claims share one
scan cursor under a thread lock; the DB admission lock and claim UPDATE remain the
authority on which work runs. A plan usage limit waits LIMIT_WAIT_SECONDS and
resumes; LIMIT_STOP_AFTER consecutive limit events stop the worker.
Heartbeats (FEAT-automation-admin 2e, `automation_heartbeats`): a run writes at its end, and
also every HEARTBEAT_SECONDS while its slots make progress; a start that runs nothing
(stopped, paused, limit wait) writes at most every IDLE_HEARTBEAT_SECONDS.
Site pause (FEAT-automation-admin 3b, `automation_controls`): the owner's page can pause this
agent. It is checked with the local switches before every claim and every inference; a claim
it interrupts is released with its attempt refunded, never cancelled. A site-paused start still
runs to its end and writes the 'finished' heartbeat, so it is not throttled like an idle start.
The local switches are checked first: a stopped or limit-waiting worker never reads (or confirms)
the site flag, and the page reads that together with the heartbeat's `enabled`.
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / 'myblog_backend', ROOT / 'myblog_shared_db' / 'src'):
    sys.path.insert(0, str(path))

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from myblog_shared_db.lyrics_demand import LyricsDemandStore, StaleDiscovery
from scripts import automation_heartbeat
from scripts.gpt_plan_auth import DEFAULT_DIR, PlanAccount, PlanUnavailable, PrivateState
from scripts.gpt_translation_store import GPTTranslationStore, VERSIONS, _source

log = logging.getLogger(__name__)
PARALLEL = 3
LIMIT_WAIT_SECONDS = 3600
LIMIT_STOP_AFTER = 3
# A slot stops claiming in this run after any of these.
FINAL = frozenset({'idle', 'scan_wrap', 'daily_budget', 'owner_paused', 'site_paused', 'usage_limit_wait', 'disabled'})
USAGE_FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens')
AGENT_KEY = 'gpt-translate-poller'
# The page calls this agent stale after 15 min (2 × 60 s, minimum 15 min). A run beats on
# slot progress, so a run whose slots all hang stops beating and shows stale.
HEARTBEAT_SECONDS = 120
IDLE_HEARTBEAT_SECONDS = 300
# One statement checks the owner's site pause and stamps that this agent honoured it, so the
# page can tell "paused and seen" from "paused, not yet seen". READ WRITE first: a pooler
# session can carry a leaked read-only default.
# Slots share one answer for this long: a pause reaches a run within SITE_PAUSE_TTL, and
# three slots do not each add a DB round trip under the scan lock to every claim.
SITE_PAUSE_TTL = 5.0
# clock_timestamp(): a stamp taken after a wait on the row lock must not predate the
# owner's changed_at, or a real skip would read as "not yet confirmed".
SITE_PAUSE = text("UPDATE automation_controls SET honored_at=clock_timestamp() WHERE job_key=:key AND paused RETURNING job_key")
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
    def __init__(self, engine, state, client, daily_cap=10, clock=time.time, heartbeat=None):
        self.engine, self.state, self.client, self.clock = engine, state, client, clock
        self.heartbeat = heartbeat
        self.store = GPTTranslationStore(daily_cap)
        self._scan = threading.Lock()
        self._site_lock = threading.Lock()
        self._site = (None, False)  # (monotonic time of the last read, paused)
        self.site_pause_ttl = SITE_PAUSE_TTL

    def held(self, settings=None):
        """Why no new claim may start now, or None."""
        settings = settings if settings is not None else self.state.settings()
        if settings.get('pause_reason'):
            return 'owner_paused'
        if settings.get('resume_at', 0) > self.clock():
            return 'usage_limit_wait'
        if self.site_paused():
            return 'site_paused'
        return None

    def site_paused(self):
        """The owner's pause from the automation page. A read failure means continue (fail-open):
        it is an operational switch, not an auth boundary, and a pause that did not apply stays
        visible on the page because `honored_at` does not advance."""
        with self._site_lock:
            read_at, paused = self._site
            if read_at is not None and time.monotonic() - read_at < self.site_pause_ttl:
                return paused
            try:
                with self.engine.begin() as connection:
                    connection.execute(text('SET TRANSACTION READ WRITE'))
                    connection.execute(text("SET LOCAL statement_timeout = '5s'"))
                    paused = connection.execute(SITE_PAUSE, {'key': AGENT_KEY}).first() is not None
            except Exception as error:
                # Only the type: driver messages can carry connection details.
                log.error('GPT site pause check failed (%s); continuing', type(error).__name__)
                paused = False
            self._site = (time.monotonic(), paused)
            return paused

    def run(self, model, parallel=PARALLEL):
        outcomes, guard, done = Counter(), threading.Lock(), threading.Event()

        def slot():
            try:
                while not done.is_set():
                    # A run can last an hour: re-read the switch, not only pause_reason.
                    outcome = self.tick(model) if self.state.settings().get('enabled') else 'disabled'
                    with guard:
                        outcomes[outcome] += 1
                        progress = dict(outcomes)
                    if self.heartbeat:
                        self.heartbeat.maybe(lambda: heartbeat_fields(self.state, 'running', progress, clock=self.clock))
                    if outcome in FINAL:
                        # One wrap/budget/stop ends every slot: no slot rescans the queue
                        # from the start after a sibling finished the pass.
                        done.set()
            except BaseException:
                done.set()
                raise

        with ThreadPoolExecutor(max_workers=parallel) as pool:
            futures = [pool.submit(slot) for _ in range(parallel)]
        for future in futures:
            future.result()
        return dict(outcomes)

    def tick(self, model):
        claimed = self._claim()
        if isinstance(claimed, str):
            return claimed
        return self._infer(model, *claimed)

    def _claim(self):
        """Next ready claim, or an outcome. Serialized so slots never share a cursor read."""
        with self._scan:
            held = self.held()
            if held:
                return held
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
                return row, claim
            return 'idle' if not rows else 'scanned'

    def _infer(self, model, row, claim):
        from scripts.gpt_plan_client import PlanInferenceError
        # A stop from the setup screen takes effect before a new inference starts.
        # Tests call tick directly; installed ticks additionally verify account/model.
        controls = self.state.settings()
        held = self.held(controls)
        if held or (controls.get('model') and controls['model'] != model):
            # Only the owner's own stop or model change cancels the source. A sibling's plan
            # stop or limit wait releases the claim and returns its attempt: no inference ran.
            owner = controls.get('pause_reason') == 'owner_paused' or not held
            with Session(self.engine) as db:
                if owner:
                    self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), 'user_cancelled')
                else:
                    self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), 'claim_released', refund=True)
                db.commit()
            return held or 'owner_paused'
        # No DB connection/transaction remains open at this point.
        try:
            segments, actual_model, usage = self.client.translate(claim, model)
        except (PlanInferenceError, PlanUnavailable) as error:
            reason = error.reason if isinstance(error, PlanInferenceError) else 'authentication_required'
            if getattr(error, 'limit', False):
                self.limit_hit(reason)
            elif isinstance(error, PlanUnavailable) or error.pause:
                # A plan rejection MUST stop consumption even when DB cleanup fails.
                with self.state.lock('control.lock'):
                    settings = self.state.settings()
                    settings.update(enabled=False, pause_reason=reason)
                    self.state.write('settings.json', settings)
            try:
                with Session(self.engine) as db:
                    # A rejected limit request produced no output: its attempt is returned,
                    # so automatic resumes cannot exhaust a source's two attempts.
                    self.store.fail(db, UUID(claim['work_id']), UUID(claim['claim_token']), reason,
                                    refund=getattr(error, 'limit', False))
                    db.commit()
            except Exception:
                log.warning('GPT claim cleanup unavailable; lease will expire')
            return reason
        self.record_usage(actual_model, usage)
        try:
            self.limit_cleared()
        except Exception as error:
            log.warning('GPT limit streak reset unavailable (%s)', type(error).__name__)
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

    def limit_hit(self, reason):
        """One limit event waits, then resumes; the LIMIT_STOP_AFTER-th consecutive one stops."""
        with self.state.lock('control.lock'):
            settings = self.state.settings()
            now = self.clock()
            if settings.get('resume_at', 0) > now:
                return  # A sibling stream rejected by the same event; already counted.
            hits = settings.get('limit_hits', 0) + 1
            if hits >= LIMIT_STOP_AFTER:
                settings.pop('resume_at', None)
                settings.pop('limit_hits', None)  # A re-enable starts a fresh streak.
                settings.update(enabled=False, pause_reason=reason)
                log.error('GPT plan usage limit %d times in a row; stopped (%s)', hits, reason)
            else:
                settings.update(limit_hits=hits, resume_at=now + LIMIT_WAIT_SECONDS)
                log.warning('GPT plan usage limit (%s); waiting %ds, %d/%d',
                            reason, LIMIT_WAIT_SECONDS, hits, LIMIT_STOP_AFTER)
            self.state.write('settings.json', settings)

    def limit_cleared(self):
        """A completed inference after the wait ends the consecutive-limit streak."""
        if not self.state.settings().get('limit_hits'):
            return
        with self.state.lock('control.lock'):
            settings = self.state.settings()
            if settings.get('resume_at', 0) > self.clock():
                return  # Started before the limit event; the wait still stands.
            settings.pop('limit_hits', None)
            settings.pop('resume_at', None)
            self.state.write('settings.json', settings)

    def record_usage(self, model, usage):
        """Per-request log line plus a UTC-daily total in usage.json; never fails the item."""
        try:
            log.info('GPT usage model=%s input=%d cached=%d output=%d reasoning=%d',
                     model, *(usage[k] for k in USAGE_FIELDS))
            day = datetime.fromtimestamp(self.clock(), timezone.utc).date().isoformat()
            with self.state.lock('usage.lock'):
                daily = self.state.read('usage.json', {})
                totals = daily.setdefault(day, dict.fromkeys(('requests',) + USAGE_FIELDS, 0))
                totals['requests'] += 1
                for key in USAGE_FIELDS:
                    totals[key] += usage[key]
                self.state.write('usage.json', daily)
        except Exception as error:
            log.warning('GPT usage record unavailable (%s)', type(error).__name__)


def heartbeat_fields(state, phase, outcomes=None, error=None, clock=time.time):
    """Row fields from the worker's own files: codes, counts and model only — no credentials."""
    settings = state.settings()
    day = datetime.fromtimestamp(clock(), timezone.utc).date().isoformat()
    try:
        usage = state.read('usage.json', {}).get(day, {})
    except Exception:
        usage = {}
    counts = {automation_heartbeat.code(k): int(v) for k, v in (outcomes or {}).items()}
    pause = settings.get('pause_reason')
    if error is not None:
        last = f'error {type(error).__name__}'
    elif phase == 'finished':
        last = automation_heartbeat.counts_summary(counts)
    elif phase == 'running':
        last = 'running: ' + automation_heartbeat.counts_summary(counts)
    elif pause:
        last = 'paused: ' + automation_heartbeat.code(pause)
    else:
        last = phase
    resume_at = settings.get('resume_at')
    details = {
        'phase': phase,
        'model': str(settings.get('model') or '')[:64] or None,
        'daily_cap': settings.get('daily_cap'),
        'parallel': PARALLEL,
        'outcomes': counts,
        'pause_reason': automation_heartbeat.code(pause) if pause else None,
        'resume_at': int(resume_at) if isinstance(resume_at, (int, float)) and resume_at > clock() else None,
        'usage_day_utc': day,
        'usage_today': {k: int(usage.get(k, 0)) for k in ('requests',) + USAGE_FIELDS},
    }
    return dict(enabled=bool(settings.get('enabled')), last_outcome=last, details=details)


def idle_heartbeat(state, phase, clock=time.time):
    """A start that runs nothing still proves the agent is loaded; throttled across starts."""
    try:
        last = state.read('heartbeat.json', {}).get('at', 0)
        if clock() - last < IDLE_HEARTBEAT_SECONDS:
            return False
        if automation_heartbeat.write(automation_heartbeat.database_url(), AGENT_KEY,
                                      **heartbeat_fields(state, phase, clock=clock)):
            state.write('heartbeat.json', {'at': clock()})
            return True
    except Exception as error:
        log.warning('GPT idle heartbeat unavailable (%s)', type(error).__name__)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--smoke', action='store_true', help='One owner-authorized queue tick while scheduler stays disabled')
    args = parser.parse_args(argv)
    state = PrivateState(args.state_dir)
    beat = None
    try:
        with state.lock('worker.lock', blocking=False):
            settings = state.settings()
            if not settings.get('model') or (not args.smoke and not settings.get('enabled')):
                idle_heartbeat(state, 'stopped' if settings.get('model') else 'not_configured')
                return 0
            if settings.get('resume_at', 0) > time.time():
                # Plan usage limit wait: no claims; only the throttled heartbeat touches the DB.
                idle_heartbeat(state, 'usage_limit_wait')
                return 0
            from scripts.gpt_plan_client import GPTPlanClient
            from scripts.lyrics_translate_poller import database_url
            url = database_url()
            beat = automation_heartbeat.Heartbeat(url, AGENT_KEY, HEARTBEAT_SECONDS)
            engine = create_engine(url.replace('postgresql://', 'postgresql+psycopg://', 1),
                                   pool_pre_ping=True, connect_args={'connect_timeout': 30})
            try:
                worker = QueueWorker(engine, state, GPTPlanClient(PlanAccount(state)), settings['daily_cap'],
                                     heartbeat=beat)
                # A smoke stays one owner-authorized item; the schedule runs PARALLEL slots.
                outcomes = {worker.tick(settings['model']): 1} if args.smoke else worker.run(settings['model'])
                state.write('status.json', {'outcomes': outcomes})
                log.info('GPT queue run: %s', outcomes)
                beat.force(lambda: heartbeat_fields(state, 'finished', outcomes))
            finally:
                engine.dispose()
    except BlockingIOError:
        return 0  # Another start holds worker.lock; that run writes the heartbeat.
    except Exception as error:
        # Credential/DB library exception text can include secrets; log only the type.
        log.error('GPT queue tick stopped (%s)', type(error).__name__)
        if beat is not None:
            beat.force(lambda: heartbeat_fields(state, 'error', error=error))
        return 1
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
