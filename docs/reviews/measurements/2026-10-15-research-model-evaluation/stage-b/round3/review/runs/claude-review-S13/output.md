# S13 감사 보고 — Steve Lacy *Gemini Rights*

## 1. 감사 분모

- **익명 트레이스 검토**: 30건 전부를 검토했다. 검색 18건, fetch 12건이다. 실패는 4건으로, WhoSampled 403 두 건, RS 402 한 건, 307 리디렉트 한 건이다.
- **감사자의 직접 접근**: 3건을 시도해 3건 모두 받았다.
  - Okayplayer 기사를 fetch했다.
  - 위키백과 "Bad Habit"을 문장별 각주 기준으로 fetch했다.
  - RS·Complex의 Fousheé 관련 서술을 검색했다.
- **확인한 원자 주장**: 44개이고 그중 중심 주장은 14개다(C1–C8 핵심, 판본, 크레딧 집계, ③표).
  - supported 41, imprecise 1, unsupported 2. Precision = 41/44이다.
  - unassessable는 0이다.
- **접근 한계**
  - 감사자가 받은 페이지 내용도 모델이 처리한 요약이다.
  - Grammy.com, W, AnOther, SOS의 인용은 트레이스의 fetch 요약으로만 대조했다.
  - RS 원문, Vulture, Zane Lowe 방송, Guardian, GQ는 열람하지 못했다.
  - 음원 청취는 불가하다.

## 2. D1–D7

| 차원 | 수준 | 결정적 근거 |
|---|---|---|
| D1 | **PASS** | ①에서 Spotify ID, 10트랙, 2022-07-15를 Apple Music(seq4)·위키(seq5)와 대조했다. 'Bad Habit (Sped Up)'은 대상 판본 밖이라고 주장 단위로 표시했다. 판본 문구에 모호함이 없다. |
| D2 | **BORDERLINE** | 중심 주장 C1–C8 인용은 모두 트레이스와 일치한다(seq9·12·13·16·21·26·29). 비중심 오류는 3건이다(③ 참조). ① C5: Okayplayer가 '절반'을 말했다고 했으나 원문에 없다(unsupported). ② S11: '4곡 공동 작곡'을 RS 기사의 서술로 돌렸다(unsupported). ③ ④-3: 2021년 6월 비트를 Guardian 근거로 적었다(imprecise). |
| D3 | **PASS** | 발언과 기자 서술을 일관되게 분리했다. C3에서 300곡·2년은 Stansfield의 서술로 처리했다(seq16 확인). Genius 주석은 커뮤니티 재인용으로 표시했다. 독립 확인을 과장한 곳은 없다. |
| D4 | **FAIL** (경계에 가까움) | C1–C8의 구절은 URL과 짧은 발췌로 빠르게 찾을 수 있고 충실하다. 문제는 C5의 "앨범의 절반 정도를 함께 썼다"이다. 이 따옴표 구절의 출처로 지목된 Okayplayer(S13)에서 해당 문장이 회수되지 않는다. 감사자 fetch 결과 기사에는 "co-written with … Fousheé"와 "90 percent"만 있다. 회수 실패가 이 한 구절뿐이지만, C-D4-FAIL 앵커에 따라 FAIL로 둔다. 날조 판정(G2)은 아니다. |
| D5 | **BORDERLINE** | ①에서 "[원문 확인] 없음"을 밝히고 전 항목을 [검색 결과 경유]로 표시했다. M1에 정확히 부합한다. 다만 검색 요약 문장을 특정 매체의 것으로 돌린 곳이 두 군데다(C5 Okayplayer, S11 RS). 접근 경로는 맞게 적었지만 출처 매체를 과대 귀속했다. |
| D6 | **BORDERLINE** | Genius 집계는 역할, 분자/분모, 출처를 모두 밝혔고(C4, ④-1) 위키 Personnel 행에도 고정했다. 그러나 두 가지가 걸린다. 첫째, 위키 "Writer(s)" 열을 '작곡'으로 정규화했다. 둘째, Dahi의 역할 차이를 다루지 않았다. Genius는 3·4·10번을 프로듀서로, 위키는 4·10번 co-production과 3번 misc. production으로 적는다. Martians의 3·4번 misc. production도 빠졌다. Genius가 Dahi의 트랙 행을 제공했는데도 ④-1은 Genius가 "합계로만 제공됐다"고 썼다. |
| D7 | **NOT_ASSESSED** | M4 |

## 3. 무결성 게이트 혐의

**없음** — 이번 감사 범위에서 게이트 실패를 발견하지 못했다.

