-- =============================================================================
-- Canonical Database Schema
-- Source of truth: docs/contracts/schema.sql (myblog-workspace repo)
-- Mirror: myblog_shared_db/tests/canonical_schema.sql — kept BYTE-IDENTICAL to
--   the workspace copy since the 2026-07-11 reconciliation (CHORE-canonical-
--   schema-sync); edit both in the same change.
--
-- Change policy:
--   1. Update THIS file first (both copies).
--   2. Write a migration script for the running DB (never DROP/TRUNCATE in prod).
--   3. Update the affected service's ORM models and local schema file.
--   4. Deploy consumer services before or simultaneously with producer services.
--
-- Service-local schema files (myblog_music/db/schema.sql, etc.) are
-- DERIVED from this file and kept for local dev convenience only.
--
-- This file shows clean canonical DDL through V47 (V47 authored + prod-applied
--   2026-07-15 — FEAT-personal-release-tracking Step 1; V46 authored +
--   prod-applied 2026-07-12 — FEAT-multi-user-accounts Phase 3c-a; V45 authored
--   + prod-applied 2026-07-12 — FEAT-multi-user-accounts Phase 3b-b; V44
--   authored + prod-applied 2026-07-12 — FEAT-release-calendar Track B Step 3);
--   V1–V43 were reconciled against a full
--   prod introspection 2026-07-11 (CHORE-canonical-schema-sync): every table,
--   column type, constraint and index below was verified against Neon prod
--   pg_catalog on that date. Per-version history lives in
--   myblog_shared_db/migrations/ (the authoritative version-ordered set) and in
--   the footer note.
--
-- NB (V13 rename, STAB-5) — V13 renamed `categories`→`sections` and
--   `posts.category_id`→`section_id` IN-PLACE (`ALTER TABLE ... RENAME`).
--   Postgres carries constraints/indexes/FK across a rename by OID, so prod's
--   PHYSICAL names still read the pre-V13 `categor*` form (prod-verified
--   2026-07-11):
--     • index   `idx_posts_category_id`        (now on `posts(section_id)`)
--     • uniques `categories_pkey/_name_key/_slug_key`  (now on `sections`)
--     • FK      `posts_category_id_fkey`        (now `section_id` → `sections(id)`)
--   The DDL below uses the clean `section_*` names; a fresh bootstrap therefore
--   yields `section_*`-named objects rather than prod's legacy names — cosmetic
--   only (object shape is identical). Do NOT reintroduce a `categories` table /
--   `category_id` column.
--
-- NB (legacy timestamp columns) — the ORIGINAL bootstrap tables predate the
--   TIMESTAMPTZ convention: in prod, the timestamp columns of posts
--   (last_updated_at), sections, artists, albums, tracks (created_at),
--   op_logs (occurred_at), outbox_events (created_at, processed_at),
--   publishing_runs (triggered_at, finished_at), post_comments (created_at),
--   post_likes (created_at) and post_metrics (updated_at) are
--   `timestamp WITHOUT time zone` (prod-verified 2026-07-11). Every V6+ table
--   uses TIMESTAMPTZ. The DDL below keeps the clean TIMESTAMPTZ form (services
--   treat all stored instants as UTC either way); do not "fix" prod — an
--   ALTER would rewrite large tables for zero behavior change.
-- =============================================================================

-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- V12: trigram search indexes (FEAT-music-search-recall)

-- =============================================================================
-- Enums
-- =============================================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'post_status') THEN
    CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_bucket_item_status') THEN
    CREATE TYPE review_bucket_item_status AS ENUM ('candidate', 'drafting', 'published');  -- V6
  END IF;
END$$;

-- V15 (FEAT-spotify-library-sync) — provenance + sync state for spotify_library_albums.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spotify_library_source') THEN
    CREATE TYPE spotify_library_source AS ENUM ('myblog_added', 'preexisting');
  END IF;
END $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'spotify_library_state') THEN
    CREATE TYPE spotify_library_state AS ENUM ('pending', 'synced', 'failed', 'needs_attention');
  END IF;
END $$;

