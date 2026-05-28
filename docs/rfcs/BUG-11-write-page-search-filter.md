# BUG-11: Writer page music search — album/track/artist filter not working correctly

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-28
- **Plan row**: `plan.md` → BUG-11

---

## Goal

글쓰기 페이지(`myblog_front` SubjectBlock)의 음악 검색에서 **앨범/트랙/아티스트 필터가 두 검색 버튼(DB 검색, Spotify 싱크) 모두에서 일관되게 동작**하고, 트랙 클릭이 source(DB|Spotify) 와 무관하게 부모 앨범 선택으로 라우팅되며, "전체" 필터 결과가 타입별 편향 없이 표시된다.

## Non-goals

- 백엔드(`myblog_music`) 검색 API 응답 스키마 변경. 응답은 이미 정상이며, 프론트 매핑/렌더링만 손본다.
- OpenAPI 계약 변경. `merged openapi.json` 재생성 불필요.
- 트랙 평점 기능 재도입(2026-05-28 롤백 결정 유지). 트랙은 "부모 앨범으로 가는 통로"로만 동작.
- 인프라(`infra/`) 변경.

## Current state

**파일**: `myblog_front/src/components/writer/SubjectBlock.tsx`, `myblog_front/src/components/writer/types.ts`

1. **DB 검색** (`runDBSearch`, line 53-114): `/api/music/search/unified?type=<filter>` 호출 → 응답 `albums + artists + tracks` 를 순차 concat 으로 `results` 배열에 넣음.
2. **Spotify 싱크** (`runSpotifySync`, line 116-156):
   - line 137-147: 응답에서 **`data.albums` 만 results 에 매핑**. `data.artists`, `data.tracks` 는 통째로 무시됨. ⚠️
3. **필터 UI** (line 27-32, 355-373): `전체 / 앨범 / 트랙 / 아티스트` 4개 버튼.
   - line 366: 힌트 텍스트 `"싱크 시 적용"` — 실제로는 DB 검색에도 적용되므로 거짓. ⚠️
4. **트랙 클릭 라우팅** (`onPick`, line 212-222): `sr.album_id` → `/api/music/albums/${album_id}` 단순 lookup.
   - `TrackSearchResult.album_id` (types.ts line 25) 는 DB UUID 가정.
   - Spotify candidate 응답의 트랙은 `album: { spotify_id, title, ... }` nested 구조 (`myblog_music/app/domain/schemas.py:141-149`) — 현재 프론트가 이를 받지 못함. ⚠️
5. **"전체" 필터 결과 순서**: albums 전체 → artists 전체 → tracks 전체 순. limit=20 + albums 가 20개면 첫 화면에 album 만 보임. ⚠️

## Target state

1. **Spotify 싱크 결과**: artist/track 도 렌더링. `runSpotifySync` 가 `runDBSearch` 와 동일하게 세 섹션을 매핑.
2. **TrackSearchResult**: `album_spotify_id: string | null` 필드 추가. DB 응답은 `album_id` (UUID) 채우고, Spotify 응답은 `album_spotify_id` (Spotify ID) 채움. 둘 중 정확히 하나는 항상 truthy.
3. **onPick(track)**: `source === 'spotify'` 이면 `/api/music/albums/by-spotify/{album_spotify_id}` 로 lookup, 그 외엔 `/api/music/albums/{album_id}`.
4. **필터 힌트**: `"DB·싱크 공통 적용"` 으로 수정.
5. **"전체" 필터**: round-robin 인터리브로 albums/artists/tracks 가 1개씩 섞여 표시.

## Steps

전부 단일 PR 로 머지(파일 2개, 동일 컴포넌트 흐름). Step 분리는 PR 내부 커밋 단위 가이드일 뿐 별도 머지 단위는 아님.

### Step 1 — Spotify 싱크 응답에 artists/tracks 매핑 추가

`runSpotifySync` (SubjectBlock.tsx:116-156) 에서 응답 매핑을 `runDBSearch` 구조와 동일하게 확장. albums(현재 유지) + artists + tracks 매핑 추가. interleave 적용은 Step 5 에서.

**검증**:
```
pnpm exec astro check && pnpm lint
```
브라우저 수동: 트랙 필터 + Spotify 싱크 → 결과 0개가 아니라 실제 트랙 카드 표시되는지.

