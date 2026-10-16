# R08 단일 샘플 감사 보고서

## 0. 감사 범위와 접근 상태

- **이번 감사에서 연 URL: 7건 시도, 7건 확보.** GRAMMY.com, AnOther, Qobuz, Sound on Sound, Wikipedia *Gemini Rights*, Wikipedia *Bad Habit*, Songfacts를 열었다. 차트 날짜 확인을 위해 웹 검색도 1회 했다.
- **WebFetch의 한계:** WebFetch는 원문을 요약 모델을 거쳐 돌려준다. 그래서 인용문은 "요약기 반환 원문 기준"이며, 문단 번호까지 대조하지는 못했다.
- **Wikipedia *Bad Habit* 문서:** 문서 끝 5,660자는 읽지 못했다.
- **Apple Music 페이지:** 다시 열지 않았다. 생성기 추적 seq 21의 반환 내용으로 갈음했다.
- **노트가 제시한 URL:** 고유 URL 10개, 도메인 8종이다. 이 중 생성기가 실제로 열어 확보한 것은 5건이다(GRAMMY, Wikipedia 2건, Songfacts, Apple, Complex를 합쳐 6건). 접근에 실패한 것은 Rolling Stone 1건과 WhoSampled 2건이다. **S8(Rolling Stone의 Fousheé 기사)은 추적상 열려는 시도 자체가 없었다.**
- **점검한 원자 주장: 24개.** 결과는 지지 14, 부분 지지·범위 문제 4, 오귀속·미지지·허위 6이다. 정밀도 수치는 위 표본에 한한 것이며, 노트 전체의 정밀도로 일반화하지 않는다.
- **분량(추정치, 정밀 계측 아님):** 본문 ①~④는 약 6,000~7,000자로 기준 상한 3,000자를 크게 넘는다. 넘긴 이유도 적혀 있지 않다. 부록은 약 1,800자다.

## 1. 차원별 점수 (R08)

| 차원 | 0–5 | 가중 점수 | 근거 |
|---|---:|---:|---|
| 사실 정확성·귀속 (25) | 2.0 | 10.0 | 아래 심각 결함 1~4 |
| 중요 근거·누락 (20) | 2.5 | 10.0 | GRAMMY·Apple·Zane Lowe 핵심은 확보. 반면 AnOther(제목 유래, 2년 작업, 300곡 이상에서 10곡 선별), Mercury 가족 녹음 폐기, "only feature", 즉흥 녹음 후 편집 과정, Sound on Sound가 빠졌다 |
| 출처 추적·근거 (20) | 2.0 | 8.0 | 문단 위치와 최소 발췌가 없다. 접근 상태 허위 기재가 있고, 인용된 출처에 해당 내용이 없는 경우가 있다 |
| 크레딧·샘플·불확실성 (10) | 3.0 | 6.0 | Fousheé 4/10은 분모를 밝혔고, Kendricks 샘플은 [미확인]으로 남겼다. 그러나 크레딧 출처가 Wikipedia 하나뿐이고, Qobuz와의 상충을 놓쳤다 |
| 관련성·밀도 (10) | 3.0 | 6.0 | 수상·차트 항목(근거 8), Helmet 뮤직비디오, 본명 같은 저가치 정보가 들어 있고 분량이 초과됐다 |
| 음악 맥락 vs 비평 대체 (10) | 3.0 | 6.0 | 청취했다는 거짓 주장은 없다. 다만 리뷰 스니펫에서 나온 "보사노바 섹션"을 확인 질문에 썼고, Apollo XXI가 랩톱 기반이었다는 대비는 근거가 없다 |
| 평론가 사용성 (5) | 3.5 | 3.5 | 전곡 점검표가 있고, 메타데이터 확인율과 실질 근거율을 분리했으며, 미해결 항목 3개를 제시했다 |
| **총점** | | **49.5 / 100** | 신뢰도: **중간**. 핵심 출처는 열었지만 WebFetch 요약에 의존했다 |

## 2. 심각 결함 (총점과 별도 보고)

