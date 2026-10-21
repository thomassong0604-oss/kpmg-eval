"""End-to-end harness check on the RAG team's real contract: score their mock retrieve() (PR #3, MIT license,
vendored unchanged in vendor/mock_retrieval_tool.py) with our key-based retrieval metrics.

The mock holds 6 verbatim chunks of Microsoft's 10-Q for the quarter ended March 31, 2026
(accession 0001193125-26-191507) and ranks by keyword overlap. These numbers measure the MOCK, not the
RAG system: they prove the harness runs on the real interface and show what the metrics surface.
Each question is asked two ways: wording that reuses filing terms, and a paraphrase an analyst might type.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.metrics.retrieval import mean_metrics, rag_adapter, score_retrieval  # noqa: E402
from kpmg_eval.stats import bootstrap_ci  # noqa: E402

spec = importlib.util.spec_from_file_location("mock", ROOT / "vendor" / "mock_retrieval_tool.py")
mock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock)

CIK, ACC = "0000789019", "0001193125-26-191507"


def ev(*contains, section=None):
    e = {"cik": CIK, "accession": ACC, "contains": list(contains), "level": "SECTION" if section else "FILING"}
    if section:
        e["section"] = section
    return e


# (qid, filing-term wording, analyst paraphrase, gold evidence)
Q = [
    ("M01", "What was Microsoft's total revenue for the three months ended March 31, 2026?",
     "How much did Microsoft sell in its March 2026 quarter?", [ev("82,886")]),
    ("M02", "What was Microsoft's net income for the three months ended March 31, 2026?",
     "How much profit did Microsoft make last quarter?", [ev("31,778")]),
    ("M03", "What was net cash from operations for the nine months ended March 31, 2026?",
     "How much cash did Microsoft's business generate so far this fiscal year?", [ev("127,494")]),
    ("M04", "What were additions to property and equipment in the three months ended March 31, 2026?",
     "How much did Microsoft spend on capex last quarter?", [ev("30,876")]),
    ("M05", "What was Intelligent Cloud revenue for the three months ended March 31, 2026?",
     "How big was the Azure / cloud segment's top line in Q3?", [ev("Intelligent Cloud Revenue $ 34,681")]),
    ("M06", "What was More Personal Computing operating income for the three months ended March 31, 2026?",
     "How profitable was the Windows, devices and gaming business last quarter?", [ev("3,672")]),
    ("M07", "What was Microsoft Cloud revenue for the three months ended March 31, 2026?",
     "How large is Microsoft's cloud business by sales?", [ev("$54.5 billion")]),
    ("M08", "How much revenue was allocated to remaining performance obligations as of March 31, 2026?",
     "What is Microsoft's contracted backlog?", [ev("$633 billion")]),
    ("M09", "Why did revenue increase in the three months ended March 31, 2026 compared with 2025?",
     "What drove Microsoft's growth this quarter?", [ev("driven by growth in Microsoft Cloud", section="Part I Item 2")]),
    ("M10", "What was Productivity and Business Processes operating income for the nine months ended March 31, 2026?",
     "How much operating profit did the Office and LinkedIn segment make year to date?", [ev("61,979")]),
]
UNANSWERABLE = [
    ("MU1", "How many employees does Microsoft have?"),
    ("MU2", "What was Microsoft's revenue in fiscal 2027?"),
    ("MU3", "What dividend did Microsoft declare per share this quarter?"),
]

KS = (1, 3, 5)
rows = []
for qid, exact, para, gold in Q:
    for style, text in (("filing_terms", exact), ("paraphrase", para)):
        res = mock.retrieve(text, filters={"ticker": "MSFT", "form": "10-Q"}, top_k=5)
        s = score_retrieval(gold, rag_adapter(res), ks=KS, expected_ciks={CIK})
        rows.append({"qid": qid, "style": style, "query": text, "n_returned": len(res),
                     "top1_score": res[0]["score"] if res else 0.0, **s,
                     "top1_chunk": res[0]["metadata"]["section_title"] if res else None})

unans = []
for qid, text in UNANSWERABLE:
    res = mock.retrieve(text, filters={"ticker": "MSFT"}, top_k=5)
    unans.append({"qid": qid, "query": text, "n_returned": len(res), "top1_score": res[0]["score"] if res else 0.0})

summary = {}
for style in ("filing_terms", "paraphrase"):
    rs = [r for r in rows if r["style"] == style]
    m = mean_metrics([{k: v for k, v in r.items() if isinstance(v, float) and k != "top1_score"} for r in rs])
    m["mrr_ci95"] = bootstrap_ci([r["mrr"] for r in rs])
    m["hit@5_ci95"] = bootstrap_ci([r["hit@5"] for r in rs])
    summary[style] = m
summary["unanswerable"] = {"n": len(unans), "returned_results": sum(u["n_returned"] > 0 for u in unans),
                           "top1_scores": [u["top1_score"] for u in unans]}
summary["answerable_top1_scores"] = [r["top1_score"] for r in rows]

out = {"note": "Scores the RAG team's MOCK retriever (6 Microsoft 10-Q chunks, keyword overlap). Harness validation, not RAG performance.",
       "summary": summary, "per_query": rows, "unanswerable": unans}
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "mock_retrieval_eval.json").write_text(json.dumps(out, indent=2))

for style in ("filing_terms", "paraphrase"):
    m = summary[style]
    print(f"{style:13s} hit@1 {m['hit@1']:.2f}  hit@5 {m['hit@5']:.2f}  MRR {m['mrr']:.2f} (CI {m['mrr_ci95'][0]:.2f}-{m['mrr_ci95'][1]:.2f})  nDCG@5 {m['ndcg@5']:.2f}")
print("unanswerable queries that still returned chunks:", summary["unanswerable"]["returned_results"], "/", len(unans),
      "top1 scores", [round(x, 3) for x in summary["unanswerable"]["top1_scores"]])
for r in rows:
    if r["hit@1"] == 0:
        print(f"  miss@1 {r['qid']} {r['style']:12s} top1={r['top1_chunk']} | {r['query']}")
