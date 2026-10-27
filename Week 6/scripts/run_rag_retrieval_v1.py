"""Score the RAG team's REAL retriever on the real Microsoft 10-Q with Gold Set v1.

    python scripts/run_rag_retrieval_v1.py      -> results/rag_retrieval_v1.json, results/rag_retrieval_v1_per_question.csv

Week 4 could only run the mock (6 hand-picked chunks). This runs RAG's own code at commit 1996e72:
  chunks   rag.chunk.chunk_filing on the Data team's copy of the filing (158 chunks; data/rag_chunks_msft_10q.jsonl)
  index    rag.index.build_index, custom backend
  search   rag.retrieve.Retriever.search(query, filters, top_k, method)
  scoring  rag.evaluate.score_question (RAG's metric definitions) + kpmg_eval metrics for what RAG's do not cover

Methods: "bm25" is RAG's production BM25 exactly. RAG's dense model (BAAI/bge-small-en-v1.5) cannot be downloaded in
this environment (huggingface.co is blocked), so "dense" and "hybrid" use RAG's built-in offline stand-in, LSA, which
RAG's config labels "offline smoke-test only (NOT a real dense baseline)". Read hybrid-LSA as a lower bound for hybrid.

Scope: questions on the Microsoft Q3 FY2026 10-Q (the one filing every team has). Peer and 10-K questions are listed
as pending until RAG shares its multi-company chunks.jsonl.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))

from rag.evaluate import score_question  # noqa: E402  (RAG's own metric code)
from rag.index import build_index  # noqa: E402
from rag.retrieve import Retriever  # noqa: E402

from kpmg_eval.metrics.abstention import auroc, best_threshold  # noqa: E402
from kpmg_eval.metrics.context import answer_in_context, evidence_rank, rank_summary  # noqa: E402
from kpmg_eval.metrics.retrieval import rag_adapter, score_retrieval  # noqa: E402
from kpmg_eval.metrics.robustness import jaccard_at_k, strip_period  # noqa: E402
from kpmg_eval.stats import bootstrap_ci, paired_bootstrap_diff  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
INDEX = ROOT / "upstream" / "rag_index_msft_lsa"
METHODS = ("bm25", "dense", "hybrid")
KS = (1, 3, 5, 10)
MSFT_CIK = "0000789019"

# Short analyst phrasings for the robustness check (ticker + fiscal label, no statement line-item wording).
ANALYST = {
    "GSv0-MSFT-001": "MSFT Q3 FY26 revenue", "GSv0-MSFT-002": "MSFT Q3 FY26 GAAP earnings",
    "GSv0-MSFT-003": "MSFT YTD FY26 operating cash flow", "EV1-001": "MSFT Q3 FY26 EBIT",
    "EV1-002": "MSFT FY26 YTD EBIT", "EV1-003": "MSFT FY26 YTD earnings", "EV1-004": "MSFT Q3 FY26 EPS",
    "EV1-005": "MSFT Q3 FY26 gross profit", "EV1-006": "MSFT Q3 FY26 R&D spend", "EV1-007": "MSFT Q3 FY26 capex",
    "EV1-008": "MSFT balance sheet size March 2026", "EV1-009": "MSFT cash on hand March 2026",
    "EV1-010": "MSFT book value March 2026", "EV1-011": "MSFT long-term borrowings March 2026",
    "EV1-012": "MSFT deferred revenue March 2026", "EV1-013": "MSFT FY26 YTD investing cash flow",
    "EV1-014": "MSFT FY26 YTD buybacks", "EV1-015": "MSFT Q3 FY26 dividend per share",
    "EV1-017": "MSFT Intelligent Cloud sales Q3 FY26", "EV1-018": "MSFT PBP segment profit Q3 FY26",
    "EV1-019": "MSFT MPC sales Q3 FY26", "EV1-020": "Xbox and gaming sales Q3 FY26",
    "EV1-021": "LinkedIn sales FY26 YTD", "EV1-022": "MSFT server and cloud sales Q3 FY26", "EV1-023": "MSFT US sales Q3 FY26",
}


def mm(v: float) -> str:
    m = v / 1e6
    return f"{m:,.0f}"


def figures_for(q: dict) -> list[str]:
    """Figures that must be in context to answer: the displayed answer for lookups, every input for calculations."""
    a = q["answer"]
    if a.get("value") is None:
        return []
    if q["type"] in ("extraction", "segment") and len(q["facts"]) == 1:
        return [a["required_points"][0]]
    figs = []
    for k, (lab, v) in zip(q["facts"], q["fact_values"].items()):
        if k["unit"] == "USD":
            figs.append(mm(abs(v)))
        elif k["unit"] == "USD/shares":
            figs.append(f"{v:.2f}")
        elif k["unit"] == "pure":
            figs.append(f"{v * 100:.0f}%")
    if "54.5 billion" in " ".join(a["required_points"]):
        figs.append("54.5 billion")
    if "(4,483)" in a["required_points"]:
        figs.append("4,483")
    return figs


def main():
    bench = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
    if INDEX.exists():
        shutil.rmtree(INDEX)
    meta = build_index(DATA / "rag_chunks_msft_10q.jsonl", INDEX, "lsa")
    retr = Retriever(INDEX, log_dir=None)

    in_scope = [q for q in bench if q["corpus"] == "msft_10q_q3fy26"]
    pending = [q["qid"] for q in bench if q["corpus"] not in ("msft_10q_q3fy26", "none")]
    answerable = [q for q in in_scope if q["answerable"] and q["rag_evidence"] and q["type"] != "false_premise"]
    unans = [q for q in bench if not q["answerable"] and q["filters"].get("ticker") == "MSFT"]

    rows, top1 = [], defaultdict(lambda: {"pos": [], "neg": []})
    ranks = defaultdict(list)
    for method in METHODS:
        for q in answerable:
            resp = retr.search(q["question"], filters=q["filters"], top_k=max(KS), method=method)
            res = resp["results"]
            gold = {"chunk_ids": [], "evidence": q["rag_evidence"]}
            s = score_question({"gold": gold, "expected": {"ticker": ["MSFT"]}}, res, KS)          # RAG's metrics
            ours = score_retrieval([{**{k: e[k] for k in ("accession",)}, "cik": MSFT_CIK, "contains": e["contains"], "level": "FILING"}
                                    for e in q["rag_evidence"]], rag_adapter(res), ks=(5, 10))      # + graded nDCG
            texts = [r["text"] for r in res]
            figs = figures_for(q)
            from rag.evaluate import is_relevant
            flags = [is_relevant(gold, r) for r in res]
            ranks[method].append(evidence_rank(flags))
            row = {"qid": q["qid"], "method": method, "type": q["type"], "tier": q["tier"], "route": q["route"], "source": q["source"],
                   "traps": " ".join(q["traps"]), **{m: round(v, 4) for m, v in s.items()},
                   "ndcg@10": round(ours["ndcg@10"], 4), "first_relevant_rank": evidence_rank(flags),
                   "top1_score": res[0]["score"] if res else None, "latency_ms": resp["latency_ms"]}
            if figs:
                for k in (5, 10):
                    row[f"answer_in_context@{k}"] = answer_in_context(figs, texts, k)
            rows.append(row)
            if res:
                top1[method]["pos"].append(res[0]["score"])
        for q in unans:
            res = retr.search(q["question"], filters=q["filters"], top_k=10, method=method)["results"]
            rows.append({"qid": q["qid"], "method": method, "type": q["type"], "tier": q["tier"], "route": q["route"], "source": q["source"],
                         "traps": " ".join(q["traps"]), "n_returned": len(res), "top1_score": res[0]["score"] if res else None})
            if res:
                top1[method]["neg"].append(res[0]["score"])

    # ---- summaries
    def agg(rs, key):
        vals = [r[key] for r in rs if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    summary = {}
    for method in METHODS:
        rs = [r for r in rows if r["method"] == method and "mrr" in r]
        block = {"n": len(rs)}
        for key in ("evidence_recall@1", "evidence_recall@5", "evidence_recall@10", "hit@5", "hit@10", "mrr", "ndcg@10",
                    "answer_in_context@5", "answer_in_context@10", "latency_ms"):
            block[key] = agg(rs, key)
        block["evidence_recall@10_ci95"] = [round(x, 3) for x in bootstrap_ci([r["evidence_recall@10"] for r in rs])]
        for dim in ("type", "route", "source", "tier"):
            block[f"by_{dim}"] = {v: {"n": len([r for r in rs if r[dim] == v]),
                                      "evidence_recall@10": agg([r for r in rs if r[dim] == v], "evidence_recall@10"),
                                      "mrr": agg([r for r in rs if r[dim] == v], "mrr")}
                                  for v in sorted({r[dim] for r in rs})}
        trap = [r for r in rs if "quarter_vs_ytd" in r["traps"]]
        block["quarter_vs_ytd_items"] = {"n": len(trap), "evidence_recall@10": agg(trap, "evidence_recall@10")}
        block["evidence_position"] = rank_summary(ranks[method], 10)
        pos, neg = top1[method]["pos"], top1[method]["neg"]
        block["abstention"] = {"n_answerable": len(pos), "n_unanswerable_with_results": len(neg),
                               "n_unanswerable_empty": sum(1 for r in rows if r["method"] == method and r.get("n_returned") == 0),
                               "auroc_top1_score": round(auroc(pos, neg), 3) if neg else None, **best_threshold(pos, neg)}
        summary[method] = block

    # paired comparison bm25 vs hybrid-LSA on evidence_recall@10
    a = [r["evidence_recall@10"] for r in rows if r["method"] == "bm25" and "mrr" in r]
    b = [r["evidence_recall@10"] for r in rows if r["method"] == "hybrid" and "mrr" in r]
    summary["paired_bm25_minus_hybridLSA_recall@10"] = paired_bootstrap_diff(a, b)

    # ---- RAG Experiment 1 side-by-side on the 30 Gold Set v0 questions
    exp1 = json.load(open(ROOT / "upstream" / "KPMG_RAG" / "eval" / "results" / "run_20261014-174752.json"))
    e1 = {(s["method"], s["tier"]): s for s in exp1["summary"] if s["filters"] == "filtered"}
    side = {}
    for method in METHODS:
        rs = [r for r in rows if r["method"] == method and r["source"] == "rag_gold_v0" and "mrr" in r]
        side[method] = {"eval_offline": {"n": len(rs), "evidence_recall@10": agg(rs, "evidence_recall@10"), "mrr": agg(rs, "mrr"),
                                         "evidence_recall@5": agg(rs, "evidence_recall@5")},
                        "rag_exp1_reported": {k: e1[(method, "ALL")][k] for k in ("n", "evidence_recall@10", "mrr", "evidence_recall@5")}}
    summary["vs_rag_experiment1"] = {"note": "Exp 1: RDS chunks, 5 companies (1,780 chunks), bge-small dense. Eval offline: RAG chunker on the "
                                             "Data team's HTML, 1 filing (158 chunks), LSA dense. BM25 rows are the like-for-like comparison.",
                                     "by_method": side}

    # ---- robustness (bm25 = production lexical ranker)
    rob = []
    for q in answerable:
        if q["qid"] not in ANALYST:
            continue
        gold = {"chunk_ids": [], "evidence": q["rag_evidence"]}
        base = retr.search(q["question"], filters=q["filters"], top_k=10, method="bm25")["results"]
        out = {"qid": q["qid"]}
        for name, text in (("filing_wording", q["question"]), ("no_period", strip_period(q["question"])), ("analyst", ANALYST[q["qid"]])):
            res = retr.search(text, filters=q["filters"], top_k=10, method="bm25")["results"]
            sc = score_question({"gold": gold}, res, (5, 10))
            out[name] = {"query": text, "evidence_recall@5": sc["evidence_recall@5"], "evidence_recall@10": sc["evidence_recall@10"], "mrr": sc["mrr"],
                         "jaccard@10_vs_original": round(jaccard_at_k([r["chunk_id"] for r in base], [r["chunk_id"] for r in res], 10), 3)}
        rob.append(out)
    rsum = {}
    for name in ("filing_wording", "no_period", "analyst"):
        rsum[name] = {m: round(sum(r[name][m] for r in rob) / len(rob), 4) for m in ("evidence_recall@5", "evidence_recall@10", "mrr", "jaccard@10_vs_original")}
    summary["robustness_bm25"] = {"n": len(rob), "summary": rsum}

    # ---- chunk-level corpus findings for the RAG team
    chunks = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl")]
    summary["corpus_findings"] = {
        "n_chunks": len(chunks), "n_table_chunks": sum(c["is_table"] for c in chunks),
        "share_section_unlabeled": round(sum(c["section"] == "Unlabeled" for c in chunks) / len(chunks), 3),
        "negative_number_rendering": "'( 84,669)' (space after parenthesis) — anchors written as '(84,669)' never match",
        "rag_gold_v0_anchor_misses": ["GSv0-MSFT-023 balance: 'authorized 24,000; outstanding 7,429' (chunker emits '24,000 ; outstanding')",
                                      "GSv0-MSFT-030 balance: same anchor"],
    }

    out = {"index": {k: meta[k] for k in ("index_version", "embedder", "n_chunks")}, "rag_commit": "1996e72",
           "n_answerable_scored": len(answerable), "n_unanswerable": len(unans), "pending_corpus_qids": pending,
           "summary": summary, "robustness_detail": rob}
    RES.mkdir(exist_ok=True)
    (RES / "rag_retrieval_v1.json").write_text(json.dumps(out, indent=1))
    cols = sorted({k for r in rows for k in r}, key=lambda c: (c not in ("qid", "method", "type", "tier", "route", "source"), c))
    with open(RES / "rag_retrieval_v1_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for m in METHODS:
        s = summary[m]
        print(f"[rag] {m:6s} n={s['n']} R@5={s['evidence_recall@5']} R@10={s['evidence_recall@10']} MRR={s['mrr']} "
              f"nDCG@10={s['ndcg@10']} AiC@5={s['answer_in_context@5']} AiC@10={s['answer_in_context@10']} "
              f"abst-AUROC={s['abstention']['auroc_top1_score']}")
    print("[rag] vs Exp1:", json.dumps(side))
    print("[rag] robustness:", json.dumps(rsum))
    print("[rag] by type (bm25):", json.dumps(summary["bm25"]["by_type"]))
    print("[rag] by route (bm25):", json.dumps(summary["bm25"]["by_route"]))
    print("[rag] position (bm25):", summary["bm25"]["evidence_position"], " abst:", summary["bm25"]["abstention"])
    print("[rag] pending corpus:", len(pending))


if __name__ == "__main__":
    main()
