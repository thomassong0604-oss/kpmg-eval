"""Week 8: which filings a gold question needs, and the filters each GraphRAG arm can actually apply.

Gold Set filters are written in RAG's vocabulary: ticker, form, fiscal_year, fiscal_period (a company's own fiscal
labels). How GraphRAG's two arms treat them:

  KPMG-GraphRAG @ 4e89acb (11/11, round 1 as GraphRAG ran it)
    structured arm  applies ticker, cik, form, accession_number, filing_date, reporting_period_end, concept, segment,
                    basis; accepts and IGNORES fiscal_year, fiscal_period, section, is_table
    graph arm       REFUSES fiscal_year, fiscal_period, is_table (FilterNotSupportedError on 129 of 155 gold questions)
    lists           fail on both: structured raised RetrievalUnavailableError (a DuckDB cast), graph matched nothing
  KPMG-GraphRAG @ 21f0795 (#70, 11/11, current pin)
    both arms build an IN for a list value (an empty list raises ValueError); the graph arm now IGNORES fiscal_year and
    fiscal_period like the structured arm (it still refuses is_table); a bad value raises ValueError, not an outage

GraphRAG confirmed (11/11) that callers, Agents included, should send {ticker, accession_number}. So Eval translates:
one filing -> {ticker, accession_number}; several filings -> the ticker(s) and the list of accessions (an IN on both
arms since #70; before #70 the ticker list was dropped); no gold evidence -> the ticker(s) and the form.
"""
from __future__ import annotations

import json
from pathlib import Path

FISCAL_KEYS = ("fiscal_year", "fiscal_period")
GRAPH_REFUSES = {"is_table"}                       # since #70 (21f0795); at 4e89acb also fiscal_year, fiscal_period
GRAPH_IGNORES = {"fiscal_year", "fiscal_period"}    # since #70
GRAPH_REFUSED_AT_4E89ACB = {"fiscal_year", "fiscal_period", "is_table"}
STRUCTURED_IGNORES = {"fiscal_year", "fiscal_period", "section", "is_table"}


def load_snapshot(path: Path) -> dict[str, dict]:
    return {f["accession"]: f for f in json.loads(Path(path).read_text())["filings"]}


def required_filings(q: dict) -> list[str]:
    """Distinct accessions holding the gold evidence (facts, text anchors, gold evidence). [] for unanswerable."""
    accs = set()
    for f in q.get("facts") or []:
        if f.get("accession"):
            accs.add(f["accession"])
    for e in q.get("rag_evidence") or []:
        if e.get("accession"):
            accs.add(e["accession"])
    for e in (q.get("gold") or {}).get("evidence") or []:
        if isinstance(e, dict) and e.get("accession"):
            accs.add(e["accession"])
    return sorted(accs)


def translate(q: dict, snapshot: dict[str, dict]) -> tuple[dict, str]:
    """-> (filters both GraphRAG arms apply, how they were derived)."""
    accs = [a for a in required_filings(q) if a in snapshot]
    gold = q.get("filters") or {}
    ticker = gold.get("ticker")
    if len(accs) == 1:
        return {"ticker": snapshot[accs[0]]["ticker"], "accession_number": accs[0]}, "one_filing"
    if accs:
        tickers = sorted({snapshot[a]["ticker"] for a in accs})
        return {"ticker": tickers[0] if len(tickers) == 1 else tickers, "accession_number": accs}, "several_filings"
    out = {}
    if ticker:
        out["ticker"] = ticker
    if isinstance(gold.get("form"), str):
        out["form"] = gold["form"]
    return out, "no_gold_evidence"


def compatibility(gold_filters: dict) -> dict:
    """What each GraphRAG arm does with a gold question's filters as written."""
    keys = set(gold_filters)
    lists = sorted(k for k, v in gold_filters.items() if isinstance(v, list))
    return {
        "graph_refuses": sorted(keys & GRAPH_REFUSES),
        "graph_ignores": sorted(keys & GRAPH_IGNORES),
        "graph_refused_at_4e89acb": sorted(keys & GRAPH_REFUSED_AT_4E89ACB),
        "structured_ignores": sorted(keys & STRUCTURED_IGNORES),
        "list_values": lists,
    }
