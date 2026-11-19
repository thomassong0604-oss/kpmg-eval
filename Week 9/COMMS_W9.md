# Week 9 messages (drafts for Thomas to post; nothing here has been sent)

## Slack reply to RAG (holdout request and narrative judge), 11/16 (draft)

Hi RAG team, thank you for the clear spec and for freezing `final_v1` before asking. Both are in hand.

**1. Holdout.** Batch A is written and sealed: 40 questions (30 numeric, 5 narrative, 5 unanswerable), 10 on
Microsoft, 14 stress questions with a `stress_type` (misspelled name 4, analyst wording 3, multi-step 2, relative
period 2, cross-filing 2, narrative across sections 1). Same JSONL fields as Gold v2, plus `split`, `stress` and
`stress_type`. Every numeric answer comes from Data's fact store, and no fact is one a dev question uses, except three
derived questions that pair a new fact with a dev one (flagged in the manifest). The file's SHA-256 is in our repo
(Week 9/results/holdout_A_manifest.json), so you can confirm later that it did not change. We will hand over the file
on Thu 11/20; tell us if you prefer it committed or sent directly. Batch B (about 30, mostly narrative) follows by
11/24 and stays with us until you tag `final_v2`.

Two notes: NetApp has no questions, because its facts are not in Data's store yet. And we count Casey's in thousands,
as its filings print.

**2. Narrative judge, both runs, same 38 questions.**

| | final_v1 | narr_union |
|---|---|---|
| Every required point stated | 26/38 | 28/38 |
| Required points stated | 94/108 | 94/108 |
| Figures supported by a cited chunk | 69/69 | 66/66 |

- narr_union gains GSv0-MSFT-029 and -030 and loses no question. It states fewer points on EV1-070 and GSv0-MSFT-019,
  which fail in both runs, so total points are level. With 38 questions, +2 is encouraging but not yet a reliable
  difference; batch B is the right test of it.
- Faithfulness is clean in both runs: every figure is printed in a cited chunk or computed correctly from printed
  ones. Nice work on the reader.
- Ten questions miss a point in both runs, usually one: a second-level detail (GSv0-MSFT-006, -007), a reason or
  driver (-011, -018, -019, -022, -027), after-tax amounts (EV1R-003), or a false-premise answer that stops after the
  correction (EV1-070, EV1R-005).
- One gold difference: your file has "approximately 27 percent" for EV1R-005; Gold Set v2.2 also accepts 25%, so we
  counted your 25% as stated.

How it was judged: Claude read each answer against the Week 8 rubric (we have no API key, so this was not an API
run); each "stated" verdict carries a quote that our script finds in the answer. Eight close calls are listed in the
results file. Agreement with humans is not computed yet. When your 20 blind labels are ready on 11/18, please send
them as qid, run, point, human_verdict (stated / missing / contradicted) and we will report agreement and kappa
before the 11/19 meeting. Per-question results: Week 9/results/narrative_judge_w9_per_question.csv.

## Slack reply to RAG (gpt-6-sol judge results), 11/16 (draft)

Thank you, this is exactly what we needed, and the identical re-run is a useful check. Your numbers reproduce from the
files: 17/30, 17/30 and 23/30, with six gained and none lost for the fuller-answers variant.

- We compared your gpt-6-sol verdicts with ours (Claude) on the same answers. On final_v1 the two judges agree on 71
  of 74 shared points (kappa 0.84). The three differences are GSv0-MSFT-026 point 2, GSv0-MSFT-027 point 2 and
  EV1-045 point 2 (28.5% computed vs 29% printed).
- On narr_union they agree on 68 of 74. Your judge shows no gain for the union variant and ours showed +2, on close
  calls, so we would report it as no measurable change. That matches your read.
- The fuller-answers variant is a clear step on dev (+6, none lost). Since it was tuned on these questions, batch B is
  the fair test, and we will keep it sealed for that. Could you send its judge_input file too, so we can run our
  figure-level faithfulness check on the longer answers?
- Hand labels: two of us will label the final_v1 sheet (87 points) by Wed 11/18 and report agreement and kappa for
  the judge, together with your 20 blind labels.
- EV1-045: we think 28.5% should not count against you, since it is the same figure with one more digit. We will make
  the gold accept it in v2.3.

## Combined Slack reply to RAG, 11/16 (the version to post; replaces the two drafts above)

Hi RAG team, thank you for the clear spec, for freezing final_v1 before asking, and for running the judge so quickly.

