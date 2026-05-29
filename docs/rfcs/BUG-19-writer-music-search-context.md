# BUG-19: writer 음악 검색 — feat 아티스트 누락 + artist→album/track 확장 부재

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: `plan.md` → BUG-19

---

## Goal

글쓰기 페이지 (`myblog_front/src/components/writer/SubjectBlock.tsx`) 와 전역 검색바 (`myblog_front/src/scripts/searchBarDb.client.ts`) 의 음악 검색 결과에서, 한 트랙에 참여한 모든 아티스트가 곡 제목 텍스트에 "feat. X" 가 박혀있는지와 무관하게 표시된다. DB · worker sync 는 이미 `track_artists` N:N 으로 모든 참여 아티스트를 정상 저장하고 있고, 같은 백엔드의 `AlbumDetail.TrackOut.feat_artist_names` 가 이미 list 로 노출 중인 비대칭만 해소한다.

artist 이름으로 검색했을 때 그 artist 의 album/track 까지 함께 나오게 하는 "related search" 는 **본 RFC 의 Step 1 범위 밖**이고, Step 1 prod 관찰 후 별도 결정한다 (Step 2 placeholder 참조).

## Non-goals

- artist match → 그 artist 의 album/track 자동 보강 (related search). Step 2 의 사전 결정 대상.
- ranking / cross-bucket dedup / 새 endpoint 설계. Step 2 가 필요할 때 결정.
- Spotify sync 의 track-artist 저장 로직 변경. 이미 정상 (`myblog_worker/worker/service/sync_service.py:105-110, 186-198`).
- MusicBrainz alias 기반 검색 정교화. BUG-14 영역.
- `AlbumDetail.TrackOut` 의 기존 `feat_artist_names` 구성 규칙 변경. album_service 는 그대로.
- 곡 제목 텍스트의 "feat. X" 정규화/제거. Spotify 가 그렇게 주는 그대로 유지.

## Current state

**DB / sync (정상)**:
- `myblog_shared_db/src/myblog_shared_db/models.py:170-193` — `Track` 에 `artist_id` FK 없음. `track ↔ artist` 는 순수 N:N (`track_artists` 조인 테이블, line 46-51).
- `myblog_worker/worker/service/sync_service.py:105-110, 186-198` — Spotify `t["artists"]` 전체 루프 후 `track_artists` 에 모두 INSERT.

