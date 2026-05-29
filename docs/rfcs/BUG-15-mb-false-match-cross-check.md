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

### Step 4 — country=NULL pass-through tiebreaker (2026-05-29 Step 2 reset 후속)

**Status**: accepted (사용자 OK 2026-05-29).

**배경**: Step 2 reset +1h31m 표본 점검 (86행 중 ~6 사이클 처리분) 에서, hint=KR + candidate.country=NULL 조합의 sticky false-match 가 ≥6행 관찰됨.

| Spotify | Spotify genres | 잔존 alias | 진짜 가리키는 인물 |
|---|---|---|---|
| V.I | `["케이팝"]` | "Shizzy Sixx", "Suicide Sixx" | Big Bang 승리 (별도 row 정상 매치) |
| JA$ | `["한국 랩"]` | "Jah", "Jeffrey Atkins" | Ja Rule (US) |
| SUGA | `["한국 랩"]` | "Dajuan L. Walker" | BTS 슈가 |
| Jimmy Paige | `["한국 랩"]` | "J Kaleth" | (mismatched) |
| Rocky L | KR token | "Kevin Hiatt" | (mismatched) |
| Suh Young Eun | KR token | "Lee Youngeun" | (mismatched) |

공통 패턴: Step 1 의 `_is_plausible_match` 에서 `candidate.country is None → True` (false-negative 회피) 룰이 발동. 정상 매치 ~30행 (최엘비/리쌍/DOK2/CL/Tiger JK 등) 도 같은 country=NULL 경로로 통과하지만, **그쪽은 MB 가 한글 alias 를 갖고 있음** (최재성 / Leessang / 도끼 / 씨엘 / 타이거 JK 등).

→ candidate alias 의 hangul 존재 여부가 정상/false-match 를 가르는 결정적 신호.

