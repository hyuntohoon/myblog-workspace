# BUG-18: alias_fill fetch 단 MBID uniqueness pre-check

- **Status**: closed (shipped via worker #22 + #23, 2026-05-29 — see `docs/archive/done/2026-05.md`)
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: dropped 2026-05-29
- **Motivation**: `~/.claude/plans/bug-15-step2-korean-widening-bundle.md` (Decisions §1) — 3행 stuck 본질 해결의 owner 가 BUG-18 으로 확정됨.

---

## Goal

`myblog_worker/worker/clients/musicbrainz_client.py:fetch_artist_mbid_and_aliases` 가 후보 채택 직전 **DB 에 같은 `musicbrainz_id` 가 이미 존재하면 그 후보를 거절** 하도록 한다. 결과: BUG-17 + BUG-15 머지 후에도 alias_fill 매 사이클 stuck 인 `j-hope` / `Kim Tae Hoon` / `dj friz` 3행이 다음 후보 (혹은 `MBID_NOT_FOUND` sentinel) 으로 자연 해소되어 WARNING 로그가 멎고 alias_fill 의 평균 진척이 사이클당 ≥1행 유지된다.

**예상 outcome**: 3행의 1st 후보가 모두 이미 DB 점유 + 2nd 후보의 score 는 `_MIN_SCORE` 미통과 가능성이 높음 (MB 한국어 alias 인덱싱 빈약, [[plan.md#BUG-14]]) → 3행 전부 `'not_found'` sentinel 박힐 확률이 가장 높음. 이는 실패가 아니며, BUG-13 의 partial UNIQUE 가 `'not_found'` 를 인덱스에서 제외하지만 컬럼 자체는 NOT NULL 상태가 됨 → 다음 사이클 `WHERE musicbrainz_id IS NULL` 셀렉트에서 자연 제외되어 head 가 비워짐 (= eviction). 따라서 "head 자리 자연 해소" 의 본질 기전은 **partial UNIQUE 가 아니라 NULL→NOT NULL 전환에 의한 row pool 축소** 임.

## Non-goals

- BUG-15 의 cross-check 자체 변경 (Spotify-genre country hint 는 그대로 보존).
- Korean hint widening (별도 BUG-15 follow-up PR — 본 RFC 의 후행).
- BUG-15 Step 2 의 known-bad row reset (별도 PR — BUG-18 + widening 머지 후 의미가 생기는 후행).
- `executemany` 재도입 / SAVEPOINT 전환 (BUG-17 결정 그대로).
- MB API 호출 횟수 감소 / 캐싱 (현 `1 search + 1 get_artist_by_id` per artist 유지).
- 과거에 잘못 박힌 MBID 일괄 sweep (BUG-15 Step 2 가 별도로 다룸).

## Current state

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py:fetch_artist_mbid_and_aliases` (line 60–122).

```python
for candidate in candidates:
    score = int(candidate.get("ext:score", 0))
    if score < _MIN_SCORE:
        break
    if not _is_plausible_match(candidate, spotify_genres):
        logger.info("MB cross-check reject: ...")
        continue
    mbid = candidate["id"]
    detail = musicbrainzngs.get_artist_by_id(mbid, includes=["aliases"])
    # ... aliases 추출 + return mbid, aliases
```

**호출자**: `myblog_worker/worker/service/sync_service.py:generate_and_save_aliases` (line 250–318). per-row tx + `IntegrityError` 캐치 패턴 (BUG-17). UNIQUE 충돌 시 행 단위 rollback + warning + skip.

**실패 모드 (관측됨, [[project-alias-fill-collision-followup]])**:

매 사이클 같은 3행 (`ORDER BY spotify_id` head) 이 MB 에서 동일 false-match MBID 받아 옴 →
- `j-hope` (sid `0b1sIQumIAsNbqAoIClSpy`) → MBID `569c0d90-28dd-413b-83e4-aaa7c27e667b`
- `Kim Tae Hoon` (sid `0hLtT90h7lbX85L58zO75h`) → MBID `4b462375-c508-432a-8c88-ceeec38b16ae` (Kim Wilde UK, 같은 MBID 가 Kim Chang-Wan 에도 매칭)
- `dj friz` (sid `0js3wKXyi7RL11sfOykRt1`) → MBID `4fa424b3-20fd-449e-baa0-4eb3b9c0c4e9`

UNIQUE index (BUG-13) 가 UPDATE 에서 거절 → BUG-17 per-row catch → warning 후 skip → `musicbrainz_id` NULL 유지 → 다음 사이클 SELECT 가 동일 3행 다시 head → 무한 반복.

**BUG-15 cross-check 가 못 잡는 이유**: 위 3행의 `genres` 가 `[]` 또는 한국어 localized (`_COUNTRY_HINTS` 영문 needle 과 불일치, [[project-prod-artists-genres-korean]]) → `_country_hint_from_genres` 가 `None` → cross-check skip → MB top-1 그대로 채택 → false-match.

UNIQUE 가 데이터 corruption 은 막지만 **fetch 단에서 거절 못 함** 이 핵심: 3행이 진척 없이 계속 head 자리만 차지.

## Target state

**파일**: `myblog_worker/worker/clients/musicbrainz_client.py`.

1. `fetch_artist_mbid_and_aliases` signature 에 `is_mbid_taken: Optional[Callable[[str], bool]] = None` 추가 (default `None` → 현행 동작 유지, 단위 테스트 backwards compat).
2. 후보 iterate 중 `_is_plausible_match` 통과 직후, `is_mbid_taken` 가 있고 `is_mbid_taken(candidate.id) == True` 이면:
   - `logger.info("MB pre-check reject: name=%s candidate=%s mbid=%s already in DB", ...)`.
   - `continue` — 다음 후보로.
3. 모든 후보가 pre-check 거절 (또는 score/cross-check 컷) → 기존 그대로 `MBID_NOT_FOUND`.

**파일**: `myblog_worker/worker/service/sync_service.py:generate_and_save_aliases`.

1. row 루프 안에 closure:
   ```python
   def _is_mbid_taken(mbid: str) -> bool:
       row = session.execute(
           text("SELECT 1 FROM artists WHERE musicbrainz_id = :mbid LIMIT 1"),
           {"mbid": mbid},
       ).first()
       return row is not None
   ```
2. 호출 변경:
   ```python
   mbid, aliases = fetch_artist_mbid_and_aliases(
       name,
       spotify_genres=genres or [],
       is_mbid_taken=_is_mbid_taken,
   )
   ```
3. 카운터에 `skipped_collision` 외 `skipped_precheck` 추가, summary INFO 한 줄에 같이 기록.

**SQL 안전성**:
- `idx_artists_musicbrainz_id` (BUG-13 partial UNIQUE excl `'not_found'`) 가 SELECT cost 를 점 lookup 으로 보장 — 사이클당 ≤10 candidates × 평균 1.x SELECT = ≤20 PK lookup. 무시 가능.
- `'not_found'` sentinel 은 partial UNIQUE 에서 제외라 인덱스 안 잡지만, MB API 가 candidate.id 로 sentinel 문자열을 반환할 일 없음 (UUID format) → false-positive 없음.

**Race**:
- SELECT then UPDATE 사이 다른 row 가 같은 MBID 박을 가능성: alias_fill 은 단일 Lambda 인스턴스 + EventBridge cron → 동시 실행 없음. 만약 일어나도 UNIQUE 가 받아냄 (BUG-17 의 IntegrityError 경로).
- **Self-MBID 회피**: `_is_mbid_taken(candidate.id)` 가 자기 자신의 MBID 도 잡는 시나리오 — 현 `generate_and_save_aliases` 는 `WHERE musicbrainz_id IS NULL` 행만 처리하므로 자기 행은 MBID 가 NULL 이라 self-collision 불가. 추후 refresh/retry 잡이 추가될 경우 (`musicbrainz_id IS NOT NULL` 도 처리하는 루프) `WHERE musicbrainz_id IS NULL OR musicbrainz_id != candidate.id` 형태로 가드 필요 — 현 PR scope 외, 본 RFC 의 assumption 으로 명시.
- pre-check 는 **best-effort 최적화** 지 safety net 이 아님 — UNIQUE 가 safety.

## Steps

### Step 1 — pre-check 주입 + 호출자 plumbing (single PR, `myblog_worker`)

`myblog_worker` 단독. cross-check 와 동일한 구조 — pre-check 만 따로 머지하면 호출자가 callback 안 넘겨서 dead code.

- `musicbrainz_client.py`:
  - import: `from typing import Callable, Optional` (이미 있음).
  - `fetch_artist_mbid_and_aliases` signature 확장.
  - 후보 루프 안에 pre-check 분기 + INFO 로그.
- `sync_service.py:generate_and_save_aliases`:
  - row 루프 위 또는 안에 `_is_mbid_taken` closure.
  - `fetch_artist_mbid_and_aliases` 호출 시 callback 전달.
  - `skipped_precheck` 카운터 + summary 로그 갱신.
- `tests/test_musicbrainz_client.py`:
  - 새 case 1: `is_mbid_taken=None` → 현행 동작 (cross-check 후 첫 후보 채택).
  - 새 case 2: 1st 후보 `is_mbid_taken=True` → 2nd 후보 (다른 mbid) 채택.
  - 새 case 3: 모든 후보 `is_mbid_taken=True` → `MBID_NOT_FOUND`.
  - 기존 cross-check / score cut 케이스는 회귀 보호.
- `tests/test_sync_service.py`:
  - mock 3행: 1행 정상, 1행 pre-check 거절 후 다음 후보 정상, 1행 모든 후보 거절 → `MBID_NOT_FOUND`.
  - DB session.execute 의 SELECT 패치 (이미 있을 가능성 — conftest 확인 후 결정).
  - 결과: `succeeded=2`, `skipped_precheck=1`, `skipped_collision=0`, `MB lookup done` INFO 1줄.
- `tests/integration/test_alias_fill_session_lifecycle.py` (**신설**, [[feedback-sa-session-lifecycle-mock-blind]] 의무):
  - 실 SA engine (`TEST_DB_URL` 또는 conftest 의 in-memory Neon test branch). mock SELECT 가 잡지 못하는 connection / autocommit / SAVEPOINT 경계 검증.
  - 케이스: 3행 처리 — row1 정상 commit → row2 pre-check (SELECT) → row2 reject → row3 정상 commit. row2 의 SELECT 가 row1 commit 후 새 transaction 에서 정상 동작하는지, 그리고 row3 commit 시 stale connection handle 사용 안 하는지 검증 (BUG-17 PR #21 의 root cause 재발 차단).
  - assertion: `succeeded=2`, `skipped_precheck=1`, 그리고 DB 의 row2 가 NULL → 'not_found' 로 정상 UPDATE 됐는지 직접 SELECT.

**Verification**:

```
cd myblog_worker && pytest tests/test_musicbrainz_client.py tests/test_sync_service.py tests/integration/test_alias_fill_session_lifecycle.py -v
ruff check worker/
```

`tests/integration/` 는 `TEST_DB_URL` 미설정 시 `pytest.skip` collection-time ([[feedback-local-db-smoke-fallback]] 패턴). CI 는 항상 실행, 로컬은 사용자 env 에 따라.

[[feedback-local-db-smoke-fallback]] — 실DB 미세팅이면 pytest + ruff 그린이면 충분, prod smoke 로 최종 검증.

**Prod smoke** (post-merge, EventBridge 1주기 ≈ 15 min):

0. **전제 — Lambda env `LOG_LEVEL=INFO` 임시 설정** (현 prod 필터가 WARNING+ 만 잡음, [[project-alias-fill-collision-followup]]). 1 사이클 관측 후 INFO → WARNING 원복. 항시 가시화는 별도 ops 개선 (BUG-18 scope 외).
1. CloudWatch `/aws/lambda/blogWorkerLambda` 필터 `"MB pre-check reject"` — 3 known stuck artist 이름이 로그에 나타나는지.
2. CloudWatch 필터 `"MB lookup done"` — `skipped_precheck` ≥ 1 + `Alias update failed` ERROR 미발생.
3. DB ([[reference-database-url-psql]]):
   ```sql
   SELECT spotify_id, name, musicbrainz_id, aliases
     FROM artists
    WHERE spotify_id IN (
            '0b1sIQumIAsNbqAoIClSpy',  -- j-hope
            '0hLtT90h7lbX85L58zO75h',  -- Kim Tae Hoon
            '0js3wKXyi7RL11sfOykRt1'   -- dj friz
          );
   -- → musicbrainz_id 가 'not_found' 로 박혔는지 (모든 후보 거절) 또는 올바른 다른 MBID 인지.
   ```
4. SELECT count(*) FROM artists WHERE musicbrainz_id IS NULL — 이전 사이클 대비 감소 추세인지.

**Rollback**: PR revert. callback default `None` 으로 돌아가 현행 동작. 데이터 mutation 없음 (단, prod smoke #3 에서 `'not_found'` 박힌 행은 그대로 남음 — BUG-15 Step 2 로 reset 가능).

---

## Open questions

1. **callback signature — `Callable[[str], bool]` vs DB engine 직접 주입** — 후자는 client 의 순수성 깨짐 + 단위 테스트 mock 어려움. 전자는 caller 가 closure 만들어야 함. **잠정 결정: callback 채택**. (Step 1)
2. **`_is_mbid_taken` 의 session 재사용** — caller 가 row 루프 안에서 closure 를 만들면 session 이 row 단위 commit 후에도 살아있는가? sync_service.py 의 `session_factory()` context manager 가 outer scope 라 OK. 단 BUG-17 hotfix 노트의 "stale handle" 우려 재발 가능성 점검 필요 (PR-21 의 root cause). **점검 항목: session.execute 가 commit 후에도 새 transaction 열고 정상 SELECT 하는지 통합 테스트 1개 추가 — [[feedback-sa-session-lifecycle-mock-blind]] 적용**. (Step 1)
3. **pre-check 로그 레벨** — INFO 면 blogWorkerLambda 의 현 필터 (WARNING+) 에 안 잡힘 ([[project-alias-fill-collision-followup]] 의 "INFO 필터링" 노트). pre-check 발화 가시성을 위해 WARNING 로 강등할지. **잠정 결정: INFO** — cross-check 와 동일 레벨 유지, prod smoke 시 임시로 Lambda log level 올려 확인. 항시 가시화는 별도 ops 개선 (BUG-18 scope 외). (Step 1)
4. **callback 누락 시 동작** — `None` 이면 pre-check skip (backwards compat). 호출자가 실수로 빼먹어도 silent. **잠정 결정: silent skip 허용** — 단위 테스트가 직접 client 만 호출하는 경우가 있고, callback 강제 시 테스트 boilerplate 증가. lint/type 시그널은 mypy/ruff 가 잡지 않으니 PR review 로 catch. (Step 1)

## Decisions log

| Date       | Decision                                                                              | Step |
|------------|---------------------------------------------------------------------------------------|------|
| 2026-05-29 | BUG-18 신규 등록 (BUG-15 follow-up 회의록 §1). stuck 3행 owner = BUG-18.              | —    |
| 2026-05-29 | callback 주입 (vs DB engine 직접) — client 순수성 + 단위 테스트 단순성 우선.          | 1    |
| 2026-05-29 | pre-check 는 best-effort 최적화. safety net 은 UNIQUE (BUG-13) + IntegrityError catch (BUG-17) 유지. | 1 |
| 2026-05-29 | session lifecycle 회귀 ([[feedback-sa-session-lifecycle-mock-blind]]) 차단용 실엔진 통합 테스트 1개 의무. | 1 |
| 2026-05-29 | feedback round (A) Verification 블록에 통합 테스트 파일 명시. (B) prod smoke 0단계 `LOG_LEVEL=INFO` 임시 설정 + 원복. (C) Goal 에 expected outcome=sentinel + (D) eviction 본질이 NULL→NOT NULL 전환임을 명문화. (E) self-MBID assumption 명시. | 1 |
