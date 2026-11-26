# kpmg-eval — Evaluation & Testing workstream (KPMG × Columbia QMSS)

Weekly work for the evaluation and testing workstream.

| Folder | Contents |
|---|---|
| [`Week 4/`](Week%204/) | Metric library, benchmark v0, test harness, results and charts ([README](Week%204/README.md)) |
| [`Week 5/`](Week%205/) | Gold Set v1 (100 questions shared with RAG/GraphRAG), RAG's real retriever scored on the real 10-Q, end-to-end floor, 5 new metrics ([README](Week%205/README.md)) |
| [`Week 6/`](Week%206/) | Data's 10 companies (139-question round-1 set, facts read twice from SEC), GraphRAG wiring + XBRL-dimension fix, RAG anchor review, provenance/version keys, relationship draft ([README](Week%206/README.md)) |
| [`Week 7/`](Week%207/) | Gold Set v2 on Data's ten companies only (155 questions, pinned to the 11/03 DB snapshot), filing-list match, Exhibit 21 relationship questions, answer/clarify/abstain/block rules and routing evaluation for Agents, RAG anchor fixes, fixed-reader adapter ([README](Week%207/README.md)) |
| [`Week 8/`](Week%208/) | RAG vs GraphRAG side by side on the same filing with each team's own code, where each does better (incl. Exhibit 21 traversal), routing chart and unneeded-call definition, demo routing examples, typo and messy-wording suite, RAG's end-to-end round 1 graded, Gold Set v2.2, narrative judge; after 11/12: GraphRAG re-scored after its ranking changes ([README](Week%208/README.md)) |
| [`Week 9/`](Week%209/) | RAG's two narrative runs (final_v1 and a retrieval variant) scored with the judge on the same 38 questions; holdout batch A for RAG's frozen `final_v1`, sealed, with its SHA-256 published ([README](Week%209/README.md)) |
| [`Week 10/`](Week%2010/) | Both sealed-holdout scores: RAG's frozen `final_v1` on batch A (numeric 28/30) and `final_v2` on batch B (narrative 17/18), with citations, cost and latency; RAG's six filter-extraction arms on the messy-wording suite, paired with the clean questions; both narrative judges checked against RAG's 126 hand labels; XBRL objective sets A and C built with a private seed, checked and sealed (Set C drawn again on 11/26); Set B scored on the 645-filing index (0.873 with gold filters, 0.767 with the pre-check) ([README](Week%2010/README.md)) |

**Current gold set:** Gold Set v2.2 (155 questions, ten companies, 21 filings; v2's questions and answers with corrected anchors (v2.1, 11/9) and the grading fixes from RAG's end-to-end round 1 (v2.2, 11/11)), see [`Week 8/GOLD_SET_V2.md`](Week%208/GOLD_SET_V2.md). Gold Set v1 (100 questions) stays frozen in every week folder.

**Slides:** each week's Eval slides (pptx and PDF) are in `Week N/deck/` (Weeks 6–8). **Check-ins** for the course are in [`Check-ins/`](Check-ins/). The team's **Benchmark & Experimental Protocol** report is in [`Assignments/`](Assignments/). **Messages** sent to other teams start in `Week 8/COMMS_W8.md`.

## What this work demonstrates

I own the Evaluation & Testing workstream: deciding how we know whether a SEC-filings Q&A system is
actually right, building the measurement, and giving KPMG numbers they can act on. Everything under
`kpmg_eval/`, `scripts/`, `tests/` and `data/` is my work. Code under `vendor/` and snapshots under
`upstream/` belong to the Retrieval and GraphRAG teams, kept unchanged and attributed so results reproduce.

| Skill | Where to look |
|---|---|
| **Measurement design** — turning "is this answer good?" into metrics that hold up: numeric accuracy, evidence recall, citation support, abstention, premise checking, routing, graph traversal, robustness to messy wording | [`Week 8/kpmg_eval/metrics/`](Week%208/kpmg_eval/metrics/) — 15 metric modules |
| **Statistical honesty** — Wilson intervals on every rate, bootstrap confidence intervals, and a paired bootstrap when two systems answer the same questions, so a 5-point gap on 40 questions is never reported as a win | [`Week 8/kpmg_eval/stats.py`](Week%208/kpmg_eval/stats.py) |
| **Benchmark construction** — a 155-question gold set (143 answerable) over 21 real filings from ten companies, built from XBRL facts read twice from SEC, versioned v0 → v1 → v2.2 with the reason for every change recorded | [`Week 8/GOLD_SET_V2.md`](Week%208/GOLD_SET_V2.md), [`scripts/build_gold_v2.py`](Week%208/scripts/build_gold_v2.py) |
| **Experiment design** — oracle, refuse-all and no-LLM reference systems to bound what a score means; fault injection; held-out sets; metric-selection runs | [`Week 8/results/scorecard.md`](Week%208/results/scorecard.md), [`scripts/run_fault_injection_v1.py`](Week%208/scripts/run_fault_injection_v1.py) |
| **Data engineering** — SEC EDGAR and XBRL extraction, filing parsing, JSONL pipelines, DuckDB, pinned data snapshots and content-hash version keys stamped on every result | [`scripts/extract_xbrl_facts.py`](Week%208/scripts/extract_xbrl_facts.py), [`kpmg_eval/keys.py`](Week%208/kpmg_eval/keys.py) |
| **Reproducibility and testing** — one command rebuilds every number in a week from the data in its folder; 87 unit tests across five suites; pinned requirements | [`Week 8/scripts/run_all.sh`](Week%208/scripts/run_all.sh), [`Week 8/tests/`](Week%208/tests/) |
| **Working across teams** — written interfaces and decision policies that the Retrieval, GraphRAG and Agents teams build against, so evaluation is agreed up front rather than argued after | [`Week 8/POLICY_answer_clarify_abstain.md`](Week%208/POLICY_answer_clarify_abstain.md), [`Week 8/FOR_TEAMS_W8.md`](Week%208/FOR_TEAMS_W8.md) |
| **Communicating to a client** — weekly slides and check-in notes generated from the results files rather than retyped, so the deck can never drift from the numbers | [`Week 8/scripts/build_deck_w8.py`](Week%208/scripts/build_deck_w8.py), [`Week 8/deck/`](Week%208/deck/), [`Check-ins/`](Check-ins/) |

**Stack:** Python (pandas, numpy, matplotlib, DuckDB, BeautifulSoup/lxml, pytest, python-pptx), JSONL
data pipelines, SEC EDGAR/XBRL, Git. **Domain:** LLM and RAG evaluation, financial filings.

The judgement call this workstream keeps coming back to: a benchmark is only worth the care taken over
its gold answers, and a number is only worth the interval around it. Most of the work here is making
both of those defensible to a client who will act on them.

Each week's folder is self-contained: `cd` into it and follow its README.
