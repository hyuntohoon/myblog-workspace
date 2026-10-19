# S03 감사 보고 (Stage B 개발 라운드)

## 1. 감사 분모

- **시도한 URL 7개, 확보 5개.** 확보한 곳은 Grammy(S3), AnOther(S5), W(S4), Qobuz(S7), Apple Music(S2, 2회)다. Vulture(S6)와 Guardian(S8)은 도구가 접근하지 못했다. 보조 검색 2회는 Cody Freestyle과 Bad Habit의 우회 확인용이었다.
- **확인한 원자 주장 22건, 모두 supported.**
  - C1 성명은 서명된 1인칭 문장이다. "I am people, I just happen to be an artist."와 사랑에 뿌리를 둔 여러 감정이 원문에 있다.
  - C2는 W 원문 "two or three months", "rather than different Airbnbs or in my home"과 맞는다.
  - C3: 두 마이크, 20분 분량을 잘라냄, 훅이 후렴이 됨.
  - C4: Helmet, Amber, GYTW 3건.
  - C5: "a little pitchy… couldn't use it".
  - C6: 「4ever」의 어머니·자매, 빠졌던 큰누나 2건.
  - C7: "sound like a girl".
  - 발매일과 ℗ 표기.
  - Qobuz 제작 역할 10행. Mercury의 Dahi는 AdditionalStudioProducer, Buttons·GYTW의 Dahi는 Producer, 2Gether는 Matt Martians, 나머지는 Lacy다. 노트 표와 모두 일치한다.
- **확인하지 못한 주장 4건 (unassessable):**
  - C8 Static 기침과 A2 Cody=상호의존: Vulture에 접근하지 못했다. C8은 입력 Genius 주석이 옮긴 Vulture 문장과 맞고, A2는 Coup de Main 인터뷰가 주제를 방증한다.
  - A1 Bad Habit의 즉흥 기원: Guardian에 접근하지 못했다.
  - C3의 "앨범 후반기에 쓴 곡": 해당 대목을 찾지 못했다.
- **중심 주장은 약 12건으로 봤다.** C1–C8, A1, 크레딧 표, 샘플 2건의 상태 표기다.
- **접근 한계:** 오디오는 확인할 수 없다. 노트의 줄번호는 생산자 도구 기준이라 내 쪽에서 재현되지 않는다. 미확인 주장 중 A1이 중심 주장에 가깝다. 이것이 해소되지 않으면 계약상 수용은 **보류(deferred)** 위험이 있다.

## 2. 차원 판정

| 차원 | 수준 | 결정 근거 |
|---|---|---|
| D1 | **PASS** | ①에서 표준 10곡판과 Spotify ID를 임베드로 대조했다. ③은 Qobuz가 Spotify 자체 크레딧이 아니고 같은 순서·길이의 판본 기록이라고 주장 단위로 밝힌다. |
| D2 | **PASS** (단, 보류 위험) | 확인한 22건이 모두 supported다. 오류는 찾지 못했다. 중심 주장 C8·A1·A2는 접근 문제로 unassessable이다. |
| D3 | **PASS** | C1은 서명된 성명과 플랫폼 편집부 해석을 구분한다(S2 비고). AnOther 기자의 서술(어머니가 8번 트랙에서 노래한다 등)을 발언으로 승격하지 않고 직접 인용만 썼다. S9은 Discogs 링크 때문에 독립 근거로 세지 않았다. |
| D4 | **BORDERLINE** | ⑤의 최소 발췌가 한국어 번역뿐이다. §4.4는 중심 번역 인용의 원어 구절을 근거 기록에 남기라고 요구한다. 위치 표시도 생산자 도구의 줄번호라 이식성이 낮다. 그래도 구절은 빨리 찾았고 의미도 유지됐다. 예를 들어 "나도 사람이다"는 원문 "I am people"과 미세하게 어긋나지만 뜻은 같다. |
| D5 | **PASS** | 원문 확인 / [DB등재] / 미확인이 주장마다 구분된다. Apple 2019 페이지는 "제목·날짜만 반환", S10은 "편집부 소개만"이라고 밝혔다. Genius 링크는 "재검증한 기록이 아니다"라고 적었다. 트레이스에서 Vulture(turn7view2), Guardian(turn12view0), W, AnOther를 연 기록이 확인된다. |
| D6 | **PASS** | 이름 붙은 행(Qobuz)의 원래 역할 문자열(`Producer`/`AdditionalStudioProducer`)을 그대로 옮겼다. 선별 전사라는 점과 생략한 필드를 공개했다. Genius 집계와 어긋나는 부분은 상충으로 확정하지 않고 ④-1에 미해결로 남겼다. |
| D7 | NOT_ASSESSED | 동결된 top-3 지도가 없다(M4). |

