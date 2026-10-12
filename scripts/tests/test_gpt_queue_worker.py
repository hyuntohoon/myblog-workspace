"""Automatic queue regression tests; synthetic sources, no remote inference."""
import json
import os
import sys
import threading
import time
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / 'myblog_backend', ROOT / 'myblog_shared_db' / 'src'):
    sys.path.insert(0, str(path))

import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.services.lyrics_service import LyricsService
from myblog_shared_db.lyrics_demand import LyricsDemandStore, StaleDiscovery
from scripts.gpt_plan_auth import PrivateState
from scripts.gpt_plan_client import PlanInferenceError
from scripts.gpt_queue_worker import FINAL, QueueWorker, bind_album
from scripts.gpt_translation_store import VERSIONS, _source

TEST_DB_URL = os.environ.get('TEST_DB_URL')
pytestmark = [pytest.mark.skipif(not TEST_DB_URL, reason='TEST_DB_URL not set')]
MODEL = 'eligible-selected-model'
ACTUAL = 'eligible-actual-model-version'
USAGE = {'input_tokens': 100, 'cached_input_tokens': 10, 'output_tokens': 200, 'reasoning_tokens': 30}
LIMIT = 'subscription_sharing_usage_limit_exceeded'


class FakeClient:
    def __init__(self, hook=None, error=None):
        self.calls = []
        self.hook, self.error = hook, error

    def translate(self, claim, model):
        self.calls.append((claim, model))
        if self.hook:
            self.hook(claim)
        if self.error:
            raise self.error
        return [{'i': s['i'], 'text_ko': '한국어 자리표시' if s['text'] else ''}
                for s in claim['segments']], ACTUAL, USAGE


class Clock:
    def __init__(self):
        self.now = time.time()

    def __call__(self):
        return self.now


@pytest.fixture
def queue(tmp_path):
    engine = create_engine(TEST_DB_URL)
    album, user = uuid4(), uuid4()
    tracks = [uuid4() for _ in range(4)]
    spotify = [uuid4().hex[:22] for _ in tracks]
    album_sid = 'gpt-queue-' + uuid4().hex
    with engine.begin() as c:
        c.execute(text("INSERT INTO users(id,handle,display_name) VALUES (:id,:handle,'Queue test')"),
                  {'id': user, 'handle': 'gpt-queue-' + uuid4().hex[:12]})
        c.execute(text("INSERT INTO albums(id,title,spotify_id,total_tracks) VALUES (:id,'Queue test',:sid,3)"),
                  {'id': album, 'sid': album_sid})
        for track, sid in zip(tracks, spotify):
            c.execute(text("INSERT INTO tracks(id,album_id,title,spotify_id) VALUES (:id,:album,'Queue test',:sid)"),
                      {'id': track, 'album': album, 'sid': sid})
            c.execute(text("INSERT INTO track_lyrics(track_id,match_status,lyric_plain) VALUES (:id,'matched',:body)"),
                      {'id': track, 'body': 'placeholder first\n\nplaceholder second'})
    state = PrivateState(tmp_path / 'private')
    state.write('settings.json', {'enabled': True, 'model': MODEL, 'daily_cap': 1000, 'active': 'fixture'})
    data = dict(engine=engine, album=album, user=user, tracks=tracks, spotify=spotify,
                album_sid=album_sid, state=state, jobs=[])
    yield data
    with engine.begin() as c:
        for job in data['jobs']:
            c.execute(text('DELETE FROM lyrics_album_jobs WHERE id=:id'), {'id': job})
        c.execute(text('DELETE FROM users WHERE id=:id'), {'id': user})
        c.execute(text('DELETE FROM albums WHERE id=:id'), {'id': album})
    engine.dispose()


def execute(q, sql, **params):
    with q['engine'].begin() as c:
        return c.execute(text(sql), params)


def row(q, sql, **params):
    with q['engine'].connect() as c:
        return c.execute(text(sql), params).mappings().one()


def request(q, index=0):
    execute(q, "INSERT INTO track_lyrics_translations(track_id,status) VALUES (:id,'requested')", id=q['tracks'][index])


