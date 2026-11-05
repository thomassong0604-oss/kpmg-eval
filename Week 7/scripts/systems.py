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


# ---------------------------------------------------------------- Week 7: RAG's fixed reader (Slack 10/28)
FIXED_READER_PROMPT = """You answer questions about companies using ONLY the numbered SEC filing excerpts provided.
Rules:
- Cite every factual claim with the excerpt number in brackets, e.g. [2]. Use several if needed: [1][3].
- Quote numbers exactly as they appear, with units and the period they refer to.
- If the excerpts do not contain the answer, say "The provided filings do not contain this information." Do not guess.
- Be concise."""   # same instructions as RAG's rag/generate.py, so RAG and Eval measure the same reader
NO_ANSWER = "do not contain this information"


class FixedReaderSystem:
    """RAG's proposal (10/28): put one fixed reader (gpt-4o-mini, temperature 0) behind the retriever, so numeric accuracy
    measures RAG's table fixes rather than recall alone. Same prompt as RAG's generate.py, top 8 (RAG's k).
    Needs OPENAI_API_KEY; `client` can be injected (tests use a stub). Logs tokens and cost per question."""

    name = "fixed_reader_gpt4o_mini"
    model, k = "gpt-4o-mini", 8
    price_per_1m = {"input": None, "output": None}  # fill from the provider's price page to log cost (as RAG's config.yaml)

    def __init__(self, client=None):
        if client is None:
            import os
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("FixedReaderSystem needs OPENAI_API_KEY (or an injected client)")
            from openai import OpenAI
            client = OpenAI()
        self.client = client

    def answer(self, item, retrieve):
        import re
        flt, why = scope_check(item["question"], item.get("session_ticker"))
        if why:
            return {"answered": False, "decision": "abstain", "answer_text": why, "citations": []}
        res = retrieve(item["question"], {k: v for k, v in flt.items() if k in ("ticker", "form", "fiscal_year", "fiscal_period")}
                       or None, self.k)
        ctx = "\n\n---\n\n".join(f"[{i}] {r.get('ticker', '')} {r.get('form', '')} {r.get('reporting_period_end') or ''}\n{r['text']}"
                                 for i, r in enumerate(res, 1))
        out = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": FIXED_READER_PROMPT},
                      {"role": "user", "content": f"Excerpts:\n\n{ctx}\n\nQuestion: {item['question']}"}])
        text = out.choices[0].message.content or ""
        cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 0 < int(n) <= len(res)})
        refused = NO_ANSWER in text.lower()
        usage = getattr(out, "usage", None)
        return {"answered": not refused, "decision": "abstain" if refused else "answer", "answer_text": text,
                "value_text": None if refused else text.split("\n")[0],
                "citations": [{"id": res[n - 1]["chunk_id"], "source": "vector_rag"} for n in cited],
                "prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None),
                "model": self.model}
