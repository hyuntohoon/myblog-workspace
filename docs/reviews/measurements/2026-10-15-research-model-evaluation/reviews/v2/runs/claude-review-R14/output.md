# R14 단독 감사 보고서

## 0. 감사 범위와 접근 한계

- **열어 본 출처: 시도 6건, 확보 6건.** AnOther, GRAMMY.com, Wikipedia 《Gemini Rights》·〈Bad Habit〉, Qobuz(크레딧 필드만 사용), Apple Music. 웹 검색은 1회 했습니다(Billboard 1위 날짜 확인).
- **열지 않은 출처:**
  - 《W》 원문, Billboard 원문, Sound on Sound: 열지 않았습니다. Sound on Sound는 앵커에 기록된 403 이력이 있습니다. 이번 감사에서 재시도하지 않았으므로 지금도 접근할 수 없는지는 모릅니다.
  - Wikipedia 〈Bad Habit〉 페이지: 105,660자 중 끝부분 5,660자는 읽지 않았습니다.
- **도구 한계:** 모든 페이지는 WebFetch 요약 모델을 거쳐 받았습니다. 그래서 "원문 그대로 대조"가 아니라 요약기가 옮긴 발췌와 대조한 것입니다. 이 한계는 생성기에도 똑같이 적용됩니다.
- **원자 주장 점검: 22건.** 지지 14건, 부분 지지·범위 오류 4건, 틀림 2건, 확인 불가 2건. 노트에 있는 모든 원자 주장을 전수 조사한 것은 아니므로 정밀도 분모로 쓰면 안 됩니다.
- **기계적 지표**
  - 분량: 본문(①~④)은 약 5,500자, 부록은 약 1,800자로 추정합니다. 프롬프트의 1,800~3,000자 목표를 넘겼지만 초과 사유는 적혀 있지 않습니다.
  - 출처: 명시된 URL은 5개이고 도메인은 3개(anothermag, grammy, wikipedia)입니다. S6은 URL이 없습니다.
  - 전곡 점검표: 10/10 트랙이 있습니다.

## 1. 차원별 점수

| 차원 | 0–5 | 환산 | 근거 |
|---|---:|---:|---|
| 사실 정확성·귀속 | 3 | 15/25 | 인용 대부분은 원문에서 확인됩니다. 다만 아래 결함 2건이 있습니다. ① 서두의 "Wikipedia에 한국어 지시문이 삽입됨"은 틀렸습니다. ② C3에서 기자 서술을 직접 발언으로 표기했습니다. 그 밖에 2Gether 프로듀서 오기, 차트 날짜 범위 오류가 있습니다. |
| 중요 근거·누락 | 2.5 | 10/20 | Apple Music의 아티스트 명의 성명, 제목 유래 직접 발언(생성기 자신의 trace에도 나옴), GRAMMY의 편집 과정 발언, Qobuz 크레딧, Sound on Sound 시도가 모두 빠졌습니다. |
| 출처 추적·지지 | 3 | 12/20 | 출처 ID, URL, 최소 발췌는 갖췄습니다. 그러나 요약기 출력을 "원문 확인"으로 올렸고, S6은 URL이 없는 "검색 결과 집계"입니다. 같은 출처(S1)에 정반대 성격의 라벨이 붙은 곳도 있습니다. |
| 크레딧·샘플·불확실성 | 2.5 | 5/10 | 참여 비중 계산은 없고, 샘플 미확인도 과장하지 않았습니다. 하지만 접근 가능했던 Wikipedia Personnel 구획을 쓰지 않고 프로듀서를 "(추정)"으로 채웠습니다. Lacy를 2Gether 프로듀서로 잘못 넣었습니다. |
| 관련성·밀도 | 3.5 | 7/10 | C8(차트 궤적)이 깁니다. 부록에는 Metacritic 80이 들어가 있어 "타 평자 점수 반입 금지" 규칙과 부딪힙니다. 인젝션 서두는 본문 정보로서 가치가 낮습니다. |
| 음악적 맥락(비평 비대체) | 3.5 | 7/10 | 청취했다고 꾸민 표현이나 판정은 없습니다. 비교 후보는 0개입니다. 그 자체는 허용되지만, 전작 비교 근거는 얇습니다. |
| 평론가 사용성 | 3.5 | 3.5/5 | 전곡 점검표, 메타데이터와 실질 근거의 분리, 실행 가능한 Q1~Q3가 있습니다. |
| **합계** | | **59.5/100** | |

