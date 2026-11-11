"""Week 8: send Gold Set v2.2 to the Agents' API v0.2 (`POST /query`) and save the responses for grade_agent_run.py.

    python scripts/run_agent_api.py --base-url http://localhost:8000 --tag agents_v02
    python scripts/run_agent_api.py --base-url ... --tag agents_v02_nofallback --extra '{"disable_fallback": true}'
        -> private/agent_responses_<tag>.jsonl   (git-ignored: evidence holds filing text from Data's corpus)

Each request: {"query": question, "top_k": 10, "trace_id": "<tag>:<qid>"} (+ --extra). top_k 10 matches the rest of
round 1 (the contract's default is 8). The API keeps a given trace_id, so every response maps back to its question.
--only takes a comma-separated list of qids or a case from data/fallback_cases_w8.csv (e.g. --only rescue).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, PRIV = ROOT / "data", ROOT / "private"


def post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--extra", default="{}", help="JSON merged into every request body")
    ap.add_argument("--only", help="qids (comma-separated) or a case name from data/fallback_cases_w8.csv")
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args()
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2_2.jsonl")]
    if a.only:
        cases = {r["qid"]: r["case"] for r in csv.DictReader(open(DATA / "fallback_cases_w8.csv"))}
        keep = set(a.only.split(","))
        gold = [q for q in gold if q["qid"] in keep or cases.get(q["qid"]) in keep]
    PRIV.mkdir(exist_ok=True)
    out = PRIV / f"agent_responses_{a.tag}.jsonl"
    extra = json.loads(a.extra)
    with open(out, "w") as f:
        for q in gold:
            body = {"query": q["question"], "top_k": a.top_k, "trace_id": f"{a.tag}:{q['qid']}", **extra}
            t0 = time.perf_counter()
            try:
                r = post(a.base_url.rstrip("/") + "/query", body, a.timeout)
            except Exception as exc:  # noqa: BLE001 - recorded, graded as ERROR
                r = {"query": q["question"], "trace_id": body["trace_id"], "status": "ERROR", "error": f"client: {exc}"}
            r.update(qid=q["qid"], client_ms=round((time.perf_counter() - t0) * 1000, 1))
            f.write(json.dumps(r) + "\n")
    print(f"[agent api] {len(gold)} questions -> {out}")


if __name__ == "__main__":
    main()
