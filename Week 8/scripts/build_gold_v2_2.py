"""Gold Set v2.2: Gold Set v2.1 plus the grading fixes from RAG's end-to-end round-1 run (11/11).

    python scripts/build_gold_v2_2.py [--chunks path/to/chunks_C1.jsonl]
        -> data/benchmark_v2_2.jsonl, results/gold_v2_2_changes.json, results/anchor_check_c1.json (with --chunks)

Same 155 questions and the same expected answers. What changes, and why:
  1. Sig-fig floor never above the precision the filing prints. EV1-015 (USD 0.91 per share) and EV1-027 (0.66 pp)
     asked for 3 significant figures of a 2-figure number; now 2. Only EV1-015 changes a score: percentages are
     already graded at their written decimals.
  2. Questions that ask for several figures (7) get gold["values"]; all must be stated (kpmg_eval/metrics/numeric.py).
     Each value is recomputed here from the question's own XBRL facts, so a typo cannot slip in.
  3. Routes: EV1R-002 and EV1R-006 move graph -> text. RAG's reader answered both from the 10-K text, and GraphRAG's
     review of the drafts (11/11) found no RENAMED_FROM edge for EV1R-002 and only partial graph support for EV1R-006.
  4. Anchors for the last four unanchored questions (EV2-035/036/037/044), read from RAG's round-1 chunks.
  5. One evidence item per required point for the 22 questions re-anchored in v2.1. v2.1 put two or more sentences in
     one item, which RAG's matcher needs inside a single chunk; RAG's round-1 chunker (C1) splits 8 of them across
     chunks (e.g. GSv0-MSFT-019's two sentences sit in chunks 0080 and 0083), so they could never be found.
  6. EV1R-005 (false premise, no date in the question): the Q3 FY2026 10-Q says Microsoft holds "approximately 27
     percent" of OpenAI; the later FY2026 10-K says "an approximate 25% interest". RAG's reader quoted the 10-K, which is
     also right, so the point now accepts either (" | " = alternatives).
  7. With --chunks, every anchor is checked against RAG's chunks with RAG's own matcher (rag.evaluate.evidence_hits),
     filing by filing. The chunks file stays private (Data asks that exports stay off GitHub); only the check result
     (question ids, pass/fail, chunk ids) is written.

benchmark_v2.jsonl and benchmark_v2_1.jsonl are kept unchanged: RAG's round-1 runs used them.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"

SIG_FIG_FIX = {"EV1-015": 2, "EV1-027": 2}   # printed: "0.91", "0.66"

# (label, kind, min_sig_figs, value in base units computed from the question's fact_values `f`)
M = 1e6
VALUES = {
    "GSv0-MSFT-014": [
        ("change in the surplus", "money", 4, lambda f: (f["NetCashProvidedByUsedInOperatingActivities|YTD|"] - f["PaymentsToAcquirePropertyPlantAndEquipment|YTD|"]) - (f["NetCashProvidedByUsedInOperatingActivities|YTDP|"] - f["PaymentsToAcquirePropertyPlantAndEquipment|YTDP|"])),
        ("nine months 2026 surplus", "money", 3, lambda f: f["NetCashProvidedByUsedInOperatingActivities|YTD|"] - f["PaymentsToAcquirePropertyPlantAndEquipment|YTD|"]),
        ("nine months 2025 surplus", "money", 3, lambda f: f["NetCashProvidedByUsedInOperatingActivities|YTDP|"] - f["PaymentsToAcquirePropertyPlantAndEquipment|YTDP|"])],
    "GSv0-MSFT-015": [
        ("Productivity and Business Processes margin", "percent", 3, lambda f: round(100 * f["OperatingIncomeLoss|Q|ProductivityAndBusinessProcessesMember"] / f["RevenueFromContractWithCustomerExcludingAssessedTax|Q|ProductivityAndBusinessProcessesMember"], 2)),
        ("Intelligent Cloud margin", "percent", 3, lambda f: round(100 * f["OperatingIncomeLoss|Q|IntelligentCloudMember"] / f["RevenueFromContractWithCustomerExcludingAssessedTax|Q|IntelligentCloudMember"], 2))],
    "GSv0-MSFT-016": [
        ("change", "money", 5, lambda f: f["CashCashEquivalentsAndShortTermInvestments|BS|"] - f["CashCashEquivalentsAndShortTermInvestments|BSP|"]),
        ("percentage change", "percent", 3, lambda f: round(100 * (f["CashCashEquivalentsAndShortTermInvestments|BS|"] / f["CashCashEquivalentsAndShortTermInvestments|BSP|"] - 1), 2))],
    "GSv0-MSFT-023": [
        ("change in cash", "money", 4, lambda f: f["CashAndCashEquivalentsAtCarryingValue|BS|"] - f["CashAndCashEquivalentsAtCarryingValue|BSP|"]),
        ("beginning cash", "money", 3, lambda f: f["CashAndCashEquivalentsAtCarryingValue|BSP|"]),
        ("ending cash", "money", 3, lambda f: f["CashAndCashEquivalentsAtCarryingValue|BS|"])],
    "GSv0-MSFT-024": [
        ("Intelligent Cloud share of the increase", "percent", 3, lambda f: round(100 * _seg(f, "IntelligentCloud") / sum(_seg(f, s) for s in SEGS), 2)),
        ("Productivity and Business Processes change", "money", 3, lambda f: _seg(f, "ProductivityAndBusinessProcesses")),
        ("Intelligent Cloud change", "money", 3, lambda f: _seg(f, "IntelligentCloud")),
        ("More Personal Computing change", "money", 3, lambda f: _seg(f, "MorePersonalComputing")),
        ("total change", "money", 3, lambda f: sum(_seg(f, s) for s in SEGS))],
    "GSv0-MSFT-025": [
        ("six-month growth", "percent", 3, lambda f: round(100 * (_h1(f, "") / _h1(f, "P") - 1), 2)),
        ("six months fiscal 2026 revenue", "money", 3, lambda f: _h1(f, "")),
        ("six months fiscal 2025 revenue", "money", 3, lambda f: _h1(f, "P"))],
    "EV1-043": [
        ("operating income change", "money", 3, lambda f: f["OperatingIncomeLoss|Q|MorePersonalComputingMember"] - f["OperatingIncomeLoss|QP|MorePersonalComputingMember"]),
        ("revenue change", "money", 3, lambda f: f["RevenueFromContractWithCustomerExcludingAssessedTax|Q|MorePersonalComputingMember"] - f["RevenueFromContractWithCustomerExcludingAssessedTax|QP|MorePersonalComputingMember"]),
        ("cost of revenue change", "money", 3, lambda f: f["CostOfGoodsAndServicesSold|Q|MorePersonalComputingMember"] - f["CostOfGoodsAndServicesSold|QP|MorePersonalComputingMember"])],
}
SEGS = ("ProductivityAndBusinessProcesses", "IntelligentCloud", "MorePersonalComputing")
REV = "RevenueFromContractWithCustomerExcludingAssessedTax"


def _seg(f, s):
    return f[f"{REV}|Q|{s}Member"] - f[f"{REV}|QP|{s}Member"]


def _h1(f, p):
    return f[f"{REV}|YTD{p}|"] - f[f"{REV}|Q{p}|"]


ROUTE_FIX = {
    "EV1R-002": "Answered from the FY2026 10-K text (segment note and the 'XBOX (formerly Gaming)' line) in RAG's round-1 "
                "run; GraphRAG's review: no RENAMED_FROM edge, rename half not answerable by the graph.",
    "EV1R-006": "Answered from the FY2026 10-K text in RAG's round-1 run; GraphRAG's review: partly supported (the "
                "Exhibit 21 edge is not loaded, Activision attribution not available).",
}

# Read from RAG's round-1 chunks (chunking_version rag-C1-v0-m460), 11/11; strings exactly as the filings print them.
C1_ANCHORS = {
    "EV2-035": [{"ticker": "NKE", "form": "10-Q", "accession": "0000320187-26-000193",
                 "contains": ["three months ended August 31, 2026", "first quarter of fiscal 2027"]}],
    "EV2-036": [{"ticker": "MDT", "form": "10-Q", "accession": "0001628280-26-060473",
                 "contains": ["Fiscal year 2027 is a 53-week fiscal year",
                              "first quarter and included in the three months ended July 31, 2026"]}],
    "EV2-037": [{"ticker": "MU", "form": "10-Q", "accession": "0000723125-26-000015",
                 "contains": ["Thursday closest to August 31", "third quarter of 2026"]}],
    "EV2-044": [{"ticker": "CASY", "form": "10-K", "accession": "0000726958-26-000046",
                 "contains": ["Fiscal Year Ended April 30, 2026"]},
                {"ticker": "MDT", "form": "10-K", "accession": "0001628280-26-044354",
                 "contains": ["last Friday in April"]},
                {"ticker": "NTAP", "form": "10-K", "accession": "0001193125-26-259683",
                 "contains": ["last Friday in April"]}],
}


POINT_FIX = {"EV1R-005": ("approximately 27 percent",
                            "approximately 27 percent | approximately 25% | approximate 25% | approximately 25 percent",
                            ("approximately 27 percent of OpenAI on an as-converted basis",
                             "approximately 27 percent of OpenAI on an as-converted basis at March 31, 2026 (Q3 FY2026 10-Q; "
                             "the FY2026 10-K gives an approximate 25% interest at June 30, 2026)"))}


def build(gold: list[dict]) -> tuple[list[dict], list[dict]]:
    out, changes = [], []
    for q in gold:
        q2, what = copy.deepcopy(q), []
        qid = q["qid"]
        if qid in SIG_FIG_FIX:
            q2["gold"]["min_sig_figs"] = q2["answer"]["min_sig_figs"] = SIG_FIG_FIX[qid]
            what.append(f"min_sig_figs {q['gold']['min_sig_figs']} -> {SIG_FIG_FIX[qid]}")
        if qid in VALUES:
            f = q["fact_values"]
            vals = [{"label": lab, "value": float(fn(f)), "kind": kind, "min_sig_figs": sf} for lab, kind, sf, fn in VALUES[qid]]
            assert any(abs(v["value"] - q["gold"]["value"]) <= 1e-6 * max(1, abs(v["value"])) for v in vals), qid
            q2["gold"]["values"] = vals
            what.append("values: " + "; ".join(f"{v['label']} {v['value'] / M if v['kind'] == 'money' else v['value']:,g}" for v in vals))
        if qid in ROUTE_FIX:
            assert q["route_expected"] == "graph", qid
            q2["route_expected"], q2["route_note"] = "text", ROUTE_FIX[qid]
            what.append("route_expected graph -> text")
        if qid in POINT_FIX:
            old, new, (d_old, d_new) = POINT_FIX[qid]
            rp = q2["answer"]["required_points"]
            assert old in rp and d_old in q2["answer"]["display"], qid
            rp[rp.index(old)] = new
            q2["answer"]["display"] = q2["answer"]["display"].replace(d_old, d_new)
            what.append(f"required point '{old}' -> '{new}'")
        if any(e.get("anchor_source") == "eval_w8_review" for e in q["rag_evidence"]):
            q2["rag_evidence"] = [{**e, "contains": [c]} for e in q["rag_evidence"] for c in dict.fromkeys(e["contains"])]
            what.append(f"anchors split: one evidence item per required point ({len(q2['rag_evidence'])} items)")
        if qid in C1_ANCHORS:
            assert not q["rag_evidence"], qid
            q2["rag_evidence"] = [{"region": "rag_chunks_c1", **e, "anchor_source": "rag_chunks_c1"} for e in C1_ANCHORS[qid]]
            what.append("anchors: " + " | ".join(", ".join(e["contains"]) for e in C1_ANCHORS[qid]))
        if what:
            changes.append({"qid": qid, "question": q["question"], "changes": what})
        out.append(q2)
    return out, changes


def check_anchors(gold: list[dict], chunks_path: Path) -> dict:
    """Every anchor against RAG's chunks with RAG's matcher, restricted to the anchor's own filing."""
    sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))
    from rag.evaluate import evidence_hits
    by_acc: dict[str, list[dict]] = {}
    meta = {}
    with open(chunks_path) as fh:
        for line in fh:
            c = json.loads(line)
            c["accession_number"] = c.get("accession_number") or c["accession"]
            by_acc.setdefault(c["accession"], []).append(c)
            meta.setdefault("chunking_version", c.get("chunking_version"))
    rows, missing = [], []
    for q in gold:
        for i, e in enumerate(q["rag_evidence"]):
            pool = by_acc.get(e.get("accession"), []) if e.get("accession") else [c for cs in by_acc.values() for c in cs]
            hits = [c["chunk_id"] for c in pool if evidence_hits(e, c)]
            rows.append({"qid": q["qid"], "item": i, "accession": e.get("accession"), "n_chunks_matching": len(hits),
                         "chunk_ids": hits[:5], "filing_in_chunks": bool(pool)})
            if not hits:
                missing.append({"qid": q["qid"], "accession": e.get("accession"), "contains": e["contains"],
                                "filing_in_chunks": bool(pool)})
    return {"chunks_file": chunks_path.name, "chunking_version": meta.get("chunking_version"),
            "filings_in_chunks": len(by_acc), "evidence_items": len(rows),
            "items_found": sum(r["n_chunks_matching"] > 0 for r in rows),
            "questions_with_anchors": len({r["qid"] for r in rows}),
            "questions_all_items_found": len({r["qid"] for r in rows} - {m["qid"] for m in missing}),
            "not_found": missing, "items": rows}


