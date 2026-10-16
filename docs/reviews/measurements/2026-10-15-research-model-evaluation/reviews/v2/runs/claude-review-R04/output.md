# R04 개별 감사 보고서

## 0. 감사 범위와 분모

- **열어 본 URL: 10개 시도, 8개 확보.**
  - 확보: GRAMMY.com, AnOther, Apple Music 앨범 페이지, W, Shazam(2Gether), Shazam(Mercury), Qobuz(us-en/v9b6d7bh8muhl), vinyl.com
  - 실패: GQ(내 fetch 도구가 차단됨), MusicBrainz(브라우저 확인 화면만 반환됨)
  - GQ는 웹 검색 1회로 보조 확인을 시도했지만 해당 문장을 찾지 못했다.
- **열지 않은 곳:** Spotify embed, Sony LP 상품 페이지, Discogs, Apple 2019 post, Sound on Sound. 곡순과 재생 시간은 독립적으로 재확인하지 않았다.
- **원자 주장 검증: 26개 중 확인 21, 경미한 범위 이탈·부정확 3, 검증 불가 2(GQ 발언, "Apple 검색 결과의 C418 표기").**
- **도구 한계:** 페이지 요약은 소형 모델을 거쳐 나온다. Qobuz와 Shazam의 개별 역할 행은 2차 요약을 읽은 결과다. 이 수치를 정밀도 지표로 일반화하지 말아야 한다.
- **trace에 대해:** 생성기가 GRAMMY, AnOther, W, GQ, Shazam, Qobuz, vinyl.com, Apple 2019 post를 실제로 열었다는 기록이 있다. Sound on Sound를 시도한 흔적은 없다.

## 1. 기계적 감사

| 항목 | 관찰 |
|---|---|
| 분량 | 본문 ①~④ 약 2,600~3,000자(추정, URL 제외), 부록 약 2,500자 |
| 명시 URL / 도메인 | 14개 / 12개 도메인 |
| 1차 자료 대 재인용 | 핵심 근거 C1~C6은 모두 당사자 직접 발언. 재인용 기사는 쓰지 않음 |
| 전곡 점검 | 10/10곡이 표에 있음. 실질 근거 분자는 **틀림**(아래 결함 D1) |
| 중복 | 적음. C4의 가족 보컬이 표와 부록에서 반복되지만 역할이 다름 |
| 상태 라벨 | 프롬프트가 정한 체계를 대체로 정확히 사용함. C7에 붙은 "[유통 크레딧·원문 확인]"은 "원문이 그렇게 표기한다"는 뜻으로만 유효함 |
| 분모 공개 | 10/10, 10/10, 6/10을 제시. 마지막 값이 표와 불일치 |

## 2. 주장별 출처 대조