**백엔드 검색 응답 (병목 #1)**:
- `myblog_music/app/api/routers/search.py:20-37` + `app/services/search_service.py:27-47` — artist/album/track 완전 병렬 독립 검색.
- `app/repositories/track_repo.py:29-41` — `search_by_title` 이 `selectinload(Track.album).selectinload(Album.artists)` + `selectinload(Track.artists)` 둘 다 eager-load. **N+1 위험 없음**.
- `app/mappers/track_mapper.py:14-21` — `track.artists[0].name` 첫 1명만 뽑아 `artist_name` 에 채움. album_artists fallback.
- `app/domain/schemas.py:36-51` — `TrackItem.artist_name: Optional[str]` **단일 필드**. feat list 없음.
- 비대칭: `schemas.py:67-73` 의 `TrackOut.feat_artist_names: List[str]` 은 이미 list 로 노출. 구성 규칙은 `app/services/album_service.py:46-49`:
  ```python
  feat_artist_names=sorted(
      ta.name for ta in (t.artists or [])
      if ta.id not in album_artist_ids and ta.name
  )
  ```

**프론트 (병목 #2)**:
- `myblog_front/src/components/writer/SubjectBlock.tsx:76-106` — `TrackSearchResult.artist_name: string | null` 단일 필드만 매핑. feat list 받을 그릇 없음.
- 렌더링 (`SubjectBlock.tsx:414-415`): `${r.artist_name} · ${r.album_title}` — feat 표시 미지원.
- `myblog_front/src/scripts/searchBarDb.client.ts:10, 103-104` — `mapDBTracksUnified` 가 같은 패턴으로 `Music_TrackItem` 의 `artist_name` 만 사용.
- `myblog_front/src/lib/api.gen.ts:658-681` — generated `Music_TrackItem` 의 `artist_name?: string | null` 단일.

→ DB 엔 모두 있는데 검색 응답이 첫 1명만 노출, 프론트도 그것만 받음. 사용자가 "feat 가 곡 제목에 들어있을 때만 보인다" 고 느끼는 증상의 원인.

## Target state

**백엔드** (`myblog_music`):
- `app/domain/schemas.py` 의 `TrackItem` 에 `feat_artist_names: List[str] = Field(default_factory=list)` 추가. 기존 `artist_name: Optional[str]` 유지.
- `app/mappers/track_mapper.py` 가 `artist_name` (대표 1명) 외 나머지 track artists 를 알파벳순 정렬해 `feat_artist_names` 로 노출.
- 변형 규칙: album_service 와 달리 **representative `artist_name` 자체를 제외**. 이유는 검색 응답에는 `album.artists` 메타가 없어 클라이언트가 album primary 를 가르킬 수 없고, UI 는 `${artist_name} (feat. ${feat...})` 로 표시하므로 representative 중복만 막으면 자연스러움. (compilation album, 예: `album.artists=[Various Artists]`, `track.artists=[BTS, Halsey]` 케이스에서 album_service 규칙을 그대로 복사하면 "BTS (feat. BTS, Halsey)" 중복.)

**프론트** (`myblog_front`):
- `pnpm generate:types` 로 `api.gen.ts` 재생성 — `Music_TrackItem.feat_artist_names?: string[]` 노출.
- `SubjectBlock.tsx` 의 `TrackSearchResult` 타입 + 매핑 + 렌더링에 feat list 반영. 표시 패턴 잠정: `${artist_name}${feat?.length ? ` (feat. ${feat.join(', ')})` : ''} · ${album_title}` (Open Q1).
- `searchBarDb.client.ts:103-104` `mapDBTracksUnified` 도 동일 패턴.

기존 `artist_name` 단일 필드는 유지 — 기존 consumer 코드 호환성 유지.

## Steps

### Step 1 — TrackItem 에 feat_artist_names 추가 (single PR, contract change)

`myblog_music` + workspace contract regen + `myblog_front` 를 한 PR 에 묶는다 (분리 머지하면 contract drift 또는 frontend 가 백엔드 새 필드 무시).

**`myblog_music` 변경**:

- `app/domain/schemas.py:36-51` `TrackItem` 클래스:
  - `feat_artist_names: List[str] = Field(default_factory=list)` 한 줄 추가.
- `app/mappers/track_mapper.py:14-21`:
  - `artist_name` 결정 로직은 유지.
  - 결정된 `artist_name` 을 제외한 `track.artists` 의 나머지 이름들을 알파벳순 정렬해 `feat_artist_names` 로 채움.
  - `track.artists` 가 비어 album_artists fallback 으로 갔다면 `feat_artist_names = []`.
  - 의사 코드:
    ```python
    primary = artist_name
    feat = sorted(
        a.name for a in (track_artists or [])
        if a.name and a.name != primary
    )
    ```
- openapi 재생성:
  - `cd myblog_music && pytest tests/ -k openapi` (또는 해당 레포 spec 빌드 명령) 으로 `openapi.json` regen + commit.
- 단위 테스트 (`tests/test_track_mapper.py` 신설 또는 기존 파일에 추가):
  - track.artists=`[A, B]`, artist_name=A → `feat_artist_names=[B]`.
  - track.artists=`[A]` (단일) → `feat_artist_names=[]`.
  - track.artists=`[]`, album_artists=`[X]` → `artist_name=X`, `feat_artist_names=[]`.
  - track.artists=`[BTS, BTS]` (중복 가능성, 데이터 보호) → primary BTS 제외 후 빈 list.
  - track.artists=`[A, B, A]` (drop primary 후 잔여 중복) → `[A]` 잠재 아님 — 정렬+제거. (Open Q3 참조)

**Workspace contract regen**:

- `python scripts/merge_openapi.py` 로 `docs/contracts/openapi.json` regen + commit.

**`myblog_front` 변경**:

- `pnpm --filter myblog_front generate:types` 로 `src/lib/api.gen.ts` 재생성 + commit ([[feedback-frontend-api-gen-sync]]).
- `src/components/writer/SubjectBlock.tsx`:
  - line 76-106 의 `tracks` 매핑에 `feat_artist_names: t.feat_artist_names ?? []` 추가.
  - `TrackSearchResult` 타입 정의 (`src/scripts/types/search.ts` 또는 동일 파일) 에 `feat_artist_names?: string[]` 추가.
  - line 414 표시 패턴: `${r.artist_name}${r.feat_artist_names?.length ? ` (feat. ${r.feat_artist_names.join(', ')})` : ''} · ${r.album_title}`.
- `src/scripts/searchBarDb.client.ts:103-104` `mapDBTracksUnified` 도 동일 패턴.

**Verification (local)**:

```
cd myblog_music && pytest tests/test_track_mapper.py -v
cd myblog_music && ruff check app/
cd myblog_front && pnpm lint && pnpm exec astro check
```

Local smoke (DB optional, [[feedback-local-db-smoke-fallback]]): pytest + lint + astro check + 신규 mapper 단위 테스트 그린이면 충분 — 검색 API 자체는 prod smoke 로 최종 확인. UI 변경 있으므로 dev server 띄워 SubjectBlock + 전역 검색바 양쪽 브라우저 클릭 검증 ([[feedback-browser-verify-ui-changes]]).

**Prod smoke** (post-merge):

- prod `/api/music/search/unified?q=<feat 있는 곡>&type=track&limit=10` → 응답 JSON 에 `feat_artist_names` 가 list 로 노출되는지 + representative 가 list 에 중복 안 되는지 확인.
- 글쓰기 페이지 prod 에서 같은 q 로 검색 → UI 에 ` (feat. ...)` 표시되는지 + 곡 제목 텍스트의 "feat. X" 와 중복 표시 안 되는지 (Open Q2).
- compilation album 표본 (있다면) 도 같이 — `album.artists=[Various Artists]` 패턴에서 representative 가 BTS 같은 진짜 primary 로 잡히고 list 에 중복 없는지.

**Rollback**: PR revert. 스키마는 optional list 추가 + 단일 필드 유지라 기존 consumer 깨짐 없음. 데이터 mutation 없음.

---

### Step 2 — artist→album/track 확장 (Step 1 prod 관찰 후 별도 결정)

**Status**: deferred. Step 1 prod 검증 후 사용자가 "feat 보여도 흐름은 여전히 끊긴다" 고 판단할 때 본 Step 의 방향을 결정.

후보:
- **A. unified search 에 related search 추가** — artist match → 그 artist 의 album/track 보강. ranking / cross-bucket dedup / grouping 스키마 신설 필요. 함정: BUG-15 sentinel 게이트 / SA session lifecycle 같은 회귀 위험. 별도 RFC 로 ranking 규칙 사전 못박고, 실엔진 통합 테스트로 conn-pool/N+1 영향 확인 의무.
- **B. artist 선택 → 별도 endpoint + 클릭 흐름 분리** — 새 라우터 (`/api/music/artists/<id>/discography` 같은) + 프론트 클릭 시 추가 fetch. 현재 `SubjectBlock.tsx:264-266` 이 artist 클릭 시 query 교체 + filter='album' 재검색을 사용자에게 떠넘기는 구조라 B 는 자연스럽지만 구현 자체는 작지 않음.

방향 결정 시 별도 RFC 분리. 본 RFC 는 Step 1 만으로 닫고, Step 2 가 결정되면 BUG-19-step2 또는 새 RFC 로 이어감.

---

## Open questions

1. **UI 표시 패턴 — `${artist_name} (feat. ${feat_artist_names.join(', ')}) · ${album_title}` 가 곡 제목에 이미 "feat. X" 가 박혀있는 케이스와 중복되지 않는가** — 잠정: 백엔드는 raw 데이터만 노출, 표시는 그대로. 곡 제목 텍스트의 "feat. X" 와 응답의 `feat_artist_names` 중복 표시는 prod smoke 후 빈도 보고 판단. 잠재 후속: mapper 에서 `track.title` substring 검사로 list 항목 제거? 결정은 prod 표본 후. (Step 1 영향, 표시만 영향).
2. **representative 중복 케이스 빈도** — compilation album (`album.artists=[Various Artists]`) 또는 representative 가 `track.artists[0]` 이 아니라 album_artists fallback 으로 잡힌 경우의 prod 빈도. mapper 의 `if a.name != primary` 가드는 이름 같음 기준이라 이름이 같은 다른 artist 있으면 false-negative (정상 표시 안 됨). prod 표본 분포 보고 ID 기준 비교로 바꿀지 결정. (Step 1 영향).
3. **`feat_artist_names` 정렬 기준** — album_service 는 알파벳순 (`sorted(...)`). 본 RFC Step 1 도 동일 적용. UI 일관성 우선. 만약 prod 에서 "원래 등장 순서" 표시 선호가 나오면 별도 결정. (Step 1 영향, 잠정 결정: 알파벳순).
4. **Step 2 방향** — A vs B 는 Step 1 prod 관찰 후 사용자가 판단. 본 RFC 안에서 결정하지 않음. (Step 2 영향).

## Decisions log

| Date       | Decision                                                                                                                                                                                                              | Step |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| 2026-05-29 | 두 증상 (artist→album/track 미확장 / feat 누락) 은 서로 다른 문제로 분리. Step 1 = feat 응답 보강 only. Step 2 (related search) 는 deferred 후 prod 관찰 후 재결정.                                                    | 1, 2 |
| 2026-05-29 | mapper 변형 규칙 — album_service 의 `if ta.id not in album_artist_ids` 가 아니라 검색 응답에서는 `if a.name != primary`. 이유: 검색 응답에 album.artists 메타 없음 + UI 가 `${artist_name} (feat. ...)` 로 표시하므로 representative 중복만 제거하면 됨. | 1    |
| 2026-05-29 | 기존 `artist_name: Optional[str]` 필드 유지. 새 `feat_artist_names: List[str]` 만 추가. 양쪽 호환성 깨짐 없음.                                                                                                          | 1    |