**신뢰도:** 중간. 핵심 인용은 직접 대조했지만 요약기를 거쳤고, 《W》와 Billboard는 원문을 보지 않았습니다.

## 2. 심각 결함 (총점과 별도)

1. **서두의 출처 내용 허위 보고 (출처 이력 결함)**
   - "Wikipedia 본문에 한국어 지시문이 삽입됐다"고 보고했습니다.
   - 실제 Wikipedia 페이지에는 한국어 내용도, 지시문도 없습니다(제가 직접 확인). Trace seq 3을 보면, 요약기가 생성기 자신의 한국어 fetch 프롬프트를 페이지 내용으로 잘못 보고했습니다. 생성기는 이를 검증하지 않고 사실로 전달했습니다.
   - 음악 주장은 아니지만, 출처에 관한 허위 진술입니다.
2. **C3의 귀속 오류**
   - 표제 "홈 레코딩 중심에서 풀 스튜디오(The Village)로"와 "전작은 랩톱 중심 홈 레코딩"을 [직접 발언·원문 확인]으로 표기했습니다.
   - AnOther에서 홈 레코딩은 **기자 서술**이고 내용도 "iPhone으로 녹음한 DIY 데모"입니다. 기사에는 랩톱도 The Village도 나오지 않습니다.
   - 생성기 자신의 fetch 결과(seq 4)에도 "기자 서술이며 Lacy의 직접 발언이 아님"이라는 경고가 있었는데 무시했습니다.
   - "랩톱"은 검색 요약(seq 1)에서만 나옵니다. 한 주장 안에 검증 수준이 서로 다른 내용을 묶어서, 프롬프트 4-B를 위반했습니다.

## 3. 주장별 검증 요약

| 위치 | 판정 | 근거 |
|---|---|---|
| C1 "a fucking break-up album" | 지지 | AnOther 직접 인용 |
| C1 회복·"더 희망적" | 지지 | GRAMMY: "me coming into myself after a breakup", "way more hopeful" |
| C1 "두 매체에서 교차 확인" | **범위 오류** | 두 출처는 서로 다른 발언입니다. 같은 사실을 독립적으로 교차 확인한 것이 아닙니다. |
| C2 "first time I consciously said I was an artist" | 지지 | AnOther. 다만 원문 뒤에 이어지는 "I thought I was just a guitar player"가 빠져서, 스스로를 어떻게 규정했는지의 맥락이 줄었습니다. |
| C3 gym/trash/bullshit | 지지 | AnOther 직접 인용 |
| C3 홈 레코딩·랩톱·The Village | **오귀속** | 위 심각 결함 2 참고 |
| C3/Q1 300곡→10곡 [미확인] | 부분 | AnOther 기자 서술에 명시돼 있어 "기자 서술·원문 확인"으로 확정할 수 있었습니다. 다만 Lacy의 발언으로 승격하지 않은 판단은 적절합니다. |
| C4 Fousheé "only feature" | 지지(발언 범위) | GRAMMY 직접 인용. 그러나 점검표 6번(Matt Martians 피처)과 부딪히는데 상충 표시가 없습니다. |
| C5 Bad Habit 제작 경로 | 부분 | "보도 각주가 다수 달려 있다"고 했지만, 20분 프리스타일과 1년 수정 문장은 Wikipedia에 각주가 없습니다. "RCA 제출 1주 전"만 [6] 각주가 있습니다. |
| C6 가족 보컬(Helmet/Amber/GYTW), Mercury 미사용 | 지지 | GRAMMY: "a little pitchy… couldn't use it" |
| C6 "4ever" = 《Apollo XXI》 | **추론 미표시** | AnOther는 "my last album"이라고만 말합니다. 앨범명 연결은 생성기의 추론입니다. |
| C7 Sunshine "anger and animosity" | 지지 | GRAMMY |
| C7 Mercury 라이브 "위험했지만 자연스러웠다" | 지지 | GRAMMY: "a risk that I took" |
| C7 Static(《W》) | 재인용 표시 적절 | 《W》 원문은 미확인 |
| C8 Hot 100 100위 진입, 9/10 장르 차트 | Wikipedia와 일치 | 독립 확인은 하지 않음 |
| C8 "2022-10-03자 Hot 100 1위" | **날짜 범위 오류 가능** | Wikipedia 문구를 그대로 옮겼습니다. 10/3은 보도·발표일(The Fader 2022-10-03)이고, 차트 날짜는 별도로 확인해야 합니다. |
| C8 그래미 Best Progressive R&B Album | 지지 | Wikipedia |
| 점검표 6 2Gether 프로듀서 "Lacy, Matt Martians" | **틀림** | Wikipedia Personnel: Lacy는 1–5, 7–10만 프로듀싱했고 6번은 Matt Martians입니다. Qobuz도 Matt Martians만 표기합니다. |
| 점검표 "(추정)" 프로듀서 | 방법 결함 | Wikipedia Personnel에 이미 있습니다. Helmet/Cody/Amber/Sunshine은 Lacy, Buttons/GYTW는 DJ Dahi 공동, Mercury는 Dahi·Martians misc.입니다. 확인할 수 있었던 값을 추정으로 남겼습니다. |
| 점검표 9 Riggins 역할 미확인 | 누락 | Wikipedia와 Qobuz 모두 drums(9)를 명시합니다. |
| 점검표 10 GYTW 작가 | 상충 미발견 | Qobuz에는 Margaux Alexis Roselena Whitney가 추가돼 있고, Wikipedia에는 없습니다. |
| 판본 "RCA Records" | 부분 | Apple 메타데이터: "L-M Records, under license to RCA" |

