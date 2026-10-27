"""Reference systems for the grading pipeline. The Agent team adds theirs the same way (see AgentTemplate).

  OracleSystem     knows the gold answers; cites a retrieved chunk that holds the number. Must score ~1.0 on every
                   headline metric: a sanity check that the pipeline grades a perfect system as perfect.
  RefuseAllSystem  always declines: numeric accuracy 0, balanced refusal 0.5. Catches graders that reward silence.
  BaselineSystem   the no-LLM floor: scope check (abstention stage 1) -> RAG BM25 top 5 -> table reader.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from rag_fiscal import fiscal_label  # noqa: E402
from run_e2e_baseline import read  # noqa: E402  (the table reader)

from kpmg_eval.filters import extract_filters  # noqa: E402
from kpmg_eval.metrics.context import figure_in  # noqa: E402

SCOPE = json.loads((ROOT / "config" / "scope.json").read_text())
POOL = json.loads((ROOT / "data" / "filing_pool_v1.json").read_text())["filings"]
RAG_FYE = {"MSFT": "0630", "AAPL": "0927", "NVDA": "0126"}
MANIFEST = {(f["ticker"], *fiscal_label(f["reporting_period_end"], RAG_FYE.get(f["ticker"], "1231"), f["form"])) for f in POOL}
TICKERS = {f["ticker"] for f in POOL}


def scope_check(question: str, session_ticker: str | None):
    flt = extract_filters(question, SCOPE, fiscal_label, session_ticker=session_ticker)
    t = flt.get("ticker")
    if isinstance(t, str) and t not in TICKERS:
        return flt, f"{t} is not in the corpus"
    if isinstance(t, str) and "fiscal_year" in flt and (t, flt["fiscal_year"], flt.get("fiscal_period", "Q3")) not in MANIFEST:
        return flt, f"no {t} filing for FY{flt['fiscal_year']} {flt.get('fiscal_period', '')} in the corpus"
    return flt, None


class RefuseAllSystem:
    name = "refuse_all"

    def answer(self, item, retrieve):
        return {"answered": False, "answer_text": "I can't answer that from the filings.", "citations": []}


class OracleSystem:
    name = "oracle"

    def __init__(self, bench: dict, suite: dict):
        self.bench, self.suite = bench, suite

    def answer(self, item, retrieve):
        q = self.bench.get(item["id"])
        if q is None:
            s = self.suite[item["id"]]
            return {"answered": s["answerable"], "answer_text": s["expected"], "citations": []}
        if not q["answerable"]:
            return {"answered": False, "answer_text": q["answer"]["display"], "citations": []}
        res = retrieve(q["question"], q["filters"], 10)
        a = q["answer"]
        out = {"answered": True, "answer_text": a["display"] + " " + " ".join(a.get("required_points", [])), "citations": []}
        if a.get("value") is not None:
            out.update({"value": a["value"], "unit": a["unit"]})
            if a["unit"] == "USD":
                out["value_text"] = f"{a['value'] / 1e6:,.0f} million"
                fig = f"{abs(a['value']) / 1e6:,.0f}"
            elif a["unit"] == "USD/shares":
                out["value_text"] = fig = f"{a['value']:.2f}"
            else:
                out["value_text"] = {"%": f"{a['value']:g}%", "pp": f"{a['value']} pp"}.get(a["unit"], f"{a['value']}")
                fig = out["value_text"] if a["unit"] == "%" else None
            hit = next((c for c in res if fig and figure_in(fig, c["text"])), None)
            out["citations"] = [{"id": hit["chunk_id"], "source": "vector_rag"}] if hit else []
        return out


class BaselineSystem:
    name = "baseline_no_llm"

    def answer(self, item, retrieve):
        flt, why = scope_check(item["question"], item.get("session_ticker"))
        if why:
            return {"answered": False, "answer_text": f"I can't answer that: {why}.", "citations": []}
        filters = {k: v for k, v in flt.items() if k in ("ticker", "form", "fiscal_year", "fiscal_period")}
        res = retrieve(item["question"], filters or None, 5)
        if not res:
            return {"answered": False, "answer_text": "No evidence found.", "citations": []}
        v, label = read(item["question"], res)
        top = res[0]
        if v is None:
            return {"answered": True, "answer_text": top["text"][:600], "citations": [{"id": top["chunk_id"], "source": "vector_rag"}]}
        src = next((c for c in res if label and label in c["text"]), top)
        neg = "sign" in item["question"].lower()
        return {"answered": True, "value": (v if neg else abs(v)) * 1e6, "unit": "USD", "value_text": f"{v if neg else abs(v):,.0f} million",
                "answer_text": f"{label}: {v:,.0f}", "citations": [{"id": src["chunk_id"], "source": "vector_rag"}]}


class AgentTemplate:
    """Copy this for the Agent: call your agent, return its AnswerBlock. `retrieve` is RAG's real retrieve(); use it
    (or your own call to rag.retrieve) so the harness logs what the agent saw."""
    name = "agent_v0"

    def answer(self, item, retrieve):
        raise NotImplementedError("return your agent's AnswerBlock (kpmg_eval/answer_schema.py)")
