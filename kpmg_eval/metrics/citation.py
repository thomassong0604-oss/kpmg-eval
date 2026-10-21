"""Metric B (code-checkable half): Claim-level citation support. Precedents: ALCE, Ragas faithfulness.

The numeric half of faithfulness needs no LLM: every number in a claim must appear in a passage the
claim cites. Narrative claims ("driven by Azure growth") go to a calibrated LLM judge, out of scope here.

  citation_validity   share of citations that point to evidence actually retrieved in this trace
                      (catches fabricated or stale chunk ids)
  numeric_support     share of numeric claims whose every number appears in at least one cited passage
  citation_recall     share of gold evidence items cited by the answer
"""
from __future__ import annotations

from ..normalize import extract_quantities


def _numbers(text: str) -> list:
    return [q for q in extract_quantities(text) if q.kind in ("money", "percent", "pp") or abs(q.value) >= 10]


def number_supported(q, passage: str) -> bool:
    for p in extract_quantities(passage):
        if (p.kind in ("percent", "pp")) != (q.kind in ("percent", "pp")):
            continue
        # compare at the precision the claim was written with
        if q.kind in ("percent", "pp"):
            if round(p.value, q.decimals) == round(q.value, q.decimals):
                return True
        else:
            for scale in (1.0, 1e3, 1e6, 1e9):  # filings state tables "in millions"
                if round(p.value * scale / q.scale, q.decimals) == round(q.value / q.scale, q.decimals):
                    return True
    return False


def score_citations(claims: list[dict], retrieved: dict[str, str], gold_ids: set[str] | None = None) -> dict:
    """claims: [{"text": str, "cites": [chunk_id, ...]}]; retrieved: {chunk_id: text} for this trace."""
    all_cites = [c for cl in claims for c in cl.get("cites", [])]
    valid = [c for c in all_cites if c in retrieved]
    numeric_claims = supported = 0
    unsupported: list[str] = []
    for cl in claims:
        nums = _numbers(cl["text"])
        if not nums:
            continue
        numeric_claims += 1
        passages = [retrieved[c] for c in cl.get("cites", []) if c in retrieved]
        if passages and all(any(number_supported(q, p) for p in passages) for q in nums):
            supported += 1
        else:
            unsupported.append(cl["text"])
    out = {
        "citation_validity": len(valid) / len(all_cites) if all_cites else None,
        "numeric_support": supported / numeric_claims if numeric_claims else None,
        "unsupported_claims": unsupported,
    }
    if gold_ids:
        out["citation_recall"] = len(gold_ids & set(all_cites)) / len(gold_ids)
    return out
