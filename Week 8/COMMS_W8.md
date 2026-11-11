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

Updated 11/11 evening: round 1 has now run on both retrievers (RAG 11/9 and 11/11, GraphRAG 11/11), and GraphRAG agreed
to send this right after it.

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

Two small asks:
- Narrative judge: `scripts/run_narrative_judge.py` is ready (point by point, with a quote check). Could you run it with
  your key, or lend one for the run? `--dry-run` shows the exact prompts. It counts only after it agrees with our hand
  labels.
- GSv0-MSFT-023 and EV1R-005 state the answer but come back `answered: false`. Could the reader mark those as answered?

(NetApp's 10-Q isn't in chunks_C1, and that's expected: Data holds it for review because NetApp tagged its opening cash
a day late. So EV2-026 and EV3-008/009 are out of reach for every team until Data clears it.)

Everything is in kpmg-eval → Week 8 (FOR_TEAMS_W8.md, results/answers_rag_reader_round1.json, GOLD_SET_V2.md). Your
answers and chunks stay off GitHub.

## Slack reply to GraphRAG (Adeline), round 1 results, 11/11

Thank you, Adeline, this is great: both arms on all 155, the store, and #70 merged the same day.

What we did with it (kpmg-eval → Week 8, EVAL_GRAPHRAG_W8.md):
- Loaded the store: 20 filings, 24,533 facts, corpus_version data-api-raw:20. It stays private on our side, so no
  credentials needed; the gzip was the easiest path. We can't reach Data's Postgres from our workspace anyway.
- Re-ran the structured arm on it with your #70 code. With translated filters we match your run on all 155 questions:
  63/93 numbers in the top 10, rank 1 right on 26. With the gold filters, #70 removes all 10 errors (the list-ticker
  questions), and the result is still 63/93.
- Updated our filters to your guidance: {ticker, accession_number} for one filing, and now lists of both for the 11
  multi-filing questions, since IN works on both arms.

On GSv0-MSFT-001, it isn't the store. Both stores put Microsoft 365 rows at the top for our wording, all tied at 1.05,
because "three months" matches the ThreeSixFive members. Which tied row comes first even changes with top_k (74,083 at
k=3, 21,883 at k=10). "Quarter ended" wording gives 241,832 at rank 1, which is the figure you saw, and it's a
nine-month total. On the Microsoft 10-Q side by side your store gives 24/50 vs 25/50 on our build. The one change is
EV1-015, where a date fact (DividendsPayableDateDeclared) outranks the dividend per share. Two ideas for #68: break ties
deterministically (period match first, then facts without dimensions), and drop non-numeric facts for number
questions. Also, with no ticker filter the top fact for a Microsoft question comes from Medtronic's 10-Q, so callers
should always send the ticker.

Small asks:
1. When it's convenient, re-run the graph arm with #70 on Gold Set v2.2. The script defaults to it now: same command,
   new tag please (graphrag_aura_v2_2). v2.2 adds anchors for 4 questions, so prose goes from 38 to 42.
2. (Hops: received, thank you. See the reply below.)
3. Exhibit 21 after midweek is fine. We'll re-score the 9 Exhibit 21 questions once Subsidiary nodes are loaded.

Data: agreed, the joint ask for Microsoft FY2024 and FY2025 is drafted (COMMS_W8.md). Send it whenever you're ready.

One small thing: since the Neo4j password went into the channel, it may be worth rotating it. We don't need it, because
our workspace can't reach Aura.

## Slack reply to GraphRAG (Adeline), hops, 11/11

Thank you for the hops, and for spelling out both points. Agreed on both.

It's merged into data/hops_v2.csv as you sent it, and your file is kept alongside. The 95 XBRL rows stay blank, since
writing 2 would claim a walk your graph can't make. Because the ontologies differ, the sheet now keeps your hops next
to the edge count of our gold path. EV3-002 shows 2 vs 4, which is the Jurisdiction-node difference, not a counting one.

We checked every row. Three things:
- EV3-008/009 were our mistake. They're NetApp fiscal-label questions, but our gold labelled their pattern
  "relationship", which sent the derivation to Exhibit 21. Relabelled in Gold Set v2.2, so nothing needed from you.
