# Week 5: Gold Set v1, RAG's real retriever, new metrics

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 4 built the metric library and scored RAG's *mock*.
Week 5 moves everything onto what the other teams actually built: the RAG pilot corpus (AAPL, AMZN, META, MSFT, NVDA),
RAG's real `retrieve()` code, the Data team's XBRL instance, and the Business/UI prototype's use cases.

```bash
pip install -r requirements.txt
./scripts/run_all.sh     # pins upstream repos, rebuilds Gold Set v1, validates, 47 tests, every evaluation + scorecards (~15 s)
python scripts/run_harness.py --answers agent_output.jsonl   # grade the Agent's AnswerBlocks
```

## 1. Gold Set v1: 100 questions (`data/`)

| File | What |
|---|---|
| `benchmark_v1.jsonl` | 100 questions, full records: typed answer, XBRL fact keys, distractors, RAG evidence anchors, graph paths, traps |
| `benchmark_v1_rag_format.jsonl` | The same questions in RAG's `eval/README.md` format, a drop-in for `python -m rag.cli eval --gold ...` |
| `benchmark_v1_questions.md` / `.csv` | Readable list with expected answers (for Business/UI review) |
| `gold_graph_v1.json` | 93 nodes / 104 edges GraphRAG needs for these questions (Company, Filing, Fact, Segment/Product/Geography) |
| `msft_xbrl_facts.jsonl` | 1,622 facts parsed from the Data team's MSFT 10-Q XBRL instance (SHA-256 matches their manifest) |
| `peer_facts_v1.jsonl` | 16 peer and MSFT 10-K facts, each read twice from the SEC companyconcept API (`sec_api_calibration.json`: 2/2 identical to local XBRL) |

**Composition.** 30 questions are RAG's Gold Set v0 (Microsoft Q3 FY2026 10-Q), kept under their ids and wording,
so both teams score the same set. The 70 new ones fill the gaps that RAG's own documentation lists: cross-company,
cross-document (10-K vs 10-Q), unanswerable and false-premise questions, plus balance-sheet, segment and fiscal-calendar traps.

| Type | RAG v0 | New | Total |
|---|---|---|---|
| Extraction (incl. segment) | 3 | 23 | 26 |
| Calculation & comparison | 4 | 13 | 17 |
| Derived & reconciliation | 3 | 7 | 10 |
| Definition & narrative | 20 | 6 | 26 |
| Cross-company (5 tickers, calendar Q1 2026) | 0 | 11 | 11 |
| Unanswerable & false premise | 0 | 10 | 10 |

The Business/UI prototype's flows are in the set: "compare revenue", "profitability", "explain a term", the
"Q4 derived from annual less Q1–Q3" calculation (3 derived questions using the FY2026 10-K), and scope guidance (10 refusal/false-premise questions).
64 questions carry GraphRAG paths (31 need 2+ facts, 5 cross-company); 29 answerable ones are text-only (RAG territory).

**Validation (`scripts/validate_benchmark_v1.py` → `results/benchmark_v1_validation.json`).**
- Every expected number is computed from facts, never typed. 7/7 accounting identities hold (segments sum to total, cash roll-forward, derived six-month revenue equals the separately filed Q2 YTD fact).
- 98% of checkable evidence anchors match RAG's own chunks under RAG's own matching rule. The 2 misses are RAG's: see finding R1.
- All 10 numeric RAG v0 reference answers agree with the XBRL. 17/17 quoted figures in Eval's text answers occur in the filing.
- An independent pass over the raw filing HTML finds all 110 MSFT figures the benchmark uses.
- 25 evidence anchors on peer and 10-K filings cannot be checked until RAG shares its multi-company `chunks.jsonl`.

## 2. RAG's real retriever on the real filing (`scripts/run_rag_retrieval_v1.py`)

RAG's code at commit `1996e72`, unmodified: `rag.chunk` on the Data team's HTML (158 chunks), `rag.index`,
`rag.retrieve.Retriever.search`, scored with RAG's own `rag.evaluate.score_question` so the numbers mean the same thing to both teams.
76 answerable questions on the MSFT 10-Q, plus 6 unanswerable ones.

