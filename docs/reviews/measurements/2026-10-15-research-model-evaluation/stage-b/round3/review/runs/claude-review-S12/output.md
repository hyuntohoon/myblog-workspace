# 감사 보고서 — 노트 S12 (Steve Lacy, *Gemini Rights*)

## 1. 감사 분모

- **직접 시도한 URL은 7건이고 6건을 얻었다.** 얻은 것은 GRAMMY.com(S1), W(S5), Sound On Sound(S6), Qobuz(S7), 위키백과 "Gemini Rights"(S8), 그리고 검색 1건(Mercury–Kendricks)이다. The Guardian(S10)은 감사자 환경에서도 열리지 않았다.
- **점검한 원자적 주장은 약 38건이다.** 이 중 약 26건은 트레이스와 대조했고 12건은 감사자가 직접 연 원문과 대조했다.
- **중심 주장은 14건으로 보았다.** K1 인용 2건, K2(90% 발언, 유통 크레딧상 프로듀서 9/10, Dahi 3·4·10), K3(W 인용, SoS 서술, 엔지니어·믹스·마스터 10/10), K4 상충, K5 3개 항목과 Pogue 인용, K6 인용과 크레딧, K7 배킹 보컬, K8 샘플 2건이다.
- **판정 결과**
  - 지지(supported): 35건
  - 부정확(imprecise): 2건, 모두 주변 주장 (아래 D2)
  - 판단 불가(unassessable): 1건. K5의 "June 2021 세션·15~20분 프리스타일"을 Guardian 출처로 귀속한 부분이다. Guardian은 열리지 않았고, 위키백과의 해당 문단에는 인라인 출처가 없다.
  - 정밀도: 35/37
- **접근 한계**
  - Genius, Guardian, GQ는 차단, Rolling Stone·Billboard는 402, WhoSampled는 403이었다.
  - 오디오는 확인할 수 없었다.
  - WebFetch 결과는 모델이 가공한 텍스트이므로, 감사자가 확인한 인용도 가공 출력에 기반한다.

## 2. D1–D6

| 차원 | 수준 | 결정적 근거 |
|---|---|---|
| D1 대상 고정 | **PASS** | ①에서 Spotify ID와 표준판 10곡을 명시했다. Spotify 페이지를 열지 않았다는 사실, 바이닐이 같은 10곡이라는 것은 [검색 결과 경유]라는 사실, Sped Up이 대상 밖이라는 사실을 모두 주장 단위로 공개했다. Qobuz에서도 10트랙·34:57이 확인된다. |
| D2 정확성 | **BORDERLINE** | 중심 주장의 오류는 없다. Qobuz의 역할 문자열(K2·K4·K6·K7)이 노트와 전부 일치하고, W·GRAMMY·SoS 인용도 감사자가 연 원문과 일치한다. 주변 부정확 2건: ① K4 "위키백과 작곡 표기는 Qobuz와 일치함" — 10번 트랙에서 Qobuz에만 Margaux A. R. Whitney가 있다(위키 표기는 Lacy·Natche·Rise). ② K5 "결말부는 Diana Gordon이 썼다" — 위키백과 S9는 "part of the ending"이라고 한다. 범위가 넓어졌다. |
| D3 귀속 | **PASS** | Apple Music 텍스트를 "아티스트 명의 성명"으로 표시했다(S2). SoS는 기자 서술과 Pogue 발언, 그리고 "Pogue의 전언"을 구분했다(K3·K5). Complex와 Okayplayer가 같은 원본을 옮겼으므로 독립 근거가 아니라고 명시했다(K2). GRAMMY의 Martians 관련 인용은 화자 불명으로 보고 제외했다(S1). 감사자 확인 결과 이 인용의 화자는 Lacy였으므로 제외는 보수적 판단이지 오류가 아니다. |
| D4 추적성 | **BORDERLINE** | 중심 인용은 짧은 기사에서 빠르게 회수된다. 다만 세 가지 문제가 있다. S10(Guardian), S8·S9(위키백과), S14(FADER)에 URL이 없다. K5를 확인하려면 10만 자가 넘는 위키백과 페이지를 거쳐야 한다. S13에 적힌 URL(`/sample/965926/`)은 실제로 fetch한 적이 없고, 403이 난 곳은 `/Steve-Lacy/2Gether-(Enterlude)/`이다. |
| D5 출처 전달 | **BORDERLINE** | 재인용·검색 결과 경유·미확인 표시는 대체로 정확하다(K5, K8, Mercury 샘플). 그러나 K1·K3·K6·S1·S2·S5·S7에 붙은 "원문 확인" 라벨은 모델 가공 WebFetch 요약에 붙어 있다. M1에 따르면 이는 *relayed*이므로 접근 경로를 과장한 것이다. 내용은 감사에서 지지되었으므로 귀결은 없다. |
| D6 크레딧·판본 | **PASS** | 명명된 행(Qobuz)을 기준으로 원래 역할 문자열과 트랙 번호를 제시했다. "John Kirby" 표기 차이와 Yuli=Whitney 미확인도 기록했다. "10곡 중 9곡, 2Gether 제외"처럼 집계에 분자·분모·제외 항목을 밝혔다. Sunshine에 대해서는 Genius 모호 규칙을 지켰다. 다만 Genius의 "Dahi 작곡 3/9"와 Qobuz의 "Dacoury Natche"를 연결하지 않았다(소소한 누락). |
| D7 누락 | **NOT_ASSESSED** | M4(동결된 top-3 지도 없음) |