def write_list(out: list[dict], h: str):
    """Readable list of v2.2 (data/benchmark_v2_2_questions.md); v2's lists stay as built."""
    md = ["# Gold Set v2.2: ten companies, Data database snapshot of 2026-11-03", "",
          f"{len(out)} questions. Generated by `scripts/build_gold_v2_2.py`; do not edit by hand. File hash `{h}`. Same "
          "questions and expected answers as v2; routes, anchors and grading per `GOLD_SET_V2.md`. 'All figures' lists "
          "what a multi-part question must state (every one).", "",
          "| qid | Company | Type | Route | Question | Expected answer | All figures |", "|---|---|---|---|---|---|---|"]
    for q in out:
        a = q["answer"]["display"].replace("|", "/")
        vals = "; ".join(f"{v['label']}: {v['value'] / M:,.0f}M" if v["kind"] == "money" else f"{v['label']}: {v['value']:g}%"
                         for v in (q.get("gold") or {}).get("values", []))
        md.append(f"| {q['qid']} | {' '.join(q['tickers'])} | {q['type']} | {q['route_expected']} | "
                  f"{q['question'].replace('|', '/')} | {a[:200] + ('...' if len(a) > 200 else '')} | {vals} |")
    (DATA / "benchmark_v2_2_questions.md").write_text("\n".join(md) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", help="RAG's chunks_C1 .jsonl (private; not in the repo)")
    a = ap.parse_args()
    src = DATA / "benchmark_v2_1.jsonl"
    gold = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    out, changes = build(gold)
    text = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in out)
    (DATA / "benchmark_v2_2.jsonl").write_text(text)
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    h21 = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    routes = {}
    for q in out:
        routes[q["route_expected"]] = routes.get(q["route_expected"], 0) + 1
    summary = {"gold_set": "v2.2", "sha256_16": h, "based_on": f"benchmark_v2_1.jsonl ({h21})", "questions": len(out),
               "answerable": sum(q["answerable"] for q in out), "routes": routes,
               "questions_changed": len(changes),
               "sig_fig_floor_lowered": sorted(SIG_FIG_FIX), "multi_value_questions": sorted(VALUES),
               "route_changes": {k: "graph -> text" for k in ROUTE_FIX},
               "required_point_alternatives": sorted(POINT_FIX),
               "anchored_from_rag_chunks_c1": sorted(C1_ANCHORS),
               "anchors_split_one_item_per_point": sorted(q["qid"] for q in gold if any(e.get("anchor_source") == "eval_w8_review" for e in q["rag_evidence"])),
               "questions_without_anchors": [q["qid"] for q in out if q["answerable"] and not q["rag_evidence"]],
               "changes": changes}
    if a.chunks:
        chk = check_anchors(out, Path(a.chunks))
        (RES / "anchor_check_c1.json").write_text(json.dumps(chk, indent=1, ensure_ascii=False))
        summary["anchor_check_c1"] = {k: v for k, v in chk.items() if k not in ("items",)}
        print(f"[gold v2.2] anchors in RAG's chunks: {chk['items_found']}/{chk['evidence_items']} items, "
              f"{chk['questions_all_items_found']}/{chk['questions_with_anchors']} questions; not found: "
              f"{[m['qid'] for m in chk['not_found']]}")
    elif (RES / "anchor_check_c1.json").exists():
        prev = json.loads((RES / "anchor_check_c1.json").read_text())
        summary["anchor_check_c1"] = {k: v for k, v in prev.items() if k not in ("items",)}
    (RES / "gold_v2_2_changes.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    write_list(out, h)
    print(f"[gold v2.2] {len(out)} questions, {len(changes)} changed, routes {routes}, hash {h}")


if __name__ == "__main__":
    main()
