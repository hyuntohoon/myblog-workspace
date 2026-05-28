# BUG-17: alias_fill `executemany` 배치가 첫 UniqueViolation 에서 통째로 롤백

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: `plan.md` → BUG-17
- **Discovered**: BUG-15 Step 1 post-merge verification (2026-05-28T16:07Z CloudWatch)

---

## Goal

`worker/service/sync_service.py:generate_and_save_aliases` 의 단일 `executemany` UPDATE 를 **per-row UPDATE + `IntegrityError` 캐치** 로 바꿔서, 한 행의 MBID 충돌이 같은 배치의 나머지 9행을 롤백시키지 않도록 한다. 충돌행은 `logger.warning` 으로 흘리고 건너뛴다. 결과: alias_fill 이 매 15분 사이클마다 의미 있는 진척을 낸다.

## Non-goals

- 충돌의 **근본 원인** (false-match) 자체는 BUG-15 / BUG-14 scope. 이 RFC 는 batch failure mode 만 다룬다.
- `_COUNTRY_HINTS` 를 한국어 토큰까지 확장 (별도 BUG-15 follow-up 으로 분리, [[Open Q1]] 참조).
- 알려진 false-match 행 reset (BUG-15 Step 2 scope).
- `executemany` 를 PG bulk upsert / `INSERT ... ON CONFLICT` 로 전환 (10행/cycle 규모에 과한 변경).
- 충돌행에 `'not_found'` sentinel 강제 박기 ([[Open Q3]] 참조 — 현재 RFC 안은 sentinel 박지 않음).

## Current state

**파일**: `myblog_worker/worker/service/sync_service.py:generate_and_save_aliases` (line 249–299).

```python
with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT spotify_id, name, genres
          FROM artists
         WHERE musicbrainz_id IS NULL
         LIMIT 10
    """)).fetchall()
    if not rows:
        logger.debug("No artists pending MB lookup")
        return
    logger.info("Looking up %d artists on MusicBrainz", len(rows))

    update_data = []
    for sid, name, genres in rows:
        mbid, aliases = fetch_artist_mbid_and_aliases(name, spotify_genres=genres or [])
        update_data.append({"sid": sid, "mbid": mbid, "aliases": json.dumps(aliases, ensure_ascii=False)})

    conn.execute(text("""
        UPDATE artists
           SET musicbrainz_id = :mbid,
               aliases        = CAST(:aliases AS jsonb)
         WHERE spotify_id = :sid
    """), update_data)   # ← executemany. 한 행 실패 시 전 배치 롤백.
    logger.info("MB lookup done for %d artists", len(update_data))
```

**실패 모드 (관측됨)**:

```
[ERROR] Alias update failed: (psycopg.errors.UniqueViolation)
  duplicate key value violates unique constraint "idx_artists_musicbrainz_id"
  DETAIL:  Key (musicbrainz_id)=(4b462375-c508-432a-8c88-ceeec38b16ae) already exists.
```

- MB lookup 이 `Kim Gwang-Jin` 에 대해 MBID `4b462375-...` (alias "Kim Wilde", UK 80s pop) 반환.
- 그 MBID 는 이미 `Kim Chang-Wan` (sid `2yMDYqTvjFeBZcGC4ZMMVH`) 에 박혀있음.
- `idx_artists_musicbrainz_id` 가 partial UNIQUE excl `'not_found'` (BUG-13) 라 충돌. UNIQUE 본연의 일.
- `executemany` 가 batch 전부 롤백. 같은 10행 (Crush, Sunny Hill&Zia, 윤상 포함, MB 응답 유효한 3행 + 'not_found' 6행 + 충돌 1행) 중 0행 persist.
- 같은 SELECT 가 다음 사이클마다 같은 10행 반환 (`ORDER BY` 없음) → 무한 재실패.
- CloudWatch 24h 기준 ≥95 `UniqueViolation` 이벤트. alias_fill 의 prod 효용 = 0.

**충돌 발생 가능성이 BUG-15 post-deploy 에 줄지 않은 이유**:

