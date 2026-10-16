# R11 개별 감사: Steve Lacy, *Gemini Rights* 조사 노트

## 판정 요약

- **총점: 49.5 / 100**
- **신뢰도: 중간.** 핵심 출처 5개는 원문으로 다시 확인했습니다. Zane Lowe 원 인터뷰, GQ, Guardian은 열지 않았습니다.
- **채택 불가.** 루브릭의 "검증되지 않은 핵심 주장" 기준에 걸립니다.
  - C5는 출처를 밝히지 않은 크레딧 상충입니다. 이것이 ④ 미해결 목록의 1순위로 올라가 있습니다.
  - C2와 C8에서는 발언을 실제로 싣지 않은 매체에 인용을 귀속했습니다.

## 감사 범위와 접근 한계

- **열려고 시도한 URL 9개, 확보 8개.**
  - 확보: GRAMMY, Complex, Crack, Wikipedia(*Gemini Rights*), Wikipedia(*Bad Habit*), Qobuz, AnOther, Apple Music
  - 실패: AOL은 HTTP 404였습니다. 생성기도 이 페이지를 열지 않았고 검색 스니펫만 썼습니다.
- **보조 검색 1회:** Zane Lowe 인터뷰 재인용 경로 확인용입니다.
- **확인하지 않은 자료:** Sound on Sound, GQ, Guardian, Zane Lowe 인터뷰 원본.
- **원자 주장 21개를 확인했습니다.**
  - 지지됨: 12개
  - 일부만 지지되거나 범위 문제: 4개
  - 오귀속·오류·부정 반전: 5개
- **도구 한계:** WebFetch는 요약 모델을 거쳐 결과를 돌려줍니다. 따라서 제가 확인한 내용도 원문을 문자 그대로 대조한 것은 아닙니다.
- **기계적 지표**
  - 본문 ①–④ 약 3,400자: 목표 범위 상한을 넘었지만 그 이유를 설명하지 않았습니다.
  - 부록 약 900자
  - 고유 URL 7개, 도메인 6종
  - 생성기가 실제로 연 URL 5개, 검색으로만 접한 URL 2개(Crack, AOL)
  - Sources 목록이 부록 표를 그대로 반복합니다.

## 차원별 점수

| 차원 | 점수(0–5) | 가중 점수 | 근거 |
|---|---:|---:|---|
| 사실 정확성·귀속 | 2.5 | 12.5 | C1과 C7의 인용은 정확합니다. 반면 C2, C3, C7, C8과 ③의 프로듀서 열에 오귀속과 부정 반전이 있습니다(아래 참조). |
| 중요 근거·누락 | 2 | 8 | AnOther, Apple 성명 본문, 편집 공정, 유통 크레딧이 빠졌습니다. |
| 출처 추적성 | 2 | 8 | 주장과 URL은 연결돼 있습니다. 그러나 문단 위치와 최소 발췌가 없고, 이름 없는 출처와 스니펫을 근거로 썼으며, 독립 평론(Crack)을 사실 근거로 사용했습니다. |
| 크레딧·샘플·불확실성 | 2 | 4 | 샘플 문제는 "미확인"으로 정직하게 남겼습니다. 그러나 프로듀서 열이 틀렸고, C5의 상충은 근거가 없습니다. |
| 관련성·밀도 | 4 | 8 | 전기·게임 같은 곁가지는 없습니다. Sources 목록이 중복입니다. |
| 음악적 맥락 | 3 | 6 | 들은 척하거나 판정을 내린 부분은 없습니다. 다만 전작 맥락을 평론 한 편에 의존했고, 비교 후보가 없습니다. |
| 평론가 활용성 | 3 | 3 | 구조와 전곡 점검표는 좋습니다. 그러나 점검표 데이터에 오류가 있고, 추가 확인 1순위가 근거 없는 상충입니다. |
| **합계** | | **49.5** | |

## 심각한 결함 (위치·근거)

1. **② C5와 ④-1: 출처 없는 상충을 최우선 미해결 과제로 올렸습니다.**
   - "Lacy+Kirby 공동 프로듀서"는 trace seq 2의 검색 요약에 나온 "another source"가 유일한 근거입니다. URL이 없습니다.
   - 다른 자료는 모두 Lacy 단독 프로듀서입니다.
     - Wikipedia *Bad Habit* Personnel: "Credits adapted from liner notes", Steve Lacy "production"
     - Qobuz 크레딧 필드: Producer Steve Lacy
   - 상충이 아니라 근거 없는 주장입니다.

