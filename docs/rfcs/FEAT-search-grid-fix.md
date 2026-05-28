# FEAT-search-grid-fix: 검색 결과 그리드 수정 (카드 크기 불균일 + 가로 스크롤)

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-05-29
- **Plan row**: `plan.md` → FEAT-search-grid-fix
- **회의록 출처**: `~/.claude/plans/soft-hatching-raccoon.md` (2026-05-29 v2, B+C 통합)

---

## Goal

검색 결과(통합 검색의 앨범/아티스트/트랙 grid)에서 (1) 카드 높이 불균일 (2) 가로 스크롤 발생 두 가지를 한 PR 로 해결. 카드 이미지에 `aspect-ratio: 1 / 1; object-fit: cover` 적용 + 결과 컨테이너를 `grid-template-columns: repeat(auto-fill, minmax(...))` 반응형 grid 로 전환한다. 워커 측 커버 해상도 들쭉날쭉이 추가 원인으로 확인되면 그 인덱스를 medium 으로 고정.

## Non-goals

- 검색 동작 자체 변경 (정렬, 점수, 필터). UI 만.
- 무한스크롤 / 페이지네이션 도입. 회의록 v2 에서 over-engineering 로 드롭.
- 카드 디자인 전면 개편. 색·폰트·여백은 현 토큰 유지.
- View 페이지(`blog/[slug].astro`) 의 트랙 그리드 등 다른 화면. 별도 작업.
- DB 의 cover_url 정규화 backfill. 워커 인덱스 고정만으로 신규/재싱크 시 자동 해소.

## Current state

**증상 (스크린샷 진단, 2026-05-29):**
1. 카드 높이 불균일 — 앨범 커버 원본 비율 그대로 들어가 세로 인물 / 정사각 / 가로형이 뒤섞이는 grid
2. 가로 스크롤 오작동 — 3열이어야 할 결과 영역이 고정폭으로 넘쳐 오른쪽 카드 잘림 + 가로 스크롤바

**파일 후보 (선조사 전, 추정):**
- 카드 컴포넌트: `myblog_front/src/scripts/components/makeCard.ts:19` (cover_url 사용 지점)
- 검색 결과 컨테이너: `myblog_front/src/scripts/searchBarDb.client.ts:88-100` (3섹션 렌더), grid CSS 정의 위치 미확인 — Step 0 에서 특정
- Spotify 이미지 인덱스: `myblog_worker/worker/service/sync_service.py` 의 album/artist upsert 로직 — `images[]` 중 어느 인덱스를 cover_url 로 저장하는지 미확인

## Target state

- 카드 이미지 요소: `aspect-ratio: 1 / 1; object-fit: cover; width: 100%;` — 어떤 원본 비율이 와도 정사각 카드
- 결과 컨테이너 grid: `display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px;` (정확한 minmax 값은 Step 0 에서 디자인 참고로 확정). 가로 overflow 없음
- 모바일 viewport (≤640px) 에서 자연스럽게 2열 또는 1열로 적응
- (조건부) 워커가 Spotify `images[]` 의 medium 인덱스(보통 `[1]`) 를 cover_url 로 저장하도록 고정. 신규 sync 부터 일관 해상도

## Steps

### Step 0 — 선조사 (30분, 별도 PR 아님)

**확인 항목:**
1. `myblog_front/src/scripts/searchBarDb.client.ts` 의 grid 렌더 위치 + 현재 CSS (Astro 스타일 / Tailwind / 외부 css)
2. `myblog_front/src/scripts/components/makeCard.ts` 의 이미지 요소 — 현재 `object-fit` 적용 여부, 크기 단위
3. `myblog_worker/worker/service/sync_service.py` 의 album/artist upsert — Spotify `images[]` 중 어느 인덱스를 cover_url 로 저장
4. 모바일 viewport 에서 grid 가 어떻게 깨지는지 dev tools 로 재현

**결과물:** Step 1 변경 위치 + Step 2 진행 여부(워커 인덱스 일관/불일관) 확정.

---

### Step 1 — CSS 그리드 + aspect-ratio 적용 (단일 PR)

**변경 파일 (Step 0 후 확정):**
- 카드 컴포넌트의 이미지 요소 CSS — `aspect-ratio: 1 / 1; object-fit: cover; width: 100%;`
- 결과 컨테이너 CSS — `grid-template-columns: repeat(auto-fill, minmax(160px, 1fr))` (값 디자인 참고 후 확정)
- 가로 overflow 제거 (필요 시 컨테이너 `overflow-x: hidden` 또는 부모 `width: 100%`)

**Verification:**
```bash
cd myblog_front && pnpm lint
cd myblog_front && pnpm exec astro check
cd myblog_front && pnpm dev
# 1. 검색에 '빈지노' 등 다건 결과 입력 → 카드 크기 균일 + 가로 스크롤 없음
# 2. 모바일 viewport (devtools 375px) 에서 1~2열 적응 확인
# 3. 큰 viewport (1440px) 에서 카드가 너무 커지지 않는지 확인
```

**Rollback**: revert 단일 PR. CSS 변경만이라 안전.

---

### Step 2 — (조건부) 워커 커버 인덱스 고정

**진행 조건:** Step 0 결과로 워커가 `images[]` 의 인덱스를 일관되지 않게 (또는 가용한 첫 번째) 저장하는 것이 확인된 경우만.

**변경 파일:**
- `myblog_worker/worker/service/sync_service.py` — album/artist upsert 에서 cover_url 선택을 `images[1] if len(images) > 1 else images[0] if images else None` 로 명시
- 또는 Spotify 응답에서 width 가 가장 가까운 해상도(예: 300px) 를 선택하는 헬퍼 추가

**주의:** 기존 DB 의 cover_url 은 그대로 둠 — Step 1 의 CSS `object-fit: cover` 가 시각 일관성을 잡으므로 backfill 불필요. 새로 sync 되는 앨범부터 일관 해상도.

**Verification:**
```bash
cd myblog_worker && uv run pytest tests/ -k "sync"
# SQS 메시지 1건 로컬 처리 → DB cover_url 확인 (선택된 인덱스의 url 인지)
```

**Rollback**: revert 단일 PR. 기존 데이터에 영향 없음.

---

## Open questions

1. **결과 컨테이너 grid 가 어디 CSS 에 정의되어 있나** — Astro 컴포넌트 scoped style? Tailwind utility? 외부 .css? Step 0 에서 특정. Blocks Step 1.
2. **minmax 값 (160px 같은 카드 최소폭)** — 현재 카드 디자인 시각 비율 확인 후 확정. Blocks Step 1.
3. **워커 cover_url 인덱스 일관성** — Step 0 결과에 따라 Step 2 진행 여부 결정. Blocks Step 2.
4. **검색 외 화면에서도 동일 카드 컴포넌트 쓰이나** — view 페이지의 추천 영역, 메인 carousel 등에서 같은 makeCard 호출 시 의도치 않은 시각 변경 발생 가능. Step 0 에서 호출처 grep. Blocks Step 1.

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-05-29 | B(스크롤)+C(이미지 크기)를 단일 PR 로 통합 | All |
| 2026-05-29 | 무한스크롤/페이지네이션 도입 X | Non-goal |
| 2026-05-29 | DB cover_url backfill X — CSS 로 시각 일관성만 | Step 2 |
