# Week 6: GraphRAG joins, relationship questions, version keys

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 6 starts from the Week 5 pipeline (Gold Set v1, RAG's
real retriever, scorecards) and adds what Eval agreed with GraphRAG on 10/26, in reply to their
[eval-ask.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-ask.md) and
[eval-reply.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-reply.md).

```bash
pip install -r requirements.txt
./scripts/run_all.sh                                        # full pipeline, 57 tests, scorecards
python scripts/run_harness.py --with-relationship-draft     # also run the draft relationship questions
```

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

## Open with RAG (contract v0, requested 10/14; checked against RAG `main` on 10/26)

`trace_id` not in `retrieve()` / `retrieval.jsonl`; `generation.jsonl` drops citations and has no `request_id`; logs carry
only `chunk_ids` (no ticker/form/period/section, no per-`index_version` snapshot); the Agent's `sec_filing_search` tool calls
`retrieve()`, which drops `request_id`, including on empty results; price fields in `config.yaml` are null; `config.yaml`
tickers are still the old pilot set; the Agent tool defaults to `top_k=8` while Eval scores recall@10.
