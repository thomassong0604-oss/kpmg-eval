"""Week 9: score AnswerBlocks on Eval's two extra suites (RAG's request of 11/16: sets D and E of its pre-registration).

    # D: messy wording, 427 rewrites of the gold questions (same answers). One AnswerBlock per rewrite, keyed "vid".
    python scripts/grade_suite_answers.py --suite messy --answers private/<file>.jsonl --tag rag_final_v1 \
        [--clean "../Week 8/results/answers_<clean run>_per_question.csv"] [--chunks <chunks.jsonl>]
    # E: abstention, 56 items (51 that must be declined, 5 false premises that must be answered). Keyed "sid".
    python scripts/grade_suite_answers.py --suite abstention --answers private/<file>.jsonl --tag rag_final_v1 [--clean ...]
        -> results/suite_<suite>_<tag>.json, results/suite_<suite>_<tag>_per_item.csv   (labels and ids, no answer text)

grade_answer_blocks.py (Week 8) scores the 155 gold questions by qid, so it cannot read these files as they are: a
rewrite has its own id and the abstention items have no gold record. This script maps each rewrite to its clean
question's Gold Set v2.2 record and scores it with the same graders, by perturbation. With --clean it pairs each rewrite
with the same system's result on the clean question (both right / only clean / only messy / neither, exact McNemar).
A narrative rewrite is not scored here (needs the judge); it counts only towards the refusal rate.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8 = ROOT.parent / "Week 8"
sys.path[:0] = [str(W8), str(W8 / "scripts")]
import grade_answer_blocks as gab  # noqa: E402
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402
from kpmg_eval.metrics.refusal import classify_response  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402

RES = ROOT / "results"


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": round(k / n, 3) if n else None, "ci95": [round(x, 3) for x in wilson(k, n)] if n else None}


def mcnemar_exact(b: int, c: int) -> float | None:
    """Two-sided exact test on the discordant pairs (b: only clean right, c: only messy right)."""
    n = b + c
    if not n:
        return None
    return round(min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n), 4)


def load_answers(path: str, key: str) -> dict:
    out = {}
    for line in open(path):
        if line.strip():
            b = json.loads(line)
            out[b.get(key) or b.get("qid") or str(b.get("trace_id", "")).rsplit(":", 1)[-1]] = b
    return out


def clean_results(path: str | None) -> dict:
    return {r["qid"]: r for r in csv.DictReader(open(path))} if path else {}


def messy(a) -> tuple[dict, list[dict]]:
    gold = {q["qid"]: q for q in map(json.loads, open(W8 / "data" / "benchmark_v2_2.jsonl"))}
    variants = [json.loads(l) for l in open(W8 / "data" / "messy_wording_v1.jsonl")]
    answers = load_answers(a.answers, "vid")
    chunks = None
    if a.chunks:
        chunks = {c["chunk_id"]: {"accession": c["accession"], "text": c["text"]} for c in map(json.loads, open(a.chunks))}
    gold_v = {v["vid"]: {**gold[v["qid"]], "qid": v["vid"]} for v in variants}
    _, rows = gab.grade(gold_v, answers, FactIndex.from_jsonl(W8 / "data" / "msft_xbrl_facts.jsonl"), chunks)
    clean = clean_results(a.clean)
    pert = {v["vid"]: v for v in variants}
    for r in rows:
        v = pert[r["qid"]]
        r.update(vid=r["qid"], qid=v["qid"], perturbation=v["perturbation"])
        c = clean.get(v["qid"])
        r["clean_passed"] = (c["passed"] == "True") if c and c.get("passed") in ("True", "False") else None

    def block(rs):
        sc = [r for r in rs if r.get("has_answer") and r.get("passed") in (True, False)]   # numeric, categorical, premise, refusal
        num = [r for r in rs if r.get("has_answer") and r.get("scored_as") == "numeric"]
        ansb = [r for r in rs if r["answerable"] and r.get("has_answer")]
        out = {"rewrites": len(rs), "answered_file_has": sum(r.get("has_answer", False) for r in rs),
               "right_of_scored": rate(sum(r["passed"] for r in sc), len(sc)),
               "numeric_accuracy": rate(sum(r["passed"] for r in num), len(num)),
               "numeric_labels": dict(Counter(r["label"] for r in num if not r["passed"])),
               "answerable_declined": rate(sum(r.get("response") == "refused" for r in ansb), len(ansb)),
               "unanswerable_declined": rate(sum(r["passed"] for r in rs if r.get("has_answer") and r.get("scored_as") == "refusal"),
                                             sum(bool(r.get("has_answer")) and r.get("scored_as") == "refusal" for r in rs))}
        pairs = [(r["clean_passed"], r["passed"]) for r in sc if r["clean_passed"] is not None]
        if pairs:
            b, c = sum(x and not y for x, y in pairs), sum(y and not x for x, y in pairs)
            out["paired_with_clean"] = {"pairs": len(pairs), "both_right": sum(x and y for x, y in pairs), "only_clean_right": b,
                                        "only_messy_right": c, "neither": sum(not x and not y for x, y in pairs),
                                        "mcnemar_exact_p": mcnemar_exact(b, c)}
        return out

    summ = {"suite": "messy_wording_v1", "gold": "benchmark_v2_2.jsonl", "answers_file": Path(a.answers).name,
            "missing_rewrites": sum(not r.get("has_answer") for r in rows), "all": block(rows),
            "by_perturbation": {p: block([r for r in rows if r["perturbation"] == p]) for p in ("typo_company", "typo_terms", "casual")},
            "note": "typo_company only tests the system if the company is NOT also passed as a filter; say which was done"}
    return summ, rows


def abstention(a) -> tuple[dict, list[dict]]:
    items = [json.loads(l) for l in open(W8 / "data" / "abstention_suite_v1.jsonl")]
    answers = load_answers(a.answers, "sid")
    clean = clean_results(a.clean)
    rows = []
    for it in items:
        b = answers.get(it["sid"])
        resp = classify_response(b) if b else None
        ok = None if b is None else (resp == "refused") if not it["answerable"] else (resp != "refused")
        c = clean.get(it.get("twin_of") or "")
        rows.append({"sid": it["sid"], "kind": it["kind"], "answerable": it["answerable"], "twin_of": it.get("twin_of") or "",
                     "has_answer": b is not None, "response": resp or "", "passed": ok,
                     "label": "no_answer" if b is None else ("correct_refusal" if ok else "answered_unanswerable") if not it["answerable"]
                     else ("answered" if ok else "declined_answerable"),
                     "twin_clean_passed": (c["passed"] == "True") if c and c.get("passed") in ("True", "False") else None})
    un = [r for r in rows if not r["answerable"] and r["has_answer"]]
    an = [r for r in rows if r["answerable"] and r["has_answer"]]
    tw = [r for r in un if r["twin_clean_passed"] is not None]
    summ = {"suite": "abstention_suite_v1", "answers_file": Path(a.answers).name, "missing_items": sum(not r["has_answer"] for r in rows),
            "must_decline": rate(sum(r["passed"] for r in un), len(un)),
            "must_decline_by_kind": {k: rate(sum(r["passed"] for r in un if r["kind"] == k), sum(r["kind"] == k for r in un))
                                     for k in sorted({r["kind"] for r in un})},
            "invented_answers": [r["sid"] for r in un if not r["passed"]],
            "false_premise_answered": rate(sum(r["passed"] for r in an), len(an)),
            "false_premise_note": "answered is counted here; whether the premise was corrected needs the expected text and a reader",
            "twin_pairs": {"pairs": len(tw), "answers_the_real_question_and_declines_its_twin": sum(r["twin_clean_passed"] and r["passed"] for r in tw),
                           "note": "needs --clean: the same system's per-question results on the gold questions"} if tw else None}
    return summ, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["messy", "abstention"], required=True)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--clean", help="per-question csv of the same system on the clean gold questions (from grade_answer_blocks.py)")
    ap.add_argument("--chunks")
    ap.add_argument("--tag", default="external")
    a = ap.parse_args()
    summ, rows = (messy if a.suite == "messy" else abstention)(a)
    RES.mkdir(exist_ok=True)
    (RES / f"suite_{a.suite}_{a.tag}.json").write_text(json.dumps(summ, indent=1))
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(RES / f"suite_{a.suite}_{a.tag}_per_item.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({k: v for k, v in summ.items() if k not in ("by_perturbation",)}, indent=1)[:1500])


if __name__ == "__main__":
    main()
