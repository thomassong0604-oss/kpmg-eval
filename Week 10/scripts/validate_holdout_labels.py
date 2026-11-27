"""Week 10: RAG's blind human rating of the 23 holdout narrative answers (received 11/27) against Eval's judge.

    python scripts/validate_holdout_labels.py -> results/holdout_narrative_hand_labels.json

    private/hand_labels_holdout/hand_labels_eval.csv        qid, run, point, rater (R1 | R2), human_verdict: both raters as labelled
    private/hand_labels_holdout/labels_rag_final_v{1,2}.csv consensus per point (4 disagreements adjudicated by RAG)
    results/holdout_{A_final_v1,B_final_v2}_per_question.csv  Eval's judge: points stated per question (published 11/23 and 11/24)

Eval's per-point verdicts were "stated" for every required point except the three in NOT_STATED (see README sections 1 and 3);
the counts per question are checked against the published files before anything is compared.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "private" / "hand_labels_holdout"
NOT_STATED = {("HA-032", 3), ("HA-034", 4), ("HB-016", 1)}            # Eval's judge: missing
FLAGGED_BORDERLINE_BEFORE_LABELS = {("HA-033", 1), ("HA-034", 1)}     # noted as close calls when the scores were published


def kappa(pairs):
    n = len(pairs)
    cats = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return {"points": n, "agree": sum(a == b for a, b in pairs), "agreement": round(po, 3), "kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else None,
            "pairs": dict(Counter(f"{a}/{b}" for a, b in pairs))}


def main():
    judge = {}
    for f in ("holdout_A_final_v1_per_question.csv", "holdout_B_final_v2_per_question.csv"):
        for r in csv.DictReader(open(ROOT / "results" / f)):
            if r["scored_as"] == "narrative":
                n = int(r["n_points"])
                v = {(r["qid"], i): "missing" if (r["qid"], i) in NOT_STATED else "stated" for i in range(1, n + 1)}
                assert sum(x == "stated" for x in v.values()) == int(r["points_stated"]), r["qid"]      # matches what was published
                judge.update(v)
    raters = {}
    for r in csv.DictReader(open(H / "hand_labels_eval.csv")):
        raters.setdefault((r["qid"], int(r["point"])), {})[r["rater"]] = r["human_verdict"].strip().lower()
    cons = {}
    for f in ("labels_rag_final_v1.csv", "labels_rag_final_v2.csv"):
        for r in csv.DictReader(open(H / f)):
            cons[(r["qid"], int(r["point"]))] = r["human_verdict"].strip().lower()
    assert set(judge) == set(raters) == set(cons) and len(judge) == 75
    keys = sorted(judge)
    split = [k for k in keys if raters[k]["R1"] != raters[k]["R2"]]
    agreed = [k for k in keys if k not in split]
    batch = lambda k: "A" if k[0].startswith("HA") else "B"  # noqa: E731
    qs = sorted({k[0] for k in keys})
    passed = lambda src, q: all(v == "stated" for k, v in src.items() if k[0] == q)  # noqa: E731
    out = {"_doc": __doc__.strip().split("\n")[0],
           "labels": {"answers": len(qs), "points": 75, "raters": "two RAG members per answer (four raters in two pairs), blind to every judge and to Eval's scores, as described by RAG"},
           "between_the_two_raters": kappa([(raters[k]["R1"], raters[k]["R2"]) for k in keys]),
           "judge_vs_consensus": {"all": kappa([(cons[k], judge[k]) for k in keys]),
                                  "batch_A_final_v1": kappa([(cons[k], judge[k]) for k in keys if batch(k) == "A"]),
                                  "batch_B_final_v2": kappa([(cons[k], judge[k]) for k in keys if batch(k) == "B"])},
           "judge_vs_points_both_raters_agree_on": kappa([(raters[k]["R1"], judge[k]) for k in agreed]),
           "judge_vs_each_rater_as_labelled": kappa([(raters[k][r], judge[k]) for k in keys for r in ("R1", "R2")]),
           "points_the_raters_split_on": [{"qid": k[0], "point": k[1], "R1": raters[k]["R1"], "R2": raters[k]["R2"], "consensus": cons[k], "judge": judge[k],
                                           "flagged_borderline_by_eval_beforehand": k in FLAGGED_BORDERLINE_BEFORE_LABELS} for k in split],
           "answers_with_every_point": {b: {"judge": sum(passed(judge, q) for q in qs if q.startswith("H" + b)), "consensus": sum(passed(cons, q) for q in qs if q.startswith("H" + b)),
                                            "of": sum(q.startswith("H" + b) for q in qs),
                                            "answer_level_differences": [q for q in qs if q.startswith("H" + b) and passed(judge, q) != passed(cons, q)]} for b in "AB"},
           "points_stated": {b: {"judge": sum(judge[k] == "stated" for k in keys if batch(k) == b), "consensus": sum(cons[k] == "stated" for k in keys if batch(k) == b),
                                 "of": sum(batch(k) == b for k in keys)} for b in "AB"},
           "limits": ["The raters are members of the team whose system is rated; Eval has not labelled these answers itself.",
                      "71 of the 75 consensus labels are two independent raters agreeing. The other 4 were adjudicated by RAG after Eval's per-question counts were public: "
                      "3 by the RAG lead and 1 (HA-034 point 1) delegated to an AI assistant, as RAG's adjudication log states.",
                      "Only 3 consensus labels are not 'stated', so kappa rests on very few cases."]}
    (ROOT / "results" / "holdout_narrative_hand_labels.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
