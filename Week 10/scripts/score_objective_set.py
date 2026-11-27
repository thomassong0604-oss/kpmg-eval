"""Week 10: official score of an XBRL objective set run (RAG final_v1; one run per pre-registered filter configuration).

    python scripts/score_objective_set.py --set B --returns private/xbrl/returns/xbrl_B_return
    python scripts/score_objective_set.py --set C --name C2 --returns private/xbrl/returns/xbrl_C2_return
        <returns>/xbrl_<SET>_<config>_answer_blocks.jsonl, _per_question.csv   for config in gold, precheck (as returned by RAG)
        private/xbrl/out/set_A.jsonl     Set A's questions (Set B is the same 150 questions on index_full); hash checked
        -> results/xbrl_<SET>_final_v1.json, results/xbrl_<SET>_final_v1_per_question.csv   (labels and strata; no question or answer text)

Scoring rules were fixed on 11/25 before any answer existed (results/xbrl_set_A_manifest.json): Eval's grader unchanged, an exact
answer may drop zeros printed after the decimal point, strict sign is primary, and a second labelled score ignores the sign on
the cash-outflow questions only.
"""
import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(Path(__file__).resolve().parent)]
import check_objective_sets as cos  # noqa: E402
rate, mcnemar = cos.gsa.rate, cos.gsa.mcnemar_exact
CONFIGS = ("gold", "precheck")


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 1)


def score_config(items, ret, S, cfg):
    blocks = {b["qid"]: b for b in map(json.loads, open(ret / f"xbrl_{S}_{cfg}_answer_blocks.jsonl"))}
    log = {r["qid"]: r for r in csv.DictReader(open(ret / f"xbrl_{S}_{cfg}_per_question.csv"))}
    assert set(blocks) == set(log) == {q["qid"] for q in items}, "answers do not cover the set exactly"
    gold = {q["qid"]: q for q in items}
    rows = {r["qid"]: r for r in cos.grade_objective(items, blocks)}
    out = []
    for q in items:
        r, b, lg = rows[q["qid"]], blocks[q["qid"]], log[q["qid"]]
        outflow = q["metric_key"] in cos.OUTFLOW
        cited = {c.get("accession") for c in b.get("citations") or []}
        out.append({"qid": q["qid"], "config": cfg, "ticker": q["tickers"][0], "metric": q["metric_key"], "statement": q["strata"]["statement"],
                    "relation": q["strata"]["relation"], "form": q["filters"]["form"], "unit": q["answer_unit"], "cash_outflow": outflow,
                    "response": r["response"], "passed": bool(r["passed"]), "label": r["label"],
                    "passed_sign_insensitive_on_outflow": bool(r["passed"]) or (outflow and r["label"] == "wrong_sign"),
                    "n_citations": len(b.get("citations") or []),
                    "cites_gold_filing": (q["facts"][0]["accession"] in cited) if b.get("answered") and cited else None,
                    "rag_own_label": lg["label"], "rag_own_passed": lg["passed"], "rag_error_source": lg.get("error_source", ""),
                    "rag_retrieved_all_figures": lg.get("retrieved_all_figures", ""), "precheck_status": lg.get("precheck_status", ""),
                    "api_call": lg["reader_prompt_tokens"] not in ("", "0"),
                    "retrieval_ms": float(lg["retrieval_ms"] or 0), "reader_ms": float(lg["reader_latency_ms"] or 0),
                    "prompt_tokens": int(float(lg["reader_prompt_tokens"] or 0)), "completion_tokens": int(float(lg["reader_completion_tokens"] or 0)),
                    "cost_usd": float(lg["cost_usd"] or 0)})
    return out


