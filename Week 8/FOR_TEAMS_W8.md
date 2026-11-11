# Week 8 for the other teams

Thank you, RAG and GraphRAG: your retriever and your fact loader both ran here unchanged from your repos, and
GraphRAG's new Exhibit 21 output fed the relationship check. Everything below is evidence-level (no reader model),
re-runs exactly with `python scripts/run_side_by_side.py` and `python scripts/run_messy_wording.py`, and uses the
current 155 questions only. Updated 11/9 to your latest commits (RAG main 5bfafeb; GraphRAG main 7bcbdaf and
alina/ex21-pipeline c21fe89), and rescored on Gold Set v2.1 (same questions and answers, corrected text anchors; see
the round-1 section below). Updated 11/11 with RAG's end-to-end run and **Gold Set v2.2** (grading fixes, next section).

## Round 1 end to end (RAG's reader, 11/11): thank you, reproduced, and three fixes
- **Reproduced exactly.** With RAG's answer blocks and our graders, we get RAG's figures on RAG's subset (no graph-route,
  no review-required questions): numbers 87/93 = 0.935, balanced refusal 0.977, unanswerable 10/10. On all 155: numbers
  87/94 = 0.926 on v2, **89/94 = 0.947 on v2.2**; balanced refusal 0.944; unanswerable 12/12; fiscal-calendar and list
  answers 5/12; false premise corrected 6/7. `results/answers_rag_reader_round1.json` (scores) and
  `_per_question.csv` (labels); the answers themselves stay private.
- **Citations, checked in RAG's chunks:** all 185 cited chunk ids exist; every answer cites a filing the gold answer
  uses (127/127); 58 of 59 lookups show the number in a cited chunk (EV1-012 computes 50,924 from two cited figures
  instead of quoting the balance-sheet line, which is fine but worth knowing).
- **RAG's three notes, all right, fixed in Gold Set v2.2:** (1) the sig-fig floor is now the precision the filing prints
  (EV1-015 "$0.91", and EV1-027); (2) the 7 multi-part questions carry `gold.values` and need every figure, read from an
  optional AnswerBlock `values` list (sign-sensitive) or else from the answer text, so EV1-043 now passes as written;
  (3) EV1R-002 and EV1R-006 route to text (GraphRAG's review agrees).
- **What RAG's files showed us:** EV1R-005's 10-K says "an approximate 25% interest" in OpenAI where the 10-Q says
  27 percent, so both count now; v2.1 put two anchor sentences in one evidence item, which RAG's chunker splits (8
  questions), so v2.2 has one item per point, and every anchor outside Exhibit 21 and NetApp's 10-Q is in RAG's chunks;
  our false-premise grader missed "was not profitable" and "did not acquire" (fixed).
- **Why 16 answerable questions were declined:** 7 need Exhibit 21 (GraphRAG's route); 3 need NetApp's 10-Q, which
  Data holds for review (a tagging defect in NetApp's filing); 3 are cross-company rankings; 2 state the answer but are marked `answered: false` (GSv0-MSFT-023,
  EV1R-005); 1 retrieval miss (GSv0-MSFT-019).
- **Narrative answers (28 of 30 answered):** `scripts/run_narrative_judge.py` judges each required point (stated /
  missing / contradicted, with a quote that must appear in the answer) and flags claims no cited chunk supports.
  `--dry-run` shows the exact prompts without a key. It counts only after it agrees with our hand labels.

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
  "46,309" (Nike revenue), read from the SEC-rendered income statements and now confirmed in your chunks.
  EV2-035/036/037/044 are anchored from `chunks_C1` in Gold Set v2.2.
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
- **Round-1 corpus:** your `eval/round1_filings.csv` (Data's freeze list) matches our Gold Set v2 filings 21/21. Thank you
  for `chunks_C1` and the answer blocks: both stay in git-ignored `private/` (Data asks that exports stay off GitHub).
  `chunks_C1` has 20 filings; NetApp's 10-Q (0001193125-26-380207) is not in it because Data holds it for review
  (NetApp tagged its opening cash a day late; Data `docs/ntap-source-review.md`). That is why EV2-026, EV3-008 and
  EV3-009 were declined, by every team.
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
- **Asks:** run `scripts/run_narrative_judge.py` with your key (or lend one for the run); set `answered: true` when the
  text states the figure (GSv0-MSFT-023, EV1R-005); optionally add a `values` list to answer blocks for multi-part questions.

## GraphRAG (KPMG-GraphRAG @ 21f0795 main 11/11, #70; Exhibit 21 @ c21fe89)
- **Your round 1 (11/11): thank you, and reproduced.** Structured arm on all 20 filings, translated filters: needed
  number in the top 10 for 63/93, rank 1 right on 26/93. Graph arm, scored for the first time: prose anchors 10/38.
  Our rerun on your store matches your structured arm on all 155 questions. Details and the GSv0-MSFT-001 answer (the
  gold wording ties Microsoft 365 rows at 1.05, so rank 1 is unstable; not the store) in
  [`EVAL_GRAPHRAG_W8.md`](EVAL_GRAPHRAG_W8.md).
- **#70 confirmed:** gold filters now run with 0 errors on the structured arm; lists work, so multi-filing questions
  get lists of tickers and accessions.
- **Asks:** re-run the graph arm on Gold Set v2.2 with #70 (`--tag graphrag_aura_v2_2`); push the filled hops (149 of
  155); for #68, a deterministic tie-breaker and no non-numeric facts on number questions.
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
  tool reaches 94.8% (it misses only the 8 questions that need no tool) at 3 calls per question; the keyword router 82.6%
  at about 1 (83.9% on v2: EV1R-002 and EV1R-006 moved from graph to text in v2.2 after RAG's round 1).
- **AnswerBlock `values` (optional, proposed 11/11):** for questions that ask for several figures, list each one as
  `{"label", "value", "unit", "value_text"}`; we grade them sign-sensitive. Without it we read the figures from the answer
  text. `value` stays the headline figure (`kpmg_eval/answer_schema.py`).
- **Always send the ticker** (and the accession when known): without a ticker filter, GraphRAG's top fact for a
  Microsoft question comes from Medtronic's 10-Q. GraphRAG confirmed `{ticker, accession_number}` is the call shape.
- **Grading your answers:** `python scripts/grade_answer_blocks.py --answers your_blocks.jsonl --tag agents` gives the same
  scorecard RAG's reader got (numbers, refusal, premise, fiscal/list answers, citations with `--chunks`).
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

## Data (data_engineering_kpmg @ 7040b8a, 11/11)
- Your freeze list (`round1_filings.csv` in RAG's repo) matches our 21 filings exactly. Round 1 has now run on both
  retrievers, on 20 of them: NetApp's 10-Q stays out while it is review-required (opening cash tagged April 25 instead
  of April 24; your `docs/ntap-source-review.md`), which explains 3 declined questions for every team. Thank you for
  documenting it.
- GraphRAG's store is built from your Postgres (`corpus_version` data-api-raw:20, 24,533 facts); Eval uses a copy
  GraphRAG shared, kept out of the repo. We have no database credentials and need none for now.
- **Joint ask with GraphRAG, now that round 1 has run:** load Microsoft's FY2024 and FY2025 10-Ks (draft in
  `COMMS_W8.md`).