| 위치 | 판정 | 근거 |
|---|---|---|
| ① 발매일 2022-07-15, 10곡 | ✅ | Apple: "July 15, 2022, 10 songs, 35 minutes", ℗ L-M Records/RCA |
| C1 스튜디오 대 집·Airbnb, "스튜디오를 집으로" | ✅ | W(Maxine Wally, 2022-10-20, 2024-02-20 갱신): "I made this one in the studio, rather than different Airbnbs or in my home… I made the studio a home". 발매 후 회고라는 표시도 정확함 |
| C2 Bad Habit이 작사 방향을 열었다, 협업 질감 | ⚠️ 검증 불가 | 내 도구로는 GQ를 열 수 없었다. trace상 생성기는 GQ를 열었다(181행). Nylon의 GQ 재인용("start of this renaissance")은 큰 방향과는 맞지만 문장 자체를 확인해 주지는 않는다 |
| C3 Sunshine: 후반에 씀, 마이크 두 대, 약 20분 즉흥 후 편집, 훅이 후렴이 됨 | ✅ | GRAMMY: "one of the last songs written", "two mics", "about 20 minutes long and [then] we'd chop it up", "It became the chorus" |
| C3 부록: "유일한 피처링"을 전체 참여자 수와 구분 | ✅ 우수 | 루브릭 기준점 3이 요구한 범위 처리와 일치함(Matt Martians 표기 병기) |
| C4 Helmet/Amber/GYTW 가족 보컬, Mercury는 음정 문제로 폐기, 어머니와 두 자매 | ✅ | GRAMMY: "they were a little pitchy… couldn't use it", "my mother and two sisters" |
| C4 전작 「4ever」에 가족 참여 | ✅(경미한 추론) | AnOther 원문은 "last album, on the track 4ever"라고만 말한다. 이를 Apollo XXI로 특정한 것은 생성기의 연결이다. 사실관계는 정확하지만 표시가 없다 |
| C4 부록: Qobuz 배경 보컬 4명 | ⚠️ 부분 누락 | Qobuz의 GYTW 행에는 **Denise Stoudmire**도 있다. 세 곡을 한 명단으로 묶으면서 한 명이 빠졌다 |
| C5 제목 유래(뉴욕 술집, gay rights → Gemini rights), 곡보다 먼저 정함, 별자리 일반화에 거리 둠 | ✅ | AnOther: "I had the name before I even had the songs written", "I don't like to generalise too much" |
| C6 Apple 성명이 Lacy 명의이며 사랑을 더 크게 하겠다고 말함 | ✅ | "I will make love bigger, not smaller". 작성 주체 구분이 정확함. 다만 **청자와 아티스트의 분리를 거부하는 진술**("I am not separate…")은 빠졌다 |
| C7 Shazam의 C418 '샘플된 아티스트' 표기, Qobuz에는 없음 | ✅ | Shazam에서 "음원으로 샘플링된 아티스트" 표기를 확인했고, Qobuz 2Gether 행에는 C418이 없음 |
| C7 "Apple 검색 결과에도 같은 표기" | ⚠️ 검증 불가 | trace의 Apple 2Gether 스니펫에는 Karl Wingate만 보인다. 다만 trace는 완전한 기록이 아니다 |
| V1 Mercury: Shazam에 Luke Titus Sangerman·Ravyn Lenae Washington 추가 표기, Qobuz에는 없음 | ✅ | 확인함. 단, Qobuz Mercury 행에 있는 **John Carroll Kirby**가 Shazam에는 없다는 반대 방향 차이는 놓쳤다 |
| V2 GYTW: Qobuz의 Margaux Whitney 작곡·작사 | ✅ / MusicBrainz 쪽은 확인 불가 | Qobuz 행은 확인함. MusicBrainz는 봇 차단으로 열지 못함 |
| V3 Dahi: Buttons·GYTW 프로듀서, Mercury 추가 스튜디오 프로듀서 | ✅ | Qobuz와 일치. Shazam은 Mercury에서 "DJ Dahi"를 그냥 프로듀서로 적는데, 이 역할 차이는 기록하지 않았다 |
| ④-3과 S12: Wingate 페이지는 소개문뿐이고 영상과 타임코드는 미확보 | ✅ | vinyl.com은 날짜가 없고 직접 인용도 없다. GYTW가 최애 곡이라는 것은 편집부의 요약이다. 접근 상태를 정직하게 처리했다 |
| 표 Static: "이별 후 쓴 곡" | ⚠️ 범위 이탈 | W의 원문은 "about going through a breakup". 곡의 주제를 작성 시점으로 바꿔 놓았다 |

## 3. 차원별 점수

