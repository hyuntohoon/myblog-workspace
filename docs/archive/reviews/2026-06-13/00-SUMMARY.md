# 00 — 종합 요약 (Overnight Review 2026-06-13)

## 개요

4개 서비스 레포(`myblog_music`/`myblog_front`/`myblog_worker`/`myblog_shared_db`)의 코드 감사, 프로덕션 Neon DB 데이터 리뷰, 작성자·독자 UX 갭 분석, 음악 리뷰 매체 시장조사, 그리고 그로부터 도출한 기능 후보를 한 패스로 훑었다. 가장 중요한 결론: **불나는 곳은 없다** — 컨벤션 위생은 전반적으로 양호하고 서비스 경계 규칙도 지켜진다. 진짜 손봐야 할 것은 (a) `shared_db` `Section.id` 타입 드리프트와 `myblog_music`의 15버전 뒤처진 pin 같은 **저비용 정합성 수정 몇 개**, (b) 워커의 Spotify/MusicBrainz **핫패스 월클럭 예산 부재**, 그리고 (c) 제품의 정의적 기능인 **AI editorial critique가 0% 빌드**이고 `/genres` 독자 페이지가 **하드코딩 가짜 데이터**를 띄우고 있다는 사실이다.

## Top 10 이슈

| 순위 | 이슈 | 출처 | 심각도 | 수정난이도 | 한줄 권고 |
|---|---|---|---|---|---|
| 1 | `Section.id`가 32-bit `Integer`로 모델링됐으나 prod는 `BIGSERIAL` (64-bit FK가 32-bit PK를 가리킴) | 01 H7 | H | 매우낮음 | `BigInteger`로 1토큰 변경 + 스키마 재생성 + 태그; M16로 parity 테스트도 타입 비교하게 |
| 2 | 워커가 열린 DB 트랜잭션 안에서 Spotify HTTP 호출 (+ MusicBrainz 직렬 ~20콜/틱·30콜 스윕, 월클럭 가드 전무) | 01 H5/H6/M11 | H | 중간 | fetch-all-then-write + 틱당 월클럭 예산 한 패턴으로 H 2개·M 1개 동시 해소 |
| 3 | `/genres` 독자 페이지가 하드코딩 샘플 그래프를 렌더 — 실제 982앨범 장르 시스템은 prod-live인데 미연결 | 03 R1 | H | 중간 | FEAT-genre-system Step 6로 샘플→`/api/genres/tree` 연결 (가짜 기능 노출 중) |
| 4 | AI editorial critique = 제품의 정의적 기능이 코드 0줄 | 03 W1/C | H | 큼(그린필드) | RFC accept + 3개 비용/모델 OQ 결정 → 백엔드 2-step (오너 승인 필요) |
| 5 | `myblog_music`의 `shared_db` pin이 v0.3.0 (backend/worker는 v0.18.1, 15버전 뒤) | 01 M1 | M | 낮음(prod smoke 필요) | v0.18.1로 bump + pyright/units + openapi 재생성 + prod smoke; 오너 플래그 |
| 6 | front 전체에 테스트 러너·스위트가 0개 (검색 race·평점 정규화 회귀 이력 있음) | 01 H2 | H | 낮음 | vitest + `lib/reviews.ts`/`lib/member.ts`/`useMusicSearch` 유닛 + CI 연결 |
| 7 | album-detail 응답 shape를 4곳에 손으로 재선언 → `api.gen.ts` 계약 게이트 무력화 | 01 H3 | H | 낮음 | `Music_AlbumDetail`에서 1개 타입 파생 + 단일 캐시드 fetcher |
| 8 | `tracks(spotify_id)`에 중복 UNIQUE 인덱스 2개 (~584kB + 핫 write 경로 이중 write-amp) | 02 §4 | M | 낮음(prod DDL은 인간승인) | source-of-truth 식별 후 하나 DROP하는 `V{N}__` 마이그레이션 |
| 9 | 공개 아티스트 페이지 부재 — 독자가 아티스트로 탐색 불가 (DB-only API는 이미 unauthed 제공 중) | 03 R2 | M | 중간 | 기존 `/api/music/artists/*` 위에 `/artist/[id]` Astro 페이지 추가 |
| 10 | front에 미사용 무거운 의존성 4개 + dead export + music dead 코드가 prod 번들에 적재 | 01 M6/M7/M8/M4 | M | 낮음 | 순수 빼기 PR — `pnpm remove` + dead export/메서드 삭제 (레포별 분리) |

