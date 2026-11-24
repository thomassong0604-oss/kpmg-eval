"""Week 10: two follow-ups on the messy-wording arms, from files RAG sent on 11/24.

    python scripts/score_rewrite_followups.py -> results/query_rewrite_followups.json

1. Clean against messy. RAG's final_v1 per-question file on the 155 clean development questions is re-graded with our grader
   (rebuilt into AnswerBlocks from the file's own columns), then every number rewrite is paired with its clean question.
   Caveat from RAG: the clean run (11/16) used the Chroma index before the persistence fix; the arms used the fixed index.
2. Narrative rewrites, judged. RAG ran the Week 8 judge script unchanged (gpt-6-sol) on the pre-check and Agents arms and sent
   a per-rewrite table. We did not run the judge; we check their totals from the table and cross it with our citation check.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8, W9 = ROOT.parent / "Week 8", ROOT.parent / "Week 9"
sys.path[:0] = [str(W9 / "scripts")]
import grade_suite_answers as gsa  # noqa: E402
gab, FactIndex = gsa.gab, gsa.FactIndex
ARMS = ["none", "precheck", "rag_llm", "agents", "agents_precheck", "gold"]
num = lambda s: float(s) if s not in ("", None) else None  # noqa: E731


def clean_vs_messy():
    gold = {q["qid"]: q for q in map(json.loads, open(W8 / "data" / "benchmark_v2_2.jsonl"))}
    rag = {r["qid"]: r for r in csv.DictReader(open(ROOT / "private" / "rag_final_v1_clean_dev_per_question.csv"))}
    blocks = {q: {"qid": q, "answered": r["answered"] == "True", "answer_text": r["answer_text"], "value": num(r["answered_value"]),
                  "value_text": r["value_text"] or None, "period_end": r["period_end"] or None,
                  "citations": [{"id": c} for c in r["cited_chunks"].split("|") if c]} for q, r in rag.items()}
    chunks = {c["chunk_id"]: {"accession": c["accession"], "text": c["text"]} for c in map(json.loads, open(W8 / "private" / "chunks_C1.jsonl"))}
    _, rows = gab.grade(gold, blocks, FactIndex.from_jsonl(W8 / "data" / "msft_xbrl_facts.jsonl"), chunks)
    clean = {r["qid"]: r for r in rows}
    ooc = set(json.load(open(ROOT / "results" / "query_rewrite_arms.json"))["out_of_corpus"]["questions"])
    cn = [r for r in rows if r["scored_as"] == "numeric" and r["qid"] not in ooc]
    differ = sorted(r["qid"] for r in cn if rag[r["qid"]]["passed"] in ("True", "False") and (rag[r["qid"]]["passed"] == "True") != bool(r["passed"]))
    items = [r for r in csv.DictReader(open(ROOT / "results" / "query_rewrite_arms_per_item.csv")) if r["scored_as"] == "numeric" and r["qid"] not in ooc]
    out = {"clean_run": "RAG final_v1, gold filters, 155 clean questions, 11/16 (index before the persistence fix)",
           "clean_numeric_accuracy_in_corpus": gsa.rate(sum(bool(r["passed"]) for r in cn), len(cn)),
           "clean_numeric_misses": dict(Counter(r["label"] for r in cn if not r["passed"])),
           "clean_differs_from_rags_own_grader": differ, "arms": {}}
    for arm in ARMS:
        it = [r for r in items if r["arm"] == arm]
        pairs = [(bool(clean[r["qid"]]["passed"]), r["passed"] == "True", r) for r in it]
        b, c = sum(x and not y for x, y, _ in pairs), sum(y and not x for x, y, _ in pairs)
        lost = [r for x, y, r in pairs if x and not y]
        qs = sorted({r["qid"] for r in it})
        out["arms"][arm] = {"pairs": len(pairs), "both_right": sum(x and y for x, y, _ in pairs), "only_clean_right": b, "only_rewrite_right": c,
                            "neither": sum(not x and not y for x, y, _ in pairs), "mcnemar_exact_p": gsa.mcnemar_exact(b, c),
                            "lost_by_perturbation": dict(Counter(r["perturbation"] for r in lost)),
                            "lost_by_label": dict(Counter(r["label"] for r in lost)),
                            "questions": len(qs),
                            "questions_right_clean_and_in_every_rewrite": sum(bool(clean[q]["passed"]) and all(r["passed"] == "True" for r in it if r["qid"] == q) for q in qs),
                            "questions_right_clean_but_wrong_in_a_rewrite": sum(bool(clean[q]["passed"]) and any(r["passed"] != "True" for r in it if r["qid"] == q) for q in qs)}
    out["note"] = "rewrites of one question are not independent, so the p-values are a guide; the question-level counts do not have that problem"
    return out


def narrative_judged():
    T = list(csv.DictReader(open(ROOT / "private" / "rag_narrative_judge_paired_1123.csv")))
    ours = {(r["arm"], r["vid"]): r for r in csv.DictReader(open(ROOT / "results" / "query_rewrite_arms_per_item.csv"))}
    out = {"source": "RAG's run of Week 8 run_narrative_judge.py, unchanged (gpt-6-sol, default temperature), each rewrite judged on its clean question's required points; "
                     "not run by Eval", "rewrites": len(T), "arms": {}}
    for arm in ("precheck", "agents"):
        f = lambda r, k: r[f"{arm}_{k}"]  # noqa: E731
        ans = [r for r in T if f(r, "answered") == "1"]
        gold_f = [r for r in ans if f(r, "cites_gold_filing") == "1"]
        other_f = [r for r in ans if f(r, "cites_gold_filing") == "0"]
        mean = lambda rs: round(sum(float(f(r, "point_recall")) for r in rs) / len(rs), 3) if rs else None  # noqa: E731
        mism = [r["rewrite_qid"] for r in ans if (f(r, "cites_gold_filing") == "1") != (ours[(arm, r["rewrite_qid"])]["cites_gold_filing"] == "True")]
        out["arms"][arm] = {"answered": len(ans), "all_points": gsa.rate(sum(f(r, "all_points") == "1" for r in T), len(T)),
                            "mean_point_recall_all": mean(T), "contradicted": sum(f(r, "contradicted") == "1" for r in T),
                            "by_perturbation": {p: gsa.rate(sum(f(r, "all_points") == "1" for r in T if r["perturbation"] == p), sum(r["perturbation"] == p for r in T))
                                                for p in ("typo_company", "typo_terms", "casual")},
                            "answers_citing_a_gold_filing": {"n": len(gold_f), "all_points": sum(f(r, "all_points") == "1" for r in gold_f), "mean_point_recall": mean(gold_f),
                                                             "contradicted": sum(f(r, "contradicted") == "1" for r in gold_f)},
                            "answers_citing_only_other_filings": {"n": len(other_f), "all_points": sum(f(r, "all_points") == "1" for r in other_f), "mean_point_recall": mean(other_f),
                                                                  "contradicted": sum(f(r, "contradicted") == "1" for r in other_f)},
                            "answered_flag_differs_from_our_file": sorted(r["rewrite_qid"] for r in T if (f(r, "answered") == "1") != (ours[(arm, r["rewrite_qid"])]["response"] == "answered")),
                            "citation_flag_differs_from_ours": sorted(mism)}
    b = sum(r["precheck_all_points"] == "1" and r["agents_all_points"] == "0" for r in T)
    c = sum(r["agents_all_points"] == "1" and r["precheck_all_points"] == "0" for r in T)
    only_ag = [r for r in T if r["agents_answered"] == "1" and r["precheck_answered"] == "0"]
    out["paired_all_points"] = {"only_precheck": b, "only_agents": c, "mcnemar_exact_p": gsa.mcnemar_exact(b, c)}
    out["answered_only_by_agents"] = {"n": len(only_ag), "all_points": sum(r["agents_all_points"] == "1" for r in only_ag),
                                      "mean_point_recall": round(sum(float(r["agents_point_recall"]) for r in only_ag) / len(only_ag), 3),
                                      "clean_questions": sorted({r["clean_qid"] for r in only_ag})}
    return out


if __name__ == "__main__":
    out = {"_doc": __doc__.strip().split("\n")[0], "clean_vs_messy_numbers": clean_vs_messy(), "narrative_rewrites_judged_by_rag": narrative_judged()}
    (ROOT / "results" / "query_rewrite_followups.json").write_text(json.dumps(out, indent=1))
    c = out["clean_vs_messy_numbers"]
    print(c["clean_numeric_accuracy_in_corpus"], c["clean_numeric_misses"], c["clean_differs_from_rags_own_grader"])
    for a, x in c["arms"].items():
        print(a, {k: x[k] for k in ("pairs", "both_right", "only_clean_right", "only_rewrite_right", "neither", "mcnemar_exact_p", "lost_by_perturbation", "lost_by_label",
                                     "questions", "questions_right_clean_and_in_every_rewrite", "questions_right_clean_but_wrong_in_a_rewrite")})
    print(json.dumps(out["narrative_rewrites_judged_by_rag"], indent=0))
