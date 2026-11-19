"""Week 9: RAG and GraphRAG on the same questions with the same metric, by question type.

    python scripts/compare_by_type.py -> results/rag_vs_graphrag_by_type.json, results/rag_vs_graphrag_by_type.csv

Metric for every system: is the evidence the gold answer needs in the top 10 results (every needed figure for a number
question, every text anchor for a prose question; same rule as Week 8's side by side). Gold Set v2.2, 20 filings.
  RAG        RAG's own retriever (pinned commit 5bfafeb), BM25 and hybrid, built here over RAG's round-1 chunks (3,736
             chunks, all 20 filings), called with the question's gold filters. Hybrid uses RAG's local LSA vectors, not
             its production embedding model, so BM25 is the like-for-like figure.
  GraphRAG   structured search at main a1e7cf7 on GraphRAG's 20-filing store (Eval's re-run, 11/14), and graph search
             from GraphRAG's own run on its live graph (11/11, before Exhibit 21 was loaded). Translated filters.
Questions a system cannot be scored on (no anchor, filing not in its store, unanswerable) are left out of its row and
counted. "Either" = the evidence is in at least one system's top 10: the ceiling for a perfect router.
"""
import csv
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
W8 = ROOT.parent / "Week 8"
sys.path[:0] = [str(W8), str(W8 / "scripts")]
import run_side_by_side as sbs  # noqa: E402

RES = ROOT / "results"
sbs.K = 10
GROUP = {"extraction": "Lookup", "segment": "Lookup", "calculation": "Calculation", "derived": "Calculation", "comparison": "Calculation",
         "reconciliation": "Calculation", "cross_company": "Cross-company", "narrative": "Narrative", "definition": "Narrative",
         "event": "Narrative", "fiscal_calendar": "Narrative", "false_premise": "False premise", "relationship": "Relationship (Exhibit 21)",
         "fabricated_relationship": "Relationship (Exhibit 21)"}


def tf(x):
    return {"True": True, "False": False}.get(x)


def main():
    gold = [json.loads(l) for l in open(W8 / "data" / "benchmark_v2_2.jsonl")]
    retr = sbs.build_rag(W8 / "private" / "chunks_C1.jsonl", ROOT / "private" / "_rag_index_c1")
    st = {r["qid"]: r for r in csv.DictReader(open(W8 / "results" / "graphrag_round1_eval_store20_a1e7cf7.csv"))
          if r["arm"] == "structured" and r["filters_mode"] == "translated"}
    gr = {r["qid"]: r for r in csv.DictReader(open(W8 / "results" / "graphrag_round1_graphrag_aura.csv"))
          if r["arm"] == "graph" and r["filters_mode"] == "translated"}
    rows = []
    for q in gold:
        if not q["answerable"]:
            continue
        row = {"qid": q["qid"], "type": q["type"], "group": GROUP.get(q["type"], q["type"]), "kind": sbs.kind(q),
               "route_expected": q["route_expected"], "msft": q["tickers"] == ["MSFT"]}
        for m in ("bm25", "hybrid"):
            try:
                texts, _ = sbs.rag_run(retr, q, m)
                row[f"rag_{m}"] = sbs.score_rag(q, texts).get("needed_in_evidence")
            except Exception as exc:  # noqa: BLE001 - a filter RAG's retriever does not take; recorded, not scored
                row[f"rag_{m}"], row["rag_error"] = None, f"{type(exc).__name__}: {exc}"[:90]
        row["graphrag_structured"] = tf(st.get(q["qid"], {}).get("needed_in_evidence", ""))
        row["graphrag_graph"] = tf(gr.get(q["qid"], {}).get("needed_in_evidence", ""))
        vals = [row[k] for k in ("rag_bm25", "graphrag_structured", "graphrag_graph")]
        row["either"] = None if all(v is None for v in vals) else any(v is True for v in vals)
        rows.append(row)
    systems = ("rag_bm25", "rag_hybrid", "graphrag_structured", "graphrag_graph", "either")

    def block(rs):
        out = {"questions": len(rs)}
        for s in systems:
            sc = [r[s] for r in rs if r[s] is not None]
            out[s] = {"k": sum(sc), "n": len(sc), "rate": round(sum(sc) / len(sc), 3) if sc else None}
        both = [r for r in rs if r["rag_bm25"] is not None and r["graphrag_structured"] is not None]
        out["rag_bm25_vs_graphrag_structured"] = {"scored_by_both": len(both), "both": sum(r["rag_bm25"] and r["graphrag_structured"] for r in both),
                                                  "only_rag": sum(r["rag_bm25"] and not r["graphrag_structured"] for r in both),
                                                  "only_graphrag": sum(r["graphrag_structured"] and not r["rag_bm25"] for r in both),
                                                  "neither": sum(not r["rag_bm25"] and not r["graphrag_structured"] for r in both)}
        return out

    by = defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)
    out = {"_doc": __doc__.strip().split("\n")[0], "gold": "benchmark_v2_2.jsonl", "k": 10, "answerable_questions": len(rows),
           "rag_commit": "5bfafeb", "graphrag_commit_structured": "a1e7cf7", "graph_search_run": "GraphRAG, 11/11 (before Exhibit 21 was loaded)",
           "rag_errors": sorted({r["rag_error"] for r in rows if r.get("rag_error")}), "all": block(rows),
           "by_question_type": {g: block(v) for g, v in sorted(by.items(), key=lambda x: -len(x[1]))},
           "by_evidence_kind": {k: block([r for r in rows if r["kind"] == k]) for k in ("number", "prose")},
           "by_company": {"Microsoft": block([r for r in rows if r["msft"]]), "other": block([r for r in rows if not r["msft"]])}}
    (RES / "rag_vs_graphrag_by_type.json").write_text(json.dumps(out, indent=1))
    with open(RES / "rag_vs_graphrag_by_type.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "type", "group", "kind", "route_expected", "msft", *systems, "rag_error"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    f2 = lambda d: f"{d['k']}/{d['n']}"  # noqa: E731
    print(f"{'type':28}{'n':>4}  " + "  ".join(f"{s[:14]:>14}" for s in systems))
    for g, b in [("ALL", out["all"]), *out["by_question_type"].items(), *out["by_evidence_kind"].items(), *out["by_company"].items()]:
        print(f"{g:28}{b['questions']:>4}  " + "  ".join(f"{f2(b[s]):>14}" for s in systems), b["rag_bm25_vs_graphrag_structured"])
    print("rag errors:", out["rag_errors"])


if __name__ == "__main__":
    main()
