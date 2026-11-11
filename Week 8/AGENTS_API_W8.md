# Eval × Agents: API v0.2 into the evaluation pipeline (11/11)

Answers the Agents' "KPMG Agentic Backbone – API Contract v0.2" (11/11; branch `feature/api-integration-v02`, PR #10).
Thank you: `trace_id`, the RAG `evidence_status` envelope and the two fallback flags are exactly what Eval needs to
score the fallback. Every field below plugs into our pipeline as it is; nothing in v0.2 has to change first.

## How a run plugs in

```bash
python scripts/run_agent_api.py --base-url <API> --tag agents_v02                 # 155 questions -> private/agent_responses_agents_v02.jsonl
python scripts/grade_agent_run.py --responses private/agent_responses_agents_v02.jsonl --tag agents_v02
#   -> results/agent_run_agents_v02.json, _per_question.csv
python scripts/run_agent_api.py --base-url <API> --tag agents_v02_off --extra '{"disable_fallback": true}'   # case 4, once a switch exists
python scripts/grade_agent_run.py --responses private/agent_responses_agents_v02.jsonl --baseline private/agent_responses_agents_v02_off.jsonl --tag agents_v02
python scripts/run_agent_api.py --base-url <API> --tag agents_rescue --only rescue,answer_in_rag_evidence      # one case at a time
```

Requests send `trace_id = "<tag>:<qid>"` (the API keeps a given trace_id, so each response maps back to its question)
and `top_k = 10`, as in the rest of round 1 (the contract's default is 8). Responses stay in git-ignored `private/`:
their evidence holds filing text from Data's corpus. Our workspace cannot reach outside hosts, so for now the Agents run
the first script and send the file.

## Field by field

| v0.2 field | What Eval does with it | Where |
|---|---|---|
| `trace_id` | Maps the response to its question (`<tag>:<qid>`; falls back to the exact question text) | `kpmg_eval/agent_api.py` |
| `status` | Decision: SUCCESS on answerable questions, NO_EVIDENCE on unanswerable ones, balanced over both. ERROR is listed and not scored | `grade_agent_run.py` |
| `evidence_status`, `weak_reasons` | Fallback analysis by status and by reason; how often the final evidence holds the answer when status is `ok` and no fallback ran | same |
| `fallback_triggered`, `fallback_used` | Trigger rate, used rate, and the four cases below | same |
| `filters` | Query understanding vs the gold filters, key by key. Same keys and value formats as ours (`ticker`, `form`, `fiscal_year` 2026, `fiscal_period` "Q3") | `agent_api.filters_match` |
| `evidence[].text` | Is the needed figure (numbers) or every text anchor (prose) in the final evidence; is a wrong-period figure shown. Same rule as the RAG vs GraphRAG side by side | `run_side_by_side.score_rag` |
| `citations[].source_url` | Accession read from the EDGAR path, checked against the filings the gold answer uses | `agent_api.accession_from_url` |
| `logs`, `error` | Kept for tracing; not scored | |
| `answer` (null in v0.2) | When it lands: numbers, premise, narrative and refusal graded with the same grader as RAG's reader (`grade_answer_blocks.py`) | |

## Your four cases, and which questions to run

Each Gold Set v2.2 question already has the case it tests, from round 1 (`data/fallback_cases_w8.csv`,
`scripts/build_fallback_cases.py`: RAG's reader, GraphRAG's structured arm on its 20-filing store, its graph arm):

| Expected case | Questions | Expected from /query |
|---|---|---|
| keep: RAG already answers | 127 | SUCCESS; a fallback here is extra cost, and must not break the answer |
| rescue: RAG declined, a GraphRAG arm had the evidence | 1 (GSv0-MSFT-019) | fallback used, SUCCESS |
| answer_in_rag_evidence: RAG's evidence had it, the reader declined | 2 (GSv0-MSFT-023, EV1R-005) | SUCCESS; NO_EVIDENCE is a false abstention (your case 3) |
| split: cross-company ranking | 3 (EV2-040, 042, 043) | SUCCESS only with one search per company; one GraphRAG call at k = 10 did not return all ten |
| not_in_graph_yet: Exhibit 21 | 7 | NO_EVIDENCE today; rescue once GraphRAG loads Exhibit 21 |
| not_in_corpus: NetApp's 10-Q (Data holds it for review) | 3 | NO_EVIDENCE, correctly |
| must_abstain: unanswerable or out of scope | 12 | NO_EVIDENCE even after fallback |

What we report for your cases (`fallback.observed_cases` in the results):

1. **empty → GraphRAG** and 2. **weak → GraphRAG**: on answerable questions, SUCCESS with the needed evidence; on
   unanswerable ones, NO_EVIDENCE. Split by `weak_reasons`.
3. **ok but final NO_EVIDENCE**: on answerable questions a likely false abstention (the two above are known cases); on
   unanswerable ones a correct catch.
4. **Before and after fallback**: the same questions with fallback off and on (`--baseline`), question by question:
   rescued, broken, both right, both wrong.

**What round 1 says about the fallback today:** of the 16 answerable questions RAG declined, GraphRAG had the evidence
for 1. Seven wait on Exhibit 21, three on NetApp's 10-Q, three need one search per company, and two are the reader's
call. So the checks that matter most now are that fallback does not break the 127 questions RAG answers, does not
turn the 12 unanswerable ones into SUCCESS, and how often it fires on questions that did not need it.

## Small asks (none blocks a first run)

1. **Per evidence item:** `source` (rag, graphrag_structured, graphrag_graph), `accession_number`, and its id (RAG
   `chunk_id`; GraphRAG fact or claim id). We could then tell which arm supplied the evidence and score by filing.
2. **For case 4:** a request switch to turn fallback off (e.g. `disable_fallback: true`), or the pre-fallback RAG
   evidence in the response. For case 3, the evidence the Agent judged insufficient.
3. **The tool-routing path** (listed as pending), e.g. `tools_called`, so the orchestrator is scored by the same routing
   script as our baselines. Until then we infer: RAG always, GraphRAG when `fallback_triggered`.
4. **Filters to GraphRAG:** `{ticker, accession_number}`, as GraphRAG confirmed on 11/11. The parser's `fiscal_year` and
   `fiscal_period` map to an accession through `data/snapshot_w7.json`.
5. **Time per stage** (ms), for the latency and cost metric.
6. **When `answer` lands:** `value`, `value_text`, `unit`, `period_end` (and the optional `values` list for multi-part
   questions), as in `kpmg_eval/answer_schema.py`, so the answer grader applies unchanged.
