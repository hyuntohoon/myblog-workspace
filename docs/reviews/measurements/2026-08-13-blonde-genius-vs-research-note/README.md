# Genius 블록 vs. 리서치 노트 — 방식과 결과, Frank Ocean *Blonde* 기준 (2026-08-13)

`docs/editorial/research-note-requirements.md`의 6-갭 스펙과 `2026-07-30-research-prompt-v2-vs-v4/`
측정의 후속. 그 측정은 v2와 v4(둘 다 "웹서치+Genius 블록"을 쓰는 완성된 노트)를 서로 비교했을 뿐,
**Genius 블록 단독**을 별도 항으로 채점한 적은 없었다. 이 문서는 그 빈칸 — Genius가 노트 없이
혼자 서면 얼마나 채우는지 — 를 *Blonde*로 실측한다.

## 방식 (같은 파이프라인 안의 서로 다른 두 산출물)

| | **Genius 블록** | **리서치 노트 (v2 프롬프트)** |
|---|---|---|
| 트리거 | `album_research` 요청 시 워커가 트랙별로 수집 (lyrics-blind) | 오너의 조사 요청 → 큐 → poller가 헤드리스 `claude -p` 실행 |
| 입력 | Genius 공식 API — 크레딧, 관계(샘플/인터폴레이션/커버/리믹스), 매칭 메타데이터뿐 | WebSearch/WebFetch(허용 툴 전부) + 있으면 Genius 블록 + 카탈로그 블록 |
| 범위 | **트랙 단위, 1홉만, 등재(클리어)된 관계만.** 무크레딧 샘플은 구조적으로 못 봄 | 앨범 전체 — 식별/전기/전작/샘플 깊이체인(1~3개, 다홉)/비교좌표/각도, 11개 고정 섹션 |
| 판단 개입 | **없음.** 매칭 신뢰도 점수로 자동 채택, 해석·선별 없음 | **있음** — 무엇을 깊이 팔지, 어떤 비교 후보를 낼지, 어떤 각도를 던질지 모델이 선택 |
| 실패 모드 | 오매칭(예: 신뢰도 0.74로 다른 곡 매칭) — `⚠︎ 곡명 불일치` 플래그로만 방어 | 환각·오염(예: ONYX에서 타 평론 verdict를 끌어들인 v4 회귀) — ★규칙으로만 방어 |
| 비용 | DB 캐시, 재사용 사실상 $0, 즉시 | opus-5 기준 RENAISSANCE 실측 424~712초, 48.7만~148.7만 입력토큰 (`2026-07-30` 문서) |
| 블록 길이 | 렌더러 자체에 상한 있음 — 넘으면 `(Genius 블록 길이 초과로 절단)` | 상한 없음(단, 부풀림 방지용 "본문은 논증에 쓸 것만" 규칙) |

요컨대 Genius는 **무판단 자동 조회**, 노트는 **판단이 개입하는 조사** — 값도 위험도 그 판단에서 나온다.

## 결과 (Blonde로 실측)

Pitchfork *Blonde/Endless* 리뷰(Ryan Dombal, 9.0, Best New Music, 2016-08-25,
`pitchfork.com/reviews/albums/22295-blonde-endless/`)가 실제로 쓴 비가청 논증 재료 22개를,
① 파이프라인이 생성한 Genius 블록(`_genius_block()` 직접 실행, 매칭 17/17)과
② DB에 저장된 기존 v2 노트(`album_research` id `7d0475e7…`, 2026-06-11 생성 — Genius 파이프라인
이전이라 웹서치만으로 쓰임)에 각각 대조했다.

