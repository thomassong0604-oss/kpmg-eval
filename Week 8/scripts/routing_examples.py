"""Week 8: concrete routing examples for the demo walkthrough (11/5 minutes, Eval items 2-5).

    python scripts/routing_examples.py   -> results/routing_examples.json, ROUTING_EXAMPLES.md

For each example: the question, the route Eval expects, and what three routers call, with the unneeded calls counted.
  unneeded calls (per question) = number of tools called that the question's expected route does not need
      expected sql -> needs {sql};  text -> {text};  graph -> {graph};  multi -> {sql, text};  none -> {} (gate answers)
      "unneeded calls per question" on the slide = the sum over all questions / number of questions (155).
  It is not "calls made when text search alone could have answered"; a call is unneeded only relative to the
  expected route.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from kpmg_eval.metrics.routing import REQUIRED  # noqa: E402
from run_decision_baselines import rule_gate  # noqa: E402
from run_routing_baselines import GRAPH, NUM, TEXT, keyword  # noqa: E402

PICKS = [("GSv0-MSFT-001", "number from a statement"), ("GSv0-MSFT-004", "explanation from the text"),
         ("EV3-001", "relationship (Exhibit 21)"), ("EV1R-003", "number plus its explanation: keyword router misses SQL"),
         ("EV1-062", "out of scope: market data"), ("GSv0-MSFT-009", "keyword router gets it wrong"),
         ("GSv0-MSFT-014", "keyword router calls one extra tool")]
TOOL = {"sql": "SQL (Data finance views)", "text": "RAG text search", "graph": "GraphRAG"}


def why(q: str, session) -> str:
    decision, calls = rule_gate(q, session)
    if calls == 0:
        return f"scope gate decides '{decision}', no tool"
    if GRAPH.search(q):
        return f"relationship word '{GRAPH.search(q).group(0)}' -> GraphRAG"
    n, t = NUM.search(q), TEXT.search(q)
    if n and t:
        return f"number word '{n.group(0)}' and explanation word '{t.group(0)}' -> SQL + RAG"
    if n:
        return f"number word '{n.group(0)}' -> SQL"
    return "no number word -> RAG text search"


def main():
    gold = {json.loads(l)["qid"]: json.loads(l) for l in open(ROOT / "data" / "benchmark_v2.jsonl")}
    ex = []
    for qid, label in PICKS:
        q = gold[qid]
        sess = q["tickers"][0] if len(q["tickers"]) == 1 else None
        need = REQUIRED[q["route_expected"]]
        row = {"qid": qid, "label": label, "question": q["question"], "expected_route": q["route_expected"],
               "needs": sorted(need), "keyword_reason": why(q["question"], sess), "routers": {}}
        for name, called in (("text_only", {"text"}), ("keyword", keyword(q["question"], sess)),
                             ("combined", {"sql", "text", "graph"})):
            ok = (not called) if not need else need <= called
            row["routers"][name] = {"called": sorted(called), "needed_tools_called": ok, "unneeded": len(called - need)}
        ex.append(row)
    (ROOT / "results" / "routing_examples.json").write_text(json.dumps(ex, indent=1))

    md = ["# Routing examples for the demo (Week 8)", "",
          "Router definitions:",
          "- **text_only**: every question goes to RAG text search (the demo path before routing).",
          "- **keyword**: Eval's rule-based stand-in for the Agents' orchestrator (regular expressions, no LLM). "
          "The scope gate runs first; if it blocks, no tool is called. Otherwise a relationship word (subsidiary, "
          "Exhibit 21, acquire, own, parent, rename) sends it to GraphRAG; a number word (how much, revenue, margin, "
          "percent, total, calculate) to SQL; an explanation word (why, explain, describe, risk, policy) to RAG text; "
          "both kinds of word to SQL + RAG; neither to RAG text.",
          "- **combined**: every question goes to all three tools.", "",
          "**Unneeded call**: a tool the router called that the question's expected route does not need "
          "(sql needs SQL; text needs RAG; graph needs GraphRAG; multi needs SQL + RAG; none needs no tool). "
          "Unneeded calls per question = total unneeded calls / 155 questions. It counts calls outside the expected "
          "route; it does not mean \"text search alone could have answered\".", "",
          "All rates are on the current 155 Gold Set v2 questions only (104 sql, 31 text, 11 graph, 8 none, 1 multi), "
          "with routes labelled by Eval. They will move as questions are added.", ""]
    for r in ex:
        md += [f"## {r['label']} ({r['qid']})", "", f"> {r['question']}", "",
               f"Expected route: **{r['expected_route']}** (needs: {', '.join(TOOL[t] for t in r['needs']) or 'no tool'}). "
               f"Keyword router: {r['keyword_reason']}.", "",
               "| Router | Calls | Needed tools called | Unneeded calls |", "| --- | --- | --- | --- |"]
        for name, v in r["routers"].items():
            md.append(f"| {name} | {', '.join(TOOL[t] for t in v['called']) or 'none'} | "
                      f"{'yes' if v['needed_tools_called'] else 'no'} | {v['unneeded']} |")
        md.append("")
    (ROOT / "ROUTING_EXAMPLES.md").write_text("\n".join(md))
    for r in ex:
        print(r["qid"], r["expected_route"], "|", r["keyword_reason"], "|",
              {k: (v["called"], v["unneeded"]) for k, v in r["routers"].items()})


if __name__ == "__main__":
    main()