2. **② C2와 C8: 매체에 없는 발언을 그 매체에 귀속했습니다.**
   - C2는 90% 발언이 "Complex, Crack Magazine 등"에 실렸다고 씁니다. Crack 기사(Ecleen Luzmila Caraballo, 2022-07-15, 앨범 평론)에는 90% 발언이 없습니다.
   - C8의 "외부 총괄 프로듀서를 쓰려 했지만…"은 Crack에도 Complex(S4)에도 없습니다. 이 문구는 검색 요약에서 왔습니다.
   - 보조 검색 결과를 보면 발언 자체는 Consequence 계열 재인용 경로에 존재하는 것으로 보입니다. 다만 노트에 연결된 URL로는 이를 추적할 수 없습니다.

3. **② C3: "약 절반을 Fousheé와 공동 작곡"을 Complex에 귀속했습니다.**
   - Complex 원문에는 이 내용이 없습니다. 생성기 자신의 fetch(seq 12)에도 없었습니다.
   - 또 C3은 "트랙 분모가 명시되지 않았다"고 하지만, 노트가 이미 확보한 Wikipedia 표로 계산할 수 있습니다. Fousheé의 작사·작곡 크레딧은 4/10곡입니다(Mercury, Bad Habit, Cody Freestyle, Sunshine).

4. **② C7: 부정 반전입니다.**
   - 노트는 가족 참여 트랙을 "어느 트랙인지는 특정되지 않았다"고 씁니다.
   - GRAMMY 원문에서 Lacy는 직접 트랙을 밝힙니다.
     - Helmet: "la-la" 부분
     - Amber: 베이스가 들어오는 부분의 큰 고조
     - Give You The World: "goodbye" 부분
     - Mercury: 녹음했지만 "pitchy"해서 쓰지 못함
   - 같은 내용이 Wikipedia Personnel의 배경 보컬(2, 8, 10번 트랙)으로도 교차 확인됩니다.
   - C7을 [보도]로 분류한 것도 틀렸습니다. Lacy의 직접 발언입니다.

5. **③ 프로듀서 열: 생성기가 이미 열어 본 자료(seq 6: "Steve Lacy 1–5, 7–10번")와 모순됩니다.**
   - Static, Helmet, Cody Freestyle, Amber, Sunshine을 "명시 안 됨"으로 적었습니다.
   - Mercury와 Give You the World는 "Martians/Dahi"로 적어 Lacy를 빠뜨렸습니다.
   - Give You the World에는 Matt Martians의 프로듀서 크레딧이 없습니다. Wikipedia와 Qobuz 모두 Lacy와 DJ Dahi입니다.

6. **C8: 독립 평론을 사실 근거로 사용했습니다.** 생성 프롬프트 §10 위반입니다.
   - Crack 평론을 *Apollo XXI* 대비의 핵심 근거로 썼습니다.
   - 같은 주제에 대해 AnOther(Ted Stansfield, 2022-09-20)의 기자 서술이 있었는데 찾지 못했습니다. 이 기사는 "혼자 다 하다가 벽에 부딪혀 타인의 의견에 더 열리려 했다"는 내용을 서술합니다.

## 지지되는 부분

- **C1:** "Gemini Rights is essentially me coming into myself after a breakup"은 GRAMMY 원문에 있는 Lacy의 직접 답변입니다. "원문 확인" 표시와 한계 서술 모두 적절합니다.
- **C2:** 90% 발언이 Complex에 실렸다는 점, 그리고 원 인터뷰를 열지 못했다는 고지는 정확합니다.
- **C4:** Wikipedia 서술과 일치합니다.
  - Diana Gordon의 엔딩 참여, RCA 제출 1주 전 완성: Guardian 인용
  - "renaissance" 발언: GQ 인용
  - Tyler, the Creator 피드백: Billboard 인용
  - 다만 June 2021 날짜와 20분 프리스타일 문장은 Wikipedia에 각주가 없습니다. 또 GRAMMY 원문의 "약 20분"은 *Sunshine* 즉흥 세션을 가리킵니다. 노트는 이 혼동 가능성을 짚지 않았습니다.
