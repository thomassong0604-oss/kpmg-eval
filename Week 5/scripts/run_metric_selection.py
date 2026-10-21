"""Narrow the metric set to a 4-metric headline scorecard (meeting action item: "narrow the metrics to 3 to 5").

    python scripts/run_metric_selection.py    -> results/metric_selection_v1.json

Every candidate is scored on five criteria. Each mark is backed by an artifact in results/, not by opinion:
  outcome    measures something a KPMG user sees in the answer (right number, honest refusal, traceable source)
  automatic  computed without an LLM judge or a human (cheap, deterministic, runnable on every commit)
  validated  its grader has been checked: planted errors (fault injection), a perfect system (oracle run), human labels
  owner      a bad score points to the team that must fix it
  any_arch   works unchanged for VectorRAG, GraphRAG and the Agent (keyed on EvalKey, not on chunk ids)
Data-driven checks added here:
  redundancy     Spearman correlation between retrieval metrics over the 76 questions (RAG BM25 run)
  sensitivity    paired bootstrap difference between two rankers (BM25 vs hybrid-LSA) per retrieval metric
  separation     headline values for oracle / baseline / refuse-all from the grading pipeline (a metric that cannot
                 tell those three apart is useless as a headline)
"""
from __future__ import annotations

import csv
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.stats import paired_bootstrap_diff  # noqa: E402

RES = ROOT / "results"

# candidate -> (stage, criteria marks, evidence, role)
#   marks: 2 = yes with evidence, 1 = partly, 0 = no
CANDIDATES = [
    ("Numerical answer accuracy (NAA)", "Answer", dict(outcome=2, automatic=2, validated=2, owner=2, any_arch=2),
     "389/389 planted errors labelled (fault_injection_v1); oracle 1.00, refuse-all 0.00 (scorecards); 8 error labels name the failing cell", "headline"),
    ("Evidence recall@10", "Retrieval", dict(outcome=1, automatic=2, validated=2, owner=2, any_arch=2),
     "RAG's own definition (rag.evaluate); 98% of anchors match RAG chunks; ceiling on answers: gold figure in top 10 for 94% of numeric questions", "headline"),
    ("Balanced refusal accuracy", "Answer", dict(outcome=2, automatic=2, validated=2, owner=2, any_arch=2),
     "142-item paired suite; oracle 1.00, refuse-all 0.50; scope gate 0.89 vs no gate 0.50 (abstention_v1)", "headline"),
    ("Citation support", "Grounding", dict(outcome=2, automatic=2, validated=1, owner=2, any_arch=2),
     "oracle 1.00 after 2 scorer fixes; baseline 0.92; planted-error check still to do", "headline"),
    ("MRR@10", "Retrieval", dict(outcome=0, automatic=2, validated=2, owner=2, any_arch=2), "redundant with nDCG@10 (see redundancy)", "diagnostic"),
    ("nDCG@10 (graded)", "Retrieval", dict(outcome=0, automatic=2, validated=1, owner=2, any_arch=2), "redundant with MRR", "diagnostic"),
    ("Hit@k", "Retrieval", dict(outcome=0, automatic=2, validated=2, owner=2, any_arch=2), "saturates (1.00 on lookups); weaker than recall for multi-evidence questions", "diagnostic"),
    ("Provenance@k", "Retrieval", dict(outcome=0, automatic=2, validated=1, owner=2, any_arch=2), "1.00 whenever filters are set; only informative unfiltered", "diagnostic"),
    ("Answer-in-context@k", "Retrieval to answer", dict(outcome=1, automatic=2, validated=1, owner=2, any_arch=2), "splits retrieval vs reading failures (24 of 25 lookups retrieved)", "diagnostic"),
    ("Error taxonomy (8 labels)", "Answer", dict(outcome=1, automatic=2, validated=2, owner=2, any_arch=2), "explains NAA; part of the NAA report, not a separate score", "diagnostic"),
    ("Reasoning-step accuracy", "Calculation", dict(outcome=1, automatic=2, validated=1, owner=2, any_arch=2), "needs the Agent's step trace; tested on constructed traces only", "diagnostic"),
    ("Filter accuracy", "Retrieval", dict(outcome=0, automatic=2, validated=1, owner=2, any_arch=1), "17/17 fiscal labels with RAG's map; filing-level P/R", "diagnostic"),
    ("Query-wording robustness", "Retrieval", dict(outcome=1, automatic=2, validated=1, owner=2, any_arch=2), "recall 1.00 -> 0.52 under analyst wording", "diagnostic"),
    ("Fact extraction P/R/F1, edges, paths", "Graph", dict(outcome=0, automatic=2, validated=1, owner=2, any_arch=0), "GraphRAG-only; fault-injected only (no graph yet)", "diagnostic"),
    ("Run-to-run consistency", "System", dict(outcome=1, automatic=2, validated=1, owner=1, any_arch=2), "needs repeated Agent runs", "diagnostic"),
    ("Latency, errors, cost/query", "System", dict(outcome=1, automatic=2, validated=1, owner=1, any_arch=2), "operational, reported beside the scorecard", "diagnostic"),
    ("Narrative faithfulness (LLM judge)", "Answer", dict(outcome=2, automatic=0, validated=0, owner=1, any_arch=2), "26 narrative questions need it; judge not validated yet", "deferred"),
    ("Answer relevance (LLM judge)", "Answer", dict(outcome=1, automatic=0, validated=0, owner=1, any_arch=2), "LLM judge, not validated", "deferred"),
]