| BM25 (RAG's production lexical ranker) | Value |
|---|---|
| Evidence recall@5 / @10 | 0.81 / 0.89 (95% CI on @10: see json) |
| MRR / graded nDCG@10 | 0.66 / 0.89 |
| Answer-in-context@10 (every needed figure in the top 10) | 94% of numeric questions |
| Recall@10, text-only vs table-fact questions | 0.80 vs 0.95 |
| Abstention AUROC of top-1 score (76 answerable vs 6 unanswerable) | 0.86, directional only (n = 6) |

**Wording robustness (25 lookup questions):** recall@10 is 1.00 with filing wording, 1.00 with the period phrase removed
(but only 45% of the top 10 stays the same), and **0.52 with analyst shorthand** ("MSFT Q3 FY26 EBIT"); MRR falls 0.75 → 0.24.
The Agent should rewrite queries into filing terms before calling `retrieve()`.

**Caveats.** (1) Not like-for-like with RAG's Experiment 1 (BM25 recall@10 0.61 on the same 30 questions): their index held
other Microsoft quarters as distractors, ours is one filing. (2) huggingface.co is blocked here, so RAG's dense model
(bge-small) cannot load. `dense`/`hybrid` rows use RAG's offline LSA stand-in, which RAG itself labels "NOT a real dense
baseline". They are in the json but not reported as results. (3) tiktoken's vocabulary download is also blocked, so the chunker
uses RAG's token-count fallback, and chunk boundaries may differ slightly from RAG's environment.

## 3. End-to-end floor (`scripts/run_e2e_baseline.py`)

There is no Agent v0 yet, so a deliberately naive, no-LLM reader (RAG BM25 top 5 → match a table row label → pick the
column from the period words) answers the 25 single-fact numeric questions. It gets **15/25 (60%, 95% CI 41–77%)**.
Every miss is a real fact from the filing read from the wrong place: 5 wrong cell, 3 wrong line item, 2 segment-instead-of-total.
All three segment-revenue misses read the segment *unearned revenue* table, which BM25 ranked above the segment revenue table.
This is the floor Agent v0 has to beat.

## 4. New and upgraded metrics (`kpmg_eval/`)

| Module | Status | What it adds |
|---|---|---|
| `metrics/reasoning.py` | spec → code | Reasoning-step accuracy: checks each lookup (key + value) and each arithmetic step of the Agent's calculation trace; names the first failing step (`wrong_period`, `wrong_concept`, `wrong_fact_value`, `bad_arithmetic`). Trace format: `answer_schema.CALC_STEPS_SCHEMA`. |
| `metrics/robustness.py` | spec → code | Query-wording robustness (filing / no-period / analyst variants), recall deltas and Jaccard@k of the top-k |
| `metrics/context.py` | new | Answer-in-context@k (ceiling on end-to-end accuracy) and evidence-rank distribution (where the evidence lands in the prompt) |
| `metrics/abstention.py` | new | AUROC of the retrieval score for answerable vs unanswerable, as a pre-Agent abstention gate |
| `metrics/premise.py` | new | False-premise handling: corrected / rejected / accepted |
| `metrics/diagnose.py` | new | Explains `wrong_value` answers by finding the filing fact the system actually read: `wrong_period`, `wrong_dimension` (segment vs total), `wrong_concept`, `wrong_cell` |
| `metrics/graph.py` | upgraded | Fact keys include XBRL dimensions; reports key collisions |
| `metrics/numeric.py` | fixed | Distractor matching takes the closest distractor (was: the first within 0.5%) |

**Grader check on Gold Set v1 (`scripts/run_fault_injection_v1.py`):** 389 fault-injected AnswerBlocks across all 62 numeric
questions (scale, sign, period, dimension, concept). Before the fix: 386/390 labels correct. After: 389/389 (95% CI 99.0–100%).
The after-fix number comes from the same generator that found the bug, so read it as a regression test, not independent validation.

**Graph fault injection (`scripts/run_graph_checks_v1.py`, not GraphRAG output):** dropping XBRL dimensions merges segment and
consolidated facts (18 key collisions, recall 0.72); missing nine-month facts → recall 0.75; period mislabel → F1 0.88;
10-Q scale error → F1 0.08.

## 5. Meeting action items (10/22 feedback)

| Ask | What exists now | Result |
|---|---|---|
| **Narrow the metrics to 3-5** | `scripts/run_metric_selection.py` scores 18 candidates on 5 criteria (user-visible outcome, automatic, grader validated, points to an owner, works for RAG and GraphRAG), each mark backed by a results file; adds redundancy (Spearman) and sensitivity (paired bootstrap) checks | **4 headline metrics:** numeric answer accuracy (north star), evidence recall@10, balanced refusal accuracy, citation support. Fifth slot: narrative quality once an LLM judge is validated. MRR and nDCG move together (ρ = 0.84) and become diagnostics; RAG should keep MRR for ranker comparisons (most sensitive: +0.17 BM25 vs hybrid-LSA) |
| **Build the automated grading pipeline** | `kpmg_eval/harness.py`, `scripts/run_harness.py`, `scripts/systems.py` (`AgentTemplate` for the Agent team). Wraps RAG's real `retrieve()` and logs every chunk a system saw; grades AnswerBlocks; scorecards record benchmark hash, RAG commit, index version, Eval commit | Perfect system 1.00 on all four (after its first run exposed 5 grader bugs, now fixed and tested); refuse-all 0.00 / 0.50; no-LLM baseline 0.32 numeric, 0.89 refusal, 0.92 citation |
| **Work on abstention** | `scripts/run_abstention_v1.py`: 56-item paired suite (`data/abstention_suite_v1.jsonl`: future-period and outside-corpus twins of answerable questions, 9 verified not-disclosed figures, 5 false premises); two-stage gate with out-of-fold thresholds | Scope check (company + period in the corpus): 42/42 out-of-scope twins refused, 0/76 real questions refused. The score gate, capped at 5% wrong refusals, catches 1 of 9 not-disclosed figures; those need an evidence check (no number without a cited passage that holds it) |
| **Help RAG measure filter accuracy** | `kpmg_eval/filters.py`, `scripts/run_filter_accuracy.py`, `data/filing_pool_v1.json` (17 pilot filings with SEC's own fiscal labels) | Fiscal labels 17/17 with RAG's year-end map, 9/17 without it. RAG Gold v0 filters (ticker + form) have filing precision 0.50 (every question also searches MSFT's other 10-Q); v1 filters 0.96, recall 1.00. 32 of 34 evidence chunks have no section label (94% lost to any section filter). 23 of 93 questions name no company: fine with the MVP session, ambiguous in comparison mode |
| **Swap tickers once the list is final** | `config/scope.json` drives the comparison questions; `scripts/refresh_peer_facts.py` re-pulls facts from the SEC API (double-read) | Config-driven build reproduces the 100 questions byte for byte; `--check` verifies config vs facts offline |
| **Run the real retriever** | Section 2 | BM25 recall@10 0.89 |
| Business/UI: MVP vs comparison, numeric vs narrative | Every question tagged `scope` and `answer_type` | 89 single-company MVP / 11 comparison; 62 exact numeric / 26 narrative / 10 refusal or false premise / 2 exact text |

## 6. Findings for other teams

| Team | Finding | Ask |
|---|---|---|
| RAG | R1. Gold v0 anchor `authorized 24,000; outstanding 7,429` (GSv0-MSFT-023, -030) never matches RAG's own chunker, which emits `24,000 ; outstanding`. Anchors are chunker-dependent. R2. Negatives render `( 84,669)`, so `(84,669)` never matches. R3. 140 of 158 chunks (89%) get section `Unlabeled`, so a `section` filter would drop them. | Normalise whitespace around punctuation in `evidence_hits`; add `fiscal_year`/`fiscal_period` to gold filters (Gold v1 has them); share the 5-company `chunks.jsonl` |
| GraphRAG | Without dimensions, segment facts and totals share a key | Keep axis + member in the Fact key; build against `gold_graph_v1.json` |
| Agents | Analyst wording halves recall; the BM25 score carries an abstention signal | Query rewriting; return `steps` in the AnswerBlock |
| Data Eng | Gold built from your XBRL instance (hash verified) | Confirm the MSFT FY2026 10-K and peer Q1-2026 10-Qs are loaded in RDS |
| Business/UI | Prototype flows are now benchmark questions | Review `benchmark_v1_questions.md` |

## Layout

```
data/       Gold Set v1 + source facts           scripts/   build, validate, evaluate (run_all.sh)
kpmg_eval/  metric library (Week 4 + Week 5)     results/   every number quoted above, as json/csv
tests/      47 tests (26 Week 4, 21 Week 5)      upstream/  pinned clones of KPMG_RAG and data_engineering_kpmg (git-ignored)
vendor/     RAG's mock retrieve() (MIT)
```
