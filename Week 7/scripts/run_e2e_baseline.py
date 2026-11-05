"""First end-to-end number on the real filing: RAG BM25 -> naive table reader -> Eval graders.

    python scripts/run_e2e_baseline.py      -> results/e2e_baseline.json

There is no Agent v0 yet, so this is a deliberately simple, LLM-free reader that a real Agent must beat:
  1. retrieve top-5 chunks with RAG's BM25 (filters from the question),
  2. read every markdown table row, score its label against the question words,
  3. pick the column from the period words: 'nine months' -> 3rd numeric column, otherwise the 1st
     (income/cash-flow tables are [3M CY, 3M PY, 9M CY, 9M PY]; the balance sheet is [current, prior]).
It answers the 26 single-fact numeric questions (extraction + segment) and is graded with the NAA grader plus the Week-5 fact-index
diagnosis, whose taxonomy says *why* each wrong answer is wrong. The point is to exercise the full pipeline on real
retrieval output and give the Agent team a floor, not to be a good system. For every miss it also records whether the
gold figure was already in the top-5 text, which separates retrieval failures from reading (row/table selection) failures.
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))
from rag.retrieve import Retriever  # noqa: E402

from kpmg_eval.metrics.context import figure_in  # noqa: E402
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402
from kpmg_eval.metrics.numeric import naa_summary, score_numeric_diagnosed  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402

INDEX = ROOT / "upstream" / "rag_index_msft_lsa"
STOP = set("what was were is the a an of for in to and how much did microsoft microsoft's ended march 31 2026 2025 usd millions "
           "three nine months according its from on with as by give amount sign statement shown balance sheet portion".split())
NUM = re.compile(r"^\(?\s*\$?\s*-?[\d,]+(\.\d+)?\s*\)?$")


def parse_num(cell: str) -> float | None:
    c = cell.strip().replace("$", "").replace(" ", "")
    if not NUM.match(c) or not re.search(r"\d", c):
        return None
    neg = c.startswith("(")
    v = float(c.strip("()").replace(",", ""))
    return -v if neg else v


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}


def read(question: str, chunks: list[dict]) -> tuple[float | None, str]:
    qw = words(question)
    best = (0.0, None, "")
    for rank, c in enumerate(chunks):
        for line in c["text"].splitlines():
            if not line.startswith("|"):
                continue
            cells = [x.strip() for x in line.strip("|").split("|")]
            label, nums = cells[0], [n for n in (parse_num(x) for x in cells[1:]) if n is not None]
            if not nums or not label:
                continue
            lw = words(label)
            if not lw:
                continue
            overlap = len(lw & qw) / len(lw)
            score = overlap + 0.05 * len(lw & qw) - 0.01 * rank
            if score > best[0]:
                nine = "nine months" in question.lower()
                col = 2 if (nine and len(nums) >= 4) else 0
                best = (score, nums[col] if col < len(nums) else nums[0], label)
    return best[1], best[2]


def main():
    bench = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v1.jsonl")]
    retr = Retriever(INDEX, log_dir=None)
    items = [q for q in bench if q["corpus"] == "msft_10q_q3fy26" and q["type"] in ("extraction", "segment")
             and q["gold"] and q["answer"]["unit"] in ("USD", "USD/shares")]
    index = FactIndex.from_jsonl(ROOT / "data" / "msft_xbrl_facts.jsonl")
    results, detail = [], []
    for q in items:
        res = retr.search(q["question"], filters=q["filters"], top_k=5, method="bm25")["results"]
        v, label = read(q["question"], res)
        if v is None:
            block = {"answered": False, "value": None}
        else:
            unit = q["answer"]["unit"]
            scale = 1e6 if unit == "USD" else 1.0
            block = {"answered": True, "value": abs(v) * scale if "sign" not in q["question"] else v * scale,
                     "value_text": f"{abs(v):,.0f} million" if unit == "USD" else f"{v:.2f}", "unit": "USD"}
            if "sign" in q["question"]:
                block["value_text"] = f"{v:,.0f} million"
        r = score_numeric_diagnosed(q, block, index)
        results.append(r)
        # Where did it break? Was the gold figure already in the top-5 text (retrieval OK, reading failed)?
        gold_fig = q["answer"]["required_points"][0].lstrip("-")  # filing prints negatives as "( 84,669)"
        gold_ranks = [i for i, c in enumerate(res, 1) if figure_in(gold_fig, c["text"])]
        same_label_rows = sum(1 for c in res for line in c["text"].splitlines()
                              if line.startswith("|") and label and line.strip("|").split("|")[0].strip() == label)
        detail.append({"qid": q["qid"], "question": q["question"], "row_label_read": label, "value_read": v,
                       "gold": q["answer"]["display"], "label": r.label, "detail": r.detail,
                       "gold_figure_ranks_top5": gold_ranks, "rows_with_same_label_top5": same_label_rows})
    s = naa_summary(results)
    k = sum(r.passed for r in results)
    s["naa_ci95"] = [round(x, 3) for x in wilson(k, len(results))]
    s["errors"] = dict(Counter(r.label for r in results if not r.passed))
    miss = [d for d in detail if d["label"] != "correct"]
    s["misses_where_breakdown"] = {
        "n_misses": len(miss),
        "gold_in_top5_reading_failed": sum(1 for d in miss if d["gold_figure_ranks_top5"]),
        "gold_not_retrieved": sum(1 for d in miss if not d["gold_figure_ranks_top5"]),
        "correct_with_gold_in_top5": sum(1 for d in detail if d["label"] == "correct" and d["gold_figure_ranks_top5"]),
    }
    out = {"system": "RAG BM25 top-5 + naive table reader (no LLM)", "n": len(results), "summary": s, "detail": detail}
    (ROOT / "results" / "e2e_baseline.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(s, indent=1))
    for d in detail:
        if d["label"] != "correct":
            print(f"  {d['qid']:14s} {d['label']:14s} read '{d['row_label_read']}' = {d['value_read']}  gold {d['gold']}  {d['detail']}")


if __name__ == "__main__":
    main()
