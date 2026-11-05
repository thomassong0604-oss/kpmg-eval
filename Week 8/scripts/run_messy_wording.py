"""Week 8: typos and messy wording (11/5 minutes, Eval item 7: estimate real-user accuracy).

    python scripts/run_messy_wording.py   -> data/messy_wording_v1.jsonl, results/messy_wording.json

Every Gold Set v2 question gets up to three rewrites that keep its meaning (fixed rules, no randomness):
  typo_company   the company name misspelled the way people type it (Microsfot, Mircon, Net App, Caseys, ...)
  typo_terms     one or two finance words misspelled (revnue, opertaing, subsidaries, ...)
  casual         lower case, ticker instead of name, no punctuation, no "State the amount in ..." instruction
Then the clean and messy versions go through the same steps:
  scope gate    Eval's rule_gate (answer / clarify / abstain / off_topic), with and without a session company
  router        Eval's keyword router (which tools get called)
  retrieval     on the Microsoft 10-Q questions: RAG BM25 and GraphRAG structured_search (as in run_side_by_side.py).
                The filters stay the clean ones, so this isolates the retrievers from filter extraction.
Score = how often the messy version gets the result the clean version should get. Gate and router are Eval's reference
rules, not the Agents' orchestrator; the point is the size of the drop and where it comes from.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from kpmg_eval.metrics.decision import expected_decision  # noqa: E402
from kpmg_eval.metrics.routing import REQUIRED  # noqa: E402
import difflib  # noqa: E402

import run_decision_baselines as rdb  # noqa: E402
from run_decision_baselines import COMPANIES, rule_gate  # noqa: E402
from run_routing_baselines import keyword  # noqa: E402
import run_side_by_side as sbs  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"

COMPANY_TYPOS = [("Microsoft", "Microsfot"), ("Apple", "Aple"), ("Micron", "Mircon"), ("NetApp", "Net App"),
                 ("Casey's", "Caseys"), ("Take-Two", "Take Two Interactive"), ("Parker-Hannifin", "Parker Hanifin"),
                 ("Medtronic", "Medtronics"), ("McKesson", "McKeson"), ("Nike", "Nkie")]
TERM_TYPOS = [("revenue", "revnue"), ("operating", "opertaing"), ("subsidiaries", "subsidaries"), ("income", "incom"),
              ("quarter", "quater"), ("margin", "margn"), ("percentage", "precentage"), ("segment", "segmnet"),
              ("fiscal", "fiscla"), ("months", "monhts"), ("cash", "csah"), ("acquired", "aquired"),
              ("Exhibit", "Exibit"), ("calculate", "calcuate"), ("reportable", "reportible"), ("difference", "diference")]
TICKER_OF = {"Microsoft": "msft", "Apple": "aapl", "Micron": "mu", "NetApp": "ntap", "Casey's": "casey's",
             "Take-Two": "ttwo", "Parker-Hannifin": "ph", "Medtronic": "mdt", "McKesson": "mck", "Nike": "nke"}
INSTRUCTION = re.compile(r"\s*(State|Give|Answer|Report|Express|Round)[^.?]*\.\s*$")


def typo_company(q: str) -> str:
    for a, b in COMPANY_TYPOS:
        q = q.replace(a, b)
    return q


def typo_terms(q: str) -> str:
    n = 0
    for a, b in TERM_TYPOS:
        if n < 2 and re.search(rf"\b{a}\b", q, re.I):
            q = re.sub(rf"\b{a}\b", b, q, count=1, flags=re.I)
            n += 1
    return q


def casual(q: str) -> str:
    q = INSTRUCTION.sub("", q.replace("’", "'"))
    for a, t in TICKER_OF.items():
        q = re.sub(rf"{re.escape(a)}('s)?", t, q)
    q = re.sub(r"[?,;:()]", "", q).rstrip(".").lower()
    return re.sub(r"\s+", " ", q).strip()


def companies_in_fuzzy(q: str) -> list[str]:
    """Same as rule_gate's company check, plus tickers and near-miss spellings (difflib ratio >= 0.8)."""
    found = rdb.companies_in_exact(q)
    words = re.findall(r"[a-z][a-z'\-]+", q.lower().replace("\u2019", "'"))
    grams = words + [" ".join(p) for p in zip(words, words[1:])]
    for t, names in COMPANIES.items():
        if t in found:
            continue
        if t.lower() in words:
            found.append(t)
            continue
        cands = [n.replace("'s", "") for n in names]
        if any(difflib.get_close_matches(g.replace("'s", ""), cands, n=1, cutoff=0.8) for g in grams):
            found.append(t)
    return found


def rule_gate_fuzzy(question: str, session):
    rdb.companies_in = companies_in_fuzzy
    try:
        return rdb.rule_gate(question, session)
    finally:
        rdb.companies_in = rdb.companies_in_exact


rdb.companies_in_exact = rdb.companies_in


PERTURB = {"typo_company": typo_company, "typo_terms": typo_terms, "casual": casual}


