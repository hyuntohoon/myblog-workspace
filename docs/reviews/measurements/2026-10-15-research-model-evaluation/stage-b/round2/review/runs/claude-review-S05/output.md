# S05 감사 보고서 (Stage B 개발 라운드)

## 1. 감사 분모

- **열람 시도 9건, 확보 6건.** 확보한 곳은 Qobuz(S2), GRAMMY.com(S5), AnOther(S6), INDIE(S4), Apple Music(S1)과 보조 검색 1건이다. GQ 두 페이지(S3, S7)와 archive.org는 내 도구로 열 수 없었다.
- **점검한 주장 17건.**
  - 지원됨 15건
  - 판정 불가 2건: GQ 직접 인용인 C1 "질감" 발언과 V3 S7 발언
  - C5 Bad Habit 전환점 진술은 Okayplayer가 GQ 인터뷰를 재전달한 내용과 일치해 부분 지원으로 보았다.
- **중심 주장 9건으로 판단:** C1–C7, ③ 크레딧 상태, 부록 Producer 전사표.
- **접근 한계:**
  - 음원은 청취하지 않았다.
  - 트레이스상 생산자는 GQ 두 페이지를 열람했다(turn3view1, turn8view2). 나는 열지 못해 C1 인용문(고위험·중심)이 미해결로 남는다. 계약상 이 상태라면 **수용은 보류(deferred)될 수 있다.** 오너나 다른 열람 경로로 확인해야 한다.
  - Genius 원본 행은 입력에도 없다.

## 2. D1–D6

| 차원 | 수준 | 결정 근거 |
|---|---|---|
| D1 대상 고정 | **PASS** | ①에서 Spotify 페이지가 본문을 반환하지 않았다고 밝히고, 크레딧 출처를 "Qobuz 10곡 디지털판"으로 주장 단위에서 표시했다. Qobuz(2022-07-15, 10곡, 34:57, L-M/RCA)와 대조해 일치를 확인했다. 검색에 나온 별도 Apple ID 6788150539는 언급하지 않았지만 중심 주장에는 영향이 없다. |
| D2 정확성 | **PASS** | 확인한 주장은 모두 원문과 맞았다. C3 "음정 때문에"는 원문 "a little pitchy"다. C2의 두 마이크, 약 20분 녹음을 잘라냄, 훅 화음이 후렴이 됨도 S5와 일치한다. C4 "4ever"·큰누나는 S6, C1 2019년 발언은 S4("fresh ear or fresh opinion")와 일치한다. 판정 불가 2건은 따로 집계했다. |
| D3 귀속 | **PASS** | Apple 성명을 "아티스트 명의 성명"으로 구분했다. 원문도 "exclusive artist statement… —Steve Lacy"로 표기돼 있다. 기자의 음향 묘사는 제외한다고 명시했다. C2의 "앨범 후반에 쓴 곡"은 S5 문답에서 Lacy 답변을 요약한 부분이다. 이를 "직접 발언" 묶음에 넣은 것은 경미한 표기 문제다. |
| D4 추적성 | **PASS** (GQ 제외 조건부) | S2·S4·S5·S6은 짧은 번역 발췌만으로 빠르게 찾을 수 있었다. 예: "짧게 잘라냈다" ↔ "chop it up to be shorter". 행 번호는 생산자 도구 기준이라 제3자에게는 쓸모가 적다. GQ 구절은 내가 직접 찾지 못했다. |
| D5 출처 전달 | **PASS** | "원문 확인"이 열람 본문을 읽었다는 뜻임을 부록에서 정의했다. Reddit S8은 "[검색 결과 경유]"로 표시하고 사실로 승격하지 않았다(트레이스상 해당 열람은 Internal Error). Vinyl.com은 "소개문만 원문 확인"으로 적어 과장이 없다. |
| D6 크레딧·판본 | **PASS** | Qobuz 원래 역할 문자열(`Producer`, `Background Vocal`)로 전사했다. Producer 표가 정확하다: 1·2·5·7·8·9 Lacy / 3·4·10 Lacy+Dahi / 6 Matt Martians. Kirby·Ely Rise가 Producer 필드에 없다는 점도 확인했다. Denise Stoudmire가 10번에만 있다는 점도 맞다. G0 집계와의 상충을 해소하지 않고 보류한 것이 적절하다. |
| D7 | **NOT_ASSESSED** | 동결된 top-3 지도가 없다(M4). |

## 3. 무결성 게이트 위반 의혹