> 비고: 01의 H4(검색 코어 절반만 마이그레이션), M3(JWT aud/client_id 미검증), shared_db H8(README pin 13마이너 stale)은 Top10 직하 순위. DB 리뷰의 trgm GIN 4.55MB(0 scan)는 **드롭 후보 아님** — 43분 통계 창 + Korean recall용 operator class라 장기 warm 측정 후 판단.

## Top 10 기능 후보

| 순위 | 후보 | 대상 | 근거 | 규모 | 리스크 |
|---|---|---|---|---|---|
| 1 | ⚠️ ~~RSS 피드~~ **이미 출시·정상** — `rss.xml.ts`(@astrojs/rss, prerender) + autodiscovery `layout.astro:18`. `'buckit'` placeholder 제목 + 가시적 구독 링크만 XS 폴리시 | 독자 | 05 #1 정정(2026-06-13) | XS | 없음 |
| 2 | 연말 "Best Albums of [year]" 리스트 페이지 | 독자 | 04 "모든 매체 공통의 단일 아티팩트"; 연 1회·고공유성 | S-M | 낮음(콘텐츠 부족 시 inert) |
| 3 | 공개 아티스트 페이지 `/artist/[id]` | 독자 | 03 R2; DB-only API 이미 출시·unauthed | M | 낮-중(컴포넌트 재사용) |
| 4 | 워커 fetch/write 분리 + 틱당 월클럭 예산 | 신뢰성 | 01 H5/H6/M11 — 감사 #1 교차 테마·#2 임팩트 번들 | M | 중(라이브 sync write 경로·통합 테스트 필요) |
| 5 | front 테스트 하네스 (vitest) | 작성자/dev | 01 H2 — 회귀 이력 있는 순수 로직이 미테스트; 이후 작업 de-risk | M | 낮음 |
| 6 | dead-weight 빼기 sweep (front 의존성 + music dead 코드) | dev | 01 교차 테마 #3; 순수 빼기 | S-M | 낮음 |
| 7 | 아티스트 drill-in 완성 (load-more + count + 타입 필터) | 작성자 | 03 W2/W3/A; 백엔드 paging 이미 존재 | S-M | 낮음 |
| 8 | 이메일 구독 (무료 retention-only) | 독자 | 04 #5; 가장 durable한 retention 채널 | S(프로바이더) | 중(SaaS 의존·오너 $0 성향) |
| 9 | 리뷰 아카이브 정적 검색 (Pagefind/Fuse) | 독자 | 04 #6; 카탈로그 검색과 별개 | S-M | 낮음(콘텐츠 부족 시 inert) |
| 10 | album-detail 타입을 계약에서 파생 + 단일 fetcher | 작성자/dev | 01 H3; CI 계약 게이트 복원 | S-M | 낮음 |

> 추가 후보(틈날 때): #5 독자 cross-link, #7 tag/section 랜딩 페이지, #8 "이 달의 앨범" rail, `apiFetch` 타임아웃(01 L8), 검색 코어 통합(01 H4), 중복 인덱스 DROP(#8 이슈와 동일). 모두 in-flight/frozen 제외 리스트와 충돌하지 않음 확인됨.

## Impact × Effort 매트릭스

### 이슈 매트릭스

```
                낮은 노력                          높은 노력
        ┌──────────────────────────┬──────────────────────────┐
 높은   │ [지금 바로]               │ [계획]                    │
 임팩트 │ #1 Section.id BigInteger  │ #2 워커 월클럭 예산        │
        │ #6 front vitest 도입      │ #3 /genres 실데이터 연결   │
        │ #7 album-detail 타입 파생 │ #4 AI critique (그린필드)  │
        │                          │ #9 공개 아티스트 페이지     │
        ├──────────────────────────┼──────────────────────────┤
 낮은   │ [틈날 때]                 │ [보류]                     │
 임팩트 │ #5 music pin bump         │ (해당 없음 — 저임팩트       │
        │ #8 중복 UNIQUE 인덱스 DROP│  고노력 이슈는 없음)        │
        │ #10 dead-weight 빼기      │                           │
        └──────────────────────────┴──────────────────────────┘
```

### 기능 후보 매트릭스

