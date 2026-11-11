#!/usr/bin/env bash
# Pin the other teams' repos at the commits this week was built against (all public).
set -euo pipefail
cd "$(dirname "$0")/../upstream"
clone () { [ -d "$2" ] || git clone -q "https://github.com/$1" "$2"; git -C "$2" fetch -q origin "$3" 2>/dev/null || true; git -C "$2" checkout -q "$3"; echo "$2 @ $(git -C "$2" rev-parse --short HEAD)"; }
clone Rachel-xs/KPMG_RAG KPMG_RAG 5bfafeb                    # RAG main 11/5: chunker, BM25, retriever, contract v1, round-1 corpus scripts
clone michaelliruoxi/data_engineering_kpmg data_engineering_kpmg f8d18e2   # Data: MSFT 10-Q source + XBRL instance
clone ZiyiClaudiaWang/KPMG-GraphRAG KPMG-GraphRAG 4e89acb       # GraphRAG main 11/11: graphrag.backends (real arms), filters per contract
clone ZiyiClaudiaWang/KPMG-GraphRAG KPMG-GraphRAG-ex21 c21fe89  # GraphRAG alina/ex21-pipeline 11/8: Exhibit 21 edges for the ten
# GraphRAG's structured store for the MSFT 10-Q, built with GraphRAG's own loader from Data's copy (offline)
if [ ! -f graphrag_store_msft_10q.duckdb ]; then
  (cd KPMG-GraphRAG/structured && python3 fact_loader_v1.py \
     --html ../../data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331.htm \
     --cik 0000789019 --ticker MSFT --accession 0001193125-26-191507 --filing-date 2026-04-29 --form 10-Q \
     --company-name "Microsoft Corporation" --output ../../graphrag_store_msft_10q.duckdb | tail -1)
fi
