# Week 8 messages (drafts written for Thomas to post)

Kept here so the repo has a record of what Eval told the other teams. Per-team asks with file paths are in
[`FOR_TEAMS_W8.md`](FOR_TEAMS_W8.md).

## Group update (Eval channel), 11/9

This week we ran RAG and GraphRAG side by side on the same Microsoft 10-Q, all 84 questions, using each team's own
code. RAG found the numbers it needed for 49 of 50 questions and the text it needed for 22 of 27 (on Gold Set v2.1's
corrected anchors). GraphRAG's structured search found 25 of 50 numbers and no text, but showed far fewer wrong-period
numbers. Traversing GraphRAG's own Exhibit 21 data answered all 9 relationship questions exactly, while RAG can't reach
Exhibit 21 today. RAG also ran round 1 on our gold set (105 of 124 found at k = 10) and traced every miss; four were our
anchors, so we fixed all 22 anchors from the same automatic conversion (Gold Set v2.1). We also labelled the routing
chart, defined the keyword router and unneeded calls, wrote 7 routing examples for the demo, and tested 427
messy-wording versions of our questions. Everything is in kpmg-eval/Week 8, with one section per team in
FOR_TEAMS_W8.md.

## Slack reply to RAG (Xiangxinrui Shan), round 1, 11/9

Hi Xiangxinrui, thank you for running round 1 and tracing every miss. This is really helpful. 105/124 at k=10, with
the nine other companies at 34/37, is a great result.

You were right about GSv0-MSFT-019/021/027/029. Those anchors came from Gold v0's automatic region conversion and don't
match the questions. That same conversion produced 22 anchors in total, so we replaced all 22 with the sentence or
figure that supports each required point, exactly as the 10-Q prints it. We checked every string against the filing and
your chunker's output.

This is now Gold Set v2.1 (kpmg-eval, Week 8/data/benchmark_v2_1.jsonl, sha 1e104c626c6c9833). Questions and answers are
unchanged, so only the prose questions need rescoring. Old vs new anchors per question are in
Week 8/results/gold_v2_1_changes.json. On our local Microsoft 10-Q run, BM25 prose went from 18/27 to 22/27 with the
fixed anchors.