1. **인용 출처 오귀속 (근거 4, 부록 S7).** 노트는 "a play on confidence"를 *Rolling Stone* 발언으로 적었다. 그러나 Wikipedia *Bad Habit*은 이 말을 Shaad D'Souza의 **The Guardian** 인터뷰(각주 6)로 귀속한다. Songfacts도 "Lacy to *The Guardian*"으로 표기한다. 노트가 경유했다는 두 자료가 모두 Rolling Stone 귀속을 반박하는 셈이다.
2. **인용된 출처에 해당 내용이 없음 (근거 7).** Breakfast Club의 "I thought that album was a failure"와 Apollo XXI의 그래미 후보 사실을 [S5]로 표시했다. 그러나 Wikipedia *Bad Habit* 문서에는 Breakfast Club, "failure", Best Urban Contemporary Album이 모두 없다. 확인 범위는 앞쪽 10만 자다. 이 내용은 추적상 검색 요약(seq 13)에서만 나왔다.
3. **접근 상태 허위 기재 (부록 S8, "Rolling Stone 본문 2건: HTTP 402").** 추적상 402 응답을 받은 것은 S7 한 건뿐이다. S8은 검색 결과에만 나왔고, 열려는 시도 자체가 없었다. 실패 이력을 지어낸 것이므로 정직한 접근 기록 기준을 위반한다.
4. **검증 라벨 오용 (근거 4).** Wikipedia와 Songfacts를 경유한 발언에 "[직접 발언·원문 확인]"을 붙였다. 프롬프트 정의상 이는 [재인용]이다. 근거 8도 Billboard 차트 페이지를 연 적이 없는데 "[원문 확인(Billboard 차트 데이터)]"로 표기했다.
5. **근거 없는 대비 (근거 2).** "Apollo XXI가 랩톱 기반이었던 반면 이번 앨범은 The Village 스튜디오"라는 문장을 [S3, S4, S5]로 표시했다. 그러나 S4(Wikipedia *Gemini Rights*)에는 인포박스에 스튜디오명만 있고 랩톱 대비 문장은 없다. 출처는 검색 스니펫(seq 13)뿐이다. 랩톱 대비는 전작 비교의 논거로 쓰였기 때문에 결함이 더 무겁다.

**주의(결함 수준 미정):** 근거 8의 "Hot 100 1위(2022-10-03 차트)"는 Wikipedia 문구를 그대로 옮긴 것이다. Billboard 차트는 토요일 날짜로 발행되므로, 10월 3일(월)은 발표일이고 실제 차트 날짜는 10월 8일일 가능성이 높다. 다만 이는 **내 추론이며**, 원 차트 페이지로 확인하지는 못했다.

## 3. 출처가 주장을 실제로 지지하는가 (주요 항목)

| 위치 | 주장 | 판정 |
|---|---|---|
| 근거 1 | "coming into myself after a breakup", "way more hopeful" | GRAMMY 직접 발언, **지지** |
| 근거 1 | Apple 성명의 "easy and fun", "how small we make love" | 추적 seq 21 기준 **지지**. 감정 목록과 무조건적 사랑 부분은 축약됐다 |
| 근거 2 | "about 90%", 이그제큐티브 프로듀서 고려 | Complex 등 2차 보도이며, [재인용] 표기가 **적절** |
| 근거 3 | Fousheé 작곡 크레딧 4/10, "절반" 발언과의 불일치 | 분모를 명시했고 불일치를 공개해 **양호**. Qobuz와도 일치 |
| 근거 4 | Fousheé와 20분 프리스타일로 코러스·벌스 멜로디를 얻음 | Wikipedia는 지지한다. 그러나 Songfacts에 인용된 Guardian 발언은 "Fousheé가 첫 두 줄, 멜로디는 내가"라고 해 **서술이 상충**한다. 노트는 상충을 표시하지 않았다 |
| 근거 5 | 가족 BV가 트랙 2·8·10에 참여, "too much, man" | 크레딧은 지지한다. 다만 원문의 "too much"는 가족 녹음을 **디렉팅한 소감**이다. 노트는 이를 "**뮤직비디오 연출**"로 바꿔 **범위를 왜곡**했다 |
| 근거 5 누락 | GRAMMY 원문의 Mercury 가족 녹음 폐기("a little pitchy… couldn't use it") | **누락**. 근거 5에 바로 필요한 사실이다 |
| 점검표 #7 | 앨범 전반에 대한 "래퍼처럼" 발언을 Cody Freestyle 행에 배치 | 트랙 근거로는 **부적합**하다. 즉흥 후 편집이라는 과정 사실(20분 세션, 편집, B-sides 가능성)은 핵심 근거로 승격되지 못했다 |
| 점검표 #9 | Sunshine이 앨범을 요약한다는 발언 | GRAMMY 직접 발언, **지지** |
| 점검표 #3 | Mercury 프로듀싱 "Lacy+Martians misc.+Dahi misc." | Qobuz 크레딧 필드는 **Producer: Steve Lacy, Dahi**다. **상충을 놓쳤다** |
| 점검표 #10 | Give You the World 작곡 "Lacy, Natche, Ely Rise" | Qobuz에는 **Margaux Alexis Roselena Whitney**가 추가돼 있다. 생성기는 추적 seq 19에서 Deezer 스니펫으로 이 이름을 접했는데도 **반영하지 않았다** |
| 점검표 #8 | Amber 단독 작곡 | Qobuz와 일치, **지지**. 다만 "독특한 위치"는 해석이다 |
| 부록 S2 | "전문 일부만 렌더링" | 추적에는 근거가 없다. 경미함 |

