# Eval × GraphRAG, week 8: what we did with your 11/11 replies, and what we still need

**Latest (11/14): your ranking changes re-scored. Rank 1 is right on 60 of 93 number questions, up from 26.**
Newest first below.

## Your #72 and #76 (main a1e7cf7, 11/13): re-scored on your store

Same store (20 filings, 24,533 facts), same 155 questions (Gold Set v2.2), same script, translated filters, top 10.
Before is main `21f0795` (#70), the commit round 1 was presented on.

| Measure (structured search) | 21f0795 (11/11) | a1e7cf7 (11/13) |
|---|---|---|
| Rank 1 is the needed figure | 26/93 | **60/93** |
| A known wrong figure at rank 1 | 5/42 | **2/42** |
| Needed figures in the top 10 | 63/93 | 63/93 |
| Prose (not this arm's job) | 0/40 | 0/40 |

- This matches the 64.5% in your #72 (60/93). **34 questions gained rank 1 and none lost it.** Lookups went from
  14/52 to 41/52. (With the gold filters as written the figure is 59/93: our tighter tolerance, below, no longer
  counts EV1-004.)
- Still open at rank 1 (12 questions have the figure in the top 10 but not first): EV1-004, EV1-009, EV1-011, EV1-017,
  EV1-024, EV1-034, EV1-038, EV1-039, EV2-013, EV2-029, EV2-045, GSv0-MSFT-001. Two put a known wrong figure first:
  **EV1-004** (basic EPS 4.28 ahead of diluted 4.27) and **EV1-011** (long-term debt: not the non-current portion at
  3/31/2026).
- The 30 questions with no needed figure in the top 10 are unchanged: mostly calculations that need several facts
  from one call, and three cross-company rankings. Per question: `results/graphrag_rescore_a1e7cf7.json`.
- **A correction on our side.** Our number matching allowed a difference of 0.5 for every value. That is right for
  amounts in dollars, too loose for per-share figures and rates. It is now half a cent below 100. Three questions are
  affected (EV1-004, EV1-015, EV1-016). None of your round-1 scores changes. One figure we sent you on 11/11 does: on
  our Microsoft 10-Q store, rank 1 was a known wrong figure on 5 of 36, not 6 of 36 (EV1-015).
- Not re-scored yet: the graph arm (needs your Aura run) and Exhibit 21 (#75 is merged as a pipeline; we will score
  it once the edges are in the graph you serve).

**Earlier (11/11 evening): hops PR #71 merged into our sheet; your graph arm's prose score is mostly a scope
question.**

## Your third reply (11/11, 5:04 PM): hops PR #71, EV1R-001, a dropped connection

| Your point | What we did |
|---|---|
| Hops in PR #71 (7928d89, `tools/fill_hops.py`) | Merged into `data/hops_v2.csv` (your file kept as `data/hops_v2_graphrag_pr71.csv`; the first one stays as history). Thank you for deriving it in code. 155 rows, none held: hops on 44 questions, blank on the XBRL questions on purpose |
| 1. EV3-008/009 noted | Thanks. One thing remains on these two (below) |
| 2. False premises fixed | Confirmed: all five now take their route's support |
| 3. EV1R-001: Exhibit 21 is outside your section scope | Thank you for checking the live graph. Now blocked like the other Exhibit 21 rows |
| EV3-007 "Failed to read from defunct connection" (Aura free tier) | Agreed, not an arm failure. `run_graphrag_round1.py` now retries a dropped connection (`--retries 3`), and one that persists is reported as `infra_errors`, apart from arm `errors`. Errored calls were already left out of every rate |

**Your section scope explains most of the graph arm's prose score.** With anchors placed by RAG's chunk sections
(`results/anchor_check_c1.json`), the 38 prose questions in your round 1 split three ways
(`results/graphrag_round1_check.json`):

| Where the answer's text sits | Questions | Graph arm found it |
|---|---|---|
| Inside your five section types (10-K Items 1, 1A, 7; 10-Q Items 2, 1A) | 20 | **10** |
| Only outside them (mostly the notes to the statements, 10-Q Item 1) | 10 | 0 |
| Not in the corpus or the chunks (Exhibit 21; NetApp's 10-Q) | 8 | 0 |

So the 26% headline is 50% on what the graph holds. Adding the notes to the statements (10-Q Item 1, 10-K Item 8)
would put 10 more prose questions within reach (GSv0-MSFT-006, 007, 008, 009, 011, 012, 028, 029, 030, EV1-047).

**The same scope rule applies to some hops rows** (`eval_check`): 10 text questions marked "yes" through the claim path
have their answer only in the notes, so support today is no; EV3-008/009 are NetApp's 10-Q, which is not in the
20-filing corpus (Data holds it for review), so also no; EV1R-005's "no" is right, but because the correcting text is
in the notes, not because it is XBRL.


## Your round 1 (11/11, second reply): checked

Files: `results/graphrag_round1_graphrag_aura.json` and `.csv` (yours, as received; host and local path removed),
`results/graphrag_round1_eval_store20*` (our rerun), `results/graphrag_round1_check.json`
(`scripts/check_graphrag_round1.py`). Pinned: GraphRAG main @ 21f0795 (#70). Your store stays in git-ignored
`private/` (a Data export): 20 filings, 24,533 facts, `corpus_version` data-api-raw:20.

| Your point | What we found or did |
|---|---|
| 1, 3. Round 1, both arms | Structured arm, translated filters: needed number in the top 10 for 63/93, rank 1 right 26/93, wrong period at rank 1 5/42. Graph arm, scored for the first time: prose anchors 10/38, numbers 5/94; returned nothing on 3/19 unanswerable or false-premise questions. **Our rerun of the structured arm on your store matches yours on 155/155 questions** |
| 2. The store and GSv0-MSFT-001 | Not the store. On both stores the gold wording puts Microsoft 365 product rows at the top, all scored 1.05 (tied), because "three months" matches `MicrosoftThreeSixFive` members; which tied row is first changes with `top_k` (74,083 at k = 3, 21,883 at k = 10). "Quarter ended" wording gives 241,832 at rank 1, the figure you saw, and it is the nine-month total. Part A on your store: numbers 24/50 (ours 25/50); the one change is EV1-015, where a date fact outranks the dividend per share. 14 of 84 rank-1 facts differ between stores, almost all ties ordered differently. Your store holds 1,511 facts for the Microsoft 10-Q, ours 1,317 |
| 4. #70 (lists as IN; ValueError) | Confirmed: gold filters now run with 0 errors on the structured arm (10 at 4e89acb, all list-ticker questions) and give the same 63/93 as translated |
| 5. Graph arm ignores fiscal labels | In #70. Our compatibility report now shows both behaviours (refused at 4e89acb, ignored at 21f0795). Only you can confirm the graph arm's gold-filter run: please re-run it (below) |
| 6. Send `{ticker, accession_number}` | Adopted, and FOR_TEAMS tells the Agents the same. Multi-filing questions (11) now get lists of both, an IN on both arms |
| 7. Exhibit 21 (PR #34) after midweek | Fine. The 9 Exhibit 21 questions keep their traversal score on your edges (9/9) until Subsidiary nodes are in Aura |
| 8. hops (file received 11/11) | Merged into `data/hops_v2.csv` unchanged (your file kept as `data/hops_v2_graphrag_2026-11-11.csv`): hops on 43 questions (3 on 33: Company -FILES-> Filing -CONTAINS-> Section -SUPPORTS-> Claim; 1 on 9; 2 on EV3-002), blank on the 95 XBRL questions on purpose, as you explain. Agreed, writing 2 would claim a walk your graph cannot make. Since the ontologies differ, the sheet keeps both: your `hops` and our `eval_reference_edges` (EV3-002: 2 vs 4, because our gold path has a Jurisdiction node and yours has country as a property on Subsidiary). That is an ontology difference, not a counting one. Our checks are in `eval_check`: EV3-008/009 were our mistake (we labelled two NetApp fiscal-label questions 'relationship', which pointed your derivation at Exhibit 21; relabelled in v2.2); 5 false-premise questions are answerable; EV1R-001 'yes' vs blocked |
| 9. Data | Agreed; the joint ask for Microsoft FY2024 and FY2025 is in `COMMS_W8.md` |

**For #68 (ranking), from these runs:** (1) ties are common and their order is not stable, so add a deterministic
tie-breaker (period match first, then facts without dimensions); (2) non-numeric facts (dates, text blocks,
enumerations) reach rank 1 on number questions (EV1-015 on your store), so drop them when the question asks for a
number; (3) with no ticker filter, the top fact for a Microsoft question comes from Medtronic's 10-Q, so callers must
always send the ticker.

**Next from you:** re-run the graph arm with #70 on Gold Set v2.2 (`--tag graphrag_aura_v2_2`; v2.2 adds anchors for
4 questions, so graph prose goes from 38 to 42). Credentials: not needed, since the store came as a
file. As the Neo4j password went into the channel, rotating it may be worth it.

**Hops: 6 rows to look at** (`eval_check` in `data/hops_v2.csv`). Answered in your third reply and PR #71 (above):
- EV1-068, EV1-069, EV1-070, EV2-048, EV2-049 are false-premise questions, so they are answerable: the answer must
  state the correct figure or fact (Microsoft's revenue rose; Take-Two's net loss of 298.2). Their support is the
  same as their route's: no for the four XBRL ones, and the claim path for EV1-070 ("Microsoft Cloud is not a
  segment").
- EV1R-001 is 'yes' through claims, while the Exhibit 21 rows (EV3-*) are blocked and your first review said "not yet".
  Does the graph hold Microsoft's Exhibit 21 list as claims?
- EV3-008 and EV3-009 need no change from you. They are NetApp fiscal-label questions, and our gold labelled their
  pattern "relationship", which led to the OWNS path. Fixed in Gold Set v2.2 (`fiscal_label`).

## Your first 11/11 reply

Answers GraphRAG's first "Reply to Eval, week 8" (11/11; markdown version `docs/eval-reply-w8.md` on branch
`docs/eval-reply-w8`). Thank you: the real tools, the filter fix, the Exhibit 21 output and the period warning all
landed in time for round 1. Everything below is in this folder and re-runs with `./scripts/run_all.sh` (87 tests).
Pinned: GraphRAG main @ 4e89acb (11/11), Exhibit 21 branch @ c21fe89.

## Done on our side

| Your point | What we did | Where |
|---|---|---|
| §1 Switch off the mock: import `graphrag.backends` | `load_tools(mock=False)` now imports `graphrag.backends` (falls back to `graphrag.retrieve` on older checkouts); `backend_status()` reports `configure_from_env()`. The side-by-side calls your structured arm this way | `kpmg_eval/graphrag_adapter.py`, `scripts/run_side_by_side.py` |
| §1 Filter fix (PR #65) | Confirmed on our store: the gold filter shape `{ticker, form, fiscal_year, fiscal_period}` now runs on the structured arm with no error. We note in our docs that `fiscal_year`, `fiscal_period`, `section`, `is_table` are accepted and **not applied** | `kpmg_eval/graphrag_filters.py` |
| §1 Period matcher | Measured: on the Microsoft 10-Q, the rank-1 fact is the needed value for **14/50** number questions and a known wrong-period value for **5/36** (we first wrote 6/36; corrected 11/14, see the top of this file). Now reported on every run (`top1_right`, `top1_wrong_period`) | `results/side_by_side.json`, `results/graphrag_round1_eval_local.json` |
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
