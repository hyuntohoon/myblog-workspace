"""V57 demand -> Claude translation bridge, against real Postgres.

FEAT-lyrics-listening-experience Step 3. These drive the REAL poller wiring —
``lyrics_translate_poller.demand_bridge()`` with the real backend normalizer, the real
fingerprint and the real V57 store — and stub only the model subprocess. That composition
is the thing worth testing: the fingerprint the bridge stores has to equal the one the read
path re-derives, and only the actual imports prove it.

The headline test is the chain the RFC's Step 3 verification asks for: a track whose source
does not exist yet must reach a published translation with **no second manual request**,
purely from repeated firings.

Requires TEST_DB_URL, plus the backend and shared_db checkouts on the path:

    TEST_DB_URL=... DATABASE_URL="$TEST_DB_URL" \\
    PYTHONPATH=<backend>:<shared_db>/src \\
    myblog_backend/.venv/bin/python -m unittest \\
        discover -s scripts/tests -p 'test_lyrics_demand_translate.py'
"""
from __future__ import annotations

import json
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

TEST_DB_URL = os.environ.get("TEST_DB_URL")

if TEST_DB_URL:
    import psycopg
    from psycopg.rows import dict_row
    from sqlalchemy import create_engine, text

    import lyrics_translate_poller as poller  # noqa: E402
    from scripts.lyrics_demand_translate import TRANSLATOR_VERSION, run_once

PREFIX = "lyr_dt_"
HANDLE_PREFIX = "lyr-dt-"
ARTIST = "Bridge Primary"
# Synthetic placeholder source — never real lyrics.
BODY_EN = "placeholder alpha\nplaceholder bravo\n\nplaceholder charlie"
BODY_KO = "한국어 자리표시 하나\n한국어 자리표시 둘"


def _conn():
    return psycopg.connect(TEST_DB_URL.replace("postgresql+psycopg", "postgresql"),
                           connect_timeout=30, row_factory=dict_row)


