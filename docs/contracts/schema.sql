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
-- =============================================================================

-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- Enums
-- =============================================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'post_status') THEN
    CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_subject') THEN
    CREATE TYPE review_subject AS ENUM ('album', 'track');
  END IF;
END$$;

-- =============================================================================
-- Categories & Tags
-- =============================================================================
CREATE TABLE IF NOT EXISTS categories (
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
  category_id     BIGINT       REFERENCES categories(id) ON DELETE SET NULL,
  search_index    BOOLEAN      NOT NULL DEFAULT TRUE,
  extra           JSONB        NOT NULL DEFAULT '{}'::jsonb,

  -- Music review fields
  album_cover_url TEXT,
  rating          NUMERIC(3,1) CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10)),
  rating_scale    SMALLINT     NOT NULL DEFAULT 5 CHECK (rating_scale >= 1 AND rating_scale <= 10)
);

CREATE INDEX IF NOT EXISTS idx_posts_posted_date  ON posts(posted_date);
CREATE INDEX IF NOT EXISTS idx_posts_category_id  ON posts(category_id);
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
  ext_refs     JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_albums_views_nonneg CHECK (views >= 0)
);

CREATE INDEX IF NOT EXISTS idx_albums_spotify_id ON albums(spotify_id);
CREATE INDEX IF NOT EXISTS idx_albums_popularity_views
  ON albums(popularity DESC, views DESC);

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
-- Reviews (polymorphic: album or track)
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_reviews (
  id           BIGSERIAL   PRIMARY KEY,
  post_id      UUID        NOT NULL REFERENCES posts(id)   ON DELETE CASCADE,
  subject      review_subject NOT NULL,
  album_id     UUID        REFERENCES albums(id)  ON DELETE SET NULL,
  track_id     UUID        REFERENCES tracks(id)  ON DELETE SET NULL,
  rating_value NUMERIC(3,1),
  rating_scale SMALLINT    NOT NULL DEFAULT 10,
  notes        TEXT,
  extra        JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_post_reviews_target CHECK (
    (subject = 'album' AND album_id IS NOT NULL AND track_id IS NULL) OR
    (subject = 'track' AND track_id IS NOT NULL AND album_id IS NULL)
  ),
  CONSTRAINT chk_post_reviews_rating CHECK (
    rating_value IS NULL OR (rating_value >= 0 AND rating_value <= rating_scale)
  )
);

CREATE INDEX IF NOT EXISTS idx_post_reviews_post_id  ON post_reviews(post_id);
CREATE INDEX IF NOT EXISTS idx_post_reviews_album_id ON post_reviews(album_id);
CREATE INDEX IF NOT EXISTS idx_post_reviews_track_id ON post_reviews(track_id);

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
