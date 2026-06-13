# Open Questions — Overnight Review 2026-06-13

Questions raised during the autonomous run, each paired with the assumption adopted to keep going. Consolidated from all phases at the end of the run.

---

## OQ-0 — Referenced prioritization doc not found

**Question:** The brief says to read `2026-05-29-feature-prioritization-v2.md` before starting. This file does not exist anywhere in the repo or in `git log` history (searched workspace-wide + `git log --all -- '*prioritization*'`).

**Assumption adopted:** Treated the "already-decided" baseline as the union of: `docs/plan.md` (Active / Backlog / Frozen sections), `docs/rfcs/README.md` index, and `docs/archive/done/` (esp. `2026-06.md` + `rfcs/`). This is a superset of what a single prioritization doc would contain, so re-proposal risk is low. If the owner has the v2 doc elsewhere (e.g. local-only, Drive), Task 5 candidates should be cross-checked against it.

---

<!-- phase agents append OQ-N entries below -->

## OQ-1 — [Task1/myblog_music] shared_db pin bump v0.3.0 → v0.18.1

**Question:** Should music's `shared_db` pin be bumped to v0.18.1 now to re-align with backend/worker, or is the lag intentional?

**Assumption adopted:** Unintentional drift. Bump needs a prod smoke since no local DB exists on this machine.

---

## OQ-2 — [Task1/myblog_music] candidates→SQS test fix vs replace

**Question:** Is the broken `tests/test_candidates_localstack.py` worth fixing to the current `/api/music/search/candidates` route + `album_ids` message shape, or should it be replaced by a fast mocked unit test of the candidates→SQS body?

**Assumption adopted:** The candidates→SQS contract boundary currently has no working test; either path is acceptable, a fast mocked unit test is preferred.

---

## OQ-3 — [Task1/myblog_music] Cognito app-client count for /candidates

**Question:** Does the Cognito user pool used by `/candidates` have more than one app client? If single-client, the missing audience/client_id check is low practical risk; if multi-client it should be added.

**Assumption adopted:** Treated as low-risk pending confirmation; recommend mirroring backend auth regardless for consistency.

---

## OQ-4 — [Task1/myblog_music] canonical prod SQS queue name

**Question:** Confirm the canonical prod SQS queue name (memory says standard `blogSQS`, README says `album-sync` FIFO+DLQ) so README/test can be corrected to match `infra/README.md`.

**Assumption adopted:** Standard `blogSQS` per memory/arch-audit; README/test are stale.

---

## OQ-5 — [Task1/myblog_music] pytest not runnable in this environment

**Question:** (Caveat, not a decision) pytest could not be executed here: the active interpreter is Python 3.10 and lacks cachetools/fastapi (CI uses 3.12). All findings are from static reading + git/grep, not a live test run.

**Assumption adopted:** Static evidence is sufficient for the findings reported; defer live verification to CI / prod smoke.

---

## OQ-6 — [Task1/myblog_front] /api/metrics/batch still live server-side?