| 차원 | 가중치 | 점수(0~5) | 환산 | 근거 |
|---|---:|---:|---:|---|
| 사실 정확성·귀속 | 25 | 4.0 | 20 | 직접 발언 귀속이 정확하고, 반대로 뒤집힌 주장이나 조작된 주장이 없다. 감점: 6/10 분자 오류, Static 시점 이탈, 배경 보컬 1명 누락, 검증 불가 진술 1개 |
| 핵심 근거·누락 | 20 | 3.5 | 14 | 기준점 1·2·3·4를 모두 다뤘다. 누락: AnOther의 "2년, 300곡 이상에서 10곡으로 편집"(기자 서술)과 GRAMMY의 "edit, edit, edit" 편집론이 본문에서 빠지고 부록 위치 표기로만 남았다. Sound on Sound 시도 기록이 없고, Apple 성명의 청자·아티스트 진술도 빠졌다 |
| 출처 추적성 | 20 | 4.0 | 16 | 주장 ID, 출처 ID, 위치, 발췌가 연결된다. 약점: "행 번호"는 생성기 도구 뷰에서만 유효해서 사람이 재현할 수 없다. Qobuz 상품 ID가 기준점(zbylnavz5biaa)과 다른데(v9b6d7bh8muhl) 판본(explicit/clean 여부)을 밝히지 않았다 |
| 크레딧·샘플·불확실성 | 10 | 4.5 | 9 | DB 등재와 권리 처리 확정을 구분했고, 미등재를 샘플 부재로 읽지 않았다. Apple과 Shazam을 독립 근거로 세지 않았고, 참여 곡 수로 작업량을 계산하지 않았다. 반대 방향 상충 2건을 놓친 것은 경미함 |
| 관련성·밀도 | 10 | 4.5 | 9 | 전기, 게임, 장르 이야기로 빠지지 않았다. Mellohi는 지목 사실만 기록하고 멈췄다 |
| 음악 맥락 | 10 | 4.0 | 8 | 청취 주장이나 발명된 의도가 없다. 전작 비교는 작업 장소와 가족 협업 두 축으로 근거가 있다. 비교 후보는 제시하지 않았고(선택 사항), 제작 방법 자료(SoS 등)가 얇다 |
| 평론가 활용성 | 5 | 4.0 | 4 | 우선순위, 미해결 3건, 접근 제한 기록이 명확하다. 분모 오류 때문에 점검표의 신뢰가 떨어진다 |
| **합계** | | | **80/100** | |

- **신뢰도: 중간.** 핵심 C1·C3·C4·C5·C6은 원문으로 확인했다. C2(GQ)와 MusicBrainz 대조는 확인하지 못했다.
- **중대 결함(채택 게이트 해당): 없음.** 발명된 출처나 인용, 거짓 청취·직접 접근 주장, 중심 주장의 무근거 확정, 미해결 집계를 논지로 쓴 사례를 발견하지 못했다.

### 비게이트 결함
- **D1.** ③ 첫 문단에서 "직접 발언 6/10곡"이라고 썼지만, 표에서 근거가 있는 곡은 Static, Helmet, Mercury, Bad Habit, Amber, Sunshine, GYTW로 **7곡**이다. 표에서 셈하지 않은 분자다.
- **D2.** 표의 Static 행이 "곡의 주제"를 "작성 시점"으로 바꿨다.
- **D3.** 부록 C4의 배경 보컬 명단이 불완전하다(GYTW의 Denise Stoudmire).

## 4. 크레딧·샘플 결론과 불확실성 처리

- C418 관계는 "Shazam 표기 있음 / Qobuz 표기 없음 / 원곡·구간·권리 미확인"으로 범위를 정확히 잡았다. Mellohi를 확정하지 않았고, Minecraft 쪽 해석으로 확장하지도 않았다. 루브릭 의도에 부합한다.
- Mercury와 GYTW의 저자 명단 상충을 드러내고 판단을 보류한 것은 적절하다. 다만 상충 기록은 양방향 모두 남겨야 한다(Qobuz의 Kirby, Shazam의 Dahi 역할).
- "현재 유통 크레딧 ≠ 발매 당시 표기"라는 전제를 명시한 점은 좋다. 실물 부클릿 대조가 미완이라는 상태도 정직하게 남겼다.

## 5. 가장 효과가 큰 수정 3가지