**크레딧·샘플 결론:**
- 크레딧은 사실상 Wikipedia 단일 출처다. 그런데 이를 10/10 "확보"로 집계했다. 판본과 역할을 대조하지 않았으므로, 상태는 "유통 크레딧 대조 미실시"가 정확하다.
- Kendricks "Just Memories" 샘플 주장은 학생 리뷰 스니펫 하나뿐이라는 점을 밝혔고 [미확인]으로 유지했다. 불확실성 처리는 **양호**하다. 다만 리뷰 스니펫을 읽은 것 자체가 "평론을 사실 탐색에 쓰지 않는다"는 지시와 긴장 관계에 있다.
- 참여 비중을 산술로 계산한 곳은 없다.

## 4. 중요 누락, 무관·중복, 해석 과잉

- **누락:**
  - AnOther(Stansfield, 2022-09-20)의 기자 서술: 2년 작업, 300곡 이상에서 10곡을 고른 편집.
  - 같은 기사의 직접 발언: 제목 유래("gay rights" → "Gemini rights"), 곡 작업 전에 제목이 먼저 있었다는 점.
  - 생성기는 "tipsy in a bar"라는 제목 유래를 추적 seq 1과 6에서 이미 봤는데도 본문에 넣지 않았다.
  - GRAMMY 원문의 "only feature" 발언.
  - Sound on Sound: 이번 감사에서는 접근됐다. 내용은 Neal Pogue의 믹스 과정과 보컬을 뒤로 배치하라는 Lacy의 요청이다. 생성기는 시도하지 않았다.
- **무관·저가치:** 근거 8 전체(수상·차트), Helmet 뮤직비디오, 본명(출처 없음), 레이블 이적 관련 GRAMMY 발언 미사용은 괜찮다. 다만 차트 정보가 핵심 근거 8개 중 한 자리를 차지한 것은 선별 실패다.
- **해석 과잉:**
  - 확인 질문 1의 "보사노바 섹션"은 리뷰와 기사가 묘사한 사운드를 들여온 것이다.
  - 근거 4의 "Tyler 조언이 작곡 기여인지" 논의는 불필요한 추측성 확장이다.
  - Apollo XXI 랩톱 대비는 결함 5에서 다뤘다.

## 5. 가장 효과가 큰 수정 3가지