def demand(q, indices=(0,)):
    with q['engine'].begin() as c:
        # The demanded fixture is a complete one-track album, not a truncated scope.
        for index, track in enumerate(q['tracks']):
            if index not in indices:
                c.execute(text('DELETE FROM tracks WHERE id=:id'), {'id': track})
        c.execute(text('UPDATE albums SET total_tracks=:count WHERE id=:id'),
                  {'id': q['album'], 'count': len(indices)})
        store = LyricsDemandStore(c)
        scope = store.reset_scope(q['user'], 'saved')
        job = store.add_demand(q['user'], scope['id'], scope['generation'], q['album_sid'], 'album:' + q['album_sid'])
        store.set_catalog(job, q['album'], [q['tracks'][i] for i in indices], complete=True)
    q['jobs'].append(job)
    return job


def candidate(q, job, index=0):
    return dict(job_id=job, track_id=q['tracks'][index])


def worker(q, client=None, clock=time.time):
    return QueueWorker(q['engine'], q['state'], client or FakeClient(), daily_cap=1000, clock=clock)


def test_idle_tick_never_calls_model(queue):
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'idle'
    assert client.calls == []


def test_legacy_request_processes_automatically_into_viewer(queue):
    request(queue)
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'saved'
    assert len(client.calls) == 1
    assert client.calls[0][1] == MODEL
    with Session(queue['engine']) as db:
        view = LyricsService().get_normalized(db, spotify_track_id=queue['spotify'][0])
        assert view.translation.status == 'done'
        assert view.segments[0].text_ko == '한국어 자리표시'
        assert view.segments[1].text_ko is None
    saved = row(queue, 'SELECT model,translator_version FROM track_lyrics_translations WHERE track_id=:id', id=queue['tracks'][0])
    assert saved['model'] == ACTUAL
    assert saved['translator_version'] == VERSIONS['lyrics']
    assert worker(queue, client).tick(MODEL) in ('idle', 'scan_wrap')
    assert len(client.calls) == 1


def test_matched_genius_queue_processes_without_lyrics_request(queue):
    annotation = int(uuid4().hex[:14], 16)
    execute(queue, "INSERT INTO track_genius_songs(track_id,genius_song_id,match_status) VALUES (:track,:id,'matched')", track=queue['tracks'][0], id=annotation)
    execute(queue, "INSERT INTO track_genius_annotations(genius_annotation_id,track_id,fragment,referent_ordinal,body_source) VALUES (:id,:track,'placeholder',0,'Synthetic commentary')", id=annotation, track=queue['tracks'][0])
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'saved'
    saved = row(queue, 'SELECT body_ko,translation_status,translator_model,translator_version FROM track_genius_annotations WHERE genius_annotation_id=:id', id=annotation)
    assert saved['body_ko'] == '한국어 자리표시'
    assert saved['translation_status'] == 'done'
    assert saved['translator_model'] == ACTUAL
    assert saved['translator_version'] == VERSIONS['genius']
    assert len(client.calls) == 1


@pytest.mark.parametrize('old_claude', [False, True])
def test_album_demand_links_or_rebinds_old_claude_then_completes(queue, old_claude):
    job = demand(queue)
    old_id = None
    if old_claude:
        with Session(queue['engine']) as db:
            _, fp, _ = _source(db, queue['tracks'][0], 'lyrics')
            store = LyricsDemandStore(db.connection())
            snapshot = store.track_snapshot(job, queue['tracks'][0])
            old_id = store.ensure_work(job, queue['tracks'][0], fp, 'ko', 'claude.sonnet/v2',
                expected_work_id=snapshot['work_id'], expected_source_revision=snapshot['source_revision'])
            db.commit()
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'saved'
    joined = row(queue, 'SELECT lat.work_id,w.translator_version,w.status,w.manual_requested FROM lyrics_album_tracks lat JOIN lyrics_translation_work w ON w.id=lat.work_id WHERE lat.job_id=:job', job=job)
    assert joined['translator_version'] == VERSIONS['lyrics']
    assert joined['status'] == 'done'
    assert joined['manual_requested'] is False
    if old_id:
        assert joined['work_id'] != old_id
        assert row(queue, 'SELECT status FROM lyrics_translation_work WHERE id=:id', id=old_id)['status'] == 'cancelled'
    with queue['engine'].begin() as c:
        assert LyricsDemandStore(c).album_progress(queue['user'], job)['state'] == 'done'
    assert len(client.calls) == 1


