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

## 3. Two judges on the same answers (RAG's gpt-6-sol run, 11/16)

RAG ran our Week 8 judge script unchanged with gpt-6-sol on the 30 narrative questions. `scripts/compare_judges.py`
→ `results/judge_agreement_w9.json`; RAG's verdict files are in `results/rag_judge_gpt6sol/`.

| RAG run (gpt-6-sol judge) | Questions passed | Points stated | vs final_v1 |
|---|---|---|---|
| final_v1 | 17/30 | 74/87 | |
| narr_union | 17/30 | 73/87 | +1, −1 |
| narr_long (fuller answers, final_v2 candidate) | **23/30** | 80/87 | **+6, −0** |

- RAG's summary reproduces from its files: 17, 17 and 23 of 30; six gained, none lost; the re-run is identical on all
  87 points.
- **The two judges agree on 71 of 74 shared points on final_v1 (kappa 0.84)** and on 68 of 74 on narr_union
  (kappa 0.66). The three final_v1 disagreements: GSv0-MSFT-026 point 2, GSv0-MSFT-027 point 2, EV1-045 point 2
  (the answer computes 28.5% where the filing prints 29%; gpt-6-sol calls it contradicted, Claude stated).
- **The narr_union gain depends on the judge:** +2 with Claude, 0 with gpt-6-sol. All six union disagreements are
  points Claude marked as close calls or loosely worded. Treat narr_union as no measurable change.
- **narr_long's +6 is a dev-set result** (tuned and judged on the same questions). Batch B is its test. We have not
  seen its answers, so its faithfulness is RAG's judge only.
- **Human validation is still open.** No hand labels exist yet on either side. `private/labels_final_v1_priority.csv`
  is RAG's blank sheet with the judge disagreements flagged; two Eval labellers fill it, then
  `run_narrative_judge.py --validate` gives agreement and kappa for gpt-6-sol.

## 4. RAG's final_v2 candidate (fuller narrative answers), judged 11/16

RAG sent the judge input for its fuller-answers run (`narr_long`, the final_v2 candidate). Same 38 questions, same
rubric, same script (`scripts/score_rag_judge_runs.py`, run C).

| Measure (Claude judge) | final_v1 | narr_long |
|---|---|---|
| Questions with every required point stated | 26/38 | **34/38** |
| narrative only | 17/27 | **24/27** |
| Required points stated | 94/108 | 102/108 |
| Figures supported by a cited chunk | 69/69 | 80/80 (73 printed, 7 computed and re-checked) |
| Mean answer length (characters) | 197 | 240 |

