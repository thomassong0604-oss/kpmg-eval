# Week 6: Data's 10 companies, GraphRAG wiring, RAG anchor review

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 6 starts from the Week 5 pipeline (Gold Set v1, RAG's
real retriever, scorecards) and adds what Eval agreed with GraphRAG on 10/26, in reply to their
[eval-ask.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-ask.md) and
[eval-reply.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-reply.md).

```bash
pip install -r requirements.txt
./scripts/run_all.sh                                        # full pipeline, 63 tests, scorecards
python scripts/run_harness.py --benchmark scope10           # round-1 set: v1 in scope + 49 new 10-company questions
python scripts/run_harness.py --with-relationship-draft     # also run the draft relationship questions
python scripts/run_graphrag_wiring.py --tools mock          # GraphRAG's own mock module (default: Eval's stand-in over its rows)
python scripts/build_deck_w6.py <base.pptx> <out.pptx>      # this week's five Eval slides (base: 10/22 team deck, Eval slide x5)
```

## 10/29 update: scope moves to Data's 10 companies

Data (Emma, 10/28) proposed AAPL, CASY, MCK, MDT, MSFT, MU, NKE, NTAP, PH, TTWO: 21 filings (10 10-Ks, 11 10-Qs).

| Piece | Where | Result |
|---|---|---|
| Which 21 filings | `data/scope10_filings.json` | Data gave counts, not accessions. Eval assumes each company's latest 10-K and 10-Q filed by 2026-10-13, plus the 5 GraphRAG listed (AAPL x3, MSFT x2). That reproduces 10 and 11 exactly; **Data to confirm** |
| Facts | `data/sec_reads/`, `data/scope10_facts.jsonl` | Revenue and net income from the SEC companyconcept API, read twice on 10/29: 53/53 re-reads agree, 18/18 quarterly sums equal the nine-month totals, no conflicting duplicates. Apple FY2024 read once |
| Gold set for round 1 | `data/benchmark_scope10.jsonl` (`scripts/build_scope10.py`) | 139 questions: 90 Gold Set v1 questions kept, 10 retired (need AMZN, META or NVDA; `benchmark_scope10_status.csv`), 49 new `EV2-*` (34 lookups, 2 calculations, 5 ten-company comparisons, 3 fiscal-calendar, 3 unanswerable, 2 false premise). Answers computed in code; text anchors wait for Data's chunks |
| Grader on the new questions | `scripts/run_scope10_grader_check.py` | 156/156 labels right (gold text, restated, x1000 scale error, sign error) after fixing the sig-fig rule for values like 614 and 34.1 |
| What the 21 filings support | `results/scope10_coverage.json` | Single-company lookups and year-over-year: yes. Fiscal years end in 6 months and the latest 10-Qs fall in 3 calendar quarters, so no same-quarter comparison of all ten. No multi-year trends; no 10-K/A, so restatement questions drop |
| Traps found in the SEC data | questions EV2-045 to -049 | Micron's latest 10-K is FY2025; Parker-Hannifin tags net income as ProfitLoss; Take-Two's loss; Nike's and NetApp's Q1 FY2027 10-Q revenue is not under the concept their 10-Ks use |
| Relationship tranche | `data/benchmark_v1_relationship_draft.jsonl` | EV1R-006 (M17) moved to the FY2026 10-K: all 6 now use GraphRAG's 5 filings |

## 10/29 update: GraphRAG wiring and an Eval bug

| Piece | Where | Result |
|---|---|---|
| Both GraphRAG arms in the harness | `kpmg_eval/graphrag_adapter.py`, `scripts/run_graphrag_wiring.py` | Graph arm scored at section/filing level with `contains`; structured arm at XBRL fact level. 87 Microsoft questions, 174 calls, 0 errors; 87/87 pass the 5 contract checks. Runs on Eval's stand-in over the INT-0 mock's rows (`tests/fixtures/graphrag_int0_mock_evidence.json`); `--tools mock` / `--tools real` call GraphRAG's code. Measures plumbing, not the graph |
| **Eval bug fixed** | `kpmg_eval/keys.py` | Fact-level keys ignored XBRL dimensions, so a segment fact ("Intelligent Cloud revenue") matched the gold "total revenue". Keys now carry normalised axis/member (labels and QNames compare equal); 27 segment-vs-total false matches rejected in the wiring run. Week 5 results unchanged |
| Repeated provenance keys | `kpmg_eval/harness.py` | The mock returns two rows with one `section_id`; the citation join now keeps both texts |
| Findings for GraphRAG | `results/graphrag_wiring.json` | Fact `value_num` is in USD millions while the unit is USD; segment members are labels, not QNames; `section_id` not unique per evidence row |

## 10/29 update: review of RAG's Gold v1 anchors (RAG PR #10)

`scripts/review_rag_gold_v1_anchors.py` reads RAG's `eval/gold_v1.jsonl` (snapshot in `data/upstream_snapshots/`, as data) and
checks it against Eval's gold and Eval's copy of the 10-Q as RAG chunks it: 100/100 questions present; 97/99 numbers the
numeric answers use sit in an anchored chunk (49/50 questions); 2 anchors match no chunk (a share-count string from Gold v0 on
GSv0-MSFT-023 and -030); 33 anchors match 4+ chunks (bare numbers); 10 retired questions to drop; 47 rows filter on
ticker + form only.

