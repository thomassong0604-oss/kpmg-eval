#!/usr/bin/env bash
# Pin the other teams' repos at the commits Week 5 was built against (all public).
set -euo pipefail
cd "$(dirname "$0")/../upstream"
clone () { [ -d "$2" ] || git clone -q "https://github.com/$1" "$2"; git -C "$2" fetch -q origin "$3" 2>/dev/null || true; git -C "$2" checkout -q "$3"; echo "$2 @ $(git -C "$2" rev-parse --short HEAD)"; }
clone Rachel-xs/KPMG_RAG KPMG_RAG 1996e72                    # RAG: retrieve() v0, chunker, BM25, Gold Set v0 (MSFT)
clone michaelliruoxi/data_engineering_kpmg data_engineering_kpmg 1f32768   # Data: MSFT 10-Q source + XBRL instance
