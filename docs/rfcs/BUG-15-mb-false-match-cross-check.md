# BUG-15: MusicBrainz false-match — Spotify-genre cross-check filter

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: `plan.md` → BUG-15

---

## Goal

`worker/clients/musicbrainz_client.py` 의 artist lookup 이 score=100 인 후보라도 **Spotify 가 알려준 장르와 region 이 어긋나면** 거절한다. 'Big Bang' (K-pop, Spotify genres=["k-pop"]) → 'Big Country' (GB rock, MB country=GB) false-match 가 다시 일어나지 않고, alias_fill 이 엉뚱한 `musicbrainz_id` 를 박지 않는다.

## Non-goals

- BUG-14 (한글 artist name 자체가 MB 에서 안 잡히는 문제) 는 별개 RFC.
- MB API 자체의 score 알고리즘 변경 (불가).
- Country/tag 정보가 전무한 artist 에 대해 더 적극적인 거절 (false-negative 키우기).
- 과거 false-match 로 채워진 행 전체 sweep (Step 2 에서 known case 만 처리).
- 사내 한↔영 alias 매핑 테이블 도입 (BUG-14 scope).

## Current state

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`

1. `fetch_artist_mbid_and_aliases(name: str)` (line 21–62):
   - `musicbrainzngs.search_artists(artist=name, limit=1)` — top 1 후보만.
   - `score = int(best.get("ext:score", 0))`; `score < _MIN_SCORE (=90)` 이면 sentinel `MBID_NOT_FOUND` 반환.
   - score 만족 시 `get_artist_by_id(mbid, includes=["aliases"])` 로 alias 채워 반환.
2. **호출자**: `myblog_worker/worker/service/sync_service.py:generate_and_save_aliases` (line 249–299).
   - 배치 10개 행 (`SELECT spotify_id, name FROM artists WHERE musicbrainz_id IS NULL LIMIT 10`).
   - `mbid, aliases = fetch_artist_mbid_and_aliases(name)` — **`name` 만** 전달, Spotify 가 갖고 있는 `genres` JSONB 미사용.
3. **Artist row 가 갖고 있는 cross-check 가능 데이터** (`myblog_shared_db/src/myblog_shared_db/models.py:96+`):
   - `genres: JSONB` (Spotify-derived, 예: `["k-pop"]`, `["british rock", "rock"]`)
   - `popularity`, `followers` — 신호 약함
   - artist-level country 없음 (Spotify 미제공)

→ MB search 가 score=100 으로 같은 토큰의 다른 band 를 반환하면 그대로 통과. `musicbrainz_id` 가 박히고 alias_fill 이 GB rock band 의 alias 를 K-pop artist 행에 덮어씀. 사용자가 알기 어려운 silent data corruption.

**알려진 incident**: 'Big Bang' (KR) → 'Big Country' (GB) 매칭 (score=100, type=Group, country=GB).

## Target state

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`

1. `fetch_artist_mbid_and_aliases(name, spotify_genres=None)` — 호출자가 Spotify genres 를 함께 넘긴다 (default `None` 으로 backwards compat).
2. MB search `limit=10` 으로 변경 (1 API call, 응답 payload 만 커짐).
3. 후보를 score 내림차순으로 순회하며:
   - score < `_MIN_SCORE` → 컷 (현행 유지).
   - cross-check 통과 시 그 후보 채택.
   - 모두 거절되면 `MBID_NOT_FOUND` 반환.
4. **Cross-check 함수** `_is_plausible_match(candidate: dict, spotify_genres: list[str]) -> bool`:
   - Spotify genres → country hint 추출 (`_country_hint_from_genres`).
     - 예: `"k-pop"`, `"korean"` → `"KR"` / `"j-pop"`, `"japanese"` → `"JP"` / `"british …"`, `"uk …"` → `"GB"` / `"american …"`, `"us …"` → `"US"`.
     - 매핑 못 잡으면 `None`.
   - hint 가 `None` 이거나 candidate 에 `country` 가 없으면 → `True` (cross-check 미적용, 현행과 동일).
   - hint 와 candidate `country` 가 다르면 → `False` (거절).
   - 같으면 → `True`.
