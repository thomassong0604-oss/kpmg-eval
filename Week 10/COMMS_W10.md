# Week 10 messages (drafts; nothing here is sent automatically)

## Slack reply to RAG (Xiangxinrui), holdout A and the six arms, 11/23 (draft)

Hi Xiangxinrui, thank you, this is exactly what we needed: one run, the hash checked before opening, the persistence check, and a clean log. Both are scored. Details are in Week 10/README.md in kpmg-eval.

1. Holdout A, final_v1 (official)
   - Numeric: 28/30 = 0.933 (95% interval 0.787 to 0.982). Your development score was 0.935, so there is no drop on unseen questions. Normal wording 17/18, stress 11/12.
   - Unanswerable declined: 5/5.
   - Narrative: 3/5 with every required point, 15/17 points stated.
   - Citations: all 49 cited chunks exist, every answer cites a gold filing, every lookup figure is in a cited chunk.
   - Cost and time, from your log: $0.273 in total, median 3.0 s per question, p95 6.5 s.
   - Our grader and yours agree on all 35 questions both score.
   - The two misses: HA-009 gives the right amount with a negative sign for a question about expenditures. HA-029 declines the derived fourth-quarter figure although both inputs were retrieved.
   - One narrative question (HA-034) is recorded as disputed: your answer gives a reason that may be better than our gold answer, and the point it misses is a date the question does not ask for. The official score stays the strict one, since we do not change gold answers after seeing answers. Without that point it would be 4/5.

2. Six arms on messy wording (official, exploratory)
   - Numeric: 0.777 / 0.822 / 0.818 / 0.822 / 0.822 / 0.875 of 264. Same ranking and the same paired tests as yours.
   - Each arm is 2 higher than in your table. Both are rewrites of EV1-043, where the answer states the figure in the text and leaves the value field empty. Our grader reads the text; yours labels it no_value.
   - We agree with leaving out the NetApp 10-Q rewrites.
   - Your conclusion holds: the rule pre-check matches both LLM extractors on numbers (p = 1.0) and all three stay about 5 points under gold filters.
   - Two things the numeric table does not show. Agents' extractor answers more narrative rewrites than the pre-check (64/72 against 57/72, p = 0.039) and matches gold filters on categorical and false-premise questions. But in every arm except gold filters, 20 to 22 narrative answers cite only a filing other than the one asked about (0 with gold filters). So the narrative gain needs judging before anyone relies on it.

3. What we need from you
   a. Which three unanswerable rewrites you left out: we count 29, your table says 26.
   b. Your per-question file for final_v1 on the clean development questions, so we can pair each rewrite with its clean question.
   c. The hand-label file from 11/17 (20 questions, 126 points). We still have not received it.
   d. If you have budget, the narrative judge on the pre-check and Agents arms. That settles point 2.

4. Batch B comes by DM on 11/24 as planned, for final_v2 at 789bf81. We revised it on 11/23 before sending, so the hash changed: it now starts f6326a34 (Week 9/results/holdout_B_manifest.json).

## DM to RAG (Xiangxinrui) with holdout batch B, 11/24 (draft)

Hi Xiangxinrui, here is holdout batch B for final_v2 at 789bf81 (file attached: holdout_B.jsonl, 30 questions).

SHA-256: f6326a3486460526e1088f515bfd7b8eadf448109cacf8ca955bd98b3bea2c54

Please note the hash is new. We revised the file on 11/23, before anyone outside Eval saw it, and published the new hash in Week 9/results/holdout_B_manifest.json first (the old one started f6d3782d). Reason: batch A showed one required point that the question did not ask for (HA-034), so we checked batch B against one rule, every required point must be something the question asks for. Four questions were reworded to ask for a point they already required and one unasked point was removed. No answer, count or category changed.

Same procedure as batch A, please:
1. Check the hash before opening.
2. One run, final_v2, pre-registered default filters, no changes after opening.
3. Send back answer_blocks.jsonl and per_question.csv (with tokens, cost, retrieval and reader time), plus the commit and index version.

Contents: narrative 18, numeric 6 (all stress), unanswerable 6; Microsoft 7; stress 18. We score within a day of receiving the answers.
