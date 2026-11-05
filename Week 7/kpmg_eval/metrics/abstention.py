"""Week 5. Can a retrieval score tell answerable from unanswerable questions?

Week 4 found that the mock retriever returned chunks for every unanswerable query. This module measures whether the
top-1 score separates the two groups well enough to use as an abstention gate, before the Agent spends tokens:

  auroc            probability that a random answerable question scores higher than a random unanswerable one
                   (0.5 = no signal, 1.0 = perfect separation). Rank-based, so it is valid for raw BM25/RRF
                   scores, which the Retrieval API says must not be thresholded across calls.
  best_threshold   the cut that maximises balanced accuracy on this set (descriptive only, not a recommended
                   production threshold: the set is small and the cut would be tuned on the test data).
"""
from __future__ import annotations


def auroc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def best_threshold(pos: list[float], neg: list[float]) -> dict:
    cands = sorted(set(pos) | set(neg))
    best = {"threshold": None, "balanced_accuracy": 0.0}
    for t in cands:
        tpr = sum(p >= t for p in pos) / len(pos)
        tnr = sum(n < t for n in neg) / len(neg)
        ba = (tpr + tnr) / 2
        if ba > best["balanced_accuracy"]:
            best = {"threshold": t, "balanced_accuracy": ba, "answerable_kept": tpr, "unanswerable_blocked": tnr}
    return best
