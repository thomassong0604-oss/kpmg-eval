#!/usr/bin/env bash
# Week 5, one command: pin upstream repos, rebuild Gold Set v1, validate it, test, score RAG's real retriever,
# run the end-to-end baseline, fault injection, graph checks,
# filter accuracy, abstention gate, grading pipeline (scorecards) and metric selection; export the Word question list. About 15 s after the first clone.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/fetch_upstream.sh
python3 scripts/extract_xbrl_facts.py upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331_htm.xml data/msft_xbrl_facts.jsonl
python3 scripts/build_rag_chunks.py upstream/KPMG_RAG upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331.htm data/rag_chunks_msft_10q.jsonl
python3 scripts/build_benchmark_v1.py
python3 scripts/validate_benchmark_v1.py
python3 -m pytest -q
python3 scripts/run_rag_retrieval_v1.py
python3 scripts/run_e2e_baseline.py
python3 scripts/run_fault_injection_v1.py
python3 scripts/run_graph_checks_v1.py
python3 scripts/run_filter_accuracy.py
python3 scripts/run_abstention_v1.py
python3 scripts/run_harness.py
python3 scripts/run_metric_selection.py
node scripts/export_questions_docx.js
python3 scripts/refresh_peer_facts.py --check
# slides: python3 scripts/build_deck_w5.py <10/15 deck with one eval slide duplicated> <out.pptx>