@unittest.skipUnless(TEST_DB_URL, "requires TEST_DB_URL (Postgres test database)")
class DemandBridgeTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_DB_URL, pool_pre_ping=True, future=True)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    # ── fixture ────────────────────────────────────────────────────────────────────────
    def setUp(self):
        self._cleanup()
        self.calls: list[list[str]] = []
        self.during_call = None
        self.sfx = uuid.uuid4().hex[:8]
        self.album_sid = f"{PREFIX}alb_{self.sfx}"
        self.user = uuid.uuid4()
        self.album = uuid.uuid4()
        self.track = uuid.uuid4()

        with self.engine.begin() as c:
            c.execute(text("INSERT INTO users (id, handle, display_name) "
                           "VALUES (:i, :h, 'Bridge Member')"),
                      {"i": self.user, "h": f"{HANDLE_PREFIX}{self.sfx}"})
            c.execute(text("INSERT INTO albums (id, spotify_id, title, total_tracks) "
                           "VALUES (:i, :s, 'Bridge Album', 1)"),
                      {"i": self.album, "s": self.album_sid})
            artist = uuid.uuid4()
            c.execute(text("INSERT INTO artists (id, spotify_id, name, popularity) "
                           "VALUES (:i, :s, :n, 40)"),
                      {"i": artist, "s": f"{PREFIX}art_{self.sfx}", "n": ARTIST})
            c.execute(text("INSERT INTO tracks (id, album_id, spotify_id, title, duration_sec) "
                           "VALUES (:i, :a, :s, 'Bridge Track', 200)"),
                      {"i": self.track, "a": self.album, "s": f"{PREFIX}trk_{self.sfx}"})
            c.execute(text("INSERT INTO track_artists (track_id, artist_id) VALUES (:t, :a)"),
                      {"t": self.track, "a": artist})

        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            store = LyricsDemandStore(c)
            scope = store.reset_scope(self.user, "saved")
            self.job = store.add_demand(self.user, scope["id"], scope["generation"],
                                        self.album_sid, "album:" + self.album_sid)
            store.set_catalog(self.job, self.album, [self.track], complete=True)

        # Real wiring; only the model subprocess is stubbed.
        os.environ["DATABASE_URL"] = TEST_DB_URL
        poller._SA_ENGINE = None
        self._real_translate = poller.claude_translate
        poller.claude_translate = self._stub_translate
        self.bridge = poller.demand_bridge()

    def tearDown(self):
        poller.claude_translate = self._real_translate
        # Dispose before dropping the reference: nulling the module global alone leaves the
        # pool's psycopg connections to be closed by the garbage collector, which is what
        # raises ResourceWarning and holds Neon sessions open across the suite.
        if poller._SA_ENGINE is not None:
            poller._SA_ENGINE.dispose()
        poller._SA_ENGINE = None
        self._cleanup()

    def _stub_translate(self, lines):
        self.calls.append(list(lines))
        if self.during_call is not None:
            hook, self.during_call = self.during_call, None
            hook()
        return [f"KO {ln}" for ln in lines]

    def _cleanup(self):
        with self.engine.begin() as c:
            for stmt in (
                # Jobs first: lyrics_album_tracks cascades from them, and its
                # fk_lyrics_album_track_work reference is what pins the work rows.
                "DELETE FROM lyrics_album_jobs WHERE spotify_album_id LIKE :p",
                "DELETE FROM lyrics_translation_work WHERE track_id IN "
                "(SELECT id FROM tracks WHERE spotify_id LIKE :p)",
                "DELETE FROM track_lyrics_translations WHERE track_id IN "
                "(SELECT id FROM tracks WHERE spotify_id LIKE :p)",
                "DELETE FROM track_lyrics WHERE track_id IN "
                "(SELECT id FROM tracks WHERE spotify_id LIKE :p)",
                "DELETE FROM tracks WHERE spotify_id LIKE :p",
                "DELETE FROM albums WHERE spotify_id LIKE :p",
                "DELETE FROM artists WHERE spotify_id LIKE :p",
            ):
                c.execute(text(stmt), {"p": f"{PREFIX}%"})
            c.execute(text("DELETE FROM lyrics_discovery_scopes WHERE user_id IN "
                           "(SELECT id FROM users WHERE handle LIKE :p)"),
                      {"p": f"{HANDLE_PREFIX}%"})
            c.execute(text("DELETE FROM users WHERE handle LIKE :p"), {"p": f"{HANDLE_PREFIX}%"})

    # ── helpers ────────────────────────────────────────────────────────────────────────
    def _add_source(self, body=BODY_EN, status="matched"):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO track_lyrics (track_id, match_status, lyric_plain) "
                           "VALUES (:t, :s, :b) ON CONFLICT (track_id) DO UPDATE SET "
                           "match_status = EXCLUDED.match_status, "
                           "lyric_plain = EXCLUDED.lyric_plain, updated_at = now()"),
                      {"t": self.track, "s": status, "b": body})

    def _album_track(self):
        with self.engine.begin() as c:
            return dict(c.execute(text(
                "SELECT source_state, last_reason, work_id FROM lyrics_album_tracks "
                "WHERE job_id = :j AND track_id = :t"),
                {"j": self.job, "t": self.track}).mappings().one())

    def _work(self):
        with self.engine.begin() as c:
            row = c.execute(text(
                "SELECT id, status, attempts, source_fingerprint, segments, last_reason "
                "FROM lyrics_translation_work WHERE track_id = :t"),
                {"t": self.track}).mappings().one_or_none()
            return dict(row) if row else None

    def _published(self):
        with self.engine.begin() as c:
            row = c.execute(text(
                "SELECT status, origin, model, translator_version, source_fingerprint, "
                "       segments, normalizer_version, lang "
                "FROM track_lyrics_translations WHERE track_id = :t"),
                {"t": self.track}).mappings().one_or_none()
            return dict(row) if row else None

    def _expire_claim(self):
        with self.engine.begin() as c:
            c.execute(text("UPDATE lyrics_translation_work "
                           "SET lease_until = now() - INTERVAL '1 second' "
                           "WHERE track_id = :t"), {"t": self.track})

    def _claim_snapshot(self):
        with self.engine.begin() as c:
            return dict(c.execute(text(
                "SELECT status, attempts, claim_token, lease_until, updated_at "
                "FROM lyrics_translation_work WHERE track_id = :t"),
                {"t": self.track}).mappings().one())

    def _complete_manual_translation(self):
        with self.engine.begin() as c:
            c.execute(text(
                "INSERT INTO track_lyrics_translations "
                "(track_id, status, origin, segments, source_fingerprint) "
                "VALUES (:t, 'done', 'manual', CAST(:seg AS jsonb), :fp)"),
                {"t": self.track, "fp": self._read_path_fingerprint(),
                 "seg": json.dumps([{"i": 0, "text_ko": "수동 번역"}])})

    def _read_path_fingerprint(self):
        """What the backend read path would derive from the CURRENT source row — the value
        `attach_translation` compares against before it will show a translation."""
        from types import SimpleNamespace
        with self.engine.begin() as c:
            src = c.execute(text("SELECT match_status, lyric_plain, lyric_synced "
                                 "FROM track_lyrics WHERE track_id = :t"),
                            {"t": self.track}).mappings().one()
        out = poller.normalize_lyrics(SimpleNamespace(**dict(src), track_id=self.track))
        return poller.compute_source_fingerprint(out.normalizer_version, out.segments)

    # ── the chain ──────────────────────────────────────────────────────────────────────
    def test_waiting_demand_reaches_a_published_translation_with_no_second_request(self):
        """source waiting -> source acquired -> translated -> published, from firings alone.

        Nothing between the phases is a manual step: the same ``run_once`` that found
        nothing on firing 1 completes the whole chain on firing 2, once the worker's fetch
        has landed a source row.
        """
        # Firing 1 — the source does not exist yet. Demand waits; nothing is invented.
        first = run_once(self.bridge)
        self.assertEqual(first["link"]["linked"], 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self._album_track()["source_state"], "source_pending")
        self.assertIsNone(self._published())

        # The worker's targeted fetch lands a usable source.
        self._add_source()

        # Firing 2 — same entry point, no new request anywhere.
        second = run_once(self.bridge)

        self.assertEqual(second["link"]["linked"], 1)
        self.assertEqual(second["work"]["done"], 1)
        self.assertEqual(second["work"]["published"], 1)
        self.assertEqual(len(self.calls), 1, "exactly one model call for one track")

        self.assertEqual(self._album_track()["source_state"], "linked")
        work = self._work()
        self.assertEqual(work["status"], "done")

        pub = self._published()
        self.assertEqual(pub["status"], "done")
        self.assertEqual(pub["origin"], "poller")          # contract enum, unchanged
        self.assertEqual(pub["translator_version"], TRANSLATOR_VERSION)
        self.assertEqual(pub["lang"], "ko")

        # Parity with the read path: a mismatch here is exactly what makes the viewer
        # withhold a translation as "stale", so this is the assertion that proves the
        # published row is actually viewable.
        self.assertEqual(pub["source_fingerprint"], self._read_path_fingerprint())
        self.assertEqual(work["source_fingerprint"], pub["source_fingerprint"])

        # Gap segments survive as "" and every source line has a counterpart.
        stored = pub["segments"]
        stored = json.loads(stored) if isinstance(stored, str) else stored
        self.assertEqual([s["i"] for s in stored], list(range(len(stored))))
        self.assertTrue(any(s["text_ko"].startswith("KO ") for s in stored))

        # And the album is now complete on the demand side.
        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            progress = LyricsDemandStore(c).album_progress(self.user, self.job)
        self.assertEqual(progress["state"], "done")

    def test_third_firing_is_a_no_op(self):
        """Restart/redelivery safety: completed work is never re-translated."""
        self._add_source()
        run_once(self.bridge)
        again = run_once(self.bridge)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(again["work"]["done"], 0)
        self.assertEqual(again["link"]["linked"], 0)

    def test_repeated_link_returns_the_same_work_row(self):
        """Duplicate discovery must converge, not fan out into duplicate model calls."""
        self._add_source()
        self.bridge.link_ready_sources()
        first = self._work()["id"]
        self.bridge.link_ready_sources()
        self.assertEqual(self._work()["id"], first)

    # ── OQ5 classification ─────────────────────────────────────────────────────────────
    def test_korean_source_is_not_required_and_never_calls_the_model(self):
        """OQ5: already in the target language is an explicit not-required observation.

        The legacy path writes ``failed('korean_source')`` here, which would leave the album
        permanently short of completion — album progress counts only done + not_required.
        """
        self._add_source(body=BODY_KO)
        metrics = run_once(self.bridge)

        self.assertEqual(self.calls, [])
        self.assertEqual(metrics["link"]["korean"], 1)
        row = self._album_track()
        self.assertEqual(row["source_state"], "not_required")
        self.assertEqual(row["last_reason"], "korean_source")
        self.assertIsNone(self._work())

        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            progress = LyricsDemandStore(c).album_progress(self.user, self.job)
        self.assertEqual(progress["state"], "done")   # not_required counts as covered

    # ── the boundaries the legacy write-back cannot hold ───────────────────────────────
    def test_manual_edit_during_the_model_call_is_not_overwritten(self):
        """A hand edit that lands while Claude is running keeps the row — and the automatic
        result is retained rather than thrown away."""
        self._add_source()

        def edit_mid_call():
            with self.engine.begin() as c:
                c.execute(text(
                    "INSERT INTO track_lyrics_translations "
                    "(track_id, status, origin, segments, source_fingerprint, updated_at) "
                    "VALUES (:t, 'done', 'manual', CAST(:seg AS jsonb), :fp, now())"),
                    {"t": self.track, "fp": "f" * 64,
                     "seg": json.dumps([{"i": 0, "text_ko": "손으로 고친 번역"}])})
        self.during_call = edit_mid_call

        metrics = run_once(self.bridge)

        self.assertEqual(metrics["work"]["done"], 1)             # work completed
        self.assertEqual(metrics["work"]["publish_skipped"], 1)  # publication refused
        pub = self._published()
        self.assertEqual(pub["origin"], "manual")                # the edit survived intact
        self.assertEqual(self._work()["status"], "done")         # result retained, not lost

    def test_non_manual_row_change_during_the_model_call_also_blocks_publication(self):
        """Isolates the ``updated_at <= claimed_before`` guard from the ``origin`` guard.

        The manual-edit test above cannot do this: an edit that sets ``origin='manual'`` is
        caught by EITHER guard, so it passes even with the timestamp check deleted (verified
        by mutation). Here the concurrent writer stays non-manual — a re-request from the
        viewer's 번역 요청 button, which resets the row to 'requested' — so only the
        timestamp comparison can refuse the overwrite.
        """
        self._add_source()

        def rerequest_mid_call():
            with self.engine.begin() as c:
                c.execute(text(
                    "INSERT INTO track_lyrics_translations "
                    "(track_id, status, requested_at, updated_at) "
                    "VALUES (:t, 'requested', now(), now())"), {"t": self.track})
        self.during_call = rerequest_mid_call

        metrics = run_once(self.bridge)

        self.assertEqual(metrics["work"]["done"], 1)
        self.assertEqual(metrics["work"]["publish_skipped"], 1)
        pub = self._published()
        self.assertEqual(pub["status"], "requested")     # the concurrent write survived
        self.assertIsNone(pub["origin"])                 # and it was NOT a manual row
        self.assertEqual(self._work()["status"], "done")  # our result is still retained

    def test_completed_manual_translation_is_never_claimed(self):
        self._add_source()
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO track_lyrics_translations "
                           "(track_id, status, origin, segments, source_fingerprint) "
                           "VALUES (:t, 'done', 'manual', CAST(:seg AS jsonb), :fp)"),
                      {"t": self.track, "fp": "f" * 64,
                       "seg": json.dumps([{"i": 0, "text_ko": "수동"}])})

        metrics = run_once(self.bridge)
        self.assertEqual(self.calls, [])
        self.assertEqual(metrics["link"]["linked"], 0)
        self.assertEqual(metrics["work"]["done"], 0)
        self.assertEqual(self._published()["origin"], "manual")

        # It must also be recorded as COVERED, not left waiting. `claim_work` refuses this
        # track outright, so leaving it `source_pending` would mean the album could never
        # reach `done` however many times the sweep looks at it — the same defect that
        # `korean_source` exists to avoid.
        row = self._album_track()
        self.assertEqual(row["source_state"], "not_required")
        self.assertEqual(row["last_reason"], "manual_translation")

        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            progress = LyricsDemandStore(c).album_progress(self.user, self.job)
        self.assertEqual(progress["state"], "done")

    def test_work_keyed_to_a_superseded_source_never_publishes(self):
        """A queued work row whose source has since changed must not attach a translation of
        the old text — the fingerprint recheck happens before the model call, so no budget
        is spent either."""
        self._add_source()
        self.bridge.link_ready_sources()
        stale_fp = self._work()["source_fingerprint"]

        self._add_source(body=BODY_EN + "\nplaceholder delta")  # re-matched source
        self.assertNotEqual(self._read_path_fingerprint(), stale_fp)

        metrics = self.bridge.process_due_work()

        self.assertEqual(self.calls, [], "no model call spent on a superseded version")
        self.assertEqual(metrics["source_changed"], 1)
        self.assertIsNone(self._published())
        self.assertEqual(self._work()["status"], "retryable_error")
        self.assertEqual(self._work()["last_reason"], "source_changed")

        # And the ladder left it due later, not discarded.
        with self.engine.begin() as c:
            due = c.execute(text("SELECT next_attempt_at IS NOT NULL FROM "
                                 "lyrics_translation_work WHERE track_id = :t"),
                            {"t": self.track}).scalar()
        self.assertTrue(due)

        # The track must be RELEASED, not merely failed. `ensure_work` moved it to
        # 'linked' and nothing else moves it back, so without the release it is deadlocked:
        # claim, re-derive, mismatch, fail, forever, and the album can never complete.
        self.assertEqual(metrics["released"], 1)
        row = self._album_track()
        self.assertEqual(row["source_state"], "source_pending")
        self.assertEqual(row["last_reason"], "source_changed")
        self.assertIsNone(row["work_id"])

    def test_changed_source_is_relinked_and_translated_on_the_next_firing(self):
        """The recovery half of the test above: a released track must actually come back.

        This is the case a NORMALIZER_VERSION bump creates for every linked-not-yet-done row
        at once, so "it recovers on its own" has to be true rather than assumed.
        """
        self._add_source()
        self.bridge.link_ready_sources()
        old_work = self._work()["id"]

        self._add_source(body=BODY_EN + "\nplaceholder delta")
        self.bridge.process_due_work()          # detects, fails, releases

        metrics = run_once(self.bridge)          # next firing: relink at the new fingerprint
        self.assertEqual(metrics["link"]["linked"], 1)
        self.assertEqual(metrics["work"]["published"], 1)

        with self.engine.begin() as c:
            rows = c.execute(text(
                "SELECT id, status, source_fingerprint FROM lyrics_translation_work "
                "WHERE track_id = :t ORDER BY created_at"), {"t": self.track}).mappings().all()
        self.assertEqual(len(rows), 2, "a new work row at the new fingerprint")
        new = [r for r in rows if r["id"] != old_work][0]
        self.assertEqual(new["status"], "done")
        self.assertEqual(new["source_fingerprint"], self._read_path_fingerprint())
        self.assertEqual(self._published()["source_fingerprint"], self._read_path_fingerprint())

    def test_existing_translation_at_the_same_fingerprint_is_not_re_translated(self):
        """The legacy album_research sweep already translates at this exact fingerprint.

        Without this the demand path spends a second model call per track on any album that
        is both research-linked and member-demanded, against a shared per-song budget.
        """
        self._add_source()
        fp = self._read_path_fingerprint()
        with self.engine.begin() as c:
            c.execute(text(
                "INSERT INTO track_lyrics_translations "
                "(track_id, status, origin, translator_version, segments, source_fingerprint) "
                "VALUES (:t, 'done', 'poller', 'v2', CAST(:seg AS jsonb), :fp)"),
                {"t": self.track, "fp": fp,
                 "seg": json.dumps([{"i": 0, "text_ko": "기존 번역"}])})

        metrics = run_once(self.bridge)

        self.assertEqual(self.calls, [], "no second model call for an identical version")
        self.assertEqual(metrics["link"]["already_covered"], 1)
        row = self._album_track()
        self.assertEqual(row["source_state"], "not_required")
        self.assertEqual(row["last_reason"], "already_translated")

    def test_expired_claim_discards_the_late_result(self):
        """If the lease expired mid-call, another runner owns the row; our result must not
        be written on top of theirs."""
        self._add_source()
        self.bridge.link_ready_sources()

        def expire_mid_call():
            with self.engine.begin() as c:
                c.execute(text("UPDATE lyrics_translation_work "
                               "SET lease_until = now() - INTERVAL '1 hour' "
                               "WHERE track_id = :t"), {"t": self.track})
        self.during_call = expire_mid_call

        metrics = self.bridge.process_due_work()
        self.assertEqual(metrics["lost_claim"], 1)
        self.assertEqual(metrics["done"], 0)
        self.assertIsNone(self._published())

    def _assert_failed_engine_claim_recovers(self, error):
        self._add_source()

        def fail_during_call():
            raise error

        self.during_call = fail_during_call
        run_once(self.bridge)
        self.assertEqual(self._work()["status"], "running")
        self.assertIsNone(self._published())

        self._expire_claim()
        recovered = run_once(self.bridge)

        self.assertEqual(recovered["work"]["published"], 1)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self._work()["status"], "done")
        self.assertEqual(self._work()["attempts"], 2)
        self.assertEqual(self._published()["source_fingerprint"], self._read_path_fingerprint())

    def test_transient_failure_is_reclaimed_after_the_lease_expires(self):
        self._assert_failed_engine_claim_recovers(poller.TransientEngineError("CLI unavailable"))

    def test_cooldown_claim_is_reclaimed_after_the_lease_expires(self):
        self._assert_failed_engine_claim_recovers(poller.LLMSubscriptionCooldown(60))

    def test_active_lease_is_untouched_by_another_firing(self):
        self._add_source()
        self.bridge.link_ready_sources()
        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            token = LyricsDemandStore(c).claim_work(self._work()["id"])
        self.assertIsNotNone(token)
        before = self._claim_snapshot()

        metrics = run_once(self.bridge)

        self.assertEqual(self.calls, [])
        self.assertEqual(self._claim_snapshot(), before)
        self.assertEqual(metrics["work"]["lost_claim"], 0)
        self.assertIsNone(self._published())

    def test_source_changed_during_translation_is_relinked_on_the_next_firing(self):
        self._add_source()
        self.bridge.link_ready_sources()
        old_work = self._work()["id"]
        self.during_call = lambda: self._add_source(body=BODY_EN + "\nplaceholder delta")

        first = self.bridge.process_due_work()

        self.assertEqual(first["done"], 0)
        self.assertEqual(first["source_changed"], 1)
        self.assertEqual(first["released"], 1)
        self.assertEqual(self._work()["status"], "retryable_error")
        self.assertIsNone(self._work()["segments"])
        self.assertIsNone(self._published())
        self.assertEqual(self._album_track()["source_state"], "source_pending")
        self.assertIsNone(self._album_track()["work_id"])

        recovered = run_once(self.bridge)

        self.assertEqual(recovered["work"]["published"], 1)
        self.assertEqual(len(self.calls), 2)
        self.assertIn("placeholder delta", self.calls[-1])
        self.assertNotEqual(self._album_track()["work_id"], old_work)
        self.assertEqual(self._published()["source_fingerprint"], self._read_path_fingerprint())

    def test_source_unavailable_during_translation_releases_the_track_for_fetching(self):
        self._add_source()
        self.during_call = lambda: self._add_source(body="", status="matched")

        metrics = run_once(self.bridge)

        self.assertEqual(metrics["work"]["done"], 0)
        self.assertEqual(metrics["work"]["released"], 1)
        self.assertEqual(self._work()["status"], "retryable_error")
        self.assertEqual(self._work()["last_reason"], "source_unavailable")
        self.assertIsNone(self._published())
        self.assertEqual(self._album_track()["source_state"], "source_pending")
        self.assertEqual(self._album_track()["last_reason"], "source_unavailable")
        self.assertIsNone(self._album_track()["work_id"])

    def test_publication_failure_rolls_back_completion_and_recovers_after_lease_expiry(self):
        self._add_source()
        real_publish = self.bridge._publish

        def fail_after_publication(*args, **kwargs):
            # Execute the real write first: a failed transaction must undo both database
            # changes, including completion that preceded this publication.
            real_publish(*args, **kwargs)
            raise RuntimeError("publication transaction interrupted")

        with patch.object(self.bridge, "_publish", side_effect=fail_after_publication):
            with self.assertRaisesRegex(RuntimeError, "publication transaction interrupted"):
                run_once(self.bridge)

        self.assertEqual(self._work()["status"], "running")
        self.assertIsNone(self._work()["segments"])
        self.assertIsNone(self._published())

        self._expire_claim()
        recovered = run_once(self.bridge)

        self.assertEqual(recovered["work"]["published"], 1)
        self.assertEqual(self._work()["status"], "done")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self._published()["source_fingerprint"], self._read_path_fingerprint())

    def test_manual_translation_after_linking_completes_album_without_a_model_call(self):
        self._add_source()
        self.bridge.link_ready_sources()
        self.assertEqual(self._album_track()["source_state"], "linked")
        self._complete_manual_translation()

        run_once(self.bridge)

        self.assertEqual(self.calls, [])
        self.assertEqual(self._published()["origin"], "manual")
        self.assertEqual(self._album_track()["source_state"], "not_required")
        self.assertEqual(self._album_track()["last_reason"], "manual_translation")
        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            progress = LyricsDemandStore(c).album_progress(self.user, self.job)
        self.assertEqual(progress["state"], "done")

    def test_removed_demand_stops_the_bridge_but_keeps_the_completed_result(self):
        """Unsaving the album halts future automatic work; a finished translation stays."""
        self._add_source()
        run_once(self.bridge)
        self.assertEqual(self._published()["status"], "done")

        from myblog_shared_db.lyrics_demand import LyricsDemandStore
        with self.engine.begin() as c:
            LyricsDemandStore(c).remove_origin(
                self.user, "saved", origin_key="album:" + self.album_sid)

        after = run_once(self.bridge)
        self.assertEqual(after["work"]["done"], 0)
        self.assertEqual(self._work()["status"], "done")     # completed work is preserved
        self.assertEqual(self._published()["status"], "done")


if __name__ == "__main__":
    unittest.main()
