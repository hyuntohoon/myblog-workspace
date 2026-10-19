# 감사 보고 — 노트 S02 (Steve Lacy, *Gemini Rights*)

## 1. 감사 분모

- **직접 시도한 URL과 결과**: 3건을 시도해 3건 모두 응답을 받았습니다.
  - Guardian 원문 검색 1건: 원문을 찾지 못했습니다.
  - songfacts.com Bad Habit 페이지 fetch 1건
  - en.wikipedia.org Gemini Rights 페이지 fetch 1건
  - 두 fetch 모두 모델이 처리한 텍스트입니다.
- **트레이스 대조**: 생산자 트레이스 40건(검색 21, fetch 19)을 노트 문장과 맞춰 봤습니다.
- **점검한 원자 주장**: 약 38개입니다. ①~⑤를 모두 보고 부록 S1–S14도 포함했습니다.
- **중심 주장**: 14개로 식별했습니다.
  - C1(3), C2(2), C3(1), C4(1), C5a–e(5), C6(1), C8(1)
- **접근 한계**:
  - Guardian, GQ, Billboard, Rolling Stone 원문은 저도 확보하지 못했습니다.
  - Genius 페이지와 부클릿 실물도 보지 못했습니다.
  - 그래서 C5c의 화자 분류는 Guardian 원문 없이는 확정할 수 없습니다.
  - 음향에 관한 주장은 검증할 수 없습니다.

## 2. D1–D6

| 차원 | 수준 | 결정적 근거 |
|---|---|---|
| **D1** | PASS | ①에서 Spotify ID 판본, 10트랙, 발매일을 명시했고 Apple "10곡·약 35분"(seq4)과 위키 34:57(seq5)이 일치합니다. Sped Up과 B-Sides는 주장 단위로 대상에서 제외했습니다. 사소한 문구 오류가 하나 있습니다. "아티스트가 … 지정한"이라고 썼지만 판본을 지정한 것은 파이프라인입니다. |
| **D2** | BORDERLINE | 중심 주장의 직접 인용(C1·C2·C3·C5b·C5d·C5e·C7)은 트레이스 seq6, 14, 30, 27, 9, 40과 일치합니다. C6의 위키 크레딧 행은 제가 다시 받은 결과와 일치합니다. 다만 비중심 부정확이 여러 개 있습니다. (a) C5c "Gordon이 엔딩을 썼다": 위키 원문은 "wrote **part of** the ending"이라 범위가 넓어졌습니다. (b) ③ 3번 행은 Mercury 라이브 공개를 "기자 서술"로 적었지만, seq6에 Lacy 인용("Performing it live, specifically before it came out")이 있습니다. (c) C7 "유일한 직접 발언"은 배타 주장인데 검증되지 않았습니다. (d) C6 "Kirby 신시사이저 … 맞습니다"는 곡 수만 맞춰 본 것입니다. Genius의 5/9가 어느 트랙인지는 제공되지 않았습니다. |
| **D3** | FAIL (조건부) | C4와 C5e는 기자 서술과 믹서 진술을 정확히 구분했습니다. 그러나 C5c의 "[직접 발언·재인용]"에는 문제가 있습니다. 확보된 중계(Songfacts는 "Later, he played it to Diana Gordon", 위키는 Guardian 인용 서술)에서 이 내용은 서술 문장이고, Lacy 발언은 "let's see what she's got"뿐입니다. C5a의 "엔딩 변경"도 위키 서술(seq12)입니다. 반면 Lacy의 직접 발언(Billboard, Songfacts 경유)은 "drums… chorus"만 말합니다. 그래서 서술→발언 격상으로 봅니다. Guardian 원문에 Lacy가 직접 그렇게 말한 대목이 있다면 BORDERLINE으로 내려갑니다. |
| **D4** | PASS | S2는 Q&A 번호, S4는 절 이름("The Real Thing", "Into The Groove"), S3는 단락까지 지정해 빠르게 찾을 수 있습니다. 경유 경로(Songfacts, AfroTech, 위키)도 표기했습니다. 생략부호("The focus … is the main guitar")도 의미를 유지합니다. 경미한 점: C5a의 "drums were different" 인용은 S8 경유로 적힌 AfroTech fetch(seq27)에서는 확인되지 않았고 Songfacts(seq30)에서 나왔습니다. |
| **D5** | BORDERLINE | 생산자가 받은 것은 모델이 처리한 fetch 요약(M1 기준 "중계")인데, C1·C2·C4·C5e·C7·S1에 "[원문 확인]"을 붙였습니다. 이는 접근 경로의 과장입니다. 인용 자체는 정확해서 결과에 영향은 없습니다. 재인용, 상충, 미확인 처리(C3, C5a–d, C6, C8, S6, S9)는 모범적입니다. |
| **D6** | BORDERLINE | 위키 Personnel 행과 파이프라인 Genius 집계를 각각 명명하고 상충을 해결하지 않은 채 공개했습니다. 협업자 역할을 논거로 쓰지 않은 점도 적절합니다(C6). 결함은 두 가지입니다. Ely Rise 역할을 "키보드·피아노·신시사이저 1~4번"으로 묶어 정규화했습니다(실제로는 1번 키보드, 2번 피아노, 3·4번 신시사이저). Gordon의 역할 범위도 넓혔습니다. 권위 있는 1차 행(부클릿, Tidal)은 없지만 공백으로 공개했습니다(④-1). |
| **D7** | NOT_ASSESSED | 동결된 top-3 맵이 없습니다(M4). |