## 3. 무결성 게이트 위반 주장

**없음.** 이번 감사에서 게이트 위반은 발견되지 않았다.

- G6: Mercury–Kendricks를 "확인하지 못함이지 샘플이 없다는 뜻이 아니다"로 처리했다. 해당 패턴이 없다.
- G3a: 사운드를 노트 자신의 관찰로 묘사한 곳이 없다. 청취 질문은 질문 형태로 되어 있다.
- G8: 검색 결과 안의 "REMINDER" 문구는 도구 텍스트다. 노트는 이를 따르지 않았다.

## 4. 반복 결함

1. **absent.** K5의 "[직접 발언·재인용]"은 검색 요약이 Lacy의 Guardian 발언으로 제시한 것을 옮긴 것이다. 생산자가 서술을 발언으로 승격한 것은 아니다.
2. **present.** K1, K3, K6, 부록 S1, S2, S5, S7에서 가공 요약을 "원문 확인"으로 표기했다.
3. **absent.**
4. **absent.** Qobuz, Genius, 위키백과를 교차 대조했다.
5. **absent.** "유일한 피처링"은 Lacy 발언 취지로 귀속했고, 2Gether는 "with" 표기다.
6. **absent.** 4/10의 분자 기준이 명시되어 있다.
7. **absent.**
8. **absent.** Guardian 접근 실패가 다섯 곳에서 반복되지만 경미하다.

## 5. 영향이 큰 수정 3가지

1. **출처 라벨 교정(D5).** WebFetch 요약은 "가공 요약 경유"로 표시한다. "원문 확인"은 생산자가 가공되지 않은 원문을 직접 본 경우에만 쓴다.
2. **K5 항목별 출처 분리.** Gordon 관련 내용과 "제출 1주 전 완성"은 위키백과가 Guardian을 인용한 것이다. June 2021 세션과 프리스타일은 위키백과에 인라인 출처가 없고 검색 요약만 Guardian에 귀속한다. 이 둘을 구분해 적는다. 결말부는 "part of the ending"으로 범위를 바로잡고 Guardian URL을 추가한다.
3. **추적성과 정밀성 보정.** S13 URL을 실제로 403이 난 경로와 맞춘다. S8·S9·S10·S14에 URL을 넣는다. K4의 "위키·Qobuz 일치"에 10번 트랙 Whitney 예외를 단다. Dacoury Natche(=Dahi로 추정)와 Genius 작곡 집계의 관계를 명시한다. Billboard 402도 접근 제한 목록에 추가한다.

## 6. D8–D11 및 종합 신뢰도

- **D8:** 맥락 단서가 앨범에 한정되어 있다. 이별 서사, 전작 대비 작업 조건, 믹스상 보컬 위치가 그렇다. 결론은 청취 질문으로 평론가에게 남겼다. 비교 근거도 구체적이다(SoS, W).
- **D9:** 단위 대부분이 조사나 검증에 쓰인다. 부록의 S12(Rolling Stone)는 본문에서 쓰이지 않는다. 접근 실패를 반복 서술한 부분은 건너뛰어도 된다.
- **D10:** 42건의 호출 가운데 실패와 차단이 9건이었다. 차단된 곳은 위키백과·검색으로 우회했고, 같은 실패를 반복하지 않았다. 후반의 Mellohi·Kendricks 검색이 상충 해소에 기여했다.
- **D11:** 과업 기록이 없다. 오너에게 남는 작업은 Guardian 원문, 부클릿, WhoSampled 확인으로 추정된다.
- **종합 신뢰도: 중상.** Guardian 귀속 1건은 판단할 수 없다. 오너가 이를 중심 주장으로 판정하면 §2 규칙에 따라 수용이 보류된다.

```json
{"label": "S12", "D1": "PASS", "D2": "BORDERLINE", "D3": "PASS", "D4": "BORDERLINE", "D5": "BORDERLINE", "D6": "PASS", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "present", "3": "absent", "4": "absent", "5": "absent", "6": "absent", "7": "absent", "8": "absent"}}
```