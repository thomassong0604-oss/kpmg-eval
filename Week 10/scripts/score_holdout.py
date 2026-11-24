"""Week 10: official score of a sealed holdout batch (RAG's final_v1 on batch A, 11/22-23; final_v2 on batch B, 11/24; each run once by RAG).

    python scripts/score_holdout.py [--batch A --system final_v1 | --batch B --system final_v2]
        private/holdout_<B>_answer_blocks.jsonl, private/holdout_<B>_rag_per_question.csv   as returned by RAG
        ../Week 9/private/holdout_<B>.jsonl                                                  the sealed questions (hash checked)
        private/holdout_<B>_narrative_verdicts.py                                            judge verdicts for narrative answers
        -> results/holdout_<B>_final_v1.json, results/holdout_<B>_final_v1_per_question.csv  (labels only; no question or answer text)

Same graders as the development set (Week 8 grade_answer_blocks.grade). Nothing in the gold answers was changed after
the answers arrived: a disputed gold answer is reported as disputed, not re-graded.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8, W9 = ROOT.parent / "Week 8", ROOT.parent / "Week 9"
sys.path[:0] = [str(W8), str(W8 / "scripts"), str(W9 / "scripts")]
import grade_answer_blocks as gab  # noqa: E402
import score_rag_judge_runs as sj  # noqa: E402
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402


SYSTEMS = {"final_v1": "RAG final_v1 (tag 03a9220; code and index at main 0685fd4, Chroma chroma_C1 7a7ad9801f86)",
           "final_v2": "RAG final_v2 (tag 789bf81; code at main 69198ee, Chroma chroma_C1 7a7ad9801f86)"}


def rate(k, n):
    return {"k": k, "n": n, "value": round(k / n, 3) if n else None, "ci95": [round(x, 3) for x in wilson(k, n)] if n else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="A")
    ap.add_argument("--system", default="final_v1")
    a = ap.parse_args()
    B, SYS = a.batch, a.system
    gold_path = W9 / "private" / f"holdout_{B}.jsonl"
    sha = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    man = json.load(open(W9 / "results" / f"holdout_{B}_manifest.json"))
    assert sha == man["sha256"], "the sealed file no longer matches the published hash"
    gold = {q["qid"]: q for q in map(json.loads, open(gold_path))}
    answers = {b["qid"]: b for b in map(json.loads, open(ROOT / "private" / f"holdout_{B}_answer_blocks.jsonl"))}
    chunks = {c["chunk_id"]: {"accession": c["accession"], "text": c["text"]} for c in map(json.loads, open(W8 / "private" / "chunks_C1.jsonl"))}
    _, rows = gab.grade(gold, answers, FactIndex.from_jsonl(W8 / "data" / "msft_xbrl_facts.jsonl"), chunks)
    spec = importlib.util.spec_from_file_location("v", ROOT / "private" / f"holdout_{B}_narrative_verdicts.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    rag = {r["qid"]: r for r in csv.DictReader(open(ROOT / "private" / f"holdout_{B}_rag_per_question.csv"))}
    for r in rows:
        q = gold[r["qid"]]
        r.update(stress_type=q["stress_type"] or "", msft="MSFT" in q["tickers"], form=q["filters"].get("form", "several or none"))
        if r["scored_as"] == "narrative":
            raw, pts = vd.V[r["qid"]], q["answer"]["required_points"]
            v = sj.guard(raw, answers[r["qid"]]["answer_text"] or "", len(pts))
            assert v == [x[0] for x in raw], f"quote not in the answer: {r['qid']}"
            r.update(points_stated=v.count("stated"), n_points=len(pts), passed=v.count("stated") == len(pts),
                     label="all_points" if v.count("stated") == len(pts) else "missing_points", borderline=r["qid"] in vd.BORDERLINE)
        x = rag.get(r["qid"], {})
        r.update(rag_own_passed=x.get("passed", ""), rag_own_label=x.get("label", ""), retrieval_ms=float(x["retrieval_ms"]) if x.get("retrieval_ms") else None,
                 reader_ms=float(x["reader_latency_ms"]) if x.get("reader_latency_ms") else None,
                 prompt_tokens=int(x["reader_prompt_tokens"]) if x.get("reader_prompt_tokens") else None,
                 completion_tokens=int(x["reader_completion_tokens"]) if x.get("reader_completion_tokens") else None,
                 cost_usd=float(x["cost_usd"]) if x.get("cost_usd") else None, filter_mode=x.get("filter_mode", ""), cached=x.get("reader_cached", ""))
    prev = getattr(vd, "PREVIEWED", {})
    num = [r for r in rows if r["scored_as"] == "numeric"]
    nar = [r for r in rows if r["scored_as"] == "narrative"]
    ref = [r for r in rows if r["scored_as"] == "refusal"]
    naa = lambda rs: rate(sum(r["passed"] for r in rs), len(rs))  # noqa: E731
    ansd = [r for r in rows if r.get("response") == "answered" and r["answerable"]]
    cv = [tuple(map(int, r["citations_valid"].split("/"))) for r in ansd if r.get("citations_valid")]
    pct = lambda xs, p: round(sorted(xs)[min(len(xs) - 1, int(p * len(xs)))], 1)  # noqa: E731
    tot_ms = [r["retrieval_ms"] + r["reader_ms"] for r in rows if r["retrieval_ms"] is not None and r["reader_ms"] is not None]
    disagree = [r["qid"] for r in rows if r["rag_own_passed"] in ("True", "False") and r["passed"] is not None and (r["rag_own_passed"] == "True") != bool(r["passed"])]
    out = {"_doc": __doc__.strip().split("\n")[0], "batch": B, "system": SYSTEMS[SYS],
           "sealed_file_sha256": sha, "hash_matches_manifest": True, "questions": len(rows), "answers_received": sum(r["has_answer"] for r in rows),
           "filters": dict(Counter(r["filter_mode"] for r in rows)), "from_cache": sum(r["cached"] == "True" for r in rows),
           "numeric": {"accuracy": naa(num), "labels_of_misses": dict(Counter(r["label"] for r in num if not r["passed"])),
                       "misses": {r["qid"]: r["label"] for r in num if not r["passed"]},
                       "normal": naa([r for r in num if not r["stress_type"]]), "stress": naa([r for r in num if r["stress_type"]]),
                       "by_stress_type": {s: naa([r for r in num if r["stress_type"] == s]) for s in sorted({r["stress_type"] for r in num if r["stress_type"]})},
                       "microsoft": naa([r for r in num if r["msft"]]), "other_companies": naa([r for r in num if not r["msft"]]),
                       "by_form": {f: naa([r for r in num if r["form"] == f]) for f in sorted({r["form"] for r in num})}},
           "unanswerable_declined": naa(ref),
           "narrative": {"every_point_stated": naa(nar), "points_stated": rate(sum(r["points_stated"] for r in nar), sum(r["n_points"] for r in nar)),
                         "per_question": {r["qid"]: f"{r['points_stated']}/{r['n_points']}" for r in nar}, "borderline_for_human_review": sorted(vd.BORDERLINE),
                         "normal": naa([r for r in nar if not r["stress_type"]]), "stress": naa([r for r in nar if r["stress_type"]]),
                         "by_stress_type": {s: naa([r for r in nar if r["stress_type"] == s]) for s in sorted({r["stress_type"] for r in nar if r["stress_type"]})},
                         "marked_not_answered_by_system": sorted(r["qid"] for r in nar if r.get("response") != "answered"),
                         "previewed_before_run": sorted(prev),
                         "every_point_stated_excluding_previewed": naa([r for r in nar if r["qid"] not in prev]),
                         "judge": "Claude (Fable 5.2), Week 8 rubric with quote guard; not an API run"},
           "citations": {"cited_chunks_exist": rate(sum(k for k, _ in cv), sum(n for _, n in cv)),
                         "answers_citing_a_gold_filing": rate(sum(r.get("cites_gold_filing") is True for r in ansd), sum(r.get("cites_gold_filing") in (True, False) for r in ansd)),
                         "lookup_figure_in_a_cited_chunk": rate(sum(r.get("number_in_cited_chunk") is True for r in ansd), sum(r.get("number_in_cited_chunk") in (True, False) for r in ansd))},
           "cost_and_latency": {"method": "RAG's log: tokens x list price, wall-clock per question; one fresh API call per question",
                                "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rows), "completion_tokens": sum(r["completion_tokens"] or 0 for r in rows),
                                "cost_usd_total": round(sum(r["cost_usd"] or 0 for r in rows), 4), "cost_usd_per_question": round(sum(r["cost_usd"] or 0 for r in rows) / len(rows), 5),
                                "retrieval_ms": {"median": round(statistics.median(r["retrieval_ms"] for r in rows), 1), "p95": pct([r["retrieval_ms"] for r in rows], 0.95)},
                                "reader_ms": {"median": round(statistics.median(r["reader_ms"] for r in rows), 1), "p95": pct([r["reader_ms"] for r in rows], 0.95)},
                                "total_ms": {"median": round(statistics.median(tot_ms), 1), "p95": pct(tot_ms, 0.95)}},
           "eval_vs_rags_own_grader": {"disagreements": disagree},
           "development_set_for_comparison": {"final_v1_numeric_as_reported_by_RAG": "87/93 = 0.935",
                                              "round1_reader_numeric_eval_scored": "89/94 = 0.947 (Gold v2.2)",
                                              "narrative_every_point_gpt6sol_judge_scored_by_eval": "final_v1 17/27, final_v2 candidate 24/27 (Week 9)"}}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"holdout_{B}_{SYS}.json").write_text(json.dumps(out, indent=1))
    keys = [k for k in dict.fromkeys(k for r in rows for k in r) if k not in ("snapshot_status",)]
    with open(ROOT / "results" / f"holdout_{B}_{SYS}_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({k: v for k, v in out.items() if k not in ("_doc", "development_set_for_comparison")}, indent=1))


if __name__ == "__main__":
    main()