5. **호출자 변경** (`sync_service.py:generate_and_save_aliases`):
   - SELECT 에 `genres` 추가.
   - 호출 시 `fetch_artist_mbid_and_aliases(name, spotify_genres=row.genres)`.
6. **로깅**: 거절된 후보는 `logger.info("MB cross-check reject: name=%s candidate=%s candidate_country=%s hint=%s", ...)` — prod CloudWatch 에서 hit rate 관찰 가능.

## Steps

### Step 1 — MB client cross-check + 호출자 plumbing (single PR)

`myblog_worker` 단독. 한 PR 에 다음을 묶는다 (cross-check 만 따로 머지하면 호출자가 genres 안 넘겨서 dead code).

- `musicbrainz_client.py`:
  - `_COUNTRY_HINTS` 상수 dict (genre substring → ISO country code). 초기 매핑은 K-pop / J-pop / British / American 4종.
  - `_country_hint_from_genres(genres: list[str]) -> Optional[str]`.
  - `_is_plausible_match(candidate, spotify_genres) -> bool`.
  - `fetch_artist_mbid_and_aliases` signature 에 `spotify_genres: Optional[list[str]] = None` 추가, `limit=10` 변경, 후보 iterate 로직.
- `sync_service.py:generate_and_save_aliases`:
  - SELECT `spotify_id, name, genres` (현재 `spotify_id, name` 만).
  - `fetch_artist_mbid_and_aliases(name, spotify_genres=genres or [])`.
- 신규 단위 테스트 (`tests/test_musicbrainz_client.py` 신설):
  - `_country_hint_from_genres` 매핑 테이블 (k-pop → KR, british rock → GB, 빈 list → None).
  - `_is_plausible_match` 조합표 (hint=KR / candidate.country=GB → False; hint=None / 무엇이든 → True; candidate.country 없음 / 무엇이든 → True).
  - `fetch_artist_mbid_and_aliases` mock (`musicbrainzngs.search_artists` patch) 로 'Big Bang' (Spotify genres=["k-pop"]) 시나리오: 1st 후보 country=GB → reject, 2nd 후보 country=KR (or country 없음) → accept. 모두 reject 시 `MBID_NOT_FOUND`.

**Verification**:
```
cd myblog_worker && pytest tests/test_musicbrainz_client.py tests/test_sync_service.py -v
ruff check worker/
```

Local smoke (DB optional): `pytest` + `ruff` 통과 + cross-check 로직 단위 테스트 그린이면 충분 — alias_fill 은 EventBridge 트리거라 prod 검증으로 최종 확인 ([[feedback-local-db-smoke-fallback]]).

**Rollback**: PR revert. 호출자가 `spotify_genres` 안 넘기던 시점으로 되돌리고 limit=1 복구. 데이터 mutation 없음.

---

### Step 3 — Korean hint widening (2026-05-29 BUG-18 prod smoke 후속, 우선순위 상승)

**배경**: BUG-18 Step 1 머지 후 prod EventBridge 1 사이클 (2026-05-29 01:06 UTC) 결과, stuck 3행 (`j-hope` / `Kim Tae Hoon` / `dj friz`) 이 sentinel 이 아니라 또 다른 false-match MBID 로 교체됨. 원인 = 한국 아티스트의 `artists.genres` 가 ko-KR localized → `_COUNTRY_HINTS` 영문 needle (`"k-pop"`, `"korean"`) 이 안 잡힘 → `_country_hint_from_genres` None 반환 → cross-check 비활성 → MB top-N 통과. BUG-18 의 pre-check 가 UNIQUE collision 가드를 우회시킨 부작용으로 데이터 정확성 악화.

