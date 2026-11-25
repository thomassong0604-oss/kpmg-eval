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

## Slack reply to RAG (Xiangxinrui), batch B and the four follow-ups, 11/24 (draft)

Hi Xiangxinrui, thank you for all five messages. Batch B is scored and everything you sent is checked. Details are in Week 10/README.md, sections 3 to 6.

1. Holdout B, final_v2 (official)
- Narrative: 17/18 with every required point, 57/58 points. Your development result for this variant was 24/27, so the gain holds on unseen questions.
- Numeric: 5/6. Unanswerable declined: 6/6.
- Citations: all 33 cited chunks exist and every answer cites a gold filing.
- Cost and time match your log: $0.222, median 2.9 s per question.
- Our grader and yours agree on all 12 questions both score.
- The two misses: HB-016 gives one of its two figures and says the other is not in its excerpts. HB-024 declines the change between the annual and the quarterly balance sheet. With HA-029, the two-filing questions are 3 of 5 across both batches, and both misses are declines, not wrong numbers.
- HB-004 is our mistake: the question says revenue fell, but reported revenue rose slightly and the 2% fall is currency-neutral. Your answer corrected that and still gave every point, so it passes.
- HB-001: thank you for disclosing the preview. It is in the record, and without it the narrative score is 16/17. We will send future files zipped so Slack cannot preview them.

2. Human review of the 23 holdout narrative answers: yes, please go ahead by 11/27, same format as 11/17. The narrative scores above come from our judge, and your hand labels show it gives credit slightly too easily (point 3), so a human check matters here. Our scores per question are in this message and in the Week 10 README, so please have the two raters label from the answers and required points only, before reading either. We will also label the same 23 on our side so we can report agreement between raters.

3. Hand labels from 11/17: received, thank you.
- Your kappas reproduce: gpt-6-sol against your raters is 0.93 (final_v1) and 0.90 (final_v2), 124 of 126 points.
- Our judge against your raters: 97 of 100 points, kappa 0.83.
- Every disagreement, for both judges, is the judge giving credit where your raters did not. On EV1-045 your raters and gpt-6-sol are right and our judge was wrong.
- With your labels applied, our Week 9 counts become 25/38 for final_v1 and 32/38 for final_v2 (were 26 and 34). The gain from v1 to v2 stays.

4. Your follow-ups
a. 29 against 26: understood, the three graph-route rewrites. Both counts are 100%.
b. Clean against messy, paired: no rewrite is right where its clean question was wrong. Of the 252 pairs right when clean, 21 are lost with gold filters, 35 with the rule pre-check, 47 with no filters. With the pre-check, 30 of the 35 are declines, so it fails safely. Yes please to the re-run of final_v1 on the fixed index, so both sides of the pairing use one index.
d. Thank you for running the judge on both arms. Every total in your message reproduces from your table, and your answered and citation flags match ours on all 72 rewrites. We agree with your reading and with the recommended setup. One thing we would add to the citation limitation: in each arm, 4 of the 5 contradictions come from answers that cite only another filing (4 of 22, against 1 of 35 and 1 of 42). It is two questions, so a lead, not a result.

5. XBRL A and C: we are still missing the two inputs, so nothing is generated yet.
a. The saved pull of the metric rows (the --from-json input), by DM.
b. The commit of build_objective_set.py you want us to run.
c. A yes or no on the four rule changes we proposed (leave out anything a dev or holdout question uses; unfiltered run as primary for messy wording; pre-check filters as co-primary; precision from the printed digits).
Once we have these, manifests and hashes for A and C follow within a day.

## Slack reply to RAG (Xiangxinrui), XBRL sets A and C, 11/25 (draft)

Hi Xiangxinrui, thank you, all three inputs arrived and both sets are built. No need to apologise, this was fast.

1. What we did
- Metric rows: hash checked, 7c7bb541…8496, 19,474 rows.
- Built A and C with your scripts/build_objective_set.py at 6b7d53b, unchanged, with a 128-bit seed only we know, excluding the dev set and both holdout batches.
- Manifests and hashes are public: Week 10/results/xbrl_set_A_manifest.json and xbrl_set_C_manifest.json in kpmg-eval. We publish the seed after the last run, so anyone can rebuild both files.

2. Set A is ready: 150 questions, 15 per company. It comes by DM as set_A.zip.
- SHA-256 of set_A.zip: a7f6bc11260636a0188b89202dd6281be5ad12ca3433b5af7283276a13703b99
- SHA-256 of set_A.jsonl inside: 18794c0f4bb39da6977d39fe13d1171615c9b17937fcc64f5d9c284bc49020a5
- Same procedure as the holdout: check the hash before opening, one run per pre-registered configuration (gold filters and pre-check filters), then answer_blocks.jsonl and per_question.csv for each.

3. Checks we ran without anyone reading the questions
- Exclusion: 62 rows left out because a dev or holdout question uses them. Zero overlap, by concept and again by value.
- Precision floor equals the printed digits and the asked unit equals the table's scale: 150 of 150.
- All 20 gold filings are in the frozen index and every printed figure is present in its filing's chunks, so every Set A question is answerable from the index.
- Our grader, dry run: perfect answers pass 150 of 150; 1% off, rounded and sign-flipped answers fail.

4. Two scoring rules we are fixing now, before any answer exists. Please say if you object.
a. Trailing zeros: an answer equal to the gold value is correct even if it drops zeros printed after the decimal point ("7,043" for a cell printed "7,043.0"). This affects 4 questions in A and 1 in C.
b. Sign: strict is primary, with the XBRL sign (cash paid is positive, a loss is negative). We will also report a second score that ignores the sign on the cash-outflow questions only (capital expenditures and dividends, 22 in A), since those cells are printed in parentheses. This is the HA-009 pattern.

5. Set C is built and sealed: 100 questions, one per company, 94 of them from 10-Qs. Your scope note is fine with us. Once index_full is recorded, send us its id and filing count and C follows by DM the same way.

6. Thank you for the final_v1 re-run and for the human review by 11/27. We will pair the re-run as soon as it arrives.

## DM to RAG with Set A (draft)

Hi Xiangxinrui, Set A is attached as set_A.zip (150 questions).

SHA-256 of set_A.zip: a7f6bc11260636a0188b89202dd6281be5ad12ca3433b5af7283276a13703b99
SHA-256 of set_A.jsonl inside: 18794c0f4bb39da6977d39fe13d1171615c9b17937fcc64f5d9c284bc49020a5

Both are in Week 10/results/xbrl_set_A_manifest.json. Please check the hash before opening, then run once per pre-registered configuration on the frozen index and send back answer_blocks.jsonl and per_question.csv for each. Thank you!
