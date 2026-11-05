"""Week 7: answer / clarify / abstain / off_topic decision metrics (policy: POLICY_answer_clarify_abstain.md).

Each case: {"expected": decision, "predicted": decision, "tool_calls": int, "gate_only": bool}.
  gate_only = the scope check alone should settle the question (no retrieval needed): off-topic, out-of-snapshot company
  or period, forecast, advice, missing company.
"""
from __future__ import annotations

from collections import Counter

DECISIONS = ("answer", "clarify", "abstain", "off_topic")


def decision_of(answer_block: dict) -> str:
    """AnswerBlock -> decision. Uses the optional `decision` field, else answered True/False -> answer/abstain."""
    d = answer_block.get("decision")
    if d in DECISIONS:
        return d
    return "answer" if answer_block.get("answered") else "abstain"


def expected_decision(q: dict) -> str:
    """Gold Set v2 question -> expected decision."""
    if q.get("expected_decision"):
        return q["expected_decision"]
    kind = q["answer"]["kind"]
    if kind == "refusal":
        return "abstain"
    return "answer"  # includes false premises, answered by correcting them


def score_decisions(cases: list[dict]) -> dict:
    n = len(cases)
    conf = Counter((c["expected"], c["predicted"]) for c in cases)
    per = {}
    for d in DECISIONS:
        tot = sum(v for (e, _), v in conf.items() if e == d)
        per[d] = {"n": tot, "recall": round(conf[(d, d)] / tot, 3) if tot else None}
    not_answer = [c for c in cases if c["expected"] != "answer"]
    answer = [c for c in cases if c["expected"] == "answer"]
    off = [c for c in cases if c["expected"] == "off_topic"]
    gate = [c for c in cases if c.get("gate_only")]
    return {
        "n": n,
        "decision_accuracy": round(sum(conf[(d, d)] for d in DECISIONS) / n, 3) if n else None,
        "unsafe_answer_rate": round(sum(c["predicted"] == "answer" for c in not_answer) / len(not_answer), 3) if not_answer else None,
        "over_refusal_rate": round(sum(c["predicted"] != "answer" for c in answer) / len(answer), 3) if answer else None,
        "off_topic_tool_calls": sum(c.get("tool_calls", 0) for c in off),
        "off_topic_questions_with_tool_calls": sum(c.get("tool_calls", 0) > 0 for c in off),
        "gate_violations": sum(c.get("tool_calls", 0) > 0 for c in gate),
        "per_decision": per,
        "confusion": {f"{e}->{p}": v for (e, p), v in sorted(conf.items())},
    }
