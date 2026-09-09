#!/usr/bin/env python3
"""FEAT-lyrics-listening-experience Step 3 — V57 album demand -> Claude translation.

The bridge between the durable demand V57 stores and the translation engine the existing
poller already runs. It reuses that poller's engine, frozen prompt, subscription guard,
normalizer and fingerprint verbatim (imported, not copied) and replaces exactly two things:
**which rows it works on**, and **how a result is written back**.

Why the legacy write-back cannot serve this
-------------------------------------------
``lyrics_translate_poller`` claims ``track_lyrics_translations`` rows and completes them by
``track_id`` alone. That is safe for a queue whose only producer is a human pressing a
button, and unsafe the moment demand is generated automatically: a model call takes minutes,
during which the source can be re-matched, the member can unsave the album, or the owner can
hand-edit the translation — and a ``WHERE track_id = ...`` write silently overwrites all
three. Step 2 therefore shipped the version-safe stores but deliberately left them
unpublished; this module is the writer that closes that gap, and every write it makes is
guarded by three things the legacy path has no notion of:

1. the **claim token + lease** (``complete_work``/``fail_work`` are no-ops for an expired or
   stolen claim, so a slow run cannot overwrite its own replacement),
2. the **source version** — ``ensure_work`` refuses a superseded ``source_revision``, and the
   fingerprint is re-verified after the model call, so a re-matched source produces a NEW
   work row instead of a wrong translation attached to the old one,
3. a **manual-edit check at publication time** — an edit that landed while the model was
   running keeps the row; the result is not lost, it stays durable in
   ``lyrics_translation_work``.

Division of labour with the worker
----------------------------------
The worker's ``lyrics_demand_source`` job fetches sources; this module links and translates
them. The split is not arbitrary: ``ensure_work`` is keyed by the source fingerprint, and
that fingerprint must equal what the read path re-derives — it comes from the backend's
``normalize_lyrics``/``compute_source_fingerprint``, which the worker Lambda cannot import
and must not re-implement. This process already imports them (parity by construction, same
as the legacy poller), so linking belongs here. The two consumers therefore partition
``source_pending`` by whether a usable source exists, and never both hold the same track.

Nothing here creates demand — the automatic producers are Steps 4/5.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable

log = logging.getLogger("lyrics-demand-translate")

# The V57 work-row identity for this engine + prompt. The fingerprint already covers the
# source text and the normalizer, so this only has to change when the *translator* does —
# a model swap or a prompt edit — at which point unchanged sources correctly become new work
# instead of silently inheriting an older engine's output.
TRANSLATOR_VERSION = "claude.sonnet/v2"
TARGET_LANG = "ko"

CLAIM_LEASE_S = 1200          # 20 min — matches the legacy poller's stale-claim window
LINK_BATCH_PER_RUN = 50       # pure DB + normalization, no model calls
WORK_BATCH_PER_RUN = 5        # model calls — mirrors the legacy poller's BATCH_PER_RUN

# OQ5 work-retry ladder (owner-approved 2026-09-09). Paces a failing translation without
# ever discarding it: `attempts` sets the rung, it is never a discard threshold, and the
# top rung is a ceiling that still yields a due date.
WORK_RETRY_BASE_S = 600.0     # 10 minutes
WORK_RETRY_CAP_S = 21_600.0   # 6 hours

# A source whose row says "usable" but which the normalizer rejects (a `matched` row whose
# LRC parses to nothing). Rare, and it belongs to neither consumer's normal path, so it gets
# an explicit rest rather than spinning through the link sweep every firing.
UNNORMALIZABLE_REST_S = 21_600.0  # 6 hours

# Live demand, or an explicit manual request. Mirrors `claim_work`'s own predicate so the
# selection never offers a row the store would refuse to claim.
_LIVE_DEMAND = """(
    NOT j.cancelled
    AND EXISTS (
        SELECT 1 FROM lyrics_album_demands d
        JOIN lyrics_discovery_scopes s ON s.id = d.scope_id AND s.active
        WHERE d.job_id = j.id
    )
)"""

# Tracks whose source is ready but not yet linked to a version-keyed work row. The
# `match_status`/body predicate is the same one `normalize_lyrics` treats as availability
# "ok", so this queue and the worker's fetch queue are exact complements.
LINK_CANDIDATES_SQL = f"""
SELECT lat.job_id, lat.track_id, lat.work_id, lat.source_revision,
       tl.match_status, tl.lyric_plain, tl.lyric_synced
