"""Week 7: score three reference routers on Gold Set v2's expected routes. Week 8: plug in any other router.

    python scripts/run_routing_baselines.py   -> results/routing_baselines.json

    # Agents: score your orchestrator on the same 155 questions, either as a function ...
    python scripts/run_routing_baselines.py --router orchestrator=path/to/your_module.py:route
        # route(question: str, session_ticker: str | None) -> the tools it would call, e.g. {"sql", "text"}
    # ... or from a log of the tool calls it actually made (one JSON object per line: {"qid": ..., "tools": [...]})
    python scripts/run_routing_baselines.py --calls orchestrator=path/to/calls.jsonl

Tool names are mapped to Eval's three (sql = Data finance views / structured facts, text = RAG, graph = GraphRAG);
see TOOL_ALIASES. Coverage ("required_tools_called") = share of questions where every tool the question needs was
called. It is not answer accuracy: calling the right tools does not make the final answer right.

  text_only   every question goes to RAG text search (today's demo path)
  combined    every question goes to all three tools (the "combined retrieval" option from 10/29)
  keyword     a keyword router (Eval's stand-in for the Agents' orchestrator; regex, no LLM)
The expected routes are Eval's labels (scripts/build_gold_v2.py, route_for); Agents should review them. What this shows is
the measurement and the cost side of the trade-off, not how well the real orchestrator routes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from kpmg_eval.metrics.routing import score_routing  # noqa: E402
from run_decision_baselines import rule_gate  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
GRAPH = re.compile(r"subsidiar|exhibit 21|acquir|\bowns?\b|parent|renam|reportable segments between|relationship", re.I)
NUM = re.compile(r"usd|how much|percentage|percent|margin|rank|growth|total|how many|which fiscal year|per share|"
                 r"effective tax rate|reconcil|calculate|compare|exceed|higher|net income|revenue|cash", re.I)
TEXT = re.compile(r"\bwhy\b|explain|describe|discuss|\bmean\b|defin|what drove|driven|risk|policy|what is .* segment|name ", re.I)


def keyword(q: str, session: str | None) -> set[str]:
    decision, calls = rule_gate(q, session)
    if calls == 0:
        return set()
    if GRAPH.search(q):
        return {"graph"}
    num, txt = bool(NUM.search(q)), bool(TEXT.search(q))
    if num and txt:
        return {"sql", "text"}
    return {"sql"} if num else {"text"}


TOOL_ALIASES = {"sql": "sql", "finance": "sql", "finance_data": "sql", "structured_search": "sql", "xbrl": "sql",
                "text": "text", "rag": "text", "retrieve": "text", "sec_filing_search": "text", "vector": "text",
                "graph": "graph", "graphrag": "graph", "graph_search": "graph"}


def _tools(called) -> set[str]:
    out = set()
    for t in called or []:
        key = str(t).strip().lower()
        if key not in TOOL_ALIASES:
            raise ValueError(f"unknown tool name {t!r}: add it to TOOL_ALIASES")
        out.add(TOOL_ALIASES[key])
    return out


def load_router(spec: str):
    """'path/to/module.py:function' -> callable(question, session) -> set of Eval tool names."""
    import importlib.util
    path, func = spec.rsplit(":", 1)
    mod_spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    fn = getattr(mod, func)
    return lambda q, sess: _tools(fn(q, sess))


def load_calls(path: str, gold: list[dict]):
    """Logged tool calls {"qid", "tools"} -> callable(question, session) looked up by question text."""
    by_qid = {json.loads(l)["qid"]: json.loads(l)["tools"] for l in open(path) if l.strip()}
    by_text = {q["question"]: by_qid.get(q["qid"]) for q in gold}
    missing = [q["qid"] for q in gold if q["qid"] not in by_qid]
    if missing:
        print(f"[routing] {path}: no calls logged for {len(missing)} questions (scored as no tool called), e.g. {missing[:5]}")
    return lambda q, sess: _tools(by_text.get(q) or [])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", action="append", default=[], help="name=path/to/module.py:function")
    ap.add_argument("--calls", action="append", default=[], help="name=path/to/calls.jsonl")
    args = ap.parse_args()
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2.jsonl")]
    routers = {"text_only": lambda q, s: {"text"}, "combined": lambda q, s: {"sql", "text", "graph"}, "keyword": keyword}
    for spec in args.router:
        name, target = spec.split("=", 1)
        routers[name] = load_router(target)
    for spec in args.calls:
        name, target = spec.split("=", 1)
        routers[name] = load_calls(target, gold)
    out = {"n": len(gold), "expected_routes": {}, "routers": {},
           "note": "Expected routes are Eval's labels; keyword is a regex stand-in for the orchestrator."}
    for q in gold:
        out["expected_routes"][q["route_expected"]] = out["expected_routes"].get(q["route_expected"], 0) + 1
    for name, fn in routers.items():
        cases, misses = [], []
        for q in gold:
            sess = q["tickers"][0] if len(q["tickers"]) == 1 else None
            called = fn(q["question"], sess)
            cases.append({"expected": q["route_expected"], "called": called})
            from kpmg_eval.metrics.routing import REQUIRED
            if called != REQUIRED[q["route_expected"]]:
                misses.append({"qid": q["qid"], "expected": q["route_expected"], "called": sorted(called)})
        out["routers"][name] = {**score_routing(cases), "n_not_exact": len(misses), "examples_not_exact": misses[:15]}
        r = out["routers"][name]
        print(f"[routing] {name:9s} required-tools-called={r['required_tools_called']} exact={r['exact_route']} "
              f"calls/q={r['tool_calls_per_question']} unneeded/q={r['unneeded_calls_per_question']} "
              f"by route {json.dumps(r['required_tools_called_by_route'])}")
    RES.mkdir(exist_ok=True)
    (RES / "routing_baselines.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
