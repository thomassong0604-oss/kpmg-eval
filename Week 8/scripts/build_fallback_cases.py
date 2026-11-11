"""Week 8: the fallback test set for the Agents' API v0.2 (RAG -> GraphRAG), built from round-1 evidence.

    python scripts/build_fallback_cases.py   -> data/fallback_cases_w8.csv, results/fallback_cases_w8.json

Every Gold Set v2.2 question gets the case it tests and what the Agent API should return, from what round 1 showed:
RAG's reader (results/answers_rag_reader_round1_per_question.csv, 11/11), GraphRAG's structured arm on its 20-filing
store (results/graphrag_round1_eval_store20.csv, #70) and GraphRAG's graph arm (results/graphrag_round1_graphrag_aura.csv).

  case                    what it tests (Agents' case numbers, 11/11)                 expected
  keep                    RAG already answers; fallback must not break it (case 4)    SUCCESS, fallback not needed
  rescue                  RAG declined, a GraphRAG arm had the evidence (cases 1-2)   fallback used, SUCCESS
  answer_in_rag_evidence  RAG's evidence had the answer, the reader declined (case 3) SUCCESS; NO_EVIDENCE is a false abstention
  split                   cross-company ranking: one call does not fetch ten firms    SUCCESS only with one search per company
  not_in_graph_yet        Exhibit 21: GraphRAG has not loaded it                      NO_EVIDENCE today; rescue once loaded
  not_in_corpus           NetApp's 10-Q, held for review by Data                      NO_EVIDENCE (correct for this corpus)
  must_abstain            unanswerable or out of scope                                NO_EVIDENCE even after fallback
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
NOT_IN_CORPUS = "0001193125-26-380207"      # NetApp 10-Q, review-required at Data


def rows(path, keep=lambda r: True):
    return {r["qid"]: r for r in csv.DictReader(open(path)) if keep(r)}


def main():
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2_2.jsonl")]
    rag = rows(RES / "answers_rag_reader_round1_per_question.csv")
    st = rows(RES / "graphrag_round1_eval_store20.csv", lambda r: r["arm"] == "structured" and r["filters_mode"] == "translated")
    gr = rows(RES / "graphrag_round1_graphrag_aura.csv", lambda r: r["arm"] == "graph" and r["filters_mode"] == "translated")
    out = []
    for q in gold:
        qid = q["qid"]
        r, s, g = rag.get(qid, {}), st.get(qid, {}), gr.get(qid, {})
        rag_ok = r.get("response") == "answered" and (r.get("passed") == "True" or r.get("scored_as") == "narrative"
                                                      or r.get("label") == "corrected")
        gr_has = s.get("needed_in_evidence") == "True" or g.get("needed_in_evidence") == "True"
        accs = {f.get("accession") for f in q.get("facts", [])} | {e.get("accession") for e in q.get("rag_evidence", [])}
        if not q["answerable"]:
            case, status, note = "must_abstain", "NO_EVIDENCE", "unanswerable or out of scope; fallback must not produce evidence that passes"
        elif rag_ok:
            case, status, note = "keep", "SUCCESS", "RAG's reader answered correctly in round 1"
        elif r.get("response") == "refused" and (r.get("values_stated", "").split("/")[0] not in ("", "0")
                                                  or qid in ("GSv0-MSFT-023", "EV1R-005")):
            case, status, note = "answer_in_rag_evidence", "SUCCESS", "RAG's reader stated the answer but marked it not answered"
        elif NOT_IN_CORPUS in accs:
            case, status, note = "not_in_corpus", "NO_EVIDENCE", "NetApp's 10-Q is held for review by Data, so no team has it"
        elif q["route_expected"] == "graph" or q["type"] in ("relationship", "fabricated_relationship"):
            case, status, note = "not_in_graph_yet", "NO_EVIDENCE", "needs Exhibit 21, not yet loaded into GraphRAG's graph"
        elif gr_has:
            case, status, note = "rescue", "SUCCESS", ("GraphRAG's " + ("graph" if g.get("needed_in_evidence") == "True"
                                                                       else "structured") + " arm had the evidence in round 1")
        elif q["type"] == "cross_company":
            case, status, note = "split", "SUCCESS", "ten companies' figures; one GraphRAG call at k=10 did not return them all"
        else:
            case, status, note = "rag_miss_other", "SUCCESS", "RAG declined and neither GraphRAG arm had it in round 1"
        out.append({"qid": qid, "case": case, "expected_status": status, "expect_fallback": case in ("rescue", "split"),
                    "route_expected": q["route_expected"], "answerable": q["answerable"], "type": q["type"],
                    "rag_round1": f"{r.get('response', '')}:{r.get('label', '')}",
                    "graphrag_structured_round1": s.get("needed_in_evidence", ""),
                    "graphrag_graph_round1": g.get("needed_in_evidence", ""), "note": note, "question": q["question"]})
    with open(DATA / "fallback_cases_w8.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    summary = {"questions": len(out), "cases": dict(Counter(r["case"] for r in out)),
               "by_case": {c: [r["qid"] for r in out if r["case"] == c] for c in sorted({r["case"] for r in out}) if c != "keep"}}
    (RES / "fallback_cases_w8.json").write_text(json.dumps(summary, indent=1))
    print(f"[fallback cases] {summary['cases']}")
    for c, q in summary["by_case"].items():
        print(f"  {c}: {q if len(q) < 14 else str(len(q)) + ' questions'}")


if __name__ == "__main__":
    main()