| # | 항목 | Genius | 노트 |
|---|---|---|---|
| 1 | "RIP Trayvon…" (Nikes 가사 직접 인용) | X | X |
| 2 | Chris Rock 인용구 | X | X |
| 3 | D'Angelo 비교 | X | X |
| 4 | Lauryn Hill 비교 | X | X |
| 5 | Dave Chappelle 비교 | X | X |
| 6 | Kendrick Lamar / Beyoncé 비교 | X | X |
| 7 | Ferguson / Orlando 반응 | X | X |
| 8 | *Channel Orange*(2012) 연속성 | X | **O** |
| 9 | "Super Rich Kids" 내용 요약 | X | X |
| 10 | "Novacane" 내용 요약 | X | X |
| 11 | *Boys Don't Cry* 매거진 | X | **O** |
| 12 | "Nikes" 뮤직비디오 연출 | X | X |
| 13 | Lil B 인터뷰 발언 | X | X |
| 14 | *Endless* (동반 비주얼 앨범) | X | **X — 노트에 언급 자체가 없음** |
| 15 | *Endless*/*Blonde* 계약 이행 전략 | X | X |
| 16 | Brian Eno / Rick Rubin 비교 | X | X |
| 17 | "Frank is 28 now" | X | X |
| 18 | "Godspeed" 단편소설=유년 실화 | X | X |
| 19 | "Siegfried" = Elliott Smith 문구 차용 | **O** | **O** |
| 20 | André 3000 verse (Solo Reprise) | 관여 사실만 O, 가사 텍스트 X | 관여 사실만 O, 가사 텍스트 X |
| 21 | *Nostalgia, Ultra.* (23세 발매) | X | X |
| 22 | 동생 Ryan(11세) 인터뷰 인용 | X | 녹음 존재는 O, 인용문 자체는 X |

**Genius 단독 2/22 · 노트 5/22.** 교집합은 19·20 — 노트가 앞서는 3항목(8·11·22)도 "그런 게
있다"는 존재 확인이지, 리뷰처럼 인용 가능한 문장·구체 서술까지는 못 감.

## 발견

1. **Genius가 주는 유일한 실질 값은 크레딧 표에 이름이 걸려 있다는 사실 하나(Elliott Smith/
   Siegfried)뿐**이고, 이마저 노트가 웹서치로 이미 독립적으로 갖고 있던 사실과 겹친다 — 이
   앨범에서는 Genius 블록이 노트에 새로 더한 정보가 사실상 0.
2. **이 리뷰는 RENAISSANCE보다 더 "Kid A형"이다.** `research-note-requirements.md`가 기록한
   반례(리서치 거의 없이 개인적 경험·비유로 쓰인 2000년 Kid A 리뷰)처럼, 이 리뷰의 뼈대는
   D'Angelo·Lauryn Hill·Chappelle·Kendrick·Beyoncé라는 **"흑인 스타덤과 침묵"** 비교 축이다.
   샘플·크레딧이 아니라 갭2(비교 좌표)·갭1(가사 인용)이 결정적인데, 노트도 Genius도 여기서 0에
   가깝다.
3. **`Endless`가 노트에 통째로 없다.** Pitchfork 페이지 자체가 "Blonde / Endless" 합본 리뷰인데,
   저장된 노트는 *Blonde* 17트랙만 조사 대상으로 고정 — 미세 사실 누락이 아니라 **조사 범위가
   리뷰의 절반을 애초에 안 봄**.
4. **노트의 비교 후보 축이 리뷰와 어긋난다.** 노트의 "장르 계보" 섹션(이 노트는 07-26 개정 이전
   버전이라 "계보와 비교 좌표"가 아니라 이 이름으로 존재)은 *Kid A*·Big Star *Third*·Stevie
   Wonder-Prince-Brian Wilson이라는 **소닉/장르 인접** 축을 냈다. 실제 비평가는 D'Angelo·Lauryn
   Hill·Chappelle·Kendrick·Beyoncé라는 **정치·가시성** 축을 썼다 — 겹치는 후보가 하나도 없다.
   비교 후보 생성이 장르 인접만 내고 이런 축은 못 만들 수 있다는 구체 사례.

## 재현

- Genius 블록: `myblog_backend/.venv/bin/python`에서 `scripts/research_poller.py`의
  `_genius_block(conn, 'd8fe438b-9f01-4243-ab52-c608d4a0a74b')` 직접 호출(`dict_row` 커서 필수).
- 기존 노트: `SELECT result_md FROM album_research WHERE id='7d0475e7-858a-452f-ad1f-83cd1c4d772f'`.
- 리뷰: 자동 fetch 차단 → chrome-devtools MCP로 실제 브라우저 로드 후 `article.innerText` 추출.
- 두 원문(Genius 블록 렌더 결과, 저장된 노트 전문)은 `blonde-genius-block.md` /
  `blonde-existing-note.md`로 이 디렉터리에 그대로 첨부. Pitchfork 리뷰 원문은 저작권상 전문을
  담지 않고 위 표의 항목 판정으로만 남긴다(선례: `2026-07-30-research-prompt-v2-vs-v4/README.md`).
