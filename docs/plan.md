# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

### FEAT-view-redesign: Article read page → Lowfreq parity + rating / search / writer fixes

- RFC: `docs/rfcs/FEAT-view-redesign.md` (Status: draft — awaiting human accept, rule #5)
- Trigger fired 2026-05-31: Lowfreq Article design bundle arrived (sibling of closed FEAT-writer-lowfreq-redesign)
- Scope: search sectioning (front) · recommended → ★ pick model (front+backend, contract) · continuous rating `Numeric(3,2)` (shared_db→backend→front) · publish-checklist removal (front) · Lowfreq Article read page (front) · accent picker (additive) · "Appears On" (deferred)
- Order: Steps 1/2 independent (front-only); Step 3 + Step 4 before Step 5; Step 4 cross-repo strict order (migration→prod apply→backend pin); one step per session (rule #4)
- Status: 🟡 RFC draft written, awaiting accept

_(FEAT-writer-lowfreq-redesign closed 2026-05-31, all 6 steps shipped end-to-end. See `docs/rfcs/FEAT-writer-lowfreq-redesign.md` or `git log` for merge commits across all repos.)_

---

## Backlog

_(none — BUG-16 Step 2 closed 2026-05-30: Neon test-db credential rotated via Neon API, stores synced, leaked credential dead. See git log + docs/archive/done/2026-05.md)_

---

## Later (트리거 대기)

_(none — FEAT-view-redesign trigger fired 2026-05-31, promoted to Active.)_

---

## Frozen (아이디어만, RFC 없음)

확장 기능 후보. 의향 생기면 그때 RFC 시작. 지금 아무것도 안 함.

- **FEAT-spotify-personalize-light** (K) — 1인용 약식: OAuth 1회 → refresh token → Secrets → EventBridge 주기 fetch → `/api/music/recommendations/my-top` → write 사이드바
- **FEAT-new-release-feed** (L) — EventBridge 주기 → 본인 review artist 의 최근 앨범 fetch → `artist_new_releases` → `/api/music/feed/new-releases` → 메인 카드
