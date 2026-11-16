"""Week 9: score RAG's two narrative runs (final_v1 and the narrative-union retrieval variant) on the same 38 questions.

    python scripts/score_rag_judge_runs.py
        private/judge_input_final_v1.jsonl, private/judge_input_narr_union.jsonl   RAG's files (11/16): answer + cited chunk text
        private/judge_verdicts_w9.py                                               the judge's verdicts with quotes
        -> results/narrative_judge_w9.json, results/narrative_judge_w9_per_point.csv   (verdicts and ids only, no text)
        -> private/judge_labels_w9_blank.csv                                       sheet for the human check

Required points come from Gold Set v2.2 (not from RAG's file; they differ on EV1R-005, where v2.2 also accepts 25%).
Coverage: per required point stated / missing / contradicted, same rubric and quote guard as Week 8's
run_narrative_judge.py (a "stated" verdict whose quote is not in the answer becomes missing).
Faithfulness, number level: every figure in the answer must appear in a cited chunk, or be listed in DERIVED below with
the chunk figures it is computed from (checked here by arithmetic). Sentence level: sentences whose content words are
mostly absent from the cited chunks are listed for reading.
Judge: Claude (Fable 5.2) in the working session on 11/16, not an API run; verdicts are fixed in the verdict file, so this
script is deterministic. Agreement with hand labels: --validate labels.csv (qid, run, point, human_verdict).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8 = ROOT.parent / "Week 8"
PRIV, RES = ROOT / "private", ROOT / "results"
RUNS = {"A": ("final_v1", "judge_input_final_v1.jsonl"), "B": ("narr_union", "judge_input_narr_union.jsonl")}
STOP = set("the a an of in to and or for from by on at as is was were are be it its that this with which their they not "
           "than more less also both while so did does had has have s microsoft company period periods".split())
NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?")


def norm(s: str) -> str:
    return " ".join(s.lower().replace("’", "'").replace("‘", "'").split())


def guard(verdicts, answer: str, n: int) -> list[str]:
    low, out = norm(answer), ["missing"] * n
    for i, (v, quote) in enumerate(verdicts[:n]):
        if v in ("stated", "contradicted"):
            out[i] = v if quote and norm(quote) in low else "missing"
    return out


def literal(point: str, answer: str) -> bool:
    """Baseline without a judge: one of the point's alternatives appears word for word (case and commas ignored)."""
    low = norm(answer).replace(",", "")
    return any(norm(alt).replace(",", "") in low for alt in point.split(" | "))


def figures(text: str) -> list[str]:
    return [m.group().lstrip("$").replace(",", "").rstrip(".") for m in NUM.finditer(text)]


def number_support(rec: dict, derived: dict) -> dict:
    chunk = " ".join(c["text"] for c in rec["cited_chunks"]).replace(",", "")
    in_q = set(figures(rec["question"]))
    out = {"n": 0, "in_chunk": 0, "derived_ok": 0, "unsupported": []}
    for f in dict.fromkeys(figures(rec["rag_answer"] or "")):
        if f in in_q or (f.isdigit() and 2000 <= int(f) <= 2030):       # dates and years the question itself gives
            continue
        out["n"] += 1
        if re.search(rf"(?<![\d.]){re.escape(f)}(?![\d]|\.\d)", chunk):
            out["in_chunk"] += 1
        elif f in derived and abs(derived[f]["value"] - float(f)) <= derived[f].get("tol", 0.051) \
                and all(re.search(rf"(?<![\d.]){re.escape(x)}(?![\d]|\.\d)", chunk) for x in derived[f]["from"]):
            out["derived_ok"] += 1
        else:
            out["unsupported"].append(f)
    return out


def thin_sentences(rec: dict) -> list[int]:
    chunk = set(re.findall(r"[a-z]+", " ".join(c["text"] for c in rec["cited_chunks"]).lower()))
    out = []
    for i, s in enumerate(re.split(r"(?<=[.;:])\s+", rec["rag_answer"] or ""), 1):
        w = [x for x in re.findall(r"[a-z]+", s.lower()) if x not in STOP and len(x) > 2]
        if len(w) >= 4 and sum(x in chunk for x in w) / len(w) < 0.5:
            out.append(i)
    return out