**Non-goals**:
- BUG-14 (한글 name 자체가 MB 에서 안 잡힘) 와의 통합 — Step 4 는 search 결과에 후보가 있다는 전제 위에서만 동작.
- hint 가 없는 (None) artist 에 추가 reject (false-negative 위험 변동 없음).
- candidate.country 가 명시된 케이스 (Step 1 이 이미 처리).

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`

**변경 안**:

1. `_is_plausible_match(candidate, spotify_genres) -> bool` 시그니처는 유지하되, 호출자 흐름 안에서 hint=KR + country=NULL 인 후보에 대해서만 **상위 호출자 (`fetch_artist_mbid_and_aliases`) 에서 추가 게이트**.

2. 신규 helper `_has_hangul(s: str) -> bool` — `re.search(r"[가-힣]", s)`.

3. 신규 helper `_candidate_aliases_have_hangul(mbid: str) -> bool`:
   - `musicbrainzngs.get_artist_by_id(mbid, includes=["aliases"])` 호출.
   - 응답의 `artist["alias-list"]` (없을 수도 있음) 의 각 alias `name` 에 대해 `_has_hangul`.
   - 1건 이상 hangul 이면 True. 호출 실패 또는 alias 없음 → False (보수적).

4. **호출자 변경** (`fetch_artist_mbid_and_aliases`):
   ```python
   for candidate in candidates_sorted_by_score:
       if int(candidate.get("ext:score", 0)) < _MIN_SCORE:
           break
       if not _is_plausible_match(candidate, spotify_genres):
           logger.info("MB cross-check reject: ...")
           continue
       # Step 4 tiebreaker — country=NULL pass-through 사각지대 보호
       hint = _country_hint_from_genres(spotify_genres or [])
       if hint == "KR" and not candidate.get("country"):
           mbid = candidate["id"]
           if not _candidate_aliases_have_hangul(mbid):
               logger.info(
                   "MB hangul-tiebreak reject: name=%s candidate=%s mbid=%s",
                   ..., candidate.get("name"), mbid,
               )
               continue
       # accept
       return mbid, _extract_aliases(candidate or fetch_detail(mbid))
   return MBID_NOT_FOUND, []
   ```

5. **API call budget**: hint=KR + country=NULL 후보당 +1 호출. Worst-case 한 row 당 9 호출 (limit=10 의 모든 후보가 hint=KR + country=NULL), 평균 2-3. MB rate limit 1 req/sec 한도 + worker 사이클당 10 row 처리 → 추가 ~20-30 req/cycle, 여유 안.

6. **로깅**: `"MB hangul-tiebreak reject"` 분리 — Step 1 의 `"MB cross-check reject"` 와 CloudWatch 필터로 따로 추적.

**테스트** (`tests/test_musicbrainz_client.py`):

- `_has_hangul`: parametrize 로 한글 / 영문 / 일문 / mixed / 빈 string.
- `_candidate_aliases_have_hangul`: mock `musicbrainzngs.get_artist_by_id` 응답으로 alias-list 한글 포함 / 미포함 / 빈 list / 키 자체 누락 / API 예외.
- `fetch_artist_mbid_and_aliases` 통합:
  - 후보 1: country=NULL, alias 한글 없음 → reject
  - 후보 2: country=KR → accept
  - 후보 3: country=NULL, alias 한글 있음 → accept (후보 1 거절 시 fallback)
  - hint=None: tiebreaker 비활성 (Step 1 행동 동일)
  - hint=KR + 모든 후보 country 명시 (KR 아님): Step 1 이 먼저 reject → tiebreaker 도달 안 함
- fixture: `tests/fixtures/mb_va_country_null_no_hangul.json` (V.I 류 응답 sanitized), `mb_dok2_country_null_with_hangul.json` (정상 매치 응답).

**Verification (local)**:

```
cd myblog_worker && pytest tests/test_musicbrainz_client.py -v
ruff check worker/
```

Local smoke (DB optional): pytest + ruff + 신규 tiebreaker 단위 테스트 그린 ([[feedback-local-db-smoke-fallback]]).

**Prod smoke** (post-merge, EventBridge 1주기):

- CloudWatch 필터 `"MB hangul-tiebreak reject"` 가 V.I/JA$/SUGA 류 row 처리 시 발화.
- DB 사후 점검 — Step 2 reset 백업 CSV (`/tmp/bug15-step2-reset-backup-20260529-105923.csv`) 의 6개 의심 spotify_id 가 sentinel `not_found` 또는 한글 alias 보유 새 MBID 로 전환됐는지:
  ```sql
  SELECT spotify_id, name, musicbrainz_id, aliases
    FROM artists
   WHERE spotify_id IN (
     '0boGn8zBcxCZIT8N4wNpjD', -- V.I
     '0QGm4hjuiDqfRorb2tewU1', -- JA$
     '0ebNdVaOfp6N0oZ1guIxM8', -- SUGA
     '0lb59tIBwWrDfP6X956pkK', -- Jimmy Paige
     '0sVdt9nuNGEwrX3dPXRhwJ', -- Rocky L
     '1uQ8BQhLtGMfK8PS3UAdNX'  -- Suh Young Eun
   );
  ```

**Step 2 재실행 의존성**: Step 4 머지 후 위 6 spotify_id 만 별도 mini-reset SQL (musicbrainz_id NULL 화) 필요 — `not_found` sentinel 행은 EventBridge 가 안 건드림. 별도 `scripts/bug15-step4-mini-reset.sql` 작성 (Step 4 PR 에 포함).

**Rollback**: PR revert. helper 2개 + 호출자 분기 추가만이라 데이터 mutation 없음. mini-reset 은 백업 CSV 로 원본 복구.

**Open questions**:

1. **alias-list 누락 시 conservative (reject) vs permissive (accept)** — RFC 안은 reject (정상 false-match 잡기 우선). 단점은 MB 가 alias 안 가진 진짜 KR artist 행 (예: empty aliases 의 BLAY/Microdot/PATEKO 등 ~20행) 의 false-negative 가능. **잠정 결정: reject** — 정상 매치는 Step 1 의 country 명시 또는 alias 한글로 통과 가능. country=NULL + alias 없는 진짜 KR artist 는 BUG-14 영역.
2. **추가 호출의 caching** — 같은 mbid 가 사이클 안에서 반복될 수 있음. lru_cache 추가? **잠정: 안 함** — 사이클당 10 row, 후보 mbid 중복 가능성 낮음. 필요 시 별도.
3. **hint=KR 이외에도 적용 (JP/CN 확장 후)** — Step 5 (JP/CN hint widening) 머지 시점에 동일 hangul → kana/kanji/한자 체크로 확장. Step 4 는 KR 한정으로 시작.

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

### Step 5 — surname-token gate (2026-05-29 Step 4 mini-reset borderline 후속)

**Status**: reverted (2026-05-29 prod 검증 + 사용자 spirit 충돌, worker PR #27 으로 코드 revert).

**관통 원칙**: 본 Step 의 1순위 방어 대상은 **정상 매치의 과잉 거절**. Step 5 가 설계 단계에서 단순 surname-substring (algorithm C) 을 부결한 이유도 동일 (측정 SQL 의 ~60% false-positive 가 한국 가수 영문 stage ↔ 한글 alias 패턴을 정상 매치까지 거절시키는 실패 모드). 본 RFC 의 **모든 수치 임계값 (길이 캡 10, surname 최소 길이 2, 토큰 분기 기준) 은 잠정값** — Step 5 배포 후 더 큰 라벨셋으로 재검토 대상.

**배경**: Step 4 mini-reset (PR #133) prod 검증에서 6 대상 중 5 명확 개선, 1 borderline 잔존:

- `Suh Young Eun` (Spotify) → MB `Young Eun Lee` (`3864ea50...`, KR Person). candidate.country=KR + alias 한글 보유로 Step 4 까지 통과하지만 사람이 다름. 신호: Spotify name 의 surname-token (`Suh`) 이 candidate primary name + aliases 어디에도 substring 으로 등장 X.

**Prod 측정** (2026-05-29 측정 SQL `/tmp/bug15-step5-measure.sql`):

| 분모 / 의심 | 값 |
|---|---|
| KR 후보 전체 (musicbrainz_id non-sentinel + KR-genres) | 73 |
| 측정 분모 (aliases 비어있지 않음) | 46 |
| surname-substring 미매치 카운트 | 34 (74% of measurable) |
| 표본 10 사람 라벨링 | likely false-match 3, borderline 1, 정상 6 |

→ 의심율 74% 중 ~60% 는 측정 false-positive. 한국 가수 영문 stage name ↔ 한글 alias 패턴 (B.I/CL/GooseBumps/MILLHAM/PEEJAY 류) 이 측정 SQL 에 잘못 걸림. 원인: `artists.aliases` 에 MB primary name 미저장이라 측정만으론 정확 신호 못 잡음. 실제 worker 알고리즘은 `candidate.name` 들고 있어 더 정확. **실제 false-match 추정 ~30-40% (4-18 / 46행).**

표본 likely false-match — **본 게이트가 의도적으로 잡는 대상** (Step 5 mini-reset 대상):

- `Dragon Pony` → MB `Vylet Pony` (영문 alias 만, surname 무신호)
- `Lil Moshpit` → MB `이휘민` (Suh Young Eun 와 같은 패턴)
- `Suh Young Eun` (Step 4 잔존)

표본 별도 이슈 — **본 게이트가 의도적으로 잡는 대상 아님**, mini-reset 제외:

- `IU&Kim Yuna` → MB `YUNA` 단일 인물. Spotify 가 `IU + Kim Yuna` 콜라보를 한 행으로 표기 → MB 단일 인물 매칭 시스템의 구조적 한계로 한 인물에 매칭됨. surname-gate 가 우연히 거절 (토큰화 `["IU&Kim", "Yuna"]` → surname `iu&kim` 이 haystack 미매치) 하지만 이는 의도된 신호 아님. mini-reset 대상 제외, **별도 이슈 (콜라보/feat 행 매칭 전반)** 로 분리. 측정 집계에서도 surname-gate 효과로 카운트하지 않음.

**Non-goals**:

- BUG-14 (한글 name 의 MB 검색 자체 실패) — MB primary name + aliases 가 모두 한글만이고 라티나이즈 alias 자체 없는 진짜 KR artist 가 latinized Spotify name 으로 들어오면 false-negative. BUG-14 영역.
- JP/CN region 확장 — Step 4 §Open Q3 의 "Step 5 (JP/CN hint widening)" 라벨은 placeholder. 본 Step 5 는 KR 한정 surname-token gate 로 scope 변경. JP/CN 은 별도 step 또는 RFC.
- Step 4 mini-reset 의 sentinel `not_found` 5 행 (V.I/JA$/Jimmy Paige/SUGA/Rocky L) — sentinel 은 EventBridge 가 안 건드림.
- 콜라보 / feat 행 매칭 (`IU&Kim Yuna` 류, Spotify 가 다수 인물을 한 행으로 표기) — MB 단일 인물 매칭 시스템의 구조적 한계. surname-gate 가 우연히 거절할 수는 있지만 의도된 신호 아님. **별도 이슈**.
- ILLSON 류 1-토큰 borderline (1-토큰 면제 룰 안에서 통과되지만 실제 false-match 의심) — 본 게이트 신호 부재. MB 후보 직접 확인 후 진짜 오매칭이면 **별도 작은 PR 로 deny-list** 처리 (이번 PR 미포함).

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`