Gold Set v1 is unchanged: still 100 questions, same file hash (`d584962d6ef6c6b8`), so Week 5 and Week 6 scores compare.
Headline numbers are identical to Week 5 (oracle 1.00 / no-LLM baseline 0.32 / refuse-all 0.00 on numeric accuracy).

## What changed

| Agreed with GraphRAG | Where | Detail |
|---|---|---|
| Citation scoring joins on the provenance key, not `chunk_id` | `kpmg_eval/keys.py` (`provenance_key`), `metrics/citation.py`, `harness.py` | Key is `chunk_id`, else `section_id`, else `metadata.fact_id`, prefixed by arm. GraphRAG results always have `chunk_id = None`; under the old join a graph-only answer looked uncited. Bare RAG chunk ids in AnswerBlocks still work. |
| Reruns key on all three version fields | `keys.py` (`version_key`, `comparable_runs`), `harness.versions()` | Scorecards now record `chunking_version` and `extraction_version` from the evidence returned, next to `index_version`. GraphRAG rebuilds move `extraction_version` only, so comparing on `index_version` alone would hide them. |
| Scores are not comparable across tools | (no code change) | Eval compares by rank, never by raw score across tools. |
| Empty results logged against `trace_id` are fine for round 1 | (no code change) | |
| `contains` anchors normalise whitespace on both sides | `metrics/retrieval.py` | GraphRAG eval-ask, Format §3. |
| GraphRAG evidence uses RAG's field names | `metrics/retrieval.py` (`graph_adapter`) | Reads `accession_number` / `section` as well as the older `accession` / `concept`. |
| `hops` on every question; GraphRAG proposes, Eval reviews | `data/hops_v1.csv` | One row per question (100 + 6 draft), columns `hops`, `proposed_by`, `reviewed_by` left blank for GraphRAG. A sidecar keeps the frozen v1 file and hash unchanged. |

## Relationship tranche, stage 1 (`data/benchmark_v1_relationship_draft.jsonl`)

Built by `scripts/build_relationship_draft.py`. GraphRAG proposed the shapes; Eval wrote the wording and gold.
Run only with `--with-relationship-draft` until the team signs them off.

| qid | GraphRAG shape | Question (short) | Corpus | Status |
|---|---|---|---|---|
| EV1R-001 | M01 | Subsidiaries in FY2026 Exhibit 21; how many outside the US (8; 4, all Ireland) | MSFT FY2026 10-K | needs review |
| EV1R-002 | M04 | Segment changes FY2025 → FY2026 (none; Gaming renamed XBOX, Search and news advertising renamed Search advertising) | MSFT FY2026 10-K | needs review |
| EV1R-003 | M09 | OpenAI investment gains/losses, 9M FY2025 vs FY2026, and the event behind it (Recapitalization dilution gain) | MSFT Q3 FY2026 10-Q | verified, runs now |
| EV1R-004 | M14 | Is LinkedIn Ireland a subsidiary of Activision Blizzard? (not disclosed; invented-edge trap) | MSFT FY2026 10-K | needs review |
| EV1R-005 | M14 variant | "Since Microsoft acquired OpenAI…" (false premise: ~27% equity-method investment) | MSFT Q3 FY2026 10-Q | verified, runs now |
| EV1R-006 | M17 | Segment holding Activision's product line; FY2025 Gaming revenue change (MPC; +$1,952M, +9.1%) | MSFT FY2025 10-K | needs review + corpus merge |

**Verification.** 10-Q items: every anchor and figure is checked by the build script against RAG's chunks of the filing;
the build fails if any is missing. 10-K items: values read from SEC EDGAR on 2026-10-26 (URLs in `SEC_READS` in the
script) and asserted for internal consistency (segments sum to total in every year; FY2025 figures identical in both
10-Ks, so no recast; XBOX = renamed Gaming line with the same figures). They need a second reader and are anchor-checked
once the 10-Ks are in the shared index.

**Not written yet.** M06 (new Item 1A risk factors, FY2025 vs FY2026): Eval could not yet read both Item 1A sections in
full, so the set difference is unverified. M02, M12, M13, M18, M19 and M14 with an Apple subsidiary wait for Data to
confirm the corpus (the merge decision). The M17 MD&A sentence attributing Xbox growth to Activision is GraphRAG's quote
and not yet checked by Eval.

## Open with RAG (contract v0, requested 10/14; rechecked against RAG `main` @ 6f0894a on 10/29: unchanged)

`trace_id` not in `retrieve()` / `retrieval.jsonl`; `generation.jsonl` drops citations and has no `request_id`; logs carry
only `chunk_ids` (no ticker/form/period/section, no per-`index_version` snapshot); the Agent's `sec_filing_search` tool calls
`retrieve()`, which drops `request_id`, including on empty results; price fields in `config.yaml` are null; `config.yaml`
tickers are still the old pilot set; the Agent tool defaults to `top_k=8` while Eval scores recall@10.
