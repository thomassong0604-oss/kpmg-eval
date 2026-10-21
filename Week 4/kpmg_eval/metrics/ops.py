"""Run-to-run consistency (RRC) and operations metrics (latency, tool-call errors, cost).

RRC precedent: repeated-sampling stability studies; Operations: FinToolBench / Finance Agent Benchmark.
Both read the trace log the Agent team writes (one JSON line per tool call, see answer_schema.TRACE_FIELDS).
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from ..normalize import extract_quantities
from .refusal import classify_response


def _canonical(resp) -> tuple:
    """What must stay identical across runs: the decision and the headline number."""
    decision = classify_response(resp)
    if isinstance(resp, dict):
        v = resp.get("value")
        return (decision, None if v is None else round(float(v), 2))
    qs = [q for q in extract_quantities(resp or "") if q.kind in ("money", "percent", "pp")]
    return (decision, round(qs[0].value, 2) if qs else None)


def run_to_run_consistency(runs_by_qid: dict[str, list]) -> dict:
    """runs_by_qid: {qid: [response_run1, response_run2, ...]} -> share of questions where all runs agree."""
    per_q = {}
    for qid, runs in runs_by_qid.items():
        canon = [_canonical(r) for r in runs]
        modal = max(set(canon), key=canon.count)
        per_q[qid] = {"consistent": len(set(canon)) == 1, "agreement": canon.count(modal) / len(canon)}
    n = len(per_q)
    return {"rrc": sum(v["consistent"] for v in per_q.values()) / n if n else None,
            "mean_agreement": sum(v["agreement"] for v in per_q.values()) / n if n else None,
            "inconsistent_qids": [q for q, v in per_q.items() if not v["consistent"]]}


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def ops_metrics(trace_rows: list[dict]) -> dict:
    """trace_rows: one per tool call: {trace_id, tool, latency_ms, status, prompt_tokens, completion_tokens, cost_usd}"""
    by_trace = defaultdict(list)
    for r in trace_rows:
        by_trace[r["trace_id"]].append(r)
    e2e = [sum(r.get("latency_ms", 0) for r in rows) for rows in by_trace.values()]
    calls = len(trace_rows)
    errors = sum(r.get("status", "ok") != "ok" for r in trace_rows)
    costs = [sum((r.get("cost_usd") or 0) for r in rows) for rows in by_trace.values()]
    by_tool = defaultdict(list)
    for r in trace_rows:
        by_tool[r["tool"]].append(r.get("latency_ms", 0))
    return {
        "n_queries": len(by_trace), "n_tool_calls": calls,
        "latency_p50_ms": _pct(e2e, 0.5), "latency_p95_ms": _pct(e2e, 0.95),
        "tool_call_error_rate": errors / calls if calls else None,
        "cost_per_query_usd": statistics.mean(costs) if costs else None,
        "latency_by_tool_p50_ms": {t: _pct(v, 0.5) for t, v in by_tool.items()},
    }
