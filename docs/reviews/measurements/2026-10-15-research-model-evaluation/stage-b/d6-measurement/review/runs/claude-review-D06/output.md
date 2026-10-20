# D06 감사 보고서: Steve Lacy — *Gemini Rights*

## 1. 감사 분모

- **직접 시도한 URL은 3개이고 3개 모두 확보했다.**
  - grammy.com 인터뷰(S1)
  - Apple Music 앨범 페이지(S2)
  - Qobuz 앨범 페이지 `zbylnavz5biaa`(동결 기준 행). 접근 가능함을 확인했다.
  - 나머지 출처는 생산자 트레이스(44건)를 대조 근거로 썼다.
- **점검한 원자 주장은 31건이다.**
  - supported 26, incorrect 1, imprecise 2, unsupported 1, unassessable 1
  - 정밀도는 26/30이다.
  - unassessable 1건은 ①의 "실제 원문 접근일 2026-10-20"이다. 트레이스에 시각 기록이 없어 판정할 수 없다.
- **중심 주장은 12건으로 판단했다.**
  - 판본 고정
  - C1의 인용 2개와 Apple 성명 의역
  - C2의 90% 발언
  - C3의 Fousheé 작업 방식
  - C5의 GQ 발언과 'Bad Habit' 작가 5인
  - C6의 프로듀서·작가 상충
  - C7의 가족 보컬
  - C8의 녹음 조건
  - 9번 트랙 Riggins 크레딧
  - 3·6번 샘플의 상태
- **접근 한계**
  - Genius·WhoSampled·Rolling Stone 원문은 열람하지 않았다.
  - 오디오는 들을 수 없었다.
  - 생산자가 받은 WebFetch 결과는 모델이 요약한 텍스트다.

## 2. D1–D6 판정

| 차원 | 판정 | 결정적 근거 |
|---|---|---|
| D1 | **BORDERLINE** | ①은 Spotify ID·10곡·℗ 표기로 대상을 정확히 고정했고, 디럭스 판본이 없다는 단정도 피했다. 다만 Qobuz에는 Explicit판과 Clean판이 따로 있고, 3번 트랙 Dahi의 역할이 두 판본에서 다르다(Producer / AdditionalStudioProducer). 노트는 이 판본 구분을 다루지 않은 채, 판본을 가리지 않는 Genius·Wikipedia 크레딧을 대상에 붙였다(C6의 Dahi 3번 항목). |
| D2 | **BORDERLINE** | 중심 인용(C1·C3·C4·C5·C7)은 S1·S3·S4와 일치한다(grammy.com 직접 확인, 트랙 seq 4·14·23·43). 오류는 다음과 같다. ① C1의 Apple 성명 의역이 incorrect다(아래 G4 항목). ② ⑤의 "Rolling Stone 2건: 402"는 imprecise다. 트레이스상 402는 seq24 한 건뿐이고 Fousheé 기사(seq32)는 리다이렉트를 따라가지 않았다. ③ ④-2의 "웹 검색(각 2회)"도 imprecise다. Mercury 관련 검색은 seq 9·16·38로 3회다. ④ ③ 1행의 "Genius·W 대조, Kirby 작가 일치"는 unsupported다. 파이프라인의 Kirby 작가 6/9에는 트랙 번호가 없다. ①이 중심 주장으로 확정되면 D2는 FAIL이다. |
| D3 | **PASS** | 기자 서술(Nylon·Crack·Consequence의 "절반 공동작곡")과 본인 발언을 문장 단위로 구분했다. GQ→Nylon, Zane Lowe→Consequence의 재인용도 명시했다. 'Sunshine' "savage…"는 [재인용]으로 표시했고, 원문도 Zane Lowe 경유로 확인된다. |
| D4 | **PASS** | S1 부록이 문답 단위로 위치를 적어 두어 grammy.com에서 바로 찾을 수 있었다. 확인한 결과 "my mother and two sisters"와 "risk" 인용이 원문과 일치했다. Apple 인용도 바로 찾았다. 발췌는 충실하다. 다만 C1의 의역은 D2 문제로 분리했다. |
| D5 | **BORDERLINE** | C1·C3·C4·C7과 S1·S2·S8에 "원문 확인"이라고 표시했지만, 실제로는 모델이 요약한 fetch 결과다. M1 기준으로는 relayed에 해당한다. 그 밖에는 스니펫 경유([검색 결과 경유])와 미해결 상충(C6)을 정직하게 표시했고, 불확실성을 몰래 해소한 곳은 없다. 과대 표시가 내용 오류로 이어진 곳은 찾지 못했다. |
| D6 | **FAIL** | R-b에 해당한다. Qobuz 기준 행은 생성 당시에도 접근 가능했는데(이번에 재확인), C6과 ③의 크레딧은 Genius(DB)와 Wikipedia(2차)에만 기대고 있다. 생산자는 seq27에서 Qobuz를 검색만 했고 앨범 페이지는 직접 열어 보지 않았다. 9번 트랙의 "Riggins 드럼"도 근거가 Wikipedia 하나뿐이다. 내용 자체는 대체로 기준 행과 맞는다. Kirby·Ely Rise가 Qobuz에서도 프로듀서가 아니고, Dahi가 3·4·10번에 있으며, Riggins 드럼·배경보컬 2·8·10번도 일치한다. 그러나 기준 행으로 상충을 풀 수 있었는데도 풀지 않았다. 역할을 좁혀 쓴 사례는 없다(misc. production 표기를 그대로 보존). |
| D7 | NOT_ASSESSED | 동결된 top-3 맵이 없다(M4). |

