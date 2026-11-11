"""Week 8: grade AnswerBlocks produced elsewhere (RAG's round-1 reader, later the Agents' pipeline) on Gold Set v2.x.

    python scripts/grade_answer_blocks.py --answers private/rag_round1_answer_blocks.jsonl \
        --chunks private/chunks_C1.jsonl --tag rag_reader_round1
        -> results/answers_<tag>.json            scores on v2 (what the run used) and v2.2, with RAG's subset reproduced
        -> results/answers_<tag>_per_question.csv  labels per question (no answer text, no chunk text)

The answers and chunks stay in private/ (git-ignored): Data asks that exports stay off GitHub, and the per-question
answers were shared privately. Only scores, labels and ids are written.

What is scored (no LLM; narrative answers wait for the judge in scripts/run_narrative_judge.py):
  numbers       NAA, kpmg_eval/metrics/numeric.py (v2.2: multi-value questions need every figure)
  categories    every required point stated, kpmg_eval/metrics/categorical.py
  premise       corrected / rejected / accepted, kpmg_eval/metrics/premise.py
  refusal       balanced RAA on all non-false-premise questions (refusal.score_raa)
  citations     with --chunks: cited ids exist in the chunks; a cited chunk comes from a filing the gold answer uses;
                lookups: the number shown is printed in a cited chunk; text questions: gold anchors in cited chunks
  narrative     required-points coverage, provisional (word overlap), until the LLM judge runs
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.harness import _points_coverage  # noqa: E402
from kpmg_eval.metrics.categorical import score_categorical  # noqa: E402
from kpmg_eval.metrics.citation import number_supported  # noqa: E402
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402
from kpmg_eval.metrics.numeric import score_numeric_diagnosed  # noqa: E402
from kpmg_eval.metrics.premise import classify_premise  # noqa: E402
from kpmg_eval.metrics.refusal import classify_response, score_raa  # noqa: E402
from kpmg_eval.normalize import extract_quantities  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
GOLD = {"v2": "benchmark_v2.jsonl", "v2_1": "benchmark_v2_1.jsonl", "v2_2": "benchmark_v2_2.jsonl"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def gold_accessions(q: dict) -> set[str]:
    acc = {e.get("accession") for e in (q.get("gold") or {}).get("evidence", []) if isinstance(e, dict)}
    acc |= {e.get("accession") for e in q.get("rag_evidence", [])}
    acc |= {f.get("accession") for f in q.get("facts", [])}
    return {a for a in acc if a}


def anchors_in(q: dict, texts: list[str]) -> tuple[int, int]:
    items = [e["contains"] for e in q.get("rag_evidence", []) if e.get("contains")]
    low = [t.lower() for t in texts]
    return sum(any(all(s.lower() in t for s in c) for t in low) for c in items), len(items)


def grade(gold: dict, answers: dict, fi: FactIndex, chunks: dict | None) -> tuple[dict, list[dict]]:
    rows = []
    for qid, q in gold.items():
        a = answers.get(qid)
        r = {"qid": qid, "type": q["type"], "answer_type": q["answer_type"], "route_expected": q["route_expected"],
             "answerable": q["answerable"], "snapshot_status": q.get("snapshot_status"), "has_answer": a is not None}
        if a is None:
            rows.append({**r, "scored_as": "missing", "passed": False, "label": "no_answer"})
            continue
        text = a.get("answer_text") or ""
        r["answered"] = a.get("answered")
        r["response"] = classify_response(a)
        at = q["answer_type"]
        if at == "exact_numeric":
            n = score_numeric_diagnosed(q, a, fi)
            r.update(scored_as="numeric", passed=n.passed, label=n.label,
                     values_stated=f"{n.values_stated[0]}/{n.values_stated[1]}" if n.values_stated else "")
        elif at == "exact_categorical":
            if r["response"] == "refused":
                r.update(scored_as="categorical", passed=False, label="refused")
            else:
                c = score_categorical(q["answer"]["required_points"], text)
                r.update(scored_as="categorical", passed=c["passed"], label="correct" if c["passed"] else "missing_points",
                         values_stated=f"{c['points_stated']}/{c['points']}")
        elif at == "false_premise":
            lab = classify_premise(text, q["answer"]["required_points"])
            if a.get("answered") is False and lab == "accepted":
                lab = "refused"
            r.update(scored_as="premise", passed=lab == "corrected", label=lab)
        elif at == "refusal":
            r.update(scored_as="refusal", passed=r["response"] == "refused",
                     label="correct_refusal" if r["response"] == "refused" else "answered_unanswerable")
        else:  # narrative
            cov = 0.0 if r["response"] == "refused" else _points_coverage(text, q["answer"]["required_points"])
            r.update(scored_as="narrative", passed=None, label="refused" if r["response"] == "refused" else "pending_judge",
                     points_coverage_provisional=round(cov, 2))
        # citations
        cites = [c.get("id") for c in a.get("citations", []) if c.get("id")]
        r["n_citations"] = len(cites)
        if chunks is not None and r["response"] == "answered" and q["answerable"]:
            found = [chunks[c] for c in cites if c in chunks]
            r["citations_valid"] = f"{len(found)}/{len(cites)}" if cites else ""
            want = gold_accessions(q)
            r["cites_gold_filing"] = bool(want & {c["accession"] for c in found}) if want and cites else ""
            texts = [c["text"] for c in found]
            if at == "exact_numeric" and q["type"] in ("extraction", "segment") and a.get("value_text"):
                nums = [x for x in extract_quantities(a["value_text"])][:1]
                r["number_in_cited_chunk"] = bool(nums and texts and any(number_supported(nums[0], t) for t in texts))
            if at in ("narrative", "false_premise", "exact_categorical") and q.get("rag_evidence"):
                k, n = anchors_in(q, texts)
                r["gold_anchors_in_cited_chunks"] = f"{k}/{n}"
        rows.append(r)
    return summarise(rows), rows


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": round(k / n, 3) if n else None,
            "ci95": [round(x, 3) for x in wilson(k, n)] if n else None}


def summarise(rows: list[dict], scope: str = "all") -> dict:
    num = [r for r in rows if r.get("scored_as") == "numeric"]
    cat = [r for r in rows if r.get("scored_as") == "categorical"]
    prem = [r for r in rows if r.get("scored_as") == "premise"]
    nar = [r for r in rows if r.get("scored_as") == "narrative"]
    def raa_of(keep):
        return score_raa([(r["answerable"], {"answered": r.get("response") != "refused", "value": None})
                          for r in rows if keep(r) and r.get("has_answer")])
    raa = raa_of(lambda r: r["answer_type"] != "false_premise")     # our harness: false premise scored on its own
    raa_fp = raa_of(lambda r: True)                                 # false-premise questions counted as answerable
    un = [r for r in rows if r["answer_type"] == "refusal"]
    cites = [r for r in rows if "citations_valid" in r and r["citations_valid"]]
    out = {
        "scope": scope, "questions": len(rows),
        "numeric_accuracy": rate(sum(r["passed"] for r in num), len(num)),
        "numeric_errors": dict(Counter(r["label"] for r in num if not r["passed"])),
        "categorical_accuracy": rate(sum(r["passed"] for r in cat), len(cat)),
        "false_premise": dict(Counter(r["label"] for r in prem)),
        "false_premise_corrected": rate(sum(r["passed"] for r in prem), len(prem)),
        "refusal": {"balanced_raa": round(raa["balanced_raa"], 3) if raa["balanced_raa"] is not None else None,
                    "balanced_raa_incl_false_premise": round(raa_fp["balanced_raa"], 3) if raa_fp["balanced_raa"] is not None else None,
                    "appropriate_refusal_rate": raa["appropriate_refusal_rate"],
                    "unnecessary_refusal_rate": round(raa["unnecessary_refusal_rate"], 3) if raa["unnecessary_refusal_rate"] is not None else None,
                    "n_answerable": raa["n_answerable"], "n_unanswerable": raa["n_unanswerable"],
                    "unanswerable_refused": f"{sum(r['passed'] for r in un)}/{len(un)}",
                    "answerable_refused": sorted(r["qid"] for r in rows if r["answerable"] and r.get("response") == "refused")},
        "narrative": {"n": len(nar), "refused": sum(r["label"] == "refused" for r in nar),
                      "points_coverage_provisional": round(sum(r["points_coverage_provisional"] for r in nar) / len(nar), 3) if nar else None,
                      "note": "word-overlap stand-in; the LLM judge (scripts/run_narrative_judge.py) replaces it"},
    }
    if cites:
        def frac(key):
            xs = [r[key] for r in rows if isinstance(r.get(key), bool)]
            return rate(sum(xs), len(xs))
        out["citations"] = {
            "answers_with_citations": len(cites),
            "cited_ids_found_in_chunks": rate(sum(int(r["citations_valid"].split("/")[0]) for r in cites),
                                              sum(int(r["citations_valid"].split("/")[1]) for r in cites)),
            "cites_a_gold_filing": frac("cites_gold_filing"),
            "lookup_number_in_cited_chunk": frac("number_in_cited_chunk"),
            "text_answers_all_gold_anchors_cited": rate(
                sum(r["gold_anchors_in_cited_chunks"].split("/")[0] == r["gold_anchors_in_cited_chunks"].split("/")[1]
                    for r in rows if r.get("gold_anchors_in_cited_chunks")),
                sum(1 for r in rows if r.get("gold_anchors_in_cited_chunks")))}
    return out


def rag_subset(rows: list[dict]) -> list[dict]:
    """How RAG's 11/11 numbers come out exactly: leave out the graph-route and review-required questions."""
    return [r for r in rows if r["route_expected"] != "graph" and r.get("snapshot_status") != "review_required"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--chunks", help="RAG's chunks .jsonl, to check citations (private)")
    ap.add_argument("--tag", default="external")
    ap.add_argument("--eval-commit-used", default="0fd5695", help="the kpmg-eval commit the other team vendored")
    a = ap.parse_args()
    answers = {}
    for line in open(a.answers):
        if line.strip():
            b = json.loads(line)
            answers[b["qid"]] = b
    chunks = None
    if a.chunks:
        chunks = {}
        for line in open(a.chunks):
            c = json.loads(line)
            chunks[c["chunk_id"]] = {"accession": c["accession"], "text": c["text"]}
    fi = FactIndex.from_jsonl(DATA / "msft_xbrl_facts.jsonl")
    out = {"answers_file": Path(a.answers).name, "answers_sha256_16": sha(Path(a.answers)), "n_answers": len(answers),
           "graders_used_by_sender": f"kpmg-eval @ {a.eval_commit_used}", "chunks_checked": bool(chunks),
           "by_gold_set": {}}
    per_q = {}
    for v in ("v2", "v2_2"):
        gold = {q["qid"]: q for q in map(json.loads, open(DATA / GOLD[v]))}
        summ, rows = grade(gold, answers, fi, chunks)
        summ["gold_sha256_16"] = sha(DATA / GOLD[v])
        summ["rag_subset"] = summarise(rag_subset(rows), "no graph-route, no review-required (as RAG reported 11/11)")
        out["by_gold_set"][v] = summ
        per_q[v] = {r["qid"]: r for r in rows}
    changed = [q for q in per_q["v2"] if per_q["v2"][q].get("passed") != per_q["v2_2"][q].get("passed")
               or per_q["v2"][q].get("label") != per_q["v2_2"][q].get("label")]
    out["changed_v2_to_v2_2"] = {q: f"{per_q['v2'][q]['label']} -> {per_q['v2_2'][q]['label']}" for q in changed}
    (RES / f"answers_{a.tag}.json").write_text(json.dumps(out, indent=1))
    rows = list(per_q["v2_2"].values())
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(RES / f"answers_{a.tag}_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys + ["label_v2"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "label_v2": per_q["v2"][r["qid"]]["label"]})
    for v, s in out["by_gold_set"].items():
        print(f"[grade {a.tag}] {v}: NAA {s['numeric_accuracy']['k']}/{s['numeric_accuracy']['n']}"
              f" = {s['numeric_accuracy']['value']}, balanced RAA {s['refusal']['balanced_raa']} ({s['refusal']['balanced_raa_incl_false_premise']} with false premise), unanswerable"
              f" {s['refusal']['unanswerable_refused']}, categorical {s['categorical_accuracy']['k']}/{s['categorical_accuracy']['n']},"
              f" premise {s['false_premise']} | RAG subset: NAA {s['rag_subset']['numeric_accuracy']['k']}/"
              f"{s['rag_subset']['numeric_accuracy']['n']} = {s['rag_subset']['numeric_accuracy']['value']}, balanced RAA"
              f" {s['rag_subset']['refusal']['balanced_raa']} ({s['rag_subset']['refusal']['balanced_raa_incl_false_premise']} with false premise), unanswerable {s['rag_subset']['refusal']['unanswerable_refused']}")
    print(f"[grade {a.tag}] changed v2 -> v2.2: {out['changed_v2_to_v2_2']}")
    if chunks:
        print(f"[grade {a.tag}] citations (v2.2): {json.dumps(out['by_gold_set']['v2_2']['citations'])}")


if __name__ == "__main__":
    main()
