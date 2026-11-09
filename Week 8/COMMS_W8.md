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
