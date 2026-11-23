# Week 10 (Nov 20 – Nov 26): first sealed-holdout score, and filter extraction on messy wording

Everything here is scored from files RAG sent on 11/23. The answer files, RAG's per-question logs and the holdout questions
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
  from another passage that is arguably better than the gold answer. A reviewer should decide whether the date stays a required point.
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
where RAG reports 26; we have asked which three differ.

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

Not done: pairing each rewrite with its clean question, because we have no per-question file for `final_v1` on the clean
development questions. Requested from RAG.

## 3. Files

| File | What |
|---|---|
| `scripts/score_holdout.py` | scores a sealed batch from RAG's AnswerBlocks: numeric, refusals, narrative points, citations, cost and latency |
| `scripts/score_query_rewrite.py` | scores the six arms with Week 9's messy-wording scorer and compares them pairwise |
| `results/holdout_A_final_v1.json`, `_per_question.csv` | section 1 |
| `results/query_rewrite_arms.json`, `_per_item.csv` | section 2 |
| `tests/test_week10.py` | consistency checks on the result files, and that no question or answer text is published |
| `COMMS_W10.md` | message drafts |
| `private/` (not in git) | RAG's answer files and logs, narrative verdicts with quotes |