def rate(k, n):
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", help="CSV of hand labels: qid, run (final_v1 | narr_union), point, human_verdict")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("verdicts", PRIV / "judge_verdicts_w9.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    gold = {q["qid"]: q for q in map(json.loads, open(W8 / "data" / "benchmark_v2_2.jsonl"))}
    data = {r: {x["qid"]: x for x in map(json.loads, open(PRIV / f))} for r, (_, f) in RUNS.items()}
    rows, per_point, points_differ = [], [], []
    for qid, ra in data["A"].items():
        pts = gold[qid]["answer"]["required_points"]
        if pts != ra["required_points"]:
            points_differ.append(qid)
        for r, (name, _) in RUNS.items():
            rec = data[r][qid]
            raw = vd.V[qid][r] or vd.V[qid]["A"]
            assert len(raw) == len(pts), (qid, r)
            v = guard(raw, rec["rag_answer"] or "", len(pts))
            assert v == [x[0] for x in raw], f"quote not in answer: {qid} {r} {[(x, y) for x, y in zip(raw, v) if x[0] != y]}"
            ns = number_support(rec, getattr(vd, "DERIVED", {}).get(qid, {}).get(r, {}))
            lit = [literal(p, rec["rag_answer"] or "") for p in pts]
            rows.append({"qid": qid, "run": name, "group": rec["group"], "type": rec["type"], "ticker": "|".join(rec["tickers"]),
                         "rag_answered": rec["rag_answered"], "evidence_status": rec["evidence_status"],
                         "n_points": len(pts), "stated": v.count("stated"), "contradicted": v.count("contradicted"),
                         "point_recall": round(v.count("stated") / len(pts), 3),
                         "passed": v.count("stated") == len(pts), "verdicts": "|".join(x[0] for x in v),
                         "literal_stated": sum(lit), "figures": ns["n"], "figures_in_chunk": ns["in_chunk"],
                         "figures_derived_ok": ns["derived_ok"], "figures_unsupported": "|".join(ns["unsupported"]),
                         "thin_sentences": "|".join(map(str, thin_sentences(rec))),
                         "n_chunks": len(rec["cited_chunks"]), "borderline": qid in vd.BORDERLINE})
            per_point += [{"qid": qid, "run": name, "point": i, "judge_verdict": x, "literal_match": l}
                          for i, (x, l) in enumerate(zip(v, lit), 1)]

    def summ(rs):
        np_ = sum(r["n_points"] for r in rs)
        fig = sum(r["figures"] for r in rs)
        return {"questions": len(rs), "passed": rate(sum(r["passed"] for r in rs), len(rs)),
                "points_stated": rate(sum(r["stated"] for r in rs), np_),
                "point_recall_mean": round(sum(r["point_recall"] for r in rs) / len(rs), 3),
                "points_contradicted": sum(r["contradicted"] for r in rs),
                "points_literal_match": rate(sum(r["literal_stated"] for r in rs), np_),
                "figures_supported": rate(sum(r["figures_in_chunk"] + r["figures_derived_ok"] for r in rs), fig),
                "figures_printed_in_chunk": sum(r["figures_in_chunk"] for r in rs),
                "figures_derived_and_checked": sum(r["figures_derived_ok"] for r in rs),
                "answers_with_unsupported_figure": [r["qid"] for r in rs if r["figures_unsupported"]]}

    out = {"_doc": __doc__.strip().split("\n")[0],
           "judge": {"model": "Claude (Fable 5.2), working session 11/16, not an API run", "rubric": "Week 8 run_narrative_judge.py",
                     "quote_guard": "every stated verdict carries a quote found in the answer"},
           "gold": "benchmark_v2_2.jsonl", "required_points_differ_from_rag_file": points_differ,
           "borderline_verdicts": vd.BORDERLINE, "runs": {}}
    for r, (name, f) in RUNS.items():
        rs = [x for x in rows if x["run"] == name]
        out["runs"][name] = {"rag_run": next(iter(data[r].values()))["run"], "all": summ(rs),
                             "by_group": {g: summ([x for x in rs if x["group"] == g]) for g in ("narrative", "categorical", "false_premise")},
                             "by_company": {k: summ([x for x in rs if (x["ticker"] == "MSFT") == (k == "MSFT")]) for k in ("MSFT", "other")}}
    A = {x["qid"]: x for x in rows if x["run"] == "final_v1"}
    B = {x["qid"]: x for x in rows if x["run"] == "narr_union"}
    ch = lambda q: [c["chunk_id"] for c in data["A"][q]["cited_chunks"]] != [c["chunk_id"] for c in data["B"][q]["cited_chunks"]]  # noqa: E731
    out["final_v1_vs_narr_union"] = {
        "answers_differ": sum(data["A"][q]["rag_answer"] != data["B"][q]["rag_answer"] for q in A),
        "cited_chunks_differ": sum(ch(q) for q in A),
        "gained_pass": sorted(q for q in A if not A[q]["passed"] and B[q]["passed"]),
        "lost_pass": sorted(q for q in A if A[q]["passed"] and not B[q]["passed"]),
        "more_points": {q: f"{A[q]['stated']}->{B[q]['stated']} of {A[q]['n_points']}" for q in A if B[q]["stated"] > A[q]["stated"]},
        "fewer_points": {q: f"{A[q]['stated']}->{B[q]['stated']} of {A[q]['n_points']}" for q in A if B[q]["stated"] < A[q]["stated"]},
        "failed_in_both": sorted(q for q in A if not A[q]["passed"] and not B[q]["passed"])}
    if a.validate:
        j = {(p["qid"], p["run"], p["point"]): p["judge_verdict"] for p in per_point}
        pairs = [(r["human_verdict"].strip().lower(), j[(r["qid"], r["run"], int(r["point"]))]) for r in csv.DictReader(open(a.validate))
                 if r.get("human_verdict", "").strip() and (r["qid"], r["run"], int(r["point"])) in j]
        n = len(pairs)
        po = sum(h == x for h, x in pairs) / n
        pe = sum((sum(h == c for h, _ in pairs) / n) * (sum(x == c for _, x in pairs) / n) for c in ("stated", "missing", "contradicted"))
        out["validation"] = {"labels": Path(a.validate).name, "points": n, "agreement": round(po, 3),
                             "kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0, "confusion_human_judge": dict(Counter(f"{h}/{x}" for h, x in pairs))}
    RES.mkdir(exist_ok=True)
    (RES / "narrative_judge_w9.json").write_text(json.dumps(out, indent=1))
    for name, rs in (("narrative_judge_w9_per_question.csv", rows), ("narrative_judge_w9_per_point.csv", per_point)):
        with open(RES / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0]))
            w.writeheader()
            w.writerows(rs)
    with open(PRIV / "judge_labels_w9_blank.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "run", "point", "required_point", "answer_text", "human_verdict"])
        for qid in A:
            for r, (name, _) in RUNS.items():
                for i, p in enumerate(gold[qid]["answer"]["required_points"], 1):
                    w.writerow([qid, name, i, p, data[r][qid]["rag_answer"] if i == 1 else "", ""])
    for name in ("final_v1", "narr_union"):
        s = out["runs"][name]["all"]
        print(f"[judge w9] {name}: passed {s['passed']['k']}/{s['passed']['n']}, points {s['points_stated']['k']}/{s['points_stated']['n']}, "
              f"literal {s['points_literal_match']['k']}, figures supported {s['figures_supported']['k']}/{s['figures_supported']['n']}, "
              f"unsupported in {s['answers_with_unsupported_figure']}")
    d = out["final_v1_vs_narr_union"]
    print(f"[judge w9] gained {d['gained_pass']} lost {d['lost_pass']} more {d['more_points']} fewer {d['fewer_points']}")
    thin = [(r["qid"], r["run"], r["thin_sentences"]) for r in rows if r["thin_sentences"]]
    print(f"[judge w9] sentences to read against the chunks: {thin}")
    for r in rows:
        if r["figures_unsupported"]:
            print("   unsupported figures", r["qid"], r["run"], r["figures_unsupported"])


if __name__ == "__main__":
    sys.exit(main())
