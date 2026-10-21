# kpmg-eval — Evaluation & Testing workstream (KPMG × Columbia QMSS)

Metric library, benchmark v0 and test harness for the SEC-filings Q&A system. It runs today without
the project data: gold answers come straight from SEC XBRL, and the harness already scores the RAG
team's real `retrieve()` interface (their mock, PR #3).

```bash
pip install -r requirements.txt
./scripts/run_all.sh          # rebuild benchmark, 26 unit tests, all evaluations, charts (about 10 s)
SEC_USER_AGENT="Name email" python scripts/refresh_gold.py   # re-verify every gold fact against data.sec.gov
```

## One key for every team

Every gold answer, retrieved chunk and graph node resolves to the same `EvalKey` (`kpmg_eval/keys.py`):

| Level | Fields | Who produces it |
|---|---|---|
| COMPANY | CIK | everyone |
| FILING | CIK + accession | RAG chunks, GraphRAG Filing nodes |
| SECTION | + section (word-prefix match: `Item 7` matches `Item 7 MD&A`) | RAG chunks, GraphRAG Section nodes |
| FACT | CIK + XBRL concept + period start/end + unit | GraphRAG Fact nodes, XBRL tool, AnswerBlock |

These are GraphRAG's schema entities (10/8 deck: Company · Filing · Section · Fact) and RAG contract v0's
fields (`cik`, `accession_number`, `section`). So one benchmark scores VectorRAG, GraphRAG and the agent
without per-team translation. Gold evidence is written as keys plus required text, never as chunk ids,
so the gold set survives re-chunking and works for graph nodes that have no chunk id.

## What is in the box

| Path | What |
|---|---|
| `kpmg_eval/keys.py` | Shared EvalKey + adapters from RAG chunks, GraphRAG facts, SEC XBRL rows |
| `kpmg_eval/normalize.py` | Number parsing: `$21.2bn`, `21,155M`, `(412)`, `net loss of $115 million`, `3.6 pp`; precision-aware matching |
| `kpmg_eval/metrics/numeric.py` | Numerical Answer Accuracy + 7-label error taxonomy (period, concept, sign, scale, precision, value, refusal) |
| `kpmg_eval/metrics/retrieval.py` | Hit@k, evidence recall@k, MRR, graded nDCG@k, provenance@k; same code for VectorRAG and GraphRAG |
| `kpmg_eval/metrics/graph.py` | GraphRAG: fact extraction P/R/F1 + value accuracy, edge P/R/F1, entity linking to CIK, multi-hop path recall |
| `kpmg_eval/metrics/refusal.py` | RAA, group rates, balanced RAA, critical flags (hedged answers count as answered) |
| `kpmg_eval/metrics/citation.py` | Citation validity, numeric claim support (no LLM needed) |
| `kpmg_eval/metrics/ops.py` | Run-to-run consistency; latency p50/p95, tool-call error rate, cost per query from trace logs |
| `kpmg_eval/stats.py` | Wilson and bootstrap intervals, paired bootstrap for system A vs B |
| `kpmg_eval/answer_schema.py` | **AnswerBlock** JSON schema we ask the Agent team to return, + trace-log fields |
| `data/gold_facts_v0.jsonl` | 32 facts, 7 companies, 12 filings, read from the SEC companyconcept API (2026-10-14), each confirmed by a second accession-filtered read |
| `data/benchmark_v0.jsonl` | 33 questions: extraction 18 (incl. 5 quarter-vs-YTD traps), comparison 3, reconciliation 1, cross-period 6, unanswerable 5. Expected answers computed, never typed |
| `data/gold_graph_v0.json` | 51 nodes / 44 edges a correct graph must contain for these filings (fixture for GraphRAG) |
| `data/heldout_answers_v0.jsonl` | 31 hand-written answers, human-labelled before grading, never used for tuning |
| `vendor/mock_retrieval_tool.py` | RAG team's mock `retrieve()` from PR #3, unchanged (MIT License, © QMSS Practicum × KPMG — Retrieval & RAG Workstream) |

Companies: the RAG pilot set (JPM, BAC, C, CAT, DE, HON) plus Apple. Swap in the final tickers by
editing the fact table in `scripts/build_benchmark.py`; everything downstream recomputes.