def main():
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2.jsonl")]
    variants = []
    for q in gold:
        for name, fn in PERTURB.items():
            m = fn(q["question"])
            if m != q["question"]:
                variants.append({"vid": f"{q['qid']}~{name}", "qid": q["qid"], "perturbation": name, "clean": q["question"],
                                 "messy": m})
    (DATA / "messy_wording_v1.jsonl").write_text("".join(json.dumps(v) + "\n" for v in variants))
    gq = {q["qid"]: q for q in gold}

    # gate + router on all 155 questions
    gate = defaultdict(lambda: Counter())
    router = defaultdict(lambda: Counter())
    gate_examples, router_examples = [], []
    for v in variants:
        q = gq[v["qid"]]
        exp = expected_decision(q)
        sess = q["tickers"][0] if len(q["tickers"]) == 1 and q["tickers"][0] in COMPANIES else None
        for mode, s, gate_fn in (("no_session", None, rule_gate), ("with_session", sess, rule_gate),
                                 ("no_session_fuzzy_names", None, rule_gate_fuzzy)):
            clean_d, _ = gate_fn(v["clean"], s)
            messy_d, _ = gate_fn(v["messy"], s)
            c = gate[(v["perturbation"], mode)]
            c["n"] += 1
            c["clean_correct"] += clean_d == exp
            c["messy_correct"] += messy_d == exp
            c["flipped"] += clean_d != messy_d
            if mode == "no_session" and clean_d == exp and messy_d != exp and len(gate_examples) < 12:
                gate_examples.append({**v, "expected": exp, "messy_decision": messy_d})
        need = REQUIRED[q["route_expected"]]
        cs = sess
        rc, rm = keyword(v["clean"], cs), keyword(v["messy"], cs)
        ok = lambda got: (not got) if not need else need <= got  # noqa: E731
        c = router[v["perturbation"]]
        c["n"] += 1
        c["clean_required_called"] += ok(rc)
        c["messy_required_called"] += ok(rm)
        c["route_changed"] += rc != rm
        if rc != rm and ok(rc) and not ok(rm) and len(router_examples) < 12:
            router_examples.append({**v, "expected": q["route_expected"], "clean_route": sorted(rc), "messy_route": sorted(rm)})

    # retrieval on the Microsoft 10-Q questions
    retr = sbs.build_rag(DATA / "rag_chunks_msft_10q.jsonl", sbs.UP / "rag_index_w8_messy")
    os.environ["MSFT_FACT_DB_PATH"] = str(sbs.STORE)
    ret = defaultdict(lambda: Counter())
    for v in variants:
        q = gq[v["qid"]]
        if q["corpus"] != sbs.CORPUS or sbs.kind(q) == "unanswerable_or_false_premise":
            continue
        for system in ("rag_bm25", "graphrag_structured"):
            res = {}
            for label, text in (("clean", v["clean"]), ("messy", v["messy"])):
                qq = {**q, "question": text}
                if system == "rag_bm25":
                    texts, _ = sbs.rag_run(retr, qq, "bm25")
                    res[label] = sbs.score_rag(q, texts).get("needed_in_evidence")
                else:
                    ev, _ = sbs.gr_run(qq)
                    res[label] = sbs.score_gr(q, ev).get("needed_in_evidence")
            if res["clean"] is None:
                continue
            c = ret[(v["perturbation"], system)]
            c["n"] += 1
            c["clean"] += res["clean"]
            c["messy"] += res["messy"]
            c["lost"] += res["clean"] and not res["messy"]
            c["gained"] += (not res["clean"]) and res["messy"]

    pct = lambda a, b: round(a / b, 3) if b else None  # noqa: E731
    out = {
        "_doc": "Clean vs messy wording on Gold Set v2 (155 questions). Gate and router are Eval's reference rules.",
        "n_variants": len(variants), "per_perturbation": dict(Counter(v["perturbation"] for v in variants)),
        "gate": {f"{p}|{m}": {"n": c["n"], "clean_acc": pct(c["clean_correct"], c["n"]), "messy_acc": pct(c["messy_correct"], c["n"]),
                              "decision_flipped": c["flipped"]} for (p, m), c in gate.items()},
        "router": {p: {"n": c["n"], "clean_required_called": pct(c["clean_required_called"], c["n"]),
                       "messy_required_called": pct(c["messy_required_called"], c["n"]), "route_changed": c["route_changed"]}
                   for p, c in router.items()},
        "retrieval_msft_10q": {f"{p}|{s}": {"n": c["n"], "clean": pct(c["clean"], c["n"]), "messy": pct(c["messy"], c["n"]),
                                            "lost": c["lost"], "gained": c["gained"]} for (p, s), c in ret.items()},
        "gate_examples": gate_examples, "router_examples": router_examples,
    }
    RES.mkdir(exist_ok=True)
    (RES / "messy_wording.json").write_text(json.dumps(out, indent=1))
    for sec in ("gate", "router", "retrieval_msft_10q"):
        print(sec)
        for k, v in out[sec].items():
            print("  ", k, v)
    for e in gate_examples[:6]:
        print(" gate miss:", e["perturbation"], e["expected"], "->", e["messy_decision"], "|", e["messy"][:90])
    for e in router_examples[:6]:
        print(" route miss:", e["perturbation"], e["expected"], e["clean_route"], "->", e["messy_route"], "|", e["messy"][:90])


if __name__ == "__main__":
    main()