## 4. 중요 누락 / 불필요 자료 / 해석 과잉

- **누락**
  - Apple Music의 Lacy 서명 성명("how small we make love")
  - AnOther의 제목 유래 직접 발언("I kept saying it as a joke", 곡보다 제목이 먼저였음). seq 1과 seq 4에 있었는데도 빠졌습니다.
  - GRAMMY의 "edit, edit, edit" / "superpower of editing", 즉흥 연주 뒤 편집하는 과정
  - Qobuz 등 유통 크레딧과의 대조, Sound on Sound 접근 시도
- **불필요하거나 중복된 자료**
  - C8 차트 세부(Bad Habit 단일 곡 상업 궤적 비중이 큼)
  - S3의 Metacritic 80, C5와 C8의 Bad Habit 내용 중복
  - 서두 인젝션 보고(그나마 오보)
- **해석 과잉**
  - C1 표제 "자기 회복의 서사"를 자료 유형 라벨 없이 서사 프레임으로 제시했습니다. 경미합니다.
  - C5 "관련성"이 상업적 성공과 작법을 인과적으로 연결하는 듯 서술했습니다. 출처에 없는 연결입니다.

## 5. 크레딧·샘플 결론과 불확실성 처리

- **잘한 점**
  - 참여 곡 수로 지분이나 비중을 계산하지 않았습니다.
  - 샘플이 미등재라는 사실을 "샘플 없음"으로 해석하지 않았습니다("명시 자료 미확인").
  - DB 등재와 공식 크레딧을 구분하겠다고 명시했습니다.
- **문제점**
  - 접근 가능했던 역할 필드(Personnel)를 쓰지 않고 "(추정)"으로 채웠습니다. 2Gether는 실제로 틀렸습니다.
  - "only feature" 발언과 2Gether의 "with Matt Martians" 표기가 부딪히는데 표시하지 않았습니다.
  - S6은 URL이 없어 추적할 수 없습니다.

## 6. 우선순위 수정 3가지

