# Gold Set v2

The round-1 question set: **155 questions, 143 answerable**, on the Data team's ten companies and the **21 filings** in
Data's database snapshot of 2026-11-03 (the same 21 filings as Data's round-1 freeze list, `eval/round1_filings.csv` in
RAG's repo). File hash `ed4b42db6fc25ee5` (first 16 hex of sha256). Built 11/5 (Week 7), unchanged since.

## Files (this folder)

| File | For |
|---|---|
| [`data/benchmark_v2.jsonl`](data/benchmark_v2.jsonl) | The scored set: one JSON object per question (answer, facts, filters, route, distractors, anchors) |
| [`data/benchmark_v2_questions.xlsx`](data/benchmark_v2_questions.xlsx) | Filterable spreadsheet: Questions, By company, Filings |
| [`data/benchmark_v2_questions.docx`](data/benchmark_v2_questions.docx) | Word version for reviewers: summaries, the 21 filings, questions by company |
| [`data/benchmark_v2_questions.csv`](data/benchmark_v2_questions.csv) / [`.md`](data/benchmark_v2_questions.md) | Flat lists |
| [`data/snapshot_w7.json`](data/snapshot_w7.json) | The 21 filings and how they match Data's lists |
| [`data/decision_suite_v1.jsonl`](data/decision_suite_v1.jsonl) | 24 extra clarify / off-topic / abstain prompts for the Agents' scope check |
| [`data/messy_wording_v1.jsonl`](data/messy_wording_v1.jsonl) | 427 typo and casual-wording rewrites of these 155 questions |
| [`data/hops_v1.csv`](data/hops_v1.csv) | Hop counts per question, for GraphRAG |
| [`results/gold_v2_summary.json`](results/gold_v2_summary.json) | Counts, hash, change log |

Regenerate: `python scripts/build_gold_v2.py` (the jsonl), then `python scripts/export_gold_v2_xlsx.py` and
`node scripts/export_gold_v2_docx.js`. Do not edit the exports by hand.

## What is in it

| | Count |
|---|---|
| Questions / answerable | 155 / 143 |
| Route needed: finance data / text / relationship / both / no tool | 104 / 31 / 11 / 1 / 8 |
| Single-company questions: Microsoft (MVP) / each of the other nine | 95 / 4–9 |
| Questions across companies | 9 |
| Answer: exact number / exact text / narrative / refuse / correct premise | 94 / 12 / 30 / 12 / 7 |
| Check status: checked vs SEC data / read twice / needs human review | 109 / 9 / 37 |

Sources: 30 from RAG's Gold Set v0 (their IDs and wording), 60 from Gold Set v1, 50 written for the ten companies,
6 relationship questions drafted with GraphRAG, 9 from Exhibit 21 and NetApp's fiscal labels.

**Checks:** 55/55 re-reads agree; 18/18 quarterly figures sum to the reported totals; the grader labels 160/160 new
numeric answers correctly; the nine non-Microsoft income statements, read from the filings, match. The Exhibit 21
answers match GraphRAG's own Exhibit 21 output on all 62 rows we hold.

**Still open:** 37 text answers (narratives and definitions, mostly RAG's v0 wording) are flagged for a person to check
against the filing; text anchors for the new lookup questions wait on the round-1 chunks.

## How the 10/29 minutes and RAG's Slack message are reflected

| Ask | In Gold Set v2 |
|---|---|
| Match the filing list with Data (minutes #5) | 21/21 filings match Data's database and freeze list |
| Bring in Exhibit 21 (minutes #5) | 7 Exhibit 21 questions (EV3-001..007), 4 of the 11 relationship questions test invented or false links |
| Add anchors once Data shares filing text (minutes #5) | Exhibit 21 anchors in; lookup anchors wait on the round-1 chunks |
| Review RAG's draft anchors (minutes #5, RAG Slack) | `data/rag_anchor_fixes.csv`: 10 drop (8 are Amazon/Meta), 2 remove, 25 narrow |
| RAG's 8 Amazon/Meta questions need 3/31 10-Qs (RAG Slack) | Dropped: both companies are outside the ten; no answerable question names a company outside the ten |
| Report numeric accuracy by route (RAG Slack) | Every question has `route_expected`; the harness reports accuracy by route |
| Freeze one snapshot for all teams (RAG Slack) | The 11/03 database snapshot; comparison questions name that date |
| Answer / clarify / abstain rules with Agents (minutes #5) | Expected decision derived per question, plus the 24-item decision suite |
| "Micron's newest annual report is not out yet" (our 10/29 update) | Corrected: it was filed 10/09 and is in the database. EV2-045 is now a derived Q4 FY2026 question; EV2-050 tests Q1 FY2027 (outside the snapshot) |

Other changes from the Week 6 draft: McKesson and Medtronic net income questions say "excluding noncontrolling
interests" (the statement total is scored as a wrong answer); NetApp's fiscal-year labels became test questions
(EV3-008, EV3-009).