- BUG-15 cross-check 는 `spotify_genres` 가 hint 와 매칭될 때만 발동. Kim Gwang-Jin / Kim Chang-Wan 모두 `genres = []` → `_country_hint_from_genres` 가 `None` 반환 → cross-check skip → MB top-1 그대로 채택.
- 별개로, 현 `_COUNTRY_HINTS` 가 영문 토큰만 담아 prod 의 한국어 localized genre (`"케이팝"`, `"한국 랩"` 등) 와도 안 맞음 ([[Open Q1]]). BUG-15 cross-check 는 prod 의 어떤 행도 거절하지 못한다.
- 즉 false-match 자체는 BUG-15 가 막을 수도 있는 시나리오와 막을 수 없는 시나리오 (genres 빈 행) 가 섞여있고, 후자에 대해서는 **데이터 부패는 UNIQUE 가 막지만 alias_fill 처리량이 0** 인 상태.

## Target state

**파일**: `myblog_worker/worker/service/sync_service.py:generate_and_save_aliases`.

1. SELECT 에 `ORDER BY spotify_id` 추가 — `LIMIT 10` 만으로는 PG 가 매 사이클 같은 충돌행을 batch head 에 두고 다른 행 진입을 막을 수 있다. 결정적 순서로 충돌행을 큐 끝쪽으로 밀어 NULL 행 다수가 먼저 처리되게 한다. `engine.begin()` 으로 한 번에 transaction 열지 말고 **per-row tx** 로 전환.
2. 각 행:
   ```python
   for sid, name, genres in rows:
       mbid, aliases = fetch_artist_mbid_and_aliases(name, spotify_genres=genres or [])
       try:
           with engine.begin() as conn:
               conn.execute(text("""
                   UPDATE artists
                      SET musicbrainz_id = :mbid,
                          aliases        = CAST(:aliases AS jsonb)
                    WHERE spotify_id = :sid
               """), {"sid": sid, "mbid": mbid, "aliases": json.dumps(aliases, ensure_ascii=False)})
           succeeded += 1
       except IntegrityError as exc:
           logger.warning(
               "alias_fill: skipped sid=%s name=%s mbid=%s — UNIQUE collision: %s",
               sid, name, mbid, exc.orig,
           )
           skipped_collision += 1
   logger.info(
       "MB lookup done: %d ok, %d skipped (UNIQUE collision), of %d looked up",
       succeeded, skipped_collision, len(rows),
   )
   ```
3. SELECT 단계는 별도 (짧은) tx 로 묶거나 autocommit. 행 단위로 connection acquire/release 가 부담스러우면 single connection + per-row `SAVEPOINT` 패턴도 가능 ([[Open Q2]]).
4. 최상위 `try/except` (현재 `logger.error("Alias update failed: ...")`) 는 유지 — `IntegrityError` 외의 예상 못한 실패 (커넥션 끊김 등) 는 cycle 전체 실패로 두고 EventBridge 가 다음 사이클에 재시도.

## Steps

### Step 1 — per-row UPDATE 리팩터 (single PR, `myblog_worker`)

- `sync_service.py:generate_and_save_aliases`:
  - import 추가: `from sqlalchemy.exc import IntegrityError`.
  - SELECT 에 `ORDER BY spotify_id` 추가.
  - 위 Target state §2 의 구조로 refactor.
  - 카운터 `succeeded` / `skipped_collision` 합산 후 한 줄 INFO 로그.
- `tests/test_sync_service.py`:
  - mock 10행 입력. `fetch_artist_mbid_and_aliases` 가 9행 → 정상 MBID, 1행 → 기존 행과 동일한 MBID 반환하도록 patch.
  - `engine.begin()` 의 `conn.execute` 가 충돌 행에서 `IntegrityError` raise 하도록 patch.
  - 결과: 9개 행에 대해 UPDATE 호출 발생 + 충돌 1행은 warning 로그 + `Alias update failed` ERROR 미발생.

**Verification**:

```
cd myblog_worker && pytest tests/test_sync_service.py -v
ruff check worker/
```

prod smoke (post-merge, EventBridge 1주기 ≈ 15 min 대기):

