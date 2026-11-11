# Week 8: RAG and GraphRAG side by side, routing explained, messy wording

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 8 acts on the Evaluation items from the 11/5 meeting
(minutes #6) and on RAG's end-to-end round 1 (11/11). The 155 questions on Data's ten companies are unchanged from
Week 7; the current version, **Gold Set v2.2**, changes grading only. **Every number below is on those 155 questions only**
and will move as questions are added.

```bash
pip install -r requirements.txt
./scripts/run_all.sh                                     # full pipeline incl. Week 8, 99 tests, about 1 minute
python scripts/run_side_by_side.py                       # RAG vs GraphRAG on the same filing
python scripts/run_messy_wording.py                      # typos and casual wording
python scripts/routing_examples.py                       # demo walkthrough -> ROUTING_EXAMPLES.md
python scripts/grade_answer_blocks.py --answers <answer_blocks.jsonl> [--chunks <chunks.jsonl>] --tag <name>   # grade another team's answers
python scripts/run_narrative_judge.py --answers <answer_blocks.jsonl> --dry-run     # LLM judge for narrative answers (needs a key to run)
python scripts/build_deck_w8.py deck/template_base.pptx deck/KPMG_Eval_Week8_11-12.pptx   # this week's nine Eval slides
```

**Gold Set v2.2** (the round-1 questions; v2.2 = grading fixes of 11/11): [`GOLD_SET_V2.md`](GOLD_SET_V2.md), with the jsonl, a filterable spreadsheet
(`data/benchmark_v2_questions.xlsx`) and a Word version (`data/benchmark_v2_questions.docx`).

Slides for 11/12: [`deck/KPMG_Eval_Week8_11-12.pptx`](deck/) (PDF alongside). Messages to other teams: [`COMMS_W8.md`](COMMS_W8.md).

Start with [`FOR_TEAMS_W8.md`](FOR_TEAMS_W8.md) (one section per team) and [`ROUTING_EXAMPLES.md`](ROUTING_EXAMPLES.md).

## 11/5 action items → what exists now

| Action item (minutes #6) | Where | Result |
|---|---|---|
| Run round 1 in week 8 (minutes #5) | RAG's run, transcribed in `data/round1_rag_2026-11-09.json`; anchor fixes in `data/anchor_review_w8.json` → `scripts/build_gold_v2_1.py` → `data/benchmark_v2_1.jsonl` | RAG ran our scoring on Gold Set v2 (11/9): hybrid finds all evidence for 105/124 at k = 10 (numbers 83/93, prose 22/31; other nine companies 34/37). 4 of the 19 misses were our anchors; the same Gold v0 conversion made 22, all replaced in Gold Set v2.1 (questions and answers unchanged) |
| Round 1 end to end: RAG's reader with our graders (11/11), three grading notes | `scripts/grade_answer_blocks.py` → `results/answers_rag_reader_round1.json`, `_per_question.csv` (scores and labels only; RAG's answers and chunks stay in git-ignored `private/`); `scripts/build_gold_v2_2.py` → `data/benchmark_v2_2.jsonl`; `scripts/run_narrative_judge.py` | Reproduced RAG's figures exactly on its subset (NAA 87/93 = 0.935, balanced refusal 0.977, unanswerable 10/10). All 155: NAA 87/94 on v2 → 89/94 (0.947) on v2.2; balanced refusal 0.944; unanswerable 12/12; fiscal/list answers 5/12; false premise corrected 6/7. Citations: 185/185 cited chunks exist, 127/127 answers cite a gold filing, 58/59 lookups show the number in a cited chunk. RAG's three notes fixed in v2.2 (sig figs, multi-value questions, 2 routes); its files also showed two of our errors (EV1R-005's 25% vs 27%, v2.1 anchors split by its chunker). Narrative: judge ready, needs a key |
| GraphRAG's round 1 (11/11): both arms on Aura and its 20-filing store | `results/graphrag_round1_graphrag_aura.{json,csv}` (GraphRAG's, host and path removed); `scripts/check_graphrag_round1.py` → `results/graphrag_round1_check.json`; our rerun `results/graphrag_round1_eval_store20*`; the store stays in git-ignored `private/` | Structured arm: needed number in top 10 for 63/93, rank 1 right 26/93; graph arm prose 10/38 (first score). Our rerun on their store at #70 matches all 155 questions. GSv0-MSFT-001 is a tie (Microsoft 365 rows at 1.05), not a store difference; Part A on their store 24/50 vs 25/50 on ours (EV1-015). Filters: `{ticker, accession_number}`, lists for multi-filing questions. GraphRAG's hops (PR #71) merged into `data/hops_v2.csv` beside Eval's reference path. Graph arm prose by section scope: 10/20 inside the five sections it holds, 0/18 outside. Dropped connections retried, reported as infra errors |
| Run one question set on RAG and GraphRAG, compare side by side | `scripts/run_side_by_side.py` → `results/side_by_side.json`, `side_by_side_per_question.csv` | All 84 Microsoft 10-Q questions through each team's own code on the same filing, top 8. Needed figures in evidence: RAG (BM25) 49/50, GraphRAG structured search 25/50. Gold passage for prose: 22/27 vs 0/27 (Gold Set v2.1 anchors; 18/27 on v2's). Wrong-period figure also shown: 33/36 vs 19/36. Head to head on 77 answerable: both 25, RAG only 46, GraphRAG only 0, neither 6 |
| Show where GraphRAG does better, and where RAG does | same, `part_b` and `number_miss_diagnosis` | 9 Exhibit 21 relationship questions: traversal of GraphRAG's own Exhibit 21 rows answers 9/9; RAG's index has none of them (exhibits not ingested); with Exhibit 21 added as text, BM25 brings every needed row for 8/9 (the Apple-Micron join gets 15 of 31). GraphRAG's rows agree with our gold reads on 62/62. GraphRAG's 25 number misses: 13 ranked below 8 (6 because "three/six months" matches Microsoft 365 rows), 10 multi-input calculations, 2 wording |
| Label the routing chart's axes; define the keyword router | `scripts/build_deck_w8.py` (slide 6), `ROUTING_EXAMPLES.md` | Chart by expected route (x: route needed, with n; y: share whose needed tools were called). Coverage on v2.2: every tool 94.8%, keyword router 82.6% (83.9% on v2, before EV1R-002/006 moved to text), text only 21.3% |
| Explain how unneeded calls per question are measured | `kpmg_eval/metrics/routing.py`, `ROUTING_EXAMPLES.md` | Tools called that the expected route does not need, summed and divided by 155. Not "text search alone would have answered" (correction to the minutes) |
| Concrete routing examples for the demo | `scripts/routing_examples.py` → `ROUTING_EXAMPLES.md`, `results/routing_examples.json` | Seven questions: one per route plus two where rules break |
| Accuracy is on the current 155 questions only | every Week 8 result and slide | Routes (v2.2): 104 finance data, 33 text, 9 relationship, 8 no tool, 1 both |
| GraphRAG's 11/11 reply: real tools, filter fix, hops split, M-question rulings | [`EVAL_GRAPHRAG_W8.md`](EVAL_GRAPHRAG_W8.md); `scripts/run_graphrag_round1.py` → `results/graphrag_round1_eval_local.{json,csv}`; `kpmg_eval/graphrag_filters.py`; `data/hops_v2.csv`; `data/gold_candidates_v2_3.jsonl` | Harness on `graphrag.backends` (main 4e89acb). Structured arm on the MSFT 10-Q at k = 10: numbers 26/50, rank-1 right 14/50, rank-1 wrong period 6/36. Graph arm refuses fiscal labels on 129/155 gold questions, so Eval sends `accession_number` (136 questions sit in one filing); list-valued filters fail on both arms (13). Graph arm not run here: Aura and EDGAR are unreachable from Eval's workspace, so GraphRAG runs the script |
| Typos and messy wording, for real-user accuracy | `scripts/run_messy_wording.py` → `data/messy_wording_v1.jsonl`, `results/messy_wording.json` | 427 meaning-preserving rewrites. Scope check with no company picked: 98% → 19% on misspelled names, 82% → 9% casual; 94% / 79% once it matches tickers and near-miss names. Router: −5 to −7 points. Search: name typos cost nothing; misspelled finance words cost RAG 91% → 80% and GraphRAG 30% → 17% |

## How the side-by-side is run (and what it is not)

- **Same filing for both:** Microsoft Q3 FY2026 10-Q (0001193125-26-191507), Data's copy. It is the one filing both
  teams' code can load here without a network or a database server.
- **RAG @ 5bfafeb (main, 11/5):** `rag.chunk.chunk_filing` (158 chunks) → `rag.index.build_index` → `Retriever.search(question,
  filters, top_k=8)`. BM25 is RAG's own BM25 exactly; "hybrid" uses RAG's offline LSA stand-in for the dense model.
- **GraphRAG @ 7bcbdaf (main, 11/8):** `structured/fact_loader_v1.py` builds the DuckDB store (1,317 facts;
  `scripts/fetch_upstream.sh` does it), then `structured_query_v1.structured_search`. The graph arm needs Neo4j, which is
  not reachable from here, so it is not in Part A. Results are identical on the earlier demo branch (1980a79).
- **Scoring is at the evidence level** (no reader model): numbers count when every input figure is in the top 8 (RAG: the
  digits as printed, so "(84,669)" matches "84,669"; GraphRAG: a returned fact with that value). Prose counts when every
  gold text anchor is in the top 8. RAG's string match can over-count slightly.
- **Part B** uses GraphRAG's own Exhibit 21 output (`ex21_pipeline/output/graph_edges.csv` on branch
  alina/ex21-pipeline @ c21fe89, all ten companies) and answers each question by traversal in memory. It also checks those
  rows against Eval's gold reads (`data/sec_reads/exhibit21_2026-11-05.json`): 62/62 rows agree on name and jurisdiction.