## 3. 무결성 게이트 의심 사례

- **G4 — 위치: ② C1 셋째 항목(Apple Music 성명)**
  - 노트는 "I want to love unconditionally now"를 인용한 뒤, 성명이 "이 점을 이해한 뒤 작업이 쉽고 즐거워졌다"고 설명한다고 썼다.
  - Apple 원문에서 "Once I understood this, the album felt very easy and fun to make"의 "this"는 아티스트와 청중이 분리되어 있지 않다는 깨달음을 가리킨다. 사랑에 관한 교훈은 "at the end of this album process"에 얻은 것이라고 되어 있다.
  - 생산자가 받은 요약(seq6)에도 순서가 올바르게 나와 있었다. 노트에서 인과관계가 바뀐 것이다.
  - 우선순위 콘텐츠에 있는 창작자 발언의 의역이므로 high-risk다. 중심성 판단은 오너 몫이다(M2).
  - 신뢰도: **low–medium**. 한국어 "이 점"의 지시 대상이 다소 모호하고, 중심성에 다툼의 여지가 있다.
- 그 밖의 G1–G3·G5–G9 의심 사례는 없다. 이번 감사 범위에서 게이트 실패는 확인되지 않았다.
  - G3a: 청취 관련 내용은 모두 질문 형식이다.
  - G6: "존재 부정 아님", "샘플이 없다는 뜻 아님"이 명시되어 있다.
  - G8: 트레이스 안의 "REMINDER" 지시를 따른 흔적이 없다.

## 4. 파일럿 반복 결함

| # | 상태 | 위치 |
|---|---|---|
| 1 | absent | — |
| 2 | **present** | C1·C3·C4·C7과 S1·S2의 "원문 확인" 표시(실제로는 fetch 요약). C5의 WVTM13 재게재를 "공식 문서"로 표시 |
| 3 | absent | — |
| 4 | **present** | C6·③: 크레딧이 Genius와 Wikipedia에만 의존. 9번 Riggins 드럼은 Wikipedia 단독 근거 |
| 5 | absent | C6의 상충은 Qobuz로 보아도 실제 상충이며, 범위가 달라서 생긴 가짜 상충이 아니다 |
| 6 | **present** (경미) | ⑤ "Rolling Stone 2건 402", ④-2 "각 2회"가 트레이스와 불일치. ③ 1행 Kirby "일치" |
| 7 | absent | 리뷰는 명시적으로 제외했다 |
| 8 | absent | — |

## 5. 영향이 가장 큰 수정 3가지

1. **Qobuz와 Apple의 곡별 크레딧을 열어 C6을 기준 행으로 판정한다.**
   - Explicit판과 Clean판의 3번 트랙 Dahi 역할 차이를 판본 단위로 명시한다.
   - Dacoury Natche와 Dahi가 같은 인물인지(행 안에서 곡 번호가 함께 나타남)도 같이 정리한다.
2. **C1의 Apple 성명 의역을 원문의 인과에 맞게 고친다.**
   - 쉬워진 이유는 아티스트와 청중이 분리되지 않는다는 깨달음이다.
   - 사랑에 관한 교훈은 작업 막바지에 얻은 것이다.
3. **접근 경로 표시와 기록을 바로잡는다.**
   - fetch 요약은 "요약 경유"(relayed)로 표시한다.
   - Rolling Stone은 402 1건과 미추적 1건으로, 검색 횟수와 ③ 1행의 Kirby 근거도 트레이스에 맞게 고친다.

## 6. D8–D11 메모와 전체 신뢰도

- **D8**: Apollo XXI 비교는 제작 조건이라는 구체적 이유가 있고, "혼자→협업" 같은 결론을 미리 정해 두지 않고 유보했다. 양호하다.
- **D9**: 대부분의 단위가 조사·검증·탐색에 쓰인다. ①의 "실행 메타데이터"와 ⑤ 일부는 건너뛰어도 되는 수준이다.
- **D10**: 44회 호출. Genius·WhoSampled·Guardian에서 실패하면 다른 경로로 전환했다. 다만 다음 두 가지를 놓쳤다.
  - Qobuz는 검색에서 못 찾은 뒤 직접 열람을 시도하지 않았다.
  - Rolling Stone(Fousheé)과 Billboard의 리다이렉트를 따라가지 않았다.
  - 막판에 Grammy 작가 명단을 확인한 것은 유효한 교차 확인이었다.
- **D11**(추정, 과업 기록 없음): 크레딧을 판정하려면 오너가 직접 기준 행을 대조해야 한다. 인용 쪽은 가볍게 검증하면 된다.
- **전체 신뢰도: 중간.** 인용·크레딧·접근성은 직접 확인했다. G4 의심 사례의 중심성은 오너가 판정해야 한다.

```json
{"label": "D06", "D1": "BORDERLINE", "D2": "BORDERLINE", "D3": "PASS", "D4": "PASS", "D5": "BORDERLINE", "D6": "FAIL", "D7": "NOT_ASSESSED", "gate_allegations": [{"gate": "G4", "location": "② C1 third bullet (Apple Music artist statement paraphrase: 'easy and fun' causally attached to unconditional love)", "confidence": "low"}], "recurring_defects": {"1": "absent", "2": "present", "3": "absent", "4": "present", "5": "absent", "6": "present", "7": "absent", "8": "absent"}}
```