- **Eight questions gained, none lost**, and no point contradicted. gpt-6-sol (RAG's run) shows the same direction on
  the 26 narrative questions both judges saw: 16 → 22 passed (Claude 17 → 24). The judges agree on 72 of 74 points on
  this run (kappa 0.74); the two differences are EV1-045 point 2 (28.5% vs 29%) and GSv0-MSFT-030 point 4.
- **The longer answers did not add unsupported figures.** Eleven more figures appear than in final_v1 and every one is
  printed in a cited chunk or computed correctly from printed ones.
- **Still missing in all three runs:** GSv0-MSFT-006 (second level of the segment answer), EV1R-003 (after-tax
  amounts), GSv0-MSFT-019 (declined), EV1R-005 (stops after correcting the premise).
- **This is a dev-set result.** The variant was tuned on these questions; holdout batch B is its test.

## 5. Scoring the messy-wording and abstention suites for another team

`scripts/grade_suite_answers.py` scores AnswerBlocks on `messy_wording_v1` (427 rewrites, keyed `vid`) and
`abstention_suite_v1` (56 items, keyed `sid`). Week 8's `grade_answer_blocks.py` cannot read those files as they are,
because rewrites have their own ids and abstention items have no gold record. Rewrites are scored against the clean
question's Gold Set v2.2 record, by perturbation, and paired with the same system's clean result (exact McNemar).
`tests/test_week9.py`: 5 tests.

One caution for whoever runs the messy suite: if the company is also passed as a filter, the 129 misspelled-company
rewrites cannot fail, so that run measures the reader's tolerance of typos and not the system's.

## 6. GraphRAG's live graph, read directly (11/17)

Read-only count queries in the Aura console (`results/graph_inventory_2026-11-17.json`): 11,614 nodes and 17,792
relationships, of which **752 Subsidiary nodes with 752 OWNS edges across all ten companies. Exhibit 21 is loaded.**
Counts match Gold Set v2.2 for the three companies we checked (Microsoft 8, Micron 21, Casey's 9), and four Exhibit 21
answers read straight from the edges match the gold answer (EV3-003, EV3-004, EV3-006, EV1R-001). This shows the data
is in the graph; whether GraphRAG's search returns it still needs their re-run on v2.2.

## 7. Deck and script for 11/19

`deck/KPMG_Eval_Week9_11-19.pptx` (+ PDF): 6 slides and 2 appendix slides; `SCRIPT_W9.md` is the spoken script (also
in the speaker notes). `scripts/build_deck_w9.py` asserts every number the script says against the results files.

## Team paragraph, week 9

This week we moved from measuring the systems to checking our own measurements. We judged three versions of RAG's
answers on the same 38 questions: the next version, with fuller answers, states every required point on 34 of 38
(26 for the frozen version), and all 80 figures in it are supported by a cited passage. We compared our judge with
RAG's and they agree on 72 of 74 points; where they disagreed, we reported no gain. We wrote and sealed a 40-question
holdout set that no team has seen, published its hash, and reviewed RAG's pre-registered test plan. We also read
GraphRAG's live graph for the first time and confirmed that Exhibit 21 is loaded (752 subsidiaries). Next: hand labels
on 11/18, the holdout run on 11/20, and the Agents, graph and cost tests by 11/24.

## 8. RAG and GraphRAG by question type: same questions, same metric (11/19)

`scripts/compare_by_type.py` → `results/rag_vs_graphrag_by_type.json` and `.csv`. Metric for every system: the evidence
the gold answer needs is in the top 10 results. Gold Set v2.2, 20 filings. RAG is RAG's own retriever (commit 5bfafeb,
BM25) built over its round-1 chunks; GraphRAG structured search is main a1e7cf7 on its 20-filing store; graph search is
GraphRAG's own run of 11/11, before Exhibit 21 was loaded.

| Question type | Questions | RAG (BM25) | GraphRAG structured | GraphRAG graph | Either |
|---|---|---|---|---|---|
| **All answerable** | 143 | 100/136 | 63/136 | 15/132 | 116/136 |
| Lookup | 60 | 48/60 | 51/60 | 5/60 | 59/60 |
| Narrative | 32 | 26/32 | 0/32 | 9/29 | 27/32 |
| Calculation | 30 | 24/30 | 11/30 | 0/30 | 28/30 |
| Relationship (Exhibit 21) | 9 | 0/8 | 0/8 | 0/8 | 0/8 |
| Cross-company | 6 | 2/6 | 1/6 | 1/5 | 2/6 |
| Microsoft only | 87 | 73/83 | 27/83 | 10/83 | 75/83 |
| Other nine companies | 56 | 27/53 | 36/53 | 5/49 | 41/53 |

- **The two are complements, not rivals.** Of 136 questions both can be scored on, 48 are found by both,
  52 only by RAG and 15 only by GraphRAG. A router that always picked the right one would reach
  116/136, against 100/136 for RAG alone.
- **By type:** GraphRAG's structured search is at least as good as RAG on lookups; RAG is far ahead on calculations and
  narrative, where an answer needs several facts or prose.
- **By company:** RAG leads clearly on Microsoft, GraphRAG's structured search on the other nine companies.
- **Limits.** This is evidence in the top 10, not answer accuracy. RAG here is BM25; RAG's own hybrid run with its
  production embeddings found 105/124 on its scored subset. Exhibit 21 questions score zero for every system because the
  text is not in RAG's chunks and the graph run predates the load; they need GraphRAG's re-run. False-premise questions
  have no evidence anchor and are not scored here.

## 9. Holdout batch B (sealed, 11/19)

30 questions for RAG's `final_v2` (tag 789bf81), built to fill batch A's thin categories. Only
`results/holdout_B_manifest.json` (counts and SHA-256) is in the repository.

| | Batch B | A and B together |
|---|---|---|
| Numeric / narrative / unanswerable | 6 / 18 / 6 | 36 / 23 / 11 |
| Microsoft | 7 of 30 | 17 of 70 |
| Stress questions | 18 | 32: every stress type has 5 or 6 |

Numeric answers come from Data's fact store and share no fact with batch A; one question pairs a new fact with a dev
fact and is flagged. Every narrative anchor was checked against the filing text. The grader passes the right answer
and fails a 7% error on 6/6 numeric questions. 24 questions (narrative and unanswerable) need a human read before
release.

## 10. UI smoke test (ready, waiting for the UI)

`ui_smoke/run_ui_smoke.py` drives a browser with Playwright: it types gold questions into the UI and checks, on the
rendered page, that an answer appears, that the gold figure is shown, that unanswerable questions are declined, that a
citation is displayed, and how long each answer takes. It needs the UI's address and four selectors from the UI team.
`ui_smoke/mock_ui.html` is a stand-in page used by the test; nothing has been run against the real UI yet.