- **RAG's round-1 corpus** (`eval/round1_filings.csv`, Data's freeze list) matches our 21 filings 21/21. RAG shared its
  chunks (`chunks_C1`, 20 filings; NetApp's 10-Q is not among them) on 11/11; they stay in git-ignored `private/`, as Data
  asks, and are used for anchors and citation checks. The side by side stays on the one filing both teams' code loads here.

## Files

`scripts/run_side_by_side.py`, `scripts/run_messy_wording.py`, `scripts/routing_examples.py`, `scripts/build_deck_w8.py`,
`scripts/grade_answer_blocks.py`, `scripts/build_gold_v2_2.py`, `scripts/run_narrative_judge.py`, `kpmg_eval/metrics/categorical.py`,
`tests/test_week8.py`; `results/side_by_side*.{json,csv}`, `results/messy_wording.json`, `results/routing_examples.json`,
`results/answers_rag_reader_round1*.{json,csv}`, `results/gold_v2_2_changes.json`, `results/anchor_check_c1.json`;
`data/messy_wording_v1.jsonl`. Upstream pins in `scripts/fetch_upstream.sh` (RAG 5bfafeb, GraphRAG main 7bcbdaf and
Exhibit 21 branch c21fe89, Data f8d18e2; from 11/11 GraphRAG main 21f0795 and Data 7040b8a). Week 7 material (Gold Set v2, decision rules, routing baselines) is carried over unchanged.
