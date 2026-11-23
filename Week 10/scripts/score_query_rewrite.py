"""Week 10: official score of RAG's six filter-source arms on messy_wording_v1 (427 rewrites; exploratory, not pre-registered).

    python scripts/score_query_rewrite.py [--dir private/eval_query_rewrite_1122]
        <dir>/<arm>_answer_blocks.jsonl for arm in none, precheck, rag_llm, agents, agents_precheck, gold
        -> results/query_rewrite_arms.json, results/query_rewrite_arms_per_item.csv   (labels and ids, no answer text)

Scorer: Week 9 grade_suite_answers.messy (each rewrite graded against the clean question's Gold v2.2 answer), with citation
checks against chunks_C1. Pairwise comparison between arms: exact McNemar on the number questions.
RAG's own figures (from their comparison.md) are kept next to ours so any difference is visible.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
W8, W9 = ROOT.parent / "Week 8", ROOT.parent / "Week 9"
sys.path[:0] = [str(W9 / "scripts")]
import grade_suite_answers as gsa  # noqa: E402

ARMS = ["none", "precheck", "rag_llm", "agents", "agents_precheck", "gold"]
LABEL = {"none": "No filters", "precheck": "Rule pre-check", "rag_llm": "A: RAG-side LLM + pre-check", "agents": "B: Agents' LLM extractor (d89208c)",
         "agents_precheck": "B + pre-check (post-hoc)", "gold": "Gold filters (upper bound)"}
RAG_OWN = {"none": (203, 264), "precheck": (215, 264), "rag_llm": (214, 264), "agents": (215, 264), "agents_precheck": (215, 264), "gold": (229, 264)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "private" / "eval_query_rewrite_1122"))
    a = ap.parse_args()
    out_of_corpus = {r["qid"] for r in csv.DictReader(open(W8 / "data" / "fallback_cases_w8.csv")) if r["case"] == "not_in_corpus"}
    arms, rows_by, items = {}, {}, []
    for arm in ARMS:
        ns = SimpleNamespace(answers=str(Path(a.dir) / f"{arm}_answer_blocks.jsonl"), clean=None, chunks=str(W8 / "private" / "chunks_C1.jsonl"))
        summ, rows = gsa.messy(ns)
        blocks = gsa.load_answers(ns.answers, "vid")
        rows_by[arm] = {r["vid"]: r for r in rows}
        num_all = [r for r in rows if r.get("has_answer") and r.get("scored_as") == "numeric"]
        num = [r for r in num_all if r["qid"] not in out_of_corpus]
        inc = [r for r in rows if r["qid"] not in out_of_corpus]
        ansd = [r for r in rows if r["answerable"] and r.get("response") == "answered"]
        cv = [tuple(map(int, r["citations_valid"].split("/"))) for r in ansd if r.get("citations_valid")]
        nar = [r for r in rows if r.get("scored_as") == "narrative" and r.get("has_answer")]
        arms[arm] = {"label": LABEL[arm], "rewrites": summ["all"]["rewrites"], "missing": summ["missing_rewrites"],
                     "numeric_accuracy": gsa.rate(sum(r["passed"] for r in num), len(num)),
                     "by_perturbation": {p: gsa.rate(sum(r["passed"] for r in num if r["perturbation"] == p), sum(r["perturbation"] == p for r in num))
                                         for p in ("typo_company", "typo_terms", "casual")},
                     "numeric_labels_of_misses": dict(Counter(r["label"] for r in num if not r["passed"])),
                     "numeric_accuracy_incl_out_of_corpus": summ["all"]["numeric_accuracy"],
                     "answerable_declined": gsa.rate(sum(r.get("response") == "refused" for r in inc if r["answerable"] and r.get("has_answer")),
                                                     sum(bool(r["answerable"] and r.get("has_answer")) for r in inc)),
                     "out_of_corpus_declined": gsa.rate(sum(r.get("response") == "refused" for r in rows if r["qid"] in out_of_corpus),
                                                        sum(r["qid"] in out_of_corpus for r in rows)),
                     "differs_from_rags_grader_on": sorted(r["vid"] for r in num if r["passed"] and blocks[r["vid"]].get("value") is None),
                     "unanswerable_declined": summ["all"]["unanswerable_declined"],
                     "categorical_accuracy": gsa.rate(sum(bool(r["passed"]) for r in inc if r.get("scored_as") == "categorical"),
                                                      sum(r.get("scored_as") == "categorical" for r in inc)),
                     "false_premise_corrected": gsa.rate(sum(bool(r["passed"]) for r in inc if r.get("scored_as") == "premise"),
                                                         sum(r.get("scored_as") == "premise" for r in inc)),
                     "answers_citing_only_other_filings": {"n": sum(r.get("cites_gold_filing") is False for r in ansd),
                                                           "numeric_of_which_right": sum(bool(r["passed"]) for r in ansd if r.get("cites_gold_filing") is False and r.get("scored_as") == "numeric"),
                                                           "numeric": sum(r.get("scored_as") == "numeric" for r in ansd if r.get("cites_gold_filing") is False)},
                     "narrative_answered": gsa.rate(sum(r.get("response") == "answered" for r in nar), len(nar)),
                     "citations": {"cited_chunks_exist": gsa.rate(sum(k for k, _ in cv), sum(n for _, n in cv)),
                                   "answers_citing_a_gold_filing": gsa.rate(sum(r.get("cites_gold_filing") is True for r in ansd),
                                                                            sum(r.get("cites_gold_filing") in (True, False) for r in ansd)),
                                   "lookup_figure_in_a_cited_chunk": gsa.rate(sum(r.get("number_in_cited_chunk") is True for r in ansd),
                                                                              sum(r.get("number_in_cited_chunk") in (True, False) for r in ansd))},
                     "rags_own_grader": {"k": RAG_OWN[arm][0], "n": RAG_OWN[arm][1]},
                     "difference_from_rags_grader": sum(r["passed"] for r in num) - RAG_OWN[arm][0]}
        for r in rows:
            items.append({"arm": arm, **{k: r.get(k) for k in ("vid", "qid", "perturbation", "answer_type", "scored_as", "answerable", "has_answer", "response",
                                                                  "passed", "label", "n_citations", "citations_valid", "cites_gold_filing", "number_in_cited_chunk")}})
    numeric = [v for v, r in rows_by["none"].items() if r.get("scored_as") == "numeric" and r["qid"] not in out_of_corpus
               and all(rows_by[x][v].get("has_answer") for x in ARMS)]
    pairs = {}
    for x, y in combinations(ARMS, 2):
        b = sum(bool(rows_by[x][v]["passed"]) and not rows_by[y][v]["passed"] for v in numeric)
        c = sum(bool(rows_by[y][v]["passed"]) and not rows_by[x][v]["passed"] for v in numeric)
        pairs[f"{x} vs {y}"] = {"only_first_right": b, "only_second_right": c, "mcnemar_exact_p": gsa.mcnemar_exact(b, c)}
    narr = [v for v, r in rows_by["none"].items() if r.get("scored_as") == "narrative" and r["qid"] not in out_of_corpus]
    npairs = {}
    for x, y in (("precheck", "agents"), ("precheck", "rag_llm"), ("precheck", "agents_precheck"), ("agents", "gold"), ("none", "precheck")):
        b = sum(rows_by[x][v].get("response") == "answered" and rows_by[y][v].get("response") != "answered" for v in narr)
        c = sum(rows_by[y][v].get("response") == "answered" and rows_by[x][v].get("response") != "answered" for v in narr)
        npairs[f"{x} vs {y}"] = {"only_first_answered": b, "only_second_answered": c, "mcnemar_exact_p": gsa.mcnemar_exact(b, c)}
    # questions that no filter source fixes (wrong under gold filters too) and those lost only to filter extraction
    wrong_gold = [v for v in numeric if not rows_by["gold"][v]["passed"]]
    lost = {arm: sum(bool(rows_by["gold"][v]["passed"]) and not rows_by[arm][v]["passed"] for v in numeric) for arm in ARMS[:-1]}
    out = {"_doc": __doc__.strip().split("\n")[0], "suite": "messy_wording_v1", "gold": "benchmark_v2_2.jsonl (hash 416304a91b4aa400)",
           "status": "exploratory; the agents_precheck arm was designed by RAG after seeing the other arms on this suite",
           "number_questions": len(numeric),
           "out_of_corpus": {"questions": sorted(out_of_corpus), "rule": "NetApp's 10-Q is not in the round-1 corpus (20 filings); declining is the right "
                             "behaviour, so these rewrites are left out of numeric accuracy and counted on their own line"},
           "arms": arms, "pairwise_number_questions": pairs,
           "narrative_in_corpus": {"rewrites": len(narr), "answered": {x: sum(rows_by[x][v].get("response") == "answered" for v in narr) for x in ARMS},
                                   "pairwise_answered": npairs, "note": "answered is not the same as right: these answers were not judged point by point"},
           "wrong_under_gold_filters": len(wrong_gold), "right_under_gold_filters_but_wrong_in_arm": lost,
           "not_done": "no pairing with clean wording: Eval has no per-question file for final_v1 on the clean questions"}
    (ROOT / "results" / "query_rewrite_arms.json").write_text(json.dumps(out, indent=1))
    with open(ROOT / "results" / "query_rewrite_arms_per_item.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(items[0]))
        w.writeheader()
        w.writerows(items)
    for arm in ARMS:
        x = arms[arm]
        n = x["numeric_accuracy"]
        print(f"{arm:16s} NAA {n['k']}/{n['n']} = {n['value']} {n['ci95']}  vs RAG +{x['difference_from_rags_grader']} {x['differs_from_rags_grader_on']}  ooc declined {x['out_of_corpus_declined']['k']}/{x['out_of_corpus_declined']['n']}  "
              + "  ".join(f"{p} {v['k']}/{v['n']}" for p, v in x["by_perturbation"].items())
              + f"  ans-declined {x['answerable_declined']['k']}/{x['answerable_declined']['n']}  unans {x['unanswerable_declined']['k']}/{x['unanswerable_declined']['n']}"
              + f"  narr answered {x['narrative_answered']['k']}/{x['narrative_answered']['n']}  misses {x['numeric_labels_of_misses']}"
              + f"  cites {x['citations']['cited_chunks_exist']['k']}/{x['citations']['cited_chunks_exist']['n']} goldfiling {x['citations']['answers_citing_a_gold_filing']['k']}/{x['citations']['answers_citing_a_gold_filing']['n']} fig {x['citations']['lookup_figure_in_a_cited_chunk']['k']}/{x['citations']['lookup_figure_in_a_cited_chunk']['n']}")
    print({x: (arms[x]["categorical_accuracy"]["k"], arms[x]["categorical_accuracy"]["n"], arms[x]["false_premise_corrected"]["k"], arms[x]["false_premise_corrected"]["n"],
               arms[x]["answers_citing_only_other_filings"]) for x in ARMS})
    print(len(narr), out["narrative_in_corpus"]["answered"], npairs)
    print("wrong under gold:", len(wrong_gold), "lost vs gold:", lost)


if __name__ == "__main__":
    main()
