"""Gold graph v1 for GraphRAG + fault-injection check of the graph metrics.

    python scripts/run_graph_checks_v1.py    -> data/gold_graph_v1.json, results/graph_checks_v1.json

The gold graph contains every node and edge a correct graph needs to answer the 100 questions, in GraphRAG's
10/8 schema (Company -FILED-> Filing -REPORTS-> Fact; dimensional facts -FOR_MEMBER-> Segment / Product / Geography).
New in v1: segment, product and geography members (Week 4 had none), the FY2026 10-K, and 4 peer companies.

GraphRAG has no graph output yet, so the faults below are injected into the gold graph to confirm each metric
reacts. These are NOT GraphRAG results.
  A  missed nine-month facts        (extractor reads only the quarter column)
  B  period mislabel                (quarter value stored under the nine-month key)
  C  scale error                    (10-Q values stored in millions instead of dollars)
  D  dimension dropped (new)        (segment facts stored without their member -> collide with consolidated totals)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_benchmark_v1 import fact_node_id  # noqa: E402

from kpmg_eval.metrics.graph import path_recall, score_edges, score_fact_extraction  # noqa: E402

AXIS_LABEL = {"us-gaap:StatementBusinessSegmentsAxis": "Segment", "srt:ProductOrServiceAxis": "ProductOrService",
              "srt:StatementGeographicalAxis": "Geography"}


def main():
    bench = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v1.jsonl")]
    peers = {r["cik"]: r for r in map(json.loads, open(ROOT / "data" / "peer_facts_v1.jsonl"))}
    values = {}
    for q in bench:
        for k, v in zip(q["facts"], q["fact_values"].values()):
            values[fact_node_id(k)] = (k, v)
    nodes, edges = {}, set()
    names = {"0000789019": ("MSFT", "Microsoft Corporation"), **{c: (r["ticker"], r["company"]) for c, r in peers.items()}}
    for nid, (k, v) in values.items():
        t, name = names[k["cik"]]
        nodes[k["cik"]] = {"id": k["cik"], "label": "Company", "ticker": t, "name": name}
        nodes[k["accession"]] = {"id": k["accession"], "label": "Filing", "cik": k["cik"]}
        f = {"id": nid, "label": "Fact", "cik": k["cik"], "accession": k["accession"], "concept": k["concept"],
             "period_start": k["period_start"], "period_end": k["period_end"], "unit": k["unit"], "value": v}
        if k.get("dims"):
            f["dims"] = k["dims"]
            axis, mem = list(k["dims"].items())[0]
            nodes[mem] = {"id": mem, "label": AXIS_LABEL.get(axis, "Member"), "axis": axis, "cik": k["cik"]}
            edges.add((nid, "FOR_MEMBER", mem))
            if AXIS_LABEL.get(axis) == "Segment":
                edges.add((k["cik"], "HAS_SEGMENT", mem))
        nodes[nid] = f
        edges.add((k["cik"], "FILED", k["accession"]))
        edges.add((k["accession"], "REPORTS", nid))
    g = {"schema": "GraphRAG 10/8: Company, Filing, Section, Fact, Segment (+ ProductOrService, Geography members)",
         "nodes": list(nodes.values()), "edges": sorted(list(e) for e in edges)}
    (ROOT / "data" / "gold_graph_v1.json").write_text(json.dumps(g, indent=1))

    facts = [n for n in g["nodes"] if n["label"] == "Fact"]
    gold_edges = [tuple(e) for e in g["edges"]]

    def days(f):
        if not f["period_start"]:
            return 0
        return (date.fromisoformat(f["period_end"]) - date.fromisoformat(f["period_start"])).days

    ytd = [f for f in facts if 200 < days(f) < 300]
    qtr = {(f["cik"], f["concept"], json.dumps(f.get("dims"), sort_keys=True), f["period_end"]): f for f in facts if 0 < days(f) < 100}
    sc = {"perfect": score_fact_extraction(facts, facts)}
    sc["A_missed_ytd_facts"] = score_fact_extraction([f for f in facts if f not in ytd], facts)
    pred_b = [{**f, "value": qtr[(f["cik"], f["concept"], json.dumps(f.get("dims"), sort_keys=True), f["period_end"])]["value"]}
              if f in ytd and (f["cik"], f["concept"], json.dumps(f.get("dims"), sort_keys=True), f["period_end"]) in qtr else f for f in facts]
    sc["B_period_mislabel"] = score_fact_extraction(pred_b, facts)
    tenq = {n["id"] for n in g["nodes"] if n["label"] == "Filing" and n["id"] != "0001193125-26-323660"}
    sc["C_scale_error_10Q"] = score_fact_extraction([{**f, "value": f["value"] / 1e6} if f["accession"] in tenq and f["unit"] == "USD" else f for f in facts], facts)
    sc["D_dimension_dropped"] = score_fact_extraction([{k: v for k, v in f.items() if k != "dims"} for f in facts], facts)
    sc["edges_missing_FOR_MEMBER"] = score_edges([e for e in gold_edges if e[1] != "FOR_MEMBER"], gold_edges)

    multi = [q for q in bench if q["graph"] and q["graph"]["n_facts"] > 1]
    cov = [path_recall(set(gold_edges), [tuple(h) for p in q["graph"]["paths"] for h in p]) for q in bench if q["graph"]]
    patterns = Counter(q["graph"]["pattern"] for q in bench if q["graph"])
    hops = Counter(min(q["graph"]["n_facts"], 6) for q in bench if q["graph"])
    out = {"note": "Fault injection on the gold graph; not GraphRAG output.",
           "n_nodes": len(g["nodes"]), "n_fact_nodes": len(facts), "n_edges": len(gold_edges),
           "node_labels": dict(Counter(n["label"] for n in g["nodes"])),
           "questions_with_graph_paths": sum(1 for q in bench if q["graph"]), "multi_fact_questions": len(multi),
           "patterns": dict(patterns), "facts_per_question": {str(k) if k < 6 else "6+": v for k, v in sorted(hops.items())},
           "gold_path_coverage": sum(cov) / len(cov),
           "text_only_questions": sum(1 for q in bench if not q["graph"] and q["answerable"]),
           "scenarios": {k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()
                             if kk not in ("wrong_value_keys", "by_relation")} for k, v in sc.items()}}
    (ROOT / "results" / "graph_checks_v1.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "scenarios"}, indent=1))
    for k, v in out["scenarios"].items():
        print(f"  {k:26s} P={v['precision']:.2f} R={v['recall']:.2f} F1={v['f1']:.2f} value_acc={v.get('value_accuracy')} collisions={v.get('n_pred_collisions')}")


if __name__ == "__main__":
    main()
