# BUG-14: MusicBrainz hangul alias coverage — switch artist search to Lucene `query=`

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-30
- **Plan row**: `plan.md` → BUG-14

---

## Goal

`worker/clients/musicbrainz_client.py` 의 artist lookup 이 한글 name (예: 아이유 / 방탄소년단 / 정국) 을 MB 의 alias 인덱스를 통해 찾아낸다. 결과적으로 `artists.musicbrainz_id` 의 hangul-name 행 not_found 비율이 현재 62% 에서 비-hangul 수준 (≤30%) 으로 내려간다. BUG-15 의 cross-check (Step 1) 와 hangul-tiebreaker (Step 4) 게이트는 변경 없이 그대로 작동한다.

## Non-goals

- Spotify latinized form 자동 생성 (transliteration / 다른 locale API) — backlog 방향 (1) 영역, 본 RFC 잔존 분석 후 별도 RFC 로 결정.
- 사내 한↔영 매핑 테이블 — backlog 방향 (3) 영역, 동일.
- BUG-15 의 cross-check / Step 4 / Step 5 의 거절 알고리즘 변경. 본 RFC 는 *후보 모집* 단계만 손댐.
- 이미 채워진 musicbrainz_id (sentinel 아님) 의 sweep / 재검증.

## Current state

`worker/clients/musicbrainz_client.py:107`:

```python
result = musicbrainzngs.search_artists(artist=name, limit=10)
```

`musicbrainzngs.search_artists(artist=X, ...)` 은 내부적으로 `artist:"X"` Lucene 쿼리를 만든다. MB 의 `artist` 필드 인덱스는 primary name + sort name 중심이라 한글 alias 가 잘 안 잡힘.

prod 측정 (2026-05-30, `artists` 테이블 877행):

| 그룹 | 행수 | mbid set | not_found | NULL |
|---|---|---|---|---|
| 전체 | 877 | 490 | 281 | 106 |
| **hangul name** | **236** | 78 | **126 (62% 실패)** | 32 |
| non-hangul | 641 | 412 | 155 (27% 실패) | 74 |

`name ~ '[가-힣]'` 필터. hangul 실패율이 비-hangul 의 약 2.3 배.

MB API 직접 호출 sample (5 아티스트, 2026-05-30):

| 쿼리 syntax | 결과 |
|---|---|
| `artist:아이유` (현 동작) | count=0 |
| `query=아이유` (bare Lucene, 디폴트 필드 union) | IU score=100 KR Person |
| `alias:아이유` | IU score=100 KR Person |
| `alias:방탄소년단` | BTS score=100 KR |
| `alias:정국` | Jung Kook score=100 KR |
| `alias:보아` | BoA score=100 KR |
| `alias:헤이즈` | Heize score=100 KR |

5/5 hit, 전부 score=100, 전부 country=KR. MB 의 한글 alias 인덱스는 사용가능, 현 호출이 alias 필드를 조회 대상에 안 넣고 있을 뿐.

## Target state

`worker/clients/musicbrainz_client.py` 의 search 호출이 `query=` 자유형 Lucene 쿼리로 전환되어 default 필드 union (artist + sort name + alias 등) 을 모두 검색한다. 호출자 / 게이트 / sentinel 동작 변경 없음.

후보 모집이 늘어남에 따라:
- BUG-15 Step 1 cross-check (country hint 불일치 거절) 는 동일하게 작동, 더 많은 후보를 거를 수도 있음.
- BUG-15 Step 4 hangul-tiebreaker (alias 한글 보유 요구) 는 한글 alias 후보를 더 많이 끌어와 *완화 방향* 으로 영향 — 가짜 KR 후보가 줄어드는 게 아니라 진짜 KR 후보가 늘어남.

이후 prod 의 hangul not_found 126행 중 sentinel 만 mini-reset 하여 EventBridge alias_fill 이 재lookup 하도록 하고, 1-2 사이클 후 회복률을 측정해 잔존 패턴을 분석한다.

## Steps

### Step 1 — `artist=` → `query=` + Lucene escape (single PR)

**변경**:

1. `worker/clients/musicbrainz_client.py:107` 의 호출 변경:
   ```python
   result = musicbrainzngs.search_artists(query=_escape_lucene(name), limit=10)
   ```
2. `_escape_lucene` helper 추가 — Lucene 특수문자 escape:
   ```python
   _LUCENE_SPECIAL = r'+-&|!(){}[]^"~*?:\/'
   def _escape_lucene(s: str) -> str:
       return "".join("\\" + c if c in _LUCENE_SPECIAL else c for c in s)
   ```
   AND/OR/NOT 같은 boolean operator 단어는 단일 토큰으로 들어오면 무해 (대문자 전부 일치 시에만 Lucene 이 reserved 처리, 통상 artist name 은 아님). 필요 시 후속.
3. 기존 cross-check / sentinel / tiebreaker / Step 5 revert 동작은 unchanged. `search_artists` 결과 구조 (`artist-list`) 도 동일.

