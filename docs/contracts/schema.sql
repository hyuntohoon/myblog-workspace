-- =============================================================================
-- Canonical Database Schema
-- Source of truth: docs/contracts/schema.sql (myblog-workspace repo)
--
-- Change policy:
--   1. Update THIS file first.
--   2. Write a migration script for the running DB (never DROP/TRUNCATE in prod).
--   3. Update the affected service's ORM models and local schema file.
--   4. Deploy consumer services before or simultaneously with producer services.
--
-- Service-local schema files (myblog_music/db/schema.sql, etc.) are
-- DERIVED from this file and kept for local dev convenience only.
--
-- This file shows clean canonical DDL through V15 (V1–V13 prod-verified 2026-06-08;
--   V14/V15 backfilled from migration DDL 2026-06-09 — both prod-applied + prod-live).
-- NB — STAB-5 V13 renamed `categories`→`sections` and `posts.category_id`→`section_id`
--   IN-PLACE (`ALTER TABLE ... RENAME`). Postgres carries constraints/indexes/FK across
--   a rename by OID, so prod's PHYSICAL names still read the pre-V13 `categor*` form:
--     • index   `idx_posts_category_id`        (now on `posts(section_id)`)
--     • uniques `categories_pkey/_name_key/_slug_key`  (now on `sections`)
--     • FK      `posts_category_id_fkey`        (now `section_id` → `sections(id)`)
--   The DDL below uses the clean `section_*` names; a fresh bootstrap therefore yields
--   `section_*`-named objects rather than prod's legacy names — cosmetic only (object
--   shape is identical). Do NOT reintroduce a `categories` table / `category_id` column.
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

-- =============================================================================
-- Sections & Tags
-- =============================================================================
-- `sections` (V13, STAB-5) — curated public post taxonomy, one section per post
-- (single FK). Seeded by V13: Reviews / Best New Music / Features / Tracks. No
-- get-or-create, no public create API. Renamed in place from `categories` (V12).
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
  album_cover_url TEXT,
  rating          NUMERIC(3,2) CHECK (rating IS NULL OR (rating >= 0 AND rating <= rating_scale)),  -- V5 widened (3,1)→(3,2); bound is rating_scale, not a literal
  rating_scale    SMALLINT     NOT NULL DEFAULT 5 CHECK (rating_scale >= 1 AND rating_scale <= 10)
);

CREATE INDEX IF NOT EXISTS idx_posts_posted_date  ON posts(posted_date);
CREATE INDEX IF NOT EXISTS idx_posts_section_id  ON posts(section_id);  -- prod physical name still idx_posts_category_id (OID-carried across V13 rename)
CREATE INDEX IF NOT EXISTS idx_posts_status        ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_slug          ON posts(slug);

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
  musicbrainz_id  TEXT,                                    -- nullable; UNIQUE only when present (see partial index below). 'MBID_NOT_FOUND' sentinel = lookup attempted and failed.
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

CREATE INDEX IF NOT EXISTS idx_artists_spotify_id ON artists(spotify_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_artists_musicbrainz_id
  ON artists(musicbrainz_id) WHERE musicbrainz_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_artists_popularity_followers_views
  ON artists(popularity DESC, followers DESC, views DESC);
CREATE INDEX IF NOT EXISTS idx_artists_name_trgm ON artists USING gin (name gin_trgm_ops);  -- V12

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

CREATE INDEX IF NOT EXISTS idx_albums_spotify_id ON albums(spotify_id);
CREATE INDEX IF NOT EXISTS idx_albums_popularity_views
  ON albums(popularity DESC, views DESC);
CREATE INDEX IF NOT EXISTS idx_albums_best_new
  ON albums(best_new) WHERE best_new = true;
CREATE INDEX IF NOT EXISTS idx_albums_title_trgm ON albums USING gin (title gin_trgm_ops);  -- V12

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
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_tracks_duration_nonneg CHECK (duration_sec IS NULL OR duration_sec >= 0),
  CONSTRAINT chk_tracks_trackno_pos     CHECK (track_no     IS NULL OR track_no     > 0),
  CONSTRAINT chk_tracks_views_nonneg    CHECK (views >= 0)
);

CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_track_no ON tracks(track_no);
CREATE INDEX IF NOT EXISTS idx_tracks_spotify_id ON tracks(spotify_id);
CREATE INDEX IF NOT EXISTS idx_tracks_title_trgm ON tracks USING gin (title gin_trgm_ops);  -- V12

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

