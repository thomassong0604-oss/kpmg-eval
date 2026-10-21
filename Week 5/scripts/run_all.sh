#!/usr/bin/env bash
# Week 5, one command: pin upstream repos, rebuild Gold Set v1, validate it, test, score RAG's real retriever,
# run the end-to-end baseline, fault injection and graph checks. About 15 s after the first clone.
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
# slides: python3 scripts/build_deck_w5.py <10/15 deck with one eval slide duplicated> <out.pptx>
