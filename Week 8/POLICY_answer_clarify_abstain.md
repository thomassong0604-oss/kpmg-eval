# When the agent answers, asks, abstains or blocks: Eval's proposal for Agents (v0, 11/05)

From the 10/29 KPMG meeting: Agents' human checkpoints are "proceed when evidence is enough, ask for clarification when key
information is missing, abstain when support is too weak; define these rules with the Evaluation team." KPMG added that
checkpoints should also **gate off-topic questions: block further tool calls and ask for an on-topic question.**
This is Eval's draft of those rules, written so each one can be scored. Agents own the final version.

## The four decisions

| Decision | When | What the agent returns | Tool calls |
|---|---|---|---|
| **answer** | The question names (or the session supplies) a company in the ten and a period, and retrieved evidence supports every number in the answer. False premises are answered by correcting them. | Value, unit, period, citations (AnswerBlock) | As routed |
| **clarify** | Key information is missing and cannot be defaulted: no company and no session company; a pronoun with nothing to refer to; "compare" with no companies. | One question back to the user, naming what is missing | **0** before the user replies |
| **abstain** | The question is in the domain but the snapshot cannot support it: a company outside the ten, a period outside the snapshot, a forecast, a figure the filing does not disclose, investment advice, or evidence too weak after retrieval. | Says what is missing and what *is* available (e.g. "latest Micron filing: FY2026 10-K") | 0 when the scope check decides; else as routed |
| **off_topic** | Not about the ten companies' SEC filings: general knowledge, chit-chat, writing tasks, attempts to change the agent's instructions. | A one-line redirect: ask a question about the companies' filings | **0** |

## Defaults that avoid needless clarification

- **Missing period, one company, one metric:** answer for the latest period in the snapshot and say which period it is.
- **"Latest" / "most recent":** latest in the pinned snapshot (`data_db_2026-11-03`), with the period named.
- **Fiscal vs calendar:** use the company's fiscal labels from the filing text, not the cover-page metadata. NetApp's metadata
  is one year behind its own fiscal year on 3 of its 10-Qs (`data/snapshot_w7.json`).
- **Net income:** attributable to the company, unless the question says otherwise.

## How Eval scores it (`kpmg_eval/metrics/decision.py`)

| Measure | Definition | Target to propose to KPMG |
|---|---|---|
| Decision accuracy | share of questions with the expected decision | report, no target yet |
| **Unsafe answer rate** | answered when the expected decision was clarify, abstain or off_topic | as low as possible; headline |
| Over-refusal rate | did not answer when an answer was expected | report beside unsafe answers |
| **Off-topic tool calls** | tool calls made on off_topic questions | **0** (KPMG's gate) |
| Gate violations | tool calls on questions the scope check alone should settle | 0 |

The AnswerBlock gets one optional field, `decision` (answer / clarify / abstain / off_topic). Without it Eval reads
`answered: true` as answer and `answered: false` as abstain, so existing systems still score.

## Test set

- Gold Set v2 (155): expected decisions follow from each question (answerable -> answer; refusal answers -> abstain;
  false premise -> answer by correcting).
- `data/decision_suite_v1.jsonl` (24 new items): 8 clarify, 8 off_topic, 8 abstain cases specific to the ten companies.