**변경 안**:

1. 신규 helper `_spotify_name_matches_candidate(spotify_name, candidate_name, raw_aliases) -> bool`:

   ```python
   def _spotify_name_matches_candidate(
       spotify_name: str,
       candidate_name: str,
       raw_aliases: list[dict],
   ) -> bool:
       tokens = [t for t in (spotify_name or "").split() if t]
       # 핵심 면제 신호 = 토큰 수 == 1 (= 본명 아님, 무대명). 한국 가수 영문
       # 짧은 무대명 (B.I/CL/BewhY/GooseBumps/PEEJAY) 은 MB 가 한글 alias 만
       # 들고 있는 정상 패턴이라 surname-substring 으로 못 잡음 → 면제 안 하면
       # 정상 매치를 폭증 거절. 길이 ≤ 10 캡은 잠정 안전장치 (prod 표본
       # 최댓값 GooseBumps=10) — 11+ 1-토큰 무대명이 false-match 로 관찰되면
       # 임계 조정 또는 별도 신호 추가. 본문 §Open Q1 참조.
       if len(tokens) == 1 and len(spotify_name or "") <= 10:
           return True
       surname = tokens[0].lower() if tokens else ""
       if len(surname) < 2:
           return True  # 1글자 라티나이즈 토큰은 substring 신호 약함
       haystack = " ".join(
           [candidate_name or ""] + [a.get("alias", "") for a in raw_aliases]
       ).lower()
       return surname in haystack
   ```

