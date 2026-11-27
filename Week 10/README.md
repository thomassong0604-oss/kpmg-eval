# Week 10 (Nov 20 – Nov 26): both sealed-holdout scores, filter extraction on messy wording, the judge against hand labels, and XBRL sets A and C

Everything here is scored or built from files RAG sent on 11/23, 11/24 and 11/25. The answer files, RAG's per-question logs and the holdout questions
stay in the git-ignored `private/` folder; the result files hold labels and ids only.

## 1. Holdout batch A, RAG `final_v1` (official score)

`python scripts/score_holdout.py` → `results/holdout_A_final_v1.json`, `results/holdout_A_final_v1_per_question.csv`

Run by RAG once, `--preset final_v1 --backend chroma`, gold filters (the pre-registered default), code at main 0685fd4,
index `chroma_C1` 7a7ad9801f86. The sealed file's SHA-256 still matches the hash published on 11/16 (a6cf275c…0680).
Same graders as the development set; no gold answer was changed after the answers arrived.

| Measure | Holdout A | 95% interval | Note |
|---|---|---|---|
| Numeric accuracy | 28/30 = 0.933 | 0.787–0.982 | development set: 0.935 (87/93), as reported by RAG |
| – normal wording | 17/18 | 0.742–0.990 | |
| – stress questions | 11/12 | 0.646–0.985 | the miss is one of the 2 cross-filing questions |
| – Microsoft / other nine | 5/6 / 23/24 | | |
| – 10-K / 10-Q / several filings | 20/20 / 7/8 / 1/2 | | |
| Unanswerable declined | 5/5 | 0.566–1.000 | |
| Narrative, every required point | 3/5 | 0.231–0.882 | judge: Claude, Week 8 rubric with quote guard |
| Narrative, points stated | 15/17 = 0.882 | 0.657–0.967 | |
| Cited chunks exist | 49/49 | | |
| Answers citing a gold filing | 34/34 | | |
| Lookup figure found in a cited chunk | 25/25 | | |
| Cost | $0.273 total, $0.0068 per question | | 254,241 prompt and 3,748 completion tokens (RAG's log) |
| Time per question | median 3.0 s, p95 6.5 s | | retrieval 0.6 s / 1.7 s, reader 2.1 s / 5.1 s |

What it says: accuracy on questions RAG had never seen is the same as on the development set (0.933 against 0.935), so the
development score was not inflated by tuning. With 30 questions the interval is wide; batch B and the larger sets narrow it.

The two numeric misses, both labelled the same way by RAG's own grader:

- **HA-009, wrong sign.** A cash-flow line asked as "expenditures": the answer gives the right magnitude as a negative number
  (the statement's presentation). The value field would mislead anything that reads it, so it stays a miss.
- **HA-029, declined an answerable question.** A fourth-quarter figure that has to be derived from the annual and the
  nine-month totals. RAG's log says both figures were retrieved; the reader used one filing and declined.

Narrative, two things for a human to look at (scores above are the strict ones):

- **HA-034** states 3 of 4 points. The missing point is a date the question does not ask for, and the answer gives a reason
  from another passage that is arguably better than the gold answer.
  **Decision (11/23):** the official score stays the strict one, because no gold answer changes after the answers are seen.
  HA-034 is recorded as a disputed question; without the date point narrative would be 4/5 (15/16 points). The rule it
  suggests (every required point must be something the question asks for) was applied to batch B before delivery
  (`../Week 9/README.md`, section 9).
- **HA-033** says "0.2 percentage points" where the filing says "20 basis points". Counted as stated.

Our grader and RAG's own grader agree on all 35 questions that both score.

## 2. Query rewriting against Agents' extraction on `messy_wording_v1` (official score, exploratory)

`python scripts/score_query_rewrite.py` → `results/query_rewrite_arms.json`, `results/query_rewrite_arms_per_item.csv`

RAG's experiment after the mentor's question on 11/19: the same reader (`final_v1`) on the 427 rewrites, changing only where
the retrieval filters come from. Exploratory, not pre-registered; the fifth arm was designed after seeing the others on this suite.

| Arm | Numeric accuracy | 95% interval | Company typo | Term typo | Casual | Answerable declined | Narrative answered |
|---|---|---|---|---|---|---|---|
| No filters | 205/264 = 0.777 | 0.723–0.823 | 61/82 | 68/89 | 76/93 | 102/389 | 52/72 |
| Rule pre-check | 217/264 = 0.822 | 0.771–0.863 | 70/82 | 71/89 | 76/93 | 86/389 | 57/72 |
| A: RAG-side LLM + pre-check | 216/264 = 0.818 | 0.767–0.860 | 72/82 | 70/89 | 74/93 | 86/389 | 56/72 |
| B: Agents' LLM extractor (d89208c) | 217/264 = 0.822 | 0.771–0.863 | 69/82 | 74/89 | 74/93 | 74/389 | 64/72 |
| B + pre-check (post-hoc) | 217/264 = 0.822 | 0.771–0.863 | 71/82 | 71/89 | 75/93 | 79/389 | 62/72 |
| Gold filters (upper bound) | 231/264 = 0.875 | 0.830–0.910 | 75/82 | 77/89 | 79/93 | 59/389 | 64/72 |

Every arm declined all 29 unanswerable rewrites and all 9 rewrites of the three questions whose filing (NetApp's 10-Q) is not
in the round-1 corpus; those 9 are left out of the rates above (RAG left them out of numeric accuracy too).

**Against RAG's own table.** Same ranking and the same paired tests; every arm is 2 higher in ours (for example 205 against 203).
Both are rewrites of one question (EV1-043) where the answer states the figure in its text but leaves the value field empty.
Our grader reads the text, as it did on the development set; RAG's labels them `no_value`. We count 29 unanswerable rewrites
where RAG reports 26: RAG keeps three fabricated-relationship rewrites (graph route) in a separate group. All were declined in every arm,
so both counts are 100%.

**Paired comparison on the 264 number questions (exact McNemar).**

| Pair | Only first right | Only second right | p |
|---|---|---|---|
| No filters vs rule pre-check | 3 | 15 | 0.0075 |
| No filters vs A | 8 | 19 | 0.052 |
| No filters vs B | 9 | 21 | 0.043 |
| Rule pre-check vs A | 6 | 5 | 1.0 |
| Rule pre-check vs B | 8 | 8 | 1.0 |
| Rule pre-check vs gold filters | 2 | 16 | 0.0013 |
| B vs gold filters | 0 | 14 | 0.0001 |

What it says:

1. **Any filter extraction helps on numbers, and the free rule-based one is as good as either LLM** (0.822, 0.818, 0.822;
   p = 1.0 between them). RAG's choice of the rule pre-check as default is supported.
2. **Extraction still costs about 5 points against perfect filters** (0.822 against 0.875, p ≈ 0.001). 33 number questions are
   wrong even with gold filters; 14 to 17 more are lost to the filter step, 29 with no filters.
3. **Outside numbers the picture differs, which the numeric table alone does not show.** Agents' extractor answers more
   narrative rewrites than the rule pre-check (64/72 against 57/72; 8 against 1 discordant, p = 0.039) and matches gold filters
   on categorical (15/33) and false-premise questions (14/20). "Answered" is not "right": these answers were not judged.
4. **A citation risk to check before trusting point 3.** In every arm except gold filters, 20 to 22 narrative answers cite
   only filings other than the one the question is about (0 with gold filters); for Agents' extractor that is 22 of its 64.
   Number answers do not show this (every one cites a gold filing). These need the narrative judge or a human read.
5. Categorical questions are declined often in every arm (18 to 23 of 33), including with gold filters.

## 3. Holdout batch B, RAG `final_v2` (official score)

`python scripts/score_holdout.py --batch B --system final_v2` → `results/holdout_B_final_v2.json`, `_per_question.csv`

Run by RAG once on 11/24: `final_v2` (tag 789bf81, code at main 69198ee), pre-registered default filters, 30 fresh API calls.
The sealed file's SHA-256 matches the revised hash published on 11/23 (f6326a34…2c54). Batch B was built for the thin
categories, so it is mostly narrative.

| Measure | Holdout B | 95% interval | Note |
|---|---|---|---|
| Narrative, every required point | 17/18 = 0.944 | 0.742–0.990 | development set, same variant: 24/27 (22/27 with hand labels, section 4) |
| Narrative, points stated | 57/58 | 0.909–0.997 | judge: Claude, Week 8 rubric with quote guard |
| – normal / stress | 7/7 / 10/11 | | the miss is one of the 4 questions that need two sections |
| Numeric accuracy (all stress questions) | 5/6 | 0.436–0.970 | multi-step 3/3, cross-filing 2/3 |
| Unanswerable declined | 6/6 | 0.610–1.000 | |
| Cited chunks exist | 33/33 | | |
| Answers citing a gold filing | 22/22 | | |
| Cost | $0.222 total, $0.0074 per question | | 205,211 prompt and 3,442 completion tokens (RAG's log) |
| Time per question | median 2.9 s, p95 5.6 s | | retrieval 0.3 s / 1.8 s, reader 2.3 s / 4.2 s (nearest-rank percentiles) |

What it says: `final_v2`'s narrative gain holds on questions it was not tuned on. Our grader and RAG's agree on all 12 questions both score.

The two misses and what to keep in mind:

- **HB-016, one of two points.** The answer gives the second figure and says the first is not in its excerpts, so the system marks it
  not answered. A retrieval miss on one of two sections.
- **HB-024, declined an answerable question.** A change between an annual and a quarterly balance sheet; RAG's log says retrieval did
  not return the figures. With HA-029 in batch A, the two-filing questions are 3 of 5 across both batches, and both misses are declines, not wrong numbers.
- **The narrative score is now confirmed by human raters** (section 9): two RAG raters per answer, and their consensus equals our
  judge on every one of the 58 points.
- **HB-004 is our error.** The question says revenue fell; in the filing reported revenue rose slightly and the 2% fall is
  currency-neutral. The answer corrects this and still states every point, so it passes; the question is recorded as badly worded.
  The review on 11/23 did not catch it.
- **HB-001 was visible before the run** in a Slack message preview (reported by RAG; the system has been frozen since 11/17).
  Without it the narrative score is 16/17.

## 4. Both judges against RAG's hand labels

`python scripts/validate_hand_labels.py` → `results/judge_vs_hand_labels.json`

Two RAG members labelled 20 development questions blind on 11/17: 126 required points over `final_v1` and `final_v2`. The file reached us on 11/24.

| Judge | Points compared | Agreement | Cohen's kappa | Disagreements |
|---|---|---|---|---|
| gpt-6-sol (RAG's run of our script) | 126 | 124 = 98.4% | 0.92 (0.93 `final_v1`, 0.90 `final_v2`) | 2, the same point in both runs |
| Claude (Eval's judge, Week 9) | 100 | 97 = 97.0% | 0.83 (0.91 `final_v1`, 0.65 `final_v2`) | 3, on two questions |

- RAG's reported kappas (0.93 and 0.90) reproduce from the file.
- **Every disagreement goes the same way: the judge gave credit and the human did not.** Neither judge was ever stricter than the humans.
  On EV1-045 the humans and gpt-6-sol both say a point is contradicted where our judge said stated, so our judge was wrong there.
- With the human verdict used wherever one exists, our Week 9 counts drop by one or two: `final_v1` 26/38 → 25/38, the `final_v2`
  variant 34/38 → 32/38 (narrative only: 17/27 → 16/27 and 24/27 → 22/27). The gain from v1 to v2 stays (+7 instead of +8).
- Limits: only 15 of the 126 labels are not "stated", so kappa rests on few cases (the 0.65 comes from 2 disagreements in 50 points);
  26 points on two questions were outside our judge's question set; the raters are RAG members, and Eval has not labelled these points itself.

## 5. Clean wording against messy wording, question by question

`python scripts/score_rewrite_followups.py` → `results/query_rewrite_followups.json`

RAG sent `final_v1`'s per-question file on the 155 clean development questions. Re-graded with our grader it is 89/93 on in-corpus
number questions (RAG's own grader: 87/93; the two differences are grading rules fixed in Gold Set v2.2). Each number rewrite is paired with its clean question.

| Arm on the rewrites | Right in both | Right only when clean | Right only when messy | Wrong in both | Questions right clean but wrong in a rewrite |
|---|---|---|---|---|---|
| Gold filters | 231 | 21 | 0 | 12 | 16 of 89 |
| Rule pre-check | 217 | 35 | 0 | 12 | 21 of 89 |
| A: RAG-side LLM + pre-check | 216 | 36 | 0 | 12 | 21 of 89 |
| B: Agents' LLM extractor | 217 | 35 | 0 | 12 | 20 of 89 |
| No filters | 205 | 47 | 0 | 12 | 29 of 89 |

- **Messy wording only ever loses answers**: no rewrite is right where its clean question was wrong (p < 0.0001 in every arm).
- **The drop splits in two.** Clean 0.955 (252 of the 264 pairs) → 0.875 with perfect filters (wording alone, 21 answers) → 0.822 with the rule pre-check
  (finding the filing, 14 more) → 0.777 with no filters.
- **It fails safely.** With the pre-check, 30 of the 35 lost answers are declines; 5 are wrong or imprecise numbers.
- Caveat: the clean run (11/16) used the index before the persistence fix, the arms the fixed one. RAG has offered to re-run it (about $1).
  Rewrites of one question are not independent, so the question-level column is the safer figure.

## 6. Narrative rewrites, judged (RAG's run of our judge)

RAG ran the Week 8 judge script unchanged (gpt-6-sol) on the 72 in-corpus narrative rewrites of two arms. We did not run it; we checked
every total in their message against their per-rewrite table and crossed it with our own citation check. All totals reproduce, and their
answered and citation flags match ours on every rewrite.

| | Rule pre-check | Agents' extractor |
|---|---|---|
| Every required point (not answered = not passed) | 29/72 = 0.40 | 34/72 = 0.47 |
| Mean point recall | 0.635 | 0.729 |
| Paired, every point | 1 only pre-check | 6 only Agents (p = 0.125) |
| Answers citing a gold filing: every point / contradictions | 21 of 35 / 1 | 24 of 42 / 1 |
| Answers citing only other filings: every point / contradictions | 8 of 22 / 4 | 10 of 22 / 4 |

- Agents' extra narrative answers are mostly real (5 of the 8 it alone answers state every point), but the gain is not significant. RAG's recommended setup is unchanged, and we agree.
- **What we add:** 4 of the 5 contradictions in each arm come from answers that cite only another filing (4 of 22, against 1 of 35 and 1 of 42;
  Fisher exact p = 0.07 and 0.04). They come from two questions, so this is a lead, not a result. It suggests the wrong-filing answers
  are an accuracy risk as well as a citation one.
- Narrative answers are much more fragile to messy wording than numbers: 0.40 to 0.47 here against 17/30 for `final_v1` on the clean questions (RAG's figure).

## 7. XBRL objective sets A and C (built and held by Eval)

`python scripts/check_objective_sets.py` → `results/xbrl_set_A_manifest.json`, `results/xbrl_set_C_manifest.json`

RAG pre-registered five objective sets drawn from Data's XBRL metrics. Eval holds A and C so RAG cannot see them before the run.
On 11/25 RAG sent the three inputs: the saved metric rows (19,474 rows, SHA-256 7c7bb541…8496, verified), the builder commit
(6b7d53b) and a yes to our four rules. We ran RAG's `scripts/build_objective_set.py` unchanged with a 128-bit seed only Eval
knows, leaving out everything the development set and both holdout batches use.

| | Set A | Set C |
|---|---|---|
| Questions | 150 (15 for each of the ten companies) | 100 (one for each of 100 other companies) |
| Runs on | the frozen round-1 index (20 filings) | `index_full`, once RAG has added the 412 non-core filings |
| SHA-256 of the question file | 18794c0f…20a5 | 53664be8…3b13 |
| Filings | 10-K 102, 10-Q 48 | 10-K 6, 10-Q 94 |
| Answer unit | millions 125, thousands 12, per share 13 | millions 67, thousands 25, per share 8 |
| Rows left out because a dev or holdout question uses them | 62 | 0 (no core company is in C) |
| Status | sent to RAG by DM on 11/25; run as Sets A and B | **retired 11/26, never run** (see the update below) |

Nobody has read the questions. The checks ran automatically; for four items a check flagged, only the printed figure and value were looked at.

| Check | Set A | Set C |
|---|---|---|
| Overlap with dev or holdout questions, by XBRL concept and again by value | 0 | 0 |
| Precision floor equals the digits printed in the gold cell | 150/150 | 100/100 |
| Asked unit equals the table's scale | 150/150 | 100/100 |
| Gold value equals the printed figure | 150/150 | 100/100 |
| Gold filing is in the frozen index, and the printed figure is in its chunks | 150/150 | not applicable yet |
| Grader dry run: perfect answers / 1% off / rounded to 2 figures / sign flipped | 150 / 0 / 1 of 133 / 0 pass | 100 / 0 / 0 of 90 / 0 pass |

So every Set A question can be answered from the frozen index, and the grader passes exactly the answers it should.
(The one rounded answer that passes is a figure printed as "30.0": two significant figures already equal it.)

Two scoring rules fixed now, before any answer exists:

- **Trailing zeros.** An answer equal to the gold value is correct even if it drops zeros printed after the decimal point
  ("7,043" for a cell printed "7,043.0"). Without this the precision floor would fail an exact answer. 4 questions in A, 1 in C.
- **Sign.** Strict is the primary score: the gold value carries the XBRL sign, so cash paid is positive and a loss is negative.
  A second, labelled score ignores the sign on the cash-outflow questions only (capital expenditures and dividends: 22 in A,
  5 in C), because every one of those cells is printed in parentheses and `final_v1` answered a question of this kind with a
  negative number on holdout A.

The seed is published after the last run; with it, the builder at 6b7d53b and the same rows reproduce both files exactly.

**Update 11/26: Set C drawn again.** The first Set C file and the first seed reached RAG by mistake on 11/25, before the run. RAG
disclosed it the next day, reports the file unopened and the seed unused, and suggested a new draw. The first Set C
(53664be8…3b13) is retired and was never run. The replacement was drawn on 11/26 with a new 128-bit seed:
`results/xbrl_set_C2_manifest.json`, SHA-256 756e26b7…6e76, 100 questions, one per company, 10-Q 90 and 10-K 10. Every check
above passes on it (100/100, zero overlap, no core company, dry run 100 / 0 / 0 / 0) and no item was looked at.
The seed file for this set also reached RAG, in the same DM as the set (disclosed 11/27, unused and deleted). The set is run as it is:
RAG held the questions from that DM anyway, so the seed gives nothing the delivered file did not.
RAG's `index_full` (37c4eb2f1628) was recorded in their pre-registration at 0ca6fb3 on 11/24, which we verified in their
repository, so the index was fixed before this draw. Sets A and B are not affected: RAG already held those questions for the run.

## 8. XBRL Set B, RAG `final_v1` on the full index (official score)

`python scripts/score_objective_set.py --set B --returns private/xbrl/returns/xbrl_B_return` → `results/xbrl_B_final_v1.json`, `_per_question.csv`

Set B is Set A's 150 questions asked against `index_full`: 645 filings from 261 companies, 102,760 chunks, about 28 times the
frozen index. RAG ran each pre-registered filter configuration once on 11/25 and returned the files with checksums (all verify).
The workspace had been reset, so `scripts/rebuild_set_A.py` regenerated the question file from the returned questions and the
metric rows; it reproduces the published SHA-256 exactly, so the gold answers used here are the sealed ones.

| | Gold filters | Pre-check filters |
|---|---|---|
| Numeric accuracy, strict (primary) | 131/150 = 0.873 (0.811–0.917) | 115/150 = 0.767 (0.693–0.827) |
| Ignoring the sign on the 22 cash-outflow questions | 136/150 = 0.907 | 117/150 = 0.780 |
| Declined an answerable question | 10 | 29 |
| Wrong answers given | 9 (7 sign, 2 value) | 6 (5 sign, 1 value) |
| Accuracy when it answers | 131/140 = 0.936 | 115/121 = 0.950 |
| Answers citing the gold filing | 140/140 | 86/121 |
| Cost | $0.942 | $0.910 |
| Reader time, median / p95 | 3.4 s / 6.0 s | 2.9 s / 5.0 s |

Paired on the 150 questions: both right 107, only gold filters 24, only pre-check 8, neither 11 (exact McNemar p = 0.007).
Our grader and RAG's own agree on all 300 answers. The trailing-zero rule was never needed.

What it says:

1. **On an index 28 times larger the reader still rarely gives a wrong number**: 2 and 1 wrong values in 150. The other wrong answers are signs.
2. **Finding the filing is what costs accuracy.** With the rule pre-check instead of perfect filters accuracy falls 10.6 points, and
   19 of the 24 lost answers are declines. Balance-sheet questions lose most (46/51 → 33/51).
3. **Sign is a real, separate weakness.** 7 answers have the right amount with the wrong sign under gold filters: 5 on the
   cash-outflow questions (the pattern seen on holdout A) and 2 on cost of revenue. Under pre-check it also appears on the current portion of long-term debt.
4. **Misses concentrate in three companies.** With gold filters Apple is 8/15, McKesson 10/15 and Medtronic 11/15; the other seven are 102/105.
   With the pre-check Medtronic falls to 6/15.
5. **For numbers, citing another filing is mostly legitimate.** Under the pre-check 35 answers cite only a filing other than the gold
   one; 34 of those are prior-period questions and 34 are right, which is consistent with the same figure being printed in the
   filing whose own period it is. This differs from narrative answers (section 6), where wrong-filing answers carried the contradictions.

Not yet done: Set A (the same questions on the frozen index) is run but its return file has not reached this workspace, so the
frozen-against-full comparison, which is the point of Set B, is still open.


## 9. Human rating of the 23 holdout narrative answers

`python scripts/validate_holdout_labels.py` → `results/holdout_narrative_hand_labels.json`

RAG had every holdout narrative answer (5 in batch A, 18 in batch B; 75 required points) labelled by two of its members,
blind to both judges and to our scores, and sent the labels on 11/27 with an adjudication log.

| Comparison | Points | Agree | Cohen's kappa |
|---|---|---|---|
| The two raters with each other | 75 | 71 = 94.7% | 0.58 |
| Our judge with the raters' consensus | 75 | 75 = 100% | 1.00 |
| Our judge on the points where both raters agree | 71 | 71 = 100% | 1.00 |
| Our judge with each rater's own label | 150 | 146 = 97.3% | 0.74 |

- **The holdout narrative scores stand, now with a human check:** batch A 3/5 answers with every point (15/17 points), batch B 17/18 (57/58).
  The consensus names the same three missing points as our judge.
- **The four points the raters split on are all ones where our judge gave credit** and one rater did not, in each case because the answer
  paraphrases the point ("0.2 percentage points" for "20 basis points", "fell 6%" for "decreased"). The rubric counts a paraphrase as stated,
  and the adjudication went that way. We had flagged two of the four as close calls when we published the scores.
- This fits section 4: the judge does not miss points the humans see, and where humans hesitate it sides with the more generous reading.
- RAG's rater agreement figures (71/75, kappa 0.58) reproduce from their file.

Limits, stated plainly: the raters belong to the team whose system is rated, and Eval has not labelled these answers itself. 71 of the
75 consensus labels are two independent raters agreeing; the other 4 were adjudicated after our per-question counts were public, 3 by the
RAG lead and 1 by an AI assistant, as RAG's own log states. Only 3 labels are not "stated", so kappa rests on very few cases.

## 10. XBRL Set C2, RAG `final_v1` on 100 companies it was never developed on (official score)

`python scripts/score_objective_set.py --set C --name C2 --returns private/xbrl/returns/xbrl_C2_return` → `results/xbrl_C2_final_v1.json`, `_per_question.csv`
`python scripts/review_wrong_values.py` → `results/xbrl_wrong_value_review.json`

One question for each of 100 companies outside the ten, 90 of them from 10-Qs, asked against `index_full`. RAG ran each
configuration once on 11/27 after our go-ahead; the six returned files match their checksums and the question file matches the C2 manifest.

| | Gold filters | Pre-check filters |
|---|---|---|
| Numeric accuracy, strict (primary) | 76/100 = 0.760 (0.668–0.833) | 75/100 = 0.750 (0.657–0.825) |
| Ignoring the sign on the 10 cash-outflow questions | 79/100 | 78/100 |
| Declined an answerable question | 14 | 15 |
| Wrong answers given | 10 (5 value, 3 sign, 2 rounded) | 10 (same) |
| Accuracy when it answers | 76/86 = 0.884 | 75/85 = 0.882 |
| Answers citing the gold filing | 86/86 | 85/85 |
| Cost | $0.595 | $0.600 |
| Reader time, median / p95 | 2.1 s / 3.9 s | 2.3 s / 3.9 s |

Our grader and RAG's own agree on all 200 answers. The trailing-zero rule was never needed.

What it says:

1. **Accuracy is about 11 points lower on companies the system was not developed on**: 0.760 against 0.873 on the ten core companies
   (Set B, same index and filters; Fisher exact p = 0.026). The two sets differ in mix (C2 is mostly 10-Qs and one question per
   company), so this is an indication, not a controlled comparison.
2. **Here the pre-check costs nothing** (75 against 76, one question). On Set B it cost 10.6 points. The difference fits the index:
   the core companies have about 23 filings each to choose from, the others one or two.
3. **Every wrong value on Sets B and C2 is the same thing, and it is partly our question's fault.** All 7 (2 on B, 5 on C2) are answers
   that give the consolidated figure where the gold cell is the "attributable to the company" line. The question says only "net income"
   or "total shareholders' equity". The reader did not once give a figure that is not in the filing. They stay wrong in the official
   score; if the consolidated figure were accepted, B would be 133/150 and C2 81/100 (post-hoc, for information).
4. **Two answers are rounded figures taken from prose** ("$1.0 billion" where the statement prints 1,048).
5. **The sign pattern repeats**: 3 of the 10 cash-outflow questions are answered with a negative number.
6. **Some line items are much weaker than others**: cost of revenue 2/8 (5 declines; on Set B it was also the weakest at 16/21),
   capital expenditures 4/8, total liabilities 3/6, against 38/38 for revenue, cash, operating cash flow and diluted EPS.
7. The known data issue RAG recorded before opening the file (missing section labels for 10 filings of six companies) touches
   3 questions in this set; all 3 are answered correctly.

Sets A and B run on the ten core companies; Set A's return file has still not reached this workspace, so the
frozen-against-full comparison remains open.

## 11. Files

| File | What |
|---|---|
| `scripts/score_holdout.py` | scores a sealed batch from RAG's AnswerBlocks: numeric, refusals, narrative points, citations, cost and latency |
| `scripts/score_query_rewrite.py` | scores the six arms with Week 9's messy-wording scorer and compares them pairwise |
| `scripts/validate_hand_labels.py` | both judges against RAG's hand labels; last week's pass counts with the human verdicts applied |
| `scripts/score_rewrite_followups.py` | clean against messy pairing; checks RAG's judged narrative table |
| `scripts/check_objective_sets.py` | checks XBRL sets A and C without reading them, zips them, writes the public manifests; holds the scoring rules for the run |
| `scripts/rebuild_set_A.py` | regenerates Set A's question file without the seed and accepts it only if the published hash matches |
| `scripts/score_objective_set.py` | official score of an objective-set run, both filter configurations, with the rules fixed on 11/25 |
| `results/xbrl_set_A_manifest.json`, `xbrl_set_C_manifest.json` (retired), `xbrl_set_C2_manifest.json` | section 7 |
| `results/xbrl_B_final_v1.json`, `_per_question.csv` | section 8 |
| `scripts/validate_holdout_labels.py`, `results/holdout_narrative_hand_labels.json` | section 9 |
| `results/xbrl_C2_final_v1.json`, `_per_question.csv` | section 10 |
| `scripts/review_wrong_values.py`, `results/xbrl_wrong_value_review.json` | section 10: what the wrong values on B and C2 have in common |
| `results/holdout_A_final_v1.json`, `_per_question.csv` | section 1 |
| `results/holdout_B_final_v2.json`, `_per_question.csv` | section 3 |
| `results/judge_vs_hand_labels.json` | section 4 |
| `results/query_rewrite_followups.json` | sections 5 and 6 |
| `results/query_rewrite_arms.json`, `_per_item.csv` | section 2 |
| `tests/test_week10.py` | consistency checks on the result files, and that no question or answer text is published |
| `COMMS_W10.md` | message drafts |
| `private/` (not in git) | RAG's answer files and logs, narrative verdicts with quotes |
