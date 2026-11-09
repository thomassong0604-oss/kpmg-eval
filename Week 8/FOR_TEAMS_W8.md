# Week 8 for the other teams

Thank you, RAG and GraphRAG: your retriever and your fact loader both ran here unchanged from your repos, and
GraphRAG's new Exhibit 21 output fed the relationship check. Everything below is evidence-level (no reader model),
re-runs exactly with `python scripts/run_side_by_side.py` and `python scripts/run_messy_wording.py`, and uses the
current 155 Gold Set v2 questions only. Updated 11/9 to your latest commits (RAG main 5bfafeb; GraphRAG main 7bcbdaf
and alina/ex21-pipeline c21fe89); the Part A numbers did not change.

## RAG (KPMG_RAG @ 5bfafeb, main 11/5)
- **Side by side, Microsoft 10-Q (84 questions):** your BM25 search has every needed figure in the top 8 for 49/50 number
  questions and the gold passage for 18/27 prose questions. With the offline LSA stand-in for your dense model, hybrid is
  41/50 and 19/27 (a lower bound: bge cannot be downloaded here). Per question: `results/side_by_side_per_question.csv`.
- **Round-1 corpus:** your `eval/round1_filings.csv` (Data's freeze list) matches our Gold Set v2 filings 21/21. Ask: share
  the round-1 chunks (`data/round1/chunks_C1/chunks.jsonl` or the export CSV, privately, since Data asks that exports stay
  off GitHub) so we can add text anchors for the new questions and run the side by side on all ten companies.
- **Wrong-period figures:** on 33 of 36 number questions with a known distractor, the wrong-period figure (nine months vs
  three, last year vs this) is in the same top 8, because statement tables print both columns. A reader prompt that names
  the period column would help.
- **Relationship questions:** all of them come from Exhibit 21. `rag/ingest.py` reads `primaryDocument` only, and the
  round-1 corpus is Data's report chunks; Data archives Exhibit 21 files but does not chunk them
  (`docs/shortlist-acquisition.md`). Simplest is to let the router send these to GraphRAG. If you do index exhibits as
  separate documents: `rag/chunk.py` drops unlabeled text under 400 characters (`_MIN_GAP_CHARS`), so a short exhibit
  would be skipped.
- **Typos:** misspelled finance words ("revnue", "opertaing") cost BM25 9 of 70 questions (86% → 73%). Name typos cost
  nothing because the company comes in as a filter.
- **Ask:** an API key for the fixed reader, so round 1 scores answers and not only evidence.

## GraphRAG (KPMG-GraphRAG @ 7bcbdaf main 11/8; Exhibit 21 @ c21fe89)
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
