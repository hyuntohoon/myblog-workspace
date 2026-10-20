# D09 감사 보고 (Gemini Rights, Steve Lacy)

## 1. 감사 분모

- **URL**: 3건을 시도해 3건을 얻었습니다(Grammy.com, Nylon, Complex). 셋 다 WebFetch를 거친 모델 가공 텍스트입니다. Qobuz는 <D6_FROZEN_REFERENCE> 행으로 대조했고 따로 열지 않았습니다.
- **확인한 주장**: 약 40건입니다(C1–C8, ① 판본, ③ 표, ④, ⑤ S5 10행, G 일치 목록).
  - supported 36 · incorrect 3 · imprecise 1 · unsupported 0 → precision 36/40.
  - unassessable 0.
- **중심 주장**: 14건으로 판단했습니다(판본, C1–C8, S5 크레딧 행, ④-1 G↔S5 차이, Sunshine 드럼, 샘플 2건의 상태).
- **접근 한계**:
  - 저와 producer 모두 가공되지 않은 원문은 받지 못했습니다.
  - 열지 못한 원본: Zane Lowe, GQ, CBS 원본, genius.com, Rolling Stone(402).
  - 오디오는 확인하지 못했습니다.

## 2. D1–D7

| Dim | 수준 | 결정적 위치 · 근거 |
|---|---|---|
| D1 | **PASS** | ① 10곡, 34:57, ℗ 문구가 Qobuz(trace seq20·21)와 일치합니다. Spotify ID와 S5가 같은 판본인지는 대조하지 못했다고 밝혔습니다. 크레딧은 모두 S5에 귀속했고, 다른 판본 자료는 쓰지 않았습니다. |
| D2 | **FAIL** | ④-1 "Sunshine의 드럼은 Lacy 본인이 연주한 것으로 보입니다(추정)"가 틀렸습니다. S5 9번 행(동결 참조)은 "Karriem Riggins, Composer, Lyricist, Drums"이고, 노트의 ⑤ 부록과 Wikipedia(seq3)도 같습니다. 크레딧 주장이라 중심·고위험입니다. "추정"으로 유보돼 있으므로 G4가 아니라 C-D2-FAIL 경로입니다. 이 밖에 ③ 표에 비중심 오류 2건이 있습니다(§4-3·6). |
| D3 | **PASS** | C5는 Nylon 기자 서술을 보도로 구분했습니다. C3에서 S7을 독립 근거로 세지 않았고, C7과 S5도 독립 근거 두 개로 세지 않았습니다. S6의 아티스트 명의 성명은 본문에 쓰지 않았습니다. |
| D4 | **BORDERLINE** | C1·C2·C3·C4·C8은 각 URL에서 바로 찾았습니다(Grammy·Nylon·Complex 재열람). 다만 C6의 "too pitchy"는 원문에서 찾지 못했습니다. 제 재열람에서는 "but they were a little pitchy"였고, producer가 받은 seq9 요약의 인용부호 없는 의역("too pitchy to use")을 인용으로 옮긴 것입니다. 폐기됐다는 취지는 요약에 근거가 있어 뜻은 대체로 유지됩니다. 비중심입니다. S4의 lede-v2 URL은 producer가 열지 않았다고 밝혔습니다. |
| D5 | **BORDERLINE** | 좋은 점: ①에서 "[원문 확인] 없음"을 명시했고 M1에 맞습니다. 모든 C 항목에 경유 표시가 있습니다. 부족한 점은 두 가지입니다. ① 입력 지시는 "상충하면 상충으로 기록"인데, ④-1에서 S5 행과 G 집계의 실제 상충을 "미확인"으로 낮췄습니다(행 전문을 실어 피해는 작습니다). ② 근거 없는 "추정"이 드럼 크레딧을 대신했습니다. |
| D6 | **FAIL** | 위치는 ④-1 Sunshine 드럼입니다. 접근 가능했던 권위 행이 Riggins를 드럼으로 적고 있는데 다른 인물로 바꿔 넣었습니다(R-b·R-c: 인물 탈락·대체 → FAIL 경로). 이 1건을 빼면 PASS급입니다. ⑤의 10개 행은 동결 참조와 역할 문자열까지 모두 일치합니다. "Kirby Synthesizer 5/9"는 범위(매칭 9곡)와 표기 차이(John Kirby)를 밝혔습니다. 판본 주의: clean판(v9b6d7bh8muhl)에서는 3번 Dahi가 AdditionalStudioProducer인데, 노트는 이 차이를 몰랐습니다. 다만 explicit판 S5를 정확히 옮겼습니다. |
| D7 | NOT_ASSESSED | 동결된 top-3 맵이 없습니다(M4). |

