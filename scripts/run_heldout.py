"""Held-out check: 31 hand-written answers, labelled by a person BEFORE running the grader, never used to tune it.
Fault injection (run_fault_injection.py) tests the error types; this tests realistic wording the grader never saw.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.metrics.numeric import score_numeric  # noqa: E402
from kpmg_eval.metrics.refusal import classify_response  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402

bench = {json.loads(l)["qid"]: json.loads(l) for l in open(ROOT / "data" / "benchmark_v0.jsonl")}
rows = []
for l in open(ROOT / "data" / "heldout_answers_v0.jsonl"):
    h = json.loads(l)
    item = bench[h["qid"]]
    pred = score_numeric(item, h["text"]).label if item["answerable"] else classify_response(h["text"])
    rows.append({**h, "grader": pred, "agree": pred == h["human"]})

k, n = sum(r["agree"] for r in rows), len(rows)
lo, hi = wilson(k, n)
out = {"agree": k, "n": n, "agreement": k / n, "ci95": [lo, hi], "rows": rows}
(ROOT / "results" / "heldout.json").write_text(json.dumps(out, indent=2))
print(f"held-out agreement with human labels: {k}/{n} = {k/n:.0%} (95% CI {lo:.0%}-{hi:.0%})")
for r in rows:
    if not r["agree"]:
        print(f"  DISAGREE {r['hid']} human={r['human']:13s} grader={r['grader']:13s} | {r['text']}")
