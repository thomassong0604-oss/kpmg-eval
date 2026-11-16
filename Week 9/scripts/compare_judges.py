"""Week 9: two judges on the same answers. RAG ran Week 8's run_narrative_judge.py with gpt-6-sol (11/16); Eval's judge
is Claude (score_rag_judge_runs.py). Agreement point by point, plus RAG's three runs side by side.

    python scripts/compare_judges.py -> results/judge_agreement_w9.json; private/labels_final_v1_priority.csv
"""
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES, PRIV = ROOT / "results", ROOT / "private"
G = {n: {q["qid"]: q for q in json.load(open(RES / "rag_judge_gpt6sol" / f"{n}.json"))["questions"]}
     for n in ("final_v1", "final_v1_rerun", "narr_union", "narr_long")}
mine = {}
for r in csv.DictReader(open(RES / "narrative_judge_w9_per_point.csv")):
    mine[(r["run"], r["qid"], int(r["point"]))] = r["judge_verdict"]
out = {"_doc": __doc__.strip().split("\n")[0], "judges": {"rag_run": "gpt-6-sol, Week 8 script unchanged, default temperature", "eval": "Claude (Fable 5.2), session 11/16"}}
out["gpt6sol_rerun_identical"] = all(G["final_v1"][q]["verdicts"] == G["final_v1_rerun"][q]["verdicts"] for q in G["final_v1"])
dis = {}
for run in ("final_v1", "narr_union"):
    pairs, d = [], []
    for qid, q in G[run].items():
        for i, v in enumerate(q["verdicts"], 1):
            m = mine.get((run, qid, i))
            if m:
                pairs.append((v, m))
                if v != m:
                    d.append({"qid": qid, "point": i, "gpt6sol": v, "claude": m})
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in ("stated", "missing", "contradicted"))
    qs = sorted({q for q in G[run] if (run, q, 1) in mine})
    both = lambda q: all(mine[(run, q, i)] == "stated" for i in range(1, len(G[run][q]["verdicts"]) + 1))  # noqa: E731
    out[run] = {"questions_in_both": len(qs), "points": n, "agree": sum(a == b for a, b in pairs), "agreement": round(po, 3),
                "kappa": round((po - pe) / (1 - pe), 3), "passed_gpt6sol": sum(G[run][q]["passed"] for q in qs),
                "passed_claude": sum(both(q) for q in qs), "disagreements": d}
    dis[run] = {(x["qid"], x["point"]) for x in d}
f1, lg, un = G["final_v1"], G["narr_long"], G["narr_union"]
out["rag_runs_gpt6sol"] = {n: {"passed": sum(q["passed"] for q in g.values()), "of": 30, "points_stated": sum(q["verdicts"].count("stated") for q in g.values()),
                               "points": sum(len(q["verdicts"]) for q in g.values()), "contradicted": sum(q["contradicted"] for q in g.values()),
                               "unsupported_claims": sum(q["unsupported_claims"] for q in g.values())} for n, g in (("final_v1", f1), ("narr_union", un), ("narr_long", lg))}
for n, g in (("narr_union", un), ("narr_long", lg)):
    out["rag_runs_gpt6sol"][n]["vs_final_v1"] = {"gained": sorted(q for q in f1 if not f1[q]["passed"] and g[q]["passed"]),
                                                 "lost": sorted(q for q in f1 if f1[q]["passed"] and not g[q]["passed"])}
(RES / "judge_agreement_w9.json").write_text(json.dumps(out, indent=1))
rows = list(csv.DictReader(open(PRIV / "59b1c809-narrative_labels_rag_final_v1_blank.csv")))
with open(PRIV / "labels_final_v1_priority.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["qid", "point", "required_point", "answer_text", "human_verdict", "judges_disagree"])
    for r in rows:
        w.writerow([r["qid"], r["point"], r["required_point"], r["answer_text"], "", "yes" if (r["qid"], int(r["point"])) in dis["final_v1"] else ""])
print(json.dumps({k: v for k, v in out.items() if k != "_doc"}, indent=1))
