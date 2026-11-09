"""Spreadsheet version of Gold Set v2 (filterable), for teams that don't read jsonl.

    python scripts/export_gold_v2_xlsx.py   -> data/benchmark_v2_questions.xlsx

Reads data/benchmark_v2.jsonl and data/snapshot_w7.json, so it always matches what the code scores. Do not edit by hand.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NAMES = {"MSFT": "Microsoft", "AAPL": "Apple", "CASY": "Casey's General Stores", "MCK": "McKesson", "MDT": "Medtronic",
         "MU": "Micron Technology", "NKE": "Nike", "NTAP": "NetApp", "PH": "Parker-Hannifin", "TTWO": "Take-Two Interactive"}
ROUTE = {"sql": "Finance data", "text": "Text (RAG)", "graph": "Relationship (GraphRAG)", "multi": "Finance data + text",
         "none": "No tool (scope check)"}
ANSWER = {"exact_numeric": "Exact number", "narrative": "Narrative", "refusal": "Refuse", "false_premise": "Correct premise",
          "exact_categorical": "Exact (text)"}
STATUS = {"auto_verified": "Checked vs SEC data", "verified_twice": "Read twice", "needs_human_review": "Needs human review"}
HEAD = PatternFill("solid", fgColor="2F3E96")
WHITE = Font(bold=True, color="FFFFFF", name="Arial", size=10)
BODY = Font(name="Arial", size=10)


def sheet(ws, header, rows, widths):
    ws.append(header)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in ws[1]:
        c.fill, c.font = HEAD, WHITE
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = BODY
            c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def main():
    raw = (DATA / "benchmark_v2_1.jsonl").read_bytes()
    h = hashlib.sha256(raw).hexdigest()[:16]
    gold = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    snap = json.loads((DATA / "snapshot_w7.json").read_text())
    wb = Workbook()
    ws = wb.active
    ws.title = "Read me"
    lines = [
        f"Gold Set v2.1: {len(gold)} questions ({sum(q['answerable'] for q in gold)} answerable) on the Data team's ten companies",
        f"Generated from data/benchmark_v2_1.jsonl (sha256 {h}) by scripts/export_gold_v2_xlsx.py. Do not edit by hand. "
        "v2.1 is v2 with corrected text anchors (11/9); questions and answers are identical (v2: ed4b42db6fc25ee5).",
        "Scope: the 21 filings in Data's database snapshot of 2026-11-03 (sheet Filings), the same as Data's round-1 freeze list.",
        "Numbers come from SEC XBRL facts, checked against the filings. Exhibit 21 answers were read twice and match GraphRAG's own "
        "Exhibit 21 output on all 62 rows we hold. Amounts are USD millions unless stated.",
        "Route needed = which tool the question needs (Eval's label, for Agents to review). Check status 'Needs human review' marks "
        "text answers still flagged for a person to check against the filing.",
        "Gold Set v1 (100 questions) stays frozen so earlier scores still compare.",
    ]
    for l in lines:
        ws.append([l])
    ws.column_dimensions["A"].width = 150
    ws["A1"].font = Font(bold=True, size=13, name="Arial", color="2F3E96")
    for r in range(2, len(lines) + 1):
        ws.cell(r, 1).font = BODY

    rows = []
    for q in gold:
        accs = sorted({f["accession"] for f in q.get("facts") or [] if f.get("accession")})
        rows.append([q["qid"], ", ".join(q["tickers"]), q["type"].replace("_", " "), q["tier"],
                     ROUTE.get(q["route_expected"], q["route_expected"]), ANSWER.get(q["answer_type"], q["answer_type"]),
                     "yes" if q["answerable"] else "no", q["question"], q["answer"].get("display", ""),
                     "; ".join(q["answer"].get("required_points") or []),
                     " | ".join(c for e in q["rag_evidence"] for c in e["contains"]), ", ".join(accs),
                     q["snapshot_status"].replace("_", " "), STATUS.get(q["status"], q["status"]), q["source"]])
    sheet(wb.create_sheet("Questions"), ["ID", "Companies", "Type", "Tier", "Route needed", "Answer kind", "Answerable",
                                         "Question", "Expected answer", "Must mention", "Text anchors", "Filing accession(s)",
                                         "Snapshot status", "Check status", "Source"],
          rows, [15, 14, 14, 11, 20, 14, 11, 70, 50, 40, 50, 24, 18, 18, 18])

    order = ["MSFT", "AAPL", "CASY", "MCK", "MDT", "MU", "NKE", "NTAP", "PH", "TTWO"]
    routes = ["sql", "text", "graph", "multi", "none"]
    summ = []
    for t in order + ["Across companies"]:
        qs = [q for q in gold if (q["tickers"] == [t] if t in NAMES else len(q["tickers"]) != 1)]
        summ.append([f"{NAMES[t]} ({t})" if t in NAMES else t, len(qs), sum(q["answerable"] for q in qs),
                     *[sum(q["route_expected"] == r for q in qs) for r in routes]])
    summ.append(["All", len(gold), sum(q["answerable"] for q in gold), *[sum(q["route_expected"] == r for q in gold) for r in routes]])
    sheet(wb.create_sheet("By company"), ["Company", "Questions", "Answerable", *[ROUTE[r] for r in routes]], summ,
          [30, 12, 12, 14, 14, 22, 20, 20])

    sheet(wb.create_sheet("Filings"), ["Company", "Ticker", "Form", "Period end", "Accession", "Database status"],
          [[NAMES[f["ticker"]], f["ticker"], f["form"], f["period_end"], f["accession"], f["db_status"]] for f in snap["filings"]],
          [26, 10, 8, 14, 26, 18])
    out = DATA / "benchmark_v2_questions.xlsx"
    wb.save(out)
    print("[xlsx] wrote", out, len(gold), "questions, hash", h)


if __name__ == "__main__":
    main()
