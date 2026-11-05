# Week 7 for the other teams (11/05)

Thank you all: Data's 233-filing inventory and GraphRAG's filing config let us match every list against one source this week.

## Data
- **Snapshot:** we propose freezing the 21 filings in your database on 11/03 for round 1 (`data/snapshot_w7.json`). RAG asked the same.
- **Match:** all 21 are in your 2021-2026 inventory. Our Week 6 list differed only in Micron's 10-K (you have FY2026; we had FY2025). Fixed.
- **Asks:** confirm the snapshot; share text chunks for the 21 filings (for the remaining anchors); your cleaned Exhibit 21, to compare with our reads (`data/sec_reads/exhibit21_2026-11-05.json`).
- **FYI:** NetApp's cover-page metadata is one fiscal year behind its own text on 3 10-Qs (0001193125-25-189700, 0001193125-25-297237, 0001193125-26-380207).

## RAG
- **Your anchor review:** `results/rag_anchor_fixes.csv`, one row per change (10 drop, 2 remove, 25 narrow; 17 with a ready replacement).
- **Your 8 Amazon/Meta questions:** drop them; they are outside the ten companies.
- **Your two asks:** accuracy by route is in every scorecard; the fixed reader is `--system fixed_reader` (needs an API key).
- **Ask:** index the other 8 companies (your v2 index covers Apple and Microsoft).

## GraphRAG
- 11 questions routed to GraphRAG (4 drafted with you + 7 from Exhibit 21), incl. 4 invented-relationship checks.
- Hops sheet: `data/hops_v1.csv` (165 rows; values you already filled are kept on rebuild).
- Ask: review the relationship questions; a date for the graph backend.

## Agents
- Draft decision rules: `POLICY_answer_clarify_abstain.md` (answer / clarify / abstain / block off-topic, with zero tool calls on off-topic as KPMG asked).
- Routing: expected route on every question; `scripts/run_routing_baselines.py` scores any router. Please review the labels and run your orchestrator through it.
- Ask: add an optional `decision` field to the AnswerBlock.
