"""Gold Set v2.1: Gold Set v2 with corrected text anchors (questions and expected answers unchanged).

    python scripts/build_gold_v2_1.py   -> data/benchmark_v2_1.jsonl, results/gold_v2_1_changes.json

Why: RAG's round-1 retrieval run (11/9) found that GSv0-MSFT-019/021/027/029 carry anchors that do not match their
questions. All four came from RAG v0's automatic "region" conversion, and so do 18 more (22 in all: 20 narrative,
2 numeric reconciliations). Eval re-anchored all 22 on the sentence or figure that supports each required point, exactly
as the Microsoft Q3 FY2026 10-Q prints it (data/anchor_review_w8.json; every string checked against the filing text and
RAG's chunker output). Three of the seven questions RAG found without anchors get figure anchors from the SEC-rendered
income statements; the other four wait for RAG's round-1 chunks.

benchmark_v2.jsonl (sha256 ed4b42db6fc25ee5) is kept unchanged, because RAG's round-1 run used it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("\xa0", " ")).lower()


def main():
    review = json.loads((DATA / "anchor_review_w8.json").read_text())
    gold = [json.loads(l) for l in (DATA / "benchmark_v2.jsonl").read_text().splitlines() if l.strip()]
    acc = review["accession"]
    changes = []
    out = []
    for q in gold:
        q2 = copy.deepcopy(q)
        if q["qid"] in review["anchors"]:
            assert any(e.get("anchor_source") == "region" for e in q["rag_evidence"]), q["qid"]
            q2["rag_evidence"] = [{"region": "eval_w8_review", "ticker": "MSFT", "form": "10-Q", "accession": acc,
                                   "contains": review["anchors"][q["qid"]], "anchor_source": "eval_w8_review"}]
        elif q["qid"] in review["sec_page_anchors"]:
            assert not q["rag_evidence"], q["qid"]
            a = review["sec_page_anchors"][q["qid"]]
            q2["rag_evidence"] = [{"region": "income_statement", "ticker": a["ticker"], "form": a["form"],
                                   "accession": a["accession"], "contains": a["contains"],
                                   "anchor_source": "sec_r_page_pending_round1_chunks"}]
        if q2["rag_evidence"] != q["rag_evidence"]:
            changes.append({"qid": q["qid"], "question": q["question"],
                            "old": [c for e in q["rag_evidence"] for c in e["contains"]],
                            "new": [c for e in q2["rag_evidence"] for c in e["contains"]]})
        out.append(q2)
    # every re-anchored Microsoft string must be printed in the filing (Data's copy) and in RAG's chunker output
    filing = ROOT / "upstream/data_engineering_kpmg/data/raw/sec" / acc / "msft-20260331.htm"
    chunks = [json.loads(l) for l in (DATA / "rag_chunks_msft_10q.jsonl").read_text().splitlines()]
    blob = norm(" ".join(c["text"] for c in chunks))
    missing = [(qid, a) for qid, al in review["anchors"].items() for a in al if norm(a) not in blob]
    assert not missing, missing
    if filing.exists():
        import warnings
        from bs4 import BeautifulSoup
        warnings.filterwarnings("ignore")
        ftext = norm(BeautifulSoup(filing.read_text(encoding="utf-8", errors="ignore"), "lxml").get_text(" "))
        missing = [(qid, a) for qid, al in review["anchors"].items() for a in al if norm(a) not in ftext]
        assert not missing, missing
    text = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in out)
    (DATA / "benchmark_v2_1.jsonl").write_text(text)
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    summary = {"gold_set": "v2.1", "sha256_16": h, "based_on": "benchmark_v2.jsonl (ed4b42db6fc25ee5)",
               "questions": len(out), "questions_changed": len(changes),
               "reanchored_from_region": sum(c["qid"] in review["anchors"] for c in changes),
               "anchored_from_sec_pages": sum(c["qid"] in review["sec_page_anchors"] for c in changes),
               "still_without_anchors": {k: v for k, v in review["pending_round1_chunks"].items()},
               "row_labels_for_rag_anchor_fixes": {k: v for k, v in review["row_labels"].items() if k != "_doc"},
               "filing_checked": str(filing.relative_to(ROOT)) if filing.exists() else None,
               "changes": changes}
    RES.mkdir(exist_ok=True)
    (RES / "gold_v2_1_changes.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"[gold v2.1] {len(out)} questions, {len(changes)} re-anchored, hash {h}")


if __name__ == "__main__":
    main()