```
                낮은 노력                          높은 노력
        ┌──────────────────────────┬──────────────────────────┐
 높은   │ [지금 바로]               │ [계획]                    │
 임팩트 │ #6 dead-weight sweep      │ #3 공개 아티스트 페이지     │
        │ #10 album-detail 파생     │ #4 워커 hot-path 리팩터    │
        │ #7 아티스트 drill-in(부분)│ #5 front vitest 하네스     │
        │ (#1 RSS=이미완료, 제외)   │                           │
        ├──────────────────────────┼──────────────────────────┤
 낮은   │ [틈날 때]                 │ [보류]                     │
 임팩트 │ #2 연말 리스트(*)         │ #8 이메일 구독(SaaS 고민)   │
        │ #9 아카이브 검색(*)       │                           │
        └──────────────────────────┴──────────────────────────┘
  (*) #2/#9는 현재 published post=1이라 콘텐츠 쌓이기 전엔 가치 inert → 스캐폴딩으로만 의미
```

## 바로 결정 가능한 것

아침에 5분 안에 결론 낼 수 있는 결정들 (선택지 + 추천):

- **`Section.id` BigInteger 수정 즉시 진행?** → 선택: (a) 지금 고친다 (b) 둔다. **추천 (a)** — 1토큰 변경 + 재생성 + 태그, 가장 싼 정합성 승리. M16(parity 테스트 타입 비교)도 같이.
- **`myblog_music` pin을 v0.18.1로 bump?** → 선택: (a) 정렬 bump (b) 의도적 lag 주석. **추천 (a)** — 단, 로컬 DB 없으니 prod smoke로 검증하고 오너 확인 후 머지.
- **`/genres` 가짜 데이터: 얕은 즉시수정 vs Step 6 풀 작업?** → 선택: (a) 샘플→`/api/genres/tree` 얇은 swap 먼저 (b) Step 6 전체 기다림. **추천 (a)** — 지금 prod에서 독자가 fiction을 보는 중이라 얇은 수정으로 먼저 멈춘다.
- **AI editorial critique RFC를 지금 accept할까, FEAT-genre-system Steps 5-7 뒤로 둘까?** → 선택: (a) 지금 Phase 0 (b) 장르 작업 후. **추천: 오너 판단 필요** — 제품의 정의적 기능이지만 첫 유료 LLM 사용($0 성향)·3개 비용 OQ가 걸려 있어 사람이 결정해야 함.
- **독자-discovery v1 (연말 리스트 + 이메일 구독)을 한 묶음으로 vs 순차?** → 선택: (a) 묶음 (b) 순차. **추천 (b)** — **RSS는 이미 출시돼 있으니 그 위에 이메일 구독을 bridge**(이메일은 SaaS·오너 $0 성향 고민 필요), 연말 리스트/아카이브 검색은 published post가 쌓인 뒤에. 지금 당장은 RSS의 `'buckit'` placeholder 제목만 XS로 정리하면 끝.

## Open Questions 요약

각 항목은 진행을 위해 채택한 가정과 함께 정리. 상세 블록은 `OPEN_QUESTIONS.md` 참조.

**메타**
- **OQ-0 — 참조 우선순위 문서 부재:** 브리프가 가리킨 `2026-05-29-feature-prioritization-v2.md`는 레포·git log 어디에도 없음. (가정: 베이스라인 = `docs/plan.md` + `rfcs/README.md` + `archive/done/`의 합집합; 오너가 로컬/Drive에 v2를 갖고 있으면 Task 5 후보를 대조 필요.)

**myblog_music (Task 1)**
- shared_db pin v0.3.0→v0.18.1 bump이 의도적 lag인지 표류인지. (가정: 비의도적 표류; bump 시 로컬 DB 없어 prod smoke 필요.)
- 깨진 `test_candidates_localstack.py`를 현재 라우트/메시지 shape로 고칠지 vs 빠른 mocked 유닛으로 대체할지. (가정: candidates→SQS 경계에 동작하는 테스트가 현재 0개.)
- `/candidates`의 Cognito user pool에 app client가 여럿인지 — 단일이면 aud/client_id 미검증 리스크 낮음.
- prod SQS 큐 정식명 확정 (memory=standard blogSQS vs README=album-sync FIFO+DLQ) → `infra/README.md`에 맞춰 README/test 교정.
- 이 환경에서 pytest 실행 불가 (Python 3.10·cachetools/fastapi 없음; CI는 3.12). 모든 발견은 정적 읽기 + git/grep 기반, 라이브 테스트 아님.

