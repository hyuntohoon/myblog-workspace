# 2026-07-23 Current-State Audit — myblog-workspace

독립 재검증 감사(read-only). 이전 리뷰·문서·가정을 사실로 전제하지 않고, 코드/인프라/라이브 사이트를 직접 확인해 재판정했다. 애플리케이션 코드·인프라·데이터는 변경하지 않았다.

- 검증 방식: 5개 병렬 워크스트림(프론트 유지보수성 / 백엔드+뮤직 유지보수성 / 워커+CI+테스트 / 아키텍처·운영 문서 / 라이브 프로덕션 UX) + 주요 P0 주장은 감사자 직접 재확인.
- 판정 기준: Confirmed / Partially / Not confirmed / Unable to verify. 모든 결론은 파일:라인·워크플로·테스트결과·런타임 관측 등 구체 증거를 인용한다. 사실과 추론을 분리 표기한다.
- 대상 커밋: 전 리포 `main` clean (backend #129, front #305, music #58, worker #76, shared_db #68, workspace ee674a8 기준). 미커밋 변경 없음.

---

## 0. 핵심 요약 (먼저 읽을 것)

**가장 중요한 근본 원인:** 제품이 자기 핵심 산출물(평론)을 **단 한 번도 발행한 적이 없다** — 라이브 `/reviews/` `0편`, `/canon/` `0`, `/members/` `0`. 홈 히어로 문구 자체가 "첫 평론이 이 자리에 실립니다"(준비 중)이다. 따라서 canon·members·discovery·best-new-music·AI 편집 엔진 등 모든 하위 표면은 **빈 퍼널을 최적화**하고 있다. 구속 제약은 리팩터링/구조 문제가 아니라 **콘텐츠 생성(오너가 첫 평론을 쓰는 $0 습관 문제)**이다. 이는 2026-06-06 콜드리뷰 결론과 일치하며, 지금도 유효하다.

콘텐츠 수와 무관하게 **오늘 이미 동작하는 익명 브라우징 경험**을 해치는 문제 2가지가 진짜 P0다:
1. 홈 API 지연 — `new-releases` **7.3s**, `on-this-day` **5.5s** (측정치).
2. 릴리스 데이터 노이즈 — 클래식 컴필레이션 ~18% 범람 + 잘못된 아티스트 귀속 + SP/MB/iTunes 교차 중복. 두 문제는 코드상 연결돼 있다(아래 R-2 참조).

안전망 최대 공백: **백엔드 pytest 스위트가 어떤 CI 파이프라인에서도 실행되지 않는다**(fail-closed 인증 회귀 테스트 포함).

`signup → import → create Buckit → publish → discovery` 가설은 **현 시점 기각**한다(§3 결정 요약 참조): 발행 콘텐츠 0, 공개 컬렉션은 오너 자기 것 1개뿐, `/members/` 공백 → discovery는 명목상만 존재. 실사용자 검증 전에는 P2.

---

## 1. 검증 리포트 (Claim / Verdict / Evidence / Impact)

### A. 제품 · UX (라이브)

| # | Claim | Verdict | Evidence | Impact |
|---|---|---|---|---|
| P-1 | 발행 콘텐츠가 사실상 없다 | **Confirmed** | 라이브: `/reviews/` "아직 리뷰가 없습니다", 홈 "0편 평론·0개 장르", `/canon/` "아직 명반이 없습니다", `/members/` "앨범을 평가한 회원이 없습니다" | 핵심 가치(음악 비평) 인스턴스 0 → 전 하위 표면이 빈 상태 |
| P-2 | 카탈로그/릴리스 데이터는 풍부 | **Confirmed** | `/genres/` 13개 상위 장르·**4,352 앨범**(Pop 1,218/Hip-Hop 1,180…), `/releases/` 7월 **141건** | 익명 브라우징 소재는 이미 충분 — 첫 화면이 이를 안 보여줄 뿐 |
| P-3 | 첫 화면에서 제품 가치가 전달되는가 | **Not confirmed** | 히어로 H1 "첫 평론이 이 자리에 실립니다" = 준비중 프레이밍. 4,352앨범 카탈로그·컬렉션 기능은 첫 화면에 없음 | 익명 첫 방문자에게 "coming soon"으로 읽힘 → 이탈 위험 |
| P-4 | 제품 정체성 명확성 | **Not confirmed** | 워드마크 `buckit` / 도메인 `ratemymusic.blog` / 히어로=비평지 / 내비=카탈로그 / `/collection/`=수집도구. `/genres/` 설명은 "이 사이트의 평론을 가르는 장르 지도"인데 평론 0 | 블로그인지 RYM형 카탈로그인지 수집앱인지 판단 불가 |
| P-5 | 익명에게 노출되는 무효 CTA/빈 표면 | **Confirmed(빈표면)** / Not confirmed(로그인 CTA 오해소지) | 내비 `BEST NEW MUSIC`→`/reviews/?bnm=1`(0건 dead-end), `CANON`→빈페이지의 유일 CTA가 다시 빈 `/reviews/`로 순환. 반면 로그인 게이트는 정직하게 라벨됨("로그인하고 평가 남기기") | 익명 기준 주요 내비 3곳이 dead-end. 로그인 CTA 자체는 문제 없음 |
| P-6 | 타 사용자 공개 프로필/버킷 discovery | **Partially** | `/collection/`에 공개 컬렉션 정확히 1개 = "To Review" @user-0468fd3c 46장 (= OWNER_SUB). 핸들은 `@user-<sub>` 원문, 클릭 불가. `/members/`는 공백(평가자 목록인데 평가 0) | 익명 입장에서 **타 사용자** discovery는 기능적으로 부재 |
| P-7 | 릴리스 데이터 중복/노이즈 | **Confirmed** | `/releases/` 141건 중 ~26건(~18%)이 클래식 컴필("A Summer Reverie…", "065 Piano Essentials"…). 귀속 오류(같은 "070 Piano Essentials"가 홈=Bach, `/releases/`=Saint-Saëns). 교차중복(Kenshi Yonezu "夜鷹" MB+iTunes 동일일자). 홈 "새 앨범" 12칸 중 **7칸이 Bach 컴필** | 홈 캐러셀·캘린더가 저가치 컴필·중복으로 도배 → 진짜 신보가 묻힘. 익명에게 가장 눈에 띄는 데이터품질 문제 |
| P-8 | Spotify 재생 표현의 정직성 | **Not confirmed(오해소지 없음)** | 익명에 플레이어 바/now-playing/재생버튼 0개. 앨범 오버레이는 메타+트랙리스트(재생불가)만 | 익명에게 허위 재생 어포던스 없음 = 정직 |
| P-9 | 홈 로드 성능 | **Confirmed(느림)** | 측정: `GET /api/music/feed/new-releases?days=30&limit=12` **7,332ms**, `/api/music/albums/on-this-day` **5,542ms**, `/api/genres/tree` 1,548ms, `/api/todays-pick` 385ms→`null`. 셸 DOMContentLoaded 705ms지만 콘텐츠/커버는 ~8s까지 안 뜸(느린 feed 대기) | 서브-1s 셸에도 체감 로드 ~8s. 두 엔드포인트가 명확한 병목 |

### B. 코드 · 유지보수성

| # | Claim | Verdict | Evidence | Impact |
|---|---|---|---|---|
| C-1 | 과대 책임 프론트 컴포넌트(BucketBoard) | **Confirmed** | `BucketBoard.tsx` **2895 LOC**, 33 useState/18 useEffect/6 useRef, ~20 모듈 import. 한 컴포넌트가 서버상태 fetch/mutation, 스토어 구독, 라이프사이클 도메인규칙(crMeta), DnD, 리서치 정책, Spotify 라이브러리 동기화, 뷰/모달을 모두 소유. 다음 큰 파일: NowPlaying 1149, PocketTray 1003, LyricsViewer 936, WriterApp 912 | 최고 결합 지점. 이 표면 변경은 보드 전체 회귀 위험 |
| C-2 | Buckit 도메인 규칙이 컴포넌트 전반에 중복 | **Partially(주장보다 약함)** | 핵심 라이프사이클 규칙은 **단일 함수** `crMeta()`(`BucketBoard.tsx:439-451`)에 중앙화(중복 아님). 단, `@lib/buckets`가 아닌 메가 컴포넌트 **내부**에 갇혀 재사용 불가. 필드해석(isDone/researchStatus 등)은 7개 파일에 분산 | 헤드라인은 "중복"이 아니라 "재사용 불가한 위치 + 중간 결합". 회귀범위 중간 |
| C-3 | 상태 소유권 불명확(도메인/서버/로컬/DnD/API) | **Partially** | 서버상태는 잘 소유됨 — `bucketStore.ts`(199 LOC, useSyncExternalStore 싱글턴, sub-scoped, 과거 3중 복사본 드리프트를 대체). 단 DnD는 **2개 React 루트**(보드/트레이 아일랜드)가 공유 컨텍스트 없이 8개 window CustomEvent(`events.ts`) + 모듈-레벨 mutable `dnd` 변수로 통신 | 서버상태 소유권은 오히려 강점. DnD가 진짜 불명확 영역(이벤트 순서·크로스번들 mutable 의존 → 취약·테스트 난이도↑) |
| C-4 | 한 규칙 변경이 다수 위치 편집 유발 | **Partially** | API base URL이 30곳에서 재유도, `*.api.ts` 클라이언트 7개가 각자 BASE/헤더 정의, 라이프사이클 규칙이 컴포넌트 내부(C-2) | 횡단 정책 변경(타임아웃/인증헤더/base URL)은 단일 choke point 없음. 실재하나 bucket **트리**는 bucketStore로 중앙화되어 있어 한정적 |
| C-5 | 핵심 프론트 플로우 회귀 보호 부재 | **Confirmed(최강)** | `*.test.*`/`*.spec.*` **0개**, vitest/playwright/jest 설정·러너·`test` 스크립트 **전무**. CI `check`는 api.gen.ts diff + astro check + lint만. bucket 생성/이동/DnD, publish, 플레이어, 가사 뷰어 전부 자동 커버 0 | 최고복잡·최고결합 표면에 회귀망 없음. 타입/린트는 렌더·이벤트·로직 회귀를 못 잡음(BUG-11→12 전례) |
| C-6 | API 클라이언트/인증/타임아웃/취소/에러 중복 | **Confirmed** | `apiFetch`(`api.ts`, 88 LOC)는 단일 클라 **아님** — raw `fetch(` **42곳**/~25파일 + 전용 `*.api.ts` **7개**가 직접 fetch. 일부는 `Bearer`를 손으로 세팅해 apiFetch의 401→refresh 재시도 **우회**(`spotifyPlayback.ts:306,358`). `apiFetch`는 **타임아웃/AbortController 없음**(`safeFetch`만 8s). 취소는 `api.ts`에만, 검색 as-you-type엔 없음. 에러는 콜사이트별 임기응변 | 인증갱신·타임아웃·취소 시맨틱이 콜사이트마다 상이. 한 곳 수정이 8+곳 복제 필요 = 중복 클라이언트 세금 |
| C-7 | 백엔드 서비스/스키마 과대 | **Confirmed(backend) / Not confirmed(music)** | backend `api/schemas.py` **1282 LOC·111 클래스**(전 도메인 DTO 단일 파일), `bucket_service.py` **1144 LOC**(예외 10개 + 스코어링+트리연산+외부동기화 혼재 god-service), `library_service.py` 1098. music 최대는 `search_service.py` **480**(잘 분할) | backend 스키마+bucket/library 서비스가 최고 churn·리뷰표면. music은 문제 아님 — "oversized backend"를 music까지 일반화하면 과장 |
| C-8 | 크로스리포 auth 트윈 드리프트 | **Partially(Confirmed 드리프트)** | `app/core/auth.py` backend **165** vs music **97** LOC. 공통 코어(fail-closed·JWKS 503·`timeout=10`)는 미러링되나, backend만 `verify_token`/`resolve_owner`/`require_owner` 보유, music엔 없음. 주석태그도 다름(카피페이스트 트윈 별도 유지) | 미래 보안 수정이 music 트윈을 조용히 누락할 위험이 가설이 아니라 실재(CLAUDE.md 하드룰이 겨냥한 클래스) |
| C-9 | 아웃바운드 HTTP 타임아웃 하드룰 위반 | **Confirmed** | 감사자 직접 확인: `publish_service.py:114,125,144,158` — GitHub Contents API `requests.get/put/delete`에 `timeout=` **없음**(publish/unpublish 경로). 그 외 backend/music 아웃바운드는 전부 timeout 명시 | 발행 경로가 GitHub 지연 시 무한 hang 가능 = 하드룰이 겨냥한 정확한 클래스. 소규모 수정으로 제거 가능 |
| C-10 | 의존성 재현성 | **Partially** | lock 파일 없음(requirements.txt만). backend `fastapi>=0.110,<1.0`·`requests>=2.31`·`SQLAlchemy==2.*` 등 미핀. shared_db 핀 상이 — backend `@50d33c3`(=v0.27.0-17, **비태그 SHA**), music/worker `@v0.26.0`, 패키지 HEAD 0.37.0 | 미핀 + 무버블 SHA = CI↔prod 드리프트 클래스. 단 shared_db 핀 랙은 additive 컨벤션(ARCH-6)으로 대체로 수용된 설계 |
| C-11 | 백엔드 read 경로 N+1 | **Not confirmed(backend) / 리드 발견(music)** | backend `library_service`는 batch-map anti-N+1 정석 사용(`col.in_(ids)`→dict). 반면 music `feed_service.py`는 DB-only지만 300행 over-fetch 후 `al.artists`를 앨범마다 접근(`:78,83`) → lazy-load N+1 유력. **클래식 컴필이 이를 증폭**(각 Bach 컴필이 ~50 아티스트 collapse → 앨범당 50 lazy 로드) | P-9 지연의 코드상 유력 원인. 프로파일링 필요하나 리드 명확 |

### C. 아키텍처 · 운영 · 딜리버리

| # | Claim | Verdict | Evidence | Impact |
|---|---|---|---|---|
| O-1 | 백엔드 pytest가 CI에서 실행되는가 | **Confirmed 부재** | backend `deploy.yml`은 `check` 잡에서 **pyright만** 실행. `pytest`는 PR·push·deploy 어디에도 없음. 스위트는 46파일·631 테스트(로컬 554 pass)로 실존, `test_auth_failclosed.py`(fail-closed 인증 불변식·하드룰 회귀) 포함 | 최고 레버리지 안전공백. 인증 회귀가 CI에 안 걸림 |
| O-2 | 리포별 PR 머지 게이트 | **Confirmed** | music: pyright+`pytest -m "not integration"`+openapi(PR 차단○). backend: pyright+openapi만(pytest×). worker: `pull_request` 트리거 없음 → **PR CI 0**. front: `main.yml`(astro check/lint/build/api.gen diff)이 **push-only** → PR 차단 게이트 0, `code-review.yml`(Claude 자문, 빌드 실패 안 시킴)만. workspace: CI 없음. shared_db: 스키마 parity(PR○) | backend/worker/front/workspace가 유의미한 PR 차단 게이트 결여 |
| O-3 | 배포 스모크/롤백/안전장치 | **Partially** | 있음: concurrency 직렬화, `needs:[check]` 사전게이트, Errors/Throttles/DLQ 알람(SNS 이메일, detect-only). 없음: **배포후 스모크 게이트·헬스 게이트·자동 롤백 전무**. 복구=수동 재배포. 문서화된 롤백 런북 없음(`rollback/staging/canary` grep 0). staging 환경 부재(`ENV=prod` 하드코드, 단일 `$default` 스테이지) | 불량 배포가 알람만 울리고 자동 차단·되돌림 없음 |
| O-4 | 비동기 EventBridge 크론 실패 경계 | **Confirmed** | DLQ(`album-sync-dlq`)는 **SQS 경로만** 백킹. 비동기 크론(album_ingest, lastfm, member_poll, release 폴러, alias 등)은 함수에 `dead_letter_config` 없음 → 2회 재시도 후 조용히 폐기. `FailedInvocations` 알람은 ~10 크론 중 2개만 커버 | 크론 실패 페이로드 복구 불가·대부분 미알람. 상태없는 폴러엔 수용가능하나 replay 경로 없음 |
| O-5 | 워커 잡 경계 공유 | **Confirmed(뉘앙스)** | 14+ 잡타입이 단일 `blogWorkerLambda`(120s/512MB/reserved concurrency 없음) 공유. 예약 동시성 없어 SQS 버스트가 전 크론과 계정 풀 경합(Throttles≥5 알람만 신호) | 타임아웃/동시성/DLQ 경계가 대체로 공유. 잡별 분리 이득이 이주·운영비를 넘는지는 미검증 → 근거없는 전면분리 비권장 |
| O-6 | 앨범동기화가 외부호출 중 DB 트랜잭션 유지 | **Partially** | `handler.py:179-182` `session.begin():` 안에서 `sync_albums_batch`→ 첫 동작이 외부호출 `spotify.get_albums`(`sync_service.py:59`). 단 SQS batch=10·~20 ID/msg → 통상 단일 청크(~20s max). 장기 루프 잡들은 fetch→materialize→close 준수 | idle-in-txn 형상이나 현재 한정적. 느린 Spotify 응답 시 트랜잭션이 client timeout 근처까지 열림 |
| O-7 | shared 52-테이블 DB 결합 vs 서비스 경계 | **Confirmed(경계는 명목적 데이터플레인)** | 단일 Neon Postgres **52 테이블**을 backend/music/worker 3서비스 공유. 쓰기소유권은 깨끗(music은 editorial 테이블 미기입, backend는 catalog 테이블 미기입, worker가 catalog/spotify_* 소유). 단 마이그레이션/스키마 변경은 git-pin shared_db로 전 서비스에 파급, 모든 서비스가 모든 테이블 read 가능 | 격리는 외부API/Lambda 레벨(장애도메인)이지 데이터스토어 레벨 아님. Neon 사고·불량 마이그레이션은 공유 장애도메인 |
| O-8 | `docs/architecture.md` 정확성 | **Not confirmed(심각 stale)** | 서비스→Lambda 매핑·SQS 토폴로지·인증 흐름은 정확. 그러나 EventBridge를 **1개**로 기술(실제 **13개**), 워커가 shared_db "아무것도 import 안 함"이라 기술(실제 `genre_mapping.attachable_slugs` import), shared_db 핀 3개 전부 오기. `infra/README.md`도 "10 routes"(실제 **48**) | 문서-현실 최대 괴리 구간. 비동기 토폴로지 오도 |
| O-9 | 상태 문서 충돌 | **Confirmed** | (a) `RFC-ui-surface-unification`: README 인덱스는 in-progress인데 파일은 `archive/done/rfcs/`에 Status: done, plan.md엔 부재. (b) `FEAT-release-calendar`: Steps 1–7 shipped인데 3소스 모두 Status `accepted` 유지(라이프사이클표상 `done`이어야). (c) `FEAT-bucket-identity`: RFC/인덱스 in-progress인데 plan.md Backlog에 위치 | 인덱스·plan·RFC Status 3자 불일치 3건. 이력 신뢰도 저하 |

### 검증 불가(정직 기록)

- Cognito 런타임 ID(Pool/authorizer/HTTP API ID) — `.tf` 소스에 없고 tfstate/라이브 AWS 필요. **Unable to verify**.
- `/radar/`·`/members/?me` 인증 게이트 표면의 채워진 상태 — 로그인 안 함. **Unable to verify**(익명 프롬프트 상태만 관측).
- music `feed_service` 지연의 정확한 원인 — N+1 리드는 강하나 실측 쿼리 프로파일링 미실시. **Partially**(측정치는 확정, 코드원인은 리드).

### 이전 리뷰 대비 정정(부정확·과장·검증불가였던 주장)

- "Buckit 규칙이 컴포넌트 전반 중복" → **과장**. 핵심 규칙은 `crMeta` 단일 함수로 중앙화. 진짜 문제는 위치(메가 컴포넌트 내부)지 중복이 아니다.
- "프론트 문제는 OOP/클래스 도입으로 해결" → **근거 없음**. 증거는 모듈 추출 + 공유 클라이언트를 가리키며, `bucketStore` 싱글턴이 함수형-스토어 패턴이 이미 잘 작동함을 증명.
- 이전 arch 감사의 "워커는 shared_db import 0" → **오류**(genre_mapping import 실재).
- "oversized 백엔드 서비스/스키마"를 music까지 확장 → **부분 오류**. music은 잘 분할됨. 문제는 backend 한정.
- "multi-user가 유의미한 discovery 경험을 만든다" → **현 시점 미확인**(오너 콘텐츠만 존재, discovery 명목상). 실사용자+콘텐츠 전에는 검증 불가.
- shared_db 핀 상이를 "스키마 skew 위험"으로 → **부분적**. additive 컨벤션(ARCH-6)으로 대체로 수용된 설계. 단 비태그 SHA 핀은 재현성 냄새.
- (2026-06-05 arch 감사가 지적한 인증/SQS visibility/schema.sql 구멍은 STAB-2/3/4로 **이미 수정 완료** — 현재 재발 없음 확인.)

---

## 2. 근본 원인 정리

| 계층 | 근본 원인 | 이것이 설명하는 증상 |
|---|---|---|
| **제품(1차)** | 핵심 산출물(평론)이 0건 발행 = 콘텐츠 생성이 구속 제약 | P-1~5, canon/members/best-new-music 빈 상태, AI 편집엔진의 미성숙, discovery 부재 |
| **UX(오늘 실害)** | 홈 hot-path 읽기 지연 + 릴리스 데이터 노이즈(코드상 연결: 컴필→아티스트 N+1 증폭) | P-7, P-9, C-11 |
| **딜리버리 안전망** | 테스트가 실존하나 게이트에 미배선(backend pytest 미실행, front/worker PR게이트 0, 스모크/롤백 0) | O-1~4, C-5 |
| **구조(2차, 콘텐츠 있을 때 실害)** | 경계 약화 — 규칙이 메가 컴포넌트/god-service에 갇힘, 클라이언트 파편화, auth 트윈 드리프트 | C-1,2,4,6,7,8 |
| **문서 정확성** | architecture.md·infra/README 비동기 토폴로지 stale + RFC 상태 3자 불일치 | O-8, O-9 |

**핵심 판단:** 구조 문제(C-1·C-7 등)는 실재하나 **2차**다. 실사용자·콘텐츠가 생기는 날 딜리버리를 늦추는 근거가 확인되면 그때 값어치가 생긴다. 대규모·고회귀위험 리팩터를 회귀망(C-5) 없이·사용자 없이 먼저 하는 것은 정당화되지 않는다.

---

## 3. 결정 요약 (Recommended / Deferred / Rejected / User decision)

| 문제 | 대안들 | 분류 | 근거 |
|---|---|---|---|
| C-9 publish 타임아웃 위반 | 4개 `requests.*`에 `timeout=` 추가(소규모, 리포 내) | **Recommended (P0)** | 하드룰 위반·발행경로 hang·수정비 최소·회귀위험 미미 |
| O-1 backend pytest 미실행 | (a) deploy.yml `check`에 pytest 추가 (b) 별도 PR 워크플로 | **Recommended (P0)** | 실존 스위트 배선만 하면 됨. fail-closed 인증 회귀 커버. 사용자 수 무관하게 안전 이득 |
| P-9 홈 지연 7.3s/5.5s | (a) feed/on-this-day 쿼리 eager-load+인덱스 (b) 결과 캐시 (c) 프론트 스켈레톤/타임아웃 폴백 | **Recommended (P0 조사)** | 측정 확정. 코드리드(C-11) 존재. 먼저 프로파일→최소수정. (a)가 유력, (b)는 필요시 |
| P-7/C-11 릴리스 노이즈 | (a) ingest 시 컴필 필터/소스신뢰가중 (b) read 시 필터 (c) dedup 강화 | **Recommended (P1)** — FEAT-release-calendar OQ4에 편입 | 신규 RFC 불필요(기존 릴리스 RFC가 이미 이 질문 소유, OQ4 ~07-27 예정). 구체 증거를 OQ4에 주입 |
| O-2/O-3/O-4 PR게이트·스모크·롤백·크론 DLQ | 크로스리포 딜리버리 안전 게이트 통합 | **Recommended (RFC)** → `OPS-delivery-safety-gates` | 다중리포·정책·단계 이주 → RFC 적격 |
| C-1/C-5/C-6 프론트 결합·무테스트·클라이언트 파편화 | (1) 테스트망 먼저 (2) 공유 fetch 클라 (3) 라이프사이클 규칙 추출 → **그 다음** BucketBoard 분해(필요성 게이트) | **Recommended(테스트망+seam) / Deferred(대분해, P2)** → `REFACTOR-frontend-member-surface` | 다중PR·회귀위험·구조규칙 → RFC 적격. 단 대분해는 실사용자 증거 전 불필요 |
| O-8/O-9 문서 stale·상태불일치 | architecture.md/infra README 갱신 + RFC 상태 정합 | **Recommended (P1 정리)** | 루틴 정리 — RFC 불필요. 단 RFC Status 승격은 오너 승인 필요(rule #5) |
| C-8 auth 트윈 드리프트 | 트윈 정합(공유 모듈화 vs 동시수정 규율) | **Deferred (P1)** | 현 재발 없음. 다음 인증 수정 시 동시 처리 규율로 충분할 수 있음. 공유 모듈화는 필요성 게이트 |
| C-10 재현성(lock/핀) | lockfile 도입 + fastapi/boto3/SQLAlchemy 핀 + 비태그 SHA→태그 | **Deferred (P2)** | 실害 미발생. additive 컨벤션 하 수용. 배포 500 사건 재발 시 승격 |
| O-5 워커 잡 분리 | 잡별 Lambda/타임아웃/동시성 분리 | **Rejected(전면분리)** | 이득이 이주·운영비를 넘는다는 증거 없음. 예약동시성/선택적 DLQ만 필요시 |
| **`signup→import→Buckit→publish→discovery` 우선순위** | 이 플로우를 핵심으로 지금 투자 | **Rejected(현 시점) / User decision(전략)** | 발행 0·타 사용자 0·discovery 명목상 → 조기 최적화. 구속 제약은 오너의 첫 평론 발행. discovery는 실사용자 증거 나올 때 P2. **단 "지금 무엇을 핵심으로 볼지"는 오너 전략 결정** |
| 제품 정체성 P-4 / 첫화면 P-2 | 히어로/내비를 카탈로그·컬렉션 중심으로 재구성 vs 비평지 유지 | **User decision** | 방향 선택은 오너 몫. 증거만 제시(익명이 4,352앨범 카탈로그를 첫화면에서 못 봄) |

---

## 3.1 오너 결정 (2026-07-23, §3 후속)

§3의 "User decision required" 항목에 대한 오너 결정:

1. **전략 우선순위 = 안전망·품질 먼저.** OPS·REFACTOR RFC가 활성 우선. discovery 플로우는 P2 유지(실사용자 증거 후 재평가).
2. **제품 정체성 = 비평지 프레이밍 유지.** 첫화면 카탈로그 재구성 안 함 → P-2/P-4는 액션 없이 종결.
3. **RFC 2건 둘 다 accepted.** OPS·REFACTOR 모두 Step 1 착수 가능(REFACTOR Step 4 대분해는 필요성 게이트 유지).
4. **문서 불일치 전체 정리 승인.** architecture.md·infra/README·RFC 상태 3건 이 세션에서 반영 완료. FEAT-release-calendar accepted→done 승격+archive, 노이즈 작업은 `plan.md` DATA-release-noise로 분리.

## 4. 산출물 · 후속

- 이 리포트: `docs/reviews/2026-07-23-current-state-audit.md`
- 신규 RFC(draft): `docs/rfcs/OPS-delivery-safety-gates.md`, `docs/rfcs/REFACTOR-frontend-member-surface.md`
- `docs/plan.md`: 감사 파생 P0/P1/P2 통합 계획 추가, 릴리스 노이즈 증거를 FEAT-release-calendar OQ4에 편입
- **오너 결정 필요(§3):** 전략 우선순위(콘텐츠-우선 vs discovery-플로우), 제품 정체성/첫화면 방향, RFC 2건 accept 여부, FEAT-release-calendar `accepted→done` 승격, 상태 불일치 3건 정리 승인.

_이 감사는 분석·문서화만 수행했다. 어떤 애플리케이션 코드·인프라·데이터도 변경하지 않았으며, 커밋/푸시/PR도 하지 않았다. 오너가 계획을 명시 승인하기 전까지 구현에 착수하지 않는다._