2. **호출자 변경** (`fetch_artist_mbid_and_aliases`) — Step 4 hangul-tiebreak 분기 이후, accept 직전:

   ```python
   # Step 4 (existing) — country=NULL pass-through hangul tiebreaker
   if hint == "KR" and not candidate.get("country"):
       if not _aliases_have_hangul(raw_aliases):
           logger.info("MB hangul-tiebreak reject: ...")
           continue

   # BUG-15 Step 5 — surname-token gate (hint=KR 한정, country=KR 도 포함)
   if hint == "KR":
       if not _spotify_name_matches_candidate(
           name, candidate.get("name", ""), raw_aliases
       ):
           logger.info(
               "MB surname-gate reject: name=%s candidate=%s mbid=%s",
               name, candidate.get("name"), mbid,
           )
           continue

   aliases = [...]  # 기존 추출
   return mbid, aliases
   ```

3. **추가 MB API call 0** — `candidate.name` 은 `search_artists` 응답에 이미 포함, `raw_aliases` 는 Step 4 가 이미 가져옴. pure CPU.

4. **로깅**: `"MB surname-gate reject"` 분리 — Step 1 `"MB cross-check reject"`, Step 4 `"MB hangul-tiebreak reject"` 와 CloudWatch 필터 따로 추적. [[reference-prod-lambda-loglevel]] 동일 제약.