**myblog_front (Task 1)**
- `POST /api/metrics/batch`가 서버측에서 살아있는지(취소된 likes/comments와 함께 dead인지). (dead면 백엔드에서도 제거 가능.)
- `genres/index.astro`의 하드코딩 샘플 그래프가 의도된 spike인지 — FEAT-genre-system Steps 0-4가 이미 실데이터를 prod에 출시한 점 감안 재확인. (가정: 의도된 spike라 finding으로 보고 안 함; 단 03 R1은 이를 독자-facing 가짜 기능으로 별도 H 보고.)
- music-search-core 추출 반만 됨(writer는 마이그레이션, homepage `searchBarDb.client.ts`는 안 됨)이 의도적 보류인지 망각인지.

**myblog_worker (Task 1)**
- `researchWorkerLambda`(lambda.tf:142)가 동일 핸들러를 공유하지만 research-mode 분기가 없어 research 메시지는 'Unknown format'으로 삭제됨. (가정: MEMORY대로 유료 research Lambda는 dormant·실행기는 로컬 poller이므로 expected; research 실행기가 이 레포 밖에 존재하고 research 트래픽이 이 핸들러로 안 온다는 점 확인 필요.)
- 계정 전역 Lambda 동시성/커넥션 타이트함(limit 10)이 유지된다는 가정이 F1(트랜잭션 내 Spotify)을 H로 올림. Neon 풀이 넉넉하면 F1은 M으로 하향.
- F10(사진 없을 때만 장르 재enrich)은 Step-3 일일 enrichment poller가 이미 사진 있는 아티스트의 장르를 backfill한다고 가정. 그 poller가 이 레포 밖이라 미확인; 아니면 갭이 L보다 큼.

**myblog_shared_db (Task 1)**
- `backfill_genres.py` + launchd plist를 shared_db에 둔 게 의도적 co-location인지, 운영 ETL/LLM 파이프라인을 worker로 옮겨야 하는지. (F5)
- `__init__.py` export 목록이 의도적 curation('primary' 모델만)인지, `Tag` + Spotify 캐시 4모델 누락이 실수인지. (가정: 실수. F4)
- README의 서비스별 버전 표를 유지할지, 각 서비스 requirements.txt 포인터로 대체할지(항상 썩으므로). (F2)
- `canonical_schema.sql`이 라이브 prod 스키마를 충실히 반영한다는 가정(로컬 DB 없어 prod 대조 불가). F1(Section.id) 발견은 canonical 정확성에 의존; canonical 자체가 틀려도 model↔canonical 불일치는 여전히 존재.

**DB 리뷰 (Task 2)**
- 이 prod `neondb`의 Neon plan/tier (Free vs Launch/Scale) — DB 내부에서 판별 불가. (가정: 저장소 비용은 어느 쪽이든 무시 가능; compute 비용 스토리만 다름.)
- `tracks(spotify_id)` 중복 UNIQUE의 source-of-truth(ORM `unique=True` vs `V{N}__` 마이그레이션) — 아닌 쪽을 인간승인 마이그레이션으로 DROP.
- trgm GIN 인덱스(4.55MB, 창 내 0 scan) — keep/drop 결정 위한 다일 warm 측정 스케줄? (operator class가 Korean recall에 load-bearing이라 "0 scan"≠"드롭 안전".)
- `track_artists` artist→tracks 역조회 핫쿼리 존재 여부(10k행·창당 510 seq-scan·standalone `artist_id` 인덱스 없음). FEAT-genre-artist-distribution이 핫하게 만들면 `idx_track_artists_artist_id` 추가.
- `album_research` prompt_version 재실행 정책 — 풀 재실행마다 ~7MB 추가. 보존 버전 수가 유일한 비자명 성장 벡터(단 캡까지 수년).
- ~~auth/멀티테넌트 테이블이 prod `public`에 0-row로 존재 — dead DDL인지~~ **→ RESOLVED 2026-06-13 (검증 재쿼리):** `public` 아님. 전용 **`neon_auth`** 스키마(+ 플랫폼 `auth`/`pgrst`)에 9개 테이블 0-row로 존재 = **Neon Auth**(Neon 관리형 인증, Stack Auth 기반). 프로젝트 DDL 아님·마이그레이션으로 드롭 불가·FEAT-multi-user-accounts와 무관. **조치 불필요**(없애려면 Neon 콘솔에서 Neon Auth 비활성화). 원 초안이 `public`/멀티유저 잔재로 오기재 → 02-db-review §8에서 정정함.