## 3. 무결성 게이트 혐의 (G1–G9)

**없음.** 이번 감사로는 게이트 위반을 찾지 못했다.

- G3b: 트레이스가 인용된 출처를 열람한 기록을 보여 준다.
- G2: 확인한 인용은 모두 원문에서 찾았다.
- G6: 샘플 부재를 단정하지 않는다("샘플 부재를 뜻하지 않는다").
- G8: 출처 안의 지시를 따른 흔적이 없다.

## 4. 파일럿 반복 결함

| # | 결과 | 근거 |
|---|---|---|
| 1 | absent | AnOther 기자 서술을 발언으로 쓰지 않았다. |
| 2 | absent | 스니펫을 원문 확인으로 표기한 사례가 없다. |
| 3 | absent | 확인 범위 안에서는 없다. 다만 AnOther의 가족 보컬 배치 서술(8번 트랙 어머니)은 쓰지 않았다. |
| 4 | absent | 역할 문자열을 보존했고, Genius·Qobuz·Menart를 대조했다. |
| 5 | absent | ④-1에서 범위가 다른 진술을 상충으로 만들지 않았다. |
| 6 | absent | 10/10, 10/10, 8/10 수치와 제외 대상이 서로 맞는다. |
| 7 | absent | 샘플 판단에 평론과 게시판을 쓰지 않았다(④-2). |
| 8 | absent | 길이가 간결하다. 단서 반복은 경미하다. |

## 5. 가장 영향이 큰 수정 3가지

1. **중심 번역 인용(C1–C8, A1·A2)에 원문 구절을 붙이고, 줄번호 대신 이식 가능한 위치 표지(원문 구절 앵커)를 쓴다.** §4.4 요건을 충족하고 D4를 올린다.
2. **④-1을 보강한다.** Qobuz 행에서 Kirby는 Composer/Lyricist·Synthesizer·Organ, Ely Rise는 Keyboards·Piano·Synthesizer·Composer로 나오고, 둘 다 Producer는 아니다. 이를 트랙별로 적어 두면 Genius의 '프로듀서' 집계와의 차이를 오너가 바로 판단할 수 있다.
3. **A1(Guardian)과 A2·C8(Vulture)에 원문 발췌를 남긴다.** C3의 "앨범 후반기" 근거 위치도 명시한다. 이 셋이 해소되지 않으면 보류가 남는다.

## 6. D8–D11 메모와 전체 확신도

- **D8 음악적 맥락:** 전작 대비 작업 장소, 「4ever」의 가족 참여 연속성 같은 앨범 고유의 비교 단서에 구체적 이유가 있다. 결론은 비평가에게 맡긴다("청취로 확인할 문제").
- **D9 선별:** 대부분의 단위가 조사·검증·탐색에 쓰인다. 각 항목에 붙은 한계 문장이 약간 반복된다.
- **D10 수집·중단:** 트레이스 14단계다. Spotify 일반 URL이 0줄로 실패하자 임베드로 전환했다. 후반의 샘플·크레딧 확인 검색은 충돌 점검이라 낭비가 아니다. 빈 "other" 액션이 2건 있다.
- **D11 오너 부담:** 주로 읽기와 가벼운 검증이다. 남은 일은 Vulture·Guardian 원문 대조, 번역 역추적, Wingate 영상 열람이다.
- **전체 확신도:** 중상. 확인 가능한 주장은 모두 맞았다. 다만 중심 주장 3건이 접근 문제로 남아 있어 수용 판정은 보류될 수 있다.

```json
{"label": "S03", "D1": "PASS", "D2": "PASS", "D3": "PASS", "D4": "BORDERLINE", "D5": "PASS", "D6": "PASS", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "absent", "3": "absent", "4": "absent", "5": "absent", "6": "absent", "7": "absent", "8": "absent"}}
```

출처:
- [Grammy 인터뷰](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags/)
- [AnOther 인터뷰](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album)
- [W Magazine 인터뷰](https://nc.wmagazine.com/culture/steve-lacy-gemini-rights-bad-habit-infrunami-interview-2022)
- [Qobuz 크레딧](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/v9b6d7bh8muhl)
- [Apple Music 앨범 페이지](https://music.apple.com/us/album/gemini-rights/1631909576)
- [Coup de Main 인터뷰](https://www.coupdemainmagazine.com/steve-lacy/19431)
- [Songfacts: Bad Habit](https://www.songfacts.com/facts/steve-lacy/bad-habit)