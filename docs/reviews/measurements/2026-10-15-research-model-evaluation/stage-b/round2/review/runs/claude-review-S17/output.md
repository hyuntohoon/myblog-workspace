# S17 감사 보고서 (Steve Lacy, *Gemini Rights*)

## 1. 감사 분모

- **시도한 URL 5건, 모두 확보:** Wikipedia *Gemini Rights*, Wikipedia *Bad Habit*, Grammy.com, W Magazine, Sound On Sound.
- **접근 한계:**
  - 다섯 건 모두 WebFetch가 처리한 요약이다. 감사자 쪽에서도 원문을 그대로 대조하지 못했다.
  - Guardian, Billboard, GQ, Rolling Stone, Genius 원문은 열지 않았다. 생산자 trace에서 차단되거나 402를 받은 곳들이다.
  - Apple Music 성명 원문과 공식 크레딧 행(Apple, Tidal)은 확인하지 않았다.
  - 오디오 관련 주장은 들어서 확인할 수 없다.
- **점검한 원자 주장 약 24건:** 판본과 메타데이터 4, 직접 인용 9, Bad Habit 경과 6, 크레딧 행 5. 나머지는 trace와만 대조했다.
- **중심 주장 10건:** ① 판본, C1~C8, 그리고 ③의 샘플 상태.
- **판정:** supported 19 / imprecise 3 / unsupported 1 / unassessable 1.
  - unassessable 1건은 C6 원 출처의 화자 구분이다. Guardian, Billboard, GQ 원문을 열 수 없었다.

## 2. D1–D6

| 차원 | 수준 | 결정적 근거 |
|---|---|---|
| **D1** | **PASS** | ①은 Spotify ID와 Apple의 ℗ 줄(trace seq7)로 대상을 고정했다. 10곡, 34:57은 Wikipedia와 일치한다. Spotify 페이지를 열지 않았다는 점과 Sped Up 판을 뺀 이유도 주장 단위로 밝혔다. |
| **D2** | **BORDERLINE** | 인용은 모두 원문 요약과 일치한다(C1, C2, C3, C5. Grammy와 W에서 재확인). 오류는 세 가지다. (a) C7과 ④의 청취 질문은 Pogue의 지시를 "Bad Habit에 대한 것"으로 좁혔다. SOS에서는 "his songs"와 "When I mix an entire album, as with Gemini Rights…"로 앨범 전반의 이야기다. (b) S5와 C8은 "Wikipedia(라이너 노트 인용)"라고 했지만, 앨범 문서의 Personnel 절에는 그런 표기가 없다. 그런 표기가 있는 것은 Bad Habit 문서다. (c) ③의 커버리지 분자가 표와 맞지 않는다(아래 6번 결함). (a)를 incorrect로 판정하면 G4 후보가 된다. |
| **D3** | **BORDERLINE** | 세 군데는 화자를 잘 구분했다. SOS의 "기자 서술"과 Pogue 발언, Apple의 "—Steve Lacy" 서명 성명, Complex가 Zane Lowe를 재인용했다는 점이다. 문제는 C6이다. 전체에 [직접 발언·재인용] 표지를 붙였지만, Wikipedia에서 이 항목들은 모두 문서 자체의 서술이다. 드럼 재활용과 즉흥 대목에는 각주도 없다. 원 기사의 화자 구분은 노트에서 복구할 수 없다. |
| **D4** | **BORDERLINE** | Grammy와 W 구절은 바로 찾아진다. SOS도 "Into The Groove" 절 표시 덕분에 빨리 찾았다. 다만 C7의 '한계' 줄이 범위를 바꿔 놓아서 충실도가 불완전하다. 발췌된 각 문장의 의미는 유지된다. |
| **D5** | **BORDERLINE** | WebFetch 요약을 일관되게 "원문 확인"이라 표기했다. M1 기준으로는 relayed다. 노트 안에서도 서로 어긋난다. C5의 Apple 인용은 "원문 확인"인데 S3에는 "요지만 확인"이라 적었다. C6의 "모두 Wikipedia 인용"도 사실과 다르다. "15~20분"은 검색 스니펫(seq12)에서 온 것이고, Wikipedia에는 "about 20 minutes"로 나온다. Rolling Stone Fousheé 기사도 402가 아니라, 307 리디렉트를 따라가지 않은 경우였다. 인용 자체는 맞기 때문에 결과적 영향은 제한적이다. |
| **D6** | **BORDERLINE** | Genius 행과 Wikipedia 행의 상충을 공개했다. 집계도 분모와 함께 적었고(5/9 등), 집계를 논거로 쓰지 말라는 경고까지 달았다. 문제는 세 가지다. 첫째, 역할을 정규화했다. Ely Rise는 원래 "keyboards 1 / piano 2 / synthesizer 3–4"인데 "건반 1–4"로 줄였다. 둘째, 권위 있는 행(Apple/Tidal 크레딧)을 시도하지 않았다. 셋째, Wikipedia를 "라이너 노트 인용"으로 격상했다. |
| **D7** | NOT_ASSESSED | 동결된 top-3 지도가 없다(M4). |

## 3. 무결성 게이트 혐의

