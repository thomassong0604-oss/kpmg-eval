"""Week 6: Eval's review of RAG's draft evidence anchors for Gold Set v1 (RAG PR #10, 10/28, "pending Eval review").

    python scripts/review_rag_gold_v1_anchors.py [data/upstream_snapshots/rag_gold_v1_6f0894a.jsonl]
      -> results/rag_gold_v1_anchor_review.json

Reads RAG's eval/gold_v1.jsonl as data (snapshot at RAG commit 6f0894a; none of RAG's code is run) and checks:
  1. coverage   every question Eval wrote is there, and nothing else
  2. inputs     for numeric questions, every number the gold answer is computed from appears in a chunk that one of the
                question's anchors matches (anchors locate evidence; the number itself need not be in the anchor string)
  3. matching   each anchor against Eval's copy of the 10-Q as RAG chunks it (data/rag_chunks_msft_10q.jsonl), with
                RAG's own rule (all `contains` strings, case-insensitive): no_match, ok (1-3 chunks), broad (>3)
  4. scope      questions retired by the 10-company scope (AMZN/META/NVDA) that RAG should drop
  5. filters    questions whose filters stop at ticker + form (Week 5: those also search Microsoft's other 10-Q)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
MSFT_10Q = "0001193125-26-191507"


def shown(v: float, concept: str = "") -> set[str]:
    """How the filing can print a value: '82,886' (USD millions), per-share '4.27' / '0.91', rates '20%'."""
    if "TaxRate" in concept or concept.endswith("Rate") or "Percent" in concept:
        return {f"{abs(v) * 100:.0f}%", f"{abs(v) * 100:.1f}%"}
    if abs(v) < 1000:
        return {f"{abs(v):.2f}"}
    m = abs(v) / 1e6
    s = f"{m:,.0f}" if abs(m - round(m)) < 1e-9 else f"{m:,.1f}"
    return {s, f"({s})", f"( {s})"}


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "upstream_snapshots" / "rag_gold_v1_6f0894a.jsonl"
    rag = {r["qid"]: r for r in map(json.loads, open(src))}
    ours = {q["qid"]: q for q in map(json.loads, open(DATA / "benchmark_v1.jsonl"))}
    status = {r["qid"]: r for r in (dict(zip(["qid", "type", "tickers", "status", "reason"], l.rstrip("\n").split(",", 4)))
                                    for l in list(open(DATA / "benchmark_scope10_status.csv"))[1:])}
    chunks = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl")]
    low = [" ".join(c["text"].split()).lower() for c in chunks]

    out = {"source": str(src.relative_to(ROOT)), "coverage": {}, "inputs": [], "matching": Counter(), "match_detail": [],
           "retired_in_rag_file": [], "filters_ticker_form_only": 0}
    out["coverage"] = {"eval_questions": len(ours), "rag_rows": len(rag), "missing_in_rag": sorted(set(ours) - set(rag)),
                       "extra_in_rag": sorted(set(rag) - set(ours))}
    for qid, q in ours.items():
        r = rag.get(qid)
        if r is None:
            continue
        ev = r["gold"]["evidence"]
        # text of every chunk the question's anchors match (RAG's rule)
        hit_text = " | ".join(t for e in ev if e.get("contains")
                              for t in low if all(" ".join(x.split()).lower() in t for x in e["contains"]))
        if status.get(qid, {}).get("status") == "retired":
            out["retired_in_rag_file"].append(qid)
        f = r.get("filters") or {}
        if set(f) <= {"ticker", "form"}:
            out["filters_ticker_form_only"] += 1
        # 2. inputs: numbers the answer is computed from (MSFT 10-Q facts only; peers are out of scope)
        if q["answer_type"] == "exact_numeric" and q["corpus"] == "msft_10q_q3fy26" and q["fact_values"]:
            need = {k: v for k, v in q["fact_values"].items()}
            missing = [k for k, v in need.items() if not any(x.lower() in hit_text for x in shown(v, k.split('|')[0]))]
            out["inputs"].append({"qid": qid, "n_inputs": len(need), "missing": missing})
        # 3. matching against the 10-Q as RAG chunks it
        for e in ev:
            if e.get("accession") != MSFT_10Q or not e.get("contains"):
                continue
            cs = [" ".join(s.split()).lower() for s in e["contains"]]
            n = sum(all(s in t for s in cs) for t in low)
            st = "ok" if 1 <= n <= 3 else ("broad" if n > 3 else "no_match")
            out["matching"][st] += 1
            if st != "ok":
                out["match_detail"].append({"qid": qid, "contains": e["contains"], "n_chunks": n, "status": st})
    inp = out["inputs"]
    out["summary"] = {
        "coverage": f"{len(ours) - len(out['coverage']['missing_in_rag'])}/{len(ours)} Eval questions present",
        "numeric_questions_with_all_inputs_anchored": f"{sum(not x['missing'] for x in inp)}/{len(inp)}",
        "inputs_in_anchored_chunks": f"{sum(x['n_inputs'] - len(x['missing']) for x in inp)}/{sum(x['n_inputs'] for x in inp)}",
        "anchors_vs_chunks": dict(out["matching"]),
        "retired_questions_still_in_rag_file": len(out["retired_in_rag_file"]),
        "rows_with_ticker_form_filters_only": out["filters_ticker_form_only"],
    }
    out["matching"] = dict(out["matching"])
    RES.mkdir(exist_ok=True)
    (RES / "rag_gold_v1_anchor_review.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))
    for x in inp:
        if x["missing"]:
            print("  inputs not anchored:", x["qid"], x["missing"])
    for x in out["match_detail"]:
        print("  anchor", x["status"], x["qid"], x["contains"], x["n_chunks"])


if __name__ == "__main__" and "--fixes" not in sys.argv:
    main()


# ---------------------------------------------------------------- Week 7: concrete fixes to send back to RAG
STOP = {"what", "was", "were", "the", "for", "and", "in", "of", "to", "a", "its", "microsoft", "microsoft's", "usd", "millions",
        "three", "months", "ended", "march", "31", "2026", "nine", "how", "much", "did", "state", "amount", "s"}


def _row_label_anchor(value: str, question: str, chunks: list[dict], n_match) -> list[str] | None:
    """Bare number in several tables -> [row label, number] from the chunk whose row label best matches the question.
    The row label is the text just before the number in RAG's table rendering ('| Total revenue | $82,886 |')."""
    import re as _re
    qwords = {w for w in _re.findall(r"[a-z]+", question.lower()) if w not in STOP and len(w) > 2}
    best = None
    for c in chunks:
        t = " ".join(c["text"].split())
        for m in _re.finditer(_re.escape(value), t):
            pre = t[max(0, m.start() - 80):m.start()]
            seg = _re.split(r"\|", pre)
            label = next((x.strip(" $") for x in reversed(seg) if _re.search(r"[A-Za-z]{3}", x)), "")
            label = _re.sub(r"\s+", " ", label).strip()
            if not label or len(label) > 60:
                continue
            overlap = len(qwords & set(_re.findall(r"[a-z]+", label.lower())))
            if overlap == 0:
                continue
            n = n_match([label, value])
            if 1 <= n <= 3:
                key = (-overlap, n, len(label))
                if best is None or key < best[0]:
                    best = (key, [label, value])
    return best[1] if best else None

