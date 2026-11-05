# Week 8 for the other teams

Thank you, RAG and GraphRAG: your retriever and your fact loader both ran here unchanged from your repos, which is what
made the side-by-side possible this week. Everything below is evidence-level (no reader model), re-runs exactly with
`python scripts/run_side_by_side.py` and `python scripts/run_messy_wording.py`, and uses the current 155 Gold Set v2
questions only.

## RAG (KPMG_RAG @ 11f8b42)
- **Side by side, Microsoft 10-Q (84 questions):** your BM25 search has every needed figure in the top 8 for 49/50 number
  questions and the gold passage for 18/27 prose questions. With the offline LSA stand-in for your dense model, hybrid is
  41/50 and 19/27 (a lower bound: bge cannot be downloaded here). Per question: `results/side_by_side_per_question.csv`.
- **Wrong-period figures:** on 33 of 36 number questions with a known distractor, the wrong-period figure (nine months vs
  three, last year vs this) is in the same top 8, because statement tables print both columns. A reader prompt that names
  the period column would help.
- **Relationship questions:** all of them come from Exhibit 21, which `rag/ingest.py` does not index (it reads
  `primaryDocument` only). Either index exhibits or let the router send these to GraphRAG. If you index exhibits as
  separate documents: `rag/chunk.py` drops unlabeled text under 400 characters (`_MIN_GAP_CHARS`), so a short exhibit
  would be skipped.
- **Typos:** misspelled finance words ("revnue", "opertaing") cost BM25 9 of 70 questions (86% → 73%). Name typos cost
  nothing because the company comes in as a filter.
- **Ask:** an API key for the fixed reader, so round 1 scores answers and not only evidence; index the other 8 companies.

## GraphRAG (KPMG-GraphRAG @ 1980a79, demo/walkthrough)
- **How we ran it:** `structured/fact_loader_v1.py` on Data's copy of the 10-Q (1,317 facts, offline with
  `--filing-date/--form/--company-name`), then `structured_search(question, {ticker, accession_number}, top_k=8)`.
- **Result:** the needed facts are in the top 8 for 25/50 number questions. Where it hits, the evidence is precise: the
  wrong-period figure appears on 19 of 36 (RAG: 33 of 36).
- **Where the 25 misses come from** (`results/side_by_side.json` → `number_miss_diagnosis`), each with a fix:
  - 13 are in your top 50 but ranked below 8. Example: "Microsoft's total revenue for the three months ended March 31,
    2026" ranks the total (82,886) 10th, because the word "Microsoft" also matches the Microsoft 365 product-line members
    (score 1.05 vs 1.0 for the total). Suggest: undimensioned totals first unless the question names a segment or product.
  - 10 are calculations whose inputs are different concepts; one call cannot fetch them all. One call per input (or the
    Agents splitting the question) would.
  - 2 are wording: "current unearned revenue" (ContractWithCustomerLiabilityCurrent) and "repurchasing common stock"
    (PaymentsForRepurchaseOfCommonStock) do not reach their concepts. Two aliases fix them.
- **Relationship questions:** in your agreed shape (Company OWNS Subsidiary, ontology decision 2.6), all 9 Exhibit 21
  questions are answered exactly by traversal. We loaded our own Exhibit 21 reads into that shape, so this is the design,
  not your production graph. Ask: load the ten companies' Exhibit 21, and share a Neo4j endpoint so we can score the
  graph arm itself (it needs Neo4j, and the committed claims cover FY2025 10-Ks only).

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
- Ask: chunks for the 21 filings, so we can add text anchors to the new questions before round 1.