이 Step 은 원래 RFC §Open Q1 의 "prod 로그 보며 늘림" 결정에 따라 미뤄둔 후행 작업. BUG-18 prod 데이터 도착으로 트리거됨.

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`

**prod 빈도 분석** (`SELECT g.token, count(*) FROM artists, jsonb_array_elements_text(genres) AS g(token) WHERE g.token ~ '[가-힣]' GROUP BY g.token`):

| 한국어 토큰 | 빈도 | 추정 hint |
|---|---|---|
| 한국 랩 | 253 | KR |
| K-발라드 | 91 | KR |
| 케이팝 | 49 | KR |
| 한국 록 | 35 | KR |
| 일본 vgm | 3 | JP (보류) |
| 시부야계 | 2 | JP (보류) |

K + R 카테고리만 1차 — 428행 영향. JP / CN / 기타는 다음 라운드 (false-positive 위험 평가 후).

**변경**: `_COUNTRY_HINTS` 에 한국어 needle 3개 추가 (모두 KR):
- `("한국", "KR")` — substring 매치로 "한국 랩" / "한국 록" 둘 다 잡음 (288행)
- `("케이팝", "KR")` — 49행
- `("k-발라드", "KR")` — 91행 (영문 prefix + 한국어 mix, 별도 needle 필요)

`_country_hint_from_genres` 의 기존 로직 변경 없음 (`for ... in genres: for needle, code in _COUNTRY_HINTS: if needle in gl: return code`). 단순 needle 추가.

**테스트** (`tests/test_musicbrainz_client.py`):
- `_country_hint_from_genres` parametrize 에 추가: `(["한국 랩"], "KR")`, `(["케이팝"], "KR")`, `(["K-발라드"], "KR")`, `(["한국 록", "K-발라드"], "KR")`, `(["일본 vgm"], None)` (JP 는 아직 미추가).
- 기존 영문 케이스 회귀 보호.

**Verification**:
```
cd myblog_worker && pytest tests/test_musicbrainz_client.py -v
```

**Prod smoke** (post-merge, EventBridge 1주기):
- CloudWatch 필터 `"MB cross-check reject"` 가 한국어 토큰 행에서 발화 (LOG_LEVEL=INFO 필요 — BUG-18 §Prod smoke step 0 와 같은 전제).
- DB:
  ```sql
  -- 다음 사이클 처리 행 중 한국어 genres 가 있고 cross-check 작동했는지
  SELECT spotify_id, name, musicbrainz_id, genres
    FROM artists
   WHERE genres @> '["한국 랩"]'::jsonb OR genres @> '["케이팝"]'::jsonb
   ORDER BY name LIMIT 30;
  ```

**Rollback**: PR revert. needle 3개 추가만이라 데이터 mutation 없음 (단, Step 2 reset 은 별도).

---

### Step 2 — known false-match 행 reset (Step 3 머지 + prod 관찰 후)

prod 에서 Step 1 의 cross-check reject 로그가 정상 작동함을 확인한 다음에만 실행. EventBridge alias_fill 은 `musicbrainz_id IS NULL` 만 처리하므로 known bad 행은 NULL 로 되돌려야 재시도.

- SQL:
  ```sql
  -- 사전에 SELECT 로 row 확인 후 UPDATE
  UPDATE artists
     SET musicbrainz_id = NULL,
         aliases        = '[]'::jsonb
   WHERE spotify_id IN (:bad_spotify_ids);
  ```
- 대상 후보 선정 방법:
  - 시작은 known incident ('Big Bang' Spotify ID) 만.
  - 추가로 prod SELECT 로 "Spotify genres 에 k-pop / korean / j-pop / japanese 포함 AND musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found'" 인 행을 추출하고, 표본 점검 후 결정 (자동 일괄 NULL 화는 false-positive 위험).
- 다음 EventBridge 사이클에서 Step 1 의 cross-check 가 재lookup 한다.

**Verification**:
```
-- prod DB
SELECT spotify_id, name, musicbrainz_id, aliases
  FROM artists
 WHERE spotify_id IN (:bad_spotify_ids);