**없음.** 이번 감사 범위에서는 게이트 위반을 찾지 못했다. 다만 C1 GQ 인용은 내가 확인하지 못했다. 이는 게이트 의혹이 아니라 판정 불가 상태이며, 위 보류 위험으로 기록한다.

## 4. 파일럿 반복 결함

| # | 결함 | 판정 | 비고 |
|---|---|---|---|
| 1 | 내레이션→직접 발언 승격 | absent | C2 "후반 작업기"는 Lacy 답변을 요약한 것으로, 승격이 아니다. |
| 2 | 검색·요약을 원문 확인으로 표시 | absent | S8은 경유로 표시했다. |
| 3 | 확보한 출처를 덜 읽고 부재 선언 | absent | — |
| 4 | 역할 축소·단일 출처 크레딧 | absent | Qobuz와 G0를 병치했다. |
| 5 | 범위가 다른 진술의 허위 상충, 배타적 진술 미검증 | absent | Producer 필드 상충은 실재한다. |
| 6 | 표·집계 분자 불일치 | absent | 10/10, 6/10(2·3·5·8·9·10)이 서로 맞는다. |
| 7 | 리뷰를 사실 근거로 사용 | absent | Qobuz 평론을 명시적으로 제외했다. |
| 8 | 불필요한 분량·의례적 반복 | absent | 고지 문구가 일부 반복되지만 경미하다. |

## 5. 영향이 큰 수정 3가지

1. **번역 인용의 원문 보존(§4.4).** 특히 GQ의 C1·C5 인용과 S7은 영어 원문 구절을 남겨야 한다. 지금은 비생산자가 접근하지 못하면 중심 인용이 미해결로 남아 수용이 보류된다.
2. **V1 상충 기록을 Producer 밖으로 넓히기.** G0는 Kirby 작곡 6/9로 집계하지만, Qobuz의 Composer 행은 1·5·6번 3곡뿐이다. Qobuz의 "John Kirby"(5·9번)와 "John Carroll Kirby"의 동일인 여부도 미확인이다. 크레딧 상충의 범위가 실제보다 좁게 보고됐다.
3. **C4 제목 다듬기.** Lacy 본인 목소리를 "여자처럼 들리게" 하려던 목표와 가족 보컬의 연속성은 별개 진술이다. 둘을 "여성 목소리의 질감" 하나로 묶은 제목은 해석을 앞서 간다. 행 번호 대신 절 제목이나 영어 앵커를 쓰는 것도 권한다.

## 6. D8–D11 메모와 전체 신뢰도

- **D8 음악적 맥락:** Apollo XXI와의 연속성(S4·S6·S7)이 앨범에 특정되고 근거가 있다. V4의 Badu·Stereolab은 "관심 대상이지 사용 확인 아님"으로 관계 유형을 정확히 제한했다. 결론은 평론가에게 남겼다.
- **D9 선별:** 단위 대부분이 검증이나 탐색에 쓰인다. 미확보 고지가 다소 반복된다.
- **D10 수집 효율:** 트레이스 11단계다. 실패 후 반복이 있다: Genius 열람 Internal Error 4회, Vinyl.com 4회, AnOther 약 6회. 그래도 Qobuz·INDIE·S7을 늦게 확보해 상충 점검에 기여했으므로 경계 수준이다.
- **D11 오너 부담:** 주로 읽기와 가벼운 검증이다. 다만 GQ 인용 원문 확인과 Kirby 역할 상충 정리는 오너 몫으로 남는다.
- **전체 신뢰도:** 중상. 확인한 범위에서 정확성과 출처 표기가 우수하다. GQ 접근 불가가 유일한 큰 불확실성이다.

출처: [Qobuz](https://www.qobuz.com/us-en/album/gemini-rights-steve-lacy/zbylnavz5biaa) · [GRAMMY.com](https://www.grammy.com/news/steve-lacy-new-album-gemini-rights-relationships-and-red-flags/) · [AnOther](https://www.anothermag.com/design-living/14353/steve-lacy-interview-gemini-rights-album) · [INDIE](https://www.indie-mag.com/2019/08/steve-lacy-interview/) · [Apple Music](https://music.apple.com/us/album/gemini-rights/1631909576) · [Okayplayer(GQ 재전달)](https://www.okayplayer.com/music/steve-lacy-thundercat-2023-grammys.html)

```json
{"label": "S05", "D1": "PASS", "D2": "PASS", "D3": "PASS", "D4": "PASS", "D5": "PASS", "D6": "PASS", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "absent", "3": "absent", "4": "absent", "5": "absent", "6": "absent", "7": "absent", "8": "absent"}}
```