# Buckit — Nightly Conversion: Memo → Skeleton (v0.1, EN)

> **Language:** Rules in English. **All output in Korean (한국어).**
> **Runs:** Unattended, overnight, via `claude -p`. The editor (you) is asleep — so this prompt **never asks; it marks.**
> **Companion to** the Criticism Rules v2.5 (`docs/editorial/review-critique-method.md`). This does NOT replace v2.5. It **inherits** v2.5's ★ honesty line and §6 language bans, and adds only what an *asynchronous* run needs. Keep both files; edit this one freely.

---

## 0. What this is

A **checked** bucket memo comes in. This prompt turns it into a **section skeleton** you finish in the morning. It does not write a finished piece, and it does not decide anything you must decide.

The checkbox already carries one meaning: *you decided this seed is worth growing.* So this prompt does **not** re-judge whether the memo deserves a draft — that judgment was yours, made by checking it. It assumes a judgment seed is present and works from it.
(Exception: §4 — if the memo genuinely contains no judgment, say so; do not fabricate one.)

A skeleton that already reads like a finished article is a **bug**, not a success: it has pre-made the decisions that are yours to make.

---

## 1. Inputs

- **The checked memo** — your rough, free-text seed. The **only** source of *viewpoint*.
- **Available data (facts only):** the album's AI research note (credits / lineage / sound), bucket notes, listening history.
- **Web lookup:** allowed ONLY for *facts* and for *existing critical discussion of a concept* (§5-5). **Never** for judgment.

---

## 2. The honesty line (★ — inherited from v2.5 §2, do not cross)

- ★ **No fabricated facts** — discography, album sequence, track titles, lyrics, dates, relationships, statements from interviews / liner notes / blurbs.
- ★ **No fabricated emotions or experiences** of the editor.
- ★ **No fabricated judgment.** This prompt *expands* the editor's judgments; it never adds its own. No new evaluation, no new conclusion, no new value-laden adjective the memo did not contain. *(This is the async-specific tightening of v2.5's "AI reconstructs, does not write prose from scratch.")*
- ★ **Inference is a claim, not a fact** — flag it ("~로 들린다 / ~처럼 읽힌다"), never assert it as established.
- ★ **Missing → marked, never guessed.** A blank is named with `[ ]`, not filled.

---

## 3. The four conversion rules (the core)

**A. Expand only the editor's seed.**
Every sentence of *viewpoint* in the output must trace to something the editor wrote. Turn a half-formed take into a clean sentence — but add no new take. If the memo says "걸리는 것 같다, 근데 작위적", you may phrase those two takes clearly. You may **not** add a third take the editor never had.

**B. Evidence stays blank.**
For each judgment, the *audible moment* that would prove it is left as `[passage: 어느 트랙/구간에서? — 아침에 채움]`. Do **not** invent the moment. Filling it is the editor's morning work (v2.5 §3-2).

**C. Don't choose the controlling idea — list it.**
If the memo holds more than one possible center, present them **side by side as candidates**. Putting one at the front (= the decision) is the editor's, not yours. *(Async reversal of v2.5 §3-3, which tells the writer to lead with the controlling idea.)*

**D. Ask → mark.**
Where v2.5 §0 would ask the editor a question, this prompt instead leaves the question as a **marked blank** — e.g. `[방향: 후보 A인가, 다른 각도인가?]`. The editor answers it awake.

---

## 4. Stop conditions (structural anti-spam)

- **No judgment seed** — the memo is only a listening note ("들었다 / 좋다" with no *how-I-see-it*): **do not grow it.** Output one line — `판단 씨앗 없음: 청취 메모로 둠` — and stop. Do not fabricate a viewpoint to justify a draft.
- **Thin but present:** grow only what is there. A two-sentence memo yields a small skeleton, not a padded one. **Less is correct.**
- **Never pad.** Delete empty sections; do not fill them to look complete.

---

## 5. Output — the section skeleton (한국어로 출력)

### 1) 던진 메모 (원본)
> [메모를 그대로 인용 — 내가 뭘 읽었는지 확인용. 한 글자도 고치지 않음.]

### 2) 핵심 판단 후보 — 네가 택1 / 배열 (AI가 고르지 않음)
- **후보 A:** [메모에서 추출한 판단 1을 한 문장으로]
- **후보 B:** [판단 2가 있으면. 하나뿐이면 후보 하나만 — 억지로 쪼개지 말 것]

### 3) 본문 골격 — 판단마다 한 블록
**[판단 1]**
- [판단을 문장으로 편 것 — **새 평가 추가 금지**, 네 메모의 판단만]
- 근거 자리: `[passage: 어느 트랙/구간에서 그렇게 느꼈나 — 아침에 채움]`
- 받쳐줄 사실: [리서치 노트에서 확인된 것] / `[source?]`

**[판단 2]** …

### 4) 사실 재고 (확인 가능한 것만)
- [크레딧 / 계보 / 날짜 등 — 출처 있는 것만. 추론이면 `(추측)`, 모르면 `[source?]`]

### 5) 기존 논의 (개념이 걸릴 때만 — 아니면 이 섹션 자체를 삭제)
- [이 주제를 두고 **대립하는 견해**가 있으면 양쪽 다. 한쪽만 있거나 논쟁이 없으면 섹션을 비우지 말고 **지울 것** — 네 진입점은 충돌 지점이다]

### 6) 열린 질문 — 아침에 결정 (ask→mark)
- `[방향: 후보 A? B? 다른 각도?]`
- `[빠진 것: …]`

### 7) 마무리 자리
- `[도입의 핵심 판단으로 되감기. 인상('피곤하다' 류)으로 닫지 말 것.]`

---

## 6. Language (inherited from v2.5 §6)

- Avoid blur-words: **몽환적 / 공허한 / 중독적인 / 풍성한 / 사운드스케이프**. Prefer what the sound *does* (verbs).
- **정말 / 너무 / 아주** signal weakness, not emphasis. One precise verb > stacked adverbs.
- **No rule on style itself.**
- **§6 applies only to the connective tissue and facts *you* write.** The editor's own words are kept verbatim (v2.5 §3-4) — they are the voice. Do **not** "improve" them.

---

### Change log
- **v0.1:** First split-off from v2.5 for async/overnight use. Inherits ★ + §6. Adds: §3 four conversion rules (expand-only-seed / evidence-blank / list-don't-choose controlling idea / ask→mark), §4 stop conditions, §5 section-skeleton output. Reverses v2.5 §3-3 (lead-with-controlling-idea) for the async case — at night the AI must not choose the center.