-- → musicbrainz_id NULL, aliases [] 인지 확인.
```
EventBridge 1주기 후 (cron 빈도 → `infra/README.md`):
```
SELECT spotify_id, name, musicbrainz_id, aliases
  FROM artists
 WHERE spotify_id IN (:bad_spotify_ids);
-- → 'not_found' (cross-check 거절 결과) 또는 올바른 MBID 채워졌는지 확인.
```

**Rollback**: 사전 SELECT 결과를 미리 캡쳐해 두고, 잘못된 NULL 화 발생 시 원본 값으로 UPDATE 복구.

---

## Open questions

1. **`_COUNTRY_HINTS` 초기 매핑 범위** — K-pop / J-pop / British / American 4종으로 시작하고 prod 로그 보며 늘릴지, 시작부터 더 넓게 잡을지. (Step 1 영향. 좁게 시작 추천 — false-negative 줄이기 우선.) **2026-05-29 결정**: 좁게 시작이 prod 에서 부정 효과 (한국 아티스트의 ko-KR localized genres → cross-check 비활성 → false-match 통과). Step 3 (Korean hint widening) 으로 추가. [[project-prod-artists-genres-korean]] 확인.
2. **cross-check 거절 시 sentinel `MBID_NOT_FOUND` 박기 vs NULL 유지** — 현재 RFC 안은 sentinel 박음 (rate limit 보호). NULL 유지 시 다음 EventBridge 사이클에서 재query 하지만 결과 동일 → 무한 재query. **결정: sentinel 박음.** 단점은 향후 매핑 늘려도 자동 재시도 안 됨 → Step 2 와 동일하게 수동 reset 필요. (Step 1 영향.)
3. **`_MIN_SCORE` 유지 여부** — cross-check 통과면 score floor 낮춰도 안전한가? **잠정 결정: 유지.** cross-check 는 추가 게이트일 뿐 score 신뢰는 변하지 않음. (Step 1 영향.)
4. **Step 2 의 자동 sweep vs known case only** — 위 RFC 는 known case 만. 자동 sweep 은 false-positive (정상 매치까지 NULL 화) 위험 → SELECT 로 표본 점검 단계 의무화. (Step 2 영향.)
5. **테스트에서 musicbrainzngs 응답 fixture** — 실제 prod 응답 1건을 sanitized JSON 으로 저장해 두는 게 mock 구조 일치에 안전. fixture 위치는 `tests/fixtures/mb_bigbang_search.json`. (Step 1 영향.)

## Decisions log

| Date       | Decision                                                                                                    | Step |
|------------|-------------------------------------------------------------------------------------------------------------|------|
| 2026-05-29 | Cross-check 1차 신호로 Spotify genres → country hint 매핑 채택 (Spotify 가 artist-level country 미제공이라). | 1    |
| 2026-05-29 | Tag/disambiguation 가중치는 1차 범위에서 제외 (false-negative 위험 + 매핑 룰 폭발).                          | 1    |
| 2026-05-29 | limit=1 → 10. 1 API call 로 동일하므로 rate limit 영향 없음.                                                | 1    |
| 2026-05-29 | Step 3 (Korean hint widening) 추가 — BUG-18 prod smoke (01:06 UTC) 의 false-match 누적 가속화 부작용으로 우선순위 P1. needle 추가: `"한국"` / `"케이팝"` / `"k-발라드"` → KR. JP/CN 등은 다음 라운드. | 3 |
| 2026-05-29 | Step 2 (known-bad row reset) 활성화 — Step 3 머지 + 1 사이클 관찰 후. 대상은 K* genres + musicbrainz_id NOT NULL && != 'not_found'. 사전 SELECT 캡처 의무. | 2 |
