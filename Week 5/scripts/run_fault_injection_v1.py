"""Does the numeric grader still label errors correctly on Gold Set v1? (Week-4 method, new question set.)

    python scripts/run_fault_injection_v1.py   -> results/fault_injection_v1.json

For every numeric question, structured AnswerBlocks are generated with a known error, and the grader
(score_numeric_diagnosed = Week-4 NAA grader + Week-5 fact-index diagnosis) must return that label:
  correct           the gold value
  wrong_scale       x1,000 (thousands/millions confusion)
  wrong_sign        negated
  wrong_period      same concept and member, another period in the filing          (from the XBRL facts)
  wrong_dimension   same concept and period, another segment/member or the total   (from the XBRL facts)
  wrong_concept     benchmark distractors labelled wrong_concept / wrong_dimension
Single-fact questions on the Microsoft 10-Q get the period and dimension faults; every numeric question gets the rest.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402
from kpmg_eval.metrics.numeric import score_numeric_diagnosed  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402


def block(v, unit):
    return {"answered": True, "value": v, "unit": unit if unit in ("USD", "%", "pp") else None}


def main():
    bench = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v1.jsonl")]
    facts = [json.loads(l) for l in open(ROOT / "data" / "msft_xbrl_facts.jsonl")]
    index = FactIndex(facts)
    cases = []
    for q in bench:
        if not q["gold"]:
            continue
        g, unit = q["gold"]["value"], q["answer"]["unit"]
        cases.append((q, block(g, unit), "correct"))
        if g != 0:   # x1000 and negation of zero are still zero
            cases.append((q, block(g * 1000, unit), "wrong_scale"))
            cases.append((q, block(-g, unit), "wrong_sign"))
        for d in q["gold"]["distractors"]:
            if d["label"] in ("wrong_concept", "wrong_dimension"):
                cases.append((q, block(d["value"], unit), d["label"]))
        if q["corpus"] == "msft_10q_q3fy26" and len(q["facts"]) == 1 and q["type"] in ("extraction", "segment"):
            k = q["facts"][0]
            vals_seen = {g}
            for f in facts:
                if f["concept"] != k["concept"] or not f["unit"]:
                    continue
                try:
                    v = float(f["value"])
                except ValueError:
                    continue
                if v in vals_seen or v == 0 or index.lookup(v) != [f] and len({json.dumps([h["concept"], h["start"], h["end"], h["dims"]]) for h in index.lookup(v)}) > 1:
                    continue  # skip values that are ambiguous in the filing (same number, several facts)
                same_dims = (f["dims"] or {}) == (k.get("dims") or {})
                same_per = (f["start"] or None) == k["period_start"] and f["end"] == k["period_end"]
                if same_dims and not same_per:
                    cases.append((q, block(v, unit), "wrong_period")); vals_seen.add(v)
                elif same_per and not same_dims and len(f["dims"]) <= 1:
                    cases.append((q, block(v, unit), "wrong_dimension")); vals_seen.add(v)
    conf = defaultdict(Counter)
    ok = 0
    for q, b, want in cases:
        got = score_numeric_diagnosed(q, b, index).label
        conf[want][got] += 1
        ok += got == want
    lo, hi = wilson(ok, len(cases))
    out = {"n_cases": len(cases), "n_questions": len({q["qid"] for q, _, _ in cases}), "label_accuracy": ok / len(cases),
           "ci95": [round(lo, 4), round(hi, 4)], "by_injected_label": {k: dict(v) for k, v in conf.items()},
           "per_label_accuracy": {k: round(v[k] / sum(v.values()), 4) for k, v in conf.items()}}
    (ROOT / "results" / "fault_injection_v1.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
