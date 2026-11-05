"""Week 7: routing metrics, so Agents can compare question-based routing with combined retrieval on the same questions
(10/29 KPMG meeting). Tools: sql (Data finance views), text (RAG), graph (GraphRAG).

Each case: {"expected": route_expected, "called": set of tools}.
  route_expected  sql | text | graph | multi (= sql + text) | none (scope gate answers, no tools)
"""
from __future__ import annotations

from collections import Counter

REQUIRED = {"sql": {"sql"}, "text": {"text"}, "graph": {"graph"}, "multi": {"sql", "text"}, "none": set()}


def score_routing(cases: list[dict]) -> dict:
    n = len(cases)
    hit = exact = wasted = calls = 0
    by = Counter()
    by_hit = Counter()
    for c in cases:
        need, got = REQUIRED[c["expected"]], set(c["called"])
        ok = (not got) if not need else need <= got
        hit += ok
        exact += got == need
        wasted += len(got - need)
        calls += len(got)
        by[c["expected"]] += 1
        by_hit[c["expected"]] += ok
    return {
        "n": n,
        "required_tools_called": round(hit / n, 3) if n else None,   # every needed tool was called (none: no tool called)
        "exact_route": round(exact / n, 3) if n else None,            # called exactly the needed tools
        "tool_calls_per_question": round(calls / n, 2) if n else None,
        "unneeded_calls_per_question": round(wasted / n, 2) if n else None,
        "required_tools_called_by_route": {k: round(by_hit[k] / v, 3) for k, v in sorted(by.items())},
    }
