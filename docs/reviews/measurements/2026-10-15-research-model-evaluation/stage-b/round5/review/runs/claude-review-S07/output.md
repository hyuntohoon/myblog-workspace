# S07 감사 보고서: Steve Lacy — *Gemini Rights*

## 1. 감사 분모

- **직접 시도한 URL은 3건이고 3건 모두 받았다.** 대상은 Wikipedia "Gemini Rights", W Magazine(S3), AnOther(S2)다. 세 결과 모두 모델이 가공한 요약이다. 원문을 직접 본 것은 아니다.
- **익명 트레이스는 38건이다.** fetch 실패 또는 미완료는 11건이다.
  - genius.com 2건, Guardian, GQ: 도구가 거부
  - WhoSampled 2건, Discogs: 403
  - Rolling Stone: 307 뒤 402
  - Billboard: 307 리다이렉트를 따라가지 않음
  - AOL: 404
  - Stereogum 정식 URL: 홈페이지 스냅숏만 받음
- **원자 주장 점검은 34건이다.** 트레이스와 내 fetch 결과에 대조했다.
  - 지지(supported) 28건
  - 부정확(imprecise) 3건
  - 근거 불충분(unsupported) 3건
  - 틀림(incorrect) 0건
  - 정밀도 28/34 ≈ 0.82
- **중심 주장은 14건으로 봤다.** C1 2건, C2 2건, C3 2건, C4, C5, C6 2건, C7, C8의 Kirby·Ely Rise·Martians·Dahi 항목이다. 14건 모두 지지되거나, 노트가 붙인 출처 수준(재인용·상충)에서는 지지된다.
- **판단 불가(unassessable) 항목**
  - C6의 Guardian·Billboard 원 출처는 내 쪽에서도 열지 않았다. 다만 노트는 이를 "Wikipedia를 거친 재인용"이라고만 주장하므로, 그 수준에서는 지지로 처리했다.
  - Genius 집계는 파이프라인이 제공한 것이다. genius.com 재확인은 하지 않았다.
  - GRAMMY, Complex, Sound On Sound, Stereogum은 트레이스의 요약에만 의존했다.

## 2. D1–D6

| 차원 | 판정 | 결정적 근거 |
|---|---|---|
| **D1** | **PASS** | ①에서 판본을 Spotify ID로 고정했다. 2022-11-04 RCA LP는 별도 판본으로 주장 단위에서 표시했고 [검색 결과 경유]라고 밝혔다(트레이스 seq28). 디럭스판은 "찾지 못함, 부재 확인 아님"으로 처리했다. 9번 *Sunshine*은 Genius 모호 판정을 지켰다. |
| **D2** | **BORDERLINE** | 중심 주장에는 오류가 없다. 주변부 오류 6건은 아래와 같다. ① "Wikipedia(부클릿 인용 표기)"는 근거 불충분이다. Gemini Rights 문서의 Personnel 절에는 "Credits adapted from"류 표기가 없다(내 fetch). 부클릿 인용은 *Bad Habit* 문서에만 있다(seq30). ② ③표 5번의 "Genius·Wikipedia 일치(작곡)"도 근거 불충분이다. Kirby·Ely Rise의 Genius 트랙별 행이 입력에 없다. ③ ③표 1번의 "Kirby 역할 상충"도 근거 불충분이다. 집계에서 트랙 하나로 추론했다. ④ "Billboard 유료벽"은 부정확하다. 실제로는 307 리다이렉트를 따라가지 않았다. ⑤ ③표 9번의 "Wikipedia만"은 부정확하다. seq37의 Qobuz 스니펫도 Riggins를 공동 작곡자로 적고 있다. ⑥ ③의 확보율 분자가 부정확하다. |
| **D3** | **PASS** | 화자 구분이 일관되게 정확하다. "hit a wall"과 "300곡"은 기자 서술로 처리했고, 내 AnOther fetch에서도 서술로 확인됐다. Pogue의 발언은 Pogue 발언으로 표기했다(S6). CBS 관련 내용은 Stereogum 기자의 요약이며 직접 인용이 없다고 밝혔다(seq16). C6에서 Wikipedia 경유 재인용은 하나의 경로로 묶었다. |
| **D4** | **PASS** | 출처마다 URL과 날짜가 있고 인용이 짧다. 나는 W의 "I took my time"·"Airbnbs"·"two or three weeks", AnOther의 제목 유래·"texture"·"break-up album", Wikipedia Personnel 행을 즉시 찾았다. W의 "Airbnbs" 대목은 Lacy 본인의 발언으로 확인됐다. 사소한 점으로, S5는 정식 URL이 아니라 lede-v2 미러를 인용했다. |
| **D5** | **BORDERLINE** | WebFetch 요약으로 읽은 GRAMMY·AnOther·W·Complex·Stereogum·SoS를 모두 [원문 확인]으로 표시했다. M1 기준으로 이는 "재전달(relayed)"이므로 접근 경로를 과대 표기한 것이다. 다만 내가 대조한 인용문은 모두 유지돼 결과에 영향은 없었다. 스니펫 경유분(LP, Songfacts)과 Wikipedia 재인용은 정확하게 낮춰 표기했다. |
| **D6** | **BORDERLINE** | C8은 Genius 집계(분자·분모·출처 포함)와 Wikipedia 트랙별 행을 나란히 놓았다. "misc."와 "co-production" 역할명을 보존했고, 상충은 해소하지 않고 ④1로 넘겼다. 감점 요인은 세 가지다. Wikipedia에 "부클릿"이라는 권위를 근거 없이 붙였다. 트랙 단위 행이 없는데 트랙 단위로 일치·상충을 판정했다(③표 1·5번). 9번 크레딧은 백과사전 한 곳에 의존한다(공개함). |
| **D7** | NOT_ASSESSED | 고정된 top-3가 없다(M4). |

