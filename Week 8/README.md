# Week 8: RAG and GraphRAG side by side, routing explained, messy wording

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 8 acts on the Evaluation items from the 11/5 meeting
(minutes #6). Gold Set v2 (155 questions on Data's ten companies) is unchanged from Week 7; **every number below is on
those 155 questions only** and will move as questions are added.

```bash
pip install -r requirements.txt
./scripts/run_all.sh                                     # full pipeline incl. Week 8, 82 tests, about 1 minute
python scripts/run_side_by_side.py                       # RAG vs GraphRAG on the same filing
python scripts/run_messy_wording.py                      # typos and casual wording
python scripts/routing_examples.py                       # demo walkthrough -> ROUTING_EXAMPLES.md
python scripts/build_deck_w8.py <base.pptx> <out.pptx>   # this week's seven Eval slides
```

Start with [`FOR_TEAMS_W8.md`](FOR_TEAMS_W8.md) (one section per team) and [`ROUTING_EXAMPLES.md`](ROUTING_EXAMPLES.md).

## 11/5 action items → what exists now

| Action item (minutes #6) | Where | Result |
|---|---|---|
| Run one question set on RAG and GraphRAG, compare side by side | `scripts/run_side_by_side.py` → `results/side_by_side.json`, `side_by_side_per_question.csv` | All 84 Microsoft 10-Q questions through each team's own code on the same filing, top 8. Needed figures in evidence: RAG (BM25) 49/50, GraphRAG structured search 25/50. Gold passage for prose: 18/27 vs 0/27. Wrong-period figure also shown: 33/36 vs 19/36. Head to head on 77 answerable: both 25, RAG only 42, GraphRAG only 0, neither 10 |
| Show where GraphRAG does better, and where RAG does | same, `part_b` and `number_miss_diagnosis` | 9 Exhibit 21 relationship questions: GraphRAG's agreed shape answers 9/9 by traversal; RAG's index has none of them (exhibits not ingested); with Exhibit 21 added as text, BM25 brings every needed row for 6/7 tested. GraphRAG's 25 number misses: 13 ranked below 8, 10 multi-input calculations, 2 wording |
| Label the routing chart's axes; define the keyword router | `scripts/build_deck_w8.py` (slide 4), `ROUTING_EXAMPLES.md` | Chart by expected route (x: route needed, with n; y: share whose needed tools were called) |
| Explain how unneeded calls per question are measured | `kpmg_eval/metrics/routing.py`, `ROUTING_EXAMPLES.md` | Tools called that the expected route does not need, summed and divided by 155. Not "text search alone would have answered" (correction to the minutes) |
| Concrete routing examples for the demo | `scripts/routing_examples.py` → `ROUTING_EXAMPLES.md`, `results/routing_examples.json` | Seven questions: one per route plus two where rules break |
| Accuracy is on the current 155 questions only | every Week 8 result and slide | Routes: 104 finance data, 31 text, 11 relationship, 8 no tool, 1 both |
| Typos and messy wording, for real-user accuracy | `scripts/run_messy_wording.py` → `data/messy_wording_v1.jsonl`, `results/messy_wording.json` | 427 meaning-preserving rewrites. Scope check with no company picked: 98% → 19% on misspelled names, 82% → 9% casual; 94% / 79% once it matches tickers and near-miss names. Router: −5 to −7 points. Search: name typos cost nothing; misspelled finance words cost RAG 86% → 73% and GraphRAG 30% → 17% |

## How the side-by-side is run (and what it is not)

- **Same filing for both:** Microsoft Q3 FY2026 10-Q (0001193125-26-191507), Data's copy. It is the one filing both
  teams' code can load here without a network or a database server.
- **RAG @ 11f8b42:** `rag.chunk.chunk_filing` (158 chunks) → `rag.index.build_index` → `Retriever.search(question,
  filters, top_k=8)`. BM25 is RAG's own BM25 exactly; "hybrid" uses RAG's offline LSA stand-in for the dense model.
- **GraphRAG @ 1980a79 (demo/walkthrough):** `structured/fact_loader_v1.py` builds the DuckDB store (1,317 facts;
  `scripts/fetch_upstream.sh` does it), then `structured_query_v1.structured_search`. The graph arm needs Neo4j and has
  no claims for this filing, so it is not in Part A.
- **Scoring is at the evidence level** (no reader model): numbers count when every input figure is in the top 8 (RAG: the
  digits as printed, so "(84,669)" matches "84,669"; GraphRAG: a returned fact with that value). Prose counts when every
  gold text anchor is in the top 8. RAG's string match can over-count slightly.
- **Part B** loads Eval's Exhibit 21 reads (`data/sec_reads/exhibit21_2026-11-05.json`) into GraphRAG's agreed shape
  (Company OWNS Subsidiary, ontology decision 2.6). It shows what the design can answer; it is not GraphRAG's production
  graph. NetApp's two questions are not tested on the RAG side: we read only its Israel rows, and a 5-row page falls under
  RAG's 400-character minimum for unlabeled text.

## Files

`scripts/run_side_by_side.py`, `scripts/run_messy_wording.py`, `scripts/routing_examples.py`, `scripts/build_deck_w8.py`,
`tests/test_week8.py`; `results/side_by_side*.{json,csv}`, `results/messy_wording.json`, `results/routing_examples.json`;
`data/messy_wording_v1.jsonl`. Upstream pins in `scripts/fetch_upstream.sh` (RAG 11f8b42, GraphRAG main 97eeba5 and
demo 1980a79, Data f8d18e2). Week 7 material (Gold Set v2, decision rules, routing baselines) is carried over unchanged.