def fixes(src: Path | None = None) -> list[dict]:
    """One row per anchor RAG should change: the 2 that match no chunk and the broad ones (4+ chunks). The suggestion is
    Eval's own anchor for that question when it matches 1-3 chunks of the same 10-Q (RAG's matching rule); else a row
    label to add. Plus the 10 retired questions to drop (they answer RAG's AMZN/META question)."""
    import csv as _csv
    src = src or DATA / "upstream_snapshots" / "rag_gold_v1_6f0894a.jsonl"
    rag = {r["qid"]: r for r in map(json.loads, open(src))}
    ours = {q["qid"]: q for q in map(json.loads, open(DATA / "benchmark_v1.jsonl"))}
    status = {r["qid"]: r for r in _csv.DictReader(open(DATA / "benchmark_scope10_status.csv"))}
    chunks = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl")]
    low = [" ".join(c["text"].split()).lower() for c in chunks]

    def n_match(cs):
        cs = [" ".join(x.split()).lower() for x in cs]
        return sum(all(x in t for x in cs) for t in low)

    rows = []
    for qid, r in rag.items():
        if status.get(qid, {}).get("status") == "retired":
            rows.append({"qid": qid, "action": "drop", "rag_anchor": "", "rag_n_chunks": "", "suggested_anchor": "",
                         "suggested_n_chunks": "", "why": status[qid]["reason"] + " (scope is now Data's 10 companies)"})
            continue
        for e in r["gold"]["evidence"]:
            if e.get("accession") != MSFT_10Q or not e.get("contains"):
                continue
            n = n_match(e["contains"])
            if 1 <= n <= 3:
                continue
            if n == 0:
                others = [x for x in r["gold"]["evidence"] if x is not e and x.get("contains") and n_match(x["contains"]) >= 1]
                rows.append({"qid": qid, "action": "remove", "rag_anchor": " | ".join(e["contains"]), "rag_n_chunks": 0,
                             "suggested_anchor": "", "suggested_n_chunks": "",
                             "why": f"matches no chunk; a share-count string carried over from Gold v0 that is not evidence for "
                                    f"this question ({len(others)} other anchors remain)"})
                continue
            vals = [v for v in e["contains"] if any(ch.isdigit() for ch in v)]
            # Eval's own anchor for the same number(s), if it is specific enough
            cands = [x["contains"] for x in ours[qid]["rag_evidence"] if x.get("contains") and 1 <= n_match(x["contains"]) <= 3
                     and vals and all(v in x["contains"] for v in vals)]
            sug = cands[0] if cands else None
            if not sug and vals:
                lab = _row_label_anchor(vals[0], ours[qid]["question"], chunks, n_match)
                if lab and 1 <= n_match([lab[0]] + vals) <= 3:
                    sug = [lab[0]] + vals
            rows.append({"qid": qid, "action": "narrow", "rag_anchor": " | ".join(e["contains"]),
                         "rag_n_chunks": n, "suggested_anchor": " | ".join(sug) if sug else "add the table row label",
                         "suggested_n_chunks": n_match(sug) if sug else "",
                         "why": f"value appears in {n} chunks (several tables)"})
    with open(RES / "rag_anchor_fixes.csv", "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["qid", "action", "rag_anchor", "rag_n_chunks", "suggested_anchor",
                                           "suggested_n_chunks", "why"])
        w.writeheader()
        w.writerows(rows)
    c = Counter(r["action"] for r in rows)
    fixed = sum(1 for r in rows if r["action"] == "narrow" and r["suggested_n_chunks"] not in ("", None))
    print(f"[rag-fixes] {dict(c)}; {fixed} of {c['narrow']} broad anchors get a 1-3 chunk replacement")
    return rows


if __name__ == "__main__" and "--fixes" in sys.argv:
    fixes()
