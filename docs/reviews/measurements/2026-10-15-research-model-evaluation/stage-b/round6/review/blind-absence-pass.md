# Contradicted absence values — orchestrator pass over blind labels (ROUND.md §6 (d))

Done on S01–S07 **before `blind-key.json` was read**, while the review lanes ran, and committed before any unblinding. Reviewer reports were not read for this pass; their defect-3/5 prose is merged in RESULTS after unblinding, with each addition marked as such.

**Method.**
- Unit: any statement in ③ (cells and lines under the table) or in ⑤ that an item or role is absent, not received, or exclusive ('없음', '등재 없음', '미등재', '미확보', '~뿐', '못했다', '0').
- A blank marker ('—') is not counted, because it does not state absence. Where it sits on a track the input lists a relation for, it is noted below.
- Each unit was checked against:
  - the shared input's Genius relation block, which lists relations for tracks 1, 3, 4, 5, 6 and 10 and none for 2, 7 and 8, with 9 unmatched;
  - the label's anonymous web trace, grepped per track for production statements, and for credit rows with role fields;
  - the note's own ②/③/⑤.
- A column whose legend or other cells limit its scope (for example "선행 샘플" only) is read within that scope.

| Label | Contradicted units | Location and evidence |
|---|---:|---|
| S01 | 0 | Reference column consistent with G. The line "1·2·4·6·7·10번은 … 트랙별 제작 근거를 찾지 못했다" is scoped to S1–S8: trace hits for those tracks are credit/tracklist rows only. |
| S02 | 0 | The "선행 샘플" column is scoped by its legend to prior samples, so "미등재" on 1, 4 and 10 (later derivatives only) is within scope. "미확보" on 4, 6 and 7: no production statement in the trace. ⑤ "통합 근거를 받지 못했다" (Dahi / Natche): the received Qobuz row lists them as separate people, with no identity link. |
| S03 | **1** | ③ track 4 Buttons, reference column "등재 없음". The input G block lists a later remix of Buttons (ikimasu). The same column writes Static as "등재 없음(이후 파생만)", so the column counts later derivatives. Production "없음" on 4, 6 and 7: no production statement in the trace. |
| S04 | 0 | Reference column consistent with G ("파생만", "커버 1건"). Production "없음" on 1, 4, 6 and 7: trace hits are credit rows and a Mic.com co-writing line for Static, which is a credit, not a production statement. |
| S05 | 0 | Reference column consistent with G. "역할 필드가 있는 유통 크레딧의 트랙별 행은 확보하지 못했습니다": Tidal fetch 404, Apple pages without credits, and no credit-row result anywhere in the trace. Consistent. |
| S06 | 0 | Production "없음" on 2, 4, 6, 7, 8 and 10: 0 trace hits with production or family-vocal context for Helmet, Amber or Give You the World. *Noted, not counted:* the reference column is '—' on 1, 4 and 10, where G lists derivatives. |
| S07 | 0 | Production "미확인" is a status, not an absence. "나머지는 앨범 단위 발언뿐" is consistent with the trace (0 track-level production hits for 2, 4, 6, 7, 8 and 10). The reference column for 2, 7 and 8 reads "G 관계 없음 3곡 중 하나로 추정", consistent with G's "관계 없음 3/9". |

Limits: grep-based trace check (track names near production / family-vocal terms, and credit rows by role-field pattern). A production statement phrased without the track title would be missed.
