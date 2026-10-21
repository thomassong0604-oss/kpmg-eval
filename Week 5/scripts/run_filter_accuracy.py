"""Filter accuracy for the RAG team (meeting action item: "help the RAG team measure filter accuracy").

    python scripts/run_filter_accuracy.py      -> results/filter_accuracy_v1.json

A. Fiscal labels. RAG derives fiscal_year / fiscal_period (RDS stores neither) with rag.ingest.fiscal_label and a
   per-company fiscal-year-end map (scripts/run_exp1.sh: --fye MSFT=0630,AAPL=0927,NVDA=0126). Checked against SEC's own
   fy/fp for 17 pilot filings (data/filing_pool_v1.json), with RAG's map and with the map missing.
B. Filter precision / recall at filing level over the same 17-filing pool, for three filter sources:
   RAG Gold Set v0 filters (ticker + form only), Gold Set v1 gold filters, and the rule-based extractor baseline.
C. Question -> filter extraction accuracy of the baseline against Gold Set v1 gold filters, per key.
D. Effect on retrieval: evidence recall@10 on the real MSFT index with gold / extracted / no filters, and the section-filter
   hazard (share of evidence-bearing chunks whose section is 'Unlabeled', which any section filter would drop).
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))
from rag.evaluate import evidence_hits, score_question  # noqa: E402
from rag.ingest import fiscal_label as rag_fiscal_label  # noqa: E402
from rag.retrieve import Retriever  # noqa: E402
from rag_fiscal import fiscal_label  # noqa: E402

from kpmg_eval.filters import extract_filters, filing_filter_pr, score_filters  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
RAG_FYE = {"MSFT": "0630", "AAPL": "0927", "NVDA": "0126"}  # scripts/run_exp1.sh in KPMG_RAG; others default to 1231


def main():
    scope = json.loads((ROOT / "config" / "scope.json").read_text())
    pool = json.loads((DATA / "filing_pool_v1.json").read_text())["filings"]
    bench = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
    out = {}

    # ---- A. fiscal labels vs SEC
    rows = []
    for f in pool:
        a = rag_fiscal_label(f["reporting_period_end"], RAG_FYE.get(f["ticker"], "1231"), f["form"])
        assert a == fiscal_label(f["reporting_period_end"], RAG_FYE.get(f["ticker"], "1231"), f["form"])  # vendored copy == upstream
        b = rag_fiscal_label(f["reporting_period_end"], "1231", f["form"])
        truth = (f["sec_fiscal_year"], f["sec_fiscal_period"])
        rows.append({"ticker": f["ticker"], "accession": f["accession"], "period_end": f["reporting_period_end"], "sec": truth,
                     "rag_with_fye_map": a, "ok_with_map": a == truth, "rag_without_map": b, "ok_without_map": b == truth})
    for f in pool:  # label the pool with RAG's derived labels (what the index actually filters on)
        f["fiscal_year"], f["fiscal_period"] = rag_fiscal_label(f["reporting_period_end"], RAG_FYE.get(f["ticker"], "1231"), f["form"])
    out["A_fiscal_labels"] = {
        "n_filings": len(rows), "correct_with_rag_map": sum(r["ok_with_map"] for r in rows),
        "correct_without_map": sum(r["ok_without_map"] for r in rows),
        "wrong_without_map": [f"{r['ticker']} {r['period_end']}: {r['rag_without_map']} vs SEC {r['sec']}" for r in rows if not r["ok_without_map"]],
        "missing_from_rag_map": sorted({f["ticker"] for f in pool} - set(RAG_FYE) - {"AMZN", "META"}),
        "detail": rows}

    # ---- B/C. filter sources
    rag_v0 = {json.loads(l)["qid"]: json.loads(l)["filters"] for l in open(ROOT / "upstream" / "KPMG_RAG" / "eval" / "gold_v0_msft.jsonl")}
    pool_acc = {f["accession"] for f in pool}
    pr = {"rag_gold_v0_filters": [], "gold_v1_filters": [], "extracted_baseline": []}
    ext_scores, ext_rows, ext_mvp = [], [], []
    for q in bench:
        if not q["answerable"]:
            continue
        gold_acc = {k["accession"] for k in q["facts"]} | {e["accession"] for e in q["rag_evidence"] if e.get("accession")}
        gold_acc &= pool_acc
        pred = extract_filters(q["question"], scope, fiscal_label)
        s = score_filters(pred, q["filters"])
        s_mvp = score_filters(extract_filters(q["question"], scope, fiscal_label, session_ticker=scope["mvp"]["ticker"]), q["filters"])
        ext_mvp.append(s_mvp)
        ext_scores.append(s)
        ext_rows.append({"qid": q["qid"], "pred": pred, "gold": q["filters"], **{k: v for k, v in s.items() if k != "per_key"}, "per_key": s["per_key"]})
        if not gold_acc:
            continue
        if q["qid"] in rag_v0:
            pr["rag_gold_v0_filters"].append(filing_filter_pr(rag_v0[q["qid"]], pool, gold_acc))
        pr["gold_v1_filters"].append(filing_filter_pr(q["filters"], pool, gold_acc))
        pr["extracted_baseline"].append(filing_filter_pr(pred, pool, gold_acc))

    def mean(xs, k):
        v = [x[k] for x in xs if x[k] is not None]
        return round(sum(v) / len(v), 3) if v else None

    out["B_filing_filter_pr"] = {k: {"n": len(v), "recall": mean(v, "recall"), "precision": mean(v, "precision"),
                                     "mean_filings_kept": round(sum(x["kept"] for x in v) / len(v), 2) if v else None,
                                     "questions_losing_a_gold_filing": sum(1 for x in v if x["recall"] is not None and x["recall"] < 1)}
                                 for k, v in pr.items()}
    per_key = Counter()
    for s in ext_scores:
        for k, v in s["per_key"].items():
            per_key[(k, v)] += 1
    keys = sorted({k for k, _ in per_key})
    out["C_extraction_baseline"] = {
        "n": len(ext_scores), "exact_match": round(sum(s["exact_match"] for s in ext_scores) / len(ext_scores), 3),
        "any_wrong_key": sum(s["any_wrong"] for s in ext_scores),
        "per_key": {k: {v: per_key[(k, v)] for v in ("correct", "wrong", "missing")} for k in keys},
        "no_company_named": sum(1 for s in ext_scores if s["per_key"].get("ticker") == "missing"),
        "with_mvp_session_context": {"exact_match": round(sum(s["exact_match"] for s in ext_mvp) / len(ext_mvp), 3),
                                     "ticker_correct": sum(1 for s in ext_mvp if s["per_key"].get("ticker") == "correct"),
                                     "any_wrong_key": sum(s["any_wrong"] for s in ext_mvp)},
        "questions_without_period_words": sum(1 for r in ext_rows if "fiscal_period" in r["gold"] and r["per_key"].get("fiscal_period") == "missing"),
        "wrong_examples": [r for r in ext_rows if r["any_wrong"]][:8]}

    # ---- D. retrieval effect on the real MSFT index + section hazard
    retr = Retriever(ROOT / "upstream" / "rag_index_msft_lsa", log_dir=None)
    msft = [q for q in bench if q["corpus"] == "msft_10q_q3fy26" and q["answerable"] and q["rag_evidence"] and q["type"] != "false_premise"]
    eff = {"gold_filters": [], "extracted_filters": [], "no_filters": []}
    for q in msft:
        pred = extract_filters(q["question"], scope, fiscal_label)
        pred = {k: v for k, v in pred.items() if k in ("ticker", "form", "fiscal_year", "fiscal_period")}
        for name, flt in (("gold_filters", q["filters"]), ("extracted_filters", pred), ("no_filters", None)):
            res = retr.search(q["question"], filters=flt, top_k=10, method="bm25")["results"]
            eff[name].append(score_question({"gold": {"evidence": q["rag_evidence"]}}, res, (10,))["evidence_recall@10"])
    chunks = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl")]
    ev_chunks = {c["chunk_id"] for q in msft for e in q["rag_evidence"] for c in chunks
                 if evidence_hits(e, {**c, "accession_number": c["accession"]})}
    unl = sum(1 for c in chunks if c["chunk_id"] in ev_chunks and c["section"] == "Unlabeled")
    out["D_retrieval_effect"] = {"n": len(msft), **{k: round(sum(v) / len(v), 4) for k, v in eff.items()},
                                 "note": "Single-filing index: filters cannot remove distractor filings here, only evidence (when wrong)."}
    out["D_section_hazard"] = {"evidence_bearing_chunks": len(ev_chunks), "labelled_unlabeled": unl,
                               "share_lost_to_any_section_filter": round(unl / len(ev_chunks), 3) if ev_chunks else None}
    RES.mkdir(exist_ok=True)
    (RES / "filter_accuracy_v1.json").write_text(json.dumps(out, indent=1, default=list))
    a = out["A_fiscal_labels"]
    print(f"[filters] A fiscal labels: {a['correct_with_rag_map']}/{a['n_filings']} with RAG's FYE map, {a['correct_without_map']}/{a['n_filings']} without")
    for w in a["wrong_without_map"]:
        print("            ", w)
    print("[filters] B filing-level P/R:", json.dumps(out["B_filing_filter_pr"]))
    print("[filters] C extraction:", json.dumps({k: v for k, v in out["C_extraction_baseline"].items() if k != "wrong_examples"}))
    for r in out["C_extraction_baseline"]["wrong_examples"]:
        print("            ", r["qid"], r["per_key"], r["pred"])
    print("[filters] D:", json.dumps(out["D_retrieval_effect"]), json.dumps(out["D_section_hazard"]))


if __name__ == "__main__":
    main()
