"""Week 8, after the 11/12 meeting: GraphRAG's structured search before and after its ranking changes.

    python scripts/compare_graphrag_rescore.py   -> results/graphrag_rescore_a1e7cf7.json

Same store (GraphRAG's 20 filings), same questions (Gold Set v2.2), same script (run_graphrag_round1.py), translated
filters, top 10. Before: main 21f0795 (11/11, #70), the commit round 1 was presented on. After: main a1e7cf7 (11/13),
which adds #72 (equal scores are ordered by the period the question named, then consolidated over slice, then newest)
and #76 (sign of the value as a tie-break). GraphRAG's PR #72 reports rank-1 right 28.0% -> 64.5% and wrong period at
rank 1 11.9% -> 4.8% with the top 10 unchanged at 67.7%; this file is Eval's reproduction, question by question.
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
BEFORE, AFTER = "eval_store20", "eval_store20_a1e7cf7"
METRICS = ("numbers", "top1_right", "top1_wrong_period", "prose", "returned_nothing_on_unanswerable")


def rows(tag):
    return {r["qid"]: r for r in csv.DictReader(open(RES / f"graphrag_round1_{tag}.csv"))
            if r["arm"] == "structured" and r["filters_mode"] == "translated"}


def main():
    if not (RES / f"graphrag_round1_{AFTER}.json").exists():
        print("[rescore] no re-score yet (needs upstream/KPMG-GraphRAG-1113 and the private store)")
        return
    ja, jb = (json.load(open(RES / f"graphrag_round1_{t}.json")) for t in (BEFORE, AFTER))
    a, b = rows(BEFORE), rows(AFTER)
    frac = lambda m: f"{m['hits']}/{m['n']}"  # noqa: E731
    out = {"_doc": __doc__.strip().split("\n")[0], "gold": jb["gold"], "store": jb["store"], "k": jb["k"],
           "before_commit": ja["graphrag_commit"], "after_commit": jb["graphrag_commit"], "filters": "translated",
           "summary": {m: {"before": frac(ja["summary"]["structured|translated"][m]),
                           "after": frac(jb["summary"]["structured|translated"][m])} for m in METRICS}}
    num = [q for q in a if a[q]["kind"] == "number" and b[q]["filing_in_store"] != "False"]  # scored: filing in store
    out["rank1_gained"] = sorted(q for q in num if a[q]["top1_right"] != "True" and b[q]["top1_right"] == "True")
    out["rank1_lost"] = sorted(q for q in num if a[q]["top1_right"] == "True" and b[q]["top1_right"] != "True")
    out["top10_changed"] = sorted(q for q in num if a[q]["needed_in_evidence"] != b[q]["needed_in_evidence"])
    out["known_wrong_figure_at_rank1_after"] = sorted(q for q in num if b[q]["top1_wrong_period"] == "True")
    out["in_top10_not_rank1_after"] = sorted(q for q in num if b[q]["needed_in_evidence"] == "True" and b[q]["top1_right"] != "True")
    out["not_in_top10_after"] = sorted(q for q in num if b[q]["needed_in_evidence"] != "True")
    by = {}
    for q in num:
        d = by.setdefault(b[q]["type"], {"n": 0, "rank1_before": 0, "rank1_after": 0})
        d["n"] += 1
        d["rank1_before"] += a[q]["top1_right"] == "True"
        d["rank1_after"] += b[q]["top1_right"] == "True"
    out["rank1_right_by_type"] = dict(sorted(by.items()))
    ms = sorted(float(r["ms"]) for r in b.values() if r["ms"])
    out["latency_ms_per_call_after"] = {"n": len(ms), "median": round(statistics.median(ms), 1),
                                        "p95": round(ms[int(0.95 * len(ms)) - 1], 1),
                                        "note": "structured search on a local DuckDB store in Eval's workspace; no model call"}
    (RES / "graphrag_rescore_a1e7cf7.json").write_text(json.dumps(out, indent=1))
    s = out["summary"]
    print(f"[rescore] {out['before_commit']} -> {out['after_commit']}: rank 1 right {s['top1_right']['before']} -> "
          f"{s['top1_right']['after']}, known wrong figure at rank 1 {s['top1_wrong_period']['before']} -> "
          f"{s['top1_wrong_period']['after']}, numbers in top 10 {s['numbers']['before']} -> {s['numbers']['after']}; "
          f"lost {len(out['rank1_lost'])}")


if __name__ == "__main__":
    main()