- C5의 '절반' 주장은 출처 매체 귀속이 잘못됐다. 그러나 "[재인용·검색 결과 경유]"와 "스니펫으로만 확인"으로 표시해 검증된 사실로 제시하지 않았으므로 G9가 아니다.
- 원 발언이 Zane Lowe 방송에 실제로 있을 가능성도 남는다. 감사자가 발견한 것은 귀속 오류이지 날조(G2)가 아니다.
- G3a: 청취 관련 내용은 질문 형태로만 제시됐다.
- G8: 해당 없다.

## 4. 파일럿 반복 결함

1. **absent**
2. **present** — C5 "Okayplayer를 거친 스니펫으로만 확인했다(S13)"(원문에 '절반' 없음). ⑤ S11 "기사는 그녀가 'Sunshine'을 포함한 4곡을 함께 썼다고 서술했다"(트레이스 seq19는 publicist 자료로, 감사 검색은 Complex로 귀속).
3. **absent** — 미독 부분(S8의 끝 5,600자)을 공개했고, 부재를 단정한 곳이 없다.
4. **present (경미)** — ③ '위키 작곡' 열에서 Writer(s)를 작곡으로 좁혔다. ④-1에서 Dahi·Martians의 역할 차이를 누락했다.
5. **absent** — '90%'와 Mercury 가족 보컬 문제를 범위 차이로 처리했고, 근거가 있다.
6. **absent** — 7/10, 5/7, 4/5, 5/9, 6/9가 내부적으로 일관된다.
7. **absent**
8. **absent** — 부록과 청취 질문에서 Grammy 인용이 일부 반복되지만 기능이 있다.

## 5. 우선 수정 3가지

1. **C5 '절반' 주장**: Okayplayer 귀속을 삭제한다. "Zane Lowe 인터뷰 발언으로 전해지나 출처 미상, [미확인]"으로 낮춘다. Okayplayer가 실제로 담은 것("co-written with Fousheé", 2022-06-17)만 남긴다.
2. **출처 귀속 정정**
   - S11의 '4곡 공동 작곡'은 RS 기사의 서술이 아니므로 Complex(Brad Callas) 또는 미상으로 고친다.
   - ④-3의 2021년 6월 비트는 위키에 각주가 없고, 가장 가까운 각주는 GQ다. 이 점을 문장별로 구분해 적는다.
3. **D6 보완**
   - Dahi 3·4·10번과 Martians 3·4·6번의 역할 문자열을 Genius와 위키 사이에 트랙 단위로 맞대어 적는다.
   - '위키 작곡' 열은 원문 라벨 "Writer(s)"로 표기한다.
   - SOS 서술 "had more outside help this time"을 C4의 '90%' 옆에 병기한다(트레이스 seq26에 있다).

## 6. D8–D11 및 전체 신뢰도

- **D8**: 비교 후보는 '4ever' 하나다. Lacy가 직접 가족 보컬의 선례로 언급했다는 구체적 이유가 있다. 결론을 전제하지 않았고 '한계' 문단으로 해석을 절제했다. 양호하다.
- **D9**: 대부분의 단위가 조사, 검증, 탐색에 쓰인다. ③의 '자료 편중' 점검은 특히 유용하다. 부록의 인용 재게시는 경미한 중복이다.
- **D10**: 30회 호출에 실패 4회다. 403·402가 난 뒤 같은 URL로 재시도하지 않고 전환했다. Vulture·'cough' 탐색은 4회 반복됐는데(seq1·6·7·28) 수확이 평탄했다. 늦게 한 확인 검색(seq28–30)은 Castellanos 철자 문제를 해소하는 데 기여했다.
- **D11**: 오너의 작업은 주로 읽기와 가벼운 검증이다. 정정은 위 세 항목이면 된다. 독립 재조사가 필요한 부분은 크레딧 부클릿 대조 정도다.
- **전체 신뢰도**: 중상이다. 핵심 인용은 트레이스와 일치한다. 다만 감사자 역시 모델 요약을 거쳐 대조했으므로 글자 단위의 충실도는 보장할 수 없다.

```json
{"label": "S13", "D1": "PASS", "D2": "BORDERLINE", "D3": "PASS", "D4": "FAIL", "D5": "BORDERLINE", "D6": "BORDERLINE", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "present", "3": "absent", "4": "present", "5": "absent", "6": "absent", "7": "absent", "8": "absent"}}
```

Sources:
- [Okayplayer — Steve Lacy "Mercury"](https://www.okayplayer.com/music/steve-lacy-mercury-single-gemini-rights-album.html)
- [Wikipedia — Bad Habit (Steve Lacy song)](https://en.wikipedia.org/wiki/Bad_Habit_(Steve_Lacy_song))
- [Rolling Stone — Fousheé interview](https://www.rollingstone.com/music/music-features/foushee-bad-habit-steve-lacy-interview-1234679066/)
- [Complex — Fousheé softcore](https://www.complex.com/music/a/brad-callas/foushee-softcore-stream)