1. CloudWatch `/aws/lambda/blogWorkerLambda` 필터 `"MB lookup done"` — `%d ok` 가 0 이 아닌지.
2. CloudWatch 필터 `"Alias update failed"` — 신규 ERROR 없음.
3. DB:
   ```sql
   SELECT count(*) FROM artists WHERE musicbrainz_id IS NOT NULL AND musicbrainz_id <> 'not_found';
   ```
   2026-05-28T16Z 기준 = 13. PR 머지 후 다음 사이클부터 증가 추세이면 통과.
4. 충돌 행 (`Kim Gwang-Jin`, sid `7dawlSgGRNM0ueE3RQzxZj`) 의 `musicbrainz_id` 가 여전히 NULL 인지 (정상 — sentinel 박지 않는 결정).

**Rollback**: PR revert. 데이터 변경 없음 (UNIQUE 가 corruption 계속 막아줌). 롤백 후 alias_fill 은 다시 매 사이클 fail 하지만 user-facing 영향은 그대로 0.

---

## Open questions

1. **`_COUNTRY_HINTS` 한국어 토큰 확장 (BUG-15 follow-up)** — prod genres 는 `"케이팝"`, `"한국 랩"`, `"K-발라드"`, `"한국 록"` 같은 한국어 localized 형식. 현 `_COUNTRY_HINTS` 는 영문 needle 만이라 prod 행 어디에서도 발동 안 함. BUG-17 PR 에 묶을지, 별개 PR (BUG-15 Step 1.5 같은) 로 뺄지. **잠정 결정: 별개** — BUG-17 의 scope 가 작아야 검증 빠르다. BUG-15 hint widening 은 root-cause (worker SpotifyClient 의 locale 설정이 한국어 응답을 받게 만드는가?) 까지 같이 봐야 해서 한 PR 이 비대해진다.
2. **per-row tx vs. SAVEPOINT** — per-row 로 `engine.begin()` 을 매번 열면 connection acquire 10회. SAVEPOINT 패턴 (`with conn.begin_nested():`) 은 single connection 안에서 충돌 행만 rollback. 10행 / 15분 규모에 perf 차이 무시 가능. **잠정 결정: per-row tx (단순함 우선)**. SAVEPOINT 는 행 수가 1000+ 로 늘어나면 재검토.
3. **충돌 행 sentinel 처리 (해소)** — 충돌행에 `'not_found'` 박으면 다음 사이클에서 SELECT 가 더 안 뽑아 무한 재query 안 함. 단점: MB false-match 가 본질 문제이므로 sentinel 박는 건 증상 가리기. 추후 BUG-15 hint widening 후에도 그 행이 sentinel 이라 영영 재시도 안 됨. **결정: sentinel 박지 않음 + SELECT 에 `ORDER BY spotify_id` 추가**. 후자가 충돌행을 큐 끝쪽으로 밀어 NULL 행 다수가 먼저 진척한다. 충돌행 수가 늘거나 batch head 점유가 다시 문제가 되면 sentinel 정책 재검토.
4. **batch size** — 현재 LIMIT 10. per-row 로 가면 한 사이클에 10회 MB API call + 10회 UPDATE. MB rate limit `1.0 req/s` (musicbrainzngs 설정) 라 10초 이상 걸림. Lambda timeout 120s 라 여유 있음. 추후 batch 키울 시 timeout/perf 재검토.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-29 | BUG-17 분리 등록 (BUG-15 와 별도). false-match 방지와 batch failure mode 는 별개 관심사. | — |
| 2026-05-29 | 충돌행에 sentinel 박지 않음 — 운영 hook 이 BUG-15 Step 2 에 이미 있음. | 1 |
| 2026-05-29 | per-row tx 채택 (vs. SAVEPOINT) — 10행 규모에서 단순함 우선. | 1 |
| 2026-05-29 | SELECT 에 `ORDER BY spotify_id` 추가 — sentinel 없이도 충돌행이 batch head 를 점유하지 않게. | 1 |
| 2026-05-29 | `_COUNTRY_HINTS` 한국어 토큰 확장은 BUG-17 와 분리 — 별도 BUG-15 follow-up. | — |