1. **③ 분모 수정 (근거: 표 자체).** 6/10을 7/10으로 고치거나, Static을 제외한 기준을 명시해야 한다. 표에서 분자를 자동으로 세게 해야 한다.
2. **② 본문에 편집 규모 사실을 추가하고 귀속을 분리 (근거: AnOther "two years' work and a ten-track edit of more than 300 songs" [기자 서술], GRAMMY "edit, edit, edit" [직접 발언]).** 현재 C3의 Sunshine 편집 사례와 묶이는 앨범 단위의 제작 사실이 빠져 있다. 기자 서술과 직접 발언을 다른 주장 ID로 두어야 한다.
3. **⑤ 위치 표기를 재현 가능하게 바꾸고 판본을 고정 (근거: S4~S12의 "행 번호", Qobuz 상품 ID 불일치).** 도구 뷰의 행 번호 대신 문단 첫 구절을 앵커로 쓰고, Qobuz 상품 ID와 explicit/clean 구분을 적어야 한다. Sound on Sound(Bad Habit Inside Track)도 한 번 시도하고 결과를 남겨야 한다.

## 6. 평론가 사용 적합성 (잠정)

**조건부 적합.** 핵심 근거는 원문과 일치하고, 직접 발언과 편집부 서술, DB 등재가 구분되어 있다. 청취나 평가를 대신하지도 않는다. 그대로 넘기기 전에 위 수정 1·2를 반영하고, C2를 GQ 원문으로 재확인하는 것을 권한다. 이번 결과는 한 앨범, 한 번의 생성에 대한 관찰이다. 안정적인 품질이나 생산 채택 적합성을 입증하지 않는다.

## 7. 비교·실패 원인·프롬프트 개정안

**잠정 비교:** 이번 배정에는 표본이 하나뿐이라 순위를 매기지 않는다. 다른 표본과의 비교는 같은 루브릭으로 따로 감사한 뒤에만 의미가 있다.

**실패 원인 구분:**
- **모델·실행 쪽:** D1 분자 오류, Denise Stoudmire 누락, 상충의 한 방향만 기록, SoS 미시도.
- **프롬프트가 유도한 쪽:** 프롬프트는 "문단·페이지·타임코드"를 요구하지만 재현 가능성을 정의하지 않아 도구 행 번호를 쓰게 됐다. 또 "본문 핵심 근거 최대 8개" 상한이 기자 서술형 규모 사실을 본문에서 밀어냈을 가능성이 있다(추정).
- **하네스 쪽:** GQ와 MusicBrainz 접근은 내 쪽 도구의 제약이다. 생성기의 결함으로 집계하지 않았다.

**프롬프트 개정안:**
1. §4A에 추가: "위치는 사람이 재현할 수 있는 앵커(문단 첫 구절, 소제목)로 적고, 도구가 매긴 행 번호는 보조로만 쓴다."
2. §9에 추가: "확보율의 분자는 점검표의 행에서 직접 세고, 포함과 제외 기준을 한 줄로 적는다."
3. §6에 추가: "유통 크레딧 페이지는 서비스 상품 ID와 explicit/clean 판본을 기록한다. 상충은 출처 A에만 있는 것과 출처 B에만 있는 것을 모두 적는다."
4. §3에 추가: "엔지니어나 기술 매체의 제작 기사가 존재한다고 알려졌으면, 접근 시도와 결과를 접근 제한 기록에 남긴다."
5. §3에 추가: "기자 서술로만 확인되는 제작 규모(기간, 곡 수, 선별 비율)도 앨범 이해를 바꾸면 본문에 [보도] 상태로 둘 수 있다."

Sources:
- [GRAMMY.com — Kevin L. Clark](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags/)
- [AnOther — Ted Stansfield](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album)
- [Apple Music — Gemini Rights](https://music.apple.com/us/album/gemini-rights/1631909576)
- [W Magazine — Maxine Wally](https://www.wmagazine.com/culture/steve-lacy-gemini-rights-bad-habit-infrunami-interview-2022)
- [Shazam — 2Gether (Enterlude)](https://www.shazam.com/song/1631909585/2gether-enterlude)
- [Shazam — Mercury](https://www.shazam.com/song/1631909581/mercury)
- [Qobuz — Gemini Rights (us-en)](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/v9b6d7bh8muhl)
- [vinyl.com — Karl Wingate](https://vinyl.com/blogs/featured/karl-wingate-on-steve-lacys-gemini-rights)
- [Nylon — Bad Habit (GQ 재인용 보조)](https://www.nylon.com/entertainment/steve-lacy-bad-habit-tiktok-trend)