- **기타 확인된 사실**
  - 작사·작곡 표(C6)는 Wikipedia와 일치합니다.
  - Amber가 Lacy 단독 작사·작곡이라는 점도 맞습니다.
  - *Mercury*를 두고 "보사노바·펑크 서술이 어느 곡을 가리키는지 불확실"하다고 쓴 것은 정확한 범위 설정입니다. GRAMMY 원문도 곡명을 밝히지 않습니다.
- **불확실성 처리**
  - 청취하지 않았다는 고지, 샘플 문제의 "미확인" 처리, 실행 메타데이터를 지어내지 않은 점은 양호합니다.

## 중요한 누락

- **AnOther:** 기자 서술(2년 작업, 300곡 이상 중 10곡 선별)과 제목 유래에 관한 직접 발언("gay rights"를 "Gemini rights"로 바꾼 농담, 곡을 쓰기 전에 제목이 먼저 정해짐)이 빠졌습니다.
  - 노트는 제목 유래 자체를 다루지 않습니다. 생성기는 Wikipedia·Complex의 "tipsy in a bar" 서술까지만 접했습니다.
- **Apple Music 성명(S6):** 서명된 성명의 내용(예술가와 청중의 분리, 사랑을 작게 만들어 왔다는 성찰, 감정)을 본문에 반영하지 않았습니다. "전문 미확보"라고 했지만, 실제 페이지에서는 "—Steve Lacy" 서명과 핵심 문장들을 확인할 수 있습니다.
- **GRAMMY 편집 공정:** "blurt words out… edit, edit, edit", "you got to make trash", Sunshine의 약 20분 즉흥 후 편집, B-sides 질문("Maybe, yeah?")이 빠졌습니다. 구체적인 제작 사실인데 누락됐습니다.
- **유통 크레딧(Qobuz 등):** 확인하지 않았습니다.
  - 확인했다면 C5가 바로 해소됐을 것입니다.
  - Give You the World의 작곡자 표기 차이(Qobuz에는 Margaux Whitney가 추가됨)도 발견할 수 있었습니다.
- **Sound on Sound:** *Bad Habit* Inside Track 기사를 시도하지 않았습니다.

## 링크가 주장을 실제로 지지하는가

| 출처 | 판정 |
|---|---|
| S1 GRAMMY | 지지. 단, C7의 "트랙 미특정"은 반대 방향으로 잘못 읽음 |
| S2 Wikipedia *Gemini Rights* | 작사·작곡은 지지. 프로듀서 열은 원문과 불일치 |
| S3 Wikipedia *Bad Habit* | 연대기는 지지. C5의 "상충"은 지지하지 않음(Lacy 단독만 기재) |
| S4 Complex | 90%와 관련해서만 지지. "절반 공동작곡"과 "총괄 프로듀서" 발언은 없음 |
| S5 Crack | 평론. 노트북 기반 DIY와 "full studio treatment" 서술만 있고, 90%·총괄 프로듀서 발언은 없음 |
| S6 Apple | 성명은 존재. 본문에서는 활용하지 않음 |
| S7 AOL | 생성기가 열지 않음. 제가 시도했을 때는 404. 상태 표기 누락 |

또 Wikipedia를 [DB등재]로 분류했는데, 프롬프트의 분류 체계상 부정확합니다. 2차 편집물(백과사전)이므로 [보도·재인용]에 가깝습니다.

## 영향이 가장 큰 수정 3가지

1. **C5와 ④-1 삭제 또는 재작성.** Wikipedia Personnel(라이너 노트 기반)과 Qobuz 크레딧 필드를 근거로 "Lacy 단독, 2개 경로에서 일치, 실물 부클릿과는 미대조"로 바꿉니다. 미해결 1순위 자리는 Zane Lowe 원문 확보로 교체합니다.
2. **C2·C3·C8과 ③ 프로듀서 열 정정.**
   - 인용은 실제로 실린 URL에만 귀속합니다. 찾지 못했다면 [검색 결과 경유]로 낮춥니다.
   - 프로듀서 열은 seq 6과 Qobuz 값으로 다시 채웁니다.
   - Fousheé 크레딧 4/10곡을 분모와 함께 적고, "약 절반"이라는 발언과 나란히 둡니다.