@pytest.mark.parametrize('covered,reason', [('cached', 'already_translated'), ('manual', 'manual_translation'), ('korean', 'already_korean')])
def test_covered_album_reconciles_without_inference(queue, covered, reason):
    job = demand(queue)
    if covered == 'korean':
        execute(queue, 'UPDATE track_lyrics SET lyric_plain=:body WHERE track_id=:id', id=queue['tracks'][0], body='한국어 자리표시 하나\n한국어 자리표시 둘')
    else:
        with Session(queue['engine']) as db:
            _, fp, _ = _source(db, queue['tracks'][0], 'lyrics')
        execute(queue, "INSERT INTO track_lyrics_translations(track_id,status,origin,source_fingerprint,segments,normalizer_version) VALUES (:id,'done',:origin,:fp,CAST(:segments AS jsonb),1)", id=queue['tracks'][0], origin='manual' if covered == 'manual' else 'poller', fp='f' * 64 if covered == 'manual' else fp, segments=json.dumps([{'i': 0, 'text_ko': '기존 자리표시'}]))
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'scanned'
    covered_row = row(queue, 'SELECT source_state,last_reason,work_id FROM lyrics_album_tracks WHERE job_id=:job', job=job)
    assert covered_row['source_state'] == 'not_required'
    assert covered_row['last_reason'] == reason
    assert covered_row['work_id'] is None
    with queue['engine'].begin() as c:
        assert LyricsDemandStore(c).album_progress(queue['user'], job)['state'] == 'done'
    assert not client.calls


def test_canceled_album_cannot_bind_or_claim(queue):
    job = demand(queue)
    execute(queue, 'UPDATE lyrics_album_jobs SET cancelled=true WHERE id=:id', id=job)
    with Session(queue['engine']) as db, pytest.raises(StaleDiscovery):
        bind_album(db, candidate(queue, job))
    client = FakeClient()
    assert worker(queue, client).tick(MODEL) == 'idle'
    assert client.calls == []


def test_album_canceled_during_inference_cannot_complete(queue):
    job = demand(queue)
    def cancel(_):
        execute(queue, 'UPDATE lyrics_album_jobs SET cancelled=true WHERE id=:id', id=job)
    client = FakeClient(hook=cancel)
    assert worker(queue, client).tick(MODEL) == 'superseded_result'
    with queue['engine'].connect() as c:
        assert c.execute(text('SELECT count(*) FROM track_lyrics_translations WHERE track_id=:id'), {'id': queue['tracks'][0]}).scalar_one() == 0
    assert len(client.calls) == 1


def test_queue_temporary_failure_has_delayed_two_attempt_cap(queue):
    request(queue)
    client = FakeClient(error=PlanInferenceError('temporary_error'))
    w = worker(queue, client)
    assert w.tick(MODEL) == 'temporary_error'
    assert w.tick(MODEL) == 'scan_wrap'
    assert w.tick(MODEL) == 'scanned'
    assert len(client.calls) == 1
    execute(queue, "UPDATE lyrics_translation_work SET next_attempt_at=now()-interval '1 second' WHERE track_id=:id", id=queue['tracks'][0])
    assert w.tick(MODEL) == 'scan_wrap'
    assert w.tick(MODEL) == 'temporary_error'
    execute(queue, "UPDATE lyrics_translation_work SET next_attempt_at=now()-interval '1 second' WHERE track_id=:id", id=queue['tracks'][0])
    assert w.tick(MODEL) == 'scan_wrap'
    assert w.tick(MODEL) == 'scanned'
    assert len(client.calls) == 2
    assert row(queue, 'SELECT attempts FROM lyrics_translation_work WHERE track_id=:id', id=queue['tracks'][0])['attempts'] == 2


def limit_error():
    return PlanInferenceError(LIMIT, pause=True, limit=True)


def test_plan_usage_limit_waits_an_hour_then_resumes(queue):
    request(queue)
    clock = Clock()
    client = FakeClient(error=limit_error())
    w = worker(queue, client, clock)
    assert w.tick(MODEL) == LIMIT
    settings = PrivateState(queue['state'].directory).settings()
    assert settings['enabled'] is True and settings.get('pause_reason') is None
    assert settings['resume_at'] == clock.now + 3600
    assert settings['limit_hits'] == 1
    # The rejected request produced nothing, so the source keeps both of its attempts.
    assert row(queue, 'SELECT last_reason,status,attempts FROM lyrics_translation_work WHERE track_id=:id', id=queue['tracks'][0]) == {'last_reason': LIMIT, 'status': 'retryable_error', 'attempts': 0}
    clock.now += 3599
    assert w.tick(MODEL) == 'usage_limit_wait'
    assert len(client.calls) == 1
    clock.now += 2
    client.error = None
    assert w.tick(MODEL) == 'scan_wrap'
    assert w.tick(MODEL) == 'saved'
    assert len(client.calls) == 2
    settings = PrivateState(queue['state'].directory).settings()
    assert 'limit_hits' not in settings and 'resume_at' not in settings