For your 7 unanchored questions:
- EV2-041 and EV2-048 now use 298.2 (Take-Two's net loss).
- EV2-049 uses 46,398 and 46,309 (Nike revenue), read from the SEC income statements. Let us know if your chunks print
  these differently.
- EV2-035/036/037/044 need the fiscal-calendar wording, so we'll anchor them as soon as we have chunks_C1.jsonl.

The missing row label is now spelled out in Week 8/data/anchor_review_w8.json (row_labels). For operating income all 4
chunks show the total, so any of them counts.

Could you send chunks_C1.jsonl and the per-question results privately (Drive or DM)? We'll finish those 4 anchors and
check your results against v2.1. The cross-company and 10-K + 10-Q misses we'll take to Agents as query splitting.
Thanks again!

## Slack reply to GraphRAG (Adeline, Wenyu, Alina, Claudia), 11/11

Hi GraphRAG team, thank you for the week-8 reply, and congratulations on getting the real tools out. The filter fix,
the Exhibit 21 output and the heads-up on periods all came in time for round 1. Everything we did with it is in
kpmg-eval → Week 8/EVAL_GRAPHRAG_W8.md. Short version:

Done on our side
- Harness now imports graphrag.backends (pinned to main @ 4e89acb), and the side by side calls your structured arm that way.
- Your fourth mock finding was right, and it was worse than a mismatch: the real list of {axis, member, type} made our key code crash. Fixed and tested. Dict, list and gold pairs now give the same key, and nothing depends on section.
- hops split adopted. data/hops_v2.csv has `filings` filled by us in code (136 questions need 1 filing, 11 need 2 or more). `hops` is left for you. Your verdicts on the six drafts are recorded.
- M17 was already reworded in Gold Set v2 to the FY2026 decline (XBOX 23,455 → 21,790, −7.1%, no Activision revenue line).
- M08 is now an abstention candidate (EV3-010) for v2.2, after round 1.
- M12: agreed on the segment-figure version. But Data's inventory for the ten has no 10-K/A at all, so M12/M13/M19 stay parked.

Two things we found while switching
1. The graph arm refuses fiscal_year/fiscal_period, which 129 of 155 gold questions carry. The structured arm accepts and ignores them. So we now send {ticker, accession_number} whenever the evidence sits in one filing (136 questions); both arms apply that. Is that how you want callers (incl. the Agents) to do it?
2. List-valued ticker filters (13 cross-company questions) fail on both arms. Structured raises RetrievalUnavailableError from a DuckDB cast error, which looks like an outage. Graph returns nothing, silently. Could you support IN, or refuse with a ValueError?

Also: on our store (your fact_loader_v1 on Data's copy of the 10-Q), GSv0-MSFT-001 puts a Microsoft 365 product row at rank 1, not the 241,832 you saw. "Three months" matches the ThreeSixFive members. Rank 1 is the right number on 14 of 50 number questions and a wrong-period number on 6 of 36. So we may be on different stores.

What would help most
1. Our workspace can't reach Aura (*.databases.neo4j.io) or sec.gov, so we can't run the graph arm or build the store ourselves. Could you run round 1 on your side, like RAG did? From kpmg-eval/Week 8: `python scripts/run_graphrag_round1.py --graphrag <your checkout> --tag graphrag_aura` with your Neo4j variables and MSFT_FACT_DB_PATH set. Then send us results/graphrag_round1_graphrag_aura.json and .csv. It runs both arms on all 155 questions.
2. The 20-filing DuckDB store, shared privately, so we can compare stores and rerun the structured arm on every company.
3. Is PR #34 the alina/ex21-pipeline branch, and when will it merge and load? 9 questions depend on it, and its rows matched our gold reads 62/62.
4. `hops` in hops_v2.csv when you have them, starting with the six drafts.

And for Data together: Microsoft's FY2024 and FY2025 10-Ks are already in Data's inventory and passed their checks. They just aren't in the 21-filing database. Shall we ask Data to load them right after round 1 (draft below)? That unblocks M05 and gives M04/M06/M17 a third year.

Thanks again!

## Joint ask to Data (draft, to send with GraphRAG after round 1), 11/11

Hi Emma, a joint ask from Eval and GraphRAG, for after round 1 so the 11/03 freeze holds until then. Could you load
Microsoft's FY2024 10-K (0000950170-24-087843) and FY2025 10-K (0000950170-25-100235) into the database? Both are in
your 2021–2026 inventory and passed your fact checks. They unblock one gold question (first year a segment was
reported) and give three others a third year to compare. Thank you!

## Slack reply to RAG, end-to-end round 1, 11/11

Thank you, this is exactly what we needed, and all three notes were right.

We reproduce your numbers exactly with our graders: NAA 87/93 = 0.935, balanced RAA 0.977, unanswerable 10/10 (your
subset, without the graph-route and review-required questions). On all 155 it's NAA 87/94 and RAA 0.944, with every
unanswerable question refused.

1. EV1-015: agreed. The sig-fig floor is now the precision the filing prints, so 2. EV1-027 had the same issue.
2. EV1-043: the 7 multi-part questions now list every figure (`gold.values`), and all must be stated. We read them from an
   optional `values` list in the AnswerBlock (sign-sensitive) or, without one, from `answer_text`, so your EV1-043 passes
   as written.
3. EV1R-002 / 006: agreed, both now route to text. GraphRAG's review of those drafts says the same.

These are in Gold Set v2.2 (same questions and answers, grading only). With them NAA is 89/94 = 0.947.

Your files also caught two of our mistakes. The 10-K gives Microsoft's OpenAI stake as about 25%, where the 10-Q says
27%, so both count now (EV1R-005). And v2.1 put two anchor sentences in one evidence item, which your chunker splits
(8 questions), so v2.2 has one item per point. We had chunks_C1 in the zip, thanks, so the last 4 anchors are done, and
every anchor outside Exhibit 21 and NetApp's 10-Q is in your chunks. Citations look strong: all 185 cited chunks exist,
and 58 of 59 lookups show the number in a cited chunk.

Three small asks:
- Narrative judge: `scripts/run_narrative_judge.py` is ready (point by point, with a quote check). Could you run it with
  your key, or lend one for the run? `--dry-run` shows the exact prompts. It counts only after it agrees with our hand
  labels.
- GSv0-MSFT-023 and EV1R-005 state the answer but come back `answered: false`. Could the reader mark those as answered?
- chunks_C1 has 20 filings, and NetApp's 10-Q isn't among them (EV2-026, EV3-008/009 were declined). Is that intended?

Everything is in kpmg-eval → Week 8 (FOR_TEAMS_W8.md, results/answers_rag_reader_round1.json, GOLD_SET_V2.md). Your
answers and chunks stay off GitHub.