## Results so far (all reproducible with `run_all.sh`)

**These measure our graders and harness, not the project system, which does not exist yet.**

| Check | Result | What it means |
|---|---|---|
| Unit tests | 26 / 26 pass | |
| Structured AnswerBlock grading, 189 fault-injected answers | 99.5% correct label (95% CI 97.1–99.9%) | Scoring fields is near-exact. Basis for asking Agents to return AnswerBlock |
| Free-text grader, 31 held-out human-labelled answers | 90% agreement (28/31; CI 75–97%) | Up from 2/10 for the week-1 pattern grader |
| Free-text grader, 697 fault-injected answers | 74.9% before fixes → 99.9% after | Round 1 found 4 grader bugs (see below). Post-fix figure is on the same generator, so the held-out 90% is the honest number |
| RAG mock retriever, 10 questions × 2 wordings | MRR 0.64 with filing wording, 0.26 paraphrased; Hit@5 1.00 vs 0.60 | Harness runs end-to-end on contract v0; paraphrase is the risk to test on the real retriever |
| RAG mock, 3 unanswerable queries | 3/3 still returned evidence | Retrieval alone gives no abstention signal; refusal must be decided downstream |
| Graph metrics, 3 injected extraction faults | F1 0.88 (missed YTD facts), 0.78 (period mislabel), 0.41 (10-Q scale error) | Each graph metric moves the way it should |

Round-1 grader bugs found by fault injection and fixed: refusals in free text were not scored as
`false_refusal`; "net loss of $X" was read as positive; trailing zeros ("$110 billion") counted as
significant figures; sign and scale checks ignored the precision the answer was written with.
Remaining known misses (held-out): "9,074 (in millions)" (scale stated in words after the number),
"declined 17.1%" (direction in a verb), a refusal phrased as "has not yet filed".

## Findings other teams should know

* **Data / GraphRAG — the same line item uses different XBRL concepts.** Caterpillar's recent filings
  report profit under `ProfitLoss`, not `NetIncomeLoss` (its `NetIncomeLoss` series in the API ends in 2011).
  Citigroup reports both for 2025 and they differ by $146M (noncontrolling interests: $14,452M vs $14,306M).
  A graph keyed on concept must map these, and our benchmark has a question (C03) that tests it.
* **Data — Citigroup's 2026 10-Q facts did not appear** in the companyconcept API for `NetIncomeLoss` or
  `ProfitLoss` when we read it (latest 10-Q fact filed 2025-11-06). Worth checking before Citi enters the corpus.
* **Data — fiscal calendars differ.** Deere's fiscal 2025 ended November 2, 2025; its "Q3 2026" ended
  August 2, 2026. Period keys must use dates, not calendar quarter labels.
* **RAG — on the mock, the contract's own example query** ("Microsoft's total revenue for the three months
  ended March 31, 2026") ranks the Microsoft Cloud note above the income statement. Expected for keyword
  overlap; a good first regression test for the real retriever.
* **Agents — please return an AnswerBlock** (`kpmg_eval/answer_schema.py`) with `trace_id`, `value`,
  `unit`, `period_start/end`, `concept` and `citations`, and pass the same `trace_id` to `retrieve()`.

## Metric owners

| Metric | Module | Owner |
|---|---|---|
| Numerical Answer Accuracy | `metrics/numeric.py` | |
| Claim faithfulness & citation support | `metrics/citation.py` | |
| Reasoning-step accuracy | spec only | |
| Answer relevance | spec only (LLM judge) | |
| Refusal & abstention appropriateness | `metrics/refusal.py` | |
| Run-to-run consistency | `metrics/ops.py` | |
| Retrieval Recall@k & MRR | `metrics/retrieval.py` | |
| Position & length robustness | spec only | |
| Latency, tool-call errors, cost | `metrics/ops.py` | |
| GraphRAG graph metrics | `metrics/graph.py` | |

## Next

1. Owners review and extend their module; add 5 questions each from the final tickers (→ ~70-question v1).
2. Agree AnswerBlock + `trace_id` with Agents; run on the real retriever as soon as PR #3's index is built.
3. Add the LLM-judge metrics (answer relevance, narrative faithfulness) once API budget is released,
   calibrated against `heldout_answers` before use.
