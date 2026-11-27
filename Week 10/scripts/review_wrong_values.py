"""Week 10: what the wrong-value answers on the objective sets have in common (post-hoc, after the runs; not a pre-registered score).

    python scripts/review_wrong_values.py -> results/xbrl_wrong_value_review.json

For every answer the grader labelled wrong_value or too_imprecise on Sets B and C2 it records whether the gold cell is a
"attributable to the company" line (parent only) while the question says only "net income" or "total shareholders' equity",
and how far the answer is from the gold value. No question or answer text is written.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
X = ROOT / "private" / "xbrl"
SETS = {"B": ("set_A.jsonl", "xbrl_B_return", "B"), "C2": ("set_C2.jsonl", "xbrl_C2_return", "C2")}
PARENT = re.compile(r"attributable|\b(inc|corp|corporation|company|co)\b\.?.*(stockholders|shareholders)", re.I)


def said(block):
    m = re.search(r"(-?)\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion)?", (block.get("value_text") or "").replace("USD", ""))
    if not m:
        return None
    return float(m.group(2).replace(",", "")) * {"thousand": 1e3, "million": 1e6, "billion": 1e9, None: 1.0}[m.group(3)] * (-1 if m.group(1) else 1)


def main():
    out = {"_doc": __doc__.strip().split("\n")[0], "status": "post-hoc description; the official scores are the strict ones", "sets": {}}
    for name, (qf, ret, pre) in SETS.items():
        items = {q["qid"]: q for q in map(json.loads, open(X / "out" / qf))}
        parent_qs = [q for q in items.values() if q["metric_key"] in ("net_income", "shareholders_equity") and PARENT.search(q["gold_cell"].get("row_heading") or "")]
        res = {"questions": len(items), "net_income_or_equity_questions_whose_gold_cell_is_parent_only": len(parent_qs), "configs": {}}
        for cfg in ("gold", "precheck"):
            blocks = {b["qid"]: b for b in map(json.loads, open(X / "returns" / ret / f"xbrl_{pre}_{cfg}_answer_blocks.jsonl"))}
            rows = [r for r in csv.DictReader(open(ROOT / "results" / f"xbrl_{name}_final_v1_per_question.csv")) if r["config"] == cfg]
            bad = [r for r in rows if r["label"] in ("wrong_value", "too_imprecise")]
            detail = []
            for r in bad:
                q, v = items[r["qid"]], said(blocks[r["qid"]])
                g = float(q["answer"]["value"])
                parent = q in parent_qs
                detail.append({"qid": r["qid"], "metric": r["metric"], "label": r["label"], "gold_cell_is_parent_only_line": parent,
                               "relative_difference": round(abs(v - g) / abs(g), 4) if v is not None else None,
                               "kind": "consolidated figure given where the gold cell is the parent-only line" if parent and r["label"] == "wrong_value"
                                       else "rounded figure" if r["label"] == "too_imprecise" else "other"})
            strict = sum(r["passed"] == "True" for r in rows)
            cons = sum(d["kind"].startswith("consolidated") for d in detail)
            res["configs"][cfg] = {"strict_right": strict, "wrong_value_or_imprecise": len(bad), "by_kind": dict(Counter(d["kind"] for d in detail)),
                                   "parent_only_questions_answered_with_the_consolidated_figure": f"{cons}/{len(parent_qs)}",
                                   "right_if_the_consolidated_figure_were_accepted": strict + cons,
                                   "right_if_also_ignoring_sign_on_cash_outflow": strict + cons + sum(r["label"] == "wrong_sign" and r["cash_outflow"] == "True" for r in rows),
                                   "detail": detail}
        out["sets"][name] = res
    (ROOT / "results" / "xbrl_wrong_value_review.json").write_text(json.dumps(out, indent=1))
    for n, r in out["sets"].items():
        for c, x in r["configs"].items():
            print(n, c, {k: v for k, v in x.items() if k != "detail"}, [(d["qid"], d["kind"][:12], d["relative_difference"]) for d in x["detail"]])


if __name__ == "__main__":
    main()
