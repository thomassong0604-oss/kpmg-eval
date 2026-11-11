# Week 8 for the other teams

Thank you, RAG and GraphRAG: your retriever and your fact loader both ran here unchanged from your repos, and
GraphRAG's new Exhibit 21 output fed the relationship check. Everything below is evidence-level (no reader model),
re-runs exactly with `python scripts/run_side_by_side.py` and `python scripts/run_messy_wording.py`, and uses the
current 155 questions only. Updated 11/9 to your latest commits (RAG main 5bfafeb; GraphRAG main 7bcbdaf and
alina/ex21-pipeline c21fe89), and rescored on Gold Set v2.1 (same questions and answers, corrected text anchors; see
the round-1 section below).

## Round 1 (RAG's run, 11/9): thank you, and what we fixed
- RAG ran our scoring on Gold Set v2 against its 20-filing index: hybrid with filters finds all evidence for 105/124 scored
  questions at k = 10 (numbers 83/93, prose 22/31); the nine other companies' single-company questions score 34/37.
  Transcribed in `data/round1_rag_2026-11-09.json`.
- **You were right about GSv0-MSFT-019/021/027/029.** Their anchors came from Gold v0's automatic "region" conversion
  and do not match the questions. The same conversion produced 22 anchors in all, so we replaced all 22 with the sentence
  or figure that supports each required point, exactly as the 10-Q prints it (`data/anchor_review_w8.json`, applied by
  `scripts/build_gold_v2_1.py`; each string checked against the filing and your chunker's output). That is **Gold Set
  v2.1** (`data/benchmark_v2_1.jsonl`, sha256 `1e104c626c6c9833`); questions and answers are identical to v2, so only
  the prose anchors need rescoring. Old and new anchors per question: `results/gold_v2_1_changes.json`.
- **Your 7 unanchored questions:** EV2-041 and EV2-048 get "298.2" (Take-Two's net loss) and EV2-049 gets "46,398" and
  "46,309" (Nike revenue), read from the SEC-rendered income statements; please tell us if your chunks print them
  differently. EV2-035/036/037/044 need fiscal-calendar wording from the filings, so we will anchor them as soon as we
  have `chunks_C1.jsonl`.
- **The one row label still missing** from our 37 fixes: every "add the table row label" item is now spelled out in
  `data/anchor_review_w8.json` (`row_labels`). For operating income the label does not narrow anything: all 4 chunks with
  38,398 or 114,634 show total operating income, so any of them is valid evidence.
- The 3 cross-company rankings and 3 derived 10-K + 10-Q questions are routing work for the Agents (one search per
  company or form); our expected routes already send them to finance data.

## RAG (KPMG_RAG @ 5bfafeb, main 11/5)
- **Side by side, Microsoft 10-Q (84 questions):** your BM25 search has every needed figure in the top 8 for 49/50 number
  questions and the gold passage for 22/27 prose questions (18/27 on v2's anchors). With the offline LSA stand-in for your
  dense model, hybrid is 41/50 and 23/27 (a lower bound: bge cannot be downloaded here). Per question:
  `results/side_by_side_per_question.csv`.
- **Round-1 corpus:** your `eval/round1_filings.csv` (Data's freeze list) matches our Gold Set v2 filings 21/21. Ask: share
  `chunks_C1.jsonl` and the per-question results privately (Data asks that exports stay off GitHub), so we can anchor the
  last 4 questions, check your results against v2.1, and run the side by side on all ten companies.
- **Wrong-period figures:** on 33 of 36 number questions with a known distractor, the wrong-period figure (nine months vs
  three, last year vs this) is in the same top 8, because statement tables print both columns. A reader prompt that names
  the period column would help.
- **Relationship questions:** all of them come from Exhibit 21. `rag/ingest.py` reads `primaryDocument` only, and the
  round-1 corpus is Data's report chunks; Data archives Exhibit 21 files but does not chunk them
  (`docs/shortlist-acquisition.md`). Simplest is to let the router send these to GraphRAG. If you do index exhibits as
  separate documents: `rag/chunk.py` drops unlabeled text under 400 characters (`_MIN_GAP_CHARS`), so a short exhibit
  would be skipped.
- **Typos:** misspelled finance words ("revnue", "opertaing") cost BM25 8 of 70 questions (91% → 80%). Name typos cost
  nothing because the company comes in as a filter.
- **Ask:** an API key for the fixed reader, so round 1 scores answers and not only evidence.

## GraphRAG (KPMG-GraphRAG @ 4e89acb main 11/11; Exhibit 21 @ c21fe89)
- **Your 11/11 reply is answered point by point in [`EVAL_GRAPHRAG_W8.md`](EVAL_GRAPHRAG_W8.md):** harness on
  `graphrag.backends`; dims list/dict fixed; hops split adopted (`data/hops_v2.csv`, `filings` filled by Eval); M17
  already reworded; M08 as an abstention candidate; the graph arm refuses fiscal labels on 129 questions, so we send
  `accession_number`; list-valued filters fail on both arms; please run `scripts/run_graphrag_round1.py` with Aura.
- Earlier this week (Part A on 7bcbdaf; unchanged on 4e89acb):
- **How we ran it:** `structured/fact_loader_v1.py` on Data's copy of the 10-Q (1,317 facts, offline with
  `--filing-date/--form/--company-name`), then `structured_search(question, {ticker, accession_number}, top_k=8)`.
- **Result:** the needed facts are in the top 8 for 25/50 number questions (the same on 1980a79 and on main after your
  11/5 concept-matching changes). Where it hits, the evidence is precise: the wrong-period figure appears on 19 of 36
  (RAG: 33 of 36).
- **Where the 25 misses come from** (`results/side_by_side.json` → `number_miss_diagnosis`), each with a fix:
  - 13 are in your top 50 but ranked below 8. In 6 of them the cause is a period word: "three months" / "six months"
    matches Microsoft's "Microsoft 365" members (`msft:MicrosoftThreeSixFive...`), so those rows score 1.05 and the
    consolidated total (1.0) drops out; "total revenue for the three months ended March 31, 2026" ranks 82,886 10th.
    Suggest: treat three/six/nine/twelve months as period words and skip them when matching dimension members.
  - 10 are calculations whose inputs are different concepts; one call cannot fetch them all. One call per input (or the
    Agents splitting the question) would.
  - 2 are wording: "current unearned revenue" (ContractWithCustomerLiabilityCurrent) and "repurchasing common stock"
    (PaymentsForRepurchaseOfCommonStock) do not reach their concepts. Two aliases fix them.
- **Exhibit 21 (thank you):** your `ex21_pipeline/output/graph_edges.csv` covers all ten companies' snapshot 10-Ks. It
  agrees with our gold reads on all 62 rows we have (Apple 19, Casey's 9, Micron 21, Microsoft 8, NetApp's 5 Israel rows),
  names and jurisdictions. Traversing your rows answers all 9 Exhibit 21 questions exactly (in memory here, since we cannot
  reach Neo4j). Ask: merge the pipeline into main, load it into the graph, and share a Neo4j endpoint so we can score the
  graph arm itself.

## Agents
- **Score your orchestrator on our routing questions (new 11/11):** `python scripts/run_routing_baselines.py --router
  orchestrator=your_module.py:route` (a function `route(question, session_ticker)` returning tool names), or `--calls
  orchestrator=calls.jsonl` from your logs (`{"qid": ..., "tools": [...]}` per line). Tool names like
  `sec_filing_search`, `graph_search`, `structured_search` are mapped for you. You get coverage, calls per question and
  unneeded calls next to our three baselines. The keyword router is only a baseline; it is not part of the pipeline.
- **Coverage is not accuracy:** the routing bars show the share of questions whose needed tools were called. Every
  tool reaches 94.8% (it misses only the 8 questions that need no tool) at 3 calls per question; the keyword router 84%
  at about 1.
- **Routing slide fixed:** axes labelled, keyword router defined, and unneeded calls defined (`ROUTING_EXAMPLES.md`).
  To correct the 11/5 minutes: an unneeded call is a tool called that the question's expected route does not need, averaged
  over all 155 questions. It does not mean "text search alone could have answered".
- **Demo walkthrough:** seven worked examples in `ROUTING_EXAMPLES.md`, including two where rules break ("What does revenue
  allocated to remaining performance obligations include?" is a text question that the word "revenue" sends to finance data).
- **Messy wording:** with no company picked in the UI, a name check that knows exact names only gets 19% of decisions right
  on misspelled names and 9% on casual wording with tickers (most become "which company?"). Adding tickers and near-miss
  spellings (`companies_in_fuzzy` in `scripts/run_messy_wording.py`) brings it to 94% and 79%, with no change on the clean
  questions (172/179 either way).
- **Abstaining:** neither retriever returns an empty result on the 7 unanswerable Microsoft questions, so the decision to
  abstain has to come from your evidence check.
- **Ask:** run your orchestrator through `scripts/run_routing_baselines.py`; review our expected routes.

## Data
- Your freeze list (`round1_filings.csv` in RAG's repo) matches our 21 filings exactly. Ask: keep it fixed through round 1.