-- =============================================================================
-- Post ↔ Artist (M:N)
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_artists (
  post_id   UUID NOT NULL REFERENCES posts(id)   ON DELETE CASCADE,
  artist_id UUID NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, artist_id)
);

-- =============================================================================
-- Post Recommended Tracks
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_recommended_tracks (
  post_id  UUID     NOT NULL,
  album_id UUID     NOT NULL,
  track_id UUID     NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  position SMALLINT,
  note     TEXT,
  PRIMARY KEY (track_id),
  FOREIGN KEY (post_id, album_id) REFERENCES post_albums(post_id, album_id) ON DELETE CASCADE
);

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
-- Review Buckets — private review-writing kanban (V6; parent_id V11)
-- (Backfilled 2026-06-05 from prod introspection — STAB-4. NOT public taxonomy.)
-- =============================================================================
CREATE TABLE IF NOT EXISTS review_buckets (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT        NOT NULL,
  position   INTEGER     NOT NULL,
  color      TEXT,
  is_done    BOOLEAN     NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  parent_id  UUID        REFERENCES review_buckets(id) ON DELETE CASCADE,  -- V11
  kind       TEXT        NOT NULL DEFAULT 'review'                         -- V15: marks the single spotify_library bucket
);
CREATE INDEX IF NOT EXISTS idx_review_buckets_parent_id ON review_buckets(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_done
  ON review_buckets((true)) WHERE is_done;
-- V15: at most one kind='spotify_library' bucket (constant-expression partial unique)
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_spotify_library
  ON review_buckets((true)) WHERE kind = 'spotify_library';

CREATE TABLE IF NOT EXISTS review_bucket_items (
  id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket_id  UUID         NOT NULL REFERENCES review_buckets(id) ON DELETE CASCADE,
  album_id   UUID         NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  position   INTEGER      NOT NULL,
  note       TEXT,
  status     review_bucket_item_status NOT NULL DEFAULT 'candidate',
  post_id    UUID         REFERENCES posts(id) ON DELETE SET NULL,
  rec_reason TEXT,
  added_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
  UNIQUE (bucket_id, album_id)
);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_album_id  ON review_bucket_items(album_id);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_bucket_id ON review_bucket_items(bucket_id);
CREATE INDEX IF NOT EXISTS idx_review_bucket_items_post_id   ON review_bucket_items(post_id);

-- =============================================================================
-- Library — "To Listen" queue (V8; supersedes the never-applied V7 library_items)
-- =============================================================================
CREATE TABLE IF NOT EXISTS album_to_listen_items (
  id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id UUID        NOT NULL UNIQUE REFERENCES albums(id) ON DELETE CASCADE,
  position INTEGER     NOT NULL,
  note     TEXT,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Spotify Listening Cache — now-playing + recent albums (V9), play events (V10), recent tracks (V14)
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
  album_id       UUID        NOT NULL UNIQUE REFERENCES albums(id) ON DELETE CASCADE,
  last_played_at TIMESTAMPTZ NOT NULL,
  source         TEXT        NOT NULL DEFAULT 'spotify',
  synced_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spotify_recent_albums_last_played_at
  ON spotify_recent_albums(last_played_at);

CREATE TABLE IF NOT EXISTS spotify_play_events (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  album_id    UUID        NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
  played_at   TIMESTAMPTZ NOT NULL,
  source      TEXT        NOT NULL DEFAULT 'spotify',
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (album_id, played_at)
);
CREATE INDEX IF NOT EXISTS idx_spotify_play_events_played_at ON spotify_play_events(played_at);

-- V14: rolling TRACK-level cache of the recently-played window (album-level = spotify_recent_albums).
-- DENORMALIZED text + nullable album_id FK so tracks whose album isn't catalogued still display.
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

-- =============================================================================
-- Spotify Library Sync — two-way saved-albums mirror (V15; FEAT-spotify-library-sync)
-- review_buckets.kind='spotify_library' (above) + this immutable provenance side-table.
-- =============================================================================
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
-- NOTE: `library_items` (V7) is intentionally absent — it was superseded by
-- `album_to_listen_items` (V8) before any prod apply and does NOT exist in prod.
-- This file is current through V15. V1–V13 verified against prod 2026-06-08
-- (categories→sections rename; see the section-rename note in the header for prod's
-- legacy physical object names). V14 (spotify_recent_tracks) + V15 (spotify_library_albums
-- + review_buckets.kind + 2 enums) backfilled from migration DDL 2026-06-09 — both
-- prod-applied + prod-live. Last full structural prod-verify 2026-06-05 (STAB-4).
-- =============================================================================
