# Eval × GraphRAG: what is done, where it is, what we need

One page for the GraphRAG team (Adeline, Wenyu, Alina, Claudia). Everything is in this folder (`Week 6/`).
Replies to [eval-ask.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-ask.md) and
[eval-reply.md](https://github.com/ZiyiClaudiaWang/KPMG-GraphRAG/blob/main/docs/eval-reply.md).

## Done (your asks from 10/22)

| Your ask | Status | Where |
|---|---|---|
| Citation scoring joins on the provenance key, not `chunk_id` | Done: `chunk_id`, else `section_id`, else `metadata.fact_id` | `kpmg_eval/keys.py` (`provenance_key`), `kpmg_eval/metrics/citation.py` |
| Reruns key on all three version fields | Done: scorecards record `index_version`, `chunking_version`, `extraction_version` | `kpmg_eval/keys.py` (`comparable_runs`), `kpmg_eval/harness.py` |
| Scores not comparable across tools | Agreed: Eval compares by rank, never raw score across arms | none |
| Empty result logged against `trace_id` enough for round 1 | Agreed | none |
| `contains` normalises whitespace both sides | Done | `kpmg_eval/metrics/retrieval.py` |
| `hops` on every question | Sidecar ready for you to fill (we review) | `data/hops_v1.csv` (155 rows) |
| Relationship tranche, Eval writes wording and gold | 6 drafted (M01, M04, M09, M14 + variant, M17), all on your 5 filings this week | `data/benchmark_v1_relationship_draft.jsonl`, built by `scripts/build_relationship_draft.py` |
| Fabricated-relationship check | 2 questions: LinkedIn Ireland "owned by" Activision (EV1R-004); "since Microsoft acquired OpenAI" (EV1R-005) | same file |

## Your tools in our harness

- `kpmg_eval/graphrag_adapter.py`: turns `graph_search` and `structured_search` evidence into Eval keys. Graph arm is scored
  by section and `contains` text; structured arm by XBRL fact (concept, period, unit, dimensions).
- `scripts/run_graphrag_wiring.py`: runs every in-scope Microsoft question through both arms. Results:
  `results/graphrag_wiring.json`. 87 questions, 174 calls, 0 errors; 87/87 pass the 5 checks we join on
  (trace_id echoed, one provenance key, provenance resolves, extraction_version, fact concept + period).
  - `--tools fixture` (default): Eval's stand-in over your INT-0 mock's rows (`tests/fixtures/graphrag_int0_mock_evidence.json`)
  - `--tools mock`: imports your `mock/mock_retrieval_tools.py`
  - `--tools real`: calls `graphrag.retrieve` once you register a backend
- This measures the plumbing on the mock's rows, not the graph.

## Three findings from your mock output

1. Structured-arm `value_num` is in USD millions (82,886) while the unit is `iso4217:USD`. Please return the value in the XBRL
   unit, or add a scale field.
2. Segment members are labels (`"Intelligent Cloud"`), not XBRL members (`msft:IntelligentCloudMember`). Eval normalises both
   for now; please carry the member name.
3. Two graph rows share `section_id` `sec-msft-26q3-note16`. Citation scoring needs one id per evidence row (our harness keeps
   both texts for now).

## Scope update (Data's 10 companies)

- Round-1 gold set: `data/benchmark_scope10.jsonl` (139 questions). Facts for the 8 added companies: `data/scope10_facts.jsonl`.
- Your 5 filings (AAPL ×3, MSFT ×2) are all in it. The relationship tranche only uses the MSFT Q3 FY2026 10-Q and FY2026 10-K.
- For stage 2 (M02, M18, M14 with another company), Exhibit 21 from the other 10-Ks is the input; tell us which you clean first.

## What we need from you before round 1 (W8)

1. Proposed `hops` values in `data/hops_v1.csv` (and one definition of a hop: edges traversed, or filings crossed?)
2. A date for a real backend behind `graphrag.retrieve`
3. The three fixes above
4. Review of the 6 draft relationship questions (wording, graph path)
