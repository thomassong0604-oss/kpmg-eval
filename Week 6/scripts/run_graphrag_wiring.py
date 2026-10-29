"""Week 6: wire GraphRAG's retrieval tools into the Eval harness, using their INT-0 mock.

    python scripts/run_graphrag_wiring.py      -> results/graphrag_wiring.json

GraphRAG (Adeline, 10/28): "graph_search and structured_search at their final signatures ... for wiring the harness.
Returns four hardcoded rows, and measures mock not the graph." So this run tests the plumbing, not GraphRAG:
  * every in-scope Microsoft question goes through both arms with its gold filters and trace_id = qid
  * each evidence object is checked against what Eval joins on (trace echo, exactly one provenance key, versions)
  * both arms are scored with the same gold: structured-arm facts at FACT level (incl. XBRL dimensions),
    graph-arm sections at filing level with the question's `contains` anchors
Hit rates are reported only to show the scoring path works; with 4 hardcoded rows they say nothing about the graph.
Default --tools fixture runs Eval's stand-in over the mock's rows (transcribed, no GraphRAG code executed);
--tools mock imports their mock module; --tools real calls graphrag.retrieve once a backend is registered.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.graphrag_adapter import (GraphRAGRetriever, adapter, contract_checks, evidence_key,  # noqa: E402
                                       fixture_tools, load_tools)
from kpmg_eval.keys import EvalKey, Level, matches  # noqa: E402
from kpmg_eval.metrics.retrieval import score_retrieval  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
MSFT_CORPORA = {"msft_10q_q3fy26", "msft_10k_fy26", "msft_10k_fy26+msft_10q_q3fy26"}


def gold_for(q: dict) -> tuple[list[dict], list[dict]]:
    """(fact-level gold for the structured arm, filing-level text gold for the graph arm)."""
    facts = [{**k, "level": "FACT"} for k in ((q.get("gold") or {}).get("evidence") or [])]
    text = [{"cik": "0000789019", "accession": e["accession"], "contains": e.get("contains", []), "level": "FILING"}
            for e in q.get("rag_evidence", []) if e.get("accession") and e.get("contains")]
    return facts, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", choices=["fixture", "mock", "real"], default="fixture",
                    help="fixture: Eval's stand-in over the mock's rows (default, runs no external code); "
                         "mock: GraphRAG's mock module; real: graphrag.retrieve (needs a registered backend)")
    a = ap.parse_args()
    repo = ROOT / "upstream" / "KPMG-GraphRAG"
    if a.tools == "fixture":
        gs, ss = fixture_tools(ROOT / "tests" / "fixtures" / "graphrag_int0_mock_evidence.json")
    else:
        gs, ss = load_tools(repo, mock=a.tools == "mock")
    both = GraphRAGRetriever(gs, ss, "both", f"graphrag-{a.tools}")
    items = [q for q in map(json.loads, open(DATA / "benchmark_scope10.jsonl"))
             if q["corpus"] in MSFT_CORPORA and q["answerable"]]
    items += [q for q in map(json.loads, open(DATA / "benchmark_v1_relationship_draft.jsonl")) if q["answerable"]]

    errors, checks, per_q = Counter(), Counter(), []
    fact_scores, text_scores = [], []
    dims_prevented = 0
    for q in items:
        filt = {k: v for k, v in q["filters"].items() if k in ("ticker", "form", "fiscal_year", "fiscal_period")}
        try:
            env = both.search(q["question"], filters=filt, top_k=10, trace_id=q["qid"])
        except Exception as e:  # scored, never skipped
            errors[type(e).__name__] += 1
            per_q.append({"qid": q["qid"], "error": repr(e)})
            continue
        res = env["results"]
        c = contract_checks(res, q["qid"])
        for k, v in c.items():
            if k != "n":
                checks[f"{k}:{'ok' if v else 'FAIL'}"] += 1
        gf, gt = gold_for(q)
        structured = [r for r in res if r["metadata"]["arm"] == "structured"]
        graph = [r for r in res if r["metadata"]["arm"] == "graph"]
        row = {"qid": q["qid"], "n_graph": len(graph), "n_structured": len(structured), "extraction_version": env["extraction_version"]}
        if gf:
            s = score_retrieval(gf, adapter(structured), ks=(1, 10))
            fact_scores.append(s)
            row["structured_hit@10"] = s["hit@10"]
            # how many structured results would have counted as gold if XBRL dimensions were ignored
            for r in structured:
                k = evidence_key(r)
                for g in gf:
                    gk = EvalKey(**{x: y for x, y in g.items() if x in EvalKey.__dataclass_fields__})
                    if k.dims != gk.dims and matches(EvalKey(**{**k.to_dict(), "dims": gk.dims}), gk, Level.FACT):
                        dims_prevented += 1
        if gt:
            s = score_retrieval(gt, adapter(graph), ks=(1, 10))
            text_scores.append(s)
            row["graph_hit@10"] = s["hit@10"]
        per_q.append(row)

    def mean(xs, k):
        return round(sum(x[k] for x in xs) / len(xs), 3) if xs else None

    # the one question the mock was built to answer: total revenue, three months ended 2026-03-31
    demo = next((r for r in per_q if r["qid"] == "GSv0-MSFT-001"), None)
    sample = both.search("Microsoft total revenue three months ended March 31 2026", {"ticker": "MSFT"}, 10, trace_id="demo")
    facts = [r for r in sample["results"] if r["metadata"].get("fact_id")]
    out = {
        "what_this_measures": "plumbing on GraphRAG's 4-row INT-0 mock; not the graph",
        "tools": {"fixture": "Eval stand-in over the mock's transcribed rows (tests/fixtures/graphrag_int0_mock_evidence.json)",
                  "mock": "mock/mock_retrieval_tools.py", "real": "graphrag.retrieve"}[a.tools],
        "questions": len(items), "calls": len(items) * 2, "errors": dict(errors),
        "contract_checks": dict(checks),
        "scored": {"structured_arm_fact_level": {"n": len(fact_scores), "hit@10": mean(fact_scores, "hit@10")},
                   "graph_arm_filing_level": {"n": len(text_scores), "hit@10": mean(text_scores, "hit@10")}},
        "segment_fact_vs_total_pairs_rejected_by_dims": dims_prevented,
        "demo_GSv0_MSFT_001": demo,
        "findings_for_graphrag": [
            {"finding": "structured arm value_num is in USD millions (82886) while the fact unit is USD",
             "evidence": [{"fact_id": r["metadata"]["fact_id"], "value_num": r["metadata"]["value_num"],
                           "unit_ref": r["metadata"]["unit_ref"]} for r in facts[:1]],
             "ask": "return the value in the XBRL unit, or add a scale field"},
            {"finding": "dimension members are labels ('Intelligent Cloud'), not XBRL members (msft:IntelligentCloudMember)",
             "evidence": [r["metadata"]["dimensions"] for r in facts if r["metadata"]["dimensions"]][:1],
             "ask": "carry the member QName; Eval normalises labels for now"},
        ],
        "per_question": per_q,
    }
    RES.mkdir(exist_ok=True)
    (RES / "graphrag_wiring.json").write_text(json.dumps(out, indent=1))
    print(f"[graphrag] {out['questions']} questions, {out['calls']} calls, errors {dict(errors) or 0}; checks {dict(checks)}")
    print(f"[graphrag] scored {json.dumps(out['scored'])}; segment-vs-total pairs rejected by dims: {dims_prevented}; demo {demo}")


if __name__ == "__main__":
    main()