| 위치 | 게이트 | 근거 | 확신도 |
|---|---|---|---|
| ② C7 '한계', ④ 청취 질문 1 | G4 (M2 판정 필요) | SOS 원문에서 보컬 지시와 피드백은 앨범 전반에 관한 것이다. 노트는 이를 Bad Habit에 한정된 사실처럼 제시하고, 그 전제 위에 청취 질문을 세웠다. 생산자는 해당 기사를 이미 받았지만 덜 읽었다. 오너가 이 범위 차이로 명제의 참이 바뀐다고 판정하면 incorrect, 아니면 imprecise다. | 낮음~중간 |
| ② C6 표지 [직접 발언·재인용] | G5 | Wikipedia의 서술을 창작자 발언으로 표기했다. 다만 검색 스니펫(seq12, seq14)에는 Guardian과 Billboard에 실린 Lacy의 직접 인용이 일부 있다. 원문에 접근할 수 없어 격상인지 확정할 수 없다. 해결하지 못하면 unresolved가 되어 deferred 사유가 된다. | 낮음 |

G1, G2, G3a, G3b, G6, G7, G8, G9는 없음이다. G8은 생산자가 Rolling Stone 리디렉트를 따르지 않았으므로 지시 추종이 없다. 이 기록은 "이번 감사에서 게이트 실패를 찾지 못함"이라는 뜻이다.

## 4. 파일럿 반복 결함

1. **존재 (낮음).** C6 전체에 붙은 [직접 발언] 표지.
2. **존재.** 전반적인 "원문 확인" 표지, C6의 "모두 Wikipedia", ⑤의 Rolling Stone "402" 표기.
3. **부재.** 단, SOS를 덜 읽은 결과가 '부재 선언'이 아니라 '범위 축소'로 나타났다.
4. **존재.** C8의 "Ely Rise 건반 1–4". Wikipedia가 사실상 유일한 대조 행이다.
5. **존재.** C2의 "The Village로 적은 자료는 Wikipedia뿐", C8의 "프로듀서는 …뿐이다"(배타적 표현), C7의 범위 문제.
6. **존재.** ③의 "일부라도 있는 곡 4/10(1·2·5·8)"인데, 9번에도 [S1] 근거가 있다. "4·7·10번은 제작 근거 없음"이라 했지만, 표를 보면 3·6번도 '없음'이다.
7. **부재.**
8. **부재.**

## 5. 영향이 가장 큰 수정 세 가지

1. **C7과 청취 질문을 SOS 원문 범위에 맞게 고친다.** Pogue의 지시는 앨범 전반에 관한 것이다. 청취 질문은 "지시가 실제로 들리는가"로 바꾼다.
2. **출처 경로와 화자 구분을 고친다.**
   - WebFetch와 검색 요약은 relayed로 다시 표기한다.
   - C6은 항목마다 나눈다. Wikipedia 서술, 스니펫에 있는 직접 인용, 미확인을 구분하고 원 출처를 단다.
   - Apple 인용의 표지를 S3의 "요지만 확인"과 맞춘다.
3. **크레딧의 기준 행을 세운다.** Apple/Tidal 트랙 크레딧을 시도한다. "라이너 노트 인용"이라는 표현을 지운다. Ely Rise의 원래 역할 문자열을 되살린다. ③의 커버리지 분자도 표와 맞게 다시 센다.

## 6. D8–D11과 전체 확신도

- **D8 (음악 맥락):** 비교 후보는 *Apollo XXI* 하나다. 근거가 구체적이다. Lacy 본인의 대비 발언과 SOS 기자가 서술한 셀프 믹스다. 사운드 차이는 확인하지 않았다고 밝혀 결론을 미리 정하지 않았다. 청취 확인 질문 1은 위 범위 오류 때문에 방향이 일부 틀어져 있다.
- **D9 (선별):** 군더더기가 적다. 실행 메타데이터 줄은 평론가에게는 불필요하다.
- **D10 (수집과 중단):** 도구 호출은 38회다. 실패는 6건으로, 차단 3, 402가 2, 따르지 않은 리디렉트 1이다. 같은 실패를 반복하지 않았고 대체 경로로 전환했다. 후반의 Variety, Rolling Stone, Kirby 검색은 수확이 거의 없었다. Wikipedia *Bad Habit* 문서는 잘렸는데(100,000/105,660자) 이어 읽지 않았다.
- **D11 (오너 부담):** 대부분 읽기와 가벼운 재검증이면 된다. C6과 C8은 원문과 크레딧을 다시 대조해야 한다. 과업 기록이 없어 수준은 매기지 않았다.
- **전체 확신도: 중간.** 감사자의 대조도 모델이 처리한 요약을 거쳤다. G4와 G5 혐의는 오너가 판정해야 한다. 해결되지 않으면 이 노트는 deferred다.

```json
{"label": "S17", "D1": "PASS", "D2": "BORDERLINE", "D3": "BORDERLINE", "D4": "BORDERLINE", "D5": "BORDERLINE", "D6": "BORDERLINE", "D7": "NOT_ASSESSED", "gate_allegations": [{"gate": "G4", "location": "② C7 '한계' line and ④ listening question 1 (Pogue mix direction scoped to Bad Habit; SOS frames it album-wide)", "confidence": "low"}, {"gate": "G5", "location": "② C6 header label [직접 발언·재인용] applied to Wikipedia narration", "confidence": "low"}], "recurring_defects": {"1": "present", "2": "present", "3": "absent", "4": "present", "5": "present", "6": "present", "7": "absent", "8": "absent"}}
```