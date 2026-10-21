"""Uncertainty for small benchmarks. With 30-50 questions, a 5-point difference between two systems is
often noise; every reported rate carries an interval so KPMG never sees an over-confident number."""
from __future__ import annotations

import math
import random


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def bootstrap_ci(values: list[float], iters: int = 5000, alpha: float = 0.05, seed: int = 7) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(iters))
    return (means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters) - 1])


def paired_bootstrap_diff(a: list[float], b: list[float], iters: int = 5000, seed: int = 7) -> dict:
    """System A vs B on the same questions: mean diff, 95% CI, and share of resamples where A > B."""
    assert len(a) == len(b) and a
    rng = random.Random(seed)
    n = len(a)
    diffs = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    return {"mean_diff": sum(x - y for x, y in zip(a, b)) / n, "ci95": (diffs[int(0.025 * iters)], diffs[int(0.975 * iters) - 1]),
            "p_a_better": sum(d > 0 for d in diffs) / iters}
