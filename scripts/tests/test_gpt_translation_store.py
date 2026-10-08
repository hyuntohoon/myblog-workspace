"""Real PostgreSQL claims, races and publication; canonical schema is preloaded.

Uses only uniquely named fixture rows, cleaned by album cascade. The service
never calls an LLM; the supplied translations are test fixtures.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "myblog_backend", ROOT / "myblog_shared_db" / "src"):
    sys.path.insert(0, str(path))
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scripts.gpt_translation_store import GPTTranslationStore
from app.services.lyrics_service import LyricsService, compute_body_fingerprint

TEST_DB_URL = os.environ.get("TEST_DB_URL")
pytestmark = [pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DB_URL not set")]
SERVICE = GPTTranslationStore()
RESULT = [{"i": 0, "text_ko": "첫 줄"}, {"i": 1, "text_ko": ""}, {"i": 2, "text_ko": "두 번째 줄"}]


@pytest.fixture
def catalog(monkeypatch):
    engine = create_engine(TEST_DB_URL)
    album = uuid4()
    tracks = [uuid4() for _ in range(3)]
    spotify_ids = [uuid4().hex[:22] for _ in tracks]
    annotation = int(uuid4().hex[:14], 16)
    monkeypatch.setattr(SERVICE, "daily_cap", 10)
    with engine.begin() as connection:
        assert connection.execute(text("SELECT to_regclass('lyrics_translation_work')")).scalar(), "Load canonical schema first"
        connection.execute(text("INSERT INTO albums(id,title,spotify_id) VALUES (:id,'GPT fixture',:spotify)"),
                           {"id": album, "spotify": "gpt-fixture-"+uuid4().hex})
        for track, spotify in zip(tracks, spotify_ids):
            connection.execute(text("INSERT INTO tracks(id,album_id,title,spotify_id) VALUES (:id,:album,'GPT fixture',:spotify)"),
                               {"id": track, "album": album, "spotify": spotify})
            connection.execute(text("INSERT INTO track_lyrics(track_id,match_status,lyric_plain) VALUES (:id,'matched','first line\n\nsecond line')"), {"id": track})
        connection.execute(text("INSERT INTO track_genius_songs(track_id,genius_song_id,match_status) VALUES (:id,:song,'matched')"),
                           {"id": tracks[0], "song": annotation})
        connection.execute(text("""INSERT INTO track_genius_annotations
            (genius_annotation_id,track_id,fragment,referent_ordinal,body_source)
            VALUES (:annotation,:track,'first line',0,'A commentary paragraph.')"""),
                           {"annotation": annotation, "track": tracks[0]})
    yield engine, tracks, spotify_ids, annotation
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM albums WHERE id=:id"), {"id": album})
    engine.dispose()


def prepare(catalog, index=0, **kwargs):
    engine, _, spotify, _ = catalog
    with Session(engine) as db:
        output = SERVICE.prepare(db, spotify[index], **kwargs)
        db.commit()
        return output


def submit(catalog, prepared, segments=RESULT, **kwargs):
    with Session(catalog[0]) as db:
        output = SERVICE.submit(db, UUID(prepared["work_id"]), UUID(prepared["claim_token"]), segments, **kwargs)
        db.commit()
        return output


def edit(catalog, sql, **params):
    with catalog[0].begin() as connection:
        return connection.execute(text(sql), params)


def test_saved_viewer_cache_and_duplicate_submission(catalog):
    claim = prepare(catalog)
    assert submit(catalog, claim)["status"] == "saved"
    assert submit(catalog, claim)["status"] == "already_completed"
    assert prepare(catalog)["status"] == "cached"
    with Session(catalog[0]) as db:
        view = LyricsService().get_normalized(db, spotify_track_id=catalog[2][0])
        assert view.translation.status == "done"
        assert view.segments[0].text_ko == "첫 줄"
        assert view.segments[1].text_ko is None
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim, [{"i": 0, "text_ko": "changed"}])
    assert error.value.status_code == 409


def test_two_gpts_only_admit_one_claim(catalog):
    def run():
        try:
            return prepare(catalog)["status"]
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results, key=str) == sorted(["ready", 409], key=str)
    with catalog[0].connect() as connection:
        assert connection.execute(text("SELECT attempts FROM lyrics_translation_work WHERE track_id=:track"), {"track": catalog[1][0]}).scalar_one() == 1


def test_daily_admission_cap_is_shared_across_sources(catalog, monkeypatch):
    monkeypatch.setattr(SERVICE, "daily_cap", 1)
    prepare(catalog)
    with pytest.raises(HTTPException) as error:
        prepare(catalog, index=1)
    assert error.value.status_code == 429


@pytest.mark.parametrize("change", ["expired", "replaced"])
def test_expired_or_replaced_claim_cannot_publish(catalog, change):
    claim = prepare(catalog)
    if change == "expired":
        edit(catalog, "UPDATE lyrics_translation_work SET lease_until=now()-interval '1 minute' WHERE id=:id", id=UUID(claim["work_id"]))
    else:
        edit(catalog, "UPDATE lyrics_translation_work SET claim_token=gen_random_uuid() WHERE id=:id", id=UUID(claim["work_id"]))
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim)
    assert error.value.status_code == 409
    with catalog[0].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM track_lyrics_translations WHERE track_id=:track"), {"track": catalog[1][0]}).scalar() == 0


def test_source_change_and_invalid_alignment_do_not_complete(catalog):
    claim = prepare(catalog)
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim, [{"i": 0, "text_ko": "only one"}])
    assert error.value.status_code == 422
    edit(catalog, "UPDATE track_lyrics SET lyric_plain='different source' WHERE track_id=:track", track=catalog[1][0])
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim)
    assert error.value.status_code == 409
    with catalog[0].connect() as connection:
        assert connection.execute(text("SELECT status FROM lyrics_translation_work WHERE id=:id"), {"id": UUID(claim["work_id"])}).scalar_one() == "running"


@pytest.mark.parametrize("newer", ["manual", "request"])
def test_newer_manual_edit_or_request_wins(catalog, newer):
    claim = prepare(catalog)
    edit(catalog, """INSERT INTO track_lyrics_translations
        (track_id,status,origin,updated_at,segments,source_fingerprint,normalizer_version,translated_at)
        VALUES (:track,:status,:origin,clock_timestamp(),CAST(:segments AS jsonb),:fp,1,now())""", track=catalog[1][0],
        segments='[{"i":0,"text_ko":"수동 번역"}]', fp=claim["source_fingerprint"],
        status="done" if newer == "manual" else "requested", origin="manual" if newer == "manual" else "poller")
    assert submit(catalog, claim)["status"] == "stored_not_published"
    with catalog[0].connect() as connection:
        row = connection.execute(text("SELECT status,origin FROM track_lyrics_translations WHERE track_id=:track"), {"track": catalog[1][0]}).one()
        assert row.status == ("done" if newer == "manual" else "requested")
        assert row.origin == ("manual" if newer == "manual" else "poller")
    if newer == "request":
        # A later, explicit GPT request reuses the stored result and resolves
        # the newer pending request without another inference admission.
        assert prepare(catalog)["status"] == "cached"
        with catalog[0].connect() as connection:
            assert connection.execute(text("SELECT status FROM track_lyrics_translations WHERE track_id=:track"), {"track": catalog[1][0]}).scalar_one() == "done"


def test_refusal_stops_and_temporary_failure_has_two_attempt_cap(catalog):
    claim = prepare(catalog)
    with Session(catalog[0]) as db:
        SERVICE.fail(db, UUID(claim["work_id"]), UUID(claim["claim_token"]), "refused")
        db.commit()
    with pytest.raises(HTTPException) as error:
        prepare(catalog)
    assert error.value.status_code == 409
    for _ in range(2):
        edit(catalog, "UPDATE lyrics_translation_work SET next_attempt_at=now()-interval '1 second' WHERE track_id=:track", track=catalog[1][1])
        transient = prepare(catalog, index=1)
        with Session(catalog[0]) as db:
            SERVICE.fail(db, UUID(transient["work_id"]), UUID(transient["claim_token"]), "temporary_error")
            db.commit()
    with pytest.raises(HTTPException) as error:
        prepare(catalog, index=1)
    assert error.value.status_code == 409


def test_genius_lease_source_hash_and_manual_lyrics_are_independent(catalog):
    edit(catalog, """INSERT INTO track_lyrics_translations
        (track_id,status,origin,segments,source_fingerprint,normalizer_version,translated_at)
        VALUES (:track,'done','manual',CAST(:segments AS jsonb),:fp,1,now())""",
        track=catalog[1][0], segments='[{"i":0,"text_ko":"수동 번역"}]', fp='a'*64)
    claim = prepare(catalog, kind="genius", annotation_id=catalog[3])
    assert claim["status"] == "ready"
    translated = [{"i": 0, "text_ko": "해설 문단."}]
    assert submit(catalog, claim, translated, annotation_id=catalog[3])["status"] == "saved"
    assert prepare(catalog, kind="genius", annotation_id=catalog[3])["status"] == "cached"
    with catalog[0].connect() as connection:
        row = connection.execute(text("SELECT body_ko,body_source_fingerprint FROM track_genius_annotations WHERE genius_annotation_id=:id"), {"id": catalog[3]}).one()
        assert row.body_ko == "해설 문단."
        assert row.body_source_fingerprint == compute_body_fingerprint("A commentary paragraph.")


def test_genius_changed_source_rejects_old_result(catalog):
    claim = prepare(catalog, kind="genius", annotation_id=catalog[3])
    edit(catalog, "UPDATE track_genius_annotations SET body_source='new paragraph' WHERE genius_annotation_id=:id", id=catalog[3])
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim, [{"i": 0, "text_ko": "옛 해설"}], annotation_id=catalog[3])
    assert error.value.status_code == 409


@pytest.mark.parametrize("segments", [None, {}, [], [None], [{"i": True, "text_ko": "x"}],
    [{"i": 0, "text_ko": None}], [{"text_ko": "x"}], [{"i": 0, "text_ko": "x" * 64001}],
    [{"i": 0, "text_ko": "첫 줄"}, {"i": 1, "text_ko": "gap"}, {"i": 2, "text_ko": "마지막"}],
    [{"i": 0, "text_ko": " "}, {"i": 1, "text_ko": ""}, {"i": 2, "text_ko": "마지막"}]])
def test_malformed_segments_never_complete(catalog, segments):
    claim = prepare(catalog)
    with pytest.raises(HTTPException) as error:
        submit(catalog, claim, segments)
    assert error.value.status_code == 422
    with catalog[0].connect() as c:
        assert c.execute(text("SELECT status FROM lyrics_translation_work WHERE id=:id"),
                         {"id": UUID(claim["work_id"])}).scalar_one() == "running"
        assert c.execute(text("SELECT count(*) FROM track_lyrics_translations WHERE track_id=:id"),
                         {"id": catalog[1][0]}).scalar_one() == 0


def test_global_serialization_also_covers_different_tracks(catalog):
    def run(index):
        try:
            return prepare(catalog, index=index)["status"]
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [0, 1]))
    assert sorted(results, key=str) == sorted(["ready", 409], key=str)
    with catalog[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM lyrics_translation_work WHERE track_id=ANY(:tracks) AND status='running'"),
                         {"tracks": catalog[1]}).scalar_one() == 1


def test_actual_model_provenance_is_saved(catalog):
    claim = prepare(catalog)
    assert submit(catalog, claim, model="eligible-model-real-version")["status"] == "saved"
    with catalog[0].connect() as c:
        row = c.execute(text("SELECT model,translator_version FROM track_lyrics_translations WHERE track_id=:id"),
                        {"id": catalog[1][0]}).one()
        assert row.model == "eligible-model-real-version"
        assert row.translator_version == "chatgpt/lyrics-ko-v1"


def test_temporary_retry_is_not_due_until_backoff(catalog):
    claim = prepare(catalog)
    with Session(catalog[0]) as db:
        SERVICE.fail(db, UUID(claim["work_id"]), UUID(claim["claim_token"]), "temporary_error")
        db.commit()
    with pytest.raises(HTTPException) as error:
        prepare(catalog)
    assert error.value.status_code == 409
    with catalog[0].connect() as c:
        row = c.execute(text("SELECT attempts,next_attempt_at>now() AS delayed FROM lyrics_translation_work WHERE id=:id"),
                        {"id": UUID(claim["work_id"])}).one()
        assert row.attempts == 1
        assert row.delayed



def test_cache_republication_retains_actual_model_and_hides_internal_metadata(catalog):
    claim = prepare(catalog)
    edit(catalog, """INSERT INTO track_lyrics_translations(track_id,status,updated_at)
        VALUES (:track,'requested',clock_timestamp())""", track=catalog[1][0])
    assert submit(catalog, claim, model="actual-before-newer-request")["status"] == "stored_not_published"
    cached = prepare(catalog)
    assert cached["status"] == "cached"
    assert cached["segments"] == RESULT
    with catalog[0].connect() as c:
        saved = c.execute(text("SELECT model,segments FROM track_lyrics_translations WHERE track_id=:id"),
                          {"id": catalog[1][0]}).one()
        assert saved.model == "actual-before-newer-request"
        assert saved.segments == RESULT
    with Session(catalog[0]) as db:
        view = LyricsService().get_normalized(db, spotify_track_id=catalog[2][0])
        assert view.translation.status == "done"
        assert view.segments[0].text_ko == "첫 줄"
        assert "_translator_model" not in view.model_dump_json()
