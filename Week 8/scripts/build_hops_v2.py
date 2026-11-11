"""Week 8: hops sheet v2, split into two columns as GraphRAG proposed on 11/11, and agreed by Eval.

    python scripts/build_hops_v2.py   -> data/hops_v2.csv

  filings   distinct accessions whose evidence the gold answer needs. Eval fills it in code from the gold evidence
            (facts, text anchors, gold evidence), so it re-runs when questions change. Measures what vector retrieval
            struggles with: a question answerable from one filing should not score like one that joins several.
  hops      edges traversed on the agreed ontology path, from the entity the question names to the evidence that
            answers it (base path Company -FILES-> Filing -CONTAINS-> Section -SUPPORTS-> Claim). Measures graph
            difficulty. GraphRAG derives it in code from the ontology path; left blank here.
  graph_support, graph_path   GraphRAG's review of the six relationship drafts (reply of 11/11); blank elsewhere.

Keyed on Gold Set v2.1 (155 questions). Replaces data/hops_v1.csv (165 rows keyed on Gold Set v1 + drafts + scope10,
none filled), which stays for reference.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.graphrag_filters import load_snapshot, required_filings  # noqa: E402

DATA = ROOT / "data"
# GraphRAG, reply to Eval week 8 (2026-11-11), section 5
GRAPH_REVIEW = {
    "EV1R-001": ("Filing -HAS_EXHIBIT-> Exhibit 21 -LISTS-> Subsidiary", "not_yet",
                 "Exhibit 21 is PR #34; no HAS_EXHIBIT or LISTS edge on main (output exists on alina/ex21-pipeline)"),
    "EV1R-002": ("ProductLine -RENAMED_FROM-> ProductLine", "no",
                 "no RENAMED_FROM edge and no ProductLine node; segment half answerable, rename half not"),
    "EV1R-003": ("Event -AFFECTS-> Investment -REPORTED_IN-> ...", "supported_by_text",
                 "claim-level: MD&A sentences held, Event not a node, resolves by text not traversal"),
    "EV1R-004": ("absent edge", "supported", "the absence is real in the graph"),
    "EV1R-005": ("absent edge", "supported", "same shape as EV1R-004"),
    "EV1R-006": ("Exhibit 21 -LISTS-> Activision -PART_OF-> XBOX -IN_SEGMENT-> More Personal Computing", "partly",
                 "first edge depends on Exhibit 21 (PR #34); revenue direction right, Activision attribution not available"),
}


def main():
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2_1.jsonl")]
    snap = load_snapshot(DATA / "snapshot_w7.json")
    rows = []
    for q in gold:
        accs = required_filings(q)
        path, support, note = GRAPH_REVIEW.get(q["qid"], ("", "", ""))
        rows.append({"qid": q["qid"], "route_expected": q["route_expected"], "answerable": q["answerable"],
                     "filings": len(accs), "filing_accessions": " ".join(accs),
                     "filing_forms": " ".join(sorted({snap[a]["form"] for a in accs if a in snap})),
                     "hops": "", "graph_path": path, "graph_support": support, "graph_note": note,
                     "filled_by": "eval:filings" + (" graphrag:review" if support else ""), "reviewed_by": ""})
    with open(DATA / "hops_v2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    dist = {}
    for r in rows:
        dist[r["filings"]] = dist.get(r["filings"], 0) + 1
    print(f"[hops v2] {len(rows)} rows; questions by filings needed: {dict(sorted(dist.items()))}")


if __name__ == "__main__":
    main()