**Suh Young Eun 검증** (예상):

- tokens=`["Suh","Young","Eun"]`, len=13 → 단일 토큰 면제 X.
- surname="suh", haystack=`"young eun lee 이영은 ..."` → `"suh" not in` → **reject** ✓.

**정상 한국식 본명 검증** (예: `Choi Jae Seong` → MB primary `최재성`, aliases `["Choi Jae Seong", ...]`):

- surname="choi", haystack 에 `"choi"` (alias 내) → **accept** ✓.
- MB primary name + aliases 모두 한글만이고 라티나이즈 alias 자체 없으면 → reject (BUG-14 영역, false-negative 인정).

**짧은 stage name 면제 검증** (prod 표본 적용):

| Spotify name | tokens, len | 분기 | 결과 |
|---|---|---|---|
| B.I | 1, 3 | 면제 | accept (정상) ✓ |
| CL | 1, 2 | 면제 | accept (정상) ✓ |
| BewhY | 1, 5 | 면제 | accept (정상) ✓ |
| PEEJAY | 1, 6 | 면제 | accept (정상) ✓ |
| MILLHAM | 1, 7 | 면제 | accept (정상) ✓ |
| GooseBumps | 1, 10 | 면제 | accept (정상) ✓ |
| ILLSON | 1, 6 | 면제 | accept (borderline; deny-list 영역) |
| Dragon Pony | 2, 11 | gate, surname="dragon" | reject ✓ (의도) |
| IU&Kim Yuna | 2, 11 | gate, surname="iu&kim" (split 공백 기준 `["IU&Kim", "Yuna"]`) | reject — **콜라보 구조적 한계, 의도 아님** |
| Lil Moshpit | 2, 11 | gate, surname="lil" | reject ✓ (의도) |
| Suh Young Eun | 3, 13 | gate, surname="suh" | reject ✓ (의도) |

**테스트** (`tests/test_musicbrainz_client.py`):

- `_spotify_name_matches_candidate` parametrize:
  - 면제 그룹: `("B.I", "B.I", [{"alias": "비아이"}])` → True, `("CL", "CL", [{"alias": "이채린"}])` → True, `("GooseBumps", "GooseBumps", [{"alias": "구스범스"}])` → True (length=10 경계).
  - 다토큰 surname 매치: `("Choi Jae Seong", "최재성", [{"alias": "Choi Jae Seong"}])` → True (alias 내), `("Choi Jae Seong", "Choi Jae Seong", [{"alias": "최재성"}])` → True (primary name 내).
  - 다토큰 surname 미매치: `("Suh Young Eun", "Young Eun Lee", [{"alias": "이영은"}])` → False, `("Lil Moshpit", "이휘민", [{"alias": "이휘민"}])` → False, `("Dragon Pony", "Vylet Pony", [{"alias": "Pony!"}])` → False.
  - 가드: `("", "Foo", [])` → True (빈 이름은 차단 안 함), `("X Y", "Z", [])` → True (1글자 surname).
- `fetch_artist_mbid_and_aliases` 통합:
  - hint=KR + Step 1/4 통과 + surname-gate fail → 다음 후보 (다음 후보 없으면 `MBID_NOT_FOUND`).
  - hint=KR + Step 1/4 통과 + surname-gate pass → accept.
  - hint=None → surname-gate 비활성 (현행 행동 보존).
- fixture: `tests/fixtures/mb_suh_young_eun_search.json` (Spotify "Suh Young Eun" 입력에 대한 search 응답 sanitized), `mb_suh_young_eun_detail.json` (alias-list 응답).

**Verification (local)**:

```
cd myblog_worker && pytest tests/test_musicbrainz_client.py -v
ruff check worker/
```

Local smoke (DB optional): pytest + ruff + 신규 surname-gate 단위 테스트 그린 ([[feedback-local-db-smoke-fallback]]).

