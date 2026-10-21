"""Validate Gold Set v1 before anyone scores a system on it.

    python scripts/validate_benchmark_v1.py      -> results/benchmark_v1_validation.json

1. Anchors: every Microsoft 10-Q evidence item must match >= 1 chunk of the filing as RAG chunks it, using
   RAG's own rule (rag/evaluate.py: all `contains` strings, case-insensitive substring). Anchors that match
   many chunks are flagged as weak (they would let an irrelevant chunk count as a hit).
2. Answer points: for Eval's own text and refusal questions, every quoted figure or phrase must occur in the filing text.
3. RAG Gold Set v0 audit: for the 10 quantitative RAG questions, the numbers Eval computes from XBRL must
   appear in RAG's reference answer.
4. Accounting identities that tie the facts together (segments sum to total, cash-flow roll-forward,
   derived six-month revenue equals the separately filed Q2 YTD fact).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
MSFT_ACC = "0001193125-26-191507"


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def main():
    bench = load(DATA / "benchmark_v1.jsonl")
    chunks = load(DATA / "rag_chunks_msft_10q.jsonl")
    low = [c["text"].lower() for c in chunks]
    fulltext = re.sub(r"\s+", " ", "\n".join(c["text"] for c in chunks)).lower()
    out = {"anchors": [], "answer_points": [], "rag_audit": [], "identities": []}

    # 1. anchors
    for q in bench:
        for e in q["rag_evidence"]:
            if e.get("accession") != MSFT_ACC:
                out["anchors"].append({"qid": q["qid"], "region": e.get("region"), "status": "not_checkable_offline",
                                       "accession": e.get("accession")})
                continue
            cs = [s.lower() for s in e.get("contains", [])]
            n = sum(all(s in t for s in cs) for t in low)
            if e.get("is_table") is not None:
                n = sum(all(s in t for s in cs) and c["is_table"] == e["is_table"] for t, c in zip(low, chunks))
            status = "ok" if 1 <= n <= 3 else ("broad" if n > 3 else "no_match")
            out["anchors"].append({"qid": q["qid"], "region": e.get("region"), "contains": e.get("contains"), "n_chunks": n,
                                   "status": status})

    # 2. answer points for Eval-authored text / refusal / false-premise questions on the MSFT 10-Q
    for q in bench:
        if q["source"] != "eval_v1" or q["answer"]["kind"] not in ("text", "refusal", "false_premise"):
            continue
        if q["corpus"] != "msft_10q_q3fy26":
            continue
        for p in q["answer"]["required_points"]:
            literal = bool(re.search(r"\d", p)) or q["type"] == "narrative"
            if not literal:
                continue
            ok = re.sub(r"\s+", " ", p.lower()) in fulltext
            out["answer_points"].append({"qid": q["qid"], "point": p, "found_in_filing": ok})

    # 3. audit RAG reference answers
    for q in bench:
        if q["source"] != "rag_gold_v0" or q["answer"]["kind"] == "text":
            continue
        ref = q["rag_reference_answer"]
        ref_nums = {abs(float(x.replace(",", ""))) for x in re.findall(r"\d[\d,]*\.?\d*", ref)}
        pts = [q["answer"]["display"]] + q["answer"]["required_points"][1:]
        checks = []
        for p in pts:
            nums = [abs(float(x.replace(",", ""))) for x in re.findall(r"\d[\d,]*\.?\d*", p)]
            if not nums:
                continue
            checks.append({"point": p, "in_reference": all(n in ref_nums for n in nums)})  # sign/wording-insensitive
        out["rag_audit"].append({"qid": q["qid"], "eval_value": q["answer"]["display"], "checks": checks,
                                 "agrees": all(c["in_reference"] for c in checks)})

    # 4. identities
    facts = {}
    for q in bench:
        facts.update(q["fact_values"])
    peer = {r["fact_id"]: r["value"] for r in load(DATA / "peer_facts_v1.jsonl")}
    R = "RevenueFromContractWithCustomerExcludingAssessedTax"
    def fv(name, per, mem=""):
        return facts[f"{name}|{per}|{mem}"]
    ids = [
        ("segment revenue sums to total, 3M FY26", sum(fv(R, "Q", m) for m in ("ProductivityAndBusinessProcessesMember", "IntelligentCloudMember", "MorePersonalComputingMember")), fv(R, "Q")),
        ("segment revenue sums to total, 3M FY25", sum(fv(R, "QP", m) for m in ("ProductivityAndBusinessProcessesMember", "IntelligentCloudMember", "MorePersonalComputingMember")), fv(R, "QP")),
        ("segment operating income sums to total, 3M FY26", sum(fv("OperatingIncomeLoss", "Q", m) for m in ("ProductivityAndBusinessProcessesMember", "IntelligentCloudMember", "MorePersonalComputingMember")), fv("OperatingIncomeLoss", "Q")),
        ("gross margin - opex = operating income, 3M FY26", fv("GrossProfit", "Q") - fv("ResearchAndDevelopmentExpense", "Q") - fv("SellingAndMarketingExpense", "Q") - fv("GeneralAndAdministrativeExpense", "Q"), fv("OperatingIncomeLoss", "Q")),
        ("cash roll-forward, 9M FY26", fv("CashAndCashEquivalentsAtCarryingValue", "BSP") + fv("NetCashProvidedByUsedInOperatingActivities", "YTD") + fv("NetCashProvidedByUsedInInvestingActivities", "YTD") + fv("NetCashProvidedByUsedInFinancingActivities", "YTD") + fv("EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations", "YTD"), fv("CashAndCashEquivalentsAtCarryingValue", "BS")),
        ("derived H1 FY26 revenue (9M - Q3) = separately filed Q2 10-Q YTD fact", fv(R, "YTD") - fv(R, "Q"), peer["MSFT_REV_CY25Q4"]),
        ("SEC API = local XBRL, revenue 3M FY26", 82_886e6, fv(R, "Q")),
    ]
    for name, a, b in ids:
        out["identities"].append({"identity": name, "lhs": a, "rhs": b, "holds": abs(a - b) < 0.5})

    st = Counter(a["status"] for a in out["anchors"])
    summary = {
        "n_questions": len(bench),
        "anchors": dict(st),
        "anchors_matching_pct": round(100 * (st["ok"] + st["broad"]) / max(1, st["ok"] + st["broad"] + st["no_match"]), 1),
        "answer_points_found": f"{sum(p['found_in_filing'] for p in out['answer_points'])}/{len(out['answer_points'])}",
        "rag_audit_agree": f"{sum(a['agrees'] for a in out['rag_audit'])}/{len(out['rag_audit'])}",
        "identities_hold": f"{sum(i['holds'] for i in out['identities'])}/{len(out['identities'])}",
    }
    out["summary"] = summary
    RES.mkdir(exist_ok=True)
    (RES / "benchmark_v1_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))
    for a in out["anchors"]:
        if a["status"] == "no_match":
            print("  ANCHOR", a["status"], a["qid"], a["region"], a.get("contains"), a.get("n_chunks"))
    for p in out["answer_points"]:
        if not p["found_in_filing"]:
            print("  POINT missing", p["qid"], repr(p["point"]))
    for a in out["rag_audit"]:
        if not a["agrees"]:
            print("  AUDIT", a["qid"], a["checks"])
    for i in out["identities"]:
        if not i["holds"]:
            print("  IDENTITY FAILS", i)


if __name__ == "__main__":
    main()
