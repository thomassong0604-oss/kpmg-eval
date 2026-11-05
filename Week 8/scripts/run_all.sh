#!/usr/bin/env bash
# Week 8, one command (Week 7 + RAG vs GraphRAG side by side, messy-wording suite, routing examples) (Week 7: Gold Set v2, decision and routing baselines) (Week 5 pipeline + relationship draft tranche, provenance-key joins): pin upstream repos, rebuild Gold Set v1, validate it, test, score RAG's real retriever,
# run the end-to-end baseline, fault injection, graph checks,
# filter accuracy, abstention gate, grading pipeline (scorecards) and metric selection; export the Word question list. About 15 s after the first clone.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/fetch_upstream.sh
python3 scripts/extract_xbrl_facts.py upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331_htm.xml data/msft_xbrl_facts.jsonl
python3 scripts/build_rag_chunks.py upstream/KPMG_RAG upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331.htm data/rag_chunks_msft_10q.jsonl
python3 scripts/build_benchmark_v1.py
python3 scripts/validate_benchmark_v1.py
python3 scripts/build_scope10.py
python3 scripts/run_scope10_grader_check.py
python3 scripts/build_relationship_draft.py
python3 scripts/build_gold_v2.py
python3 scripts/run_decision_baselines.py
python3 scripts/run_routing_baselines.py
python3 scripts/routing_examples.py
python3 scripts/review_rag_gold_v1_anchors.py
python3 scripts/review_rag_gold_v1_anchors.py --fixes
python3 -m pytest -q
python3 scripts/run_rag_retrieval_v1.py
python3 scripts/run_e2e_baseline.py
python3 scripts/run_fault_injection_v1.py
python3 scripts/run_graph_checks_v1.py
python3 scripts/run_filter_accuracy.py
python3 scripts/run_abstention_v1.py
python3 scripts/run_harness.py
python3 scripts/run_harness.py --benchmark scope10
python3 scripts/run_harness.py --benchmark v2
python3 scripts/run_graphrag_wiring.py
python3 scripts/run_metric_selection.py
python3 scripts/run_side_by_side.py
python3 scripts/run_messy_wording.py
node scripts/export_questions_docx.js
python3 scripts/refresh_peer_facts.py --check
