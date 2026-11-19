"""Week 9: front-end smoke test. A browser types gold questions into the UI and we check what the user actually sees.

    python ui_smoke/run_ui_smoke.py --url <UI address> --input "<css>" --submit "<css>" --answer "<css>" \
        [--citation "<css>"] [--n 20] [--tag ui_v1] [--timeout 90]
        -> results/ui_smoke_<tag>.json and _per_question.csv (verdicts and timings; no answer text)

Four checks per question, all on the rendered page (Playwright, Chromium):
  answered      an answer appears before the timeout
  figure_shown  number questions: the gold figure as printed appears in the answer text (thousands separators ignored)
  declines      unanswerable questions: the answer reads as a refusal and shows no figure
  has_citation  answered questions: at least one element matches the citation selector (only if --citation is given)
plus seconds from submit to answer. This is a smoke test of the UI path, not a second accuracy score: the API-level
graders remain the measure of correctness. Selectors come from the UI team (data-testid attributes are best).
The mock page ui_smoke/mock_ui.html lets the script be tested without the real UI (tests/test_week9.py).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8 = ROOT.parent / "Week 8"
sys.path.insert(0, str(W8))
REFUSAL = re.compile(r"\b(cannot|can't|unable|not (available|disclosed|in the (corpus|filings?|provided))|no (information|filing|data)|"
                     r"do(es)? not (contain|disclose|provide|report)|insufficient|not enough (information|evidence))\b", re.I)


def pick(gold: list[dict], n: int) -> list[dict]:
    """A fixed sample: mostly single-company lookups, some narrative, some unanswerable; spread over companies."""
    look = [q for q in gold if q["answerable"] and q["answer_type"] == "exact_numeric" and q["type"] == "extraction" and len(q["tickers"]) == 1]
    nar = [q for q in gold if q["answerable"] and q["answer_type"] == "narrative"]
    un = [q for q in gold if not q["answerable"]]
    seen, spread = set(), []
    for q in look:                                   # one per company first, then fill
        if q["tickers"][0] not in seen:
            seen.add(q["tickers"][0])
            spread.append(q)
    spread += [q for q in look if q not in spread]
    k_un, k_nar = max(1, n // 5), max(1, n // 5)
    return spread[: n - k_un - k_nar] + nar[:k_nar] + un[:k_un]


def figure_in(text: str, q: dict) -> bool:
    flat = text.replace(",", "")
    return any(p.split(" | ")[0].replace(",", "").lstrip("$").rstrip("%") in flat for p in q["answer"]["required_points"][:1])


def run(a) -> tuple[dict, list[dict]]:
    from playwright.sync_api import sync_playwright
    gold = [json.loads(l) for l in open(W8 / "data" / "benchmark_v2_2.jsonl")]
    qs, rows = pick(gold, a.n), []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for q in qs:
            row = {"qid": q["qid"], "answer_type": q["answer_type"], "answerable": q["answerable"], "answered": False, "seconds": None,
                   "figure_shown": None, "declines": None, "has_citation": None, "error": ""}
            try:
                page.goto(a.url)                                      # a fresh page per question: no chat history carried over
                page.fill(a.input, q["question"])
                t0 = time.perf_counter()
                page.click(a.submit)
                page.wait_for_function("s => { const e = document.querySelector(s); return e && e.innerText.trim().length > 0; }",
                                       arg=a.answer, timeout=a.timeout * 1000)
                row["seconds"] = round(time.perf_counter() - t0, 2)
                text = page.inner_text(a.answer)
                row["answered"] = True
                refused = bool(REFUSAL.search(text))
                if not q["answerable"]:
                    row["declines"] = refused and not re.search(r"\d[\d,]{3,}", text)
                elif q["answer_type"] == "exact_numeric":
                    row["figure_shown"] = figure_in(text, q)
                if a.citation and q["answerable"] and not refused:
                    row["has_citation"] = page.locator(a.citation).count() > 0
            except Exception as exc:  # noqa: BLE001 - a UI failure is a result, recorded per question
                row["error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"[:140]
            rows.append(row)
        browser.close()

    def rate(key):
        v = [r[key] for r in rows if r[key] is not None]
        return {"k": sum(v), "n": len(v)}
    secs = sorted(r["seconds"] for r in rows if r["seconds"] is not None)
    summ = {"ui": a.url if a.url.startswith("http") else "local file", "gold": "benchmark_v2_2.jsonl", "questions": len(rows),
            "answered": {"k": sum(r["answered"] for r in rows), "n": len(rows)}, "figure_shown": rate("figure_shown"),
            "declines_unanswerable": rate("declines"), "has_citation": rate("has_citation"),
            "seconds": {"median": round(statistics.median(secs), 2), "max": secs[-1]} if secs else None,
            "errors": [f"{r['qid']}: {r['error']}" for r in rows if r["error"]]}
    return summ, rows


def main():
    ap = argparse.ArgumentParser()
    for k in ("url", "input", "submit", "answer"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--citation")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--tag", default="ui")
    a = ap.parse_args()
    summ, rows = run(a)
    (ROOT / "results" / f"ui_smoke_{a.tag}.json").write_text(json.dumps(summ, indent=1))
    with open(ROOT / "results" / f"ui_smoke_{a.tag}_per_question.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