FROM lyrics_album_tracks lat
JOIN lyrics_album_jobs j ON j.id = lat.job_id
JOIN track_lyrics tl     ON tl.track_id = lat.track_id
WHERE lat.source_state = 'source_pending'
  AND (lat.next_attempt_at IS NULL OR lat.next_attempt_at <= now())
  AND tl.match_status = 'matched'
  AND (btrim(coalesce(tl.lyric_synced, '')) <> '' OR btrim(coalesce(tl.lyric_plain, '')) <> '')
  AND {_LIVE_DEMAND}
  -- A completed manual translation is authoritative; never queue work that would only be
  -- refused at claim time.
  AND NOT EXISTS (
      SELECT 1 FROM track_lyrics_translations x
      WHERE x.track_id = lat.track_id AND x.status = 'done' AND x.origin = 'manual'
  )
ORDER BY lat.updated_at
LIMIT %s;
"""

# Due work for linked tracks. `attempts` carries the retry ladder's rung.
DUE_WORK_SQL = f"""
SELECT w.id AS work_id, w.track_id, w.source_fingerprint, w.attempts, w.lang
FROM lyrics_translation_work w
WHERE w.status IN ('ready', 'retryable_error')
  AND (w.next_attempt_at IS NULL OR w.next_attempt_at <= now())
  AND w.lang = %s
  AND (w.manual_requested OR EXISTS (
        SELECT 1 FROM lyrics_album_tracks lat
        JOIN lyrics_album_jobs j ON j.id = lat.job_id
        WHERE lat.work_id = w.id AND {_LIVE_DEMAND}
  ))
  AND NOT EXISTS (
      SELECT 1 FROM track_lyrics_translations x
      WHERE x.track_id = w.track_id AND x.status = 'done' AND x.origin = 'manual'
  )
ORDER BY w.updated_at
LIMIT %s;
"""

SOURCE_FOR_TRACK_SQL = """
SELECT tl.match_status, tl.lyric_plain, tl.lyric_synced, t.title,
       COALESCE((SELECT array_agg(ar.name ORDER BY ar.name)
                 FROM track_artists ta JOIN artists ar ON ar.id = ta.artist_id
                 WHERE ta.track_id = t.id), '{}') AS artists
FROM tracks t LEFT JOIN track_lyrics tl ON tl.track_id = t.id
WHERE t.id = %s;
"""

# Publication into the table the viewer reads. Three guards, in one statement so the check
# and the write cannot be separated by a concurrent edit:
#
#   * `origin IS DISTINCT FROM 'manual'` — a manual translation is never reset by automatic
#     discovery. (`claim_work` refuses these too; this is the belt to that suspenders,
#     because the row can become manual *during* the model call.)
#   * `updated_at <= claimed_before` — nothing touched the row while the model was running.
#     A re-request or a hand edit wins; the automatic result is simply not published.
#   * the caller only reaches this after `complete_work` returned True, i.e. the claim token
#     was still valid and the result is already durable in `lyrics_translation_work`.
#
# A skipped publication therefore loses NOTHING: the translation stays stored under its
# exact source version and is re-published the moment the conflicting edit is resolved.
#
# `origin` stays 'poller': the contract pins it to the enum ["poller","manual"], and full
# provenance lives in `lyrics_translation_work` where it does not need a contract change.
PUBLISH_SQL = """
INSERT INTO track_lyrics_translations
    (track_id, status, lang, segments, source_fingerprint, normalizer_version,
     origin, model, translator_version, error, requested_at, translated_at, updated_at,
     claimed_at)