**Prod smoke** (post-merge, EventBridge 1주기):

- CloudWatch 필터 `"MB surname-gate reject"` — prod LOG_LEVEL=WARNING ([[reference-prod-lambda-loglevel]]) 이면 INFO 안 잡힘. DB 증거로 우회.
- DB 사후 점검 — mini-reset 후 다음 EventBridge 사이클에서 3 표본 행이 sentinel `not_found` 또는 진짜 KR Person MBID 로 전환됐는지 (IU&Kim Yuna 는 콜라보 별도 이슈로 제외):

  ```sql
  SELECT spotify_id, name, musicbrainz_id, aliases
    FROM artists
   WHERE spotify_id IN (
     '1uQ8BQhLtGMfK8PS3UAdNX', -- Suh Young Eun (Step 4 잔존)
     '0tVSrjQ0NpDlecsJwGmrMy', -- Lil Moshpit
     '2aRhzujDfJ1mVe2XdddXYL'  -- Dragon Pony
   );
  ```

**Step 4 패턴 동일 mini-reset 의존성**: Step 5 머지 후 위 3 spotify_id mini-reset 필요 — `scripts/bug15-step5-mini-reset.sql` 별도 PR. 사전 SELECT 백업 캡처 의무. **IU&Kim Yuna 는 콜라보 매칭 별도 이슈로 분리, 본 reset 미포함**.

**Rollback**: PR revert. helper 1개 + 호출자 분기 추가만이라 데이터 mutation 없음. mini-reset 은 백업 CSV 로 원본 복구.

**Open questions**:

1. **단일 토큰 stage name 길이 임계** — 핵심 면제 신호는 **토큰 수 == 1** (본명 아님 = 무대명). 길이 캡 ≤ 10 은 잠정 안전장치 수준 — prod 표본 최댓값 (GooseBumps=10) 에 맞춘 과적합 값이라 라벨셋 커지면 재검토 필요. 안전장치를 조이지 않는 (= 7~8 로 낮추지 않는) 이유는 정상 매치 (GooseBumps/MILLHAM 등) 가 도리어 거절되는 실패 모드가 1순위 방어 대상이기 때문. **잠정**: 10, 배포 후 라벨셋 ≥30 시점에 재검토.
2. **surname-token = 첫 토큰 vs 마지막 토큰** — 한국식 라티나이즈는 성-first ("Suh Young Eun") 또는 이름-first reverse ("Young-Eun Suh") 둘 다 가능. substring 검사가 양방향 보호 (alias 토큰 순서 무관). 첫 토큰만 검사해도 alias 가 reverse 형태 라티나이즈 됐다면 통과. **잠정**: 첫 토큰만 (배포 후 재검토).
3. **artists.aliases 에 MB primary name 같이 저장?** — 측정 SQL false-positive 60% 가 이걸로 해결되지만 schema 변경 + BUG-15 scope 밖. **결정**: 안 함. 측정 한계는 인정.
4. **hint=None (영어권 / 일본) 후보에도 surname-gate 적용?** — **결정: 본 RFC 에서 안 함, BUG-15 는 KR 한정으로 닫음**. 영어권 무대명은 성씨 구조를 안 따르고 (Dragon Pony 류, "X feat. Y" 표기 다양), 게이트 적용 시 정상 매치 대량 거절 위험 — 이번에 algorithm C 단독 부결한 실패 모드와 동일. EN/JP prod 측정도 전무 → "별도 티켓, prod 측정 → 표본 라벨링 먼저" 규율로 미룸. KR 만으로 닫는 이유는 한국 가수의 성-first 라티나이즈 관습 + ko-KR genres 신호가 게이트 트리거 키로 안정적이기 때문.
5. **ILLSON 류 borderline (1-토큰 + 길이 ≤10 면제 통과 + 실제 false-match 의심)** — surname-gate 신호 부재. **결정: Step 5 PR 미포함**. 이유 (a) borderline 라 증거 불충분, (b) 알고리즘 PR 에 수동 데이터 패치 (deny-list) 섞으면 측정/롤백이 더러워짐 (algorithm 효과와 manual hardcode 효과가 한 PR 안에 섞임). 후속: ILLSON 의 진짜 MB 후보를 사람이 직접 확인 → 진짜 오매칭 확인되면 **별도 작은 PR 로 deny-list** (`musicbrainz_id = 'not_found'` 수동 박기) 처리.