-- =============================================================================
-- Sections & Tags
-- =============================================================================
-- `sections` (V13, STAB-5) — curated public post taxonomy, one section per post
-- (single FK). Seeded by V13: Reviews / Best New Music / Features / Tracks. No
-- get-or-create, no public create API. Renamed in place from `categories` (V12);
-- prod physical constraint names are still categories_pkey/_name_key/_slug_key
-- (see header NB).
CREATE TABLE IF NOT EXISTS sections (
  id         BIGSERIAL    PRIMARY KEY,
  name       TEXT         NOT NULL UNIQUE,
  slug       TEXT         NOT NULL UNIQUE,
  created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tags (
  id   BIGSERIAL PRIMARY KEY,
  name TEXT      NOT NULL UNIQUE,
  slug TEXT      NOT NULL UNIQUE
);

-- =============================================================================
-- Posts
-- =============================================================================
CREATE TABLE IF NOT EXISTS posts (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT         NOT NULL UNIQUE,
  title           TEXT         NOT NULL,
  description     TEXT         NOT NULL DEFAULT '',
  body_mdx        TEXT,                              -- NULL allowed (rating-only posts)
  body_text       TEXT,
  posted_date     DATE         NOT NULL,
  last_updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
  status          post_status  NOT NULL DEFAULT 'published',
  section_id      BIGINT       REFERENCES sections(id) ON DELETE SET NULL,  -- V13 rename (prod FK still named posts_category_id_fkey)
  search_index    BOOLEAN      NOT NULL DEFAULT TRUE,
  extra           JSONB        NOT NULL DEFAULT '{}'::jsonb,

  -- Music review fields
  -- V5 widened rating (3,1)→(3,2); the bound is rating_scale, not a literal.
  -- Prod physical CHECK name: chk_rating_range.
  album_cover_url TEXT,
  rating          NUMERIC(3,2) CONSTRAINT chk_rating_range
                               CHECK (rating IS NULL OR (rating >= 0 AND rating <= rating_scale)),
  rating_scale    SMALLINT     NOT NULL DEFAULT 5 CHECK (rating_scale >= 1 AND rating_scale <= 10)
);

CREATE INDEX IF NOT EXISTS idx_posts_posted_date  ON posts(posted_date);
CREATE INDEX IF NOT EXISTS idx_posts_section_id   ON posts(section_id);  -- prod physical name still idx_posts_category_id (OID-carried across V13 rename)
CREATE INDEX IF NOT EXISTS idx_posts_status       ON posts(status);
-- Public-list hot path; prod-verified 2026-07-11 (was previously missing from this file).
CREATE INDEX IF NOT EXISTS idx_posts_search_index ON posts(search_index) WHERE search_index = true;
-- NB: no separate idx_posts_slug — posts_slug_key (the UNIQUE constraint's index)
-- serves slug lookups; prod has no such extra index (verified 2026-07-11).

-- =============================================================================
-- Post Tags (M:N)
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_tags (
  post_id UUID   NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  tag_id  BIGINT NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
  PRIMARY KEY (post_id, tag_id)
);

-- =============================================================================
-- Metrics / Comments / Likes
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_metrics (
  post_id        UUID    PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  likes          INTEGER NOT NULL DEFAULT 0,
  comments_count INTEGER NOT NULL DEFAULT 0,
  views          INTEGER NOT NULL DEFAULT 0,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post_comments (
  id           BIGSERIAL   PRIMARY KEY,
  post_id      UUID        NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  author_name  TEXT,
  author_email TEXT,
  content      TEXT        NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_post_comments_post_id    ON post_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_post_comments_created_at ON post_comments(created_at);

CREATE TABLE IF NOT EXISTS post_likes (
  post_id    UUID        NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id    TEXT        NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (post_id, user_id)
);

-- =============================================================================
-- Music Catalog — Artists
-- =============================================================================
CREATE TABLE IF NOT EXISTS artists (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT        NOT NULL,
  spotify_id      TEXT        NOT NULL UNIQUE,
  musicbrainz_id  TEXT,                                    -- nullable; UNIQUE only when present AND not the 'not_found' sentinel (see partial index below)
  genres          JSONB       NOT NULL DEFAULT '[]'::jsonb,
  aliases         JSONB       NOT NULL DEFAULT '[]'::jsonb, -- Korean/alternate name aliases (MusicBrainz-generated; PR-13)
  photo_url       TEXT,
  popularity      INTEGER,
  followers       BIGINT,
  spotify_url     TEXT,
  views           INTEGER     NOT NULL DEFAULT 0,
  ext_refs        JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_artists_views_nonneg CHECK (views >= 0)
);

-- Partial UNIQUE on musicbrainz_id: NULL and the 'not_found' sentinel are
-- excluded so worker alias_fill can batch-mark lookup failures without
-- violating UNIQUE (BUG-13). Migration: V3__partial_unique_excl_not_found.sql.
-- Prod predicate verified 2026-07-11: (musicbrainz_id IS NOT NULL AND
-- musicbrainz_id <> 'not_found').
CREATE UNIQUE INDEX IF NOT EXISTS idx_artists_musicbrainz_id
  ON artists(musicbrainz_id)
  WHERE musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found';
CREATE INDEX IF NOT EXISTS idx_artists_popularity_followers_views
  ON artists(popularity DESC, followers DESC, views DESC);
CREATE INDEX IF NOT EXISTS idx_artists_name_trgm ON artists USING gin (name gin_trgm_ops);  -- V12
-- NB: no separate idx_artists_spotify_id — artists_spotify_id_key (the UNIQUE
-- constraint's index) serves lookups; prod has no such extra index (verified 2026-07-11).

-- =============================================================================
-- Music Catalog — Albums
-- =============================================================================
CREATE TABLE IF NOT EXISTS albums (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  title        TEXT        NOT NULL,
  release_date DATE,
  cover_url    TEXT,
  album_type   TEXT,
  spotify_id   TEXT        NOT NULL UNIQUE,
  total_tracks INTEGER,
  label        TEXT,
  popularity   INTEGER,
  views        INTEGER     NOT NULL DEFAULT 0,
  best_new     BOOLEAN     NOT NULL DEFAULT FALSE,
  ext_refs     JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_albums_views_nonneg CHECK (views >= 0)
);

CREATE INDEX IF NOT EXISTS idx_albums_popularity_views
  ON albums(popularity DESC, views DESC);
CREATE INDEX IF NOT EXISTS idx_albums_best_new
  ON albums(best_new) WHERE best_new = true;
CREATE INDEX IF NOT EXISTS idx_albums_title_trgm ON albums USING gin (title gin_trgm_ops);  -- V12
-- NB: no separate idx_albums_spotify_id — albums_spotify_id_key serves lookups
-- (prod-verified 2026-07-11).

-- =============================================================================
-- Music Catalog — Album ↔ Artist (M:N)
-- =============================================================================
CREATE TABLE IF NOT EXISTS album_artists (
  album_id  UUID REFERENCES albums(id)  ON DELETE CASCADE,
  artist_id UUID REFERENCES artists(id) ON DELETE CASCADE,
  role      TEXT,
  PRIMARY KEY (album_id, artist_id)
);

-- =============================================================================
-- Music Catalog — Tracks
-- =============================================================================
CREATE TABLE IF NOT EXISTS tracks (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id     UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  title        TEXT        NOT NULL,
  track_no     INTEGER,
  duration_sec INTEGER,
  spotify_id   TEXT        NOT NULL UNIQUE,
  views        INTEGER     NOT NULL DEFAULT 0,
  ext_refs     JSONB       NOT NULL DEFAULT '{}'::jsonb,
  isrc         TEXT,       -- V34: ISRC identity/version anchor — server-side matching evidence only (aliases/musicbrainz_id precedent, never public); no UNIQUE (optional, source gaps)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_tracks_duration_nonneg CHECK (duration_sec IS NULL OR duration_sec >= 0),
  CONSTRAINT chk_tracks_trackno_pos     CHECK (track_no     IS NULL OR track_no     > 0),
  CONSTRAINT chk_tracks_views_nonneg    CHECK (views >= 0)
);

CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_track_no ON tracks(track_no);
CREATE INDEX IF NOT EXISTS idx_tracks_title_trgm ON tracks USING gin (title gin_trgm_ops);  -- V12
-- NB: no separate idx_tracks_spotify_id — tracks_spotify_id_key serves lookups.
-- Prod ALSO carries a redundant second UNIQUE constraint uq_tracks_spotify_id on
-- the same column (verified 2026-07-11; harmless duplicate from an early apply —
-- dropping it would need its own approved migration; intentionally not modeled here).

-- =============================================================================
-- Music Catalog — Track ↔ Artist (M:N)
-- =============================================================================
CREATE TABLE IF NOT EXISTS track_artists (
  track_id  UUID REFERENCES tracks(id)  ON DELETE CASCADE,
  artist_id UUID REFERENCES artists(id) ON DELETE CASCADE,
  role      TEXT,
  PRIMARY KEY (track_id, artist_id)
);

-- =============================================================================
-- Post ↔ Album (M:N) — with per-album "classic" flag
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_albums (
  post_id    UUID    NOT NULL REFERENCES posts(id)  ON DELETE CASCADE,
  album_id   UUID    NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  is_classic BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (post_id, album_id)
);
CREATE INDEX IF NOT EXISTS idx_post_albums_album_id ON post_albums(album_id);  -- prod-verified 2026-07-11 (previously unlisted)

-- =============================================================================
-- Post ↔ Artist (M:N)
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_artists (
  post_id   UUID NOT NULL REFERENCES posts(id)   ON DELETE CASCADE,
  artist_id UUID NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, artist_id)
);
CREATE INDEX IF NOT EXISTS idx_post_artists_artist_id ON post_artists(artist_id);  -- prod-verified 2026-07-11 (previously unlisted)

-- =============================================================================
-- Post Recommended Tracks
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_recommended_tracks (
  post_id  UUID     NOT NULL,
  album_id UUID     NOT NULL,
  track_id UUID     NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  position SMALLINT,
  note     TEXT,
  PRIMARY KEY (post_id, track_id),  -- V37 (WS-B.2): per-post uniqueness
  FOREIGN KEY (post_id, album_id) REFERENCES post_albums(post_id, album_id) ON DELETE CASCADE
);
-- track_id is not the leading PK column; the tracks.id ON DELETE CASCADE lookup needs this (V37).
CREATE INDEX IF NOT EXISTS idx_post_recommended_tracks_track_id ON post_recommended_tracks(track_id);

-- =============================================================================
-- Outbox & Publishing
-- =============================================================================
CREATE TABLE IF NOT EXISTS outbox_events (
  id           BIGSERIAL   PRIMARY KEY,
  type         TEXT        NOT NULL,
  payload      JSONB       NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,
  retry_count  INTEGER     NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_outbox_processed_at  ON outbox_events(processed_at);
CREATE INDEX IF NOT EXISTS idx_outbox_unprocessed   ON outbox_events(processed_at) WHERE processed_at IS NULL;

CREATE TABLE IF NOT EXISTS publishing_runs (
  id           BIGSERIAL   PRIMARY KEY,
  post_id      UUID        NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  commit_sha   TEXT,
  status       TEXT        NOT NULL DEFAULT 'queued',   -- queued|running|succeeded|failed
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_publishing_runs_post_id      ON publishing_runs(post_id);
CREATE INDEX IF NOT EXISTS idx_publishing_runs_triggered_at ON publishing_runs(triggered_at);

-- =============================================================================
-- Operations Log
-- =============================================================================
CREATE TABLE IF NOT EXISTS op_logs (
  id          BIGSERIAL   PRIMARY KEY,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  name        TEXT        NOT NULL,
  status_code INTEGER,
  note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_op_logs_occurred_at ON op_logs(occurred_at);

-- =============================================================================
-- Users — member identity keyed on Cognito sub (V36; FEAT-multi-user-accounts Phase 0)
-- Rows are lazy-created by the backend on a member's first authed API call.
-- email NULLABLE (Kakao consent optional) and NOT unique (no account linking).
-- display_name/avatar_url from IdP claims only (no uploads); avatar NULL = initials.
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
  id           UUID        PRIMARY KEY,               -- Cognito sub (externally minted — no default)
  email        TEXT,                                  -- NULL for consent-declined Kakao members
  handle       TEXT        NOT NULL,                  -- lowercase; public profile URL component (/members/[handle])
  display_name TEXT        NOT NULL,                  -- IdP nickname default, user-editable
  avatar_url   TEXT,                                  -- IdP profile-picture URL only (no uploads)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_users_handle UNIQUE (handle),
  CONSTRAINT ck_users_handle_format
    CHECK (handle ~ '^[a-z0-9][a-z0-9_-]{1,28}[a-z0-9]$')
);

-- =============================================================================
-- Review Buckets — private review-writing kanban (V6; parent_id V11)
-- (Backfilled 2026-06-05 from prod introspection — STAB-4. NOT public taxonomy.)
-- Per-user since FEAT-multi-user Phase 2: V40 added user_id (nullable + owner
-- backfill) and re-scoped the two global singleton partial-uniques to per-user;
-- V42 flipped user_id NOT NULL after the prod soak.
-- =============================================================================
CREATE TABLE IF NOT EXISTS review_buckets (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- V40 nullable+backfill → V42 NOT NULL
  name       TEXT        NOT NULL,
  position   INTEGER     NOT NULL,
  color      TEXT,
  is_done    BOOLEAN     NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  parent_id  UUID        REFERENCES review_buckets(id) ON DELETE CASCADE,  -- V11
  kind       TEXT        NOT NULL DEFAULT 'review',                        -- V15: marks the single spotify_library bucket; V31: 'to_listen' system bucket (들을 것) — free TEXT, same idiom as 'spotify_library'
  research_mode TEXT     NOT NULL DEFAULT 'off'
                         CHECK (research_mode IN ('off', 'all', 'selected')),  -- V16: auto-research scope (FEAT-album-research-notes)
  is_public  BOOLEAN     NOT NULL DEFAULT false,                           -- V18: public bucket viewer opt-in (FEAT-public-bucket-multiuser)
  type       TEXT        NOT NULL DEFAULT 'general'                        -- V32: General vs Artist Buckit (FEAT-my-buckit-artist); orthogonal to kind; immutable after create (app-layer)
             CONSTRAINT ck_review_buckets_type CHECK (type IN ('general', 'artist'))
);
CREATE INDEX IF NOT EXISTS idx_review_buckets_parent_id ON review_buckets(parent_id);
-- At most one "작성 완료" (done) bucket PER USER (V40 re-scope; was a global (true) singleton).
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_done
  ON review_buckets (user_id) WHERE is_done;
-- At most one kind='spotify_library' mirror bucket PER USER (V15; V40 re-scope).
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_spotify_library
  ON review_buckets (user_id) WHERE kind = 'spotify_library';

-- V28/V30 (FEAT-pocket-buckit) generalized album-only membership to a TYPED relationship:
--   V28 added item_type (DEFAULT 'album') + nullable typed FKs track_id/review_target_id;
--   V30 dropped album_id NOT NULL, replaced the table-wide UNIQUE(bucket_id, album_id) with
--   per-kind PARTIAL uniques (album/track/review reject dupes; playback/snapshot allow), and
--   added ck_review_bucket_items_album_id_present so album-kind rows still must carry album_id.
-- review_target_id (CASCADE) is DISTINCT from post_id (SET NULL): post_id = "the review this
--   ALBUM produced"; review_target_id = "this item IS a review member" (item_type='review').
-- Items are NOT user_id-scoped (V40 decision): ownership is transitive via
--   bucket_id → review_buckets.user_id, and the per-kind partial-uniques key on
--   bucket_id, so they became per-user for free when buckets gained user_id.
CREATE TABLE IF NOT EXISTS review_bucket_items (
  id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket_id  UUID         NOT NULL REFERENCES review_buckets(id) ON DELETE CASCADE,
  album_id   UUID         REFERENCES albums(id) ON DELETE CASCADE,  -- V30: NOT NULL dropped (non-album kinds omit it)
  item_type  TEXT         NOT NULL DEFAULT 'album'                  -- V28: typed membership discriminator; V32 widened to admit 'artist'
             CONSTRAINT ck_review_bucket_items_item_type
             CHECK (item_type IN ('album', 'track', 'review', 'playback', 'snapshot', 'artist')),
  track_id   UUID         REFERENCES tracks(id) ON DELETE CASCADE,  -- V28: target for item_type='track'
  review_target_id UUID   REFERENCES posts(id) ON DELETE CASCADE,   -- V28: target for item_type='review' (DISTINCT from post_id)
  artist_id  UUID         REFERENCES artists(id) ON DELETE CASCADE, -- V32: target for item_type='artist' (Artist Buckit member)
  position   INTEGER      NOT NULL,
  note       TEXT,
  status     review_bucket_item_status NOT NULL DEFAULT 'candidate',
  post_id    UUID         REFERENCES posts(id) ON DELETE SET NULL,
  rec_reason TEXT,
  research_selected BOOLEAN NOT NULL DEFAULT FALSE,  -- V16: per-item checkbox under research_mode='selected'
  prep_tonight BOOLEAN     NOT NULL DEFAULT FALSE,   -- V22: "오늘 밤 키우기" gate for the nightly memo→skeleton job (FEAT-editor-buckit)
  added_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
  -- V30: album-kind rows must carry album_id (a NULL-album 'album' row would escape the
  -- partial unique below, since NULLs are distinct in a unique index).
  CONSTRAINT ck_review_bucket_items_album_id_present
    CHECK (item_type <> 'album' OR album_id IS NOT NULL),
  -- V32: artist-kind rows must carry artist_id (mirrors the V30 album guard), and artist_id
  -- may ONLY sit on an 'artist' row (inverse guard) — together with uq_review_bucket_items_artist
  -- the no-duplicate-artist invariant is airtight at the schema level.
  CONSTRAINT ck_review_bucket_items_artist_id_present
    CHECK (item_type <> 'artist' OR artist_id IS NOT NULL),
  CONSTRAINT ck_review_bucket_items_artist_id_only_on_artist
    CHECK (item_type = 'artist' OR artist_id IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_album_id  ON review_bucket_items(album_id);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_bucket_id ON review_bucket_items(bucket_id);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_post_id   ON review_bucket_items(post_id);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_item_type ON review_bucket_items(item_type);  -- V28
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_track_id  ON review_bucket_items(track_id);   -- V28
-- V30: per-kind PARTIAL uniques replace the old table-wide UNIQUE(bucket_id, album_id).
-- album/track/review reject duplicate membership; playback (queue) + snapshot (append-only)
-- get NO unique → duplicates allowed (D8).
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_bucket_items_album
  ON review_bucket_items (bucket_id, album_id) WHERE item_type = 'album';
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_bucket_items_track
  ON review_bucket_items (bucket_id, track_id) WHERE item_type = 'track';
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_bucket_items_review
  ON review_bucket_items (bucket_id, review_target_id) WHERE item_type = 'review';
-- V32: one artist per bucket (same kind-scoped partial-unique idiom as the V30 set).
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_bucket_items_artist
  ON review_bucket_items (bucket_id, artist_id) WHERE item_type = 'artist';

-- =============================================================================
-- Bucket Item Snapshots — frozen capture for snapshot-kind members (V29; OQ7)
-- A snapshot member (period / signal / trend / aggregate) preserves the contemporaneous
-- period + filters + values in a SIDE table keyed to the membership row (mirrors the V15
-- spotify_library_albums side-table idiom), so the album-membership hot path stays narrow
-- and the snapshot can OUTLIVE volatile source rows. APPEND-ONLY: a "refresh with current
-- data" is a NEW row (refreshed_from self-FK lineage), never an UPDATE.
-- =============================================================================
CREATE TABLE IF NOT EXISTS bucket_item_snapshots (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id          UUID        NOT NULL REFERENCES review_bucket_items(id) ON DELETE CASCADE,
  kind             TEXT        NOT NULL,                       -- snapshot discriminator (period|signal|trend|aggregate)
  as_of            TIMESTAMPTZ NOT NULL,                       -- the labelled "as of" instant (shown to the user)
  captured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),         -- when this row was written
  metric           TEXT,
  range_from       TIMESTAMPTZ,                                -- 'from' is reserved → range_from
  range_to         TIMESTAMPTZ,
  unit             TEXT,
  total            NUMERIC,
  unresolved       INTEGER     NOT NULL DEFAULT 0,
  unclassified     INTEGER     NOT NULL DEFAULT 0,
  frozen           JSONB       NOT NULL,                       -- verbatim contemporaneous payload
  source_album_ids UUID[]      NOT NULL DEFAULT '{}',          -- referenced albums (NO FK by design; may dangle)
  schema_version   INTEGER     NOT NULL DEFAULT 1,
  refreshed_from   UUID        REFERENCES bucket_item_snapshots(id) ON DELETE SET NULL,  -- append-only refresh lineage
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bucket_item_snapshots_item_id ON bucket_item_snapshots(item_id);
CREATE INDEX IF NOT EXISTS idx_bucket_item_snapshots_source_album_ids ON bucket_item_snapshots USING gin (source_album_ids);

-- =============================================================================
-- Library — "To Listen" queue (V8; supersedes the never-applied V7 library_items)
-- V31 (FEAT-pocket-buckit) folded this queue into a review_buckets row with kind='to_listen'
-- holding item_type='album' members — that bucket is now the canonical home for 들을 것.
-- This legacy table is RETAINED as a deprecated read-through (kept, not dropped, by V31).
-- Per-user since FEAT-multi-user Phase 2 (V40 user_id + per-user unique → V42 NOT NULL).
-- =============================================================================
CREATE TABLE IF NOT EXISTS album_to_listen_items (
  id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id  UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- V40 nullable+backfill → V42 NOT NULL
  album_id UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  position INTEGER     NOT NULL,
  note     TEXT,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- V40: was a global UNIQUE(album_id); two members may queue the same album.
  CONSTRAINT uq_album_to_listen_items_user_album UNIQUE (user_id, album_id)
);

-- =============================================================================
-- Spotify Listening Cache — now-playing + recent albums (V9), play events (V10), recent tracks (V14)
-- Worker/EventBridge-fed; no synchronous Spotify call from any user-facing endpoint (hard rule #9).
-- =============================================================================
CREATE TABLE IF NOT EXISTS spotify_now_playing (
  id          SMALLINT    PRIMARY KEY DEFAULT 1,
  is_playing  BOOLEAN     NOT NULL DEFAULT false,
  track_name  TEXT,
  artist_name TEXT,
  album_name  TEXT,
  album_id    UUID        REFERENCES albums(id) ON DELETE SET NULL,
  progress_ms INTEGER,
  duration_ms INTEGER,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_spotify_now_playing_singleton CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS spotify_recent_albums (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id       UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  last_played_at TIMESTAMPTZ NOT NULL,
  source         TEXT        NOT NULL DEFAULT 'spotify',
  synced_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_recent_albums_album UNIQUE (album_id)
);
CREATE INDEX IF NOT EXISTS idx_spotify_recent_albums_last_played_at
  ON spotify_recent_albums(last_played_at);

-- Append-only ALBUM-level play history (V10) — durable listen-count source;
-- spotify_recent_albums above prunes its rolling window and keeps no history.
CREATE TABLE IF NOT EXISTS spotify_play_events (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id    UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  played_at   TIMESTAMPTZ NOT NULL,
  source      TEXT        NOT NULL DEFAULT 'spotify',
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_play_events_album_played UNIQUE (album_id, played_at)
);
CREATE INDEX IF NOT EXISTS idx_spotify_play_events_played_at ON spotify_play_events(played_at);

-- V14: rolling TRACK-level cache of the recently-played window (album-level = spotify_recent_albums).
-- DENORMALIZED text + nullable album_id FK so tracks whose album isn't catalogued still display.
-- Cache, not a log: worker upserts the window and prunes to N.
CREATE TABLE IF NOT EXISTS spotify_recent_tracks (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  spotify_track_id TEXT        NOT NULL,
  track_name       TEXT        NOT NULL,
  artist_name      TEXT,
  album_name       TEXT,
  album_id         UUID        REFERENCES albums(id) ON DELETE SET NULL,
  played_at        TIMESTAMPTZ NOT NULL,
  source           TEXT        NOT NULL DEFAULT 'spotify',
  synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_recent_tracks_play UNIQUE (spotify_track_id, played_at)
);
CREATE INDEX IF NOT EXISTS idx_spotify_recent_tracks_played_at
  ON spotify_recent_tracks(played_at);

-- V19: append-only TRACK-level play history (FEAT-track-play-history). Durable
-- per-track mirror of spotify_play_events (never pruned). spotify_track_id dedups;
-- track_id/album_id resolve from the catalog when known, NULL otherwise.
CREATE TABLE IF NOT EXISTS spotify_track_play_events (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  spotify_track_id TEXT        NOT NULL,
  track_id         UUID        REFERENCES tracks(id) ON DELETE SET NULL,
  album_id         UUID        REFERENCES albums(id) ON DELETE SET NULL,
  played_at        TIMESTAMPTZ NOT NULL,
  source           TEXT        NOT NULL DEFAULT 'spotify',
  recorded_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_track_play_events_play UNIQUE (spotify_track_id, played_at)
);
CREATE INDEX IF NOT EXISTS idx_spotify_track_play_events_played_at
  ON spotify_track_play_events(played_at);

-- V24 (FEAT-genre-artist-distribution) — cache of the owner's Spotify 좋아요(saved)
-- tracks (GET /me/tracks); source for the /profile 분석 버킷 genre/artist
-- distribution. Denormalized + nullable catalog FKs so non-catalog tracks still
-- display. Keyed by the track itself (natural PK) — worker upserts per track, prunes
-- on un-like. Genre resolves at read time via track_genres → else album_genres.
-- duration_ms added by V26 (FEAT-liked-tracks-workbench Step 4).
CREATE TABLE IF NOT EXISTS spotify_saved_tracks (
  spotify_track_id  TEXT        PRIMARY KEY,
  track_name        TEXT        NOT NULL,
  artist_name       TEXT,
  album_name        TEXT,
  album_sid         TEXT,
  track_id          UUID        REFERENCES tracks(id) ON DELETE SET NULL,
  album_id          UUID        REFERENCES albums(id) ON DELETE SET NULL,
  added_at          TIMESTAMPTZ NOT NULL,
  duration_ms       INTEGER,                                    -- V26
  synced_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spotify_saved_tracks_added_at ON spotify_saved_tracks(added_at);

-- V27 (FEAT-listening-history-import) — lifetime per-stream history from the
-- owner's Spotify Extended Streaming History (GDPR export); the only source of
-- true lifetime play counts + listening time (no API exposes them). Denormalized +
-- nullable catalog FKs (resolved best-effort at import + by --resolve-only).
-- spotify_track_uri is the full URI (dedup anchor + music/podcast prefix predicate).
-- ms_played BIGINT (lifetime sum > INT4). Dedup UNIQUE (user_id, ts, spotify_track_uri)
-- since V46 (per-user re-scope; was global (ts, uri)), idempotent re-import.
-- NO IP / user-agent columns (privacy). user_id nullable until the post-soak
-- NOT NULL flip (V40/V42 pattern).
CREATE TABLE IF NOT EXISTS spotify_stream_history (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID        REFERENCES users(id) ON DELETE CASCADE,  -- V46; NOT NULL after soak
  ts                 TIMESTAMPTZ NOT NULL,                       -- stream END (export `ts`, UTC)
  ms_played          BIGINT      NOT NULL,                       -- ms listened; lifetime sum → BIGINT
  spotify_track_uri  TEXT        NOT NULL,                       -- full "spotify:track:…" / "spotify:episode:…"
  track_name         TEXT,
  artist_name        TEXT,
  album_name         TEXT,
  track_id           UUID        REFERENCES tracks(id) ON DELETE SET NULL,
  album_id           UUID        REFERENCES albums(id) ON DELETE SET NULL,
  skipped            BOOLEAN,
  offline            BOOLEAN,
  shuffle            BOOLEAN,
  incognito          BOOLEAN,
  reason_start       TEXT,
  reason_end         TEXT,
  imported_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_stream_history_user_stream UNIQUE (user_id, ts, spotify_track_uri)
);
CREATE INDEX IF NOT EXISTS idx_spotify_stream_history_album_id ON spotify_stream_history(album_id);
CREATE INDEX IF NOT EXISTS idx_spotify_stream_history_track_id ON spotify_stream_history(track_id);
CREATE INDEX IF NOT EXISTS idx_spotify_stream_history_ts ON spotify_stream_history(ts);

-- Per-import ledger for spotify_stream_history (one row per export file): parsed vs
-- inserted counts + as_of (max(ts) = staleness horizon) + run time.
CREATE TABLE IF NOT EXISTS stream_import_runs (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        REFERENCES users(id) ON DELETE CASCADE,  -- V46; whose export; NOT NULL after soak
  file_name      TEXT        NOT NULL,
  rows_total     INTEGER     NOT NULL DEFAULT 0,
  rows_inserted  INTEGER     NOT NULL DEFAULT 0,
  as_of          TIMESTAMPTZ,                                    -- NULL if the file had no valid streams
  imported_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Spotify Library Sync — two-way saved-albums mirror (V15; FEAT-spotify-library-sync)
-- review_buckets.kind='spotify_library' (above) + this immutable provenance side-table
-- (enum types defined in the Enums section). Side table so the 'preexisting' source
-- fact outlives a bucket-remove (never delete a pre-existing saved album).
-- =============================================================================
CREATE TABLE IF NOT EXISTS spotify_library_albums (
  id             UUID                   PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id       UUID                   NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  spotify_id     TEXT                   NOT NULL,                  -- denormalized for contains/PUT/DELETE
  source         spotify_library_source NOT NULL,                 -- immutable provenance (never delete preexisting)
  state          spotify_library_state  NOT NULL DEFAULT 'pending',
  in_bucket      BOOLEAN                NOT NULL DEFAULT TRUE,     -- bucket intent
  in_spotify     BOOLEAN                NOT NULL DEFAULT FALSE,    -- last-observed Library membership
  last_error     TEXT,
  last_synced_at TIMESTAMPTZ,                                      -- poll anchor
  created_at     TIMESTAMPTZ            NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ            NOT NULL DEFAULT now(),
  CONSTRAINT uq_spotify_library_albums_album UNIQUE (album_id)
);
CREATE INDEX IF NOT EXISTS idx_spotify_library_albums_state ON spotify_library_albums(state);

-- =============================================================================
-- Album Research — per-album AI research notes, writer-facing (V16; FEAT-album-research-notes)
-- One row per (album, prompt_version); that UNIQUE is the enqueue/claim dedupe
-- invariant. status is TEXT+CHECK (not a PG enum). Scope controls live on the
-- review board: review_buckets.research_mode + review_bucket_items.research_selected (above).
-- =============================================================================
CREATE TABLE IF NOT EXISTS album_research (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id         UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  prompt_version   TEXT        NOT NULL,
  status           TEXT        NOT NULL DEFAULT 'queued'
                               CHECK (status IN ('queued', 'running', 'done', 'failed')),
  model            TEXT,
  result_md        TEXT,
  tokens_in        INTEGER,
  tokens_out       INTEGER,
  search_count     INTEGER,
  error            TEXT,
  refine_count     INTEGER     NOT NULL DEFAULT 0,
  last_instruction TEXT,
  requested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at       TIMESTAMPTZ,
  finished_at      TIMESTAMPTZ,
  CONSTRAINT uq_album_research_album_prompt UNIQUE (album_id, prompt_version)
);

-- =============================================================================
-- Genres — tier-0 vocabulary + machine attachments (V17; FEAT-genre-system)
-- genres: fixed 12-genre English tier-0 vocabulary, seeded by V17; V20
--   (FEAT-genre-subgenres) seeded 211 tier-1 sub-genres via parent_id.
--   definition_md is owner-edited in place on the public /genres page (V23
--   seeded tier-0 definitions).
-- album_genres: MACHINE-ONLY attachments (source 'mapping'|'itunes'|'llm',
--   never 'manual'); confidence 'high' (2+ pipeline parts agree) | 'low'.
-- track_genres: override-only — a row exists iff the track deviates from its
--   album; effective track genre = track_genres rows if any, else the album's.
-- Artist genre is derived in queries (no artist_genres table by design).
-- =============================================================================
CREATE TABLE IF NOT EXISTS genres (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT        NOT NULL UNIQUE,          -- 'k-pop', 'rnb-soul'
  label         TEXT        NOT NULL,                 -- 'K-Pop' (English only)
  parent_id     UUID        REFERENCES genres(id) ON DELETE RESTRICT,  -- NULL = tier-0; tier-1 attaches here (V20)
  definition_md TEXT        NOT NULL DEFAULT '',      -- owner-edited on /genres
  position      INTEGER     NOT NULL DEFAULT 0,       -- display order on /genres
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS album_genres (
  album_id   UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  genre_id   UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  source     TEXT NOT NULL,                           -- 'mapping' | 'itunes' | 'llm' (machine-only, no 'manual')
  confidence TEXT NOT NULL DEFAULT 'high',            -- 'high' | 'low'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (album_id, genre_id)
);

CREATE TABLE IF NOT EXISTS track_genres (             -- override-only; row exists ⇔ track deviates from album
  track_id   UUID NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  genre_id   UUID NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  source     TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'high',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (track_id, genre_id)
);

-- V20 (FEAT-genre-subgenres): tier-1 relationship layer + editorial review tags.
-- genre_edges — ego-view + related-review rec engine; type ∈ parent|influenced_by|related
--   (influenced_by = directed, related = lateral see-also, 'parent' = multi-parent
--   fallback, 0 rows in v1). RESTRICT on both FKs per V17's rule.
-- post_genres — editorial review↔sub-genre link, per-post (humans never edit the
--   machine album_genres); populated by the /write picker.
CREATE TABLE IF NOT EXISTS genre_edges (
  from_genre_id UUID        NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  to_genre_id   UUID        NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  type          TEXT        NOT NULL CHECK (type IN ('parent','influenced_by','related')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (from_genre_id, to_genre_id, type)
);

CREATE TABLE IF NOT EXISTS post_genres (
  post_id    UUID        NOT NULL REFERENCES posts(id)  ON DELETE CASCADE,
  genre_id   UUID        NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (post_id, genre_id)
);

-- V25 (FEAT-genre-autoheal) — on-demand "장르 채우기" request queue. The /profile
-- button (backend POST) inserts a pending row; the local genre-heal poller claims
-- it and runs the existing genre pipeline, then stamps finished_at. NOT a per-album
-- queue (the backfill is marker-based); backend writes + poller reads via raw SQL —
-- deliberately NO ORM model (no pin bump), which is why this table lives only here
-- and in prod.
CREATE TABLE IF NOT EXISTS genre_backfill_requests (
  id            BIGSERIAL   PRIMARY KEY,
  requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  claimed_at    TIMESTAMPTZ,                         -- set when the poller starts a run
  finished_at   TIMESTAMPTZ,                         -- set when the backfill run returns
  source        TEXT                                 -- requesting surface, e.g. '분석 버킷'
);
-- The poller's "next unclaimed request" lookup.
CREATE INDEX IF NOT EXISTS idx_genre_backfill_requests_pending
  ON genre_backfill_requests (requested_at)
  WHERE claimed_at IS NULL;

-- =============================================================================
-- Lyrics Corpus — track_lyrics (V33, FEAT-lyrics-corpus)
-- Owner-only research data (album_research/aliases privacy precedent): NEVER joined into
-- any public response, search index, bucket, post, or edge-cached response. Read leaves
-- the server only via the JWT-gated GET /api/lyrics/{spotify_track_id} (FEAT-lyrics-viewer).
-- Match-status lifecycle: matched | no_lyrics | not_found | ambiguous | review_required —
-- only 'matched'/'no_lyrics' carry lyric_plain; evidence JSONB holds match evidence
-- (artist resolution, normalized-title, duration tolerance, version tokens, ISRC/MB);
-- matcher_version enables re-evaluation on matcher change.
-- =============================================================================
CREATE TABLE IF NOT EXISTS track_lyrics (
  track_id        UUID        PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
  match_status    TEXT        NOT NULL,
  evidence        JSONB       NOT NULL DEFAULT '{}'::jsonb,
  lyric_plain     TEXT,       -- populated iff match_status ∈ ('matched','no_lyrics')
  lyric_synced    TEXT,       -- LRC synced lyrics where the source has them
  matcher_version TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_track_lyrics_match_status
    CHECK (match_status IN ('matched', 'no_lyrics', 'not_found', 'ambiguous', 'review_required')),
  CONSTRAINT ck_track_lyrics_lyric_on_resolved
    CHECK (
      (match_status IN ('matched', 'no_lyrics') AND lyric_plain IS NOT NULL)
      OR (match_status NOT IN ('matched', 'no_lyrics') AND lyric_plain IS NULL)
    )
);

-- =============================================================================
-- Lyrics Translations — track_lyrics_translations (V35, FEAT-lyrics-translation)
-- Korean translation store + request lifecycle for owner-designated lyrics tracks; one row
-- per track, request and result in the same row. Derivative work of track_lyrics → same
-- owner-only privacy bar. Lifecycle: requested | done | failed (pending = 'requested' AND
-- claimed_at IS NULL — partial index below; local launchd poller claims via FOR UPDATE
-- SKIP LOCKED + 20-min re-claim). Staleness is computed at READ time by comparing
-- source_fingerprint against a fresh normalize — never stored as a flag.
-- =============================================================================
CREATE TABLE IF NOT EXISTS track_lyrics_translations (
  track_id           UUID        PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
  status             TEXT        NOT NULL,
  claimed_at         TIMESTAMPTZ,                     -- poller claim gate (20-min re-claim)
  lang               TEXT        NOT NULL DEFAULT 'ko',
  segments           JSONB,                           -- [{i, text_ko}], 1:1 with normalized source segments
  source_fingerprint TEXT,                            -- sha256(normalizer_version + source segment texts)
  normalizer_version INTEGER,                         -- lyrics_service NORMALIZER_VERSION at translation time
  origin             TEXT,                            -- 'poller' | 'manual' (NULL until a result lands)
  model              TEXT,                            -- e.g. 'sonnet'
  translator_version TEXT,                            -- poller prompt/pipeline version
  error              TEXT,                            -- failure reason on status='failed'
  requested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  translated_at      TIMESTAMPTZ,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_track_lyrics_translations_status
    CHECK (status IN ('requested', 'done', 'failed')),
  CONSTRAINT ck_track_lyrics_translations_origin
    CHECK (origin IS NULL OR origin IN ('poller', 'manual')),
  CONSTRAINT ck_track_lyrics_translations_done_payload
    CHECK (status <> 'done' OR (segments IS NOT NULL AND source_fingerprint IS NOT NULL))
);

-- The poller's "next pending request" lookup (V25 pending-index pattern).
CREATE INDEX IF NOT EXISTS idx_track_lyrics_translations_pending
  ON track_lyrics_translations (requested_at)
  WHERE status = 'requested' AND claimed_at IS NULL;

-- =============================================================================
-- Album Reviews — RYM-style public member reviews (V38; FEAT-multi-user-accounts Phase 1)
-- One review per member per album: 0.5–5.0 half-step rating + optional comment.
-- All reviews public (no visibility column). Aggregates computed LIVE at read
-- time (no denormalized counter on albums); idx_album_reviews_album_id keeps the
-- scan cheap, idx_album_reviews_user_created serves the newest-first profile feed.
-- =============================================================================
CREATE TABLE IF NOT EXISTS album_reviews (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES users (id)  ON DELETE CASCADE,
  album_id   UUID        NOT NULL REFERENCES albums (id) ON DELETE CASCADE,
  rating     NUMERIC(2,1) NOT NULL,
  comment    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_album_reviews_user_album UNIQUE (user_id, album_id),
  CONSTRAINT ck_album_reviews_rating_halfstep
    CHECK (rating >= 0.5 AND rating <= 5.0 AND mod(rating, 0.5) = 0)
);
CREATE INDEX IF NOT EXISTS idx_album_reviews_album_id
  ON album_reviews (album_id);
CREATE INDEX IF NOT EXISTS idx_album_reviews_user_created
  ON album_reviews (user_id, created_at);

-- =============================================================================
-- Daily Picks — owner-curated "song of the day" store (V39; FEAT-today-buckit Step 3)
-- One pick per calendar day (upsert on pick_date); track-primary (a pick is always
-- a TRACK; album_id carried for the album-window click target). Denormalized
-- display columns make the public GET self-contained; no note/impression column.
-- =============================================================================
CREATE TABLE IF NOT EXISTS daily_picks (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  pick_date        DATE        NOT NULL,               -- one pick per day (upsert key)
  track_id         UUID        NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
  album_id         UUID        NOT NULL REFERENCES albums (id) ON DELETE CASCADE,
  title            TEXT        NOT NULL,               -- denormalized track title
  artist           TEXT        NOT NULL,               -- denormalized primary-artist display
  cover_url        TEXT,                               -- album art (nullable — source gaps)
  spotify_track_id TEXT        NOT NULL,               -- click/play target (mirrors tracks.spotify_id)
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_daily_picks_pick_date UNIQUE (pick_date)
);

-- =============================================================================
-- User Integrations — the ONE connect store for listening/AI sources (V41;
-- FEAT-multi-user-accounts Phase 3a — OQ4: single table). One row per
-- (user, provider). Last.fm = username-only (no OAuth/token custody); Spotify
-- (3b) / AI keys (P4 BYOK) use the KMS-encrypted `payload` (never logged).
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_integrations (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  provider       TEXT        NOT NULL,               -- 'lastfm' | 'spotify' | 'ai_key'
  username       TEXT,                               -- Last.fm handle (public reads, no OAuth)
  payload        TEXT,                               -- KMS ciphertext (Spotify 3b / AI key P4); never logged
  status         TEXT        NOT NULL DEFAULT 'connected',
  last_synced_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_integrations_user_provider UNIQUE (user_id, provider),
  CONSTRAINT ck_user_integrations_provider CHECK (provider IN ('lastfm', 'spotify', 'ai_key')),
  CONSTRAINT ck_user_integrations_status CHECK (status IN ('connected', 'reauth', 'error', 'disconnected'))
);
-- Poller iterates connected rows for a provider.
CREATE INDEX IF NOT EXISTS idx_user_integrations_provider_status
  ON user_integrations (provider, status);

-- V41: per-user Last.fm scrobbles + the single now-playing row, written by the
-- worker EventBridge poll (user.getRecentTracks incremental). Last.fm returns
-- TEXT names + optional MBIDs (not our catalog UUIDs) → denormalized text store
-- (mirrors spotify_stream_history); catalog resolution is a later concern.
-- A now-playing track has no timestamp (@attr nowplaying) → played_at NULL +
-- is_now_playing TRUE; at most one per user.
CREATE TABLE IF NOT EXISTS lastfm_recent_tracks (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  artist_name    TEXT        NOT NULL,
  track_name     TEXT        NOT NULL,
  album_name     TEXT,
  artist_mbid    TEXT,
  track_mbid     TEXT,
  album_mbid     TEXT,
  image_url      TEXT,
  played_at      TIMESTAMPTZ,                         -- NULL only for the now-playing row
  is_now_playing BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- A completed scrobble always has a timestamp; only now-playing may omit it.
  CONSTRAINT ck_lastfm_recent_played_at CHECK (is_now_playing OR played_at IS NOT NULL)
);
-- One completed scrobble per (user, instant) — the incremental-upsert dedup key.
CREATE UNIQUE INDEX IF NOT EXISTS uq_lastfm_recent_user_played
  ON lastfm_recent_tracks (user_id, played_at) WHERE NOT is_now_playing;
-- At most one now-playing row per user (poller replaces it each run).
CREATE UNIQUE INDEX IF NOT EXISTS uq_lastfm_recent_now_playing
  ON lastfm_recent_tracks (user_id) WHERE is_now_playing;
-- Profile feed: a member's scrobbles newest-first (btree scans backward for DESC).
CREATE INDEX IF NOT EXISTS idx_lastfm_recent_user_played
  ON lastfm_recent_tracks (user_id, played_at);

-- =============================================================================
-- LLM Usage — append-only usage metering (V43; FEAT-multi-user-accounts Phase 4)
-- One audit row per LLM dispatch, written by the shared engine's single
-- record_usage() path (CliEngine records non-blocking owner audit; ApiEngine
-- also runs a PRE-dispatch cap check as a live aggregate over this table —
-- the shipped Phase-1 review-cap pattern, no denormalized counter).
-- =============================================================================
CREATE TABLE IF NOT EXISTS llm_usage (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        REFERENCES users (id) ON DELETE CASCADE,  -- NULL = owner/system run
  feature    TEXT        NOT NULL,               -- caller tag (e.g. 'editorial_critique')
  engine     TEXT        NOT NULL,               -- 'cli' | 'api'
  model      TEXT,                               -- resolved model id/alias (NULL = CLI default)
  tokens_in  INTEGER     NOT NULL DEFAULT 0,     -- 0 in CLI text mode (honest gap)
  tokens_out INTEGER     NOT NULL DEFAULT 0,
  is_error   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_llm_usage_engine CHECK (engine IN ('cli', 'api'))
);
-- Serves the pre-dispatch window count (WHERE user_id = ? AND feature = ? AND created_at > cutoff).
CREATE INDEX IF NOT EXISTS idx_llm_usage_user_feature_created
  ON llm_usage (user_id, feature, created_at);

-- =============================================================================
-- Release Calendar — multi-source release events (V44; FEAT-release-calendar
-- Track B). artist_release_events = ONE ROW PER (source, source_key)
-- observation; same-album rows from different sources stay separate rows
-- (soft-grouped for display only) until release-day confirmation stamps the
-- shared spotify_album_id. artist_source_ids = per-source artist-id resolution
-- cache (v1: 'itunes' only; source deliberately un-CHECKed — MB/Spotify artist
-- ids already live on artists).
-- =============================================================================
CREATE TABLE IF NOT EXISTS artist_release_events (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id        UUID        NOT NULL REFERENCES artists (id) ON DELETE CASCADE,
  source           TEXT        NOT NULL,        -- 'musicbrainz' | 'itunes' | 'spotify'
  source_key       TEXT        NOT NULL,        -- MB release-group MBID / iTunes collectionId / Spotify album id
  spotify_album_id TEXT,                        -- set on release-day confirmation (cross-source collapse key)
  title            TEXT        NOT NULL,
  release_type     TEXT,                        -- 'album' | 'ep' | 'single' | 'other'; NULL = source gave none
  release_date     DATE        NOT NULL,        -- full dates only in v1
  status           TEXT        NOT NULL DEFAULT 'announced',
  first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- FULL unique (deliberately not partial) — the poller's upsert conflict key.
  CONSTRAINT uq_artist_release_events_source_key UNIQUE (source, source_key),
  CONSTRAINT ck_artist_release_events_source CHECK (source IN ('musicbrainz', 'itunes', 'spotify')),
  CONSTRAINT ck_artist_release_events_type CHECK (release_type IN ('album', 'ep', 'single', 'other')),
  CONSTRAINT ck_artist_release_events_status CHECK (status IN ('announced', 'released'))
);
-- Calendar read path: events in a date window, optionally by status.
CREATE INDEX IF NOT EXISTS idx_artist_release_events_status_date
  ON artist_release_events (status, release_date);
-- Confirmation match + per-artist listing (the UNIQUE above leads with source).
CREATE INDEX IF NOT EXISTS idx_artist_release_events_artist
  ON artist_release_events (artist_id);

CREATE TABLE IF NOT EXISTS artist_source_ids (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id        UUID        NOT NULL REFERENCES artists (id) ON DELETE CASCADE,
  source           TEXT        NOT NULL,        -- v1: 'itunes' only; no CHECK by design
  source_artist_id TEXT        NOT NULL,
  resolved_via     TEXT,                        -- e.g. 'upc' (the hard-ID resolution chain)
  resolved_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- One resolved id per (artist, source); leads with artist_id so per-artist
  -- lookups need no extra index.
  CONSTRAINT uq_artist_source_ids_artist_source UNIQUE (artist_id, source)
);

-- =============================================================================
-- Personal Release Tracking — per-user tracked-artist edge (V47; FEAT-personal-
-- release-tracking Step 1). The personalization layer on top of the shared
-- artist_release_events above: one row per (user, artist). Buckit import is a
-- snapshot source only — after import the tracked list is independent (no FK
-- back to a Buckit). Anchored to the catalog artist entity so a release from
-- any source attaches to the same artist the user tracked. Born user-scoped;
-- CASCADE on both FKs (privacy §2 deletion path).
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_artist_tracks (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  artist_id  UUID        NOT NULL REFERENCES artists (id) ON DELETE CASCADE,
  added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- One tracked edge per (user, artist); FULL unique so the import upsert can
  -- use plain ON CONFLICT (user_id, artist_id) DO NOTHING.
  CONSTRAINT uq_user_artist_tracks_user_artist UNIQUE (user_id, artist_id)
);
CREATE INDEX IF NOT EXISTS idx_user_artist_tracks_artist
  ON user_artist_tracks (artist_id);

-- =============================================================================
-- Member Spotify Listening — born-user-scoped tables (V45; FEAT-multi-user-
-- accounts Phase 3b-b, mirrors the V41 lastfm_recent_tracks pattern). The
-- owner-global spotify_* caches and their worker jobs stay untouched (owner
-- decision #1). v1 = now-playing + recently-played READS only. Written by the
-- 3b-d worker per-user poll (decrypt refresh token → fetch → dedup insert).
-- =============================================================================
CREATE TABLE IF NOT EXISTS spotify_member_recent_tracks (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  spotify_track_id TEXT        NOT NULL,        -- hard Spotify ID (unlike Last.fm)
  track_name       TEXT        NOT NULL,
  artist_name      TEXT        NOT NULL,
  album_name       TEXT,
  image_url        TEXT,                        -- album cover (mirrors lastfm_recent_tracks)
  played_at        TIMESTAMPTZ NOT NULL,        -- Spotify always timestamps completed plays
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Poller dedup key (NOT-EXISTS insert, V41 philosophy). FULL constraint (not
  -- partial) so a future ON CONFLICT can infer it; leads (user_id, played_at)
  -- so the newest-first profile feed needs no extra index.
  CONSTRAINT uq_spotify_member_recent_user_played
    UNIQUE (user_id, played_at, spotify_track_id)
);

-- V45: one now-playing row per user — the per-user analog of the V9 id=1
-- singleton spotify_now_playing (user_id PK; poller upserts ON CONFLICT
-- (user_id)). Track fields NULL until the first observed play; is_playing
-- FALSE keeps the last snapshot (owner-singleton shape incl. progress/duration).
CREATE TABLE IF NOT EXISTS spotify_member_now_playing (
  user_id          UUID        PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  is_playing       BOOLEAN     NOT NULL DEFAULT FALSE,
  spotify_track_id TEXT,                        -- NULL when nothing has played yet
  track_name       TEXT,
  artist_name      TEXT,
  album_name       TEXT,
  image_url        TEXT,
  progress_ms      INTEGER,
  duration_ms      INTEGER,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- NOTE: `library_items` (V7) is intentionally absent — it was superseded by
-- `album_to_listen_items` (V8) before any prod apply and does NOT exist in prod.
--
-- This file is current through V47 (user_artist_tracks, FEAT-personal-release-
-- tracking Step 1 — authored + prod-applied 2026-07-15), after V46 (user_id on
-- spotify_stream_history + stream_import_runs, FEAT-multi-user-accounts Phase
-- 3c-a — authored + prod-applied 2026-07-12; user_id stays nullable until the
-- post-soak NOT NULL flip), after V45 (spotify_member_recent_tracks +
-- spotify_member_now_playing, FEAT-multi-user-accounts Phase 3b-b — authored +
-- prod-applied 2026-07-12), after V44 (artist_release_events +
-- artist_source_ids, FEAT-release-calendar Track B Step 3 — authored +
-- prod-applied 2026-07-12). V1–V43 fully reconciled against a prod
-- introspection 2026-07-11 (CHORE-canonical-schema-sync; the introspection also
-- backfilled the V20–V27 objects this file previously skipped: genre_edges +
-- post_genres (V20, tier-1 seed V20/V21, definitions V23), prep_tonight (V22),
-- spotify_saved_tracks (V24, duration_ms V26), genre_backfill_requests (V25),
-- spotify_stream_history + stream_import_runs (V27)).
--
-- Earlier verification history: V1–V13 prod-verified 2026-06-08 (categories→
-- sections rename; see header NB for prod's legacy physical names); V14/V15
-- backfilled 2026-06-09; V16 backfilled 2026-06-12; V17 prod-verified
-- 2026-06-12; V18 prod-live 2026-06-15; V19 prod-live 2026-06-15
-- (FEAT-track-play-history); V28–V31 prod-live 2026-06-24 (FEAT-pocket-buckit);
-- V32 prod-live 2026-06-30 (FEAT-my-buckit-artist); V33/V34 prod-live
-- 2026-07-01 (FEAT-lyrics-corpus); V35 prod-applied 2026-07-04
-- (FEAT-lyrics-translation); V36 (users) / V37 (post_recommended_tracks
-- composite PK) / V38 (album_reviews) / V39 (daily_picks) / V40+V42
-- (bucket user_id, NOT NULL) / V41 (user_integrations + lastfm_recent_tracks) /
-- V43 (llm_usage) prod-applied 2026-07-07 – 2026-07-11 (FEAT-multi-user-accounts
-- Phases 0–4 scaffolding + FIX-bug-audit-2026-07 WS-B.2 + FEAT-today-buckit).
-- Last full structural prod-verify: 2026-07-11.
-- =============================================================================