VALUES (%s, 'done', %s, %s::jsonb, %s, %s, 'poller', %s, %s, NULL, now(), now(), now(), NULL)
ON CONFLICT (track_id) DO UPDATE SET
    status = 'done', lang = EXCLUDED.lang, segments = EXCLUDED.segments,
    source_fingerprint = EXCLUDED.source_fingerprint,
    normalizer_version = EXCLUDED.normalizer_version,
    origin = EXCLUDED.origin, model = EXCLUDED.model,
    translator_version = EXCLUDED.translator_version,
    error = NULL, translated_at = now(), updated_at = now(), claimed_at = NULL
WHERE track_lyrics_translations.origin IS DISTINCT FROM 'manual'
  AND track_lyrics_translations.updated_at <= %s
RETURNING track_id;
"""


def work_retry_at(attempts: int, now: datetime | None = None) -> datetime:
    """OQ5 ladder for a failed translation: 10m, 20m, 40m, ... capped at 6h.

    ``attempts`` paces the retry; it never ends it. The cap is a ceiling that still returns
    a due date, so a permanently failing track keeps its demand and keeps being retried
    rather than being dropped on a count.
    """
    now = now or datetime.now(timezone.utc)
    rung = max(0, int(attempts) - 1)
    gap = min(WORK_RETRY_CAP_S, WORK_RETRY_BASE_S * (2.0 ** min(rung, 20)))
    return now + timedelta(seconds=gap)


class DemandBridge:
    """Wires the V57 stores to the existing engine.

    Every collaborator is injected so this class carries no import-time dependency on the
    local backend/shared_db checkouts — the poller supplies them, and the tests supply the
    same real functions with a stub engine.
    """

    def __init__(
        self,
        *,
        connect: Callable[[], Any],              # psycopg connection factory
        sa_connect: Callable[[], Any],           # SQLAlchemy connection factory (store)
        store_cls: Any,                          # LyricsDemandStore
        stale_error: type[Exception],            # StaleDiscovery
        normalize_lyrics: Callable[[Any], Any],
        compute_source_fingerprint: Callable[[int, Any], str],
        normalizer_version: int,
        translate: Callable[[list[str]], list[str]],
        hangul_ratio: Callable[[str], float],
        hangul_dominant_ratio: float,
        model_name: str,
        ensure_subscription_available: Callable[[], None],
        transient_errors: tuple[type[Exception], ...],
        validation_errors: tuple[type[Exception], ...],
        cooldown_error: type[Exception],
    ) -> None:
        self._connect = connect
        self._sa_connect = sa_connect
        self._store_cls = store_cls
        self._stale = stale_error
        self._normalize = normalize_lyrics
        self._fingerprint = compute_source_fingerprint
        self._normalizer_version = normalizer_version
        self._translate = translate
        self._hangul_ratio = hangul_ratio
        self._hangul_dominant = hangul_dominant_ratio
        self._model = model_name
        self._ensure_subscription = ensure_subscription_available
        self._transient = transient_errors
        self._validation = validation_errors
        self._cooldown = cooldown_error

    # ── helpers ────────────────────────────────────────────────────────────────────────
    def _store_txn(self):
        """One short store transaction. The store never opens its own — the caller owns it,
        which is what keeps every V57 mutation to a handful of milliseconds."""
        return self._sa_connect()

    def _normalized(self, src: dict) -> Any:
        row = SimpleNamespace(
            match_status=src["match_status"], lyric_plain=src["lyric_plain"],
            lyric_synced=src["lyric_synced"], track_id=None,
        ) if src.get("match_status") is not None else None
        return self._normalize(row)

    # ── phase 1: link ready sources to version-keyed work ──────────────────────────────
    def link_ready_sources(self, limit: int = LINK_BATCH_PER_RUN) -> dict:
        """Turn every demanded track with a usable source into a version-keyed work row.

        Idempotent by construction: ``ensure_work``'s unique key is
        (track, fingerprint, lang, translator_version), so a re-run of an unchanged source
        returns the SAME work row rather than duplicating it, and a changed source creates a
        new one without touching the completed old one.
        """
        counts = {"linked": 0, "korean": 0, "unnormalizable": 0, "stale": 0}
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(LINK_CANDIDATES_SQL, (limit,))
                rows = cur.fetchall()
            conn.commit()  # release the read snapshot before any per-row work
        finally:
            conn.close()

        for row in rows:
            try:
                self._link_one(row, counts)
            except self._stale:
                # The source was re-observed while we were normalizing; the next firing
                # picks up whatever is now true.
                counts["stale"] += 1
            except Exception:  # noqa: BLE001 — one row must not sink the sweep
                log.exception("demand link failed for track %s", row["track_id"])
        if any(counts.values()):
            log.info("demand link sweep: %s", counts)
        return counts

    def _link_one(self, row: dict, counts: dict) -> None:
        out = self._normalized(row)
        if out.availability != "ok":
            # The SQL said usable but the normalizer disagrees — rest it rather than
            # re-normalizing the same row every 60 seconds.
            with self._store_txn() as sa:
                self._store_cls(sa).set_source_state(
                    row["job_id"], row["track_id"], "source_pending", "source_unavailable",
                    next_attempt_at=datetime.now(timezone.utc)
                    + timedelta(seconds=UNNORMALIZABLE_REST_S),
                    expected_work_id=row["work_id"],
                    expected_source_revision=row["source_revision"],
                )
            counts["unnormalizable"] += 1
            return

        non_gap = [s for s in out.segments if s.text != ""]
        if self._hangul_ratio(" ".join(s.text for s in non_gap)) >= self._hangul_dominant:
            # OQ5: already in the target language — an explicit not-required observation,
            # not a failure, and no model call is ever spent on it. The legacy path writes
            # a `failed('korean_source')` row here; that would leave the album permanently
            # short of completion, since album progress counts only done + not_required.
            with self._store_txn() as sa:
                self._store_cls(sa).set_source_state(
                    row["job_id"], row["track_id"], "not_required", "korean_source",
                    expected_work_id=row["work_id"],
                    expected_source_revision=row["source_revision"],
                )
            counts["korean"] += 1
            return

        fingerprint = self._fingerprint(out.normalizer_version, out.segments)
        with self._store_txn() as sa:
            self._store_cls(sa).ensure_work(
                row["job_id"], row["track_id"], fingerprint, TARGET_LANG, TRANSLATOR_VERSION,
                expected_work_id=row["work_id"],
                expected_source_revision=row["source_revision"],
            )
        counts["linked"] += 1

    # ── phase 2: claim, translate, complete, publish ───────────────────────────────────
    def process_due_work(self, limit: int = WORK_BATCH_PER_RUN) -> dict:
        """Claim and translate up to ``limit`` due work rows. Raises the cooldown error
        upward so one firing stops claiming instead of burning the subscription budget."""
        counts = {"done": 0, "published": 0, "publish_skipped": 0,
                  "failed": 0, "transient": 0, "lost_claim": 0, "source_changed": 0}
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(DUE_WORK_SQL, (TARGET_LANG, limit))
                rows = cur.fetchall()
            conn.commit()
        finally:
            conn.close()

        for row in rows:
            self._ensure_subscription()   # wait/refuse BEFORE a row receives a claim
            if not self._process_one_work(row, counts):
                break
        if any(counts.values()):
            log.info("demand work pass: %s", counts)
        return counts

    def _process_one_work(self, row: dict, counts: dict) -> bool:
        """One work row end to end. Returns False to stop the firing."""
        work_id, track_id = row["work_id"], row["track_id"]

        with self._store_txn() as sa:
            token = self._store_cls(sa).claim_work(work_id, lease_seconds=CLAIM_LEASE_S)
        if token is None:
            # Another runner holds it, or the demand went away between selection and claim.
            counts["lost_claim"] += 1
            return True

        # Materialize the source and the publication baseline, then CLOSE the connection.
        # Nothing below this line may hold a transaction — the model call takes minutes
        # (reference-db-session-across-long-external-loop).
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(SOURCE_FOR_TRACK_SQL, (track_id,))
                src = cur.fetchone()
                cur.execute("SELECT now() AS now")
                claimed_before = cur.fetchone()["now"]
            conn.commit()
        finally:
            conn.close()

        if src is None:
            self._fail(work_id, token, row, "track_vanished", counts)
            return True

        out = self._normalized(src)
        if out.availability != "ok":
            self._fail(work_id, token, row, "source_unavailable", counts)
            return True

        # The source must still be the exact version this work row is keyed to. If it moved
        # while the row sat in the queue, translating it would attach the new text's
        # translation to the old fingerprint — the link sweep will mint a new work row.
        fingerprint = self._fingerprint(out.normalizer_version, out.segments)
        if fingerprint != row["source_fingerprint"]:
            counts["source_changed"] += 1
            self._fail(work_id, token, row, "source_changed", counts, count_failed=False)
            return True

        non_gap = [s for s in out.segments if s.text != ""]
        log.info("demand claim %s — %s (%d lines)", track_id, src["title"], len(non_gap))
        try:
            texts_ko = self._translate([s.text for s in non_gap])
        except self._cooldown:
            # Claim intentionally kept: the lease is the retry gate, exactly as the legacy
            # poller treats a cooldown. Stop this firing.
            log.info("subscription cooldown on %s — stopping this firing", track_id)
            return False
        except self._transient as e:
            # Not a translation verdict. Leaving the claim in place lets the lease expire
            # and the row be reclaimed, without spending a retry rung on a CLI hiccup.
            counts["transient"] += 1
            log.warning("transient engine failure on %s — claim kept: %s", track_id, e)
            return True
        except self._validation as e:
            self._fail(work_id, token, row, f"engine_validation: {e}", counts)
            return True

        ko_by_i = {s.i: t for s, t in zip(non_gap, texts_ko)}
        segments = [{"i": s.i, "text_ko": ko_by_i.get(s.i, "")} for s in out.segments]

        with self._store_txn() as sa:
            completed = self._store_cls(sa).complete_work(work_id, token, segments)
        if not completed:
            # The lease expired mid-call and someone else owns the row now. Discarding our
            # result is correct: theirs is the one with a live claim.
            counts["lost_claim"] += 1
            log.warning("claim lost during translation of %s — result discarded", track_id)
            return True
        counts["done"] += 1

        self._publish(track_id, segments, fingerprint, out.normalizer_version,
                      claimed_before, counts)
        return True

    def _publish(self, track_id, segments, fingerprint, normalizer_version,
                 claimed_before, counts) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(PUBLISH_SQL, (
                    track_id, TARGET_LANG,
                    json.dumps(segments, ensure_ascii=False), fingerprint,
                    normalizer_version, self._model, TRANSLATOR_VERSION,
                    claimed_before,
                ))
                published = cur.fetchone()
            conn.commit()
        finally:
            conn.close()
        if published is None:
            counts["publish_skipped"] += 1
            log.info(
                "publication skipped for %s — the viewer row changed during the model call; "
                "the result is retained in lyrics_translation_work", track_id,
            )
        else:
            counts["published"] += 1

    def _fail(self, work_id, token, row, reason, counts, count_failed: bool = True) -> None:
        with self._store_txn() as sa:
            self._store_cls(sa).fail_work(
                work_id, token, reason, work_retry_at(row.get("attempts") or 1)
            )
        if count_failed:
            counts["failed"] += 1
        log.warning("demand work %s failed: %s", work_id, reason)


def run_once(bridge: DemandBridge, *, link_limit: int = LINK_BATCH_PER_RUN,
             work_limit: int = WORK_BATCH_PER_RUN) -> dict:
    """One firing: link whatever became ready, then translate whatever is due.

    Link-then-translate in the same firing is what makes the chain automatic — a source that
    arrived since the last run is translated on this one, with no second manual request.
    """
    link = bridge.link_ready_sources(link_limit)
    work = bridge.process_due_work(work_limit)
    return {"link": link, "work": work}


__all__ = [
    "DemandBridge", "run_once", "work_retry_at",
    "TRANSLATOR_VERSION", "TARGET_LANG",
    "LINK_BATCH_PER_RUN", "WORK_BATCH_PER_RUN",
]