def spearman(a, b):
    def rank(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r, i = [0.0] * len(x), 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else None


def main():
    rows = [r for r in csv.DictReader(open(RES / "rag_retrieval_v1_per_question.csv")) if r.get("mrr")]
    M = ["evidence_recall@10", "hit@10", "mrr", "ndcg@10"]
    bm = [r for r in rows if r["method"] == "bm25"]
    hy = {r["qid"]: r for r in rows if r["method"] == "hybrid"}
    red = {f"{a} vs {b}": round(spearman([float(r[a]) for r in bm], [float(r[b]) for r in bm]), 2) for a, b in combinations(M, 2)}
    sens = {}
    for m in M:
        a = [float(r[m]) for r in bm]
        b = [float(hy[r["qid"]][m]) for r in bm]
        d = paired_bootstrap_diff(a, b)
        sens[m] = {"bm25_minus_hybridLSA": round(d["mean_diff"], 3), "ci95": [round(x, 3) for x in d["ci95"]],
                   "separates": d["ci95"][0] > 0 or d["ci95"][1] < 0}
    sep = {}
    for name in ("oracle", "baseline", "refuse_all"):
        c = json.loads((RES / f"scorecard_{name}.json").read_text())
        sep[c["system"]] = {k: v["value"] for k, v in c["headline"].items()}
    table = []
    for name, stage, marks, evidence, role in CANDIDATES:
        table.append({"metric": name, "stage": stage, **marks, "score": sum(marks.values()), "evidence": evidence, "role": role})
    table.sort(key=lambda r: (-r["score"], r["metric"]))
    out = {"criteria": ["outcome", "automatic", "validated", "owner", "any_arch"],
           "headline": [r["metric"] for r in table if r["role"] == "headline"],
           "north_star": "Numerical answer accuracy (NAA)",
           "fifth_slot": "Narrative answer quality, once an LLM judge is validated against human labels (26 narrative questions)",
           "candidates": table, "redundancy_spearman_bm25": red, "sensitivity_bm25_vs_hybridLSA": sens, "separation": sep}
    (RES / "metric_selection_v1.json").write_text(json.dumps(out, indent=1))
    for r in table:
        print(f"{r['score']:2d} {r['role']:10s} {r['metric']}")
    print("redundancy:", red)
    print("sensitivity:", json.dumps(sens))
    print("separation:", json.dumps(sep))


if __name__ == "__main__":
    main()
