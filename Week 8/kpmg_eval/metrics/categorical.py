"""Week 8. Exact-categorical answers (fiscal calendars, which companies, which subsidiaries): pass = every required point
is stated. Rule-based, no LLM judge, so it is strict on wording; the normalisation below covers the phrasings seen in
RAG's round-1 answers (11/11):

  * curly quotes straightened ("Casey’s" = "Casey's"), case ignored
  * "first quarter" / "1st quarter" = "Q1" (and Q2-Q4)
  * "fiscal year 2027" / "FY2027" / "FY 2027" = "fiscal 2027"
  * a required point may list alternatives separated by " | "
"""
from __future__ import annotations

import re

_Q = {"first": "q1", "1st": "q1", "second": "q2", "2nd": "q2", "third": "q3", "3rd": "q3", "fourth": "q4", "4th": "q4"}


def norm(s: str) -> str:
    s = (s or "").lower().replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    s = re.sub(r"\b(first|1st|second|2nd|third|3rd|fourth|4th) (fiscal )?quarter\b", lambda m: _Q[m.group(1)], s)
    s = re.sub(r"\bfiscal year (\d{4})\b|\bfy ?(\d{4})\b", lambda m: f"fiscal {m.group(1) or m.group(2)}", s)
    return re.sub(r"\s+", " ", s)


def point_stated(point: str, answer_text: str) -> bool:
    low = norm(answer_text)
    return any(norm(alt.strip()) in low for alt in point.split(" | "))


def score_categorical(required_points: list[str], answer_text: str) -> dict:
    found = [point_stated(p, answer_text) for p in required_points]
    return {"passed": bool(found) and all(found), "points_stated": sum(found), "points": len(found),
            "missing": [p for p, f in zip(required_points, found) if not f]}