- EV1-068/069/070 and EV2-048/049 are false-premise questions, so they're answerable: the answer has to state the
  correct fact (e.g. revenue rose, or Take-Two's 298.2 loss). Could they take their route's support (no for the four
  XBRL ones, the claim path for EV1-070) instead of "unanswerable"?
- EV1R-001 is "yes" through claims, while the Exhibit 21 rows are blocked. Does the graph hold Microsoft's Exhibit 21
  list as claims?

Each row has an eval_check column with these notes. kpmg-eval → Week 8, EVAL_GRAPHRAG_W8.md.

## Slack reply to GraphRAG (Adeline), PR #71 and the dropped connection, 11/11

Thank you, Adeline. PR #71 is merged into our hops sheet, and deriving it in code was the right call. Agreed on EV3-007:
a dropped Aura connection isn't the arm's fault. Our round-1 script now retries it (--retries 3), and anything that
still fails is reported as an infra error, separate from arm errors. Errored calls were already left out of the scores.

Your section-scope note turned out to explain most of the graph arm's prose score. We placed each anchor by RAG's chunk
sections. Of the 38 prose questions, 20 have their text inside your five section types, and the graph
arm found 10 of them. The other 18 sit outside: 10 only in the notes to the statements, 8 in
Exhibit 21 or NetApp's 10-Q. So the 26% is 50% on what the graph holds. Adding the notes (10-Q Item 1, 10-K Item 8)
would bring 10 more within reach, if that fits your plans.

The same rule touches a few hops rows (eval_check column, nothing urgent):
- 10 text questions are "yes" via claims, but their answer is only in the notes, so support today is no
  (GSv0-MSFT-006/007/008/009/011/012/028/029/030, EV1-047).
- EV3-008/009 are NetApp's 10-Q, which isn't in the 20-filing corpus (Data holds it for review), so also no.
- EV1R-005's "no" is right, but the reason is that the correcting text is in the notes, not that it's XBRL.

Details: kpmg-eval → Week 8, EVAL_GRAPHRAG_W8.md.

## Slack reply to Agents (API v0.2), 11/11

哈咯！谢谢，v0.2 文档很清楚，这些字段都可以直接接进我们现在的 pipeline，不需要先改。

我们这边已经接好了（kpmg-eval → Week 8，AGENTS_API_W8.md）：
- `scripts/run_agent_api.py`：把 Gold v2.2 的 155 题逐题 POST 到 /query。trace_id 用 "<tag>:<qid>"（你们会保留传入的 trace_id，所以每条结果都能对回题号），top_k=10，和 round 1 一致。
- `scripts/grade_agent_run.py`：直接读 /query 的原始 response（一行一个 JSON）。v0.2 的 answer 还是 null，所以先按 decision 和 evidence 打分：
  - status：可答题应为 SUCCESS，不可答题应为 NO_EVIDENCE。ERROR 单独列出，不计分
  - evidence：最终 evidence 里有没有需要的数字或原文 anchor
  - citations：从 source_url 读 accession，看是不是正确的 filing
  - filters：和 gold filters 逐个 key 对比（字段名和取值格式刚好一致）
  - fallback：按 evidence_status 和 weak_reasons 拆开看 triggered、used 和最终结果
  等 answer 上线后，用和 RAG reader 一样的 grader 给数字、premise 和 narrative 打分。

你们说的 4 类 case，我们用 round 1 的结果把每道题提前分好了组（data/fallback_cases_w8.csv），可以用 `--only <case>` 分开跑：
1. empty → GraphRAG
2. weak → GraphRAG
   这两类都看：可答题是否 SUCCESS 且 evidence 里有答案；12 道不可答题在 fallback 之后也必须是 NO_EVIDENCE。
3. ok but final NO_EVIDENCE：GSv0-MSFT-023 和 EV1R-005 这两题 RAG 的 evidence 里其实有答案，这里返回 NO_EVIDENCE 就算 false abstention。
4. fallback 前后对比：同一批题跑两次（关和开），用 `--baseline` 逐题算 rescued 和 broken。

一个发现：round 1 里 RAG 没答的 16 道可答题，目前只有 1 题（GSv0-MSFT-019）GraphRAG 有 evidence。另外 7 题要等 Exhibit 21 进 graph，3 题是 NetApp 10-Q（Data 还在 review，不在 corpus 里），3 题是跨公司排名（需要每家公司各查一次），2 题是上面的 case 3。所以现阶段 fallback 最要紧的是：不把 RAG 已经答对的 127 题弄坏，不让 12 道不可答题变成 SUCCESS，再看看它在不需要的题上 trigger 的频率（成本）。

几个小请求，都不影响先跑第一轮：
1. evidence 每条加上 `source`（rag / graphrag_structured / graphrag_graph）、`accession_number` 和 id（RAG 的 chunk_id；GraphRAG 的 fact 或 claim id）。这样能知道 evidence 来自哪个 arm，也能按 filing 打分。
2. case 4 需要一个关掉 fallback 的开关（比如 request 里加 `disable_fallback: true`），或者 response 里带上 fallback 之前的 RAG evidence。case 3 最好也能看到被判为不够的那批 evidence。
3. 文档里列为 pending 的 tool-routing path（比如 `tools_called`）有了以后，orchestrator 就能和我们的 routing baseline 用同一个脚本比较。在那之前，我们先按“RAG 总会调用，fallback_triggered 时调用 GraphRAG”来推断。
4. 调 GraphRAG 时 filter 用 {ticker, accession_number}，这是 GraphRAG 11/11 确认的方式。query parser 给出的 fiscal_year / fiscal_period 可以用我们的 data/snapshot_w7.json 对到 accession。
5. 方便的话，加上每个阶段的耗时（ms），用于 latency 和 cost 指标。

我们这边的环境连不到外部地址，所以麻烦你们跑一下：
`python scripts/run_agent_api.py --base-url <你们的地址> --tag agents_v02`
然后把 private/agent_responses_agents_v02.jsonl 私下发给我们就好（evidence 里有 filing 原文，所以不放 GitHub）。拿到后我们当天出结果。