**Outcome (2026-05-29 prod 검증 후 revert)**:

worker PR #26 (Step 5 코드 적용) 머지 + mini-reset 3 spotify_id + EventBridge 1 사이클 결과:

- **Lil Moshpit**: 같은 MBID 재박힘. MB API 확인 결과 primary name 자체가 `Lil Moshpit` (country=KR) + alias `이휘민` (legal name, Lee Hwi-min). PR #134 의 표본 라벨링 ("확실 false-match") 이 **over-aggressive** 였음. surname-gate 가 raw alias 안의 `Lil Moshpit` 잡고 정상 통과 → algorithm 자체는 의도대로 작동.
- **Suh Young Eun**: sentinel `not_found` 박힘. surname `suh` 가 MB candidate `Young Eun Lee` + alias 어디에도 substring 미매치 → reject → 다음 후보 없음 → sentinel. algorithm 의도대로 작동.
- **Dragon Pony**: candidate.country=`US` (`Vylet Pony`, brony musician) — Step 1 cross-check 가 잡는 영역, Step 5 와 무관.

**사용자 spirit (결정적 신호)**: "별칭에 대해서는 보수적으로 하지마 검색에만 쓰이잖아". alias 가 약간 다른 사람 거여도 검색용이라 들어가는 게 sentinel-on-reject 보다 낫다. Step 5 의 sentinel 패턴이 이 spirit 과 정면 충돌 — Suh Young Eun sentinel = "이영은" / "Lee Youngeun" 검색 시 영원히 누락.

**결정**: Step 5 전체 revert.

- worker PR #27 으로 코드 revert (helper + 분기 + 21 테스트 제거, 202 lines deleted)
- prod `Suh Young Eun` row 수동 복구 (`3864ea50-df4d-4615-943c-9778b598102b` + `["Lee Youngeun"]`)
- 본 workspace cleanup PR 으로 plan.md row drop + `scripts/bug15-step5-mini-reset.sql` 삭제 + 본 outcome 기록
- prod `Lil Moshpit` 은 그대로 (정상 매치 박힘), `Dragon Pony` 는 Step 1 영역으로 다음 cycle 처리 (sentinel 예상)

**교훈**:

1. **라벨링 단계 검증 의무** — mini-reset 대상 후보를 사람 라벨링만으로 정하지 말고 **MB API 직접 호출** 해서 candidate primary name + alias-list 확인. Lil Moshpit 의 경우 MB primary 자체가 영문 stage 였고 라벨링이 잘못 잡은 케이스. 향후 RFC 의 표본 라벨링 단계에 "MB API 호출로 candidate metadata 사전 확인" 게이트 추가.
2. **게이트 추가 시 검색 가용성 영향 평가** — alias 가 검색 인덱스에만 쓰일 때, 게이트가 sentinel 박는 결과는 검색 누락 → 데이터 정확성보다 검색 가용성이 사용자 가치에서 우선. Step 1/3/4 같은 region mismatch 게이트는 region 자체가 다르면 검색 노이즈 (한국 검색에 영문 brony) 라 sentinel OK 지만, Step 5 같은 "같은 region 안에서 다른 인물" 게이트는 alias 가 검색에 도움될 가능성 큼.
3. **algorithm 보강 ≠ 데이터 정확성 보강** — Step 1/3/4 는 region mismatch 같은 명확한 false-match 영역. Step 5 의 surname-gate 는 같은 region 안에서 "혹시 다른 사람일까" 의심에 sentinel 박는 게이트 — 검색 가용성 영역. 두 차원을 같은 RFC 안에 섞은 게 설계 실수.

