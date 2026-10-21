"""Build gold facts + benchmark v0 from SEC XBRL facts (pilot companies of the RAG repo + Apple).

Values were read from the SEC companyconcept API (data.sec.gov/api/xbrl/companyconcept/...) on 2026-10-14
and each was confirmed by a second, accession-filtered read. `scripts/refresh_gold.py` re-pulls the API
on any laptop and fails loudly if a value changed.
All money values in USD (base units). Expected answers are COMPUTED here, never typed.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
M = 1_000_000

COMPANIES = {
    "JPM": ("0000019617", "JPMorgan Chase & Co."),
    "BAC": ("0000070858", "Bank of America Corp."),
    "C": ("0000831001", "Citigroup Inc."),
    "CAT": ("0000018230", "Caterpillar Inc."),
    "DE": ("0000315189", "Deere & Company"),
    "HON": ("0000773840", "Honeywell International Inc."),
    "AAPL": ("0000320193", "Apple Inc."),
}

# (fact_id, ticker, concept, start, end, value_in_millions, accession, form, fy, fp)
F = [
    ("JPM_NI_FY25", "JPM", "NetIncomeLoss", "2025-01-01", "2025-12-31", 57048, "0001628280-26-008131", "10-K", 2025, "FY"),
    ("JPM_NI_FY24", "JPM", "NetIncomeLoss", "2024-01-01", "2024-12-31", 58471, "0001628280-26-008131", "10-K", 2025, "FY"),
    ("JPM_NI_Q2_26", "JPM", "NetIncomeLoss", "2026-04-01", "2026-06-30", 21155, "0001628280-26-054343", "10-Q", 2026, "Q2"),
    ("JPM_NI_Q2_25", "JPM", "NetIncomeLoss", "2025-04-01", "2025-06-30", 14987, "0001628280-26-054343", "10-Q", 2026, "Q2"),
    ("JPM_NI_H1_26", "JPM", "NetIncomeLoss", "2026-01-01", "2026-06-30", 37649, "0001628280-26-054343", "10-Q", 2026, "Q2"),
    ("BAC_NI_FY25", "BAC", "NetIncomeLoss", "2025-01-01", "2025-12-31", 30509, "0000070858-26-000157", "10-K", 2025, "FY"),
    ("BAC_NI_FY24", "BAC", "NetIncomeLoss", "2024-01-01", "2024-12-31", 26973, "0000070858-26-000157", "10-K", 2025, "FY"),
    ("BAC_NI_Q2_26", "BAC", "NetIncomeLoss", "2026-04-01", "2026-06-30", 9074, "0000070858-26-000394", "10-Q", 2026, "Q2"),
    ("BAC_NI_Q2_25", "BAC", "NetIncomeLoss", "2025-04-01", "2025-06-30", 7170, "0000070858-26-000394", "10-Q", 2026, "Q2"),
    ("BAC_NI_H1_26", "BAC", "NetIncomeLoss", "2026-01-01", "2026-06-30", 17658, "0000070858-26-000394", "10-Q", 2026, "Q2"),
    ("C_NI_FY25", "C", "NetIncomeLoss", "2025-01-01", "2025-12-31", 14306, "0000831001-26-000011", "10-K", 2025, "FY"),
    ("C_PL_FY25", "C", "ProfitLoss", "2025-01-01", "2025-12-31", 14452, "0000831001-26-000011", "10-K", 2025, "FY"),
    ("C_NI_FY24", "C", "NetIncomeLoss", "2024-01-01", "2024-12-31", 12682, "0000831001-26-000011", "10-K", 2025, "FY"),
    ("CAT_PL_FY25", "CAT", "ProfitLoss", "2025-01-01", "2025-12-31", 8882, "0000018230-26-000008", "10-K", 2025, "FY"),
    ("CAT_PL_Q2_26", "CAT", "ProfitLoss", "2026-04-01", "2026-06-30", 3593, "0000018230-26-000046", "10-Q", 2026, "Q2"),
    ("DE_NI_FY25", "DE", "NetIncomeLoss", "2024-10-28", "2025-11-02", 5027, "0001104659-25-122321", "10-K", 2025, "FY"),
    ("DE_NI_FY24", "DE", "NetIncomeLoss", "2023-10-30", "2024-10-27", 7100, "0001104659-25-122321", "10-K", 2025, "FY"),
    ("DE_NI_Q3_26", "DE", "NetIncomeLoss", "2026-05-04", "2026-08-02", 1379, "0001104659-26-102213", "10-Q", 2026, "Q3"),
    ("DE_NI_Q3_25", "DE", "NetIncomeLoss", "2025-04-28", "2025-07-27", 1289, "0001104659-26-102213", "10-Q", 2026, "Q3"),
    ("DE_NI_9M_26", "DE", "NetIncomeLoss", "2025-11-03", "2026-08-02", 3808, "0001104659-26-102213", "10-Q", 2026, "Q3"),
    ("HON_NI_FY25", "HON", "NetIncomeLoss", "2025-01-01", "2025-12-31", 4729, "0000773840-26-000013", "10-K", 2025, "FY"),
    ("HON_NI_FY24", "HON", "NetIncomeLoss", "2024-01-01", "2024-12-31", 5705, "0000773840-26-000013", "10-K", 2025, "FY"),
    ("HON_NI_Q4_25", "HON", "NetIncomeLoss", "2025-10-01", "2025-12-31", -115, "0000773840-26-000013", "10-K", 2025, "FY"),
    ("HON_NI_Q2_26", "HON", "NetIncomeLoss", "2026-04-01", "2026-06-30", 5682, "0000773840-26-000124", "10-Q", 2026, "Q2"),
    ("HON_NI_Q2_25", "HON", "NetIncomeLoss", "2025-04-01", "2025-06-30", 1570, "0000773840-26-000124", "10-Q", 2026, "Q2"),
    ("HON_NI_H1_26", "HON", "NetIncomeLoss", "2026-01-01", "2026-06-30", 6503, "0000773840-26-000124", "10-Q", 2026, "Q2"),
    # Apple Q3 FY26 10-Q, from the filing's income statement (R2.htm) and XBRL NetIncomeLoss
    ("AAPL_NS_Q3_26", "AAPL", "RevenueFromContractWithCustomerExcludingAssessedTax", "2026-03-29", "2026-06-27", 109417, "0000320193-26-000020", "10-Q", 2026, "Q3"),
    ("AAPL_NS_Q3_25", "AAPL", "RevenueFromContractWithCustomerExcludingAssessedTax", "2025-03-30", "2025-06-28", 94036, "0000320193-26-000020", "10-Q", 2026, "Q3"),
    ("AAPL_NS_9M_26", "AAPL", "RevenueFromContractWithCustomerExcludingAssessedTax", "2025-09-28", "2026-06-27", 364357, "0000320193-26-000020", "10-Q", 2026, "Q3"),
    ("AAPL_NI_Q3_26", "AAPL", "NetIncomeLoss", "2026-03-29", "2026-06-27", 29789, "0000320193-26-000020", "10-Q", 2026, "Q3"),
    ("AAPL_NI_9M_26", "AAPL", "NetIncomeLoss", "2025-09-28", "2026-06-27", 101464, "0000320193-26-000020", "10-Q", 2026, "Q3"),
    ("AAPL_NI_9M_25", "AAPL", "NetIncomeLoss", "2024-09-29", "2025-06-28", 84544, "0000320193-26-000020", "10-Q", 2026, "Q3"),
]

facts = {}
for fid, t, concept, s, e, v, acc, form, fy, fp in F:
    cik, name = COMPANIES[t]
    facts[fid] = {"fact_id": fid, "ticker": t, "cik": cik, "company": name, "concept": f"us-gaap:{concept}",
                  "period_start": s, "period_end": e, "unit": "USD", "value": v * M, "accession": acc,
                  "form": form, "fy": fy, "fp": fp, "source": API.format(cik=cik, concept=concept)}


def key(fid: str) -> dict:
    f = facts[fid]
    return {"cik": f["cik"], "accession": f["accession"], "concept": f["concept"], "period_start": f["period_start"],
            "period_end": f["period_end"], "unit": "USD", "ticker": f["ticker"], "level": "FACT"}


def path(fid: str) -> list[list[str]]:
    """GraphRAG gold path: Company -FILED-> Filing -REPORTS-> Fact (ids are CIK / accession / fact key)."""
    f = facts[fid]
    fact_node = f"{f['cik']}|{f['concept']}|{f['period_start']}|{f['period_end']}|USD"
    return [[f["cik"], "FILED", f["accession"]], [f["accession"], "REPORTS", fact_node]]


def val(fid):
    return facts[fid]["value"]


def d(label, fid=None, value=None, note=""):
    return {"label": label, "value": value if value is not None else val(fid), "note": note or (fid or "")}


items = []


def add(qid, qtype, tier, question, value, evidence, distractors=(), kind="money", paths=(), note=""):
    items.append({"qid": qid, "type": qtype, "tier": tier, "question": question, "answerable": True,
                  "gold": {"value": value, "kind": kind, "min_sig_figs": 3, "evidence": evidence,
                           "distractors": list(distractors)},
                  "graph_paths": list(paths), "notes": note})


def add_unans(qid, question, why, near=None):
    items.append({"qid": qid, "type": "unanswerable", "tier": "hard", "question": question, "answerable": False,
                  "gold": {"expected_behavior": "abstain", "why": why, "nearest_disclosed": near}, "graph_paths": [], "notes": ""})


# ---- 1. Financial information extraction (single filing, single fact) ----
ext = [
    ("E01", "JPM_NI_FY25", "What was JPMorgan Chase's net income for fiscal year 2025?", ["JPM_NI_FY24"]),
    ("E02", "JPM_NI_Q2_26", "What was JPMorgan Chase's net income for the three months ended June 30, 2026?", ["JPM_NI_H1_26", "JPM_NI_Q2_25"]),
    ("E03", "BAC_NI_FY25", "What was Bank of America's net income for fiscal year 2025?", ["BAC_NI_FY24"]),
    ("E04", "BAC_NI_Q2_26", "What was Bank of America's net income in the second quarter of 2026?", ["BAC_NI_H1_26", "BAC_NI_Q2_25"]),
    ("E05", "C_NI_FY25", "What net income attributable to Citigroup did Citi report for 2025?", ["C_NI_FY24"]),
    ("E06", "CAT_PL_FY25", "What was Caterpillar's profit (including noncontrolling interests) for 2025?", []),
    ("E07", "CAT_PL_Q2_26", "What was Caterpillar's profit for the quarter ended June 30, 2026?", []),
    ("E08", "DE_NI_FY25", "What was Deere's net income for fiscal 2025 (year ended November 2, 2025)?", ["DE_NI_FY24"]),
    ("E09", "DE_NI_Q3_26", "What was Deere's net income for the three months ended August 2, 2026?", ["DE_NI_9M_26", "DE_NI_Q3_25"]),
    ("E10", "HON_NI_FY25", "What was Honeywell's net income for 2025?", ["HON_NI_FY24"]),
    ("E11", "HON_NI_Q2_26", "What was Honeywell's net income in Q2 2026?", ["HON_NI_H1_26", "HON_NI_Q2_25"]),
    ("E12", "AAPL_NS_Q3_26", "What were Apple's total net sales for the three months ended June 27, 2026?", ["AAPL_NS_9M_26", "AAPL_NS_Q3_25"]),
    ("E13", "AAPL_NI_Q3_26", "What was Apple's net income for its fiscal third quarter of 2026?", ["AAPL_NI_9M_26"]),
]
for qid, fid, q, dist in ext:
    extra = [d("wrong_concept", "C_PL_FY25", note="ProfitLoss includes noncontrolling interests")] if fid == "C_NI_FY25" else []
    add(qid, "extraction", "basic", q, val(fid), [key(fid)], [d("wrong_period", x) for x in dist] + extra, paths=[path(fid)])

# ---- 2. Period traps: year-to-date vs quarter (10-Q specific) ----
for qid, fid, q, dist in [
    ("P01", "JPM_NI_H1_26", "What was JPMorgan Chase's year-to-date net income in its Q2 2026 10-Q?", ["JPM_NI_Q2_26"]),
    ("P02", "BAC_NI_H1_26", "What was Bank of America's net income for the first six months of 2026?", ["BAC_NI_Q2_26"]),
    ("P03", "DE_NI_9M_26", "What was Deere's net income for the first nine months of fiscal 2026?", ["DE_NI_Q3_26"]),
    ("P04", "HON_NI_H1_26", "What was Honeywell's net income for the six months ended June 30, 2026?", ["HON_NI_Q2_26"]),
    ("P05", "AAPL_NI_9M_26", "What was Apple's year-to-date net income as reported in its fiscal Q3 2026 10-Q?", ["AAPL_NI_Q3_26", "AAPL_NI_9M_25"]),
]:
    add(qid, "extraction", "medium", q, val(fid), [key(fid)], [d("wrong_period", x) for x in dist], paths=[path(fid)])

# ---- 3. Comparison & reconciliation (multi-company or multi-concept) ----
add("C01", "comparison", "medium", "By how much did JPMorgan Chase's 2025 net income exceed Bank of America's?",
    val("JPM_NI_FY25") - val("BAC_NI_FY25"), [key("JPM_NI_FY25"), key("BAC_NI_FY25")],
    [d("wrong_period", value=val("JPM_NI_Q2_26") - val("BAC_NI_Q2_26"), note="Q2 2026 gap")],
    paths=[path("JPM_NI_FY25"), path("BAC_NI_FY25")])
add("C02", "comparison", "medium", "What was the combined 2025 net income of JPMorgan Chase, Bank of America and Citigroup?",
    val("JPM_NI_FY25") + val("BAC_NI_FY25") + val("C_NI_FY25"), [key("JPM_NI_FY25"), key("BAC_NI_FY25"), key("C_NI_FY25")],
    [d("wrong_concept", value=val("JPM_NI_FY25") + val("BAC_NI_FY25") + val("C_PL_FY25"), note="used Citi ProfitLoss")],
    paths=[path("JPM_NI_FY25"), path("BAC_NI_FY25"), path("C_NI_FY25")])
add("C03", "reconciliation", "hard", "Citigroup's 2025 10-K reports net income attributable to Citigroup and total net income including noncontrolling interests. What is the difference between them?",
    val("C_PL_FY25") - val("C_NI_FY25"), [key("C_NI_FY25"), key("C_PL_FY25")], [],
    paths=[path("C_NI_FY25"), path("C_PL_FY25")], note="Tests concept disambiguation: same company, same period, two concepts")
add("C04", "comparison", "medium", "How much larger was Caterpillar's 2025 profit than Deere's fiscal 2025 net income?",
    val("CAT_PL_FY25") - val("DE_NI_FY25"), [key("CAT_PL_FY25"), key("DE_NI_FY25")], [],
    paths=[path("CAT_PL_FY25"), path("DE_NI_FY25")], note="Different fiscal year ends (Dec 31 vs Nov 2): answer should flag it")

# ---- 4. Temporal / cross-period (two facts, same company) ----
def yoy(qid, cur, prev, q, pct=False):
    c, p = val(cur), val(prev)
    v = round((c - p) / abs(p) * 100, 1) if pct else c - p
    add(qid, "temporal", "hard", q, v, [key(cur), key(prev)],
        [d("wrong_sign", value=-v)], kind="percent" if pct else "money", paths=[path(cur), path(prev)])

yoy("T01", "JPM_NI_Q2_26", "JPM_NI_Q2_25", "By what percentage did JPMorgan Chase's Q2 2026 net income change from Q2 2025?", pct=True)
yoy("T02", "BAC_NI_Q2_26", "BAC_NI_Q2_25", "By how many dollars did Bank of America's Q2 2026 net income increase versus Q2 2025?")
yoy("T03", "DE_NI_Q3_26", "DE_NI_Q3_25", "By what percentage did Deere's fiscal Q3 2026 net income change from fiscal Q3 2025?", pct=True)
yoy("T04", "HON_NI_FY25", "HON_NI_FY24", "By what percentage did Honeywell's net income change from 2024 to 2025?", pct=True)
yoy("T05", "AAPL_NS_Q3_26", "AAPL_NS_Q3_25", "By what percentage did Apple's net sales grow in the June 2026 quarter versus a year earlier?", pct=True)
add("T06", "temporal", "hard", "What was Honeywell's net income in the fourth quarter of 2025?", val("HON_NI_Q4_25"),
    [key("HON_NI_Q4_25")], [d("wrong_sign", value=-val("HON_NI_Q4_25"), note="loss reported as profit")], paths=[path("HON_NI_Q4_25")],
    note="Negative value: tests sign handling")

# ---- 5. Unanswerable: the corpus does not contain the answer ----
add_unans("U01", "How many iPhones did Apple sell in the three months ended June 27, 2026?",
          "Apple reports net sales by category in dollars, not unit volumes.", "iPhone net sales in USD")
add_unans("U02", "What was JPMorgan Chase's full-year 2026 net income?", "Fiscal 2026 had not ended; no 10-K exists in the corpus.",
          "Six-month 2026 net income from the Q2 10-Q")
add_unans("U03", "What was Deere's net income for fiscal Q4 2026?", "No filing in the corpus covers that period yet.",
          "Fiscal Q3 2026 net income")
add_unans("U04", "What will Caterpillar's profit be in 2027?", "Filings report historical results; a forecast figure is not a disclosed fact.", None)
add_unans("U05", "What was Bank of America's net income for 2026 in its 10-K?", "No 2026 10-K exists in the corpus.", "First-half 2026 net income")

out = ROOT / "data"
out.mkdir(exist_ok=True)
with open(out / "gold_facts_v0.jsonl", "w") as fh:
    for f in facts.values():
        fh.write(json.dumps(f) + "\n")
with open(out / "benchmark_v0.jsonl", "w") as fh:
    for it in items:
        fh.write(json.dumps(it) + "\n")

# Gold graph fixture for the GraphRAG team: the nodes and edges a correct graph must contain for these filings.
nodes, edges = {}, set()
for f in facts.values():
    nodes[f["cik"]] = {"id": f["cik"], "label": "Company", "ticker": f["ticker"], "name": f["company"]}
    nodes[f["accession"]] = {"id": f["accession"], "label": "Filing", "form": f["form"], "fy": f["fy"], "fp": f["fp"], "cik": f["cik"]}
    fn = f"{f['cik']}|{f['concept']}|{f['period_start']}|{f['period_end']}|USD"
    nodes[fn] = {"id": fn, "label": "Fact", "cik": f["cik"], "concept": f["concept"], "period_start": f["period_start"],
                 "period_end": f["period_end"], "unit": "USD", "value": f["value"], "accession": f["accession"]}
    edges.add((f["cik"], "FILED", f["accession"]))
    edges.add((f["accession"], "REPORTS", fn))
(out / "gold_graph_v0.json").write_text(json.dumps({"nodes": list(nodes.values()), "edges": sorted(edges)}, indent=1))

print(f"{len(facts)} gold facts, {len(items)} benchmark items, {len(nodes)} graph nodes, {len(edges)} edges")
from collections import Counter
print(Counter(i["type"] for i in items))
