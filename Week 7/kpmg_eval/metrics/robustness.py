"""Week 5. Retrieval robustness to how the question is worded (spec'd in Week 4 as "position & length robustness").

Each benchmark question is re-asked in deterministic variants that a real user produces:

  filing_wording   the benchmark question as written (states company, period and line item)
  no_period        period phrase removed ("for the three months ended March 31, 2026") -> tests whether
                   retrieval still lands on the statement table, which holds all four period columns
  analyst          short analyst phrasing, e.g. "MSFT Q3 FY26 op income?" (ticker + fiscal label, no line-item name)

For each variant: evidence_recall@k and the overlap of the top-k chunk ids with the original (Jaccard@k).
A retriever whose recall drops when wording changes needs query rewriting in the Agent, not a bigger index.
"""
from __future__ import annotations

import re

PERIOD_RE = re.compile(
    r",?\s*(for|in|during|as of|from)?\s*(the\s+)?(three|nine|six)[- ]months? ended [A-Z][a-z]+ \d{1,2},? \d{4}(\s+and\s+\d{4})?"
    r"|,?\s*as of [A-Z][a-z]+ \d{1,2},? \d{4}", re.I)


def strip_period(q: str) -> str:
    out = PERIOD_RE.sub("", q)
    return re.sub(r"\s+([,?.])", r"\1", re.sub(r"\s{2,}", " ", out)).strip()


def jaccard_at_k(a: list[str], b: list[str], k: int) -> float:
    sa, sb = set(a[:k]), set(b[:k])
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0
