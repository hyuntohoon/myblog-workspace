CONFIRM FREEZE

## (1) Fidelity of each part

**(a) §4 B: applied faithfully.** The added line comes right after the per-claim attribution rule, as the change list specifies. It covers all four elements:
- **Harness fact, stated generally:** "어느 링크에서 온 내용인지 밝히지 않는다"
- **Cite the summary, assign to no link:** "검색 요약을 출처로 적고, 목록의 어느 링크에도 배정하지 않는다"
- **A link is cited only after it is opened and gives the same content:** "링크를 열어 같은 내용을 받았을 때만"
- **Quote marks only after verbatim receipt from a link, otherwise written as what the summary relays:** "같은 문장을 그대로 받은 뒤에만 따옴표째 쓴다. 받지 못하면 따옴표 없이, 요약이 전한 내용으로 적는다"

It adds no recording duty. It covers only search summaries, so WebFetch summaries stay outside it, as declared.

**(b) §10 ⑤: applied faithfully.** The clause "검색 요약은 ID, '검색 요약', 검색어, 접근일" sits inside the existing one-line source format, as an exception to the hyperlink field. The rest of ⑤ is unchanged, including "도구가 요구하는 출처 목록은 ⑤의 출처 목록으로 갈음한다".

## (2) Scope creep

None. The diff has exactly the two hunks, one added line and one changed line. It names no outlet, service, album or track. It does not name the tool either: "검색 도구" is generic.

## (3) New material defects

None found that meet the bar.

- **Contradictions with unchanged rules:**
  - P4's relay rule and the new line agree. A summary that does name an outlet is still the document actually received, so P4's "X에 실렸다고 전함" applies to it.
  - The tension with §4 A's direct-URL requirement is the one already declared as watched.
- **Can a headless producer follow it?** Yes. Recovering the quote takes one WebFetch, and when the sentence does not come back verbatim, the instruction is simply to drop the quote marks. Nothing depends on information the harness withholds.
- **Length:** the only new output is one ⑤ line per search summary that is cited. That is smaller than the cheapest repair it replaces (putting a link's URL back on the summary). The cut order, the checklist and the role strings are untouched.
- **Cuts:** nothing is removed. Auditors gain the search query, which is what lets them replay the search.
- **Routes to known defects:** the line does not raise any status. Quote marks can only be lost, never added, so it cannot upgrade a relayed quote's attribution. It creates no conflicts and no quota.

One residual risk, already covered by the declared WebFetch half: the rule encourages fetches made to recover a quote. If a fetch prompt contains the target sentence, the fetch summarizer may echo it back. That would put the quote marks back and file the quote under the fetched link. This is the K7 shape on a different link, so it belongs to the untaken WebFetch decision and is not a defect of this edit. Worth watching in the traces: check whether the seq numbers of the fetches that recovered each quote show the quoted sentence in the fetch prompt.

Out of scope: a rule against putting the sought sentence in a fetch prompt ("찾는 문장을 열람 요청에 넣지 않는다") belongs with the WebFetch half of Claude's point 1.