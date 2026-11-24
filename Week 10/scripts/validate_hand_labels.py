"""Week 10: both narrative judges against RAG's blind hand labels (received 11/24; labelled 11/17 by two RAG members).

    python scripts/validate_hand_labels.py
        private/rag_hand_labels_1117.csv                       qid, run (rag_final_v1 | rag_final_v2), point, human_verdict
        ../Week 9/results/narrative_judge_w9_per_point.csv     Eval's judge (Claude)
        ../Week 9/results/rag_judge_gpt6sol/*.json             RAG's run of the Week 8 judge script (gpt-6-sol)
        -> results/judge_vs_hand_labels.json

rag_final_v2 is matched to the run we scored as narr_long (the variant RAG froze as final_v2).
Agreement and Cohen's kappa are per required point, over stated / missing / contradicted.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W9 = ROOT.parent / "Week 9" / "results"
RUN = {"rag_final_v1": "final_v1", "rag_final_v2": "narr_long"}
CATS = ("stated", "missing", "contradicted")


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in CATS)
    return {"points": n, "agree": sum(a == b for a, b in pairs), "agreement": round(po, 3), "kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0,
            "human/judge": dict(Counter(f"{a}/{b}" for a, b in pairs))}


def main():
    human = {(RUN[r["run"]], r["qid"], int(r["point"])): r["human_verdict"].strip().lower() for r in csv.DictReader(open(ROOT / "private" / "rag_hand_labels_1117.csv"))}
    claude = {(r["run"], r["qid"], int(r["point"])): r["judge_verdict"] for r in csv.DictReader(open(W9 / "narrative_judge_w9_per_point.csv"))}
    gpt = {}
    for run in ("final_v1", "narr_long"):
        for q in json.load(open(W9 / "rag_judge_gpt6sol" / f"{run}.json"))["questions"]:
            for i, v in enumerate(q["verdicts"], 1):
                gpt[(run, q["qid"], i)] = v
    out = {"_doc": __doc__.strip().split("\n")[0], "labels": {"points": len(human), "questions": len({k[1] for k in human}),
                                                             "by_run": dict(Counter(k[0] for k in human)), "verdicts": dict(Counter(human.values()))},
           "raters": "two RAG members, blind to the judges (as described by RAG); Eval has not labelled these points itself"}
    for name, judge in (("claude", claude), ("gpt6sol", gpt)):
        out[name] = {"missing_from_judge": sorted(f"{k[1]}#{k[2]} {k[0]}" for k in human if k not in judge)}
        for run in ("final_v1", "narr_long"):
            ks = [k for k in human if k[0] == run and k in judge]
            out[name][run] = kappa([(human[k], judge[k]) for k in ks])
            out[name][run]["disagreements"] = [{"qid": k[1], "point": k[2], "human": human[k], "judge": judge[k]} for k in sorted(ks) if human[k] != judge[k]]
            qs = sorted({k[1] for k in ks})
            allp = lambda src, q: all(v == "stated" for k, v in src.items() if k[0] == run and k[1] == q and k in human)  # noqa: E731
            out[name][run]["questions"] = len(qs)
            out[name][run]["pass_by_human"] = sum(allp(human, q) for q in qs)
            out[name][run]["pass_by_judge"] = sum(allp(judge, q) for q in qs)
            out[name][run]["pass_verdict_differs"] = [q for q in qs if allp(human, q) != allp(judge, q)]
        ks = [k for k in human if k in judge]
        out[name]["both_runs"] = kappa([(human[k], judge[k]) for k in ks])
    # Eval's Week 9 pass counts with the human verdict used wherever one exists
    pq = list(csv.DictReader(open(W9 / "narrative_judge_w9_per_question.csv")))
    out["eval_pass_counts_with_hand_labels_applied"] = {}
    for run in ("final_v1", "narr_long"):
        rs = [r for r in pq if r["run"] == run]
        def ok(r, use_human):
            v = [claude[(run, r["qid"], i)] for i in range(1, int(r["n_points"]) + 1)]
            if use_human:
                v = [human.get((run, r["qid"], i), x) for i, x in enumerate(v, 1)]
            return all(x == "stated" for x in v)
        for scope, sub in (("all_38", rs), ("narrative_27", [r for r in rs if r["group"] == "narrative"])):
            out["eval_pass_counts_with_hand_labels_applied"][f"{run}_{scope}"] = {
                "judge_only": sum(ok(r, False) for r in sub), "with_hand_labels": sum(ok(r, True) for r in sub), "of": len(sub),
                "questions_with_hand_labels": sum(any((run, r["qid"], i) in human for i in range(1, 9)) for r in sub),
                "changed": sorted(r["qid"] for r in sub if ok(r, False) != ok(r, True))}
    (ROOT / "results" / "judge_vs_hand_labels.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["eval_pass_counts_with_hand_labels_applied"], indent=0))
    print(json.dumps(out["labels"]))
    for name in ("claude", "gpt6sol"):
        print(name, "missing", out[name]["missing_from_judge"])
        for run in ("final_v1", "narr_long", "both_runs"):
            x = out[name][run]
            print(" ", run, x["agree"], "/", x["points"], x["agreement"], "kappa", x["kappa"], x["human/judge"],
                  x.get("disagreements"), "pass human/judge", x.get("pass_by_human"), x.get("pass_by_judge"), x.get("pass_verdict_differs"))


if __name__ == "__main__":
    main()
