# Plan

Active workspace tracker for cross-repo work. Each row carries `Scope / Order (if multi-repo) / Verification (local + prod smoke) / Rollback / Status`; RFC-backed entries collapse to a one-line pointer at `docs/rfcs/<id>-<slug>.md`. When a row finishes, drop it — `git log` and `docs/archive/done/YYYY-MM.md` are authoritative for history.

---

## Active

_(none)_

---

## Backlog

### BUG-14: MusicBrainz search 가 한글 artist name 을 못 잡음 — P2

- Scope: `myblog_worker` (MB lookup) — 잠재적으로 `myblog_music` (검색 fallback)
- 증상: 예 — '아이유' / '조용히' 검색 시 MB API 가 NO RESULTS. canonical 영문 표기 ('IU' / 'Jo Yong-pil') 로만 hit.
- 추정 원인: MB 의 한국어 alias 인덱싱 빈약 + 현 lookup 이 query 그대로 보냄. canonical 영문/한국어 alias fallback 미구현.
- 영향: K-pop / 국내 artist 의 `musicbrainz_id` 채움률 저조 → alias_fill 잡이 'not_found' sentinel 만 채우는 경우 다수.
- 방향(미확정): (1) Spotify artist name 의 latinized alias 를 검색 키로 fallback, (2) MB `alias:` 검색 연산자 명시 사용, (3) 사내 한↔영 alias 매핑 테이블.
- Status: ⚪ backlog

### BUG-15: MusicBrainz search false-match (예: Big Bang → Big Country, score=100) — P2

- Scope: `myblog_worker` (MB scoring/filter)
- 증상: 'Big Bang' (K-pop) 검색 시 'Big Country' (GB rock band) 가 score=100 으로 first hit. 현 `_MIN_SCORE=90` 컷오프로는 못 거름.
- 추정 원인: MB score 가 name 토큰 매칭만으로 100 을 뱉음. country / disambiguation / type 가중치 미반영.
- 방향(미확정): (1) Spotify country/genre 와 cross-check (Spotify 가 KR/k-pop 인데 MB 후보가 GB rock → 거절), (2) MB `country:` / `tag:` 필터 추가, (3) disambiguation 텍스트로 secondary filter.
- 영향: 잘못된 `musicbrainz_id` 박힘 → alias_fill 로 엉뚱한 alias 채워짐 → 검색 품질 저하.
- Status: ⚪ backlog
