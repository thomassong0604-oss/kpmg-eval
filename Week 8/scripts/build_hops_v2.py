"""Week 8: hops sheet v2, split into two columns as GraphRAG proposed on 11/11, and agreed by Eval.

    python scripts/build_hops_v2.py   -> data/hops_v2.csv, results/hops_v2_summary.json

  filings   distinct accessions whose evidence the gold answer needs. Eval fills it in code from the gold evidence
            (facts, text anchors, gold evidence), so it re-runs when questions change.
  hops, graph_path, graph_support, graph_note
            GraphRAG's, derived in code on its own ontology (data/hops_v2_graphrag_2026-11-11.csv, sent 11/11), merged
            here unchanged. Blank hops on purpose where GraphRAG's graph cannot make the walk: the 95 XBRL questions
            (no facts in the graph), and questions with no path expected.
  eval_reference_path, eval_reference_edges
            the path in Eval's gold (`graph` field), kept beside GraphRAG's because the two ontologies differ: Eval's
            gold walks to XBRL facts and has a Jurisdiction node; GraphRAG's graph has neither (country and state are
            properties on Subsidiary). A different count is an ontology difference, not a counting error.
  eval_check   Eval's review of GraphRAG's row: "ok" or what to look at. Rules: route changed in v2.2; false premise
               marked unanswerable; fiscal-label question given an Exhibit 21 path; claim-path "yes" whose filing is not
               in GraphRAG's 20-filing corpus, or whose text anchor sits outside the five section types the graph holds
               (by RAG's chunk sections, results/anchor_check_c1.json).

Keyed on Gold Set v2.2 (routes from v2.2; GraphRAG's file was keyed on v2.1). Replaces data/hops_v1.csv.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kpmg_eval.graphrag_filters import GRAPH_SECTION_TYPES, load_snapshot, required_filings  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
# GraphRAG's derivation (tools/fill_hops.py): first file 11/11 afternoon, then PR #71 (7928d89) after Eval's row check
GRAPHRAG_FILE = DATA / "hops_v2_graphrag_pr71.csv"
GRAPHRAG_FIRST = DATA / "hops_v2_graphrag_2026-11-11.csv"
GR_COLS = ("hops", "graph_path", "graph_support", "graph_note", "filled_by")
# Rows Eval asks GraphRAG about, beyond the rule checks below
QUESTIONS = {
    "EV1R-006": "noted: hops 1 counts the OWNS edge only; the product-line and segment legs are not in the ontology",
    "EV1R-005": "'no' is right, for another reason: the correcting text (approximately 27 percent, equity method) is in "
                "the notes to the statements, outside the graph's sections, not XBRL",
}
ANCHORS = RES / "anchor_check_c1.json"          # where each text anchor sits in RAG's chunks (section types)
GRAPHRAG_RUN = RES / "graphrag_round1_graphrag_aura.json"   # the 20 filings in GraphRAG's corpus


def edges(path: str) -> int:
    return len(re.findall(r"-[A-Z_]+->|<-[A-Z_]+-", path))


def reference(q: dict) -> tuple[str, int | str]:
    g = q.get("graph") or {}
    if g.get("path"):
        return g["path"], edges(g["path"])
    if g.get("paths"):
        p = max(g["paths"], key=len)
        concepts = sorted({path[-1][2].split("|")[1] for path in g["paths"] if "|" in path[-1][2]})
        rels = " ".join(f"-{r}-> {'Filing' if i == 0 else 'Fact'}" for i, (_, r, _) in enumerate(p))
        return f"Company {rels} ({', '.join(c.split(':')[-1] for c in concepts)})", len(p)
    return "", ""


def anchor_sections() -> dict:
    if not ANCHORS.exists():
        return {}
    out = {}
    for it in json.loads(ANCHORS.read_text())["items"]:
        out.setdefault(it["qid"], []).append(it.get("section_types") or [])
    return out


SECTIONS = anchor_sections()
CORPUS = set(json.loads(GRAPHRAG_RUN.read_text())["store_filings"]) if GRAPHRAG_RUN.exists() else set()


def check(q: dict, gr: dict) -> str:
    notes = []
    claims_yes = gr.get("graph_support") == "yes" and "Claim" in (gr.get("graph_path") or "")
    missing = sorted(set(required_filings(q)) - CORPUS) if CORPUS else []
    if claims_yes and missing:
        notes.append(f"filing {', '.join(missing)} is not in the 20-filing corpus (NetApp's 10-Q: Data holds it for "
                     "review), so support today is no")
    elif claims_yes and SECTIONS.get(q["qid"]):
        out = [s for s in SECTIONS[q["qid"]] if s and not set(s) & GRAPH_SECTION_TYPES]
        if out:
            where = sorted({t for s in out for t in s})
            notes.append(f"the answer's text sits in {'/'.join(where)} (RAG's chunk sections), outside the five "
                         "section types the graph holds, so support today is no")
    if gr.get("route_expected") and gr["route_expected"] != q["route_expected"]:
        notes.append(f"route is {q['route_expected']} in Gold Set v2.2 (was {gr['route_expected']} in v2.1)")
    if q["answerable"] and "unanswerable" in (gr.get("graph_note") or ""):
        notes.append("answerable false-premise question (the answer must state the correct figure or fact); support as "
                     "for its route")
    if q["type"] == "fiscal_calendar" and "OWNS" in (gr.get("graph_path") or ""):
        notes.append("fiscal-label question on NetApp's 10-Q, not Exhibit 21; Eval's gold labelled the pattern "
                     "'relationship' by mistake (fixed in v2.2: fiscal_label)")
    if q["qid"] in QUESTIONS:
        notes.append(QUESTIONS[q["qid"]])
    return "; ".join(notes) or "ok"


def main():
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2_2.jsonl")]
    snap = load_snapshot(DATA / "snapshot_w7.json")
    src = GRAPHRAG_FILE if GRAPHRAG_FILE.exists() else GRAPHRAG_FIRST
    graphrag = {r["qid"]: r for r in csv.DictReader(open(src))} if src.exists() else {}
    rows = []
    for q in gold:
        accs = required_filings(q)
        gr = graphrag.get(q["qid"], {})
        ref_path, ref_edges = reference(q)
        rows.append({"qid": q["qid"], "type": q["type"], "route_expected": q["route_expected"], "answerable": q["answerable"],
                     "filings": len(accs), "filing_accessions": " ".join(accs),
                     "filing_forms": " ".join(sorted({snap[a]["form"] for a in accs if a in snap})),
                     **{c: gr.get(c, "") for c in GR_COLS},
                     "eval_reference_path": ref_path, "eval_reference_edges": ref_edges,
                     "eval_check": check(q, gr) if gr else "", "reviewed_by": "eval 2026-11-11" if gr else ""})
    with open(DATA / "hops_v2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    hopped = [r for r in rows if r["hops"]]
    summary = {
        "rows": len(rows), "graphrag_file": src.name if graphrag else None,
        "graph_section_types": sorted(GRAPH_SECTION_TYPES),
        "filings_needed": dict(sorted(Counter(r["filings"] for r in rows).items())),
        "hops_filled": len(hopped), "hops": dict(sorted(Counter(r["hops"] for r in hopped).items())),
        "hops_by_route": {rt: dict(Counter(r["hops"] or "blank" for r in rows if r["route_expected"] == rt))
                          for rt in sorted({r["route_expected"] for r in rows})},
        "graph_support": dict(Counter(r["graph_support"] for r in rows)),
        "blank_hops_reasons": dict(Counter((r["graph_note"] or "")[:60] for r in rows if not r["hops"])),
        "ontology_differences": [{"qid": r["qid"], "graphrag_hops": r["hops"], "eval_reference_edges": r["eval_reference_edges"],
                                  "graphrag_path": r["graph_path"], "eval_reference_path": r["eval_reference_path"]}
                                 for r in hopped if r["eval_reference_edges"] not in ("", int(r["hops"]))],
        "eval_check_not_ok": {r["qid"]: r["eval_check"] for r in rows if r["eval_check"] not in ("ok", "")},
    }
    RES.mkdir(exist_ok=True)
    (RES / "hops_v2_summary.json").write_text(json.dumps(summary, indent=1))
    print(f"[hops v2] {len(rows)} rows; filings needed {summary['filings_needed']}; GraphRAG hops filled "
          f"{len(hopped)} {summary['hops']}; support {summary['graph_support']}; rows to check "
          f"{len(summary['eval_check_not_ok'])}")


if __name__ == "__main__":
    main()
