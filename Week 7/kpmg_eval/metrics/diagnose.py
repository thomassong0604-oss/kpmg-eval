"""Week 5. Explain "wrong_value" answers by finding the cell the system actually read.

The Week-4 taxonomy only recognises distractors written into the benchmark. On real retrieval output most wrong
numbers are other genuine facts from the same filing: the right row in the wrong table (segment operating income
instead of consolidated), the right line in the wrong column, a sibling line item. If a wrong answer equals another
XBRL fact in the filing, we can say which part of the key differs from the gold fact:

  wrong_period      same concept and dimensions, different period          (quarter vs nine months, prior year)
  wrong_dimension   same concept and period, different member              (a segment instead of the total, or vice versa)
  wrong_concept     same period and dimensions, different concept          (current portion instead of long-term debt)
  wrong_cell        a fact that differs on two or more of the above        (read an unrelated cell)

Labels refine "wrong_value" only; answers already labelled by the Week-4 grader keep their label.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


class FactIndex:
    def __init__(self, rows: list[dict]):
        self.by_value: dict[float, list[dict]] = defaultdict(list)
        for r in rows:
            try:
                v = float(r["value"])
            except (TypeError, ValueError):
                continue
            if v == 0:
                continue
            self.by_value[round(abs(v), 4)].append(r)

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "FactIndex":
        return cls([json.loads(l) for l in open(path)])

    def lookup(self, value: float) -> list[dict]:
        return self.by_value.get(round(abs(value), 4), [])


def _rel(gold: dict, f: dict) -> str:
    same_c = f["concept"] == gold["concept"]
    same_p = (f.get("start") or None) == (gold.get("period_start") or None) and f["end"] == gold["period_end"]
    same_d = (f.get("dims") or {}) == (gold.get("dims") or {})
    diffs = (not same_c) + (not same_p) + (not same_d)
    if diffs == 0:
        return "same_fact"
    if diffs >= 2:
        return "wrong_cell"
    return "wrong_period" if not same_p else "wrong_dimension" if not same_d else "wrong_concept"


ORDER = ["wrong_period", "wrong_dimension", "wrong_concept", "wrong_cell"]


def diagnose(value: float, gold_key: dict, index: FactIndex) -> dict | None:
    hits = [h for h in index.lookup(value) if h.get("accession", gold_key.get("accession")) == gold_key.get("accession")]
    if not hits:
        return None
    labelled = sorted(((_rel(gold_key, h), h) for h in hits), key=lambda x: ORDER.index(x[0]) if x[0] in ORDER else 9)
    lab, h = labelled[0]
    if lab == "same_fact":
        return None
    return {"label": lab, "matched_concept": h["concept"], "matched_period": [h.get("start"), h["end"]], "matched_dims": h.get("dims") or {}}
