"""Week 5. Answer-in-context@k and evidence position: what retrieval leaves for the Agent to work with.

answer_in_context@k   share of numeric questions whose gold figure (as displayed in the filing, e.g. "82,886")
                      appears in the top-k retrieved text. Ceiling on end-to-end accuracy: if the number is not in
                      the context, the Agent can only get it right by computing it from other numbers or by luck.
                      For calculated answers we require every *input* figure instead (all inputs in context).
evidence_rank         rank of the first chunk that satisfies a gold evidence item. Its distribution tells the
                      Agent team where in the prompt the evidence will sit (long-context "lost in the middle" risk).

Matching ignores the spaces RAG's parser puts inside parentheses ("( 84,669)") and thousands separators split by
markdown table pipes are not an issue because figures are matched as whole tokens.
"""
from __future__ import annotations

import re
from statistics import median

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    t = text.replace("( ", "(").replace(" )", ")")
    return _WS.sub(" ", t).lower()


def figure_in(figure: str, text: str) -> bool:
    """Whole-token match: '4,832' must not match inside '14,832'."""
    f = re.escape(figure.lower())
    return re.search(rf"(?<![\d,.]){f}(?![\d]|,\d)", _norm(text)) is not None


def answer_in_context(figures: list[str], texts: list[str], k: int) -> float:
    """1.0 if every figure occurs in the concatenated top-k texts."""
    if not figures:
        return 0.0
    ctx = " \n ".join(texts[:k])
    return float(all(figure_in(f, ctx) for f in figures))


def evidence_rank(flags: list[bool]) -> int | None:
    return next((i for i, x in enumerate(flags, 1) if x), None)


def rank_summary(ranks: list[int | None], k: int) -> dict:
    found = [r for r in ranks if r is not None and r <= k]
    return {"n": len(ranks), f"found@{k}": len(found), "median_rank": median(found) if found else None,
            "share_rank1": sum(r == 1 for r in found) / len(ranks) if ranks else None,
            "share_rank_gt3": sum(r > 3 for r in found) / len(ranks) if ranks else None}
