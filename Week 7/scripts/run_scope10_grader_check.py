"""Week 6: does the numeric grader score the new 10-company questions correctly?

    python scripts/run_scope10_grader_check.py   -> results/scope10_grader_check.json

For each exact-numeric EV2 question, four answers: the gold display text and a plain restatement (both must pass),
a scale error (x1000) and a sign error (both must fail). Catches sig-fig and negative-number issues before round 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.metrics.numeric import score_numeric  # noqa: E402


def main():
    qs = [q for q in map(json.loads, open(ROOT / "data" / "benchmark_scope10_new.jsonl")) if q["answer_type"] == "exact_numeric"]
    bad, n = [], 0
    for q in qs:
        v, money = q["answer"]["value"], q["answer"]["kind"] == "money"
        cases = [("gold_display", q["answer"]["display"], True),
                 ("plain", f"{v / 1e6:,.1f} million" if money else f"{v}%", True),
                 ("scale_x1000", f"USD {v / 1e3:,.0f} million" if money else f"{v * 10}%", False),
                 ("sign_flip", f"USD {-v / 1e6:,.1f} million" if money else f"{-v}%", False)]
        for label, txt, expect in cases:
            n += 1
            r = score_numeric(q, {"answered": True, "value_text": txt, "answer_text": txt})
            if r.passed != expect:
                bad.append([q["qid"], label, txt, r.passed, r.label])
    out = {"numeric_items": len(qs), "graded": n, "mismatches": bad}
    (ROOT / "results" / "scope10_grader_check.json").write_text(json.dumps(out, indent=1))
    print(f"[grader] {len(qs)} numeric EV2 questions, {n} graded answers, {len(bad)} mismatches")


if __name__ == "__main__":
    main()
