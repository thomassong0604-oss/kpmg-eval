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
