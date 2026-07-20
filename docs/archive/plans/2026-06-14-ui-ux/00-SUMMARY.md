> **⚠️ HISTORICAL SNAPSHOT — 2026-06-14. SUPERSEDED. Read for IA/positioning rationale only, not as a current spec.**
> This is a frozen overnight UI/UX & IA planning snapshot. Since it was written: the home direction it recommends
> (two-lane WriterStrip + drag-reorder personalization) was **superseded by FEAT-home-redesign-v2** (Variant B
> "Refined Editorial", front #176, 2026-06-16, prod-live), which removed WriterStrip + drag/reorder. The public-bucket
> viewer shipped as **`/collection`** (singular; the `/collections` plural used here was a deferred proposal).
> `FEAT-home-redesign` is **done + archived** (`docs/archive/done/rfcs/FEAT-home-redesign.md`), not "draft".
> See `git log` + the FEAT-* RFCs for current state.

---

# 00 — 종합 요약 (UI/UX & IA 오버나이트, 2026-06-14)

> 아침에 15분 안에 읽고 결정하라고 만든 문서. 상세 근거는 01~05 + `OPEN_QUESTIONS.md`.
> 본문(01~05)은 영어, 이 요약만 한국어 (워크룰 7).

---

## TL;DR (한 문단)

이번 작업의 핵심 발견은 하나다 — **버킷("담기")은 이미 진짜로 구현돼 있다.** 백엔드 API로
지탱되는 중첩 트리 보드(`buckets.ts` + `member/BucketBoard.tsx`)로, 이 앱에서 가장 잘 만들어진
면이다. **그러나 100% 비공개**다 (`/profile` 인증 뒤, 모든 read가 Bearer-gated). 즉 "개인 기록을
잡지처럼 보여준다"는 이 프로젝트의 명제에서 **공개 절반이 통째로 없다.** 그래서 이번 UI/UX·IA
설계의 진짜 질문은 딱 하나로 수렴한다: **비공개 버킷 기록을, 가짜 커뮤니티/규모를 만들지 않고
어떻게 공개 에디토리얼 산출물로 투영할 것인가.** 권장 답은 **"Letterboxd 토대 / IZM 표면"** —
버킷-로그를 토대로 유지하면서 그 위에 얇은 1인 큐레이션 권위면(명반 캐논 + 연말 Picks)을 얹는 것.

---

## ✅ 확정 결정 (2026-06-14, 오너 검토 완료)

아래 §5의 D1~D9를 오너가 직접 확정한 결과. 상세 선택지/근거는 그대로 §5 참조.

| # | 결정 | 확정 |
|---|------|------|
| D1 | 포지셔닝 | **③ 중간** — "Letterboxd 토대 / IZM 표면" |
| D2 | 버킷 공개 | 지금 비공개(나만), **나중에 멀티유저와 묶어** 공개 |
| D3 | 홈 구조 | **B** (두 레인 에디토리얼) |
| D4 | `/collections` | 지금 안 만듦 (D2와 함께 미래) |
| D5 | `/canon` | **만든다** — ★4.0+ 자동 계산; 큐레이션 연말 Picks는 보류 |
| D6 | `/about/how-i-rate` | 안 만듦 |
| D7 | 점수 표시 | 별점만·숫자 금지 → **이미 구현됨**(추가 작업 0) |
| D8 | 이메일 구독 | 안 함 |
| D9 | 글 주소 | `/review/[slug]` (단수) |
| ★NEW | BNM 히어로 | **30일 롤링** — `bestNew` 켜진 최근 30일 글만 노출, 자동 만료 |

**BNM 30일 롤링 (option a):** 글에 `bestNew` 켜면 발행일 기준 ~30일간 히어로에 노출, 지나면 자동으로
빠짐. 정적 사이트라 **매일 1회 자동 재빌드(EventBridge cron)** 가 필요(콘텐츠 안 바뀌어도 날짜로 화면
갱신). 새 필드 0개 — 있는 `bestNew` + 발행일만 비교. *(BNM 없는 달의 히어로 처리 = 후속 OQ.)*

**별점 (D7) — 추가 작업 없음:** 코드 확인 결과 평점은 0.5단위가 아니라 **연속값**(드래그 소수점 2자리),
**숫자는 작가 드래그 중에만** 보이고 발행 글엔 **부분채움 별로만** 나감(`writer/DragRatingInput.tsx`).
"무조건 별점·숫자 금지"가 이미 그대로 구현돼 있음.

**→ 지금 실제로 "짓는 것" 3개:** ① 홈 B형(BNM 30일 롤링 + 매일 재빌드) · ② `/canon`(★4.0+ 자동,
빈 상태 graceful) · ③ `/blog→/review` 주소 마이그레이션(별도 단계).
**미래(멀티유저와 함께):** 버킷 **읽기전용 공개 뷰어** + 큐레이션 연말 Picks.
**안 함:** `/about/how-i-rate`, 이메일 구독, 지금 `/collections`.

---

## 0. 먼저 — 베이스라인 & 메타

- **기준 문서 부재(OQ-0).** 브리프가 가리킨 `2026-05-29-feature-prioritization-v2.md`는 레포·git
  어디에도 없다(2026-06-13 리뷰 번들도 이미 같은 결론). 베이스라인 = `docs/plan.md` + `docs/rfcs/`
  + `docs/archive/done/` + **2026-06-13 리뷰 번들**(`docs/archive/reviews/2026-06-13/`) + 로드맵 메모리.
  이번 작업은 그 번들을 **재탕하지 않고 그 위에** UI/UX·IA + 버킷↔잡지 렌즈를 얹었다.
- **이미 결정된 것(재제안 금지, 워크룰 6).** 1인 에디토리얼 정체성(커뮤니티 기능 폐기)·앨범 단위
  평점만(0.5~5, 트랙/아티스트 평점 폐기)·`FEAT-home-redesign`의 두-레인 홈 방향·`/genres` 출시·
  AI 에디토리얼 비평이 제품의 정의적 기능(0% 빌드)·RSS 출시·연말 리스트 후보·멀티유저 별도 RFC.
- **콘텐츠 현실.** 발행 글 0편(STAB-5 리셋). 모든 설계는 near-zero에서 우아하게 무너져야 함.

---

## 1. 포지셔닝 결정 — 가장 큰 결정 (→ `03-positioning.md`)

"개인 일지가 잡지처럼 느껴지게" 하는 두 레퍼런스 모델 사이에서 고른다:

| 모델 | 토대 | 권위의 출처 | 장점 | 치명적 단점 |
|---|---|---|---|---|
| **A. Letterboxd형** | 로그(버킷) | 군중 집계(이 사이트는 못 씀) | 버킷 토대 유지, near-zero에 강함(빨리 평점, 천천히 글) | 군중 없으면 권위면이 없음 → "공개된 개인 스프레드시트", 잡지감 약함 |
| **B. Pitchfork/IZM형** | 에디토리얼 평론 | 목소리 + 표준 캐논 | 즉각적 권위, 최저 빌드(투영 레이어 불필요) | 버킷(차별점) 폐기 = **금지된 "그냥 Pitchfork 돼라"**, 빈 상태 최악 |
| **★ 중간 (추천)** | 버킷-로그(A) | 목소리 + 큐레이션(B의 *표면*) | 버킷 load-bearing 유지 + 1인이 지속 가능한 권위 + near-zero 우아 | 공개 투영 레이어를 **새로 만들어야** 함, "어중간한 중간"에 빠질 위험 |

**★ 추천 = "Letterboxd 토대 / IZM 표면".**
- 토대는 버킷-로그 그대로. 공개의 원자 단위 = **평점 매긴 버킷 엔트리**(0.5~5★ + 태그 + 선택적
  노트), 산문은 나중에 얹음. (오너의 비평법 "점수는 마지막, 부산물"과도 일치 —
  `docs/editorial/review-critique-method.md`.)
- 권위는 군중이 아니라 **목소리 + 큐레이션**에서: **명반급 상시 캐논(≥4.0★)** + **순위 없는 연말
  Picks** — 둘 다 *공개로 투영된 큐레이션 버킷*일 뿐(IZM/음악취향Y 패턴).
- **홈에서 점수는 기사 뒤로 게이팅**(IZM 룰) → 홈이 스코어보드가 아닌 발행물로 읽힘.

**공개/비공개 경계 = 3옵션 (스펙트럼, 배타 아님):**
- **옵션 1** 완전 비공개(현 상태) — 리뷰 + 리뷰에서 계산한 캐논만 공개. 빌드 비용 **최저**, 누출
  위험 0, 그러나 버킷의 공개 절반 여전히 없음.
- **★ 옵션 2** 선별 버킷을 공개 큐레이션 리스트로 — 버킷 토대를 에디토리얼로 직접 투영. **중간**
  비용(visibility 플래그 + **unauthed 공개 read 엔드포인트**, fail-closed).
- **옵션 3** 엔트리별 공개 평점 기록(rated-but-unwritten) — 로그가 가장 "공개"답고 가장 빨리 채워짐.
  **최고** 비용 + 스코어보드 톤 위험. shared_db 컬럼 추가 가능성.
- **권장 순차 1 → 2 → 3** (지금 1을 floor로, 콘텐츠 쌓이면 2, 오너가 원하면 3).

> ⚠️ **경계의 진짜 어려운 부분(누출 방지).** 어떤 옵션이든: `GET /api/buckets`는 자식까지 inline된
> **전체 트리**를 반환한다. 공개 투영은 *플래그된 그 버킷의 앨범만* 내보내고 자식/부모/형제를
> 절대 자동 공개하면 안 됨 → 공개 엔드포인트는 **평탄화된 per-bucket 뷰**, 공개 DTO는 **좁힌 투영**
> (title/artist/cover/year/rating만; `researchSelected` 등 오너 필드 금지). "fail-closed"의 실제 의미.

---

## 2. 홈 전략 결정 (→ `04-home-strategy.md`)

| 컨셉 | 첫 화면 | 버킷 토대 적합 | near-zero 거동 | 빌드 |
|---|---|---|---|---|
| **A. 개인기록 대시보드** | 오너의 최근 평점 레코드 선반 | **최상**(기록이 첫 화면 척추) — 단 정직한 버전은 미구현 공개-버킷 API 의존 | **최악**(빈 선반 = "아무것도 안 함") | 높음 |
| **★ B. 두-레인 에디토리얼** *(FEAT-home-redesign)* | BNM 히어로(+ 인증된 작가 스트립 상단 고정) | **부분**(버킷은 *비공개* 작가 스트립에만) | **최상**(decision #4 + 장르 막대가 0편에도 렌더\*) | 중간 |
| **C. 린 최신 피드** | 리드 리뷰 + 시간순 | **최악**(리뷰만; 금지된 "그냥 IZM" 근접) | 우아하나 **희박** | 최저 |

\* 장르 막대는 **클라이언트 fetch가 풀린 뒤**에만 보임 — 정적 HTML·크롤러·콜드 첫 페인트엔 빈칸.

**★ 추천 = B 골격으로 출발, A 쪽으로 편향.** B를 지금 짓고(가장 buildable·빈 상태 안전), 콘텐츠가
정당화되면 **A식 공개면 1개**(공개 명반 캐논 / 연말 Picks 레인 = *공개로 투영된 큐레이션 버킷*)를
얹는다. 이게 03의 "Letterboxd 토대 / IZM 표면" + 1→2→3 경계를 **홈에서 표현**한 것. — 단, B 단독은
day-1에 버킷 공개 갭을 **못 닫는다**(버킷이 작가 스트립에만 머묾). 버킷 명제를 buildability보다
중시하면 A를 앞세우고 공개-버킷 비용을 선불.

---

## 3. 페이지/컴포넌트 핵심 결정 포인트 (→ `05-pages-and-components.md`)

- **IA 트리**: `/`(유지·내용 재구성=B), `/reviews`(유지·정식 브라우저), 리뷰 읽기 페이지(`/blog/`→
  새 prefix **마이그레이션**, 정확한 prefix는 미정 — `/review` vs `/reviews/[slug]` 충돌 주의,
  **OQ-1.5**), `/genres`(유지), `/profile`·`/write`·`/drafts`(유지; `/drafts`는 **링크 누락 수정**),
  `/blog/category*`(**폐기**, 이미 결정됨).
- **3개 NEW 제안 페이지** (각각 OQ): **`/collections`** = Task-1 버킷 갭 클로저(공개 버킷 투영, 옵션
  2) · **`/canon`** = ≥4.0★ 컴퓨티드 캐논 + 연말 Picks · **`/about/how-i-rate`** = 1인 평점 스탠스
  정적 페이지(톤 프레이밍).
- **핵심 NEW 컴포넌트**: `EditorialHome` / `WriterStrip` / `ReaderModuleStack`+`HomeEditToggle` /
  `ByTheNumbers` / **`PublicCollections`·`CollectionCard`·`CollectionDetail`**(= 갭 클로저; 기존
  비공개 `BucketBoard`의 *모델*을 재사용하되 *shape*은 재사용 금지 — **좁힌 공개 DTO + unauthed read
  path**, 이건 cross-repo: shared_db → backend → contract → front).
- **중복 통합(리디자인이 손대는 김에)**: 별점 렌더 4개 → 1개(`partial-stars.astro`), 앨범카드 6변형
  → 1 `AlbumCard`, 평점 정규화 3개 → 1개. **정규화 통합은 단순 위생이 아니라 정확성 직결** — 캐논
  ≥4.0★ 임계값이 갈라진 복사본을 쓰면 *틀린 캐논*이 됨.
- **흐름(페이지 경로)**: 작가 = `/` 작가 스트립 → `/write`(⌘K 팔레트 → 크레이트) → 작성 → 발행 →
  읽기 페이지. 독자 = `/` 에디토리얼 홈 → 모듈 → `/reviews`/읽기 페이지 → (제안)`/canon`·
  `/collections` → RSS/뉴스레터.

---

## 4. Impact × Effort 우선순위

```
                 낮은 노력                          높은 노력
        ┌──────────────────────────────┬──────────────────────────────┐
 높은   │ [지금 바로]                   │ [계획 — 별 RFC]               │
 임팩트 │ • 홈 Concept B 골격            │ • /collections 공개 버킷 투영  │
        │ • /about/how-i-rate (정적)     │   (shared_db visibility 컬럼 + │
        │ • 에디토리얼 푸터 IA + /drafts │   unauthed read, cross-repo)   │
        │   링크                         │ • /canon (캐논 v1=컴퓨티드)    │
        │ • 중복 통합(별점/정규화/카드)  │ • 옵션 3 엔트리별 공개 기록     │
        ├──────────────────────────────┼──────────────────────────────┤
 낮은   │ [틈날 때]                     │ [보류 — 선행 기능 필요]        │
 임팩트 │ • BNM 빈 상태 self-hide        │ • 큐레이션 Picks 리스트(에디터-│
        │ • album_count 빌드 스냅샷      │   리스트/버킷-as-list 기능 선행)│
        │ • 이메일 구독(푸터 affordance) │                                │
        └──────────────────────────────┴──────────────────────────────┘
```

핵심: **"지금 바로" 칸만으로도 홈은 잡지처럼 보이게 만들 수 있다**(B 골격 + 캐논 v1은 새 API
불필요, 리뷰 `rating`에서 계산). **버킷의 공개 절반(/collections)** 만이 유일한 고노력·cross-repo
항목이고, 이게 이 프로젝트 명제의 심장이므로 — 별도 RFC로 의도적으로 결정할 가치가 있음.

---

## 5. 아침에 결정할 것 (선택지 + 추천)

> ✅ **전부 확정됨 (2026-06-14)** — 결과는 맨 위 "확정 결정" 섹션 참조. 아래는 각 결정의 선택지·근거(참고용).

- **D1. 포지셔닝 모델?** → A(로그-우선) / B(에디토리얼-only) / **추천: 중간(Letterboxd 토대/IZM 표면)**.
- **D2. 공개/비공개 경계?** → 옵션 1 / 2 / 3 → **추천: 1을 지금 floor로, 2를 다음 수로(순차 1→2→3)**.
- **D3. 홈 구조?** → A / B / C → **추천: B 골격 + 후속으로 A식 공개 캐논 레인**.
- **D4. `/collections`(공개 버킷)를 지금 스코프에?** → **추천: 후속 별 RFC**(cross-repo 비용·톤 위험;
  단 명제의 핵심이라 "언젠가"가 아니라 "다음").
- **D5. `/canon`을 지금?** → **추천: 컴퓨티드 ≥4.0★는 싸니 스캐폴딩 OK, 큐레이션 연말 Picks는 보류**
  (에디터-리스트 기능 선행).
- **D6. `/about/how-i-rate`?** → **추천: 예**(가장 싼 NEW, 공개 평점이 "리더보드"로 안 읽히게 하는
  프레이밍).
- **D7. 점수 노출?** → 홈은 기사 뒤(IZM 룰) 고정, **`/reviews`의 score 패싯은 허용 가능**(거기선
  방어적). (OQ-2.1)
- **D8. 이메일 구독?** → **추천: 보류**(현 무계정·RSS-only 유지) 또는 푸터/읽기페이지 affordance만.
- **D9. 새 read prefix?** → **추천: `/review/[slug]`**(`/reviews/[slug]`는 브라우저와 충돌) — 단
  마이그레이션 RFC에서 확정.

---

## 6. Open Questions 요약 (상세 → `OPEN_QUESTIONS.md`)

- **메타**: OQ-0(기준 문서 부재 — 베이스라인 대체 채택) · OQ-A(Postgres MCP 미연결 — 홈은 콘텐츠
  컬렉션 기반이라 `content.config.ts` 스키마가 올바른 증거; DB 프로빙 불필요).
- **Task 1**: OQ-1.1 `/blog/category` 폐기(이미 결정 쪽) · 1.2 trailing-slash 엣지 정규화 미확인 ·
  1.3 near-zero `/profile` 버킷 렌더 라이브 미검증 · 1.4 클라이언트-only auth 가드 수용 여부 ·
  1.5 새 prefix `/review` vs `/reviews` 미정.
- **Task 2 (설계 결정)**: 점수 위치 · 캐논/연말 Picks 채택 · how-i-rate 페이지 · 이메일 구독 ·
  버킷 공개 원자 단위(rated-but-unwritten).
- **Task 3/4/5**: 각 문서 말미 OQ 섹션에 상세(포지셔닝 모델·경계 옵션·버킷=리스트 객체 여부·홈
  구조·BNM 빈 상태·writer-strip 버킷 카운트 소스·album_count 빌드 스냅샷·읽기페이지 추가 블록).

---

## 7. 산출물 인덱스

- `01-current-frontend.md` — 현 프론트 감사(페이지·컴포넌트 인벤토리·**버킷 현 상태**·IA 다이어그램).
- `02-reference-teardown.md` — 7개 레퍼런스 IA 분해(Letterboxd/RYM/AOTY/Pitchfork/IZM/음악취향Y/
  Bandcamp Daily) + 비교표 + **BORROW / NOT-BORROW**.
- `03-positioning.md` — 버킷↔잡지 화해(텐션·모델 A/B/추천 중간·버킷 개념·공개/비공개 경계 옵션).
- `04-home-strategy.md` — 홈 컨셉 A/B/C + 모듈별 데이터 확인 + 추천(B 골격 + A 후속).
- `05-pages-and-components.md` — 타깃 IA 트리·페이지별 와이어프레임·컴포넌트(재사용 vs 신규)·흐름.
- `PROGRESS.md` / `OPEN_QUESTIONS.md` — 진행 로그 / 미해결 질문 + 채택 가정.

> 검증 메모: 5개 문서는 교차 검토(어드버서리얼 리뷰)를 1회 거쳐 6건 수정 반영(고심각도 0건) —
> 새 read-prefix를 결정된 양 쓴 부분 완화, 공개-버킷 DTO 좁힘 규칙 명시, near-zero 장르 모듈
> 런타임-fetch 한정 명시, AOTY 구독자 수치 비검증 표시. 모든 코드 주장은 `file_path:line`,
> 외부는 URL 근거.