**Question:** Is `POST /api/metrics/batch` still live server-side, or is it dead alongside the cancelled likes/comments feature? (finding #5 — if dead on the backend too, the route can be removed there.)

**Assumption adopted:** Likely vestigial (likes/comments dropped per roadmap memory); flag for backend audit rather than assume removal.

---

## OQ-7 — [Task1/myblog_front] genres page hardcoded sample graph

**Question:** The genres page (`src/pages/genres/index.astro`) renders hardcoded sample graph data; its own comment says it's an acknowledged spike. Confirm this is still the intended state given FEAT-genre-system Steps 0-4 already shipped real genre data to prod.

**Assumption adopted:** Intended spike → NOT reported as a Task1 finding. (Task3 R1 separately reports the reader-facing fake-data exposure as an H gap.)

---

## OQ-8 — [Task1/myblog_front] half-done music-search-core extraction

**Question:** Is the half-done music-search-core extraction (writer migrated, homepage `searchBarDb.client.ts` not — finding #3) intentional deferral or forgotten? Affects whether to schedule the migration vs just document the divergence.

**Assumption adopted:** Treated as an unfinished/forgotten extraction worth flagging; reported as 01 H4.

---

## OQ-9 — [Task1/myblog_worker] researchWorkerLambda has no research branch

**Question:** `researchWorkerLambda` (infra/lambda.tf:142) shares this exact handler+codebase fed by `researchSQS` (batch_size=1), but the worker has NO research-mode branch — a research message falls through to `logger.warning('Unknown message format')` and is deleted. Confirm the research executor genuinely lives outside this repo and no research traffic is meant to reach this handler.

**Assumption adopted:** MEMORY says the paid research Lambda is dormant (executor = local poller), so treated as expected, not dead routing.

---

## OQ-10 — [Task1/myblog_worker] account-wide Lambda concurrency tightness

**Question:** Does the account-wide Lambda concurrency/connection tightness (limit 10, per MEMORY) still hold? It is what elevates F1 (Spotify-in-transaction) from cosmetic to H.

**Assumption adopted:** Still holds. If the Neon connection pool is comfortably sized, F1 drops to M.

---

## OQ-11 — [Task1/myblog_worker] genre re-enrich gated on missing photo

**Question:** F10 (genres only re-enrich when photo is missing) assumes the Step-3 daily enrichment poller reliably backfills genres for already-photographed artists. The poller is outside this repo and could not be inspected. If it does not backfill, F10's correctness gap is wider than L.

**Assumption adopted:** The Step-3 poller backfills genres → F10 rated L.

---

## OQ-12 — [Task1/myblog_shared_db] backfill_genres.py + plist co-location

**Question:** Is `backfill_genres.py` + its launchd plist deliberately co-located in shared_db (next to the `genre_mapping` module it imports), or should the operational ETL/LLM pipeline move to `myblog_worker`? (F5)

**Assumption adopted:** (guess) possibly intentional co-location — flag, don't auto-move; keep the pure `genre_mapping.py` here regardless.

---

## OQ-13 — [Task1/myblog_shared_db] __init__.py export curation vs oversight

**Question:** Is the `__init__.py` export list curated on purpose (only 'primary' models), or is the omission of `Tag` and the four Spotify cache models an oversight? (F4)

**Assumption adopted:** Oversight (Tag is used by the shipped STAB-5 `Post.tags`); reported as 01 M17.

---

## OQ-14 — [Task1/myblog_shared_db] README per-service version table

**Question:** Should the README per-service version table be maintained at all, or replaced by a pointer to each service's requirements.txt since it will always rot? (F2)

**Assumption adopted:** It rots; recommend dropping the table for a per-service pointer (or regenerate from live requirements.txt).

---

## OQ-15 — [Task1/myblog_shared_db] canonical_schema.sql fidelity to prod

**Question:** Does `tests/canonical_schema.sql` faithfully mirror the live Neon prod schema? No local DB available to verify against prod.

**Assumption adopted:** Canonical is accurate. The Section.id BIGSERIAL finding (F1/01 H7) rests on this; if canonical itself is wrong the drift direction flips but a model↔canonical mismatch still exists.

---

## OQ-16 — [Task2/DB] Neon plan/tier of this project

**Question:** Is the prod `neondb` on Free vs Launch/Scale? Not determinable from inside the DB. Storage cost is negligible either way; the compute cost story differs.

**Assumption adopted:** Storage cost is negligible regardless of tier.

---

## OQ-17 — [Task2/DB] tracks(spotify_id) duplicate UNIQUE source of truth

**Question:** Is `uq_tracks_spotify_id` from a `V{N}__` SQL migration and `tracks_spotify_id_key` from an ORM `unique=True` (or vice-versa)? Cross-ref shared_db models/migrations before dropping one, via a human-approved migration.

**Assumption adopted:** A genuine redundancy; drop the one that is NOT the source of truth. No DDL performed in this review.

---

## OQ-18 — [Task2/DB] trgm GIN indexes warm-window measurement

**Question:** Should a deliberate multi-day warm-window measurement be scheduled to decide keep-vs-drop on the ~4.55 MB trgm GIN trio (0 scans in a 43-min window)?

**Assumption adopted:** They are load-bearing for `ILIKE … gin_trgm_ops` Korean recall → "0 scans" ≠ "safe to drop". Flag for measurement, do not drop.

---

## OQ-19 — [Task2/DB] track_artists artist→tracks reverse lookup

**Question:** Is there a hot `WHERE artist_id = ?` query on `track_artists` (10k-row table, 510 seq-scans/43min, no standalone `artist_id` index)?

**Assumption adopted:** Not hot today (speculative to index now); if FEAT-genre-artist-distribution makes it hot, add `idx_track_artists_artist_id`.

---

## OQ-20 — [Task2/DB] album_research prompt_version re-run policy

**Question:** How many prompt_versions will be retained? Each full re-run across the 983-album catalog adds ~7 MB.

**Assumption adopted:** Bounded, deliberate re-runs (not a leak); still years from any storage cap.

---

## OQ-21 — [Task2/DB] auth/multi-tenant tables present in prod — ✅ RESOLVED 2026-06-13

**Question:** The auth/multi-tenant tables (`user`/`session`/`organization`/`member`/`invitation`/`account`/`verification`/`jwks`/`project_config`) exist in `public`, all 0-row / 0-idx-scan. Are they intentionally present (FEAT-multi-user-accounts draft seeding / library bootstrap) or dead/forgotten DDL?

**Resolution (main-loop verification re-query, not an assumption):** The premise was wrong — they are **not in `public`**. They live in a dedicated **`neon_auth`** schema (the prod DB also carries platform schemas `auth` and `pgrst`). All 9 tables are 0-row. This is **Neon Auth** — Neon's managed authentication product, built on Stack Auth (hence the Better-Auth-shaped names). Evidence: `select table_schema, table_name from information_schema.tables where table_name in (...)` → every match in `neon_auth`; `public` has exactly 30 project tables, none of them auth tables. **Verdict:** platform-managed, **not** project DDL, **not** droppable via a `V{N}__` migration, **unrelated** to FEAT-multi-user-accounts. Action: none — disable from the Neon console if unwanted. `02-db-review.md` §3/§5/§8 corrected.

---

## OQ-22 — [Task3/UX] editorial critique accept now or hold?

**Question:** It's the defining feature but an unaccepted draft with an open cost OQ (first paid LLM usage on a $0-bias owner). Ship Phase 0 next, or keep it parked behind FEAT-genre-system Steps 5-7?

**Assumption adopted:** Owner decision required (rule #5 human-only accept). Reported as the #1 UX gap regardless.

---

## OQ-23 — [Task3/UX] /genres real-data wiring home

**Question:** Is FEAT-genre-system Step 6 the agreed home for R1, or should a thin "swap sample → `/api/genres/tree`" fix land sooner so readers stop seeing fiction now?

**Assumption adopted:** The gap is live in prod now; a thin earlier swap is the recommended stopgap, full wiring per Step 6.

---

## OQ-24 — [Task3/UX] public artist page scope vs multi-user

**Question:** Is the public artist page (R2) in scope before FEAT-multi-user-accounts, or bundled with it? The single-owner artist hub needs no auth/user model and the API is ready.

**Assumption adopted:** Decided-but-unbuilt, shippable solo now; NOT implicitly blocked on the multi-user RFC.

---

## OQ-25 — [Task3/UX] artist drill-in 24-album cap deliberate?

**Question:** Is the 24-album cap a deliberate writer-focus choice (keep the picker tight) or an unfinished follow-up? If deliberate, surfacing `album_count` ("24 of N") may be enough without full paging.

**Assumption adopted:** Unfinished follow-up (backend paging + counts already plumbed); reported as 03 W2/W3.

---

## OQ-26 — [Task3/UX] vestigial metrics/likes/comments remove or park

**Question:** Are comments/likes permanently dropped so the dead read endpoint + `post_comments`/`post_likes` tables can be cleaned?

**Assumption adopted:** Permanently dropped per roadmap memory; flagged for cleanup (cross-ref code-audit dead-code list).

---

## OQ-27 — [Task3/UX] "artist detail" interpretation + severity scaling

**Question:** (Assumptions, not decisions) (i) "artist detail" in the brief = the writer-only drill-in, since no public artist page exists; (ii) severities are scaled to a single-owner blog, so multi-user-only gaps (D27 PKCE) are rated L today.

**Assumption adopted:** As stated above.

---

## OQ-28 — [Task5] discovery bundle ordering (RSS + year-end + email)

**Question:** Should RSS (#1) + year-end (#2) + email (#3) be bundled as one "reader-discovery v1" effort, or sequenced (RSS first, since email bridges off it)?

**Assumption adopted:** They share a content-collection foundation; RSS-first sequencing is the natural order.

---

## OQ-29 — [Task5] email subscribe provider choice

**Question:** Does the $0-bias owner accept an external SaaS dependency (Buttondown/Substack/Stibee, the S path) or insist on a self-hosted SES list (the M path with ops cost)?

**Assumption adopted:** Provider route is the S/recommended path; build size depends entirely on this answer.

---

## OQ-30 — [Task5] public artist page shippable solo now?

**Question:** Is the public artist page (#4) shippable solo now over the existing unauthed API, or implicitly held behind FEAT-multi-user-accounts? (Mirrors OQ-24.)

**Assumption adopted:** Decided-but-unbuilt, not frozen; API + data are done and need no user model.

---

## OQ-31 — [Task5] year-end list + archive search value at editorial scale

**Question:** Year-end list (#2) and review-archive search (#6) have near-zero value at today's editorial scale (1 published post). Build now as scaffolding, or defer until N reviews exist?

**Assumption adopted:** Cheap to build but inert until content lands; tied to the "hand-publish ≥1 real review first" precondition.

---

## OQ-32 — [Task5] refactor-vs-feature appetite (necessity gate)

**Question:** Which of #12/#13/#14/#16 clear the necessity-gate bar ("name concrete harm-if-unfixed") for the owner today vs. which are gold-plating to defer?

**Assumption adopted:** Presented as options, not recommendations. (#14 worker hot-path is reliability-load-bearing; #16 is pure low-risk subtraction.)

---

## OQ-33 — [Task5] album-of-the-month rail + tag/section pages scope collision

**Question:** Do #8 (album-of-the-month rail) and #7 (tag/section landing pages) risk overlapping/colliding with FEAT-genre-system Steps 5-7 scope (the genre `/reviews` filter, frozen sub-genre work)?

**Assumption adopted:** Scoped to tags/sections to avoid the genre lane; boundary worth confirming.

---

## OQ-34 — [Task4] defunct-Substack substitutions

**Question:** The brief's examples Music Journalism Insider (ended Dec 2023) and Penny Fractions (sunset late 2023) are BOTH defunct, replaced with verified-active Hearing Things and First Floor. Domestic stew! (ended 2026-03-15) replaced by 재즈피플. Confirm these substitutions are acceptable.

**Assumption adopted:** Substitutions acceptable; verified-active picks chosen.

---

## OQ-35 — [Task4] Pitchfork format/RSS unverifiable

**Question:** Pitchfork's exact current review length/section structure and whether RSS/email newsletter still exist — pitchfork.com is unfetchable (403); evidenced only via Metacritic mirror.

**Assumption adopted:** Length ~600–1500 words (guess); RSS/email existence unverified.

---

## OQ-36 — [Task4] The Quietus word counts + Metacritic "80"

**Question:** The Quietus per-review word counts and the precise meaning of Metacritic's uniform "80" — thequietus.com returns 403 to WebFetch.

**Assumption adopted:** Unscored (essayistic); Metacritic assigns a default for unscored pubs (guess).

---

## OQ-37 — [Task4] Bandcamp Daily editorial search/RSS/email

**Question:** Bandcamp Daily editorial-side search/RSS/email availability (as distinct from the Bandcamp commerce platform's fan accounts) not confirmed on fetched pages.

**Assumption adopted:** Editorial RSS/search/email standard but unverified.

---

## OQ-38 — [Task4] Hearing Things dates + year-end lists

**Question:** Hearing Things per-article publication dates and whether it runs year-end lists — homepage showed no dates.

**Assumption adopted:** June 2026 inferred from 'Pride Month' framing (guess); year-end lists likely given ex-Pitchfork DNA (guess, unverified).

---

## OQ-39 — [Task4] First Floor paid-tier price

**Question:** First Floor's exact paid-tier price not captured on the fetched archive page (unverified).

**Assumption adopted:** Substack paid subscription confirmed; exact price unverified.

---

## OQ-40 — [Task4] Bandcamp ownership secondary-source conflict

**Question:** One blog claimed a 2024 Beatport sale and that Bandcamp Daily 'went quiet' — both rejected in favor of primary sources confirming continued Songtradr ownership and active June 2026 publishing.

**Assumption adopted:** Songtradr ownership + active publishing (primary sources). Confirm against a 2026-dated primary source if a precise legal owner name is needed.

---

## OQ-41 — [Task4] 음악취향Y business/revenue model

**Question:** 음악취향Y business/revenue model is unconfirmed — no paywall/ads/donation widget found in fetched HTML; the volunteer critic-collective model is a guess.

**Assumption adopted:** Volunteer critic-collective (guess); needs the site's About page or a press interview to confirm.

---

## OQ-42 — [Task4] 음악취향Y album star scale

**Question:** 음악취향Y's exact album-review star scale (claimed 0-5) is a WebSearch synthesis, not a single quoted scale graphic.

**Assumption adopted:** 0–5 stars (unverified); should be confirmed against an actual Album-Out review page showing the score widget.

---

## OQ-43 — [Task4] 음악취향Y RSS/subscribe

**Question:** No RSS or newsletter marker was found in the fetched HTML; whether any subscribe/RSS exists is unconfirmed.

**Assumption adopted:** RSS/subscribe absent or unconfirmed (this absence is itself cited as a "dated" signal vs IZM).

---

## OQ-44 — [Task4] 재즈피플 review scoring format

**Question:** Whether the 재즈피플 print magazine assigns numeric/star scores to album reviews is unverifiable from public web pages (content is print-gated).

**Assumption adopted:** Score format unverifiable; would need a physical/scanned issue.

---

## OQ-45 — [Task4] 재즈피플 year-end feature

**Question:** 재즈피플 year-end feature (best jazz albums of the year): plausible for a monthly mag but not directly evidenced.

**Assumption adopted:** Unconfirmed.

---

## OQ-46 — [Task4] weiv (웨이브) HTTP 500

**Question:** weiv returned HTTP 500 on every fetch this session — could be transient or US-geoblocking rather than truly down.

**Assumption adopted:** Treated as fading/excluded; a KR-vantage retry would confirm whether it has any 2025-2026 posts before fully writing it off.

---

## OQ-47 — [Task4] IZM current revenue

**Question:** IZM's current (vs historical) revenue is inferred — the FAQ-cited Samyang Chemical patronage + free office is the documented funding, but whether IZM now earns from podcast/YouTube/merch is a guess.

**Assumption adopted:** Patronage + donated office (documented); adjacent podcast/YouTube/merch revenue is a guess.

---

## OQ-48 — [Task4] Korean-vantage WebSearch caveat

**Question:** WebSearch here is US-only and several outlet pages are JS-rendered SPAs/ASP; date/title extraction relied on curl HTML parsing. A KR-locale crawl could surface additional active outlets (디깅클럽서울/사운드네트워크/비웨이브/한국대중음악상 site) this pass did not fully verify.

**Assumption adopted:** Surveyed set is representative; KR-locale crawl deferred as a follow-up.
