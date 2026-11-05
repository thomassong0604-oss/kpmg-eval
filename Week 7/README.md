# Week 7: ten companies, one snapshot

Evaluation & Testing workstream, KPMG × Columbia QMSS. Week 7 acts on the Evaluation items from the 10/29 KPMG meeting
(minutes #5) and moves the gold set entirely onto the Data team's ten companies.

```bash
pip install -r requirements.txt
./scripts/run_all.sh                                   # full pipeline, 75 tests
python scripts/run_harness.py --benchmark v2           # grade systems on Gold Set v2
python scripts/run_harness.py --benchmark v2 --system fixed_reader   # RAG's gpt-4o-mini reader (needs OPENAI_API_KEY)
python scripts/build_deck_w7.py <base.pptx> <out.pptx> # this week's six Eval slides
```

Start with [`FOR_TEAMS_W7.md`](FOR_TEAMS_W7.md) (what each team gets and what we need) and
[`POLICY_answer_clarify_abstain.md`](POLICY_answer_clarify_abstain.md) (draft rules for the Agents' checkpoints).

## 10/29 action items → what exists now

| Action item (minutes #5) | Where | Result |
|---|---|---|
| Match the filing list with Data's | `data/snapshot_w7.json` (`scripts/build_gold_v2.py`) | Data's database on 11/03 holds 21 filings (from GraphRAG's `filings.yaml`); Data's 2021-2026 inventory (233 filings) contains all 21. Our Week 6 list matched 20/21: the DB has Micron's **FY2026** 10-K (filed 10/09), we had assumed FY2025. Gold Set v2 matches 21/21. One newer filing exists in Data's inventory (Microsoft Q1 FY2027 10-Q, 10/28) |
| Bring in Exhibit 21 | `data/sec_reads/exhibit21_2026-11-05.json`, questions EV3-001..007 | Read from each latest 10-K. Apple (19), Casey's (9), Micron (21) transcribed in full, read twice, reads agree; long lists (Take-Two 144) used only for lookups. 7 relationship questions incl. 2 invented-relationship checks. To compare with Data's cleaned version when it lands |
| Evidence anchors so RAG and GraphRAG can be scored | `data/benchmark_v2.jsonl` (`rag_evidence`) | EV3 questions carry Exhibit 21 / note anchors. Text anchors for the EV2 lookups still wait for Data's chunks of the 21 filings |
| Review RAG's draft anchors | `results/rag_anchor_fixes.csv` | One row per change: 10 questions to drop (incl. the 8 AMZN/META ones RAG asked about: outside the ten), 2 anchors to remove (stray share-count string from Gold v0), 17 of 25 broad anchors get a 1-3 chunk replacement such as `Total revenue | 82,886` (6 chunks → 1); 8 need a row label from RAG |
| Agents ↔ Eval: when to answer or abstain | `POLICY_answer_clarify_abstain.md`, `kpmg_eval/metrics/decision.py`, `data/decision_suite_v1.jsonl` | Four decisions (answer / clarify / abstain / block off-topic, per KPMG's 10/29 guidance). On 179 questions: answering everything → 100% unsafe answers and 8 off-topic tool calls; a simple scope check → 96.1% right decisions, 13.9% unsafe, 0 off-topic tool calls, 0 needless refusals |
| Agents: compare routing with combined retrieval | `kpmg_eval/metrics/routing.py`, `scripts/run_routing_baselines.py` | Expected route on all 155 questions. Text only: 20% of questions get their needed tool; keyword router 84% at 1.05 calls/question; every tool 95% at 3 calls |
| RAG: fixed reader; numeric accuracy by route | `scripts/systems.py` (`FixedReaderSystem`), `kpmg_eval/harness.py` | gpt-4o-mini, temperature 0, RAG's own prompt, top 8; tested with a stub client, runs once an API key is set. Every scorecard reports `numeric_accuracy_by_route` |

## Gold Set v2 (`data/benchmark_v2.jsonl`, hash `ed4b42db6fc25ee5`)

155 questions, 143 answerable; **every answerable question is about the ten companies**. Microsoft stays the MVP
(92 answerable); each other company has 9-16. Readable list: `data/benchmark_v2_questions.md` / `.csv`.
Gold Set v1 stays frozen.

- **Micron** moves to its FY2026 10-K: revenue USD 133,188M, net income USD 84,969M (read twice from the filing; the SEC data
  API still has no facts from it, which is why we wrongly said on 10/29 it was not in the corpus). FY2026 is a 53-week year.
  The 10/29 refusal question is now a derived Q4 question (USD 54,229M); a new refusal asks for Q1 FY2027.
- **Net income wording:** McKesson's and Medtronic's statement "Net income" includes noncontrolling interests (5,099 vs 4,762;
  4,837 vs 4,801). Questions now say "excluding noncontrolling interests"; the totals are distractors. Parker-Hannifin noted.
- **Pinned snapshot:** comparison questions say "in the November 3, 2026 database snapshot", so later loads can't change answers.
- **NetApp metadata:** 3 NetApp 10-Qs tag `DocumentFiscalYearFocus` one year behind NetApp's own text (Q1 FY2027 tagged 2026);
  question EV3-008 tests it, and filters must use fiscal labels from the text.
- **Checks:** 55/55 re-reads agree; 18/18 quarterly sums tie; 160/160 grader labels right on the new numeric questions; all nine
  other companies' income statements read from the filings match the gold.
- `snapshot_status` and `route_expected` on every question; hops sheet (`data/hops_v1.csv`) now covers 165 questions.

## Files

`data/sec_reads/` (every SEC read this week, with sources), `data/snapshot_w7.json`, `data/benchmark_v2*`, `data/decision_suite_v1.jsonl`,
`results/gold_v2_summary.json`, `results/decision_baselines.json`, `results/routing_baselines.json`, `results/rag_anchor_fixes.csv`,
`results/scorecard_*_v2.json`. Week 6 material (scope10, GraphRAG wiring) is carried over unchanged except where noted.