**Verification**:
- Unit 테스트 추가:
  - `_escape_lucene` 가 Lucene 특수문자 모두 backslash escape.
  - `fetch_artist_mbid_and_aliases` 의 search_artists 호출 인자가 `query=<escaped name>` 인지 mock 으로 확인.
- 통합 테스트 (live MB API, opt-in via env flag — 1 req/s 제한 준수):
  - `name='아이유'` → mbid=`b9545342-1e6d-4dae-84ac-013374ad8d7c` (IU), aliases 한글 포함.
  - `name='IU'` → 동일 mbid (regression — 영문 name 도 그대로 hit).
  - `name='Big Bang'` → 후보 모집 됨 (정확 mbid 는 BUG-15 cross-check 의 영역).
- worker repo `pytest`:
  ```bash
  cd myblog_worker && pytest tests/test_musicbrainz_client.py -v
  ```

**Rollback**: PR revert. helper 1개 + 1줄 호출 변경. 데이터 mutation 없음. (Step 2 mini-reset 은 별도.)

---

### Step 2 — hangul not_found mini-reset + prod 사이클 관찰 (Step 1 머지 + prod 정상 확인 후)

**전제**: Step 1 prod smoke 통과 + EventBridge 1-2 사이클 정상 (cross-check / tiebreaker 거절 로그가 폭증 안 함, false-match 신규 행 없음).

**변경**: `scripts/bug14-step2-mini-reset.sql` 작성 — `musicbrainz_id = 'not_found'` AND `name ~ '[가-힣]'` 행 (126행) 의 `musicbrainz_id` 를 NULL 로 되돌림. EventBridge alias_fill 은 NULL 만 처리하므로 sentinel 행은 재시도되지 않음.

```sql
BEGIN;
\set ON_ERROR_STOP on
-- 백업
\copy (SELECT id, spotify_id, name, musicbrainz_id FROM artists WHERE musicbrainz_id = 'not_found' AND name ~ '[가-힣]') TO '/tmp/bug14-step2-reset-backup-YYYYMMDD-HHMMSS.csv' CSV HEADER;
-- reset
UPDATE artists SET musicbrainz_id = NULL WHERE musicbrainz_id = 'not_found' AND name ~ '[가-힣]';
COMMIT;
```

[[reference-database-url-psql]] 패턴.

**Verification**:
- pre-reset count = post-reset NULL 추가분.
- EventBridge alias_fill 1-2 사이클 후 (현 주기 확인 필요, infra/eventbridge.tf):
  ```sql
  SELECT
    SUM((musicbrainz_id IS NULL)::int) AS still_null,
    SUM((musicbrainz_id = 'not_found')::int) AS new_not_found,
    SUM((musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found')::int) AS recovered
  FROM artists WHERE name ~ '[가-힣]';
  ```
- 회복률 목표: ≥50% (126 → ≥63 recovered). 미달 시 잔존 패턴 분석 (Step 3 트리거).

**Rollback**: 백업 CSV 로 복구.

---

### Step 3 (조건부) — 잔존 분석 → backlog 방향 (1)/(3) 또는 BUG-14 종료

Step 2 1-2 사이클 후:
- 회복률 ≥80%: BUG-14 종료, plan 행 드롭.
- 회복률 50-80%: 잔존 not_found 행의 패턴 검사 (Spotify name 형태 / 장르 / popularity). 일관된 패턴 (예: 매우 짧은 alias only, romanization 변종) 이면 별도 RFC.
- 회복률 <50%: 가설 (`alias` 인덱스 커버리지 = 핵심) 재검토. backlog 방향 (1) 또는 (3) RFC 작성.

본 단계는 별도 RFC 또는 BUG-14 종료 — 코드/데이터 mutation 없음.

---

## Open questions

1. **Lucene boolean keyword 충돌** — artist name 이 정확히 `AND` / `OR` / `NOT` (대문자 전부) 인 케이스가 prod 에 있나? — 점검 SQL: `SELECT id, name FROM artists WHERE name IN ('AND','OR','NOT');`. 있으면 escape 추가, 없으면 무시. **Blocks Step 1 verification 설계만, 머지 안 막음** — 실측 후 결정.

2. **EventBridge alias_fill 주기** — Step 2 사이클 관찰 시 1 사이클이 몇 분/시간인지 확인 (`infra/eventbridge.tf`). Step 2 Verification 의 측정 타이밍에 영향.

3. **통합 테스트 opt-in flag 이름** — 기존 worker 테스트에 live MB 호출 패턴 있나? 있으면 동일 flag 재사용. Step 1 PR 작성 시 확인.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-30 | RFC 시작 — backlog 방향 (2) MB `alias:` 채택. 근거: 5/5 sample 의 직접 MB API 호출에서 `alias:` 가 score=100 hit, 현재 `artist:` 는 count=0. (1) latinized fallback 은 Spotify API 가 인공 latinized form 안 줘 transliteration 별도 필요, (3) 매핑 테이블은 운영 비용 큼. 둘 다 잔존 분석 (Step 3) 후 결정. [[feedback-alias-search-availability]] 와 정합 — query union 은 strictly more candidates 라 검색 가용성 ↑. | 0 |