### Step 2 — TrackSearchResult 에 album_spotify_id 추가

`types.ts:21-31` 에 `album_spotify_id: string | null` 필드 추가. `runDBSearch` 의 track 매핑은 `album_spotify_id: null` 로, `runSpotifySync` 의 track 매핑은 `t.album?.spotify_id ?? null` 로 채움.

**검증**:
```
pnpm exec astro check
```

### Step 3 — onPick 트랙 분기를 source 별로 라우팅

`SubjectBlock.tsx:212-223` 의 track 분기:

```typescript
if (sr.kind === 'track') {
  if (sr.source === 'spotify' && sr.album_spotify_id) {
    await selectAlbumByLookup({
      lookupUrl: `${API_BASE}/api/music/albums/by-spotify/${encodeURIComponent(sr.album_spotify_id)}`,
      source: 'spotify',
    })
  } else if (sr.album_id) {
    await selectAlbumByLookup({
      lookupUrl: `${API_BASE}/api/music/albums/${encodeURIComponent(sr.album_id)}`,
      source: 'db',
    })
  } else {
    setStatus('이 트랙의 앨범 정보가 없습니다.')
  }
  return
}
```

**검증**: 브라우저 수동 — DB 트랙 클릭 → 부모 앨범 선택 OK. Spotify 싱크 트랙 클릭 → 동기화 완료 시 부모 앨범 선택 OK. (동기화 진행 중이면 기존 `selectAlbumByLookup` catch 의 "아직 완료되지 않았습니다" 메시지)

### Step 4 — 필터 힌트 문구 수정

`SubjectBlock.tsx:366` 의 `"싱크 시 적용"` → `"DB·싱크 공통 적용"`.

**검증**: 시각 확인.

### Step 5 — "전체" 필터 결과 인터리브

`SubjectBlock.tsx` 결과 매핑부에 `interleave(albums, artists, tracks)` 헬퍼 도입 후, 필터가 `'all'` 일 때만 인터리브 사용. 단일 타입 필터는 동작 변화 없음.

```typescript
function interleave<T>(...arrays: T[][]): T[] {
  const max = Math.max(0, ...arrays.map(a => a.length))
  const out: T[] = []
  for (let i = 0; i < max; i++)
    for (const arr of arrays)
      if (i < arr.length) out.push(arr[i])
  return out
}
```

**검증**: 브라우저 수동 — "전체" 필터로 검색 시 album/artist/track 카드가 섞여 표시.

---

## Verification (overall)

**Pre-merge** (CLAUDE.md DoD):
- `pnpm lint` (메모리: front-lint-before-commit)
- `pnpm exec astro check`
- 로컬 DB 없을 경우 pytest 없이 위 두 가지로 갈음 (메모리: local-db-smoke-fallback)
- `terraform plan` — 해당 없음 (front-only)
- OpenAPI 재생성 — 해당 없음

**Post-merge**:
- prod smoke: 글쓰기 페이지에서 4 필터 × 2 버튼(검색/싱크) 매트릭스 수동 검증
  - "앨범" + 검색 / "앨범" + 싱크 / "트랙" + 검색 / "트랙" + 싱크 / "아티스트" + 검색 / "아티스트" + 싱크 / "전체" + 검색 / "전체" + 싱크
  - 트랙 클릭 시 부모 앨범 선택 흐름 (DB/Spotify 각각)
- 결과 PR 코멘트 인용 후 plan.md 행 제거.

## Rollback

Front-only, 단일 PR. 문제 발생 시 PR revert 1회로 원복 가능. 데이터 마이그레이션/스키마 변경 없음.

## Open questions

_(none — 사용자 결정 완료: Step 1-5 전체, 트랙/아티스트 검색 도구로 유지)_

## Decisions log

| Date       | Decision                                                                                    | Step |
|------------|---------------------------------------------------------------------------------------------|------|
| 2026-05-28 | 트랙/아티스트도 Spotify 싱크 결과에 노출 (검색 도구로 활용) — 사용자 결정                    | 1    |
| 2026-05-28 | "전체" 필터 인터리브 적용 (단일 타입 필터는 동작 영향 없음)                                  | 5    |
| 2026-05-28 | 트랙 평점 롤백 정책과 무관 — 트랙 검색은 "부모 앨범 통로" 로 유지 (`onPick` 기존 로직 보존) | 3    |