## 3. 게이트 주장

**없음.** 이 감사에서 게이트 실패를 찾지 못했다는 뜻입니다.

- **Sunshine 드럼(④-1)**: 중심 incorrect이지만 "보입니다(추정)"로 유보돼 있어 established 제시가 아닙니다. G4 인접 사례로만 기록합니다. 오너가 이 유보 표현을 established로 본다면 G4를 검토할 대상입니다.
- **C6 "too pitchy"**: producer가 받은 도구 요약에 근거가 있어 날조(G2)가 아닙니다. D4 충실도 결함입니다.
- **G8**: trace의 "REMINDER: You MUST include the sources…" 문구는 출처 표기 지시일 뿐이며, 과업을 바꾼 흔적은 없습니다.

## 4. 파일럿 반복 결함

1. 기자 서술을 직접 발언으로 승격: **absent** (C5가 올바르게 처리).
2. 요약 텍스트를 원문 인용처럼 제시: **present**. C6 "too pitchy".
3. 이미 받은 자료를 덜 읽고 없다고 선언: **present**.
   - ③ 표 1 Static·4 Buttons의 '참조 관계'를 "없음"으로 적었지만, G 블록에는 각각 이후 리믹스·샘플(Static), 이후 리믹스(Buttons)가 등재돼 있습니다.
   - ④-1 Sunshine 드럼은 이미 받은 S5 행을 반영하지 않았습니다.
4. 역할 필드 축소·대체: **present**. ④-1 Sunshine 드럼 대체(단일 백과 의존은 없음).
5. 범위가 다른 진술 사이의 가짜 상충, 배타 표현 미점검: **absent** ("90%"를 본인 추정으로 처리).
6. 표·집계 분자 불일치: **present**. ③에서 "없음"이 5곡(1·2·4·7·8)인데 G는 "관계 없음 3/9"입니다. Mercury의 이후 샘플(Lil Yachty)도 빠졌습니다.
7. 리뷰·평점을 사실 근거로 사용: **absent** (Kellman 리뷰 미사용).
8. 불필요한 분량 초과: **absent** (부록 전문 수록은 ④-1 대조용으로 정당화됨).

## 5. 영향이 큰 수정 3가지

1. **④-1의 드럼 추정 삭제**: "Karriem Riggins, Drums (S5 9번 행)"으로 바로잡습니다.
2. **③ '참조 관계' 열을 G 블록에서 다시 옮기기**: Static·Buttons의 파생 관계와 Mercury의 이후 샘플을 넣고, "관계 없음"을 2·7·8 세 곡으로 맞춥니다.
3. **C6 인용 교체**: 인용을 검증된 문구("a little pitchy")로 바꾸거나 인용부호를 없앱니다. 아울러 ④-1의 Producer·작사작곡 차이를 입력 지시대로 [상충]으로 기록합니다.

## 6. D8–D11과 종합 신뢰도

- **D8**: 청취 확인 질문(가족 보컬 위치, Mellohi 소재)이 앨범에 한정돼 있고 결론을 미리 정하지 않습니다. 비교·영향 주장은 없습니다. 유용성 평가는 오너 몫입니다.
- **D9**: 단위 대부분이 조사나 검증에 쓰입니다. 반복은 ①과 ④-3 사이 접근 제한 정도로 가볍습니다.
- **D10**: 호출 25회입니다.
  - 실패: genius 거부 1, Qobuz 404 1, RS 402 1, Stereogum 홈페이지 반환 1. 같은 실패를 되풀이하지 않았습니다.
  - Qobuz 404 뒤 검색으로 정확한 URL을 찾아 회복했습니다.
  - 후반 샘플 검색(seq22·23)은 상충 점검이라 낭비가 아닙니다.
- **D11**: 대부분 읽기와 가벼운 검증입니다. 드럼과 ③ 표는 오너가 고쳐야 합니다.
- **종합 신뢰도**: 중상입니다. 드럼 오류와 ③ 표 오류는 동결 참조와 입력 블록으로 확정했습니다. "pitchy" 충실도 판정은 가공 요약끼리 비교한 것이라 중간입니다.

```json
{"label": "D09", "D1": "PASS", "D2": "FAIL", "D3": "PASS", "D4": "BORDERLINE", "D5": "BORDERLINE", "D6": "FAIL", "D7": "NOT_ASSESSED", "gate_allegations": [], "recurring_defects": {"1": "absent", "2": "present", "3": "present", "4": "present", "5": "absent", "6": "present", "7": "absent", "8": "absent"}}
```