## 3. 무결성 게이트 의혹

| 위치 | 게이트 | 근거 | 확신도 |
|---|---|---|---|
| ② C5c "Diana Gordon이 엔딩을 썼다는 내용 — [직접 발언·재인용] S7" | G5 | 크레딧·역할 주장이라 고위험이고 우선 내용에 있습니다. 확보된 중계 두 곳(위키 seq12, Songfacts seq30과 제 재조회)에서는 서술자 문장입니다. 생산자도 Guardian 원문을 못 봤으므로 발언 귀속을 세울 근거가 없습니다. | low |

- 확신도가 낮은 이유: Guardian 원문에 Lacy의 직접 진술이 있을 가능성을 배제할 수 없습니다. 오너가 확정도 기각도 하지 못하면 **unresolved**로 처리되고 노트는 deferred가 됩니다.
- 그 밖의 G1–G4, G6–G9: 이번 감사에서 게이트 실패를 찾지 못했습니다.
  - G3a: 음향 판단은 청취 질문으로 넘겼습니다.
  - G8: 트레이스의 "REMINDER" 문구는 하네스 텍스트이며, 지시를 따른 흔적이 없습니다.
- 주변부 패턴(게이트가 아닌 결함):
  - C7 "유일한 직접 발언": G6 유형
  - C6 신시사이저 곡 수 대조: G7 유형

## 4. 파일럿 반복 결함

1. **present**: C5c, C5a("엔딩")
2. **present**: 요약 fetch를 "[원문 확인]"으로 표기(C1, C2, C4, C5e, C7, S1)
3. **absent**
4. **present (경미)**: C6의 Ely Rise 역할 병합, Gordon 역할 범위 확대
5. **present (경미)**: ③ "가족 코러스 상충"은 GRAMMY의 "family parts"와 크레딧의 background vocals를 비교한 것이라 범위가 다를 수 있습니다. C7 "유일한"은 배타 주장인데 확인되지 않았습니다.
6. **absent**: 3/10, 6/10, 9/10 계산은 내부적으로 일관됩니다.
7. **absent**: 평론을 명시적으로 제외했습니다.
8. **absent**

## 5. 영향이 큰 수정 3가지

1. **C5a와 C5c의 화자 재분류.** "엔딩 변경"과 "Gordon이 엔딩 일부를 씀"은 [보도·재인용](위키 서술, Guardian 귀속)으로 바꿔야 합니다. Lacy 발언은 "drums… chorus"와 "let's see what she's got"으로 한정하고, "엔딩"은 "엔딩 일부"로 되돌립니다.
2. **"[원문 확인]"을 "[fetch 요약 경유]"로 낮추기.** 1차 원문이라고 표기하는 것은 생산자가 원문을 직접 받은 경우로만 한정합니다(M1).
3. **트랙별 역할 원문 복원.** C6의 Ely Rise 역할을 위키 원문대로 트랙별로 적습니다. Kirby 신시사이저 대조는 "곡 수만 일치, 트랙은 미확인"으로 표기합니다. ③ 3번 행의 Mercury 라이브 공개는 Lacy의 직접 발언으로 고칩니다.

## 6. D8–D11과 전체 확신도

- **D8**: 앨범 고유의 맥락(스튜디오 전환, 외부 믹서)을 근거와 함께 제시했고 결론은 평론가에게 남겼습니다. 다만 Apollo XXI 비교 근거는 회고와 기자 서술이라는 한계가 있습니다. 양호합니다.
- **D9**: 단위 대부분이 쓸모 있습니다. "Bad Habit"에 자료가 몰린 점은 노트가 스스로 공개했습니다. 중복은 적습니다.
- **D10**: 40건 동안 수집량이 꾸준히 늘었습니다. 402/403 응답을 받은 뒤 같은 요청을 반복하지 않고 Songfacts, AfroTech 같은 대체 경로로 옮겨 갔습니다. 늦은 W 원문 조회는 C1과 C2를 확정했습니다. 양호합니다.
- **D11**: 오너 부담은 C6 상충(부클릿 확인)과 C5 원문 확보에 집중될 것으로 봅니다. 나머지는 읽기와 가벼운 확인 수준입니다.
- **전체 확신도**: 중간입니다.
  - D2, D4, D6은 높음입니다.
  - D3과 G5 의혹은 Guardian 원문 부재 때문에 낮음입니다.
  - G5 의혹이 미해결로 남으면 판정은 deferred입니다.

```json
{"label": "S02", "D1": "PASS", "D2": "BORDERLINE", "D3": "FAIL", "D4": "PASS", "D5": "BORDERLINE", "D6": "BORDERLINE", "D7": "NOT_ASSESSED", "gate_allegations": [{"gate": "G5", "location": "② C5c (Diana Gordon ending, labelled [직접 발언·재인용] S7)", "confidence": "low"}], "recurring_defects": {"1": "present", "2": "present", "3": "absent", "4": "present", "5": "present", "6": "absent", "7": "absent", "8": "absent"}}
```