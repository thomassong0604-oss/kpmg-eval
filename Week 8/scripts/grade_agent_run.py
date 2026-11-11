"""Week 8: grade a run of the Agents' API v0.2 (`/query`) on Gold Set v2.2, including the RAG -> GraphRAG fallback.

    python scripts/run_agent_api.py --base-url <API> --tag agents_v02          # or the Agents run it and send the file
    python scripts/grade_agent_run.py --responses private/agent_responses_agents_v02.jsonl --tag agents_v02 \
        [--baseline <same questions with fallback switched off>.jsonl]
        -> results/agent_run_<tag>.json, results/agent_run_<tag>_per_question.csv (no evidence text)

One JSON response per line, as /query returns it (plus "qid" if you have it; otherwise trace_id "<tag>:<qid>" or the
exact question text is used). v0.2 has no answer yet, so this scores decisions and evidence:

  decision      SUCCESS on answerable questions, NO_EVIDENCE on unanswerable ones (balanced over both); ERROR is not
                scored and is listed apart
  evidence      needed figure (numbers) or every text anchor (prose) in the final evidence texts
  citations     the cited filing (accession read from source_url) is one the gold answer uses
  filters       query understanding vs the gold filters, key by key
  fallback      the Agents' four cases: 1 empty -> GraphRAG, 2 weak -> GraphRAG, 3 ok but final NO_EVIDENCE,
                4 with/without fallback (--baseline); plus each question's expected case from round 1
                (data/fallback_cases_w8.csv): rescue, keep, must_abstain, not_in_graph_yet, ...
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import run_side_by_side as sbs  # noqa: E402
from kpmg_eval.agent_api import (accession_from_url, decision, filters_match, observed_case,  # noqa: E402
                                 qid_of)
from kpmg_eval.graphrag_filters import required_filings  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"


def rate(xs: list[bool]) -> dict:
    xs = [x for x in xs if x is not None]
    return {"k": sum(xs), "n": len(xs), "value": round(sum(xs) / len(xs), 3) if xs else None}


def load(path: str, gold: dict) -> dict:
    byq = {q["question"].strip(): k for k, q in gold.items()}
    out = {}
    for line in open(path):
        if line.strip():
            r = json.loads(line)
            qid = qid_of(r, gold, byq)
            if qid:
                out[qid] = r
    return out


def grade_one(q: dict, r: dict, case: dict) -> dict:
    ev_texts = [e.get("text") or "" for e in r.get("evidence") or []]
    ev = sbs.score_rag(q, ev_texts) if q["answerable"] else {}
    cited = {accession_from_url(c.get("source_url")) for c in r.get("citations") or []} - {None}
    need = set(required_filings(q))
    fm = filters_match(r.get("filters"), q.get("filters"))
    d = decision(r)
    return {
        "qid": q["qid"], "type": q["type"], "route_expected": q["route_expected"], "answerable": q["answerable"],
        "expected_case": case.get("case", ""), "expected_status": case.get("expected_status", ""),
        "status": r.get("status"), "decision": d,
        "decision_correct": None if d == "error" else (d == "answer") == q["answerable"],
        "evidence_status": r.get("evidence_status"), "weak_reasons": "|".join(r.get("weak_reasons") or []),
        "fallback_triggered": bool(r.get("fallback_triggered")), "fallback_used": bool(r.get("fallback_used")),
        "observed_case": observed_case(r), "n_evidence": len(ev_texts),
        "needed_in_evidence": ev.get("needed_in_evidence"), "distractor_shown": ev.get("distractor_shown"),
        "n_citations": len(r.get("citations") or []),
        "cites_gold_filing": (bool(cited & need) if need else None) if cited else (False if need and d == "answer" else None),
        "filters_all_match": all(fm.values()) if fm else None,
        **{f"filter_{k}": v for k, v in fm.items()},
        "error": (r.get("error") or "")[:120],
    }


def summarise(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"] and r["decision"] != "error"]
    un = [r for r in rows if not r["answerable"] and r["decision"] != "error"]
    a_ok = rate([r["decision"] == "answer" for r in ans])
    u_ok = rate([r["decision"] == "abstain" for r in un])
    out = {
        "questions_graded": len(rows), "status": dict(Counter(r["status"] for r in rows)),
        "errors_not_scored": [r["qid"] for r in rows if r["decision"] == "error"],
        "decision": {"answerable_answered": a_ok, "unanswerable_abstained": u_ok,
                     "balanced": round((a_ok["value"] + u_ok["value"]) / 2, 3) if a_ok["n"] and u_ok["n"] else None},
        "evidence": {k: rate([r["needed_in_evidence"] for r in rows if sbs_kind(r) == k and r["decision"] == "answer"])
                     for k in ("number", "prose")},
        "wrong_period_shown_on_numbers": rate([r["distractor_shown"] for r in rows if r["decision"] == "answer"]),
        "citations_cite_a_gold_filing": rate([r["cites_gold_filing"] for r in rows if r["decision"] == "answer"]),
        "filters": {"all_keys_match": rate([r["filters_all_match"] for r in rows]),
                    **{k: rate([r.get(f"filter_{k}") for r in rows]) for k in ("ticker", "form", "fiscal_year", "fiscal_period")}},
        "fallback": {"triggered": rate([r["fallback_triggered"] for r in rows]),
                     "used_when_triggered": rate([r["fallback_used"] for r in rows if r["fallback_triggered"]]),
                     "by_evidence_status": {}, "by_weak_reason": {}, "observed_cases": {}, "expected_cases": {}},
    }
    fb = out["fallback"]
    for es in sorted({str(r["evidence_status"]) for r in rows}):
        rs = [r for r in rows if str(r["evidence_status"]) == es]
        fb["by_evidence_status"][es] = {"n": len(rs), "fallback_triggered": rate([r["fallback_triggered"] for r in rs]),
                                        "needed_in_final_evidence": rate([r["needed_in_evidence"] for r in rs]),
                                        "status": dict(Counter(r["status"] for r in rs))}
    reasons = defaultdict(list)
    for r in rows:
        for w in filter(None, r["weak_reasons"].split("|")):
            reasons[w].append(r)
    for w, rs in sorted(reasons.items()):
        fb["by_weak_reason"][w] = {"n": len(rs), "fallback_used": rate([r["fallback_used"] for r in rs]),
                                   "success": rate([r["status"] == "SUCCESS" for r in rs])}
    for c in sorted({r["observed_case"] for r in rows}):
        rs = [r for r in rows if r["observed_case"] == c]
        fb["observed_cases"][c] = {
            "n": len(rs), "fallback_used": rate([r["fallback_used"] for r in rs]),
            "answerable_success_with_needed_evidence": rate([r["status"] == "SUCCESS" and r["needed_in_evidence"] is True
                                                             for r in rs if r["answerable"]]),
            "answerable_no_evidence": rate([r["status"] == "NO_EVIDENCE" for r in rs if r["answerable"]]),
            "unanswerable_abstained": rate([r["status"] == "NO_EVIDENCE" for r in rs if not r["answerable"]])}
    for c in sorted({r["expected_case"] for r in rows if r["expected_case"]}):
        rs = [r for r in rows if r["expected_case"] == c]
        fb["expected_cases"][c] = {"n": len(rs), "status_as_expected": rate([r["status"] == r["expected_status"] for r in rs
                                                                            if r["decision"] != "error"]),
                                   "fallback_triggered": rate([r["fallback_triggered"] for r in rs]),
                                   "fallback_used": rate([r["fallback_used"] for r in rs])}
    return out


def sbs_kind(r: dict) -> str:
    return r.get("_kind", "")


def compare(rows: list[dict], base: list[dict]) -> dict:
    """Case 4: the same questions with and without fallback, question by question."""
    b = {r["qid"]: r for r in base}
    out = Counter()
    lists = defaultdict(list)
    for r in rows:
        x = b.get(r["qid"])
        if not x or r["decision"] == "error" or x["decision"] == "error":
            continue
        good = lambda z: z["decision_correct"] and (not z["answerable"] or z["needed_in_evidence"] is not False)  # noqa: E731
        k = {(False, True): "rescued", (True, False): "broken", (True, True): "both_right", (False, False): "both_wrong"}[
            (bool(good(x)), bool(good(r)))]
        out[k] += 1
        if k in ("rescued", "broken"):
            lists[k].append(r["qid"])
    return {**dict(out), **{f"{k}_qids": v for k, v in lists.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--baseline", help="the same questions with fallback switched off (case 4)")
    ap.add_argument("--tag", default="agents")
    a = ap.parse_args()
    gold = {q["qid"]: q for q in map(json.loads, open(DATA / "benchmark_v2_2.jsonl"))}
    cases = {r["qid"]: r for r in csv.DictReader(open(DATA / "fallback_cases_w8.csv"))}

    def grade(path):
        resp = load(path, gold)
        rows = []
        for qid, r in resp.items():
            row = grade_one(gold[qid], r, cases.get(qid, {}))
            row["_kind"] = sbs.kind(gold[qid])
            rows.append(row)
        return rows

    rows = grade(a.responses)
    out = {"responses_file": Path(a.responses).name, "gold": "benchmark_v2_2.jsonl", "contract": "API v0.2",
           "missing_questions": sorted(set(gold) - {r["qid"] for r in rows}), **summarise(rows)}
    if a.baseline:
        out["fallback_vs_no_fallback"] = compare(rows, grade(a.baseline))
    (RES / f"agent_run_{a.tag}.json").write_text(json.dumps(out, indent=1))
    keys = [k for k in dict.fromkeys(k for r in rows for k in r) if not k.startswith("_")]
    with open(RES / f"agent_run_{a.tag}_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    d = out["decision"]
    print(f"[agents {a.tag}] {len(rows)} graded, status {out['status']}; answerable answered {d['answerable_answered']['k']}/"
          f"{d['answerable_answered']['n']}, unanswerable abstained {d['unanswerable_abstained']['k']}/"
          f"{d['unanswerable_abstained']['n']}; fallback triggered {out['fallback']['triggered']['k']}")


if __name__ == "__main__":
    main()
