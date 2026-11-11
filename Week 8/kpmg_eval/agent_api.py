"""Week 8: read the Agents' API v0.2 `/query` responses into Eval's records.

Contract: "KPMG Agentic Backbone - API Contract v0.2" (Agents, 11/11; branch feature/api-integration-v02, PR #10).
v0.2 returns no answer yet (`answer: null`), so Eval scores it at the evidence and decision level:

  trace_id            -> qid. Eval sends trace_id = "<run tag>:<qid>"; the API preserves a given trace_id
  status              -> decision: SUCCESS = answer, NO_EVIDENCE = abstain, ERROR = not scored (listed apart)
  evidence_status, weak_reasons, fallback_triggered, fallback_used -> the fallback analysis
  filters             -> query understanding, compared key by key with the gold filters (same vocabulary)
  evidence[].text     -> is the needed figure / text anchor in the final evidence (same rule as the side by side)
  citations[].source_url -> accession (from the EDGAR path), checked against the filings the gold answer uses
  logs, error         -> kept for tracing; not scored
"""
from __future__ import annotations

import re

STATUSES = ("SUCCESS", "NO_EVIDENCE", "ERROR")
_ACC = re.compile(r"/edgar/data/\d+/(\d{10})(\d{2})(\d{6})(?:/|$)")


def accession_from_url(url: str | None) -> str | None:
    """https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm -> 0001193125-26-191507"""
    m = _ACC.search(url or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def qid_of(resp: dict, gold_by_qid: dict, gold_by_question: dict) -> str | None:
    """Explicit qid, else the suffix of trace_id ("<tag>:<qid>"), else the exact question text."""
    if resp.get("qid") in gold_by_qid:
        return resp["qid"]
    tail = str(resp.get("trace_id") or "").rsplit(":", 1)[-1]
    if tail in gold_by_qid:
        return tail
    return gold_by_question.get((resp.get("query") or "").strip())


def decision(resp: dict) -> str:
    s = resp.get("status")
    return {"SUCCESS": "answer", "NO_EVIDENCE": "abstain"}.get(s, "error")


def observed_case(resp: dict) -> str:
    """The Agents' four cases (11/11), read off one response."""
    es, trig = resp.get("evidence_status"), bool(resp.get("fallback_triggered"))
    if es == "empty" and trig:
        return "1_empty_to_graphrag"
    if es == "weak" and trig:
        return "2_weak_to_graphrag"
    if es == "ok" and resp.get("status") == "NO_EVIDENCE":
        return "3_ok_but_no_evidence"
    if es in ("empty", "weak") and not trig:
        return "weak_or_empty_no_fallback"
    return "rag_only" if es == "ok" else "other"


def filters_match(pred: dict | None, gold: dict | None) -> dict:
    """Per gold key: did query understanding produce the same value? (lists compared as sets)"""
    pred, gold = pred or {}, gold or {}
    out = {}
    for k, v in gold.items():
        p = pred.get(k)
        if isinstance(v, list) or isinstance(p, list):
            out[k] = set(v if isinstance(v, list) else [v]) == set(p if isinstance(p, list) else [p] if p is not None else [])
        else:
            out[k] = p is not None and str(p).upper() == str(v).upper()
    return out