**BUG-15 종료**: Step 1/3/2/4 유지. Step 5 reverted. JP/CN 확장 또는 ILLSON deny-list 등 향후 작업은 [[feedback-brainstorm-iterate-before-commit]] + 사용자 spirit (검색 가용성 vs 정확성) 확인 후 별도 RFC.

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
| 2026-05-29 | Step 4 (country=NULL pass-through tiebreaker) draft 추가 — Step 2 reset +1h31m prod 표본에서 V.I/JA$/SUGA 류 sticky false-match (≥6행) 관찰. candidate alias 의 한글 존재 여부가 결정적 신호. Option A (추가 MB API 호출로 alias hangul 체크) 채택, B (이름 시그널만) 와 E (score 가중치) 는 효과/임계 튜닝 이슈로 부결. | 4 |
| 2026-05-29 | Step 5 (surname-token gate) draft 추가 — Step 4 mini-reset 후 borderline 잔존 (Suh Young Eun → "Young Eun Lee") + prod 측정 (46 measurable, 의심 34, 실제 false-match 추정 30-40%) 대응. 알고리즘 C' = 1-토큰 stage name 면제 (length ≤ 10) + 다토큰 surname-token substring on `candidate.name + aliases`. 단순 C (surname substring 단독) 는 측정 SQL 의 60% false-positive 가 한국 가수 영문 stage ↔ 한글 alias 패턴 (B.I/CL/GooseBumps 등) 미보호로 그대로 prod 적용 시 정상 매치 폭증 거절. hint=KR 한정, country=KR / country=NULL hangul-pass 양쪽 모두 추가 게이트. | 5 |
| 2026-05-29 | Step 5 검토 라운드 결정 (관통 원칙: 정상 매치 과잉 거절 1순위 방어, 모든 수치 임계 잠정). (a) 길이 임계 10 유지 — prod 표본 최댓값 (GooseBumps) 과적합값임을 본문에 명시, 핵심 면제 신호는 토큰 수==1, 길이 캡은 안전장치 수준 (조이지 않음), 라벨셋 ≥30 시점 재검토. (b) mini-reset 4→3 (IU&Kim Yuna 제외) — 콜라보 행은 MB 단일 인물 매칭 시스템 구조적 한계로 별도 이슈 분리, 토큰화 동작 (`["IU&Kim", "Yuna"]`) 본문 명시 + 게이트 우연 reject 와 의도 reject 구분으로 측정 집계 오염 방지. (c) ILLSON deny-list 본 PR 미포함 — borderline 증거 불충분 + 알고리즘 PR 에 수동 데이터 패치 섞으면 측정/롤백 오염, MB 후보 직접 확인 후 진짜 오매칭이면 별도 작은 PR. (d) hint=None (EN/JP) surname-gate 확장 안 함 — 영어권 무대명 성씨 구조 미사용 → 게이트 적용 시 정상 매치 거절 위험이 algorithm C 단독 부결한 실패 모드와 동일, EN/JP prod 측정 전무, "별도 티켓, prod 측정 + 표본 라벨링 먼저" 규율로 미룸 → **BUG-15 는 KR 한정으로 닫음**. | 5 |
| 2026-05-29 | Step 5 reverted — prod 검증 결과 (1) Lil Moshpit 정상 매치 (MB primary 자체가 `Lil Moshpit` + alias `이휘민` legal name) 로 표본 라벨링이 over-aggressive 였음, (2) Suh Young Eun sentinel 박힘이 algorithm 의도대로 작동했으나 **사용자 spirit ("별칭은 검색에만 쓰여 보수적 X")** 과 정면 충돌 (sentinel = 검색 영원 누락). worker PR #27 으로 코드 revert + Suh Young Eun row 수동 복구 + 본 cleanup PR 으로 plan/SQL 정리. 교훈: 라벨링 단계에 MB API 사전 확인 의무 + 게이트 추가 시 검색 가용성 영향 평가 + algorithm 보강과 데이터 정확성/검색 가용성 차원 분리. BUG-15 는 Step 1/3/2/4 까지 유지 후 종료. | 5 |
