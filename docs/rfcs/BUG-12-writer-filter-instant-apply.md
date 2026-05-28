# BUG-12: Writer page filter buttons — instant client-side apply

- **Status**: accepted
- **Owner**: TBD
- **Created**: 2026-05-28
- **Plan row**: `plan.md` → BUG-12

---

## Goal

글쓰기 페이지(`myblog_front` SubjectBlock)의 필터 버튼(전체/앨범/트랙/아티스트) 클릭이 **즉시** 화면 결과에 반영된다. 백엔드 재호출 없이 이미 받은 결과를 클라이언트사이드에서 거른다. BUG-11 에서 백엔드 API smoke 만 검증하고 UI 인터랙션을 사용자에게 떠넘긴 결과 빠진 버그를 해결.

## Non-goals

- 백엔드 검색 API 응답/스키마 변경.
- 필터 변경 시 자동 재검색 (UX 결정상 클라이언트사이드 거름 단독으로 진행 — Spotify cooldown 충돌 회피).
- 인터랙션 외 시각 디자인 변경.

## Current state

**파일**: `myblog_front/src/components/writer/SubjectBlock.tsx`

1. `filterToType(filter)` (line 36-38): 필터 → 백엔드 type 파라미터. `'album,artist,track'` 또는 단일 타입.
2. `runDBSearch` / `runSpotifySync`: `typeParam = filterToType(filter)` 로 백엔드 호출 — **검색 시점의 filter 값** 만 백엔드에 전달.
3. 필터 버튼 onClick (line 401): `setFilter(f.v)` 만 호출. 재검색·재필터링 없음. ⚠️
4. 결과 렌더링 (line 417): `results.map(...)` — `results` 그대로 표시.

→ 사용자가 검색 후 필터를 바꿔도 화면 결과 불변. "검색" 버튼을 다시 눌러야 새 필터로 반영됨. UX 직관 위배.

## Target state

1. `runDBSearch` / `runSpotifySync`: 백엔드 호출은 항상 `type=album,artist,track` (모든 타입) 로 고정. 클라이언트가 데이터를 충분히 들고 있도록.
2. 결과 렌더링: `visibleResults = useMemo(...)` 로 `filter` 적용한 결과를 렌더. `filter==='all'` → 전체 (인터리브된 상태 그대로). `filter==='album'|'artist'|'track'` → `r.kind===filter` 만 통과.
3. `filterToType` 제거 (미사용).
4. 필터 카운트 (`hdr-count`): `visibleResults.length` 로.
5. 필터 힌트 문구: `"즉시 적용"` 으로 변경 (실제 동작 반영).

## Steps

단일 PR (front-only, 1 파일 중심).

### Step 1 — 백엔드 호출 type 고정 + filterToType 제거

`runDBSearch` / `runSpotifySync` 의 `typeParam` 을 `'album,artist,track'` 하드코드. `filterToType` 함수 + 사용처 제거.

### Step 2 — visibleResults useMemo 추가

```typescript
const visibleResults = useMemo(
  () => filter === 'all' ? results : results.filter(r => r.kind === filter),
  [results, filter],
)
```

### Step 3 — 렌더링 results → visibleResults

`hdr-grid` 내부 `results.map` 과 카운트 표시 부분에서 `visibleResults` 사용. 빈 상태 처리는 results 그대로 사용 (검색 자체 여부는 results 로 판단).

### Step 4 — 필터 힌트 문구

`"DB·싱크 공통 적용"` → `"즉시 적용"`.

### Step 5 — 로컬 브라우저 매트릭스 검증

`pnpm dev` 띄우고 다음 매트릭스 직접 클릭 확인:
- "라디오헤드" 검색 → 4 필터 즉시 토글 (album/track/artist/전체) → 화면 결과 즉시 변화
- "전체" 필터에서 인터리브 순서 유지
- 트랙 카드 클릭 → 부모 앨범 선택 (DB 라우팅)
- Spotify 싱크 후 동일 매트릭스 (단, 외부 API 호출 부담 고려해 1회만)

## Verification

**Pre-merge**:
- `pnpm lint`
- `pnpm exec astro check`
- **로컬 dev server 띄워 4 필터 × 2 검색 매트릭스 브라우저 직접 확인** ← BUG-11 회귀 재발 방지

**Post-merge**:
- prod auto-deploy 완료 대기
- `./scripts/smoke.sh prod` (regression guard — API 변경 없으므로 통과 예상)
- prod 글쓰기 페이지에서 필터 즉시 반응 1회 확인
- plan.md row 제거

## Rollback

Front-only 단일 PR. 1회 revert 로 원복.

## Open questions

_(none)_

## Decisions log

| Date       | Decision                                                                   | Step |
|------------|----------------------------------------------------------------------------|------|
| 2026-05-28 | 자동 재검색(옵션 A) 대신 클라이언트 필터링(옵션 B) 선택 — Spotify cooldown 충돌 회피, 즉시 반응 확보 | 1-3  |
| 2026-05-28 | 백엔드는 항상 모든 type 받기 — limit=20 × 3 ≤ 60개라 부담 무시 가능       | 1    |
