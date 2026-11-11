"""Week 8: which filings a gold question needs, and the filters each GraphRAG arm can actually apply.

Gold Set filters are written in RAG's vocabulary: ticker, form, fiscal_year, fiscal_period (a company's own fiscal
labels). GraphRAG's two arms treat those keys differently (KPMG-GraphRAG @ 4e89acb, 2026-11-11):

  structured arm  accepts all 13 contract keys; applies ticker, cik, form, accession_number, filing_date,
                  reporting_period_end, concept, segment, basis; accepts and IGNORES fiscal_year, fiscal_period,
                  section, is_table (structured/structured_query_v1.py IGNORED_FILTERS)
  graph arm       REFUSES fiscal_year, fiscal_period and is_table (graphrag/graph_backend.py _UNSUPPORTED_FILTERS)

Neither arm handles a list value (13 cross-company questions filter on a list of tickers): the structured arm
raises RetrievalUnavailableError from DuckDB, the graph arm compares a string to a list and returns nothing.

So Eval translates instead of passing the fiscal labels: when the gold evidence sits in one filing, both arms get
{ticker, accession_number}, which both apply and which is exactly what "strict" scoring checks. When the evidence
spans several filings, they get the ticker (or nothing, for a list) and the form if all filings share it, and the
row records that the search was wider than the question.
"""
from __future__ import annotations

import json
from pathlib import Path

FISCAL_KEYS = ("fiscal_year", "fiscal_period")
GRAPH_REFUSES = {"fiscal_year", "fiscal_period", "is_table"}
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
    out = {}
    if isinstance(ticker, str):
        out["ticker"] = ticker
    forms = {snapshot[a]["form"] for a in accs} or ({gold["form"]} if isinstance(gold.get("form"), str) else set())
    if len(forms) == 1:
        out["form"] = forms.pop()
    how = "several_filings" if accs else "no_gold_evidence"
    if isinstance(ticker, list):
        how += "_ticker_list_dropped"
    return out, how


def compatibility(gold_filters: dict) -> dict:
    """What each GraphRAG arm does with a gold question's filters as written."""
    keys = set(gold_filters)
    lists = sorted(k for k, v in gold_filters.items() if isinstance(v, list))
    return {
        "graph_refuses": sorted(keys & GRAPH_REFUSES),
        "structured_ignores": sorted(keys & STRUCTURED_IGNORES),
        "list_values": lists,
    }
