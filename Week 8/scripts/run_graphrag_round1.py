"""Week 8: round 1 for GraphRAG's real tools on Gold Set v2.2 (both arms, every question).

GraphRAG asked (reply of 11/11) for Part A to be re-run with their graph arm in, now that `graphrag.backends` is real.
Eval cannot reach their Neo4j Aura instance or EDGAR from its workspace, so this script is written to run anywhere:

    # GraphRAG (or anyone with the Aura credentials and the 20-filing store):
    export NEO4J_URI=... NEO4J_USERNAME=... NEO4J_PASSWORD=... NEO4J_DATABASE=...
    export MSFT_FACT_DB_PATH=/path/to/store.duckdb        # tools/build_fact_store.py or fact_loader_data_api.py
    python scripts/run_graphrag_round1.py --graphrag /path/to/KPMG-GraphRAG --tag graphrag_aura

    # Eval, here: structured arm only, on the Microsoft 10-Q store built from Data's copy (no network)
    python scripts/run_graphrag_round1.py --tag eval_local

Writes results/graphrag_round1_<tag>.json and results/graphrag_round1_<tag>.csv. No LLM; same scoring as
run_side_by_side.py and RAG's round-1 run:
  needed_in_evidence   numbers: every input value in the top k (structured: a returned fact with that value; graph:
                       the figure as printed in a returned claim); prose: every gold text anchor in the top k
  strict               ... and the matching evidence comes from a filing the question needs
  top1_right / top1_wrong_period   structured arm, number questions: the rank-1 fact is the needed value / a known
                       wrong-period value for the same line item (GraphRAG's "period matcher" point)
  returned_nothing     on unanswerable questions
Each question runs twice per arm: filters as written in the gold set ("gold") and translated to what the arm applies
("translated", kpmg_eval/graphrag_filters.py). Errors are recorded per call, not raised, so a refused filter shows up
as a count instead of stopping the run.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from kpmg_eval.graphrag_adapter import backend_status, load_tools  # noqa: E402
from kpmg_eval.graphrag_filters import compatibility, load_snapshot, required_filings, translate  # noqa: E402
import run_side_by_side as sbs  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
K = 10


def store_contents() -> tuple[set[str], set[str]] | None:
    """(accessions, tickers) in the structured store, so questions on filings it does not hold are skipped, not scored."""
    path = os.environ.get("MSFT_FACT_DB_PATH")
    if not path or not Path(path).exists():
        return None
    import duckdb
    con = duckdb.connect(path, read_only=True)
    try:
        rows = con.execute("SELECT DISTINCT accession_number, ticker FROM financial_facts_v1").fetchall()
        return {r[0] for r in rows}, {r[1] for r in rows}
    finally:
        con.close()


# Dropped connections are the database host's, not the arm's (GraphRAG, 11/11: Aura's free tier drops connections
# mid-run; EV3-007 hit "Failed to read from defunct connection" and succeeded on retry). Retried, and if they persist
# reported as infra errors, never scored as an arm failure. (Errored calls never enter a rate's denominator either.)
TRANSIENT = ("defunct connection", "serviceunavailable", "sessionexpired", "connection reset", "connection refused",
             "connection closed", "timed out")


def is_transient(msg: str) -> bool:
    return any(t in msg.lower() for t in TRANSIENT)


def store_meta() -> dict | None:
    """File name and store_meta_v1 of the structured store (no local path, so results can be shared)."""
    path = os.environ.get("MSFT_FACT_DB_PATH")
    if not path or not Path(path).exists():
        return None
    import duckdb
    con = duckdb.connect(path, read_only=True)
    try:
        meta = dict(con.execute("SELECT key, value FROM store_meta_v1").fetchall()) if con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'store_meta_v1'").fetchone()[0] else {}
        n = con.execute("SELECT count(*), count(DISTINCT accession_number) FROM financial_facts_v1").fetchone()
    finally:
        con.close()
    return {"file": Path(path).name, **meta, "facts": n[0], "filings": n[1]}


def public_status(status: dict) -> dict:
    """backend_status without hosts or local paths: results files get shared and committed."""
    return {k: (str(v).split(":")[0] if str(v).startswith("registered") else v) for k, v in status.items()}


def _git(path: Path) -> str | None:
    import subprocess
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def score(q: dict, arm: str, ev: list[dict], need_accs: set[str]) -> dict:
    kind = sbs.kind(q)
    out = {"n_returned": len(ev)}
    if kind == "unanswerable_or_false_premise":
        out["returned_nothing"] = len(ev) == 0
        return out
    in_need = [e for e in ev if e.get("accession_number") in need_accs]
    if arm == "structured":
        out.update({f"{k}": v for k, v in sbs.score_gr(q, ev).items() if k != "n_returned"})
        out["strict"] = bool(out.get("needed_in_evidence")) and sbs.score_gr(q, in_need).get("needed_in_evidence") is True
        if kind == "number" and ev:
            top = ev[0]["metadata"].get("value_num")
            need = sbs.needed_values(q)
            dist = [d["value"] for d in (q.get("gold") or {}).get("distractors", []) if d.get("value")]
            out["top1_right"] = top is not None and any(sbs.same(top, n) for n in need)
            out["top1_wrong_period"] = top is not None and any(sbs.same(top, d) for d in dist) if dist else None
    else:
        texts = [e.get("text") or "" for e in ev]
        out.update({k: v for k, v in sbs.score_rag(q, texts).items() if k != "n_returned"})
        strict = sbs.score_rag(q, [e.get("text") or "" for e in in_need]).get("needed_in_evidence")
        out["strict"] = bool(out.get("needed_in_evidence")) and strict is True
    return out


def rate(rows, key):
    xs = [r[key] for r in rows if r.get(key) is not None]
    return {"rate": round(sum(xs) / len(xs), 3) if xs else None, "hits": sum(xs), "n": len(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graphrag", default=str(ROOT / "upstream" / "KPMG-GraphRAG"))
    ap.add_argument("--gold", default=str(DATA / "benchmark_v2_2.jsonl"))
    ap.add_argument("--tag", default="eval_local")
    ap.add_argument("--k", type=int, default=K)
    ap.add_argument("--retries", type=int, default=3, help="attempts per call when the database drops the connection")
    args = ap.parse_args()
    if "MSFT_FACT_DB_PATH" not in os.environ and (ROOT / "upstream" / "graphrag_store_msft_10q.duckdb").exists():
        os.environ["MSFT_FACT_DB_PATH"] = str(ROOT / "upstream" / "graphrag_store_msft_10q.duckdb")
    status = backend_status(Path(args.graphrag))
    graph_search, structured_search = load_tools(Path(args.graphrag), mock=False)
    arms = {"graph": graph_search, "structured": structured_search}
    live = {a for a in arms if str(status.get(a, "")).startswith("registered")}
    gold = [json.loads(l) for l in open(args.gold)]
    snap = load_snapshot(DATA / "snapshot_w7.json")
    store = store_contents()

    rows, compat = [], Counter()
    for q in gold:
        need = set(required_filings(q))
        c = compatibility(q["filters"])
        compat["graph_refuses_gold_filters"] += bool(c["graph_refuses"])
        compat["graph_ignores_some_gold_filters"] += bool(c["graph_ignores"])
        compat["graph_refused_gold_filters_at_4e89acb"] += bool(c["graph_refused_at_4e89acb"])
        compat["structured_ignores_some_gold_filters"] += bool(c["structured_ignores"])
        compat["list_valued_filters"] += bool(c["list_values"])
        tr, how = translate(q, snap)
        compat[f"translation_{how}"] += 1
        for arm in sorted(live):
            covered = None
            if arm == "structured" and store is not None:
                tickers = q["tickers"] or []
                covered = need <= store[0] if need else bool(tickers) and set(tickers) <= store[1]
            for mode, filters in (("gold", q["filters"]), ("translated", tr)):
                base = {"qid": q["qid"], "arm": arm, "filters_mode": mode, "kind": sbs.kind(q), "type": q["type"],
                        "route_expected": q["route_expected"], "required_filings": len(need), "translation": how,
                        "filing_in_store": covered, "filters": json.dumps(filters)}
                t0, attempt = time.perf_counter(), 0
                while True:
                    attempt += 1
                    try:
                        ev = arms[arm](q["question"], filters=filters, top_k=args.k,
                                       trace_id=f"{args.tag}:{q['qid']}:{arm}:{mode}")
                        rows.append({**base, "error": None, "error_class": None, "attempts": attempt,
                                     **score(q, arm, ev, need), "ms": round((time.perf_counter() - t0) * 1000, 1)})
                        break
                    except Exception as exc:  # noqa: BLE001 - recorded per call
                        msg = f"{type(exc).__name__}: {str(exc)[:160]}"
                        if is_transient(msg) and attempt < args.retries:
                            time.sleep(attempt)
                            continue
                        rows.append({**base, "error": msg, "error_class": "infra" if is_transient(msg) else "arm",
                                     "attempts": attempt, "n_returned": 0,
                                     "ms": round((time.perf_counter() - t0) * 1000, 1)})
                        break

    summary = {}
    for arm in sorted(live):
        for mode in ("gold", "translated"):
            rs = [r for r in rows if r["arm"] == arm and r["filters_mode"] == mode]
            scored = [r for r in rs if r["filing_in_store"] is not False]   # skip questions whose filing is not loaded
            ans = [r for r in scored if r["kind"] != "unanswerable_or_false_premise" and not r["error"]]
            summary[f"{arm}|{mode}"] = {
                "calls": len(rs), "errors": sum(bool(r["error"]) and r.get("error_class") != "infra" for r in rs),
                "infra_errors": sum(r.get("error_class") == "infra" for r in rs),
                "retried_calls": sum((r.get("attempts") or 1) > 1 for r in rs),
                "error_types": dict(Counter(r["error"].split(":")[0] for r in rs if r["error"])),
                "skipped_filing_not_in_store": sum(r["filing_in_store"] is False for r in rs),
                "numbers": rate([r for r in ans if r["kind"] == "number"], "needed_in_evidence"),
                "numbers_strict": rate([r for r in ans if r["kind"] == "number"], "strict"),
                "prose": rate([r for r in ans if r["kind"] == "prose"], "needed_in_evidence"),
                "top1_right": rate(ans, "top1_right"), "top1_wrong_period": rate(ans, "top1_wrong_period"),
                "returned_nothing_on_unanswerable": rate([r for r in scored if r["kind"] == "unanswerable_or_false_premise"
                                                          and not r["error"]], "returned_nothing"),
            }
    out = {"_doc": __doc__.strip().splitlines()[0], "tag": args.tag, "k": args.k, "gold": Path(args.gold).name,
           "graphrag_commit": _git(Path(args.graphrag)), "store": store_meta(),
           "backend_status": public_status(status), "arms_run": sorted(live),
           "store_filings": sorted(store[0]) if store else None,
           "filter_compatibility_of_gold_filters": dict(compat), "summary": summary}
    RES.mkdir(exist_ok=True)
    (RES / f"graphrag_round1_{args.tag}.json").write_text(json.dumps(out, indent=1))
    with open(RES / f"graphrag_round1_{args.tag}.csv", "w", newline="") as f:
        cols = ["qid", "arm", "filters_mode", "kind", "type", "route_expected", "required_filings", "translation",
                "filing_in_store", "error", "error_class", "attempts", "needed_in_evidence", "strict", "distractor_shown", "top1_right",
                "top1_wrong_period", "returned_nothing", "n_returned", "ms", "filters"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"status": public_status(status), "compat": dict(compat), "summary": summary}, indent=1))


if __name__ == "__main__":
    main()
