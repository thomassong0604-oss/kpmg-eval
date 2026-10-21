"""Week 5. Filter accuracy: does a question get the right metadata filters, and do those filters keep the right filings?

RAG's retrieve() applies filters BEFORE ranking (Retrieval API v0 §3), so a wrong filter is silent and total: the
evidence is never ranked. Three measurements:

  score_filters(pred, gold)        per-key accuracy against the benchmark's gold filters
                                   (correct / wrong / missing per key, exact match, extra keys)
  filing_filter_pr(filters, ...)   filter precision and recall at FILING level over a candidate pool:
                                   recall    = share of the question's gold filings the filter keeps (must be 1.0)
                                   precision = share of kept filings that are gold (low = distractor filings survive)
  extract_filters(question, scope) a rule-based question -> filters baseline (company names, dates, fiscal labels),
                                   the floor for the Agent's own filter extraction

Matching follows RAG's contract: lists mean OR within a key, keys are ANDed, a key absent from the filter is ignored.
"""
from __future__ import annotations

import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
DATE_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})", re.I)
FISCAL_RE = re.compile(r"fiscal\s+(?:q([1-4])\s+(\d{4})|(\d{4})\s+q([1-4])|year\s+(\d{4}))|\bq([1-4])\s+(\d{4})\b", re.I)
OUT_OF_CORPUS = {"tesla": "TSLA", "oracle": "ORCL", "salesforce": "CRM", "ibm": "IBM", "intel": "INTC", "adobe": "ADBE",
                 "alphabet": "GOOGL", "google": "GOOGL", "netflix": "NFLX", "cisco": "CSCO"}


def _as_set(v):
    return set(v) if isinstance(v, (list, tuple, set)) else {v}


def matches(filters: dict, meta: dict) -> bool:
    for k, want in (filters or {}).items():
        if want is None:
            continue
        have = meta.get(k)
        if have is None or str(have).upper() not in {str(w).upper() for w in _as_set(want)}:
            return False
    return True


def score_filters(pred: dict, gold: dict, keys=("ticker", "form", "fiscal_year", "fiscal_period")) -> dict:
    out = {"per_key": {}, "extra_keys": sorted(k for k in pred if k not in gold)}
    for k in keys:
        if k not in gold:
            continue
        if k not in pred:
            out["per_key"][k] = "missing"
        else:
            out["per_key"][k] = "correct" if {str(x).upper() for x in _as_set(pred[k])} == {str(x).upper() for x in _as_set(gold[k])} else "wrong"
    vals = list(out["per_key"].values())
    out["exact_match"] = bool(vals) and all(v == "correct" for v in vals) and not out["extra_keys"]
    out["any_wrong"] = "wrong" in vals
    return out


def filing_filter_pr(filters: dict, pool: list[dict], gold_accessions: set[str]) -> dict:
    kept = [f for f in pool if matches(filters, f)]
    gold_in_pool = [f for f in pool if f["accession"] in gold_accessions]
    tp = sum(1 for f in kept if f["accession"] in gold_accessions)
    return {"kept": len(kept), "gold_in_pool": len(gold_in_pool),
            "recall": tp / len(gold_in_pool) if gold_in_pool else None,
            "precision": tp / len(kept) if kept else None}


def extract_filters(question: str, scope: dict, fiscal_label, session_ticker: str | None = None) -> dict:
    """Rule-based baseline. Company names -> ticker; the latest date in the question -> fiscal year/period via RAG's
    fiscal_label() with the company's fiscal-year end; explicit 'fiscal Q1 2027' wins over dates.
    session_ticker: the company the UI session is scoped to (single-company MVP). Used only when the question names none."""
    q = question.lower()
    companies = {scope["mvp"]["name"].lower(): scope["mvp"], scope["mvp"]["ticker"].lower(): scope["mvp"]}
    for p in scope["peers"]:
        companies[p["name"].lower()] = p
        companies[p["ticker"].lower()] = p
    found = []
    for name, c in companies.items():
        if re.search(rf"\b{re.escape(name)}\b", q) and c["ticker"] not in found:
            found.append(c["ticker"])
    for name, t in OUT_OF_CORPUS.items():
        if re.search(rf"\b{name}\b", q) and t not in found:
            found.append(t)
    out: dict = {}
    if not found and session_ticker:
        found = [session_ticker]
    if not found:
        return out
    out["ticker"] = found[0] if len(found) == 1 else found
    multi = len(found) > 1
    has_10k = bool(re.search(r"\b10-k\b|annual report", q))
    has_10q = bool(re.search(r"\b10-q\b|three months|nine months|six months|quarter", q))
    if has_10k and not has_10q:
        out["form"] = "10-K"
    elif has_10q and not has_10k:
        out["form"] = "10-Q"
    if multi or (has_10k and has_10q):
        return out  # different fiscal calendars or two documents: fiscal filters would exclude a gold filing
    fye = next((c["fye"] for c in [scope["mvp"], *scope["peers"]] if c["ticker"] == found[0]), "1231")
    m = FISCAL_RE.search(question)
    if m:
        g = m.groups()
        if g[0]:
            out["fiscal_period"], out["fiscal_year"] = f"Q{g[0]}", int(g[1])
        elif g[2]:
            out["fiscal_year"], out["fiscal_period"] = int(g[2]), f"Q{g[3]}"
        elif g[4]:
            out["fiscal_year"] = int(g[4])
        elif g[5]:
            out["fiscal_period"], out["fiscal_year"] = f"Q{g[5]}", int(g[6])
        return out
    dates = [date(int(y), MONTHS[mn.lower()], int(d)) for mn, d, y in DATE_RE.findall(question)]
    if dates:
        end = max(dates).isoformat()
        form = out.get("form", "10-Q")
        fy, fp = fiscal_label(end, fye, form)
        if form == "10-Q" and end[5:] == f"{fye[:2]}-{fye[2:]}":
            fp = "FY"  # a quarter that ends on the fiscal-year end is reported in the 10-K
        out["fiscal_year"], out["fiscal_period"] = fy, fp
    return out
