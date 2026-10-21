"""GraphRAG metric validation on the gold graph fixture (data/gold_graph_v0.json).

GraphRAG has no graph output yet, so this injects the three faults most likely in SEC fact extraction
and confirms each metric moves the way it should. These are NOT GraphRAG results.
  A. missed facts      : 10-Q year-to-date facts dropped (extractor only reads the quarter column)
  B. period mislabel   : quarter values stored under the year-to-date period
  C. scale error       : 10-Q values stored in thousands instead of dollars
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.metrics.graph import path_recall, score_edges, score_fact_extraction  # noqa: E402

g = json.loads((ROOT / "data" / "gold_graph_v0.json").read_text())
facts = [n for n in g["nodes"] if n["label"] == "Fact"]
edges = [tuple(e) for e in g["edges"]]
bench = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v0.jsonl")]


def days(f):
    from datetime import date
    s, e = (date.fromisoformat(x) for x in (f["period_start"], f["period_end"]))
    return (e - s).days


ytd = [f for f in facts if 150 < days(f) < 300]                    # six- and nine-month facts
quarters = {(f["cik"], f["period_end"]): f for f in facts if days(f) < 100}

scenarios = {}
# A. drop year-to-date facts
pred_a = [f for f in facts if f not in ytd]
scenarios["A_missed_ytd_facts"] = score_fact_extraction(pred_a, facts)
# B. quarter value written under the YTD key
pred_b = []
for f in facts:
    if f in ytd and (f["cik"], f["period_end"]) in quarters:
        pred_b.append({**f, "value": quarters[(f["cik"], f["period_end"])]["value"]})
    else:
        pred_b.append(f)
scenarios["B_period_mislabel"] = score_fact_extraction(pred_b, facts)
# C. 10-Q values in thousands
tenq = {n["id"] for n in g["nodes"] if n["label"] == "Filing" and n["form"] == "10-Q"}
pred_c = [{**f, "value": f["value"] / 1000} if f["accession"] in tenq else f for f in facts]
scenarios["C_scale_error_10Q"] = score_fact_extraction(pred_c, facts)
scenarios["perfect"] = score_fact_extraction(facts, facts)

# Edge check: missing FILED edges for one company
drop_cik = "0000831001"
scenarios["edges_missing_citi"] = score_edges([e for e in edges if e[0] != drop_cik], edges)

# How many benchmark questions need multi-hop retrieval, and does the gold graph contain every hop?
multi = [b for b in bench if b["answerable"] and len(b["graph_paths"]) > 1]
fixture_edges = {tuple(e) for e in edges}
coverage = [path_recall(fixture_edges, [tuple(h) for p in b["graph_paths"] for h in p]) for b in bench if b["graph_paths"]]

out = {"note": "Fault-injection validation of graph metrics on the gold fixture. Not GraphRAG output.",
       "n_fact_nodes": len(facts), "n_edges": len(edges), "n_ytd_facts": len(ytd),
       "scenarios": {k: {kk: vv for kk, vv in v.items() if kk not in ("wrong_value_keys", "by_relation")} for k, v in scenarios.items()},
       "benchmark_multi_fact_questions": len(multi), "gold_path_coverage_in_fixture": sum(coverage) / len(coverage)}
(ROOT / "results" / "graph_checks.json").write_text(json.dumps(out, indent=2))
for k, v in out["scenarios"].items():
    print(f"{k:22s} P={v['precision']:.2f} R={v['recall']:.2f} F1={v['f1']:.2f}" + (f" value_acc={v['value_accuracy']:.2f}" if v.get("value_accuracy") is not None else ""))
print("multi-fact benchmark questions:", len(multi), "| gold path coverage in fixture:", out["gold_path_coverage_in_fixture"])
