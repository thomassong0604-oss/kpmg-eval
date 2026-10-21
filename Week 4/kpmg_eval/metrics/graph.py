"""GraphRAG-specific metrics (requested in Project Hub 3.3.11: "GraphRAG-specific evaluation criteria").

These score the graph itself, before any question is asked, using GraphRAG's own schema:
Company(CIK) -[FILED]-> Filing(accession) -[HAS_SECTION]-> Section
Filing -[REPORTS]-> Fact(concept, period, unit, value) ; Company -[HAS_SEGMENT]-> Segment ; Company -[OWNS]-> Subsidiary

  fact_extraction P/R/F1   extracted Fact nodes vs XBRL gold, matched on the FACT-level EvalKey,
                           with value checked separately (a matched key with a wrong value is an error)
  value_accuracy           of matched facts, share with the correct value
  edge P/R/F1              typed relationships (subject key, relation, object key)
  entity_linking_accuracy  mentions resolved to the right CIK (the 10/8 deck notes executives were dropped
                           because names are not stable identifiers; companies must resolve to CIK)
  path_recall              for multi-hop questions, share of the gold path's hops present in the graph
"""
from __future__ import annotations

from ..keys import EvalKey


def _fact_key(f: dict) -> EvalKey:
    return EvalKey(cik=f.get("cik"), concept=f.get("concept"), period_start=f.get("period_start") or f.get("start"),
                   period_end=f.get("period_end") or f.get("end"), unit=f.get("unit", "USD"))


def _prf(tp: int, n_pred: int, n_gold: int) -> dict:
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "tp": tp,
            "n_pred": n_pred, "n_gold": n_gold}


def score_fact_extraction(pred: list[dict], gold: list[dict], rel_tol: float = 5e-4) -> dict:
    gold_by_key = {_fact_key(g): float(g["value"]) for g in gold}
    pred_by_key: dict[EvalKey, float] = {}
    for p in pred:
        pred_by_key.setdefault(_fact_key(p), float(p["value"]))
    matched = [k for k in pred_by_key if k in gold_by_key]
    right = [k for k in matched if abs(pred_by_key[k] - gold_by_key[k]) <= rel_tol * max(abs(gold_by_key[k]), 1)]
    out = _prf(len(right), len(pred_by_key), len(gold_by_key))
    out["key_recall"] = len(matched) / len(gold_by_key) if gold_by_key else 0.0
    out["value_accuracy"] = len(right) / len(matched) if matched else None
    out["wrong_value_keys"] = [k.to_dict() for k in matched if k not in right]
    return out


def score_edges(pred: list[tuple], gold: list[tuple]) -> dict:
    """Edges as (subject_id, relation, object_id) with ids already canonical (CIK, accession, ...)."""
    norm = lambda e: (str(e[0]).upper(), str(e[1]).upper(), str(e[2]).upper())  # noqa: E731
    P, G = {norm(e) for e in pred}, {norm(e) for e in gold}
    out = _prf(len(P & G), len(P), len(G))
    rels = sorted({e[1] for e in G | P})
    out["by_relation"] = {r: _prf(len({e for e in P & G if e[1] == r}), len({e for e in P if e[1] == r}),
                                  len({e for e in G if e[1] == r})) for r in rels}
    return out


def entity_linking_accuracy(links: list[tuple[str, str | None]], gold: dict[str, str]) -> dict:
    """links: [(mention, predicted_cik or None)]; gold: {mention: cik}."""
    scored = [(m, p) for m, p in links if m in gold]
    correct = sum(p is not None and p.zfill(10) == gold[m].zfill(10) for m, p in scored)
    unresolved = sum(p is None for _, p in scored)
    return {"accuracy": correct / len(scored) if scored else None, "n": len(scored), "unresolved": unresolved}


def path_recall(graph_edges: set[tuple], gold_path: list[tuple]) -> float:
    norm = lambda e: (str(e[0]).upper(), str(e[1]).upper(), str(e[2]).upper())  # noqa: E731
    G = {norm(e) for e in graph_edges}
    return sum(norm(h) in G for h in gold_path) / len(gold_path) if gold_path else 0.0