def test_third_consecutive_usage_limit_stops_the_worker(queue):
    request(queue)
    request(queue, index=1)
    request(queue, index=2)
    clock = Clock()
    client = FakeClient(error=limit_error())
    w = worker(queue, client, clock)
    for hits in (1, 2):
        assert w.tick(MODEL) == LIMIT
        assert PrivateState(queue['state'].directory).settings()['limit_hits'] == hits
        clock.now += 3601
    assert w.tick(MODEL) == LIMIT
    settings = PrivateState(queue['state'].directory).settings()
    assert settings['enabled'] is False
    assert settings['pause_reason'] == LIMIT
    assert 'resume_at' not in settings
    assert w.tick(MODEL) == 'owner_paused'
    assert len(client.calls) == 3
    assert 'limit_hits' not in settings  # A re-enable starts a fresh streak.


def test_repeated_limits_on_one_source_never_exhaust_its_attempts(queue):
    request(queue)
    clock = Clock()
    client = FakeClient(error=limit_error())
    w = worker(queue, client, clock)
    for _ in range(2):
        assert w.tick(MODEL) == LIMIT
        clock.now += 3601
        assert w.tick(MODEL) == 'scan_wrap'
    client.error = None
    assert w.tick(MODEL) == 'saved'
    assert row(queue, 'SELECT status,attempts FROM lyrics_translation_work WHERE track_id=:id', id=queue['tracks'][0]) == {'status': 'done', 'attempts': 1}


@pytest.mark.parametrize('control,last_reason,attempts', [
    ({'pause_reason': 'owner_paused'}, 'user_cancelled', 1),
    ({'pause_reason': 'plan_authorization_or_usage'}, 'claim_released', 0),
    ({'resume_at': 'future'}, 'claim_released', 0)])
def test_only_the_owner_stop_cancels_a_claimed_source(queue, control, last_reason, attempts):
    request(queue)
    client = FakeClient()
    w = worker(queue, client)
    claimed_row, claim = w._claim()
    # A sibling (or the owner) changes the controls between this slot's claim and its stream.
    settings = queue['state'].settings()
    settings.update({k: (time.time() + 600 if v == 'future' else v) for k, v in control.items()})
    queue['state'].write('settings.json', settings)
    assert w._infer(MODEL, claimed_row, claim) in ('owner_paused', 'usage_limit_wait')
    assert client.calls == []
    assert row(queue, 'SELECT status,last_reason,attempts FROM lyrics_translation_work WHERE track_id=:id', id=queue['tracks'][0]) == {'status': 'retryable_error', 'last_reason': last_reason, 'attempts': attempts}


def test_sibling_streams_rejected_by_one_limit_event_count_once(queue):
    clock = Clock()
    w = worker(queue, clock=clock)
    for _ in range(3):
        w.limit_hit(LIMIT)
    settings = PrivateState(queue['state'].directory).settings()
    assert settings['limit_hits'] == 1 and settings['enabled'] is True
    # A sibling that started before the event and finishes inside the wait keeps the wait.
    w.limit_cleared()
    assert PrivateState(queue['state'].directory).settings()['resume_at'] == clock.now + 3600


def test_auth_rejection_still_stops_immediately(queue):
    request(queue)
    reason = 'subscription_sharing_user_not_eligible'
    client = FakeClient(error=PlanInferenceError(reason, pause=True))
    assert worker(queue, client).tick(MODEL) == reason
    settings = PrivateState(queue['state'].directory).settings()
    assert settings['enabled'] is False
    assert settings['pause_reason'] == reason
    assert settings['model'] == MODEL
    assert 'resume_at' not in settings
    assert len(client.calls) == 1


