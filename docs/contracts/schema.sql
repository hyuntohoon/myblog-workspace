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
-- This file shows clean canonical DDL through V35 (V1–V13 prod-verified 2026-06-08;
--   V14/V15 backfilled from migration DDL 2026-06-09; V16 backfilled 2026-06-12 —
--   all prod-applied + prod-live. V17 prod-applied + prod-verified 2026-06-12; V18
--   (review_buckets.is_public) prod-live 2026-06-15; V19 (spotify_track_play_events)
--   added 2026-06-15 — prod-apply PENDING before the worker deploy, FEAT-track-play-history.
--   V28/V29/V30/V31 (FEAT-pocket-buckit generalized membership: review_bucket_items.item_type
--   + typed FKs + per-kind partial uniques, bucket_item_snapshots side-table, 들을 것 folded to
--   a kind='to_listen' system bucket) prod-live 2026-06-24. V32 (My Buckit: review_buckets.type
--   + review_bucket_items.artist_id + artist guards, FEAT-my-buckit-artist) prod-live 2026-06-30.
--   V33 (track_lyrics) + V34 (tracks.isrc) (FEAT-lyrics-corpus Step 1) prod-live 2026-07-01.
--   V35 (track_lyrics_translations, FEAT-lyrics-translation Step 1) prod-applied 2026-07-04.
--   V20–V27 not separately backfilled
--   here — see myblog_shared_db/migrations/ for the authoritative version-ordered set.
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
  isrc         TEXT,       -- V34: ISRC identity/version anchor — server-side matching evidence only (aliases/musicbrainz_id precedent, never public); no UNIQUE (optional, source gaps)
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
  kind       TEXT        NOT NULL DEFAULT 'review',                        -- V15: marks the single spotify_library bucket; V31: 'to_listen' system bucket (들을 것) — free TEXT, same idiom as 'spotify_library'
  research_mode TEXT     NOT NULL DEFAULT 'off'
                         CHECK (research_mode IN ('off', 'all', 'selected')),  -- V16: auto-research scope (FEAT-album-research-notes)
  is_public  BOOLEAN     NOT NULL DEFAULT false,                           -- V18: public bucket viewer opt-in (FEAT-public-bucket-multiuser)
  type       TEXT        NOT NULL DEFAULT 'general'                        -- V32: General vs Artist Buckit (FEAT-my-buckit-artist); orthogonal to kind; immutable after create (app-layer)
             CONSTRAINT ck_review_buckets_type CHECK (type IN ('general', 'artist'))
);
CREATE INDEX IF NOT EXISTS idx_review_buckets_parent_id ON review_buckets(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_done
  ON review_buckets((true)) WHERE is_done;
-- V15: at most one kind='spotify_library' bucket (constant-expression partial unique)
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_buckets_single_spotify_library
  ON review_buckets((true)) WHERE kind = 'spotify_library';

-- V28/V30 (FEAT-pocket-buckit) generalized album-only membership to a TYPED relationship:
--   V28 added item_type (DEFAULT 'album') + nullable typed FKs track_id/review_target_id;
--   V30 dropped album_id NOT NULL, replaced the table-wide UNIQUE(bucket_id, album_id) with
--   per-kind PARTIAL uniques (album/track/review reject dupes; playback/snapshot allow), and
--   added ck_review_bucket_items_album_id_present so album-kind rows still must carry album_id.
-- review_target_id (CASCADE) is DISTINCT from post_id (SET NULL): post_id = "the review this
--   ALBUM produced"; review_target_id = "this item IS a review member" (item_type='review').
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
-- genres: fixed 12-genre English vocabulary, seeded by V17 (the migration is
--   the source of truth for slugs/labels). parent_id NULL = tier-0; the future
--   tier-1 (sub-genre) RFC attaches via parent_id with no migration.
--   definition_md is owner-edited in place on the public /genres page.
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
  parent_id     UUID        REFERENCES genres(id) ON DELETE RESTRICT,  -- NULL = tier-0
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
-- NOTE: `library_items` (V7) is intentionally absent — it was superseded by
-- `album_to_listen_items` (V8) before any prod apply and does NOT exist in prod.
-- This file is current through V35. V1–V13 verified against prod 2026-06-08
-- (categories→sections rename; see the section-rename note in the header for prod's
-- legacy physical object names). V14 (spotify_recent_tracks) + V15 (spotify_library_albums
-- + review_buckets.kind + 2 enums) backfilled from migration DDL 2026-06-09; V16
-- (album_research + research scope columns) backfilled from migration DDL 2026-06-12 —
-- all prod-applied + prod-live. V17 (genres + album_genres + track_genres + 12-row seed)
-- added 2026-06-12, prod-applied + prod-verified same day (FEAT-genre-system Step 1,
-- shared_db v0.17.0). V18 (review_buckets.is_public) prod-live 2026-06-15
-- (FEAT-public-bucket-multiuser Scope A). V19 (spotify_track_play_events — durable
-- TRACK-level play log) added 2026-06-15, FEAT-track-play-history — prod-apply PENDING,
-- must hit Neon main BEFORE the worker deploy. V28/V29 (review_bucket_items.item_type +
-- typed FKs; bucket_item_snapshots side-table) + V30 (album_id NOT NULL dropped, per-kind
-- partial uniques, ck_review_bucket_items_album_id_present) + V31 (들을 것 folded to a
-- kind='to_listen' system bucket; album_to_listen_items retained as deprecated read-through)
-- prod-applied + Neon-prod-live 2026-06-24 (FEAT-pocket-buckit). V32 (review_buckets.type +
-- review_bucket_items.artist_id + artist partial-unique/guards) prod-live 2026-06-30
-- (FEAT-my-buckit-artist). V33 (track_lyrics) + V34 (tracks.isrc) prod-live 2026-07-01
-- (FEAT-lyrics-corpus Step 1). V35 (track_lyrics_translations + pending partial index)
-- prod-applied 2026-07-04 (FEAT-lyrics-translation Step 1). V20–V27 are not separately
-- backfilled into this file — myblog_shared_db/migrations/ is the authoritative version set.
-- Last full structural prod-verify 2026-06-05 (STAB-4).
-- =============================================================================
