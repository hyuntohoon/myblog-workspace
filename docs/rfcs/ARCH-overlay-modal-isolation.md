# ARCH-overlay-modal-isolation: 오버레이 공통 계약 — 스크롤 락 입양 + `AddToBucketMenu` 모달 시맨틱스

- **Status**: draft
- **Owner**: TBD
- **Created**: 2026-08-06
- **Plan row**: `plan.md` → ARCH-overlay-modal-isolation
- **Partial prerequisite shipped 2026-08-06**: album-card Stage 7 (front #382, `775f683`) registered
  `AddToBucketMenu` with `useDismissable` and verified autofocus, Tab trapping, top-layer Escape,
  and trigger-focus restoration in a real 390×844 browser. This removes that part of Step 3; scroll
  locking, overscroll containment, and the remaining overlay adoption sweep stay in this RFC.
- **형제, 재론하지 않음**: `docs/rfcs/ARCH-entity-interaction-domain-audit.md` Step 4(완료, front #357) — ESC 키 해제 + 포커스 트랩(`useDismissable`) 7개 컴포넌트 이관은 이미 끝났고 이 RFC는 그 결정을 다시 열지 않는다. 이 RFC가 다루는 것은 Step 4가 **다루지 않은** 두 축 — 배경 스크롤 락(`useScrollLock`)의 입양 격차, 그리고 `AddToBucketMenu`(Step 4에서 명시적으로 범위 밖으로 남겨진 컴포넌트) 하나의 모달 시맨틱스 전체 — 이다.
- **근거**: 2026-08-06 오너 지시로 돌린 아키텍처 감사, 두 개 병렬 조사(항목 10: 스크롤 격리 27개 오버레이 인벤토리, 항목 11: `AddToBucketMenu` a11y 전면 트레이스) — 세션 스크래치패드 `inv-5-modal-scroll-isolation.md` / `inv-6-addtobucketmenu-a11y.md`. front 인용 HEAD: `cc16ab49a08166a035701450588bcbea78431b09`.

---

## Goal

배경 스크롤 락을 부르는 오버레이와 안 부르는 오버레이가 27개 중 11:16으로 갈린 지금의 상태를 없앤다 — 새 오버레이를 만드는 사람이 "이번엔 스크롤 락을 기억해야 하나"를 고민하지 않도록, 오버레이 공통 계약(스크롤 락 + `useDismissable`의 ESC/포커스트랩 + 중첩 스택)을 한 곳에서 함께 얻게 한다. 동시에 `AddToBucketMenu`가 선언만 하고 구현하지 않은 `role="dialog" aria-modal="true"`를 실제로 충족시킨다.

## Non-goals

- **`useDismissable`(ESC/포커스트랩) 자체를 다시 설계하지 않는다** — 그 훅과 `openStack` 메커니즘은 이미 검증됐고(`ARCH-entity-interaction-domain-audit` Step 4), 이 RFC는 `AddToBucketMenu`를 그 계약에 **가입**시키는 것이지 계약 자체를 바꾸는 게 아니다.
- **`useScrollLock`의 refcount/언마운트-해제 메커니즘을 다시 설계하지 않는다** — 감사 결과 이 부분은 이미 올바르게 설계돼 있다(§Current state). 문제는 메커니즘이 아니라 **입양**이다.
- **`AddToBucketMenu`/`BucketPickerSheet` 병합을 재론하지 않는다** — `ARCH-entity-interaction-domain-audit`가 이미 독립적으로 재검토해 정당하다고 결론지었다(다른 일을 함).
- **배경 비활성화(`inert`/`aria-hidden`)를 이 RFC의 필수 스코프로 강제하지 않는다** — 감사에서 확인된 대로 이건 `AddToBucketMenu` 하나만의 결함이 아니라 `useDismissable` 자체가 아직 안 가진 앱 전역 기능이다. Step에서 다루되, 이 RFC가 실패하는 조건으로 삼지는 않는다(Open questions 참고).
- **iOS `position:fixed` 기법·`overscroll-behavior` 도입의 실기기 검증을 이 RFC의 스텝 완료 조건으로 강제하지 않는다** — 코드 레벨 완화는 스텝에 포함하되, 실기기 확인은 오너 검증 항목으로 명시(§16 검증 전략 참고, 브라우저 도구 없이 진행된 조사의 한계).
- **모바일 내비게이션 드로어(`header.client.ts`)의 별도 락 구현을 이 RFC로 흡수하지 않는다** — 존재는 기록하되(§Current state), `role="dialog"`가 아닌 바닐라 JS 컴포넌트라 이 RFC의 스코프(React `role="dialog"` 오버레이) 밖으로 명시.

## Current state

**메커니즘 자체(`src/lib/useScrollLock.ts`, 39줄)는 잘 설계돼 있다** — 모듈-레벨 `lockCount` + 최초 진입 시 한 번만 저장하는 `prevOverflow`로 중첩에 안전하고(먼저 연 게 나중에 닫혀도 카운트만 줄어듦), `useEffect` cleanup이 언마운트·라우트 변경 어디서든 확실히 해제한다. 잠그는 대상은 `document.body`만(`documentElement`도 개별 스크롤 컨테이너도 아님).

**문제는 입양이다.** 스크림이 있는 `role="dialog"` 오버레이 27개 인벤토리 중 **16개가 이 훅을 아예 안 부른다** — `BucketBoard.tsx` 한 파일 안에서도 연구노트 모달(`useScrollLock(!!researchTarget)`, `:1841`, 명시적 주석까지 있음)만 걸려 있고 몇백 줄 떨어진 휴지통 서랍·버킷 삭제 확인 모달은 안 걸려 있다. 갭이 있는 컴포넌트: `TrashDrawer`, 버킷-삭제 확인, `ActionSheet`, `BucketPickerSheet`, `ImportAnalysis`(리스닝 분석 상세), `RecentAlbumsModal`/`RecentTracksModal`, 리뷰-삭제 확인, `AddToBucketMenu`, `PocketDesignSettings`, 라이터 앱 전체(`CommandPalette`/`DraftsInbox`/`SettingsPanel`/리서치 드로어), 장르맵 `Peek`. 다섯 개 서로 다른 기능 영역에 걸쳐 있고 같은 파일 안에서도 갈린다 — 한 번에 여러 PR이 각자 만들면서 매번 다시 기억해야 하는 구조라는 뜻이다.

**추가로, 락이 걸리는 오버레이에서도 세 가지가 전혀 없다**(전체 트리 grep 0건): (a) 클래식 스크롤바 플랫폼(Windows/Linux 데스크톱)에서 스크롤바 폭만큼의 레이아웃 시프트를 막는 `padding-right`/`scrollbar-gutter` 보정, (b) iOS Safari의 `overflow:hidden`이 터치 스크롤을 확실히 못 막는 문제에 대한 `position:fixed`+오프셋 완화, (c) 내부 스크롤 경계에서 바깥으로 새는 걸 막는 `overscroll-behavior: contain`(모달 프리미티브 어디에도 없음, 무관한 CSS 4곳에만 존재).

**The audit's `AddToBucketMenu` keyboard defect is resolved.** Front #382 registered the picker
portal with `useDismissable`, attached the dialog ref, and added a nested-host regression test. A
real 390×844 browser pass confirmed initial focus, Tab wrap, top-layer Escape, and focus restoration.
The picker still lacks `useScrollLock` and overscroll containment, so it remains in the 16-component
scroll-isolation gap counted above. Visual z-index stacking remains unchanged and correct (96 > 90).

## Target state

- 새 오버레이가 소비하는 **하나의 조합 훅**(가칭 `useOverlayContract` 또는 기존 `useDismissable`을 확장)이 ESC/포커스트랩(기존)과 스크롤 락(신규 통합)을 한 호출로 제공 — 개별로 두 훅을 각자 기억해서 부르는 지금 방식 대신, 부르면 둘 다 딸려온다.
- `component-map.md`의 모달/오버레이 레지스트리가 "이 오버레이가 스크롤 락을 거는가"를 컬럼으로 갖는다(지금은 ESC/포커스트랩 상태만 있음) — 신규 오버레이 PR 리뷰에서 빠짐없이 확인 가능.
- `AddToBucketMenu`가 `useDismissable`의 `openStack`에 정식으로 등록돼 있어 중첩 컨텍스트(현재 `AlbumDetail`/`ImportAnalysis`)에서 ESC가 항상 최상단 오버레이만 닫는다. 초기 포커스, 포커스 트랩, 닫을 때 트리거 요소로 포커스 복원이 구현돼 있다.
- 락이 걸리는 모든 모달 프리미티브(`.scrim`/`.slideover`, `.bps-sheet`, `.qb-modal`, `AddToBucketMenu`의 인라인 시트 등)가 `overscroll-behavior: contain`을 갖는다.
- 16개 갭 컴포넌트 전부가 새 조합 훅(또는 최소 `useScrollLock`)을 부른다.

## Steps

### Step 1 — 스크롤 락 조합 훅 신설 + `overscroll-behavior` 추가 (front-only, 순수 추가)

`useScrollLock`을 삭제/재작성하지 않고, `useDismissable`과 조합해 부르는 얇은 래퍼(또는 `useDismissable`의 옵션으로 `lockScroll?: boolean` 추가 — 둘 중 실제 구현 시점에 더 적은 콜사이트 변경을 요구하는 쪽으로 결정, Open question 1) 신설. 락이 걸리는 기존 primitive CSS 클래스(`.scrim`/`.slideover`/`.bps-sheet`/`.qb-modal`/`.rsh-modal`/`.wr-*`/`.gm-peek`)에 `overscroll-behavior: contain` 추가.

**Verification**: 신규 유닛 테스트(`useScrollLock.test.ts` — 지금 0건) — refcount/언마운트-해제가 여전히 정상임을 회귀 고정. `pnpm lint`/`astro check` 클린.

**Rollback**: 신규 파일/CSS 프로퍼티 추가뿐 — 기존 콜사이트 무변경이므로 되돌리기는 파일 삭제.

---

### Step 2 — 16개 갭 컴포넌트 스윕: 조합 훅 채택

`TrashDrawer`, 버킷-삭제 확인, `ActionSheet`, `BucketPickerSheet`, `ImportAnalysis`, `RecentAlbumsModal`/`RecentTracksModal`, 리뷰-삭제 확인, `PocketDesignSettings`, `CommandPalette`, `DraftsInbox`, `SettingsPanel`, 라이터 리서치 드로어, 장르맵 `Peek` — Step 1의 조합 훅(또는 `useScrollLock` 직접 호출)을 추가. 리뷰-삭제 확인은 `role="dialog"` 자체가 없는 추가 갭도 있음(이 RFC 범위 밖, 별도 접근성 항목으로 기록만).

**Verification**: 컴포넌트별 회귀 테스트 1개(락 걸림 확인) + `component-map.md`의 모달/오버레이 레지스트리에 "스크롤 락" 컬럼 추가·전수 갱신. `pnpm test` 전체 그린.

**Rollback**: 컴포넌트별 독립 — 한 곳씩 되돌려도 다른 곳에 영향 없음.

---

### Step 3 — finish `AddToBucketMenu` scroll isolation (keyboard half already shipped)

- **Shipped independently in front #382**: register the sheet in `useDismissable`'s `openStack`,
  autofocus the first control, trap Tab, close the top layer first on Escape, and restore focus.
- Step 1의 조합 훅으로 스크롤 락.
- 배경 비활성화(`inert`)는 이 컴포넌트 하나만 고치지 말고 `useDismissable` 자체에 옵션으로 추가할지 여부를 Open question으로 남김(§Non-goals) — 이 스텝은 `AddToBucketMenu`가 `useDismissable`이 오늘 제공하는 것(ESC/트랩/복원)까지만 정확히 받는 것을 목표로 하고, `useDismissable`이 아직 없는 기능까지 이 스텝에서 새로 발명하지 않는다.

**Verification**: front #382 already supplies the nested-host regression test and real-browser
keyboard evidence for the shipped half. The remaining Step 3 work must add scroll-lock coverage and
re-run the nested picker scenario after adopting the Step 1 composition hook.

**Rollback**: revert only the future scroll-lock adoption. The already-shipped dismissable behavior
is a prerequisite and must not be rolled back with this RFC's remaining work.

---

## Open questions

1. **스크롤 락을 `useDismissable`의 옵션으로 합칠지, 별도 조합 훅으로 둘지** — Step 1 착수 시 결정. 기존 `useDismissable` 콜사이트가 15곳 이상이라 옵션 추가가 더 적은 diff일 수 있으나, 스크롤 락 없이 ESC/트랩만 원하는 기존 케이스(`OverviewDash`의 "add widget" 메뉴처럼 `role="dialog"`가 아닌 앵커드 팝업)와 섞이지 않게 기본값을 신중히 정해야 함.
2. **배경 비활성화(`inert`/`aria-hidden`)를 이 RFC의 Step으로 흡수할지, 별도 접근성 항목으로 분리할지** — 오늘은 `useDismissable` 자체도 안 갖고 있어 `AddToBucketMenu` 하나만 고쳐도 시스템 전체 갭은 안 닫힘. 오너 결정 필요(§Non-goals).
3. **iOS 터치 스크롤 완화(`position:fixed` 기법)를 Step 1/2에 포함할지, 실기기 측정 후 별도 스텝으로 미룰지** — 코드 레벨 결함은 확정이지만 런타임 심각도가 실기기 검증 없이는 확정 안 됨(이 감사는 브라우저 도구 없이 진행됨).

## Decisions log

| Date | Decision | Step |
|------|----------|------|
| 2026-08-06 | Step 3's keyboard half shipped independently with album-card Stage 7 (front #382, `775f683`; deploy `31097251431`; prod smoke 19/19). Nested-host unit coverage and a real 390×844 browser pass verified autofocus, Tab wrap, top-layer Escape, and trigger-focus restoration. The RFC remains draft: Step 1/2 and Step 3's scroll-lock/overscroll portion are still open. | 3 (partial) |
| 2026-08-06 | RFC 신설 — 2026-08-06 아키텍처 감사(항목 10 스크롤 격리, 항목 11 `AddToBucketMenu` a11y)에서 확인된 systemic 격차. `ARCH-entity-interaction-domain-audit` Step 4(ESC/포커스트랩)와 겹치지 않게 범위를 스크롤 락 입양 + `AddToBucketMenu` 단일 컴포넌트 전면 수정으로 한정 | 0 |