1. Holdout. Batch A is written and sealed: 40 questions (30 numeric, 5 narrative, 5 unanswerable), 10 on Microsoft, 14 stress questions with a stress_type (misspelled name 4, analyst wording 3, multi-step 2, relative period 2, cross-filing 2, narrative across sections 1). Same JSONL fields as Gold v2, plus split, stress and stress_type. Its SHA-256 is in our repo (Week 9/results/holdout_A_manifest.json), so you can confirm later that it did not change. You get the file Thu 11/20; tell us if you prefer it committed or sent directly. Batch B follows by 11/24 and stays with us until you tag final_v2. Two notes: no NetApp questions (its facts are not in Data's store yet), and Casey's figures are in thousands, as its filings print.

2. Judge. Your numbers reproduce from the files: 17/30, 17/30 and 23/30, six gained and none lost for the fuller-answers variant, and the re-run is identical on all 87 points.
- We also judged final_v1 and narr_union ourselves (Claude, same rubric). The two judges agree on 71 of 74 shared points on final_v1 (kappa 0.84) and 68 of 74 on narr_union.
- narr_union: no gain with your judge, +2 with ours on close calls. We would report it as no measurable change.
- Faithfulness on both runs is clean on our side too: every figure in the answers is printed in a cited chunk or computed correctly from printed ones.
- The fuller-answers variant is a clear step on dev. Since it was tuned on these questions, batch B is the fair test. Could you send its judge_input file so we can run the same figure check on the longer answers?
- EV1-045: 28.5% is the filing's 29% with one more digit, so it should not count against you. We will make the gold accept it in v2.3. Also, your judge_input lists only 27% for EV1R-005; Gold Set v2.2 accepts 25% as well.

3. Hand labels. None exist yet on our side, so the judge is not validated today. Two of us will label the final_v1 sheet (87 points) by Wed 11/18 and report agreement and kappa, together with your 20 blind labels, before the 11/19 meeting.

## Addition to the combined reply: what we need from RAG (11/16, draft)

What we need from you:
1. By Wed 11/18: your 20 blind hand labels as a CSV with qid, run, point, human_verdict (stated / missing / contradicted).
2. By Wed 11/18: the judge_input file for the fuller-answers variant (answers plus cited chunk text), same format as the two you sent.
3. By Thu 11/20: how you want batch A delivered, committed to our public repo or sent to one person directly, and who that person is.
4. With the batch A results: the AnswerBlocks, plus latency and token counts per question.
5. A note when final_v2 is tagged, so we can release batch B.

## Slack reply to RAG (thread of 11/16, 17:10): final_v2 judged, batch A, objective sets (draft)

Thank you, all five points work for us, and thank you for switching the hand labels to the point-by-point format.

1. final_v2 (fuller answers), judged from your file. Same 38 questions and rubric:
   - Every required point stated: 34/38, against 26/38 for final_v1. Eight questions gained, none lost, nothing contradicted. On the 27 narrative questions: 24 against 17.
   - It agrees with your gpt-6-sol run: on the 26 narrative questions both judges saw, yours goes 16 to 22 and ours 17 to 24, and the judges agree on 72 of 74 points.
   - Faithfulness: 80 of 80 figures are printed in a cited chunk or computed correctly from printed ones. The answers are about 20% longer and added no unsupported figure. Nice result.
   - Still missing in every run: GSv0-MSFT-006 (Server products and cloud services), EV1R-003 (the after-tax amounts), GSv0-MSFT-019, EV1R-005.
   - It was tuned on these questions, so batch B stays sealed as its test.

2. Batch A. You will get it by DM by Thu 11/20. The SHA-256 to check is the one in Week 9/results/holdout_A_manifest.json (it starts a6cf275c). If we change a question after our own review, we will republish the manifest first and tell you.

3. Independent XBRL sets: yes, Eval will hold them. What we need from you:
   - A saved pull of the metric rows (the --from-json input), sent privately, because we cannot reach Data's database. And the commit of build_objective_set.py you want us to run.
   - Then we generate A and C with a seed only we know, publish the manifest and file hashes, keep the files, and send them at run time.
   Rules we would change before generation:
   a. Leave out any company, metric and period that a dev question or a holdout question already uses. We apply this, since only we see the holdout.
   b. Set D (messy wording): make the run without the company filter the primary one. With the clean question's filter, the 129 misspelled-company rewrites cannot fail. Keep the filtered run as a secondary result.
   c. Sets A to C: report the pre-check filters as a co-primary result next to the gold filters, since no user supplies the filing.
   d. Precision: take the digits printed in the linked cell as the floor, and watch trailing zeros and Casey's (reported in thousands) with "Answer in USD millions".
   e. Describe the sets as statement-table lookups with template wording on the listed metrics (the script has 15, the document says 17), not as overall accuracy.

4. Messy wording (427) and abstention (56) on final_v1: yes, please run each once. grade_answer_blocks.py cannot read them as they are, because the ids differ, so we added Week 9/scripts/grade_suite_answers.py. Please return one AnswerBlock per item keyed vid (messy) or sid (abstention), plus your clean per-question file, and we will score both, paired with clean.

What we need from you, in one place: the metric rows export and builder commit; your view on rule changes a to e; and the messy and abstention AnswerBlocks when run.

## Reply to three questions after the 11/19 meeting (Chinese, draft)

1. RAG 和 GraphRAG 的对比（按题型）：
   - 现在就能给：同一份 Microsoft 10-Q、同样 84 道题、同样取前 8 条的对比，按题型分。数字题 RAG 49/50、GraphRAG 25/50；文字题 RAG 22/27、GraphRAG 0/27。
   - 全部 155 道题、20 份 filing 的完整版：11/24 给。指标统一为“所需证据是否在前 10 条里”，按题型和路由分，并把“语料里没有”的题单独列出。
   - 依赖：GraphRAG 在 Gold Set v2.2 上重跑一次 graph search（Exhibit 21 已经入图，这次可以算关系题）。
2. 11/24 在 Agents 上重跑，需要 Agents 提供：
   - 一个能访问的 /query 地址（API v0.2）；或者他们自己跑我们的一条命令（Week 8/scripts/run_agent_api.py），把结果文件发回来。
   - 原样返回我们传入的 trace_id（用来对应题号）。
   - 一个关闭 fallback 的开关，这样可以比较有无 fallback。
   - 每题的耗时和 token 数；如果已经有 answer 字段，也请一起返回。
   - 只要符合 v0.2 合同就不需要适配函数；字段有变化的话，给我们一份字段对应说明即可。
3. UI 前端测试：之前没有计划，可以加一个小的冒烟测试。
   - 用 Playwright 让浏览器自动把约 20 道题提交到 UI，检查四件事：答案和 API 返回的一致；引用能显示并能点开；该拒答的题显示为拒答；每题的响应时间。
   - 需要 UI 组提供：UI 地址，以及输入框、提交按钮、答案区和引用区的稳定选择器（最好是 data-testid）。
   - UI 可用后两天内给结果，目标 11/26。

## Slack reply to RAG (six points of 11/19), draft

Thanks, all six work. Point by point:

1. Holdout A: you will have the file by DM on 11/20. The hash is unchanged (a6cf275c...). Answers within 24 hours is perfect.

2. Category counts (no questions). Batch A, 40 questions:
   - Type: numeric 30 (Microsoft 6, others 24), narrative 5 (2, 3), unanswerable 5 (2, 3). Microsoft 10 of 40.
   - Stress, 14: misspelled name 4, analyst wording 3, multi-step 2, relative period 2, cross-filing 2, narrative across sections 1.
   - Form: 10-K 26, 10-Q 8, several filings or none 6.
   Yes, B will fill the thin categories. Planned B, about 30: narrative 18, numeric 6 (all stress), unanswerable 6; stress about 18: misspelled name 2, analyst wording 3, multi-step 3, relative period 3, cross-filing 3, narrative across sections 4; Microsoft about 8. With A and B together every category then has at least 5: narrative 23, unanswerable 11, and each stress type 5 or 6.

3. Batch B: by 11/24 with its hash, for final_v2 at 789bf81. Same delivery as A.

4. Messy wording and abstention: please run Week 9/scripts/grade_suite_answers.py yourselves, then send us the AnswerBlocks (keyed vid and sid) and your clean per-question file. We re-score from the blocks and that is the official score, within a day of receiving them. Please run messy wording without the company filter as the primary run.

5. XBRL sets: we have not generated them yet, because we have not received the metric rows export (the --from-json input) or the builder commit to use. Once we have both, manifests and hashes for A and C follow within a day. On our side nothing waits for the 233-filing index except what your pre-registration assigns to it (sets B and C), so please confirm which sets you want generated now.

6. Cost and latency: agreed, same method. Tokens times list price plus wall-clock time per question. Three details so the numbers match: fix the price list and its date in the report; log retrieval and reader time separately, as your per_question.csv already does; report the median and the 95th percentile, not only the mean.
