# FEAT-header-scroll-prefs: 헤더 스크롤 거동 사용자 설정

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-06-04
- **Plan row**: `plan.md` → FEAT-header-scroll-prefs

---

## Goal

사이트 전역 헤더(`myblog_front/src/components/header.astro`)의 스크롤 거동을 **사용자가 세
방식 중 선택**할 수 있게 한다. 현재는 `sticky top-0` 하나만 있고, scroll 시 콘텐츠 가독성을
침해한다. 선택지: (a) **hide-on-scroll-down/show-on-scroll-up** (default), (b)
**compact-on-scroll**(높이 축소), (c) **threshold-based auto-hide**(첫 N px 후 사라짐). 선택은
`localStorage` 에 저장되고 페이지 새로고침/세션 간 유지된다. 프론트엔드 only — 백엔드/계약 변경 없음.

## Non-goals

- **모바일 햄버거 메뉴** — 별도 차례. 본 RFC 는 데스크톱 우선이고 모바일은 기존 거동 유지.
- **페이지별 다른 거동** — 사이트 전역 일관(Q5). `/reviews/queue` 의 가로 스크롤 컨테이너에도
  같은 정책 적용.
- **다크모드/테마 토글 통합** — 이미 `[data-theme=dark]` 시스템 별도 존재. 본 prefs 와 분리.
- **A11y 키보드 단축 모드 추가** — Section "Open questions" 로 미룸.

## Current state

- `src/components/header.astro:35` — `<header class="sticky top-0 z-50">` 단독.
- 외부 JS 0줄 (scroll listener 없음), padding-top 보정 없음, `scroll-margin` 없음.
- 모바일(<640px): 좌측 사이트 메타만 hide, nav 는 동일 라인.
- 헤더 클라이언트 스크립트 `src/scripts/header.client.ts` 는 popstate 기반 auth 동기화만 수행.
- 디자인 토큰 `src/styles/global.css` 의 `--z-sticky: 50`, header 색 `var(--color-bg)`.

## Target state

- `src/scripts/header.client.ts` 가 prefs 를 읽어 헤더 거동을 결정.
- 3가지 모드:
  - **`hide-on-scroll-down`** (default): `IntersectionObserver` 또는 `lastScrollY` 비교로
    아래로 스크롤 시 `transform: translateY(-100%)`, 위로 스크롤 시 복귀. transition 0.2s.
  - **`compact-on-scroll`**: 첫 N px(예: 80px) 스크롤 후 헤더에 `.is-compact` 클래스 추가 →
    padding/font-size 축소. 항상 보임.
  - **`threshold-hide`**: 첫 N px 스크롤 후 hide, 위로 살짝(예: 20px) 스크롤 시 show.
- 선택 UI: `/profile → 설정` 또는 헤더 자체의 작은 톱니 아이콘(추후 결정).
- localStorage 키: `lf:header-scroll-mode` 값 `'hide-down' | 'compact' | 'threshold'`.
- 디폴트는 `'hide-down'` (가독성 우선).

## Steps

> Rule #4: 세션당 1 step. 모두 frontend-only · single repo · single PR.

### Step 1 — 거동 구현 + prefs 읽기

`header.client.ts` 에 3 모드 구현, `lf:header-scroll-mode` localStorage 읽어 분기.
CSS 는 `global.css` 의 헤더 셀렉터에 `[data-scroll-mode="..."]` attribute selector 로 표현.
prefs UI 없이도 localStorage 직접 설정으로 동작 확인 가능 — 이 단계까지가 핵심 거동.

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: localStorage.setItem('lf:header-scroll-mode','hide-down') → 새로고침 → 스크롤 다운 시 헤더 숨김
# 세 모드 각각 동일 검증. /reviews/queue 가로 스크롤에서도 정상.
# Reduced motion (prefers-reduced-motion): transition 0
```

**Rollback**: `header.client.ts` 의 새 스크립트 블록 제거 + CSS 셀렉터 revert. 기존 sticky 거동 복귀.

---

### Step 2 — prefs UI

선택 UI 가 들어갈 위치 결정 후(Open Q1) 구현. 3개 라디오 + 디폴트 표시. 변경 즉시 반영(이벤트 dispatch).

**Verification**:

```
cd myblog_front && pnpm lint && pnpm exec astro check
# browser: UI 에서 모드 변경 → 새로고침 없이 즉시 적용 → localStorage 갱신 확인
```

**Rollback**: UI 컴포넌트만 제거. Step 1 동작은 유지.

---

## Open questions

1. **prefs UI 위치 (blocks Step 2)** — `/profile → 설정` 탭(`SettingsMenu` 가 이미 존재,
   현재 view 토글만) 안에 한 줄 추가 vs 헤더 자체의 작은 톱니 아이콘. 추천: SettingsMenu 확장.
2. **threshold 값** — N px 의 디폴트. 80px(헤더 한 줄 높이) 합리적이나 모바일은 다를 수 있음.
3. **a11y: focus 시 헤더 강제 표시** — focus 가 헤더 안으로 들어오면 mode 무관하게 표시? 권장: yes.
4. **`/reviews/queue` 가로 스크롤 컨테이너 영향** — 이 페이지는 본문이 가로 스크롤이라 헤더
   `scroll` 이벤트가 페이지 세로 스크롤 기준인지 확인. (예상: 별 문제 없음 — 헤더는 viewport 세로 기준.)

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-06-04 | 3 모드(hide-down / compact / threshold) 모두 선택 가능, 사용자 결정 — 사용자 결정 | 1 |
| 2026-06-04 | 디폴트 = hide-on-scroll-down (가독성 우선) — 권장 | 1 |
| 2026-06-04 | 사이트 전역 일관 (페이지별 다른 거동 X) — Q5 권장 | 1 |
| 2026-06-04 | 모바일 햄버거 본 RFC 범위 밖 — Q6 권장 | — |
| 2026-06-04 | prefs 저장 = `localStorage`, key `lf:header-scroll-mode` (백엔드 unused, 단일 사용자) | 1 |
