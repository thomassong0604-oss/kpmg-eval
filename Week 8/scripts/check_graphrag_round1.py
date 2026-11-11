"""Week 8 (11/11): check GraphRAG's round-1 run against Eval's rerun on GraphRAG's own 20-filing store.

    python scripts/check_graphrag_round1.py   -> results/graphrag_round1_check.json

Inputs
  results/graphrag_round1_graphrag_aura.{json,csv}   GraphRAG's run (KPMG-GraphRAG 4e89acb, Aura + 20-filing store, v2.1)
  results/graphrag_round1_eval_store20_v2_1.csv      Eval's rerun: structured arm, same store, GraphRAG 21f0795 (#70), v2.1
  results/side_by_side.json, side_by_side_graphrag_store.json   Part A on Eval's one-filing build vs GraphRAG's store
  private/corpus_facts_postgres.duckdb (optional)    to re-probe GSv0-MSFT-001; the store stays private (a Data export)

What it answers
  1. Does Eval's rerun reproduce GraphRAG's structured arm question by question? (translated filters)
  2. What did #70 change? (gold filters: list-valued tickers errored at 4e89acb)
  3. Does the store explain GSv0-MSFT-001 (GraphRAG 11/11 point 2)? Rank 1 on both stores, for the gold wording and
     for "quarter ended" wording.
  4. Part A on GraphRAG's store vs Eval's one-filing build.
  5. How much of the graph arm's prose score is scope: GraphRAG's graph holds five section types (10-K Items 1, 1A, 7;
     10-Q Items 2, 1A). Each prose question is placed by where its text anchors sit in RAG's chunks
     (results/anchor_check_c1.json): inside those sections, outside them, or not in the corpus at all.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES, DATA, UP = ROOT / "results", ROOT / "data", ROOT / "upstream"
FIELDS = ["filing_in_store", "needed_in_evidence", "strict", "top1_right", "top1_wrong_period", "returned_nothing", "n_returned"]


def rows(path: Path) -> dict:
    return {(r["qid"], r["arm"], r["filters_mode"]): r for r in csv.DictReader(open(path))}


def compare(theirs: dict, ours: dict, arm: str, mode: str) -> dict:
    keys = [k for k in ours if k[1] == arm and k[2] == mode and k in theirs]
    diff = [{"qid": k[0], "field": f, "graphrag": theirs[k][f], "eval": ours[k][f]}
            for k in keys for f in FIELDS if theirs[k][f] != ours[k][f]]
    return {"questions": len(keys), "questions_identical": len(keys) - len({d["qid"] for d in diff}), "differences": diff}


def probe_msft_001(store: Path) -> list[dict]:
    """Rank-1 structured fact for GSv0-MSFT-001 on a store, for two wordings, filtered to the 10-Q."""
    sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
    os.environ["MSFT_FACT_DB_PATH"] = str(store)
    for m in [m for m in sys.modules if m.split(".")[0] in ("graphrag", "structured", "structured_query_v1")]:
        del sys.modules[m]
    from kpmg_eval.graphrag_adapter import load_tools
    _, search = load_tools(UP / "KPMG-GraphRAG", mock=False)
    q = next(json.loads(l) for l in open(DATA / "benchmark_v2_2.jsonl") if json.loads(l)["qid"] == "GSv0-MSFT-001")
    out = []
    for label, text in (("gold wording", q["question"]),
                        ("'quarter ended' wording", "What was Microsoft total revenue for the quarter ended March 31, 2026?")):
        for k in (3, 10):
            ev = search(text, filters={"ticker": "MSFT", "accession_number": "0001193125-26-191507"}, top_k=k,
                        trace_id="check")
            m = ev[0]["metadata"] if ev else {}
            out.append({"store": store.name, "wording": label, "top_k": k, "rank1_value_musd": (m.get("value_num") or 0) / 1e6,
                        "rank1_period": f"{m.get('period_start')}..{m.get('period_end')}",
                        "rank1_members": [d.get("member") for d in (m.get("dimensions") or [])],
                        "top3_scores": [round(e.get("score") or 0, 3) for e in ev[:3]],
                        "rank1_is_needed_82886": abs((m.get("value_num") or 0) - 82886e6) < 0.5e6})
    return out


def graph_prose_by_scope(theirs: dict) -> dict:
    sys.path.insert(0, str(ROOT))
    from kpmg_eval.graphrag_filters import GRAPH_SECTION_TYPES
    secs = {}
    for it in json.loads((RES / "anchor_check_c1.json").read_text())["items"]:
        secs.setdefault(it["qid"], []).append(it.get("section_types") or [])
    out = {"in_scope": {"hits": 0, "n": 0, "qids_hit": []}, "outside_scope": {"hits": 0, "n": 0, "qids": []},
           "not_in_corpus_or_chunks": {"hits": 0, "n": 0, "qids": []}}
    for (qid, arm, mode), r in sorted(theirs.items()):
        if arm != "graph" or mode != "translated" or r["kind"] != "prose" or r["needed_in_evidence"] not in ("True", "False"):
            continue
        items = secs.get(qid, [])
        if not items or any(not s for s in items):
            b = "not_in_corpus_or_chunks"
        elif all(set(s) & GRAPH_SECTION_TYPES for s in items):
            b = "in_scope"
        else:
            b = "outside_scope"
        hit = r["needed_in_evidence"] == "True"
        out[b]["n"] += 1
        out[b]["hits"] += hit
        out[b]["qids_hit" if b == "in_scope" else "qids"].append(qid) if (hit or b != "in_scope") else None
    out["note"] = ("Graph arm, translated filters, Gold Set v2.1 as GraphRAG ran it. 'outside_scope': the anchor is only in "
                   "sections the graph does not hold (mostly the notes to the statements); 'not_in_corpus_or_chunks': "
                   "Exhibit 21 or NetApp's 10-Q. Section types from RAG's chunks, a proxy for GraphRAG's own parsing.")
    return out


def main():
    theirs, ours = rows(RES / "graphrag_round1_graphrag_aura.csv"), rows(RES / "graphrag_round1_eval_store20_v2_1.csv")
    meta = json.loads((RES / "graphrag_round1_graphrag_aura.json").read_text())
    out = {"graphrag_run": {"commit": "4e89acb", "gold": meta["gold"], "summary": meta["summary"]},
           "reproduction_structured_translated": compare(theirs, ours, "structured", "translated"),
           "structured_gold_filters_before_after_70": compare(theirs, ours, "structured", "gold")}
    d = out["structured_gold_filters_before_after_70"]
    d["explained_by"] = ("#70: list-valued ticker filters errored at 4e89acb (RetrievalUnavailableError) and run at "
                         "21f0795; every difference is on a question with a list filter")
    lists = {json.loads(l)["qid"] for l in open(DATA / "benchmark_v2_1.jsonl")
             if any(isinstance(v, list) for v in (json.loads(l).get("filters") or {}).values())}
    d["all_differences_on_list_filter_questions"] = all(x["qid"] in lists for x in d["differences"])
    sa, sb = json.loads((RES / "side_by_side.json").read_text()), None
    if (RES / "side_by_side_graphrag_store.json").exists():
        sb = json.loads((RES / "side_by_side_graphrag_store.json").read_text())
    if sb:
        ga, gb = sa["part_a"]["summary"]["graphrag_structured"], sb["part_a"]["summary"]["graphrag_structured"]
        pick = lambda g: {k: f"{g[k]['hits']}/{g[k]['n']}" for k in ("numbers", "top1_right_on_numbers",  # noqa: E731
                                                                       "top1_wrong_period_on_numbers", "distractor_shown_on_numbers")}
        pa = {r["qid"]: r for r in csv.DictReader(open(RES / "side_by_side_per_question.csv")) if "graphrag" in r["system"]}
        pb = {r["qid"]: r for r in csv.DictReader(open(RES / "side_by_side_graphrag_store_per_question.csv")) if "graphrag" in r["system"]}
        score_diff = [q for q in pa if q in pb and any(pa[q][f] != pb[q][f] for f in ("needed_in_evidence", "top1_right"))]
        top1_diff = [q for q in pa if q in pb and pa[q]["top1"] != pb[q]["top1"]]
        out["part_a_by_store"] = {
            "eval_one_filing_build": {"store": sa.get("graphrag_store"), **pick(ga)},
            "graphrag_20_filing_store": {"store": sb.get("graphrag_store"), **pick(gb)},
            "questions_scored_differently": score_diff, "questions_with_a_different_rank1_fact": len(top1_diff),
            "note": "Most rank-1 differences are ties: the same concept with equal scores, ordered differently by each "
                    "store (e.g. cash 11,711 vs 12,731). EV1-015 is the one score change: on GraphRAG's store a "
                    "date fact (DividendsPayableDateDeclared) outranks the dividend per share. GraphRAG's store holds "
                    "1,511 facts for this 10-Q against 1,317 in Eval's build, more of them non-numeric."}
    out["graph_prose_by_scope"] = graph_prose_by_scope(theirs)
    store = ROOT / "private" / "corpus_facts_postgres.duckdb"
    prev = json.loads((RES / "graphrag_round1_check.json").read_text()) if (RES / "graphrag_round1_check.json").exists() else {}
    if store.exists():
        out["gsv0_msft_001_rank1"] = probe_msft_001(store) + probe_msft_001(UP / "graphrag_store_msft_10q.duckdb")
    else:
        out["gsv0_msft_001_rank1"] = prev.get("gsv0_msft_001_rank1")
    out["gsv0_msft_001_conclusion"] = (
        "Not the store. For the gold wording both stores put Microsoft 365 product rows at the top, all scored 1.05 (tied), "
        "because 'three months' matches MicrosoftThreeSixFive members; which tied row is first changes with top_k (and "
        "with the store's row order), so rank 1 is not stable. 'Quarter ended' wording puts the nine-month total "
        "(241,832) at rank 1, the figure GraphRAG saw, which is itself a wrong-period value. For #68: break ties "
        "deterministically (period match first, then facts without dimensions).")
    (RES / "graphrag_round1_check.json").write_text(json.dumps(out, indent=1))
    r = out["reproduction_structured_translated"]
    print(f"[check] structured, translated filters: {r['questions_identical']}/{r['questions']} questions identical")
    print(f"[check] gold filters: {len({x['qid'] for x in d['differences']})} questions differ, all list filters: "
          f"{d['all_differences_on_list_filter_questions']}")
    g = out["graph_prose_by_scope"]
    print(f"[check] graph arm prose: in scope {g['in_scope']['hits']}/{g['in_scope']['n']}, outside scope "
          f"{g['outside_scope']['hits']}/{g['outside_scope']['n']}, not in corpus {g['not_in_corpus_or_chunks']['hits']}/"
          f"{g['not_in_corpus_or_chunks']['n']}")
    if sb:
        print(f"[check] part A by store: {json.dumps(out['part_a_by_store'])[:400]}")
    for p in out["gsv0_msft_001_rank1"] or []:
        print(f"[check] GSv0-MSFT-001 {p['store']} {p['wording']} k={p['top_k']}: rank 1 {p['rank1_value_musd']:,.0f}M "
              f"{p['rank1_period']} scores {p['top3_scores']}")


if __name__ == "__main__":
    main()
