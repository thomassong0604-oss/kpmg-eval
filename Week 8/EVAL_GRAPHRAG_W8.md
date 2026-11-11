# Eval × GraphRAG, week 8: what we did with your 11/11 reply, and what we still need

Answers GraphRAG's "Reply to Eval, week 8" (11/11; markdown version `docs/eval-reply-w8.md` on branch
`docs/eval-reply-w8`). Thank you: the real tools, the filter fix, the Exhibit 21 output and the period warning all
landed in time for round 1. Everything below is in this folder and re-runs with `./scripts/run_all.sh` (87 tests).
Pinned: GraphRAG main @ 4e89acb (11/11), Exhibit 21 branch @ c21fe89.

## Done on our side

| Your point | What we did | Where |
|---|---|---|
| §1 Switch off the mock: import `graphrag.backends` | `load_tools(mock=False)` now imports `graphrag.backends` (falls back to `graphrag.retrieve` on older checkouts); `backend_status()` reports `configure_from_env()`. The side-by-side calls your structured arm this way | `kpmg_eval/graphrag_adapter.py`, `scripts/run_side_by_side.py` |
| §1 Filter fix (PR #65) | Confirmed on our store: the gold filter shape `{ticker, form, fiscal_year, fiscal_period}` now runs on the structured arm with no error. We note in our docs that `fiscal_year`, `fiscal_period`, `section`, `is_table` are accepted and **not applied** | `kpmg_eval/graphrag_filters.py` |
| §1 Period matcher | Measured: on the Microsoft 10-Q, the rank-1 fact is the needed value for **14/50** number questions and a known wrong-period value for **6/36**. Now reported on every run (`top1_right`, `top1_wrong_period`) | `results/side_by_side.json`, `results/graphrag_round1_eval_local.json` |
| Fourth mock finding: dims dict vs list | You were right, and it was worse than a mismatch: a list of `{axis, member, type}` made our `norm_dims` raise. Fixed: dict (mock), list of dicts (real) and pairs (gold) now give the same key | `kpmg_eval/keys.py` (`norm_dims`), `tests/test_week8.py` |
| NULLABLE_FIELDS: `section` null on the structured arm | Our fact-level key never used `section`; now stated in the adapter and tested (a structured row with `section=None` keys at fact level) | `kpmg_eval/graphrag_adapter.py`, `tests/test_week8.py` |
| §2 hops: two columns | Agreed. New sheet keyed on Gold Set v2.1: `filings` filled by Eval in code from the gold evidence (136 questions need 1 filing, 5 need 2, 2 need 3, 4 need 10, 8 none); `hops` left for you to derive from the ontology path; your review of the six drafts recorded as `graph_support` and `graph_path`. And yes, `hops_v1.csv` had 165 rows and none filled; v2 replaces it | `data/hops_v2.csv`, `scripts/build_hops_v2.py` |
| §5 Six relationship drafts | Your verdicts recorded per question (not yet, no, supported by text, supported, supported, partly). Update 11/11: RAG's reader then answered EV1R-002 and EV1R-006 correctly from the 10-K text, which matches your "no" and "partly", so Gold Set v2.2 routes both to text (graph route: 9 questions, all Exhibit 21) | `data/hops_v2.csv`, `data/benchmark_v2_2.jsonl` |
| M17 | Already reworded in Gold Set v2: EV1R-006 now answers from the FY2026 10-K, XBOX (formerly Gaming) USD 23,455 million → 21,790 million, down 7.1%, and says the filing gives no revenue line for Activision alone. The +$1,952M / +9.1% draft is gone | `data/benchmark_v2_1.jsonl` |
| M08 → abstention | Written as candidate EV3-010 ("in which filing did Activision Blizzard stop reporting as a separate registrant?", expected: abstain). It joins after round 1 (v2.3; v2.2 became the grading-fix release of 11/11), so the round-1 questions stay fixed | `data/gold_candidates_v2_3.jsonl` |
| M12 → segment figure, not false premise | Agreed for when it is written. But Data's inventory of the ten companies (2021–2026: 59 10-K, 174 10-Q) has **no 10-K/A**, so M12, M13 and M19 need ADM (outside the ten) or Data adding amendments. Parked | Data `docs/validation/fact-coverage-2021-2026.csv` |
| §6 Data, together | Microsoft's FY2024 10-K (0000950170-24-087843) and FY2025 10-K (0000950170-25-100235) are in Data's inventory and passed its checks, but are not in the 21-filing database. That is the concrete ask for M05 (and a third year for M04, M06, M17). Proposed for after round 1, so the freeze holds | below |
| basicZ, "53 of 100" | Nothing to change: our files read `basic`; v1 has 62 exact-numeric | n/a |

## What we found while switching

1. **The graph arm refuses the gold filters on 129 of 155 questions.** `graph_backend._check_filters` raises
   `FilterNotSupportedError` for `fiscal_year` and `fiscal_period`; the structured arm accepts and ignores them. Our
   harness no longer sends them: when the gold evidence sits in one filing (136 questions) both arms get
   `{ticker, accession_number}`, which both apply and which is what strict scoring checks; otherwise the ticker, plus
   the form when all needed filings share it (`kpmg_eval/graphrag_filters.py`).
2. **List-valued filters fail on both arms** (13 cross-company questions filter on a list of tickers, which RAG's
   contract allows). The structured arm raises `RetrievalUnavailableError` from a DuckDB cast error, which reads like
   an outage; the graph arm compares a string to a list and returns nothing, silently.
3. **Our store and yours may differ.** For GSv0-MSFT-001 your run puts the nine-month total (241,832) at rank 1. On our
   store (your `fact_loader_v1.py` on Data's copy of the 10-Q, 1,317 facts) rank 1 is a Microsoft 365 product-line row
   (21,883, the prior-year quarter): "three months" matches `MicrosoftThreeSixFive...` members. Same code, so the
   difference is probably the store (EDGAR build vs Data's copy).

## Results so far (evidence level, no reader)

Structured arm, Microsoft Q3 FY2026 10-Q, k = 10 (`scripts/run_graphrag_round1.py --tag eval_local`): needed numbers in
the top 10 for 26/50, prose 0/27, rank-1 right 14/50; 67 questions on other filings skipped because our store holds
one filing. Gold filters and translated filters give the same scores on a one-filing store; the difference shows on
yours. The graph arm is not run: Eval's workspace cannot reach `*.databases.neo4j.io` or `sec.gov` (network allowlist).

## What we need from you

1. **Run round 1 on your side** (the way RAG did): with your Aura variables and the 20-filing store,
   `python scripts/run_graphrag_round1.py --graphrag <your checkout> --tag graphrag_aura` from this folder. It runs
   both arms on all 155 questions, with the gold filters and with translated ones, and writes
   `results/graphrag_round1_graphrag_aura.{json,csv}`. Send those two files (or push them to a branch).
2. **The DuckDB store for the 20 filings**, shared privately: we cannot reach EDGAR or Data's Postgres from here, so we
   cannot build it ourselves. With it we re-run the structured arm on every company and compare stores (finding 3).
3. **Filters:** confirm that callers should send `accession_number` instead of fiscal labels (finding 1), so we tell
   the Agents the same; and either support lists (`IN`) or refuse them with `ValueError` (finding 2).
4. **Exhibit 21:** is PR #34 the `alina/ex21-pipeline` branch? A date for merging it and loading the edges into the
   graph (EV1R-001, EV1R-006 and EV3-001..007 depend on it). Its rows matched our gold reads 62/62.
5. **`hops`** in `data/hops_v2.csv`, starting with the six relationship drafts as you offered.
6. **PR #47** (extraction cost per filing) when it lands; we will add cost to the scorecard.