**UX 갭 (Task 3)**
- editorial critique를 지금 accept할지 hold할지(첫 유료 LLM·비용 OQ 미해결).
- `/genres` 실데이터 연결이 FEAT-genre-system Step 6의 home인지, 더 빠른 thin swap을 먼저 할지.
- 공개 아티스트 페이지(R2)가 FEAT-multi-user 전에 가능한지, 묶이는지. (가정: user 모델 불필요·API ready → 멀티유저와 별개로 지금 가능.)
- 아티스트 drill-in 24앨범 캡이 의도적 작성자-focus인지 미완성 follow-up인지. (의도적이면 `album_count`만 노출해도 충분할 수 있음.)
- vestigial metrics/likes/comments(R3) 제거 vs 파킹 유지 — likes/comments 영구 드롭 확인 시 dead 엔드포인트 + 테이블 정리 가능.

**기능 후보 (Task 5)**
- 디스커버리 번들(RSS#1+연말#2+이메일#3) 묶음 vs 순차. (가정: 같은 content-collection 기반 공유; RSS 우선이 자연스러움.)
- 이메일#3 프로바이더 선택 — 외부 SaaS(S 경로) vs self-hosted SES(M·ops 비용). (가정: 프로바이더 경로가 S/추천.)
- 공개 아티스트 페이지#4가 지금 솔로로 가능한지 vs FEAT-multi-user 뒤. (가정: decided-but-unbuilt·frozen 아님.)
- 연말#2·아카이브 검색#6이 published post=1인 현 시점에 만들 가치 있는지 vs 콘텐츠 후 deferral. (cheap하지만 콘텐츠 전엔 inert.)
- 중복 인덱스 DROP#15의 source-of-truth 식별 후 DDL.
- 리팩터-vs-기능 appetite — #12/#13/#14/#16 중 necessity-gate("harm-if-unfixed 명명 가능") 통과하는 것 vs gold-plating. (#14 워커 hot-path=신뢰성 load-bearing; #16=순수 저위험 빼기.)
- #8 "이 달의 앨범" rail·#7 tag/section 랜딩이 in-flight 장르 `/reviews` 필터·frozen 서브장르와 스코프 충돌하는지. (가정: tag/section으로 한정해 장르 레인 회피.)

**시장조사 (Task 4)**
- 브리프 예시 Music Journalism Insider·Penny Fractions 둘 다 폐간(2023) → 검증된 active picks Hearing Things·First Floor로 대체. (가정: 이 대체 수용 가능; 도메스틱 stew!→재즈피플도 동일.)
- Pitchfork 현 리뷰 길이/섹션 구조·RSS/이메일 존속 — pitchfork.com fetch 불가(403), Metacritic 미러로만 추정. (길이 ~600-1500단어는 guess.)
- The Quietus 리뷰별 단어수·Metacritic 일괄 "80"의 의미 — thequietus.com 403. (무점수·Metacritic 기본값 가정.)
- Bandcamp Daily 에디토리얼 측 검색/RSS/이메일(커머스 fan 계정과 별개) 미확인.
- Hearing Things 글별 게시일·연말 리스트 운영 여부 — 홈에 날짜 없음, 2026년 6월은 'Pride Month' 표현에서 추정(guess).
- First Floor 정확한 유료 tier 가격 미포착.
- Bandcamp 소유권 2차 출처 충돌(2024 Beatport 매각설) — 1차 출처(Songtradr 지속) 채택, 거부.
- 음악취향Y 비즈/수익 모델 미확인(paywall/광고/후원 위젯 없음; 자원봉사 critic-collective는 guess).
- 음악취향Y 앨범 별점 스케일(0-5 주장)은 WebSearch 합성, 실 Album-Out 점수 위젯 미확인.
- 음악취향Y RSS/subscribe 마커 미발견.
- 재즈피플 리뷰 포맷(숫자/별점 여부) print-gated라 공개 웹에서 검증 불가; 연말 best-jazz 피처도 미확인.
- weiv(웨이브) 매 fetch HTTP 500 — transient/지오블록 가능, KR vantage 재시도로 2025-2026 게시물 존속 확인 필요.
- IZM 현(과거 대비) 수익 추정 — 문서화된 funding은 삼양화학 후원 + 무상 사무실; 팟캐/유튜브/머치 수익은 guess.
- KR-vantage caveat: 여기 WebSearch는 US-only·일부 SPA/ASP라 curl HTML 파싱에 의존; KR-locale 크롤로 추가 active 매체 노출 가능.