def test_bounded_cursor_advances_past_poison_and_oversize_rows(queue):
    # More than one page of oversized requested sources sorts before a valid source.
    poison = [UUID(int=i + 1) for i in range(31)]
    with queue['engine'].begin() as c:
        for track in poison:
            c.execute(text("INSERT INTO tracks(id,album_id,title,spotify_id) VALUES (:id,:album,'Oversize',:sid)"), {'id': track, 'album': queue['album'], 'sid': 'queue-poison-' + uuid4().hex})
            c.execute(text("INSERT INTO track_lyrics(track_id,match_status,lyric_plain) VALUES (:id,'matched',:body)"), {'id': track, 'body': 'x' * 16001})
            c.execute(text("INSERT INTO track_lyrics_translations(track_id,status) VALUES (:id,'requested')"), {'id': track})
    request(queue)
    client = FakeClient()
    w = worker(queue, client)
    assert w.tick(MODEL) == 'scanned'
    assert not client.calls
    assert w.tick(MODEL) == 'saved'
    assert len(client.calls) == 1
    assert client.calls[0][0]['spotify_track_id'] == queue['spotify'][0]
    with queue['engine'].connect() as c:
        assert c.execute(text("SELECT count(*) FROM track_lyrics_translations WHERE track_id=ANY(:ids) AND status='requested'"), {'ids': poison}).scalar_one() == 31



def test_inference_runs_with_all_db_connections_returned(queue):
    request(queue)
    def assert_closed(_):
        assert queue['engine'].pool.checkedout() == 0
    assert worker(queue, FakeClient(hook=assert_closed)).tick(MODEL) == 'saved'


def test_persistent_pause_blocks_later_queue_inference(queue):
    request(queue)
    request(queue, index=1)
    reason = 'subscription_sharing_user_not_eligible'
    client = FakeClient(error=PlanInferenceError(reason, pause=True))
    w = worker(queue, client)
    assert w.tick(MODEL) == reason
    assert w.tick(MODEL) == 'owner_paused'
    assert len(client.calls) == 1


def test_disabled_scheduled_main_stops_before_database_access(queue, monkeypatch):
    import scripts.gpt_queue_worker as module
    settings = queue['state'].settings()
    settings.update(enabled=False, pause_reason='owner_paused')
    queue['state'].write('settings.json', settings)
    def fail_if_db(*args, **kwargs):
        raise AssertionError('Disabled scheduler must not access DB')
    monkeypatch.setattr(module, 'create_engine', fail_if_db)
    assert module.main(['--state-dir', str(queue['state'].directory)]) == 0


def test_usage_limit_wait_stops_scheduled_main_before_database_access(queue, monkeypatch):
    import scripts.gpt_queue_worker as module
    settings = queue['state'].settings()
    settings.update(resume_at=time.time() + 600, limit_hits=1)
    queue['state'].write('settings.json', settings)
    def fail_if_db(*args, **kwargs):
        raise AssertionError('Usage-limit wait must not access DB')
    monkeypatch.setattr(module, 'create_engine', fail_if_db)
    assert module.main(['--state-dir', str(queue['state'].directory)]) == 0


def test_terminal_refusal_does_not_retry_on_later_scan(queue):
    request(queue)
    client = FakeClient(error=PlanInferenceError('refused'))
    w = worker(queue, client)
    assert w.tick(MODEL) == 'refused'
    assert w.tick(MODEL) == 'scan_wrap'
    assert w.tick(MODEL) == 'scanned'
    assert len(client.calls) == 1
    assert row(queue, 'SELECT attempts,last_reason FROM lyrics_translation_work WHERE track_id=:id',
               id=queue['tracks'][0])['attempts'] == 1



@pytest.mark.parametrize('reason', ['subscription_sharing_user_not_eligible', LIMIT])
@pytest.mark.parametrize('cleanup_error', ['claim_lost', 'database_failed'])
def test_plan_stop_or_wait_survives_failed_claim_cleanup(queue, monkeypatch, cleanup_error, reason):
    from fastapi import HTTPException
    request(queue)
    client = FakeClient(error=PlanInferenceError(reason, pause=True, limit=reason == LIMIT))
    w = worker(queue, client)
    def cannot_cleanup(*args, **kwargs):
        if cleanup_error == 'claim_lost':
            raise HTTPException(409, 'Synthetic expired claim')
        raise RuntimeError('Synthetic database outage')
    monkeypatch.setattr(w.store, 'fail', cannot_cleanup)
    assert w.tick(MODEL) == reason
    persisted = PrivateState(queue['state'].directory).settings()
    if reason == LIMIT:
        assert persisted['enabled'] is True and persisted['resume_at'] > time.time()
    else:
        assert persisted['enabled'] is False
        assert persisted['pause_reason'] == reason
    assert len(client.calls) == 1