1. **근거 4, 근거 7, 부록 S7·S8: 귀속과 접근 상태를 바로잡는다.**
   - "play on confidence"를 Guardian(D'Souza, Wikipedia 각주 6 경유)으로 정정하고 [재인용]으로 표기한다.
   - Breakfast Club 발언은 S5에서 빼고 [검색 결과 경유·미확인]으로 낮추거나 삭제한다.
   - S8의 "접근 실패"는 "미시도, 스니펫만"으로 고친다.
2. **근거 2와 근거 5를 원문 기준으로 다시 쓴다.**
   - 랩톱/스튜디오 대비 문장은 삭제하거나 [검색 결과 경유]로 표시한다.
   - "too much"는 가족 녹음 디렉팅에 대한 발언으로 정정한다.
   - GRAMMY의 Mercury 가족 녹음 폐기 발언과, 20분 세션 후 편집하는 과정(기자 서술과 직접 발언을 구분)을 추가한다.
   - 근거 8(차트·수상)은 부록으로 내리고, 그 자리에 AnOther의 제목 유래(직접 발언)와 2년·300곡 이상(기자 서술)을 넣는다.
3. **전곡 점검표(#3, #10)와 크레딧 상태를 고친다.**
   - Qobuz 크레딧 필드와 대조해 Mercury의 Dahi 역할 상충(misc. production vs producer)과 Give You the World의 Whitney 작곡 크레딧을 [상충]으로 표시한다.
   - "메타데이터 10/10 확보"는 "Wikipedia 단일 출처, 유통 크레딧은 일부 트랙만 대조"로 바꾼다.

## 6. 평론가 사용 적합성

**잠정 부적합. 수정 후에는 참고 자료로 쓸 수 있다.**

- 핵심 자기 설명과 Fousheé 분모 처리는 쓸 만하다.
- 그러나 게이트 조건에 걸리는 결함이 있다. 존재하지 않는 출처 위치를 댄 인용(근거 7→S5), 오귀속 인용(근거 4), 허위 접근 기록(S8)이다. 따라서 **프로덕션 채택은 권고하지 않는다.**
- 평론가가 근거 4와 근거 7을 그대로 인용하면 지면에 오귀속이 실리게 된다.

## 7. 잠정 선호, 실패 원인 분리, 프롬프트 개정안

- **잠정 선호:** 이 디스패치에는 표본이 하나뿐이라 비교하거나 순위를 매기지 않는다. 단독 판정은 "채택 불가, 수정 시 참고용"이다. 한 앨범, 한 번의 생성이므로 반복 가능성이나 우위에 대한 주장은 할 수 없다.
- **하네스·운영 요인:** WhoSampled 403과 Rolling Stone 402는 하네스 쪽 결과로 정당하게 보고됐다. 다만 Rolling Stone은 Yahoo 신디케이션(추적 seq 17)이라는 대체 경로가 보였는데도 점검하지 않았다. 프롬프트의 "다른 경로 한 차례 점검"을 이행하지 않은 것이다.
- **모델 측 실패:** 귀속 오류, 출처에 없는 내용의 인용 표시, 라벨 오용, 확보한 상충(Deezer의 Whitney)의 누락은 프롬프트가 이미 금지한 사항이다. 따라서 모델 측 실패로 본다.
- **프롬프트가 유발했을 수 있는 실패:**
  - 프롬프트에 수상·차트 같은 반응 정보의 처리 규정이 없다.
  - "원문 확인"이 경유 페이지에서 확인했다는 뜻인지, 발언 원출처를 확인했다는 뜻인지 모호하다.
- **개정안:**
  1. "원문 확인"은 **발언이 처음 실린 매체를 직접 열었을 때만** 쓰도록 한다. Wikipedia나 Songfacts 경유는 반드시 [재인용(경유처·각주번호)]로 적게 한다.
  2. 부록의 접근 상태 칸은 **실제 요청 결과(HTTP 코드 또는 "미시도")만** 적도록 하고, 시도 로그와 일치해야 한다는 자기점검 항목을 추가한다.
  3. 본문에서 크레딧을 쓸 때는 **유통 크레딧(Qobuz/Tidal 등) 1곳 이상과 대조**하고, 이름이나 역할이 다르면 [상충] 행을 의무화한다.
  4. 차트·수상·판매 같은 발매 후 반응은 **부록으로 한정**한다. 단, 평론가가 요청한 경우는 예외로 한다.
  5. 본문 3,000자를 넘기면 그 이유를 1줄로 적게 한다. 이유가 없으면 초과분은 부록으로 옮긴다.
  6. 주장마다 출처 ID와 함께 **위치(문단 첫 단어나 각주 번호)를 필수로** 적게 한다.

Sources:
- [GRAMMY.com — Kevin L. Clark, 2022-07-12](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags/)
- [AnOther — Steve Lacy's Dance With Death](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album)
- [Qobuz — Gemini Rights credits](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/zbylnavz5biaa)
- [Sound on Sound — Inside Track: Bad Habit](https://www.soundonsound.com/techniques/inside-track-steve-lacy-bad-habit)
- [Wikipedia — Gemini Rights](https://en.wikipedia.org/wiki/Gemini_Rights)
- [Wikipedia — Bad Habit (Steve Lacy song)](https://en.wikipedia.org/wiki/Bad_Habit_(Steve_Lacy_song))
- [Songfacts — Bad Habit](https://www.songfacts.com/facts/steve-lacy/bad-habit)
- [The FADER — Bad Habit tops Hot 100 (2022-10-03)](https://www.thefader.com/2022/10/03/steve-lacy-bad-habit-tops-billboard-hot-100)