def summarise(rs):
    acc = lambda sub: rate(sum(r["passed"] for r in sub), len(sub))  # noqa: E731
    by = lambda k: {v: acc([r for r in rs if r[k] == v]) for v in sorted({r[k] for r in rs})}  # noqa: E731
    ans = [r for r in rs if r["response"] == "answered"]
    cg = [r for r in ans if r["cites_gold_filing"] is not None]
    wrongf = [r for r in cg if not r["cites_gold_filing"]]
    calls = [r for r in rs if r["api_call"]]
    out_q = [r for r in rs if r["cash_outflow"]]
    return {"numeric_accuracy_strict": acc(rs), "labels": dict(Counter(r["label"] for r in rs)),
            "numeric_accuracy_sign_insensitive_on_cash_outflow": rate(sum(r["passed_sign_insensitive_on_outflow"] for r in rs), len(rs)),
            "cash_outflow_questions": {"n": len(out_q), "right": sum(r["passed"] for r in out_q), "wrong_sign": sum(r["label"] == "wrong_sign" for r in out_q),
                                       "other_misses": sum(not r["passed"] and r["label"] != "wrong_sign" for r in out_q)},
            "wrong_sign_on_other_questions": sum(r["label"] == "wrong_sign" and not r["cash_outflow"] for r in rs),
            "trailing_zero_rule_applied": sum(r["label"] == "correct_trailing_zero_dropped" for r in rs),
            "answered": rate(len(ans), len(rs)), "accuracy_when_answered": acc(ans),
            "wrong_answers_given": sum(not r["passed"] for r in ans), "declined": sum(r["response"] != "answered" for r in rs),
            "by_company": by("ticker"), "by_statement": by("statement"), "by_relation": by("relation"), "by_form": by("form"), "by_unit": by("unit"), "by_metric": by("metric"),
            "citations": {"answers_citing_the_gold_filing": rate(sum(bool(r["cites_gold_filing"]) for r in cg), len(cg)),
                          "answers_citing_only_other_filings": {"n": len(wrongf), "right": sum(r["passed"] for r in wrongf)}},
            "misses_by_rags_error_source": dict(Counter(r["rag_error_source"] or "none recorded" for r in rs if not r["passed"])),
            "differs_from_rags_own_grader": sorted(r["qid"] for r in rs if r["rag_own_passed"] in ("True", "False") and (r["rag_own_passed"] == "True") != r["passed"]),
            "cost_and_latency": {"api_calls": len(calls), "prompt_tokens": sum(r["prompt_tokens"] for r in rs), "completion_tokens": sum(r["completion_tokens"] for r in rs),
                                 "cost_usd_total": round(sum(r["cost_usd"] for r in rs), 3), "cost_usd_per_question": round(sum(r["cost_usd"] for r in rs) / len(rs), 5),
                                 "retrieval_ms": {"median": round(statistics.median(r["retrieval_ms"] for r in calls), 1), "p95": pct([r["retrieval_ms"] for r in calls], 0.95)},
                                 "reader_ms": {"median": round(statistics.median(r["reader_ms"] for r in calls), 1), "p95": pct([r["reader_ms"] for r in calls], 0.95)},
                                 "method": "RAG's log; percentiles over questions that made an API call, nearest rank"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["A", "B", "C"])
    ap.add_argument("--returns", required=True)
    ap.add_argument("--index", default="")
    ap.add_argument("--questions", default=None)
    ap.add_argument("--name", default=None, help="prefix of the returned files and of the outputs, if not the set letter (C2 for the redrawn Set C)")
    a = ap.parse_args()
    S, ret = a.set, Path(a.returns)
    N = a.name or S
    qfile = Path(a.questions) if a.questions else cos.X / "out" / ("set_C2.jsonl" if S == "C" else "set_A.jsonl")
    man = json.load(open(ROOT / "results" / ("xbrl_set_C2_manifest.json" if S == "C" else "xbrl_set_A_manifest.json")))
    sha = hashlib.sha256(qfile.read_bytes()).hexdigest()
    assert sha == man["sha256"], "the question file does not match the published hash"
    items = [json.loads(l) for l in open(qfile)]
    rows = {cfg: score_config(items, ret, N, cfg) for cfg in CONFIGS}
    out = {"_doc": __doc__.strip().split("\n")[0], "set": N, "questions": len(items), "question_file_sha256": sha, "system": "RAG final_v1", "index": a.index,
           "scoring_rules": man["scoring_rules_fixed_before_the_run"],
           "returned_files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ret.glob("*")) if p.suffix in (".jsonl", ".csv", ".json")},
           "configs": {cfg: summarise(rows[cfg]) for cfg in CONFIGS}}
    g, p = ({r["qid"]: r for r in rows[c]} for c in CONFIGS)
    b = sum(g[q]["passed"] and not p[q]["passed"] for q in g)
    c = sum(p[q]["passed"] and not g[q]["passed"] for q in g)
    out["gold_vs_precheck_filters"] = {"both_right": sum(g[q]["passed"] and p[q]["passed"] for q in g), "only_gold_filters_right": b, "only_precheck_right": c,
                                       "neither": sum(not g[q]["passed"] and not p[q]["passed"] for q in g), "mcnemar_exact_p": mcnemar(b, c),
                                       "lost_with_precheck_by_label": dict(Counter(p[q]["label"] for q in g if g[q]["passed"] and not p[q]["passed"])),
                                       "lost_with_precheck_by_precheck_status": dict(Counter(p[q]["precheck_status"] or "none" for q in g if g[q]["passed"] and not p[q]["passed"]))}
    (ROOT / "results" / f"xbrl_{N}_final_v1.json").write_text(json.dumps(out, indent=1))
    allr = rows["gold"] + rows["precheck"]
    with open(ROOT / "results" / f"xbrl_{N}_final_v1_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allr[0]))
        w.writeheader()
        w.writerows(allr)
    for cfg in CONFIGS:
        x = out["configs"][cfg]
        print(cfg, json.dumps({k: x[k] for k in x if not k.startswith("by_")}))
        print("   ", {k: {a_: (v["k"], v["n"]) for a_, v in x[k].items()} for k in x if k.startswith("by_")})
    print(json.dumps(out["gold_vs_precheck_filters"]))


if __name__ == "__main__":
    main()