def test_run_keeps_three_inferences_in_flight_without_sharing_a_source(queue):
    for index in range(4):
        request(queue, index)
    barrier = threading.Barrier(3, timeout=20)
    def overlap(_):
        if len(client.calls) <= 3:
            barrier.wait()  # Times out (BrokenBarrierError) unless three streams overlap.
    client = FakeClient(hook=overlap)
    outcomes = worker(queue, client).run(MODEL)
    assert outcomes['saved'] == 4
    assert sorted(c[0]['spotify_track_id'] for c in client.calls) == sorted(queue['spotify'])
    with queue['engine'].connect() as c:
        assert c.execute(text("SELECT count(*) FROM track_lyrics_translations WHERE track_id=ANY(:ids) AND status='done'"),
                         {'ids': queue['tracks']}).scalar_one() == 4
        assert c.execute(text('SELECT sum(attempts) FROM lyrics_translation_work WHERE track_id=ANY(:ids)'),
                         {'ids': queue['tracks']}).scalar_one() == 4


def test_extra_slots_never_exceed_the_lease_limit(queue):
    for index in range(4):
        request(queue, index)
    turn, live, peak = threading.Condition(), [0], [0]
    def hold(_):
        # Hold every stream until three overlap, then long enough for a 4th slot to claim.
        with turn:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
            turn.notify_all()
            turn.wait_for(lambda: peak[0] >= 3, timeout=30)
        time.sleep(5)
        with turn:
            live[0] -= 1
    client = FakeClient(hook=hold)
    outcomes = worker(queue, client).run(MODEL, parallel=4)
    assert peak[0] == 3
    # The 4th slot found every slot held, finished the pass, and ended the run.
    assert outcomes['saved'] == 3


def test_usage_is_summed_per_utc_day(queue):
    request(queue)
    request(queue, index=1)
    clock = Clock()
    clock.now = 1760313599.0  # 2025-10-12T23:59:59Z
    w = worker(queue, clock=clock)
    assert w.tick(MODEL) == 'saved'
    clock.now += 2
    assert w.tick(MODEL) == 'saved'
    daily = PrivateState(queue['state'].directory).read('usage.json')
    assert daily == {'2025-10-12': {'requests': 1, **USAGE}, '2025-10-13': {'requests': 1, **USAGE}}


def test_usage_totals_stay_exact_under_concurrent_writers(queue):
    w = worker(queue)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: w.record_usage(ACTUAL, USAGE), range(30)))
    (totals,) = PrivateState(queue['state'].directory).read('usage.json').values()
    assert totals == {'requests': 30, **{k: v * 30 for k, v in USAGE.items()}}


def test_disabling_mid_run_stops_new_claims(queue):
    for index in range(3):
        request(queue, index)
    def disable(_):
        settings = queue['state'].settings()
        settings['enabled'] = False
        queue['state'].write('settings.json', settings)
    client = FakeClient(hook=disable)
    outcomes = worker(queue, client).run(MODEL, parallel=1)
    assert outcomes == {'saved': 1, 'disabled': 1}
    assert len(client.calls) == 1


def test_one_finished_pass_ends_every_slot(queue):
    request(queue)
    outcomes = worker(queue).run(MODEL)
    assert outcomes.get('saved') == 1
    # Exactly one slot reaches a final outcome; the others stop on the shared signal.
    # Without it each slot runs to its own wrap, rescanning the queue up to 3 times.
    assert sum(v for k, v in outcomes.items() if k in FINAL) == 1


def test_a_failing_slot_stops_the_run_and_raises(queue):
    for index in range(4):
        request(queue, index)
    def first_fails(_):
        if len(client.calls) == 1:
            raise RuntimeError('synthetic')
        time.sleep(1)
    client = FakeClient(hook=first_fails)
    with pytest.raises(RuntimeError):
        worker(queue, client).run(MODEL)
    # Siblings finish what they hold but claim nothing new: the 4th source is never sent.
    assert len(client.calls) <= 3
