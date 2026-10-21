"""Retrieval metrics, identical for VectorRAG and GraphRAG.

Both arms return ranked evidence; each piece of evidence is converted to an EvalKey
(RAG: EvalKey.from_rag_chunk, GraphRAG: EvalKey.from_graph_fact) and judged against the gold
evidence items. Gold is written as keys + optional required text, never as chunk ids, so the gold set
survives re-chunking and works for graph nodes that have no chunk id at all.

  hit@k              any relevant item in the top k
  evidence_recall@k  share of the question's distinct evidence items covered by the top k
                     (a 3-company comparison needs 3 items; finding 1 of 3 = 0.33)
  mrr                1 / rank of the first relevant item
  ndcg@k             graded: grade 2 = satisfies an evidence item, 1 = right filing but not the evidence,
                     0 = otherwise. Rewards ranking the exact passage above merely same-filing text.
  provenance@k       share of the top k from an expected company (catches cross-company leakage)
"""
from __future__ import annotations

import math
from typing import Callable

from ..keys import EvalKey, Level, matches


def evidence_satisfied(ev: dict, key: EvalKey, text: str) -> bool:
    gold_key = EvalKey(**{k: v for k, v in ev.items() if k in EvalKey.__dataclass_fields__})
    level = Level[ev["level"]] if "level" in ev else gold_key.level
    if not matches(key, gold_key, level):
        return False
    low = text.lower()
    return all(s.lower() in low for s in ev.get("contains", []))


def grade(item_gold: list[dict], key: EvalKey, text: str) -> int:
    if any(evidence_satisfied(ev, key, text) for ev in item_gold):
        return 2
    for ev in item_gold:
        g = EvalKey(cik=ev.get("cik"), accession=ev.get("accession"))
        if g.accession and matches(key, g, Level.FILING):
            return 1
    return 0


def score_retrieval(gold_evidence: list[dict], ranked: list[tuple[EvalKey, str]], ks=(1, 3, 5),
                    expected_ciks: set[str] | None = None) -> dict:
    grades = [grade(gold_evidence, k, t) for k, t in ranked]
    out: dict[str, float] = {}
    first = next((i for i, g in enumerate(grades, 1) if g == 2), None)
    out["mrr"] = 1.0 / first if first else 0.0
    # ideal ranking: every gold evidence item at the top, then the best of what was actually retrieved
    ideal = sorted(grades + [2] * max(0, len(gold_evidence) - grades.count(2)), reverse=True)
    for k in ks:
        top = ranked[:k]
        out[f"hit@{k}"] = float(any(g == 2 for g in grades[:k]))
        covered = sum(any(evidence_satisfied(ev, key, txt) for key, txt in top) for ev in gold_evidence)
        out[f"evidence_recall@{k}"] = covered / len(gold_evidence) if gold_evidence else 0.0
        dcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(grades[:k], 1))
        idcg = sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(ideal[:k], 1))
        out[f"ndcg@{k}"] = dcg / idcg if idcg else 0.0
        if expected_ciks and top:
            out[f"provenance@{k}"] = sum(key.cik in expected_ciks for key, _ in top) / len(top)
    return out


def rag_adapter(results: list[dict]) -> list[tuple[EvalKey, str]]:
    """RAG contract v0 output -> [(key, text)]."""
    return [(EvalKey.from_rag_chunk(r), r.get("text", "")) for r in results]


def graph_adapter(nodes: list[dict], text_field: str = "text") -> list[tuple[EvalKey, str]]:
    """GraphRAG ranked Fact/Section nodes -> [(key, text)]. Facts carry no prose, so their value
    is rendered as text to allow `contains` checks on the number."""
    out = []
    for n in nodes:
        txt = n.get(text_field) or f"{n.get('concept', '')} {n.get('value', '')}"
        out.append((EvalKey.from_graph_fact(n), str(txt)))
    return out


def mean_metrics(rows: list[dict]) -> dict:
    keys = sorted({k for r in rows for k in r})
    return {k: sum(r.get(k, 0.0) for r in rows) / len(rows) for k in keys} if rows else {}
