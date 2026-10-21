"""Re-verify every gold fact against the live SEC API (run on a laptop; needs internet).

    SEC_USER_AGENT="Your Name your_email@columbia.edu" python scripts/refresh_gold.py

Exits non-zero if any value, period or accession no longer matches, so a changed or restated
fact can never silently change the benchmark.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = os.environ.get("SEC_USER_AGENT")
if not UA:
    sys.exit("Set SEC_USER_AGENT to 'Name email' (SEC fair-access rule).")

cache: dict[str, dict] = {}
bad = 0
facts = [json.loads(l) for l in open(ROOT / "data" / "gold_facts_v0.jsonl")]
for f in facts:
    url = f["source"]
    if url not in cache:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        cache[url] = json.load(urllib.request.urlopen(req, timeout=30))
        time.sleep(0.15)  # <= 10 requests/second
    rows = cache[url]["units"]["USD"]
    hit = [r for r in rows if r.get("start") == f["period_start"] and r["end"] == f["period_end"] and r["accn"] == f["accession"]]
    if not hit:
        print(f"MISSING  {f['fact_id']}: no fact for {f['period_start']}..{f['period_end']} in {f['accession']}")
        bad += 1
    elif hit[0]["val"] != f["value"]:
        print(f"CHANGED  {f['fact_id']}: gold {f['value']:,} vs SEC {hit[0]['val']:,}")
        bad += 1
    else:
        print(f"ok       {f['fact_id']}: {f['value']:,}")
print(f"\n{len(facts) - bad}/{len(facts)} gold facts verified against data.sec.gov")
sys.exit(1 if bad else 0)
