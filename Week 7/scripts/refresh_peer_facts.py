"""Re-pull comparison-company facts from the SEC API after a ticker swap in config/scope.json.

    SEC_USER_AGENT="Name email" python scripts/refresh_peer_facts.py          # writes data/peer_facts_v1.jsonl
    python scripts/refresh_peer_facts.py --check                              # offline: config vs existing facts

For every peer: revenue, operating income and net income for the comparison frame (default CY2026Q1, i.e. the fiscal
quarter that ends in March/April 2026), from https://data.sec.gov/api/xbrl/companyconcept/. Each value is read twice:
once from the frame-tagged entry and once by accession + period from the full list; the two must agree or the script
stops. Microsoft's 10-K rows are kept as they are. Needs a network that allows data.sec.gov (it is blocked in the
cloud sandbox this was built in, so the committed file was produced with the same logic through a fetch tool).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config" / "scope.json").read_text())
OUT = ROOT / "data" / "peer_facts_v1.jsonl"
URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{c}.json"
CONCEPTS = {"REV": None, "OI": "OperatingIncomeLoss", "NI": "NetIncomeLoss"}


def get(url: str, ua: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        time.sleep(0.15)  # SEC fair access: <= 10 requests/second
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="offline: verify every configured peer has its 3 facts")
    a = ap.parse_args()
    frame = CFG["comparison_frame"]
    tag = frame.replace("20", "", 1)  # CY2026Q1 -> CY26Q1
    existing = {r["fact_id"]: r for r in map(json.loads, open(OUT))} if OUT.exists() else {}
    if a.check:
        missing = [f"{p['ticker']}_{k}_{tag}" for p in CFG["peers"] for k in CONCEPTS if f"{p['ticker']}_{k}_{tag}" not in existing]
        print("[refresh] config peers:", [p["ticker"] for p in CFG["peers"]], "| missing facts:", missing or "none")
        sys.exit(1 if missing else 0)
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        sys.exit("Set SEC_USER_AGENT='Your Name your@email' (SEC requires a contact in the User-Agent)")
    rows = [r for r in existing.values() if r["ticker"] == CFG["mvp"]["ticker"]]
    for p in CFG["peers"]:
        for lab, concept in CONCEPTS.items():
            concept = concept or p["revenue_concept"]
            data = get(URL.format(cik=p["cik"], c=concept), ua)
            usd = data["units"]["USD"]
            tagged = [e for e in usd if e.get("frame") == frame and e["form"] == "10-Q"]
            if len(tagged) != 1:
                sys.exit(f"{p['ticker']} {concept}: expected 1 entry with frame {frame}, found {len(tagged)}")
            e = tagged[0]
            again = [x for x in usd if x["accn"] == e["accn"] and x["start"] == e["start"] and x["end"] == e["end"]]
            if {x["val"] for x in again} != {e["val"]}:
                sys.exit(f"{p['ticker']} {concept}: second read disagrees {[x['val'] for x in again]}")
            rows.append({"fact_id": f"{p['ticker']}_{lab}_{tag}", "ticker": p["ticker"], "cik": p["cik"], "company": data["entityName"],
                         "concept": f"us-gaap:{concept}", "period_start": e["start"], "period_end": e["end"], "unit": "USD",
                         "value": e["val"], "accession": e["accn"], "form": e["form"], "fy": e["fy"], "fp": e["fp"], "frame": frame,
                         "source": URL.format(cik=p["cik"], c=concept),
                         "verification": f"frame-tagged entry and accession/period entries agree ({time.strftime('%Y-%m-%d')})"})
            print(f"[refresh] {p['ticker']:5s} {lab}: {e['val']:,} ({e['accn']}, {e['start']}..{e['end']})")
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[refresh] wrote {len(rows)} facts -> {OUT}. Now run scripts/run_all.sh")


if __name__ == "__main__":
    main()
