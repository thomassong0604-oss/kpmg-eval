# kpmg-eval — Evaluation & Testing workstream (KPMG × Columbia QMSS)

Weekly work for the evaluation and testing workstream.

| Folder | Contents |
|---|---|
| [`Week 4/`](Week%204/) | Metric library, benchmark v0, test harness, results and charts ([README](Week%204/README.md)) |
| [`Week 5/`](Week%205/) | Gold Set v1 (100 questions shared with RAG/GraphRAG), RAG's real retriever scored on the real 10-Q, end-to-end floor, 5 new metrics ([README](Week%205/README.md)) |
| [`Week 6/`](Week%206/) | Data's 10 companies (139-question round-1 set, facts read twice from SEC), GraphRAG wiring + XBRL-dimension fix, RAG anchor review, provenance/version keys, relationship draft ([README](Week%206/README.md)) |
| [`Week 7/`](Week%207/) | Gold Set v2 on Data's ten companies only (155 questions, pinned to the 11/03 DB snapshot), filing-list match, Exhibit 21 relationship questions, answer/clarify/abstain/block rules and routing evaluation for Agents, RAG anchor fixes, fixed-reader adapter ([README](Week%207/README.md)) |
| [`Week 8/`](Week%208/) | RAG vs GraphRAG side by side on the same filing with each team's own code, where each does better (incl. Exhibit 21 traversal), routing chart and unneeded-call definition, demo routing examples, typo and messy-wording suite, RAG's end-to-end round 1 graded, Gold Set v2.2, narrative judge ([README](Week%208/README.md)) |

**Current gold set:** Gold Set v2.2 (155 questions, ten companies, 21 filings; v2's questions and answers with corrected anchors (v2.1, 11/9) and the grading fixes from RAG's end-to-end round 1 (v2.2, 11/11)), see [`Week 8/GOLD_SET_V2.md`](Week%208/GOLD_SET_V2.md). Gold Set v1 (100 questions) stays frozen in every week folder.

**Slides:** each week's Eval slides (pptx and PDF) are in `Week N/deck/` (Weeks 6–8). **Check-ins** for the course are in [`Check-ins/`](Check-ins/). **Messages** sent to other teams start in `Week 8/COMMS_W8.md`.

Each week's folder is self-contained: `cd` into it and follow its README.
