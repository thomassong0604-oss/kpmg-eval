"""One command: run systems on Gold Set v1 (+ abstention suite) through RAG's real retriever and grade them.

    python scripts/run_harness.py                       # oracle, refuse_all, baseline -> results/scorecard_*.json, scorecard.md
    python scripts/run_harness.py --system baseline     # one system
    python scripts/run_harness.py --answers my.jsonl    # grade AnswerBlocks produced elsewhere (keyed by qid)

Scope: questions whose filings are in the shared index. Peer / 10-K questions are reported as pending until RAG shares
the multi-company chunks.jsonl; they need no code change, only the corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))
from rag.retrieve import Retriever  # noqa: E402
from systems import BaselineSystem, OracleSystem, RefuseAllSystem  # noqa: E402

from kpmg_eval.harness import grade, run, scorecard_markdown, versions  # noqa: E402
from kpmg_eval.metrics.diagnose import FactIndex  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
AVAILABLE = {"msft_10q_q3fy26", "none"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=["oracle", "refuse_all", "baseline", "all"], default="all")
    ap.add_argument("--answers", help="grade a jsonl of AnswerBlocks (with qid) instead of running a system")
    a = ap.parse_args()
    bench_path = DATA / "benchmark_v1.jsonl"
    bench = {q["qid"]: q for q in map(json.loads, open(bench_path))}
    suite = {s["sid"]: s for s in map(json.loads, open(DATA / "abstention_suite_v1.jsonl"))}
    items = [{"id": q["qid"], "question": q["question"], "session_ticker": "MSFT"} for q in bench.values() if q["corpus"] in AVAILABLE]
    items += [{"id": s["sid"], "question": s["question"], "session_ticker": "MSFT"} for s in suite.values()]
    pending = sum(1 for q in bench.values() if q["corpus"] not in AVAILABLE)
    retr = Retriever(ROOT / "upstream" / "rag_index_msft_lsa", log_dir=None)
    ver = versions(ROOT, bench_path, retr)
    fi = FactIndex.from_jsonl(DATA / "msft_xbrl_facts.jsonl")
    systems = {"oracle": OracleSystem(bench, suite), "refuse_all": RefuseAllSystem(), "baseline": BaselineSystem()}
    cards = []
    if a.answers:
        answers = [json.loads(l) for l in open(a.answers)]
        cards.append(grade(bench, suite, answers, {}, fi, ver, Path(a.answers).stem))
    else:
        for name in (systems if a.system == "all" else [a.system]):
            answers, rlog = run(systems[name], items, retr)
            (RES / f"answers_{name}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in answers))
            card = grade(bench, suite, answers, rlog, fi, ver, systems[name].name)
            card["n_pending_questions"] = pending
            cards.append(card)
            (RES / f"scorecard_{name}.json").write_text(json.dumps(card, indent=1))
            hl = card["headline"]
            print(f"[harness] {card['system']:16s} numeric={hl['numeric_accuracy']['value']} (n={hl['numeric_accuracy']['n']}) "
                  f"recall@10={hl['evidence_recall@10']['value']} refusal_bal={hl['refusal_balanced']['value']} "
                  f"(refuse un={hl['refusal_balanced']['appropriate_refusal_rate']}, ans={hl['refusal_balanced']['unnecessary_refusal_rate']}) "
                  f"citation={hl['citation_support']['value']} | {json.dumps(card['diagnostics'])}")
    (RES / "scorecard.md").write_text(scorecard_markdown(cards, pending))
    print(f"[harness] items {len(items)}, pending {pending}; versions {json.dumps(ver)}")


if __name__ == "__main__":
    main()