3. **C7과 C8 보강.**
   - C7은 GRAMMY 원문의 트랙별 직접 발언(Helmet, Amber, Give You the World 사용, Mercury 미사용)으로 바꿉니다.
   - C8의 근거는 Crack 평론 대신 AnOther 기자 서술과 직접 발언으로 교체합니다.
   - 편집 공정 발언을 핵심 근거에 추가합니다.

## 평론가 사용 적합성

**잠정 부적합입니다.** 형식(ID, 상태 라벨, 전곡 점검표, 한계 고지)은 좋습니다. 하지만 점검표의 프로듀서 데이터가 틀렸고, 평론가가 우선 확인하도록 안내한 항목이 근거 없는 상충입니다. 인용 귀속 오류도 있어 그대로 넘기면 평론가를 잘못된 방향으로 이끌 수 있습니다. 위 수정 3가지를 반영하면 보조 자료로 쓸 수 있는 수준입니다.

## 잠정 평가와 실패 원인 분리

- 이 샘플은 1회 생성 결과 하나입니다. 다른 샘플과 비교하지 않았고, 일반적 우열이나 재현성에 대해서는 결론을 낼 수 없습니다.
- **모델 실패**
  - 이미 확보한 원문(seq 6)과 점검표가 모순되는데 정리하지 않았습니다.
  - 검색 요약의 "another source"를 [상충]으로 올렸습니다.
  - 인용을 엉뚱한 매체에 귀속했습니다.
  - 평론을 근거로 썼습니다. 프롬프트가 금지한 사항입니다.
- **하네스 요인**
  - WebSearch와 WebFetch가 요약 모델을 거칩니다. 그 결과 출처 없는 문장("another source")과 매체 간 혼합 요약이 그대로 유입됐습니다.
  - 생성기는 GRAMMY 원문을 받았지만, 125자 인용 제한이 걸린 요약만 볼 수 있었습니다. 이 때문에 가족 참여 트랙 정보를 놓쳤을 가능성이 있습니다.
- **프롬프트 요인**
  - [DB등재] 라벨에 백과사전과 데이터베이스의 구분이 없습니다.
  - 유통 크레딧 페이지(Qobuz, Tidal 등)를 표준 점검 경로로 명시하지 않았습니다.

## 프롬프트 개정안

1. "[상충]은 양쪽 출처를 URL과 위치로 각각 기록할 때만 사용한다. 검색 요약 속 이름 없는 출처는 [검색 결과 경유]로만 둔다."
2. "직접 연 페이지의 텍스트에서 확인하지 않은 인용은 그 URL에 귀속하지 않는다. 부록에는 '직접 열람/스니펫만'을 구분하는 열을 둔다."
3. "'특정되지 않았다', '명시 안 됨' 같은 부정 서술은 해당 원문의 관련 단락을 다시 확인한 뒤에만 쓴다."
4. "점검표의 각 열은 출처를 하나씩 지정해 채우고, 본문 표와 수치가 일치하는지 대조한다."
5. "크레딧 점검에는 위키 외에 유통 서비스의 트랙별 크레딧 필드를 최소 한 곳 포함하고, 같은 페이지의 리뷰 문단은 제외한다."
6. "[DB등재]는 크레딧·샘플 데이터베이스에만 쓰고, 위키 같은 백과사전은 [보도·재인용]으로 표기한다."

Sources:
- [GRAMMY.com 인터뷰](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags)
- [Complex](https://www.complex.com/music/steve-lacy-gemini-rights-album)
- [Crack Magazine 평론](https://crackmagazine.net/?p=185292)
- [Wikipedia – Gemini Rights](https://en.wikipedia.org/wiki/Gemini_Rights)
- [Wikipedia – Bad Habit](https://en.wikipedia.org/wiki/Bad_Habit_(Steve_Lacy_song))
- [Qobuz 크레딧](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/zbylnavz5biaa)
- [AnOther](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album)
- [Apple Music 앨범 페이지](https://music.apple.com/us/album/gemini-rights/1631909576)
- [AOL (404)](https://www.aol.com/news/led-surprise-no-1-hit-130028830.html)