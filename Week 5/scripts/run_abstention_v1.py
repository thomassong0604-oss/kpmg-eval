"""Abstention ("I don't know") handling: a paired test suite and a two-stage gate, scored with held-out thresholds.

    python scripts/run_abstention_v1.py   -> data/abstention_suite_v1.jsonl, results/abstention_v1.json

Suite. Gold Set v1 has only 7 unanswerable questions, too few to tune or trust a gate. The suite adds unanswerable
twins of answerable questions, so topic and wording are held constant and only answerability changes:
  future_period    same question, one year later (March 31, 2027): the filing does not exist yet
  outside_corpus   same question about a company that is not in the pilot corpus
  not_disclosed    in-scope company and period, but the filing gives no such figure (each checked against the filing
                   text: e.g. Azure revenue in dollars, Microsoft 365 seat count, consumer subscribers - "removed as a metric")
plus 5 more false-premise questions, which must NOT be refused but corrected (they test that the gate lets them through).

Gate.
  stage 1 scope check  extract company + period (kpmg_eval.filters.extract_filters, MVP session = MSFT); refuse if the
                       company or (fiscal_year, fiscal_period) filing is not in the corpus manifest (data/filing_pool_v1.json)
  stage 2 score gate   refuse if RAG's BM25 top-1 score (company filter only) is below a threshold. The threshold is
                       learned on 4/5 of the questions and applied to the held-out 1/5 (5-fold, twins kept in one fold),
                       so no question is scored with a threshold tuned on itself. Product setting: the threshold keeps
                       95% of the training folds' answerable questions. "score_balanced" (maximise balanced accuracy) is
                       reported to show why that is not the right objective.
Metrics: appropriate refusal rate (unanswerable refused), unnecessary refusal rate (answerable refused), balanced RAA.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "upstream" / "KPMG_RAG"))
from rag.retrieve import Retriever  # noqa: E402
from rag_fiscal import fiscal_label  # noqa: E402

from kpmg_eval.filters import extract_filters  # noqa: E402
from kpmg_eval.metrics.abstention import auroc, best_threshold  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
OTHER = ["Oracle", "Salesforce", "IBM", "Intel", "Adobe"]
NOT_DISCLOSED = [  # each: the 10-Q discloses only a growth rate or nothing (checked in the filing text)
    ("What was Azure and other cloud services revenue in dollars for the three months ended March 31, 2026?", "only the 40% growth rate is disclosed"),
    ("How many Microsoft 365 Commercial seats did Microsoft have at March 31, 2026?", "only seat growth (6%) is disclosed"),
    ("How many Microsoft 365 Consumer subscribers did Microsoft have at March 31, 2026?", "the filing says this metric was removed"),
    ("How much revenue did Microsoft 365 Copilot generate in the three months ended March 31, 2026?", "not disclosed"),
    ("How much revenue did GitHub Copilot generate in the three months ended March 31, 2026?", "not disclosed; only usage growth is mentioned"),
    ("How many datacenters did Microsoft operate at March 31, 2026?", "not disclosed"),
    ("How many Xbox consoles did Microsoft sell in the three months ended March 31, 2026?", "unit sales are not disclosed"),
    ("What was Microsoft's search advertising revenue excluding traffic acquisition costs, in dollars, for the three months ended March 31, 2026?", "only the growth rate is disclosed"),
    ("How much did Microsoft receive in revenue-sharing payments from OpenAI in the three months ended March 31, 2026?", "not disclosed"),
]
FALSE_PREMISE = [  # premise contradicted by the XBRL facts noted
    ("Why did Microsoft's Gaming revenue increase in the three months ended March 31, 2026?", "Gaming revenue fell: 5,341 vs 5,721"),
    ("Why did Intelligent Cloud operating income fall in the three months ended March 31, 2026?", "it rose: 13,753 vs 11,095"),
    ("What caused Microsoft's diluted earnings per share to decline in the three months ended March 31, 2026?", "it rose: 4.27 vs 3.46"),
    ("Why did Microsoft suspend its dividend in the three months ended March 31, 2026?", "it declared 0.91 per share"),
    ("Why did Microsoft cut research and development spending in the three months ended March 31, 2026?", "R&D rose: 8,915 vs 8,198"),
]


def fold(group: str) -> int:
    return int(hashlib.md5(group.encode()).hexdigest(), 16) % 5


def build_suite(bench):
    base = [q for q in bench if q["corpus"] == "msft_10q_q3fy26" and q["type"] in ("extraction", "segment") and q["answerable"]]
    suite, k = [], 0
    for q in base:
        if "March 31, 2026" in q["question"]:
            suite.append({"sid": f"AB-{len(suite) + 1:03d}", "kind": "future_period", "twin_of": q["qid"], "answerable": False,
                          "question": q["question"].replace("March 31, 2026", "March 31, 2027"),
                          "expected": "refuse: that filing is not in the corpus (period has not been reported)"})
        if re.search(r"Microsoft[’']s", q["question"]):
            name = OTHER[k % len(OTHER)]
            k += 1
            suite.append({"sid": f"AB-{len(suite) + 1:03d}", "kind": "outside_corpus", "twin_of": q["qid"], "answerable": False,
                          "question": re.sub(r"Microsoft([’']s)", name + r"\1", q["question"]),
                          "expected": f"refuse: {name} is not in the pilot corpus"})
    for text, why in NOT_DISCLOSED:
        suite.append({"sid": f"AB-{len(suite) + 1:03d}", "kind": "not_disclosed", "twin_of": None, "answerable": False,
                      "question": text, "expected": f"refuse: {why}"})
    for text, why in FALSE_PREMISE:
        suite.append({"sid": f"AB-{len(suite) + 1:03d}", "kind": "false_premise", "twin_of": None, "answerable": True,
                      "question": text, "expected": f"answer by correcting the premise: {why}"})
    return suite


def main():
    scope = json.loads((ROOT / "config" / "scope.json").read_text())
    pool = json.loads((DATA / "filing_pool_v1.json").read_text())["filings"]
    rag_fye = {"MSFT": "0630", "AAPL": "0927", "NVDA": "0126"}
    manifest = {(f["ticker"], *fiscal_label(f["reporting_period_end"], rag_fye.get(f["ticker"], "1231"), f["form"])) for f in pool}
    tickers = {f["ticker"] for f in pool}
    bench = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
    suite = build_suite(bench)
    with open(DATA / "abstention_suite_v1.jsonl", "w") as f:
        for s in suite:
            f.write(json.dumps(s) + "\n")

    # evaluation items: (id, group, kind, answerable, question)
    items = []
    for q in bench:
        if q["corpus"] == "msft_10q_q3fy26" and q["answerable"] and q["rag_evidence"]:
            items.append((q["qid"], q["qid"], "false_premise" if q["type"] == "false_premise" else "answerable", True, q["question"]))
        elif not q["answerable"]:
            items.append((q["qid"], q["qid"], "benchmark_unanswerable", False, q["question"]))
    for s in suite:
        items.append((s["sid"], s["twin_of"] or s["sid"], s["kind"], s["answerable"], s["question"]))

    retr = Retriever(ROOT / "upstream" / "rag_index_msft_lsa", log_dir=None)
    rows = []
    for iid, grp, kind, ans, text in items:
        flt = extract_filters(text, scope, fiscal_label, session_ticker=scope["mvp"]["ticker"])
        t = flt.get("ticker")
        reason = None
        if isinstance(t, str) and t not in tickers:
            reason = "company_not_in_corpus"
        elif isinstance(t, str) and "fiscal_year" in flt and (t, flt["fiscal_year"], flt.get("fiscal_period", "Q3")) not in manifest \
                and not (flt.get("fiscal_period") == "FY" and (t, flt["fiscal_year"], "FY") in manifest):
            reason = "period_not_in_corpus"
        if isinstance(t, str) and t in tickers:
            res = retr.search(text, filters={"ticker": t} if t == "MSFT" else {"ticker": "MSFT"}, top_k=1, method="bm25")["results"]
            score = res[0]["score"] if res and t == "MSFT" else 0.0
        else:
            score = 0.0
        rows.append({"id": iid, "group": grp, "fold": fold(grp), "kind": kind, "answerable": ans, "scope_refusal": reason,
                     "top1_score": score, "filters": flt})

    # stage-2 thresholds, learned out of fold
    for r in rows:
        train = [x for x in rows if x["fold"] != r["fold"] and x["scope_refusal"] is None]
        pos = [x["top1_score"] for x in train if x["answerable"]]
        neg = [x["top1_score"] for x in train if not x["answerable"]]
        r["threshold_balanced"] = best_threshold(pos, neg)["threshold"] if pos and neg else 0.0
        # product setting: keep >= 95% of answerable questions (wrongly refusing a real question is the costly error)
        r["threshold"] = sorted(pos)[int(0.05 * len(pos))] if pos else 0.0

    def decide(r, gate):
        if gate == "none":
            return False
        if gate == "scope":
            return r["scope_refusal"] is not None
        if gate == "score":
            return r["top1_score"] < r["threshold"]
        if gate == "score_balanced":
            return r["top1_score"] < r["threshold_balanced"]
        return r["scope_refusal"] is not None or r["top1_score"] < r["threshold"]

    summary = {}
    for gate in ("none", "scope", "score_balanced", "score", "scope+score"):
        ans = [r for r in rows if r["answerable"]]
        un = [r for r in rows if not r["answerable"]]
        refuse_un = sum(decide(r, gate) for r in un) / len(un)
        refuse_ans = sum(decide(r, gate) for r in ans) / len(ans)
        by = {}
        for kind in sorted({r["kind"] for r in rows}):
            ks = [r for r in rows if r["kind"] == kind]
            by[kind] = {"n": len(ks), "refused": sum(decide(r, gate) for r in ks)}
        summary[gate] = {"appropriate_refusal_rate": round(refuse_un, 3), "unnecessary_refusal_rate": round(refuse_ans, 3),
                         "balanced_raa": round((refuse_un + 1 - refuse_ans) / 2, 3), "by_kind": by}
    in_scope = [r for r in rows if r["scope_refusal"] is None]
    pos = [r["top1_score"] for r in in_scope if r["answerable"]]
    neg = [r["top1_score"] for r in in_scope if not r["answerable"]]
    out = {"n_items": len(rows), "n_answerable": sum(r["answerable"] for r in rows), "n_unanswerable": sum(not r["answerable"] for r in rows),
           "suite_size": len(suite), "suite_by_kind": {k: sum(1 for s in suite if s["kind"] == k) for k in sorted({s["kind"] for s in suite})},
           "score_auroc_in_scope": round(auroc(pos, neg), 3) if neg else None, "n_in_scope_unanswerable": len(neg),
           "gates": summary, "rows": rows}
    RES.mkdir(exist_ok=True)
    (RES / "abstention_v1.json").write_text(json.dumps(out, indent=1))
    print(f"[abstain] items {out['n_items']} (answerable {out['n_answerable']}, unanswerable {out['n_unanswerable']}); suite {out['suite_by_kind']}")
    print(f"[abstain] score AUROC on in-scope items: {out['score_auroc_in_scope']} ({len(neg)} in-scope unanswerable)")
    for g, s in summary.items():
        print(f"[abstain] {g:12s} refuse-unanswerable={s['appropriate_refusal_rate']:.2f} refuse-answerable={s['unnecessary_refusal_rate']:.2f} "
              f"balanced={s['balanced_raa']:.2f}  " + " ".join(f"{k}:{v['refused']}/{v['n']}" for k, v in s["by_kind"].items()))


if __name__ == "__main__":
    main()
