# Week 9 (toward the 11/19 meeting)

Scripts here reuse `../Week 8` (Gold Set v2.2, graders). Other teams' files and the sealed holdout questions stay in the
git-ignored `private/` folder.

## 1. RAG's two narrative runs, scored (RAG's request of 11/16)

Same 38 questions (27 narrative, 5 categorical, 6 false premise), answers and cited chunks from RAG:
`final_v1` (frozen settings) and `narr_union` (a retrieval variant tuned on dev).

| Measure | final_v1 | narr_union |
|---|---|---|
| Questions with every required point stated | **26/38** | **28/38** |
| Required points stated | 94/108 | 94/108 |
| narrative only: questions / points | 17/27, 66/77 | 19/27, 67/77 |
| categorical: questions | 5/5 | 5/5 |
| false premise: questions / points | 4/6, 17/20 | 4/6, 16/20 |
| Points contradicted | 0 | 0 |
| Figures in the answer supported by a cited chunk | 69/69 (61 printed, 8 computed and re-checked) | 66/66 (61 printed, 5 computed) |
| Points found by word-for-word matching (no judge) | 44/108 | 44/108 |

- **The variant gains two questions and loses none** (GSv0-MSFT-029, GSv0-MSFT-030). It states fewer points on two
  others that fail in both runs (EV1-070, GSv0-MSFT-019), so total points are equal. Two questions out of 38 is not a
  reliable difference (2 changed one way, 0 the other), and one of the two gains rests on a close call.
- **Faithfulness: no unsupported figure in either run.** Every figure is printed in a cited chunk or computed from
  printed figures (arithmetic re-checked by the script). The sentences with the least word overlap with the chunks were
  read: all are conclusions the question asks for or statements that the excerpts lack something, not new facts.
  This is a figure-level check plus a screen, not a full claim-by-claim read of every sentence.
- **Ten questions fail in both runs**, mostly one missing point: the second level of a segment answer
  (GSv0-MSFT-006, -007), the reason behind a method (-011), drivers (-018, -019, -022, -027), after-tax amounts
  (EV1R-003), and two false-premise answers that stop after the correction (EV1-070, EV1R-005).
- **Gold difference:** RAG's file lists "approximately 27 percent" only for EV1R-005. Gold Set v2.2 also accepts 25%
  (the 10-K figure), so the answer's 25% counts as stated here.
- **Judge:** Claude (Fable 5.2) in the working session on 11/16, not an API run, using the Week 8 rubric. Every
  "stated" verdict carries a quote that the script finds in the answer. Eight close calls are listed in the results
  file so the hand labels can target them. **Agreement with hand labels is not computed yet**: it needs RAG's 20
  blind labels (due 11/18): `python scripts/score_rag_judge_runs.py --validate labels.csv`.

Files: `scripts/score_rag_judge_runs.py` → `results/narrative_judge_w9.json`, `_per_question.csv`, `_per_point.csv`
(verdicts and ids only).

## 2. Holdout batch A for RAG's `final_v1` (sealed)

40 new questions, built 11/16, **not in this repo until RAG has run them**. `results/holdout_A_manifest.json` holds
the counts and the file's SHA-256, so anyone can later confirm the questions were fixed on this date.

| Slice | Count |
|---|---|
| Exact numeric / narrative / unanswerable | 30 / 5 / 5 |
| Microsoft | 10 of 40 (25%) |
| Stress questions | 14 of 40: misspelled name 4, analyst wording 3, multi-step 2, relative period 2, cross-filing 2, narrative across sections 1 |
| Companies | 9 in the corpus (no NetApp: its facts are not in Data's store) plus one outside it |

- Every numeric answer is read from Data's fact store by concept and period; the builder refuses any fact a dev
  question already uses. Three derived questions combine one new fact with one dev fact and are listed in the manifest.
- The Week 8 grader passes the right answer and fails a 7% error on 30/30 numeric questions.
- Narrative and unanswerable questions (10) are marked `needs_human_review`: a person on Eval should read them before
  release.
