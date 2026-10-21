#!/usr/bin/env bash
# One command: rebuild benchmark, run tests and every evaluation, redraw charts.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/build_benchmark.py
python3 -m pytest -q
python3 scripts/run_fault_injection.py
python3 scripts/run_heldout.py
python3 scripts/run_retrieval_eval.py
python3 scripts/run_graph_checks.py
PYTHONPATH=. python3 scripts/make_charts.py
