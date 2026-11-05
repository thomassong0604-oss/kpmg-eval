"""Week 5. Reasoning-step accuracy (was "spec only" in Week 4). Deterministic, no LLM judge.

The Agent returns its calculation as steps in the AnswerBlock (see answer_schema.CALC_STEPS_SCHEMA):

    "steps": [
      {"id": "s1", "op": "lookup", "concept": "us-gaap:OperatingIncomeLoss", "period_start": "2026-01-01",
       "period_end": "2026-03-31", "value": 38398000000},
      {"id": "s2", "op": "lookup", "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", ...},
      {"id": "s3", "op": "divide", "args": ["s1", "s2"], "value": 0.4633}
    ]

Scored against the benchmark's gold `facts` (EvalKeys + values):

  input_recall       share of gold input facts the steps looked up with the right key AND value
  input_precision    share of looked-up facts that are gold inputs (extra facts are not wrong, just noisy)
  arithmetic_valid   share of compute steps whose stated value equals op(args) (rel. tol 5e-4)
  final_correct      last step's value matches the gold answer
  first_error        the first failing step and why: wrong_fact_value | wrong_period | wrong_concept |
                     bad_arithmetic | unknown_arg | none

This separates "used the wrong number" (retrieval/extraction) from "did the math wrong" (reasoning), which the final
answer alone cannot.
"""
from __future__ import annotations

import math

OPS = {
    "add": lambda xs: sum(xs),
    "subtract": lambda xs: xs[0] - sum(xs[1:]),
    "multiply": lambda xs: math.prod(xs),
    "divide": lambda xs: xs[0] / xs[1] if xs[1] else float("nan"),
    "pct_change": lambda xs: xs[0] / xs[1] - 1 if xs[1] else float("nan"),
    "negate": lambda xs: -xs[0],
}


def _close(a: float, b: float, rel: float = 5e-4) -> bool:
    return abs(a - b) <= rel * max(abs(b), 1e-12)


def _same_key(step: dict, fact: dict) -> bool:
    return (step.get("concept") == fact.get("concept") and step.get("period_end") == fact.get("period_end")
            and (step.get("period_start") or None) == (fact.get("period_start") or None)
            and (step.get("dims") or None) == (fact.get("dims") or None))


def score_steps(gold_facts: list[dict], gold_values: list[float], gold_answer: float | None, steps: list[dict]) -> dict:
    vals: dict[str, float] = {}
    lookups = [s for s in steps if s.get("op") == "lookup"]
    matched_gold = set()
    first_error = None
    for s in steps:
        if s.get("op") == "lookup":
            vals[s["id"]] = float(s["value"])
            hit = next((i for i, f in enumerate(gold_facts) if _same_key(s, f)), None)
            if hit is not None:
                if _close(float(s["value"]), gold_values[hit]):
                    matched_gold.add(hit)
                elif first_error is None:
                    first_error = {"step": s["id"], "reason": "wrong_fact_value"}
            elif first_error is None:
                same_concept = any(s.get("concept") == f.get("concept") for f in gold_facts)
                first_error = {"step": s["id"], "reason": "wrong_period" if same_concept else "wrong_concept"}
        else:
            args = s.get("args", [])
            if any(a not in vals for a in args) or s.get("op") not in OPS:
                first_error = first_error or {"step": s.get("id"), "reason": "unknown_arg"}
                vals[s.get("id")] = float(s.get("value", float("nan")))
                continue
            expect = OPS[s["op"]]([vals[a] for a in args])
            vals[s["id"]] = float(s["value"])
            if not _close(float(s["value"]), expect) and first_error is None:
                first_error = {"step": s["id"], "reason": "bad_arithmetic", "expected": expect}
    computes = [s for s in steps if s.get("op") != "lookup"]
    arith_ok = sum(1 for s in computes if all(a in vals for a in s.get("args", [])) and s.get("op") in OPS
                   and _close(float(s["value"]), OPS[s["op"]]([vals[a] for a in s["args"]])))
    final = float(steps[-1]["value"]) if steps else None
    return {
        "input_recall": len(matched_gold) / len(gold_facts) if gold_facts else None,
        "input_precision": (sum(any(_same_key(s, f) for f in gold_facts) for s in lookups) / len(lookups)) if lookups else None,
        "arithmetic_valid": arith_ok / len(computes) if computes else None,
        "final_correct": (final is not None and gold_answer is not None and _close(final, gold_answer, 5e-3)),
        "first_error": first_error or {"step": None, "reason": "none"},
    }