1. **서두를 삭제하거나 정정합니다.** Wikipedia 인젝션 주장은 seq 3 요약기의 오보입니다. 원문 텍스트로 확인되지 않은 "삽입 지시"는 보고하지 않거나, "도구가 그렇게 보고했으나 미확인"으로 범위를 좁힙니다.
2. **C3를 분리하고 라벨을 다시 붙입니다.** iPhone DIY 데모는 [보도·기자 서술], gym/trash는 [직접 발언], The Village는 [DB등재]로 나눕니다. "랩톱"은 삭제합니다. 300곡/2년은 AnOther 기자 서술로 확정합니다.
3. **점검표 크레딧을 Wikipedia Personnel과 Qobuz 역할 필드로 다시 작성합니다.** "(추정)"을 없애고 2Gether 프로듀서를 정정합니다. Riggins drums와 Ely Rise keyboards/piano를 넣습니다. GYTW 작가 상충(Whitney)과 "only feature" 상충을 표시합니다. 이와 함께 Apple 성명과 제목 유래 발언을 핵심 근거에 추가합니다.

## 7. 평론가용 적합성 (잠정)

**조건부 사용 가능, 운영 채택은 권고하지 않습니다.**

- 쓸 만한 부분: GRAMMY와 AnOther의 직접 인용(C1, C2, C6, C7)은 대체로 정확합니다. 범위 표시도 대체로 성실합니다.
- 채택 불가 사유:
  - 출처에 관한 허위 진술(서두)
  - 핵심 근거 C3의 직접 발언 오귀속
  - 접근 가능했던 크레딧을 추정으로 채운 점
- 이 세 가지는 루브릭 게이트 중 "central unsupported verified assertion"에 근접합니다.

## 8. 비교·프롬프트 관련

- **잠정 선호:** 이 디스패치에는 표본이 1개뿐이므로 순위나 우열을 판단하지 않습니다. 이번 1회 생성으로는 반복성도 일반적 우월성도 주장할 수 없습니다.
- **프롬프트 유발 실패 vs 모델/하네스 실패**
  - 하네스 요인: 요약기 매개 fetch가 자기 프롬프트를 페이지 내용으로 오인했습니다. 검색 결과 말미의 "REMINDER" 문구도 하네스 쪽 요인입니다.
  - 모델 요인: 요약기가 준 "기자 서술" 경고를 무시했고, Personnel 구획을 다시 요청하지 않았습니다. 제목 유래가 이미 확보돼 있었는데도 누락했습니다.
  - 프롬프트 요인: 아티스트 성명 출처로 Apple과 Spotify를 구체적으로 지목하지 않았습니다. 요약 도구의 출력을 어느 검증 단계로 다룰지도 규정하지 않았습니다.
- **프롬프트 개정 제안**
  1. 요약 도구를 거친 fetch 결과는 "[원문 확인(요약 경유)]"로 표기합니다. 직접 인용은 요약기가 원문을 그대로 옮겼다고 밝힌 문장만 인정합니다.
  2. 인젝션이나 이상 내용을 보고할 때는 해당 원문 텍스트를 발췌해야 합니다. 도구가 그렇게 말했다는 이유만으로는 보고하지 않습니다.
  3. 크레딧 칸을 "(추정)"으로 채우지 않습니다. 같은 출처의 역할 구획(Personnel 등)을 한 번 더 요청한 뒤에도 없으면 "미확인"으로 둡니다.
  4. 차트 성과는 "차트 날짜"와 "발표·보도일"을 구분해 적습니다.
  5. 확보한 인터뷰에서 제목 유래와 편집·폐기 과정 발언을 추출했는지 체크리스트로 점검합니다.

Sources:
- [AnOther – Steve Lacy's Dance With Death](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album)
- [GRAMMY.com – On 'Gemini Rights' Steve Lacy Gets Personal](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags/)
- [Wikipedia – Gemini Rights](https://en.wikipedia.org/wiki/Gemini_Rights)
- [Wikipedia – Bad Habit (Steve Lacy song)](https://en.wikipedia.org/wiki/Bad_Habit_(Steve_Lacy_song))
- [Qobuz – Gemini Rights](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/zbylnavz5biaa)
- [Apple Music – Gemini Rights](https://music.apple.com/us/album/gemini-rights/1631909576)
- [The Fader – "Bad Habit" tops Billboard Hot 100 (2022-10-03)](https://www.thefader.com/2022/10/03/steve-lacy-bad-habit-tops-billboard-hot-100)