"""Week 5. Automated grading pipeline: run any system on Gold Set v1 through RAG's real retrieve(), then grade it.

Plug-in point for the Agent team: a system is any object with

    name: str
    answer(item: dict, retrieve: Callable[[str, dict | None, int], list[dict]]) -> dict   # an AnswerBlock

`item` carries only what a user would give: {"id", "question", "session_ticker"}. `retrieve` is RAG's contract-v0
retrieve(); the harness wraps it, so every chunk the system saw is logged per question without the system doing
anything. The AnswerBlock fields used: answered, value, value_text, unit, answer_text, citations[{id}], steps (optional).

Scorecard: the four headline metrics recommended on the metric-selection slide, plus diagnostics.
  1  numeric_accuracy      NAA on exact-numeric questions (Week-4 grader + Week-5 fact-index diagnosis)
  2  evidence_recall@10    from the logged retrieval (RAG's own definition, rag.evaluate.score_question)
  3  refusal_balanced      balanced refusal accuracy on answerable vs unanswerable (+ false-premise correction rate)
  4  citation_support      share of answered lookup answers whose number appears in a cited, actually-retrieved chunk
                           (calculated answers are not printed in the filing; their inputs are checked by reasoning steps)
Every scorecard records the benchmark hash, RAG commit, index_version and Eval git commit, so two teams comparing
numbers know they ran the same corpus and versions.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from collections import Counter
from pathlib import Path
from statistics import median

from .metrics.citation import score_citations
from .metrics.context import answer_in_context, figure_in
from .metrics.diagnose import FactIndex
from .metrics.numeric import score_numeric_diagnosed
from .metrics.premise import classify_premise
from .stats import wilson


class LoggedRetriever:
    def __init__(self, retriever, method: str = "bm25"):
        self.r, self.method, self.log = retriever, method, {}
        self.current = None

    def __call__(self, query: str, filters: dict | None = None, top_k: int = 10) -> list[dict]:
        t0 = time.perf_counter()
        res = self.r.search(query, filters=filters, top_k=top_k, method=self.method)["results"]
        self.log.setdefault(self.current, []).append({"query": query, "filters": filters, "top_k": top_k,
                                                      "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "results": res})
        return res


def run(system, items: list[dict], retriever) -> tuple[list[dict], dict]:
    lr = LoggedRetriever(retriever)
    answers = []
    for it in items:
        lr.current = it["id"]
        t0 = time.perf_counter()
        try:
            a = system.answer({"id": it["id"], "question": it["question"], "session_ticker": it.get("session_ticker")}, lr)
            a.setdefault("answered", True)
        except Exception as e:  # an error is scored, never skipped
            a = {"answered": None, "error": repr(e)}
        a["qid"], a["latency_ms"] = it["id"], round((time.perf_counter() - t0) * 1000, 2)
        answers.append(a)
    return answers, lr.log


def _points_coverage(answer_text: str, points: list[str]) -> float:
    low = (answer_text or "").lower()
    def hit(p):
        words = [w for w in re.findall(r"[a-z0-9][a-z0-9.,%$-]*", p.lower()) if len(w) > 3]
        return bool(words) and sum(w in low for w in words) / len(words) >= 0.6
    return sum(hit(p) for p in points) / len(points) if points else 0.0


def versions(root: Path, bench_path: Path, retriever) -> dict:
    def git(cwd):
        try:
            return subprocess.check_output(["git", "-C", str(cwd), "rev-parse", "--short", "HEAD"], text=True).strip()
        except Exception:
            return None
    return {"benchmark_sha256": hashlib.sha256(bench_path.read_bytes()).hexdigest()[:16],
            "rag_commit": git(root / "upstream" / "KPMG_RAG"), "eval_commit": git(root),
            "index_version": retriever.meta.get("index_version"), "embedder": retriever.meta.get("embedder"),
            "graded_at": time.strftime("%Y-%m-%dT%H:%M:%S")}


def grade(bench: dict, suite: dict, answers: list[dict], rlog: dict, fact_index: FactIndex, ver: dict, system: str) -> dict:
    from rag.evaluate import score_question  # RAG's metric definitions
    A = {a["qid"]: a for a in answers}
    num_res, recall, aic, cites, cover = [], [], [], [], []
    by_scope = Counter()
    refusal_cases, premise = [], []
    for qid, a in A.items():
        q = bench.get(qid)
        chunks = [r for call in rlog.get(qid, []) for r in call["results"]]
        seen = {c["chunk_id"]: c["text"] for c in chunks}
        refused = a.get("answered") is False
        if q is None:  # abstention-suite item
            s = suite[qid]
            if s["kind"] == "false_premise":
                premise.append(classify_premise(a.get("answer_text", ""), [s["expected"]]) if not refused else "refused")
            else:
                refusal_cases.append((s["answerable"], refused))
            continue
        if q["type"] == "false_premise":
            premise.append("refused" if refused else classify_premise(a.get("answer_text", ""), q["answer"]["required_points"]))
            continue
        refusal_cases.append((q["answerable"], refused))
        if not q["answerable"]:
            continue
        if q["rag_evidence"] and chunks:
            first = rlog[qid][0]["results"]
            recall.append(score_question({"gold": {"evidence": q["rag_evidence"]}}, first, (10,))["evidence_recall@10"])
        if q["answer_type"] == "exact_numeric":
            r = score_numeric_diagnosed(q, a if not refused else {"answered": False}, fact_index)
            num_res.append(r)
            by_scope[(q["scope"], r.passed)] += 1
            if q["type"] in ("extraction", "segment"):
                aic.append((r.passed, answer_in_context([q["answer"]["required_points"][0].lstrip("-")], [c["text"] for c in chunks], 10)))
            if not refused and a.get("value_text") and q["type"] in ("extraction", "segment"):  # lookups: the number is printed in the filing
                sc = score_citations([{"text": a["value_text"], "cites": [c["id"] for c in a.get("citations", [])]}], seen)
                cites.append(bool(sc["numeric_support"]))
        elif q["answer_type"] == "narrative":
            cover.append(0.0 if refused else _points_coverage(a.get("answer_text", ""), q["answer"]["required_points"]))
    n_ok = sum(r.passed for r in num_res)
    ans = [r for a_, r in refusal_cases if a_]
    un = [r for a_, r in refusal_cases if not a_]
    appropriate, unnecessary = (sum(un) / len(un) if un else None), (sum(ans) / len(ans) if ans else None)
    in_ctx = [x for x in aic if x[1]]
    lat = [a["latency_ms"] for a in answers]
    card = {
        "system": system, "versions": ver, "n_items": len(answers),
        "headline": {
            "numeric_accuracy": {"value": round(n_ok / len(num_res), 3) if num_res else None, "n": len(num_res),
                                 "ci95": [round(x, 3) for x in wilson(n_ok, len(num_res))] if num_res else None},
            "evidence_recall@10": {"value": round(sum(recall) / len(recall), 3) if recall else None, "n": len(recall)},
            "refusal_balanced": {"value": round((appropriate + 1 - unnecessary) / 2, 3) if un and ans else None,
                                 "appropriate_refusal_rate": round(appropriate, 3) if un else None,
                                 "unnecessary_refusal_rate": round(unnecessary, 3) if ans else None,
                                 "n_answerable": len(ans), "n_unanswerable": len(un)},
            "citation_support": {"value": round(sum(cites) / len(cites), 3) if cites else None, "n": len(cites)},
        },
        "diagnostics": {
            "error_labels": dict(Counter(r.label for r in num_res if not r.passed)),
            "lookups_gold_in_top10": len(in_ctx), "lookups_gold_in_top10_but_wrong": sum(1 for p, c in in_ctx if not p),
            "false_premise": dict(Counter(premise)),
            "narrative_points_coverage_provisional": round(sum(cover) / len(cover), 3) if cover else None,
            "numeric_by_scope": {f"{s}|{'ok' if p else 'wrong'}": n for (s, p), n in sorted(by_scope.items())},
            "latency_ms_p50": median(lat) if lat else None, "errors": sum(1 for a in answers if a.get("error")),
        },
    }
    return card


def scorecard_markdown(cards: list[dict], pending: int) -> str:
    h = ["# Gold Set v1 scorecard", "", f"Versions: benchmark `{cards[0]['versions']['benchmark_sha256']}`, RAG `{cards[0]['versions']['rag_commit']}`, "
         f"index `{cards[0]['versions']['index_version']}`, eval `{cards[0]['versions']['eval_commit']}`. "
         f"{pending} questions pending (peer / 10-K chunks not yet shared).", "",
         "| System | Numeric accuracy | Evidence recall@10 | Refusal (balanced) | Citation support |", "|---|---|---|---|---|"]
    fmt = lambda x: "n/a" if x is None else f"{x:.2f}"  # noqa: E731
    for c in cards:
        hl = c["headline"]
        h.append(f"| {c['system']} | {fmt(hl['numeric_accuracy']['value'])} (n={hl['numeric_accuracy']['n']}) | "
                 f"{fmt(hl['evidence_recall@10']['value'])} | {fmt(hl['refusal_balanced']['value'])} | {fmt(hl['citation_support']['value'])} |")
    h += ["", "Diagnostics per system are in the json scorecards."]
    return "\n".join(h)