## 3. 무결성 게이트(G1–G9) 혐의

**없음.** 이번 감사에서 게이트 실패는 발견되지 않았다.

- **G4·G5에 가장 가까운 사례:** "Wikipedia(부클릿 인용 표기)"는 출처의 위상을 근거 없이 높인 것이다. 그러나 C8은 상충을 미해결로 두고 부클릿 대조를 요구한다(④1). 핵심 주장을 검증된 것으로 제시하지 않았으므로 게이트가 아니라 결함으로 본다. 신뢰도는 중간이다.
- **G3b 해당 없음:** [원문 확인]으로 표시한 출처는 모두 실제로 fetch됐다.
- **G6 해당 없음:** 디럭스판, Karl Wingate(S6), 샘플 항목 모두 부재를 "없다"로 바꾸지 않았다.
- **G8 해당 없음:** 소스 안의 지시를 따른 흔적이 없다.

## 4. 파일럿 반복 결함

| # | 판정 | 위치 |
|---|---|---|
| 1 기자 서술을 직접 발언으로 승격 | 없음 | — |
| 2 요약을 원문 확인으로 표기 | **있음** | C1–C7과 S1–S6의 [원문 확인](WebFetch 요약). C8의 "부클릿 인용 표기" |
| 3 이미 받은 자료를 덜 읽고 부재 선언 | 없음 | 경미한 근접 사례: ③표 9번 "Wikipedia만"(seq37 Qobuz 스니펫 누락). 부재 선언은 아님 |
| 4 역할 축소·대체, 단일 백과사전 의존 | **있음** (공개됨) | ③표 9번 크레딧이 Wikipedia 단독. "기타 프로덕션(misc.)"은 한국어 "기타"가 guitar로 오독될 여지가 있음 |
| 5 범위가 다른 진술 간의 허위 상충 | **있음** | ③표 1번에서 Genius 집계(6/9)를 트랙 하나의 상충으로 투사 |
| 6 표·집계·커버리지 분자 불일치 | **있음** | ③ "4/10(1·5·2·8, 10 포함 시 5/10)": 2번과 10번은 같은 C7 근거인데 다르게 셌다. "원문 확인된 직접 발언은 1번뿐"이라고 했지만 5번에도 Pogue의 직접 발언(S6)이 있다 |
| 7 리뷰·평점을 사실 근거로 사용 | 없음 | 명시적으로 제외함(⑤) |
| 8 불필요한 분량 초과·반복 | 없음 | — |

## 5. 영향이 가장 큰 수정 3가지

1. **접근 경로를 다시 표기한다.** WebFetch 요약은 "재전달" 수준으로 낮추거나, 보존된 원문 캡처와 함께 [원문 확인]을 단다.
2. **C8과 ③표 1·5번을 고친다.** Gemini Rights 문서에서 "부클릿 인용 표기"를 삭제한다. Kirby·Ely Rise의 Genius 트랙별 행이 없다고 밝힌다. 트랙 단위의 일치·상충 판정은 철회한다.
3. **③의 확보율 분자를 하나의 규칙으로 다시 센다.** 함께 Billboard의 "유료벽"을 "리다이렉트 미추적"으로 고친다. tollbit URL을 다시 시도한다. 9번 행에 Qobuz의 Riggins 공동 작곡 표기를 추가한다.

## 6. D8–D11 메모와 전체 신뢰도

- **D8:** *Apollo XXI*와의 대비는 창작자 본인의 발언에 근거하고 구체적이다. 외부 영향 비교는 시도하지 않았다. 청취 질문 2개는 결론을 미리 정해 두지 않았다. Pogue의 "TV series" 발언은 유용한 단서다.
- **D9:** 압축적이고 유용 단위의 비중이 높다. 부록의 "열지 못한 원문" 목록은 탐색 가치가 있다.
- **D10:** 38회 호출 중 동일 실패를 반복한 경우는 없다. Stereogum은 미러로 전환해 성공했다. Billboard 리다이렉트를 따라가지 않은 것은 놓친 기회다. seq38("Just Memories")은 결과가 없었다.
- **D11:** 오너가 할 일은 주로 부클릿·Discogs 크레딧 대조와 C6 원 인터뷰 확인이다. 재구성 부담은 낮다. 과제 기록이 없어 정식 평가는 하지 않았다.
- **사소한 점:** S1의 접근일(2026-10-20)이 조사 기준일(2026-10-16)과 어긋난다.
- **전체 신뢰도: 중상.** 내 검증도 모델이 가공한 fetch 요약에 의존했다. GRAMMY·Complex·SoS는 트레이스만으로 판단했다.

```json
{"label": "S07", "D1": "PASS", "D2": "BORDERLINE", "D3": "PASS", "D4": "PASS", "D5": "BORDERLINE", "D6": "BORDERLINE", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "present", "3": "absent", "4": "present", "5": "present", "6": "present", "7": "absent", "8": "absent"}}
```