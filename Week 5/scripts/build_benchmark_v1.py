"""Build Gold Set v1: 100 questions shared by RAG, GraphRAG, Agents and Eval.

    python scripts/build_benchmark_v1.py

Composition
  * 30 questions = the RAG team's Gold Set v0 (eval/gold_v0_msft.jsonl @ KPMG_RAG 1996e72), kept under their
    qids and wording. We add typed expected answers, XBRL fact keys and graph paths, and audit every number.
  * 70 new questions (EV1-001..EV1-070) that fill the gaps Gold Set v0 lists for itself: cross-company,
    cross-document (10-K vs 10-Q), unanswerable / false-premise, balance sheet, segment and fiscal-calendar traps.

Every expected number is computed here from source facts, never typed:
  * Microsoft 10-Q (Q3 FY2026, accession 0001193125-26-191507): data/msft_xbrl_facts.jsonl, parsed from the
    XBRL instance in the Data Engineering repo (SHA-256 matches their source_manifest.json).
  * Peers and Microsoft's FY2026 10-K: data/peer_facts_v1.jsonl (SEC companyconcept API, each value read twice).

Outputs
  data/benchmark_v1.jsonl             full records (Eval format; superset of the RAG format)
  data/benchmark_v1_rag_format.jsonl  drop-in for `python -m rag.cli eval --gold ...` (RAG eval/README.md format)
  data/benchmark_v1_questions.csv     one row per question for humans (Business/UI review)
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAG_GOLD = ROOT / "upstream" / "KPMG_RAG" / "eval" / "gold_v0_msft.jsonl"
SCOPE = json.loads((ROOT / "config" / "scope.json").read_text())
import sys as _sys
_sys.path.insert(0, str(ROOT / "scripts"))

MSFT = {"ticker": "MSFT", "cik": "0000789019", "accession": "0001193125-26-191507", "form": "10-Q",
        "fiscal_year": 2026, "fiscal_period": "Q3"}
MSFT_10K = {"ticker": "MSFT", "cik": "0000789019", "accession": "0001193125-26-323660", "form": "10-K",
            "fiscal_year": 2026, "fiscal_period": "FY"}
PER = {  # period codes used below
    "Q": ("2026-01-01", "2026-03-31"), "QP": ("2025-01-01", "2025-03-31"),
    "YTD": ("2025-07-01", "2026-03-31"), "YTDP": ("2024-07-01", "2025-03-31"),
    "BS": (None, "2026-03-31"), "BSP": (None, "2025-06-30"),
}
SEG_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
PROD_AXIS = "srt:ProductOrServiceAxis"
GEO_AXIS = "srt:StatementGeographicalAxis"
SEG = {"PBP": "msft:ProductivityAndBusinessProcessesMember", "IC": "msft:IntelligentCloudMember",
       "MPC": "msft:MorePersonalComputingMember"}

# ------------------------------------------------------------------ facts
_facts = [json.loads(l) for l in open(DATA / "msft_xbrl_facts.jsonl")]
_peer = {r["fact_id"]: r for r in map(json.loads, open(DATA / "peer_facts_v1.jsonl"))}


def F(concept: str, per: str, member: str | None = None, axis: str | None = None) -> dict:
    """One MSFT 10-Q fact -> {value, key}. Raises if missing or ambiguous, so a typo cannot slip through."""
    start, end = PER[per]
    hits = []
    for r in _facts:
        if r["concept"] != concept or r["end"] != end or (r["start"] or None) != start:
            continue
        dims = r["dims"]
        if member is None and dims:
            continue
        if member is not None and (len(dims) != 1 or list(dims.values())[0] != member or (axis and axis not in dims)):
            continue
        hits.append(r)
    vals = {float(h["value"]) for h in hits}
    if len(vals) != 1:
        raise KeyError(f"{concept} {per} {member}: {len(hits)} hits {vals}")
    h = hits[0]
    unit = {"iso4217:USD": "USD", "iso4217:USD/shares": "USD/shares", "iso4217:USD/xbrli:shares": "USD/shares",
            "pure": "pure", "xbrli:pure": "pure", "shares": "shares", "xbrli:shares": "shares"}[h["unit"]]  # KeyError on anything new
    key = {"cik": MSFT["cik"], "accession": MSFT["accession"], "concept": concept, "period_start": start,
           "period_end": end, "unit": unit, "ticker": "MSFT", "level": "FACT"}
    if member:
        key["dims"] = {axis or list(h["dims"])[0]: member}
    return {"value": float(h["value"]), "key": key, "label": f"{concept.split(':')[1]}|{per}|{(member or '').split(':')[-1]}"}


def P(fact_id: str) -> dict:
    r = _peer[fact_id]
    key = {"cik": r["cik"], "accession": r["accession"], "concept": r["concept"], "period_start": r["period_start"],
           "period_end": r["period_end"], "unit": r["unit"], "ticker": r["ticker"], "level": "FACT"}
    return {"value": float(r["value"]), "key": key, "label": fact_id}


# ------------------------------------------------------------------ formatting
def mm(v: float) -> str:
    """USD -> '82,886' (millions, as displayed in the filing)."""
    m = v / 1e6
    return f"{m:,.0f}" if abs(m - round(m)) < 1e-9 else f"{m:,.2f}"


def paren(v: float) -> str:
    return f"({mm(-v)})" if v < 0 else mm(v)


def pct(x: float, nd: int = 2) -> str:
    return f"{x * 100:.{nd}f}%"


# ------------------------------------------------------------------ question builders
QUESTIONS: list[dict] = []


def fact_node_id(k: dict) -> str:
    """GraphRAG Fact node id: the FACT-level EvalKey, plus the XBRL member for dimensional (segment/product) facts."""
    base = f"{k['cik']}|{k['concept']}|{k['period_start']}|{k['period_end']}|{k['unit']}"
    return base + (f"|{list(k['dims'].values())[0]}" if k.get("dims") else "")


def _graph(facts: list[dict], pattern: str, extra_nodes: list[str] | None = None) -> dict:
    paths = []
    for f in facts:
        k = f["key"]
        node = fact_node_id(k)
        path = [[k["cik"], "FILED", k["accession"]], [k["accession"], "REPORTS", node]]
        if k.get("dims"):
            path.append([node, "FOR_MEMBER", list(k["dims"].values())[0]])
        paths.append(path)
    hops = len({json.dumps(f["key"], sort_keys=True) for f in facts})
    return {"pattern": pattern, "n_facts": hops, "paths": paths, "extra_nodes": extra_nodes or []}


def _distractors(concept: str, per: str, truth: float, member=None, axis=None, extra=None) -> list[dict]:
    """Same concept in the other periods = 'wrong_period'; explicit siblings = 'wrong_concept'."""
    out = []
    alt = {"Q": ["YTD", "QP"], "YTD": ["Q", "YTDP"], "QP": ["Q", "YTDP"], "YTDP": ["YTD", "QP"],
           "BS": ["BSP"], "BSP": ["BS"]}[per]
    for p in alt:
        try:
            v = F(concept, p, member, axis)["value"]
        except KeyError:
            continue
        if v != truth:
            out.append({"label": "wrong_period", "value": v, "note": f"{concept.split(':')[1]} {p}"})
    for lab, v, note in extra or []:
        if v != truth:
            out.append({"label": lab, "value": v, "note": note})
    return out


def add(qid, qtype, tier, question, *, answer, facts=(), calc=None, evidence=(), route="xbrl", traps=(),
        use_case=None, filters=None, corpus="msft_10q_q3fy26", answerable=True, distractors=(), graph_pattern=None,
        source="eval_v1", rag_qid=None, tickers=("MSFT",), notes=""):
    facts = list(facts)
    rec = {
        "qid": qid, "source": source, "rag_qid": rag_qid, "type": qtype, "tier": tier, "question": question,
        "answerable": answerable, "tickers": list(tickers), "corpus": corpus,
        "filters": filters if filters is not None else {"ticker": "MSFT", "form": "10-Q", "fiscal_year": 2026,
                                                        "fiscal_period": "Q3"},
        "answer": answer,
        "gold": None, "facts": [f["key"] for f in facts], "fact_values": {f["label"]: f["value"] for f in facts},
        "calculation": calc, "rag_evidence": list(evidence), "route": route, "traps": list(traps),
        "use_case": use_case,
        "graph": _graph(facts, graph_pattern or ("single_fact" if len(facts) == 1 else "multi_fact")) if facts else None,
        "status": "auto_verified" if answer.get("kind") not in ("text",) else "needs_human_review",
        "notes": notes,
        # Business/UI tags: single-company MVP vs future comparison scope; exact numeric vs narrative answers
        "scope": "mvp_single_company" if set(tickers) <= {"MSFT", "TSLA"} else "comparison",
        "answer_type": ("exact_numeric" if answer.get("value") is not None else
                        {"refusal": "refusal", "false_premise": "false_premise"}.get(answer.get("kind"),
                         "narrative" if route == "text" else "exact_categorical")),
    }
    if answer.get("value") is not None:  # Week-4 numeric grader format (kpmg_eval.metrics.numeric.score_numeric)
        rec["gold"] = {"value": answer["value"], "kind": answer["kind"], "min_sig_figs": answer.get("min_sig_figs", 3),
                       "evidence": [f["key"] for f in facts], "distractors": list(distractors)}
    QUESTIONS.append(rec)


def ev(region, *contains, is_table=None, meta=MSFT):
    e = {"region": region, "ticker": meta["ticker"], "form": meta["form"], "accession": meta["accession"],
         "contains": list(contains)}
    if is_table is not None:
        e["is_table"] = is_table
    return e


def money(v, extra_points=(), sf=None):
    disp = mm(v)
    # significant figures as displayed, ignoring trailing zeros (93,500 has 3, not 5); Week 5 fix found by the oracle run
    sig = sf or max(3, len(disp.replace(",", "").replace("-", "").replace(".", "").strip("0")) or 1)
    return {"kind": "money", "value": v, "unit": "USD", "display": f"USD {disp} million",
            "required_points": [disp, *extra_points], "min_sig_figs": sig, "tolerance": "exact at displayed USD millions"}


def ratio(x, extra_points=(), nd=2, kind="percent"):
    return {"kind": kind, "value": round(x * 100, nd), "unit": "%" if kind == "percent" else "pp",
            "display": pct(x, nd) if kind == "percent" else f"{x * 100:.{nd}f} pp",
            "required_points": [pct(x, nd) if kind == "percent" else f"{x * 100:.{nd}f}", *extra_points],
            "min_sig_figs": 3, "tolerance": f"±0.01 {'percentage point' if kind == 'percent' else 'pp'} after rounding to {nd} dp"}


def text(points, display=None):
    return {"kind": "text", "value": None, "unit": None, "display": display or "; ".join(points), "required_points": list(points)}


def refusal(reason, points=()):
    return {"kind": "refusal", "value": None, "unit": None, "display": reason,
            "required_points": ["declines or says the filing does not disclose it", *points]}


# =========================================================================== 30 RAG Gold Set v0 questions
def import_rag_gold():
    rag = [json.loads(l) for l in open(RAG_GOLD)]
    R = {r["qid"]: r for r in rag}
    rev_q, rev_qp = F("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "Q"), F("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "QP")
    rev_y, rev_yp = F("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "YTD"), F("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "YTDP")
    ni_q = F("us-gaap:NetIncomeLoss", "Q")
    cfo_y, cfo_yp = F("us-gaap:NetCashProvidedByUsedInOperatingActivities", "YTD"), F("us-gaap:NetCashProvidedByUsedInOperatingActivities", "YTDP")
    capex_y, capex_yp = F("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "YTD"), F("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "YTDP")
    seg = {s: {p: F("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", p, SEG[s], SEG_AXIS) for p in ("Q", "QP")} for s in SEG}
    oi = {s: F("us-gaap:OperatingIncomeLoss", "Q", SEG[s], SEG_AXIS) for s in ("PBP", "IC")}
    csti, csti_p = F("us-gaap:CashCashEquivalentsAndShortTermInvestments", "BS"), F("us-gaap:CashCashEquivalentsAndShortTermInvestments", "BSP")
    cfi_y = F("us-gaap:NetCashProvidedByUsedInInvestingActivities", "YTD")
    cff_y = F("us-gaap:NetCashProvidedByUsedInFinancingActivities", "YTD")
    fx_y = F("us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations", "YTD")
    cash, cash_p = F("us-gaap:CashAndCashEquivalentsAtCarryingValue", "BS"), F("us-gaap:CashAndCashEquivalentsAtCarryingValue", "BSP")

    g = rev_q["value"] / rev_qp["value"] - 1
    fcf, fcfp = cfo_y["value"] - capex_y["value"], cfo_yp["value"] - capex_yp["value"]
    m_pbp, m_ic = oi["PBP"]["value"] / seg["PBP"]["Q"]["value"], oi["IC"]["value"] / seg["IC"]["Q"]["value"]
    d_csti = csti["value"] - csti_p["value"]
    d_cash = cfo_y["value"] + cfi_y["value"] + cff_y["value"] + fx_y["value"]
    dseg = {s: seg[s]["Q"]["value"] - seg[s]["QP"]["value"] for s in SEG}
    h1, h1p = rev_y["value"] - rev_q["value"], rev_yp["value"] - rev_qp["value"]

    enrich = {  # qid -> (type, answer, facts, calc, traps, use_case, graph_pattern, distractors)
        "GSv0-MSFT-001": ("extraction", money(rev_q["value"], ["three months, not nine"]), [rev_q], "revenue_Q",
                          ["quarter_vs_ytd"], "compare_revenue", None,
                          _distractors(rev_q["key"]["concept"], "Q", rev_q["value"])),
        "GSv0-MSFT-002": ("extraction", money(ni_q["value"], ["GAAP"]), [ni_q], "net_income_Q", ["quarter_vs_ytd", "gaap_vs_non_gaap"],
                          "profitability", None, _distractors("us-gaap:NetIncomeLoss", "Q", ni_q["value"])),
        "GSv0-MSFT-003": ("extraction", money(cfo_y["value"], ["nine months"]), [cfo_y], "cfo_YTD", ["quarter_vs_ytd"], None, None,
                          _distractors("us-gaap:NetCashProvidedByUsedInOperatingActivities", "YTD", cfo_y["value"])),
        "GSv0-MSFT-013": ("calculation", ratio(g, ["increase", "12,820"]), [rev_q, rev_qp], "revenue_Q / revenue_QP - 1",
                          ["pct_vs_pp"], "compare_revenue", "multi_fact_same_filing", []),
        "GSv0-MSFT-014": ("calculation", money(fcf - fcfp, [mm(fcf), mm(fcfp), "increase"]), [cfo_y, capex_y, cfo_yp, capex_yp],
                          "(cfo_YTD - capex_YTD) - (cfo_YTDP - capex_YTDP)", ["non_gaap_definition"], None, "multi_fact_same_filing",
                          [{"label": "wrong_concept", "value": fcf, "note": "level, not change"}]),
        "GSv0-MSFT-015": ("calculation", ratio(m_pbp, [pct(m_ic), f"{(m_pbp - m_ic) * 100:.2f} percentage points", "PBP higher"]),
                          [oi["PBP"], seg["PBP"]["Q"], oi["IC"], seg["IC"]["Q"]], "OI_seg / Rev_seg", ["pct_vs_pp", "segment_vs_total"],
                          "profitability", "multi_fact_same_filing", [{"label": "wrong_dimension", "value": round(m_ic * 100, 2), "note": "IC margin"}]),
        "GSv0-MSFT-016": ("calculation", money(d_csti, [pct(d_csti / csti_p["value"]), "decrease"]), [csti, csti_p], "csti_BS - csti_BSP",
                          ["instant_vs_duration", "sign"], None, "multi_fact_same_filing",
                          [{"label": "wrong_sign", "value": -d_csti, "note": ""}]),
        "GSv0-MSFT-023": ("reconciliation", money(d_cash, [mm(cash_p["value"]), mm(cash["value"]), paren(fx_y["value"])]),
                          [cfo_y, cfi_y, cff_y, fx_y, cash_p, cash], "cfo + cfi + cff + fx = d_cash; cash_BSP + d_cash = cash_BS",
                          ["sign", "fx_included"], None, "multi_fact_same_filing", []),
        "GSv0-MSFT-024": ("reconciliation", ratio(dseg["IC"] / sum(dseg.values()), [mm(dseg["PBP"]), mm(dseg["IC"]), mm(dseg["MPC"]),
                                                                                     mm(sum(dseg.values()))]),
                          [seg[s][p] for s in SEG for p in ("Q", "QP")], "dIC / (dPBP + dIC + dMPC)", ["segment_vs_total"],
                          "compare_revenue", "multi_fact_same_filing", []),
        "GSv0-MSFT-025": ("derived", ratio(h1 / h1p - 1, [mm(h1), mm(h1p), "July 1 - December 31"]), [rev_y, rev_q, rev_yp, rev_qp],
                          "(rev_YTD - rev_Q) / (rev_YTDP - rev_QP) - 1", ["quarter_vs_ytd", "double_counting"], "derived_period",
                          "multi_fact_same_filing", []),
    }
    for r in rag:
        e = enrich.get(r["qid"])
        tier = r["tier"]
        if e:
            qtype, answer, facts, calc, traps, uc, gp, dis = e
            route = "xbrl"
        else:
            qtype = "narrative" if tier != "basic" else "definition"
            answer, facts, calc, traps, uc, gp, dis = text(r["required_points"], r["reference_answer"]), [], None, [], None, None, []
            route = "text"
            if r["qid"] in ("GSv0-MSFT-004", "GSv0-MSFT-005", "GSv0-MSFT-006", "GSv0-MSFT-007"):
                uc = "explain_term"
            if r["qid"] in ("GSv0-MSFT-008", "GSv0-MSFT-009", "GSv0-MSFT-012"):
                uc = "explain_term"
        add(r["qid"], qtype, tier, r["question"], answer=answer, facts=facts, calc=calc,
            evidence=r["gold"]["evidence"], route=route, traps=traps, use_case=uc,
            filters={"ticker": "MSFT", "form": "10-Q", "fiscal_year": 2026, "fiscal_period": "Q3"},
            distractors=dis, graph_pattern=gp, source="rag_gold_v0", rag_qid=r["qid"],
            notes="Wording and reference answer from RAG Gold Set v0; Eval added typed answer, fact keys and audit.")
        QUESTIONS[-1]["rag_reference_answer"] = r["reference_answer"]
        if answer["kind"] == "text":
            QUESTIONS[-1]["status"] = "needs_human_review"


# =========================================================================== 70 new questions
def build_new():
    n = iter(range(1, 200))
    q = lambda: f"EV1-{next(n):03d}"  # noqa: E731
    R = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"

    # ---- A. single-fact extraction, Microsoft 10-Q (16)
    def ext(concept, per, question, region, label, tier="basic", traps=("quarter_vs_ytd",), uc=None, member=None, axis=None,
            disp=None, extra=None, kind="money", table=True):
        f = F(concept, per, member, axis)
        v = f["value"]
        if kind == "money":
            ans = money(v)
            shown = mm(abs(v))  # bare number: RAG's parser renders negatives as "( 84,669)", so "(84,669)" never matches
        elif kind == "per_share":
            ans = {"kind": "money", "value": v, "unit": "USD/shares", "display": f"USD {v:.2f} per share",
                   "required_points": [f"{v:.2f}", "per share"], "min_sig_figs": 3, "tolerance": "exact to the cent"}
            shown = disp or f"{v:.2f}"
        elif kind == "count":
            ans = {"kind": "number", "value": v, "unit": "count", "display": f"{v:,.0f}", "required_points": [f"{v:,.0f}"],
                   "min_sig_figs": 1, "tolerance": "exact"}
            shown = disp or f"{v:,.0f}"
        add(q(), "segment" if member else "extraction", tier, question, answer=ans, facts=[f], calc=None,
            evidence=[ev(region, label, shown, is_table=table)], traps=traps, use_case=uc,
            distractors=_distractors(concept, per, v, member, axis, extra))

    ext("us-gaap:OperatingIncomeLoss", "Q", "What was Microsoft's operating income for the three months ended March 31, 2026, in USD millions?",
        "income", "Operating income", uc="profitability")
    ext("us-gaap:OperatingIncomeLoss", "YTD", "What was Microsoft's operating income for the nine months ended March 31, 2026, in USD millions?",
        "income", "Operating income", uc="profitability")
    ext("us-gaap:NetIncomeLoss", "YTD", "What was Microsoft's GAAP net income for the nine months ended March 31, 2026, in USD millions?",
        "income", "Net income", traps=("quarter_vs_ytd", "gaap_vs_non_gaap"), uc="profitability",
        extra=[("wrong_concept", 93_500e6, "adjusted (non-GAAP) net income, 9M")])
    ext("us-gaap:EarningsPerShareDiluted", "Q", "What were Microsoft's diluted earnings per share for the three months ended March 31, 2026?",
        "income", "Diluted", kind="per_share",
        extra=[("wrong_concept", F("us-gaap:EarningsPerShareBasic", "Q")["value"], "basic EPS")])
    ext("us-gaap:GrossProfit", "Q", "What was Microsoft's gross margin in dollars for the three months ended March 31, 2026, in USD millions?",
        "income", "Gross margin", uc="profitability")
    ext("us-gaap:ResearchAndDevelopmentExpense", "Q", "How much did Microsoft spend on research and development in the three months ended March 31, 2026, in USD millions?",
        "income", "Research and development")
    ext("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "Q",
        "How much cash did Microsoft spend on additions to property and equipment in the three months ended March 31, 2026, in USD millions?",
        "cashflow", "Additions to property and equipment", disp="(30,876)", traps=("quarter_vs_ytd", "sign"))
    ext("us-gaap:Assets", "BS", "What were Microsoft's total assets as of March 31, 2026, in USD millions?", "balance", "Total assets",
        traps=("instant_vs_duration",))
    ext("us-gaap:CashAndCashEquivalentsAtCarryingValue", "BS",
        "What was Microsoft's balance of cash and cash equivalents (excluding short-term investments) as of March 31, 2026, in USD millions?",
        "balance", "Cash and cash equivalents", traps=("instant_vs_duration", "concept_sibling"),
        extra=[("wrong_concept", F("us-gaap:CashCashEquivalentsAndShortTermInvestments", "BS")["value"], "cash + short-term investments")])
    ext("us-gaap:StockholdersEquity", "BS", "What was Microsoft's total stockholders' equity as of March 31, 2026, in USD millions?",
        "balance", "Total stockholders’ equity", traps=("instant_vs_duration",))
    ext("us-gaap:LongTermDebtNoncurrent", "BS",
        "What was Microsoft's long-term debt (the non-current portion shown on the balance sheet) as of March 31, 2026, in USD millions?",
        "balance", "Long-term debt", traps=("instant_vs_duration", "concept_sibling"),
        extra=[("wrong_concept", F("us-gaap:LongTermDebtCurrent", "BS")["value"], "current portion"),
               ("wrong_concept", F("us-gaap:LongTermDebt", "BS")["value"], "total incl. current portion")])
    ext("us-gaap:ContractWithCustomerLiabilityCurrent", "BS", "What was Microsoft's current unearned revenue as of March 31, 2026, in USD millions?",
        "balance", "Unearned revenue", traps=("instant_vs_duration", "concept_sibling"),
        extra=[("wrong_concept", F("us-gaap:ContractWithCustomerLiability", "BS")["value"], "total contract liability")])
    ext("us-gaap:NetCashProvidedByUsedInInvestingActivities", "YTD",
        "What was Microsoft's net cash flow from investing activities for the nine months ended March 31, 2026? Give the amount with its sign in USD millions.",
        "cashflow", "Net cash used in investing", traps=("quarter_vs_ytd", "sign"))
    ext("us-gaap:PaymentsForRepurchaseOfCommonStock", "YTD",
        "How much cash did Microsoft spend repurchasing common stock in the nine months ended March 31, 2026, according to the cash flow statement?",
        "cashflow", "Common stock repurchased", disp="(17,692)", traps=("quarter_vs_ytd",))
    ext("us-gaap:CommonStockDividendsPerShareDeclared", "Q", "What dividend per share did Microsoft declare for the three months ended March 31, 2026?",
        "dividends", "0.91", disp="0.91", kind="per_share", table=None)
    f = F("us-gaap:EffectiveIncomeTaxRateContinuingOperations", "YTD")
    add(q(), "extraction", "basic", "What effective tax rate did Microsoft report for the nine months ended March 31, 2026?",
        answer={"kind": "percent", "value": round(f["value"] * 100, 2), "unit": "%", "display": "20%", "required_points": ["20%", "nine months"],
                "min_sig_figs": 1, "tolerance": "exact as disclosed (whole percent)"},
        facts=[f], evidence=[ev("tax", "effective tax rate was 19% and 18%", "20% and 18% for the nine months")],
        route="xbrl+text", traps=["quarter_vs_ytd"],
        distractors=[{"label": "wrong_period", "value": 19.0, "note": "3M FY26"}, {"label": "wrong_period", "value": 18.0, "note": "prior year"}])

    # ---- B. segments and disaggregated revenue (9)
    ext(R, "Q", "What was Intelligent Cloud segment revenue for the three months ended March 31, 2026, in USD millions?",
        "segments", "Intelligent Cloud", member=SEG["IC"], axis=SEG_AXIS, traps=("quarter_vs_ytd", "segment_vs_total"), uc="compare_revenue")
    ext("us-gaap:OperatingIncomeLoss", "Q",
        "What was operating income of the Productivity and Business Processes segment for the three months ended March 31, 2026, in USD millions?",
        "segments", "Productivity and Business Processes", member=SEG["PBP"], axis=SEG_AXIS, traps=("quarter_vs_ytd", "segment_vs_total"),
        uc="profitability", tier="basic")
    ext(R, "Q", "What was More Personal Computing segment revenue for the three months ended March 31, 2026, in USD millions?",
        "segments", "More Personal Computing", member=SEG["MPC"], axis=SEG_AXIS, traps=("quarter_vs_ytd", "segment_vs_total"))
    ext(R, "Q", "How much revenue did Microsoft's Gaming products and services generate in the three months ended March 31, 2026, in USD millions?",
        "revenue_by_product", "Gaming", member="msft:GamingMember", axis=PROD_AXIS, traps=("quarter_vs_ytd",))
    ext(R, "YTD", "What was LinkedIn revenue for the nine months ended March 31, 2026, in USD millions?",
        "revenue_by_product", "LinkedIn", member="msft:LinkedInCorporationMember", axis=PROD_AXIS, traps=("quarter_vs_ytd",))
    ext(R, "Q", "What was revenue from Server products and cloud services for the three months ended March 31, 2026, in USD millions?",
        "revenue_by_product", "Server products and cloud services", member="msft:ServerProductsAndCloudServicesMember", axis=PROD_AXIS,
        traps=("quarter_vs_ytd",), extra=[("wrong_dimension", F(R, "Q", SEG["IC"], SEG_AXIS)["value"], "Intelligent Cloud segment total")])
    ext(R, "Q", "How much of Microsoft's revenue for the three months ended March 31, 2026 came from the United States, in USD millions?",
        "revenue_by_geography", "United States", member="country:US", traps=("quarter_vs_ytd",),
        extra=[("wrong_dimension", F(R, "Q", "us-gaap:NonUsMember")["value"], "other countries")])
    oi = {s: F("us-gaap:OperatingIncomeLoss", "Q", SEG[s], SEG_AXIS) for s in SEG}
    top = max(oi, key=lambda s: oi[s]["value"])
    names = {"PBP": "Productivity and Business Processes", "IC": "Intelligent Cloud", "MPC": "More Personal Computing"}
    add(q(), "comparison", "comparative",
        "Which of Microsoft's three reportable segments earned the most operating income in the three months ended March 31, 2026, and how much?",
        answer={**money(oi[top]["value"], [names[top]]), "display": f"{names[top]}, USD {mm(oi[top]['value'])} million"},
        facts=list(oi.values()), calc="argmax(OI_seg)", evidence=[ev("segments", "Productivity and Business Processes", mm(oi["PBP"]["value"]),
                                                                       mm(oi["IC"]["value"]), mm(oi["MPC"]["value"]))],
        traps=["segment_vs_total"], use_case="profitability", graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_dimension", "value": oi[s]["value"], "note": names[s]} for s in SEG if s != top])
    a, b = F(R, "YTD", SEG["MPC"], SEG_AXIS), F(R, "YTDP", SEG["MPC"], SEG_AXIS)
    add(q(), "comparison", "comparative",
        "How did More Personal Computing revenue for the nine months ended March 31, 2026 compare with the same period a year earlier? Give the change in USD millions.",
        answer={**money(a["value"] - b["value"], [mm(a["value"]), "unchanged"]), "display": f"Unchanged: USD {mm(a['value'])} million in both periods"},
        facts=[a, b], calc="MPC_YTD - MPC_YTDP", evidence=[ev("segments", "More Personal Computing", mm(a["value"]))],
        traps=["quarter_vs_ytd"], use_case="compare_revenue", graph_pattern="multi_fact_same_filing",
        notes="Both nine-month values are 41,198 in the XBRL; segment sums reconcile to total revenue in both years.")

    # ---- C. calculations (12)
    rq, rqp = F(R, "Q"), F(R, "QP")
    oiq, oiqp = F("us-gaap:OperatingIncomeLoss", "Q"), F("us-gaap:OperatingIncomeLoss", "QP")
    add(q(), "calculation", "comparative",
        "What was Microsoft's operating margin (operating income divided by total revenue) for the three months ended March 31, 2026? Round to two decimals.",
        answer=ratio(oiq["value"] / rq["value"]), facts=[oiq, rq], calc="OI_Q / REV_Q",
        evidence=[ev("income", "Operating income", mm(oiq["value"])), ev("income", "Total revenue", mm(rq["value"]))],
        traps=["quarter_vs_ytd"], use_case="profitability", graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_period", "value": round(F("us-gaap:OperatingIncomeLoss", "YTD")["value"] / F(R, "YTD")["value"] * 100, 2), "note": "9M margin"}])
    d = oiq["value"] / rq["value"] - oiqp["value"] / rqp["value"]
    add(q(), "calculation", "comparative",
        "By how many percentage points did Microsoft's quarterly operating margin change from the three months ended March 31, 2025 to the three months ended March 31, 2026?",
        answer=ratio(d, [pct(oiq["value"] / rq["value"]), pct(oiqp["value"] / rqp["value"]), "increase"], kind="pp"),
        facts=[oiq, rq, oiqp, rqp], calc="OI_Q/REV_Q - OI_QP/REV_QP", traps=["pct_vs_pp"], use_case="profitability",
        evidence=[ev("income", "Operating income", mm(oiq["value"]), mm(oiqp["value"]))], graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_concept", "value": round((oiq["value"] / oiqp["value"] - 1) * 100, 2), "note": "operating income growth %"}])
    gq, gqp = F("us-gaap:GrossProfit", "Q"), F("us-gaap:GrossProfit", "QP")
    d = gq["value"] / rq["value"] - gqp["value"] / rqp["value"]
    add(q(), "calculation", "comparative",
        "Calculate Microsoft's gross margin percentage for the three months ended March 31, 2026 and 2025, and the change in percentage points.",
        answer=ratio(d, [pct(gq["value"] / rq["value"]), pct(gqp["value"] / rqp["value"]), "decrease"], kind="pp"),
        facts=[gq, rq, gqp, rqp], calc="GP_Q/REV_Q - GP_QP/REV_QP", traps=["pct_vs_pp", "dollars_vs_ratio"], use_case="profitability",
        evidence=[ev("income", "Gross margin", mm(gq["value"]), mm(gqp["value"]))], graph_pattern="multi_fact_same_filing",
        notes="Numeric companion to GSv0-MSFT-027 (gross margin dollars up, percentage down).")
    ni, nip = F("us-gaap:NetIncomeLoss", "Q"), F("us-gaap:NetIncomeLoss", "QP")
    add(q(), "calculation", "comparative",
        "By what percentage did Microsoft's net income grow year over year in the three months ended March 31, 2026? Round to two decimals.",
        answer=ratio(ni["value"] / nip["value"] - 1, [mm(ni["value"]), mm(nip["value"])]), facts=[ni, nip], calc="NI_Q / NI_QP - 1",
        evidence=[ev("income", "Net income", mm(ni["value"]), mm(nip["value"]))], traps=["quarter_vs_ytd"], use_case="profitability",
        graph_pattern="multi_fact_same_filing")
    ry, ryp = F(R, "YTD"), F(R, "YTDP")
    add(q(), "calculation", "comparative",
        "What was Microsoft's year-over-year total revenue growth for the nine months ended March 31, 2026? Round to two decimals.",
        answer=ratio(ry["value"] / ryp["value"] - 1), facts=[ry, ryp], calc="REV_YTD / REV_YTDP - 1",
        evidence=[ev("income", "Total revenue", mm(ry["value"]), mm(ryp["value"]))], traps=["quarter_vs_ytd"], use_case="compare_revenue",
        graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_period", "value": round((rq["value"] / rqp["value"] - 1) * 100, 2), "note": "quarterly growth"}])
    cx = F("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "Q")
    add(q(), "calculation", "comparative",
        "What share of its quarterly revenue did Microsoft spend on cash additions to property and equipment in the three months ended March 31, 2026? Round to two decimals.",
        answer=ratio(cx["value"] / rq["value"], [mm(cx["value"])]), facts=[cx, rq], calc="CAPEX_Q / REV_Q",
        evidence=[ev("cashflow", "Additions to property and equipment", "30,876"), ev("income", "Total revenue", mm(rq["value"]))],
        traps=["quarter_vs_ytd"], graph_pattern="multi_fact_same_filing")
    tax, pbt = F("us-gaap:IncomeTaxExpenseBenefit", "Q"), F("us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "Q")
    add(q(), "calculation", "comparative",
        "Compute Microsoft's effective tax rate for the three months ended March 31, 2026 from the income statement (provision for income taxes divided by income before income taxes), to two decimals. How does it compare with the rate the filing reports?",
        answer=ratio(tax["value"] / pbt["value"], [mm(tax["value"]), mm(pbt["value"]), "reported 19%"]), facts=[tax, pbt],
        calc="TAX_Q / PBT_Q", evidence=[ev("income", "Provision for income taxes", mm(tax["value"]))], route="xbrl+text",
        traps=["rounding_disclosed_vs_computed"], graph_pattern="multi_fact_same_filing")
    oiy, ricy = F("us-gaap:OperatingIncomeLoss", "YTD", SEG["IC"], SEG_AXIS), F(R, "YTD", SEG["IC"], SEG_AXIS)
    add(q(), "calculation", "comparative",
        "What was the Intelligent Cloud segment's operating margin for the nine months ended March 31, 2026? Round to two decimals.",
        answer=ratio(oiy["value"] / ricy["value"], [mm(oiy["value"]), mm(ricy["value"])]), facts=[oiy, ricy], calc="OI_IC_YTD / REV_IC_YTD",
        evidence=[ev("segments", "Intelligent Cloud", mm(oiy["value"]), mm(ricy["value"]))], traps=["quarter_vs_ytd", "segment_vs_total"],
        use_case="profitability", graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_period", "value": round(oi["IC"]["value"] / F(R, "Q", SEG["IC"], SEG_AXIS)["value"] * 100, 2), "note": "3M IC margin"}])
    ca, cl = F("us-gaap:AssetsCurrent", "BS"), F("us-gaap:LiabilitiesCurrent", "BS")
    add(q(), "calculation", "comparative", "What was Microsoft's current ratio (total current assets divided by total current liabilities) as of March 31, 2026? Round to two decimals.",
        answer={"kind": "number", "value": round(ca["value"] / cl["value"], 2), "unit": "ratio", "display": f"{ca['value'] / cl['value']:.2f}x",
                "required_points": [f"{ca['value'] / cl['value']:.2f}", mm(ca["value"]), mm(cl["value"])], "min_sig_figs": 3, "tolerance": "±0.01"},
        facts=[ca, cl], calc="CA_BS / CL_BS", evidence=[ev("balance", "Total current assets", mm(ca["value"])),
                                                       ev("balance", "Total current liabilities", mm(cl["value"]))],
        traps=["instant_vs_duration"], graph_pattern="multi_fact_same_filing")
    dv, rp = F("us-gaap:PaymentsOfDividendsCommonStock", "YTD"), F("us-gaap:PaymentsForRepurchaseOfCommonStock", "YTD")
    dd = F("us-gaap:DividendsCommonStockCash", "YTD")
    add(q(), "calculation", "comparative",
        "How much cash did Microsoft return to shareholders through dividends paid and share repurchases in the nine months ended March 31, 2026, according to the cash flow statement?",
        answer=money(dv["value"] + rp["value"], [mm(dv["value"]), mm(rp["value"])]), facts=[dv, rp], calc="DIV_PAID_YTD + BUYBACK_YTD",
        evidence=[ev("cashflow", "Common stock cash dividends paid", "19,687"), ev("cashflow", "Common stock repurchased", "17,692")],
        traps=["paid_vs_declared"], graph_pattern="multi_fact_same_filing",
        distractors=[{"label": "wrong_concept", "value": dd["value"] + rp["value"], "note": "dividends declared instead of paid"}])
    cloud_q = 54.5e9
    add(q(), "calculation", "deep",
        "Microsoft Cloud revenue is disclosed in the filing's text. What share of total revenue did it represent in the three months ended March 31, 2026? Round to one decimal.",
        answer={**ratio(cloud_q / rq["value"], ["54.5 billion", mm(rq["value"])], nd=1), "min_sig_figs": 3,
                "tolerance": "±0.1 percentage point (the cloud figure is disclosed to one decimal in billions)"},
        facts=[rq], calc="54.5e9 / REV_Q  (Microsoft Cloud revenue from MD&A text; not an XBRL fact)",
        evidence=[ev("cloud_definition", "Microsoft Cloud revenue", "$54.5 billion"), ev("income", "Total revenue", mm(rq["value"]))],
        route="xbrl+text", traps=["cross_cutting_vs_segment"], use_case="explain_term", graph_pattern="text_plus_fact")
    # ---- D. derived periods and reconciliations (8)
    for lab, concept, ytd, fy_id, uc in [("revenue", R, ry, "MSFT_REV_FY26", "derived_period"),
                                         ("operating income", "us-gaap:OperatingIncomeLoss", F("us-gaap:OperatingIncomeLoss", "YTD"), "MSFT_OI_FY26", "derived_period"),
                                         ("net income", "us-gaap:NetIncomeLoss", F("us-gaap:NetIncomeLoss", "YTD"), "MSFT_NI_FY26", "derived_period")]:
        fy = P(fy_id)
        add(q(), "derived", "deep",
            f"Microsoft does not file a 10-Q for its fourth fiscal quarter. Using the FY2026 10-K and the Q3 FY2026 10-Q, derive Microsoft's {lab} for the three months ended June 30, 2026, in USD millions.",
            answer=money(fy["value"] - ytd["value"], [mm(fy["value"]), mm(ytd["value"]), "annual minus nine months"]),
            facts=[fy, ytd], calc="FY_10K - YTD_Q3_10Q", corpus="msft_10k_fy26+msft_10q_q3fy26",
            filters={"ticker": "MSFT", "fiscal_year": 2026, "fiscal_period": ["FY", "Q3"]},
            evidence=[ev("10k_income", mm(fy["value"]), meta=MSFT_10K), ev("income", mm(ytd["value"]))],
            traps=["derived_period", "cross_document"], use_case=uc, graph_pattern="cross_filing",
            distractors=[{"label": "wrong_period", "value": fy["value"], "note": "annual"}, {"label": "wrong_period", "value": ytd["value"], "note": "nine months"}],
            notes="Business/UI prototype use case: 'Q4 derived from annual less Q1-Q3'. Needs the FY2026 10-K (accession 0001193125-26-323660) in the index.")
    segoi = [F("us-gaap:OperatingIncomeLoss", "Q", SEG[s], SEG_AXIS) for s in SEG]
    add(q(), "reconciliation", "deep",
        "Do the three segments' operating incomes for the three months ended March 31, 2026 add up to Microsoft's consolidated operating income? Show the sum in USD millions.",
        answer=money(sum(f["value"] for f in segoi), [mm(oiq["value"]), "yes"] + [mm(f["value"]) for f in segoi]),
        facts=segoi + [oiq], calc="sum(OI_seg_Q) == OI_Q", evidence=[ev("segments", *[mm(f["value"]) for f in segoi])],
        traps=["segment_vs_total"], graph_pattern="multi_fact_same_filing")
    opx = [F(c, "Q") for c in ("us-gaap:ResearchAndDevelopmentExpense", "us-gaap:SellingAndMarketingExpense", "us-gaap:GeneralAndAdministrativeExpense")]
    add(q(), "reconciliation", "deep",
        "Reconstruct Microsoft's operating income for the three months ended March 31, 2026 from gross margin and the three operating expense lines. Show the calculation in USD millions.",
        answer=money(gq["value"] - sum(f["value"] for f in opx), [mm(gq["value"])] + [mm(f["value"]) for f in opx]),
        facts=[gq] + opx, calc="GP_Q - (RD_Q + SM_Q + GA_Q)", evidence=[ev("income", "Gross margin", mm(gq["value"]))],
        graph_pattern="multi_fact_same_filing")
    add(q(), "reconciliation", "deep",
        "Microsoft reports adjusted net income that excludes OpenAI investment effects. Using GAAP net income and the after-tax OpenAI adjustment, what was adjusted net income for the nine months ended March 31, 2026, in USD millions?",
        answer=money(F("us-gaap:NetIncomeLoss", "YTD")["value"] - 4_483e6, [mm(F("us-gaap:NetIncomeLoss", "YTD")["value"]), "(4,483)", "non-GAAP"]),
        facts=[F("us-gaap:NetIncomeLoss", "YTD")], calc="NI_YTD - 4,483 (after-tax OpenAI net gains, non-GAAP table; not an XBRL fact)",
        evidence=[ev("tax_nongaap", "Net (gains) losses from investments in OpenAI, net of tax", "(4,483)")], route="xbrl+text",
        traps=["gaap_vs_non_gaap", "quarter_vs_ytd"], graph_pattern="text_plus_fact",
        distractors=[{"label": "wrong_concept", "value": F("us-gaap:NetIncomeLoss", "YTD")["value"], "note": "GAAP net income"}])
    mr, mrp = F(R, "Q", SEG["MPC"], SEG_AXIS), F(R, "QP", SEG["MPC"], SEG_AXIS)
    mo, mop = F("us-gaap:OperatingIncomeLoss", "Q", SEG["MPC"], SEG_AXIS), F("us-gaap:OperatingIncomeLoss", "QP", SEG["MPC"], SEG_AXIS)
    mc, mcp = F("us-gaap:CostOfGoodsAndServicesSold", "Q", SEG["MPC"], SEG_AXIS), F("us-gaap:CostOfGoodsAndServicesSold", "QP", SEG["MPC"], SEG_AXIS)
    add(q(), "reconciliation", "deep",
        "More Personal Computing revenue fell year over year in the three months ended March 31, 2026, yet its operating income rose. Quantify both changes and the change in its cost of revenue, in USD millions.",
        answer=money(mo["value"] - mop["value"], [mm(mr["value"] - mrp["value"]), mm(mc["value"] - mcp["value"]), "cost of revenue fell"]),
        facts=[mr, mrp, mo, mop, mc, mcp], calc="dOI_MPC; dREV_MPC; dCOGS_MPC",
        evidence=[ev("segments", "More Personal Computing", mm(mo["value"]))], traps=["segment_vs_total", "sign"],
        graph_pattern="multi_fact_same_filing", notes="Numeric companion to GSv0-MSFT-026.")

    # ---- E. narrative / text-only (6)
    narr = [
        ("By what percentage did Azure and other cloud services revenue grow in the three months ended March 31, 2026?",
         ["40%"], [ev("quarter_overview", "Azure and other cloud services revenue increased 40%")], "quarter_vs_ytd"),
        ("What was Microsoft Cloud revenue for the three months ended March 31, 2026, and how fast did it grow?",
         ["$54.5 billion", "29%"], [ev("quarter_overview", "Microsoft Cloud revenue increased 29% to $54.5 billion")], None),
        ("What was Microsoft's commercial remaining performance obligation, and by how much did it increase?",
         ["$627 billion", "99%"], [ev("quarter_overview", "Commercial remaining performance obligation increased 99% to $627 billion")], "concept_sibling"),
        ("Approximately what percentage of OpenAI does Microsoft own, and how does it account for the investment?",
         ["approximately 27 percent", "as-converted basis", "equity method"],
         [ev("openai_accounting", "approximately 27 percent of OpenAI on an as-converted basis", "equity method")], None),
        ("Why was Microsoft's effective tax rate lower than the U.S. federal statutory rate in the periods ended March 31, 2026?",
         ["earnings taxed at lower rates in foreign jurisdictions", "foreign regional operations center in Ireland"],
         [ev("tax", "lower than the U.S. federal statutory rate", "foreign regional operations center in Ireland")], None),
        ("What drove the increase in Microsoft's sales and marketing expenses in the three months ended March 31, 2026, and by how much did they rise?",
         ["higher Copilot advertising expenses", "$602 million", "10%"],
         [ev("opex", "Sales and marketing expenses increased $602 million or 10%", "Copilot advertising")], "quarter_vs_ytd"),
    ]
    for question, pts, evs, trap in narr:
        add(q(), "narrative", "basic", question, answer=text(pts), evidence=evs, route="text", traps=[trap] if trap else [],
            use_case="explain_term")

    # ---- F. cross-company, calendar Q1 2026 (13)
    from rag_fiscal import fiscal_label  # RAG's own rule (rag.ingest.fiscal_label), vendored as a pure function
    PEERS = {}
    for p in SCOPE["peers"]:
        fid = f"{p['ticker']}_REV_{SCOPE['comparison_frame'].replace('2026', '26')}"
        end = _peer[fid]["period_end"]
        fy, fp = fiscal_label(end, p["fye"], "10-Q")
        PEERS[p["ticker"]] = (p["name"], fy, fp, p["period_phrase"])
    acc = {t: _peer[f"{t}_REV_CY26Q1"]["accession"] for t in PEERS}

    def pmeta(t):
        return {"ticker": t, "form": "10-Q", "accession": acc[t]}

    def pfilt(ts):
        if len(ts) == 1:
            t = ts[0]
            return {"ticker": t, "form": "10-Q", "fiscal_year": PEERS[t][1], "fiscal_period": PEERS[t][2]}
        return {"ticker": list(ts), "form": "10-Q"}

    for t, (lab, kind) in ((p["ticker"], p["spotlight"]) for p in SCOPE["peers"]):
        f = P(f"{t}_{lab}_CY26Q1")
        add(q(), "cross_company", "basic", f"What was {PEERS[t][0]}'s {kind} for its {PEERS[t][3]}, in USD millions?",
            answer=money(f["value"]), facts=[f], evidence=[ev("income", mm(f["value"]), meta=pmeta(t))], tickers=[t],
            filters=pfilt([t]), corpus="peer_10q_cy26q1", traps=["fiscal_calendar"] if PEERS[t][2] != "Q1" or PEERS[t][1] != 2026 else [],
            notes="Evidence anchor not yet checked against the RAG corpus (peer chunks are not public); verify once RAG shares chunks.jsonl.")
    T5 = ["MSFT"] + list(PEERS)
    NAMES = ", ".join(["Microsoft"] + [PEERS[t][0] for t in list(PEERS)[:-1]]) + " and " + PEERS[list(PEERS)[-1]][0]
    rev = {"MSFT": rq, **{t: P(f"{t}_REV_CY26Q1") for t in PEERS}}
    opi = {"MSFT": oiq, **{t: P(f"{t}_OI_CY26Q1") for t in PEERS}}
    nin = {"MSFT": ni, **{t: P(f"{t}_NI_CY26Q1") for t in PEERS}}
    cname = {"MSFT": "Microsoft", **{t: PEERS[t][0] for t in PEERS}}
    cf = {"ticker": T5, "form": "10-Q"}
    best = max(T5, key=lambda t: rev[t]["value"])
    add(q(), "cross_company", "comparative",
        f"Among {NAMES}, which company reported the highest revenue for its fiscal quarter that ended in March or April 2026, and how much?",
        answer={**money(rev[best]["value"], [cname[best]]), "display": f"{cname[best]}, USD {mm(rev[best]['value'])} million"},
        facts=[rev[t] for t in T5], calc="argmax(REV)", tickers=T5, filters=cf, corpus="peer_10q_cy26q1",
        evidence=[ev("income", mm(rev[t]["value"]), meta=pmeta(t) if t != "MSFT" else MSFT) for t in T5],
        traps=["fiscal_calendar"], use_case="compare_revenue", graph_pattern="cross_company",
        distractors=[{"label": "wrong_concept", "value": rev[t]["value"], "note": cname[t]} for t in T5 if t != best])
    margins = {t: opi[t]["value"] / rev[t]["value"] for t in T5}
    order = sorted(T5, key=lambda t: -margins[t])
    add(q(), "cross_company", "deep",
        f"Rank {NAMES} by operating margin (operating income / revenue) for their fiscal quarters that ended in March or April 2026. Which is highest, and what is its margin to two decimals?",
        answer={**ratio(margins[order[0]], [cname[t] for t in order] + [pct(margins[t]) for t in order]),
                "display": " > ".join(f"{cname[t]} {pct(margins[t])}" for t in order)},
        facts=[x for t in T5 for x in (opi[t], rev[t])], calc="sort(OI/REV)", tickers=T5, filters=cf, corpus="peer_10q_cy26q1",
        evidence=[ev("income", mm(opi[t]["value"]), mm(rev[t]["value"]), meta=pmeta(t) if t != "MSFT" else MSFT) for t in T5],
        traps=["fiscal_calendar", "pct_vs_pp"], use_case="profitability", graph_pattern="cross_company")
    above = [t for t in T5 if nin[t]["value"] > opi[t]["value"]]
    add(q(), "cross_company", "deep",
        f"For the fiscal quarters ended in March or April 2026, which of {NAMES} reported net income higher than operating income?",
        answer=text([cname[t] for t in above] + [f"{cname[t]}: NI {mm(nin[t]['value'])} vs OI {mm(opi[t]['value'])}" for t in above],
                    display=", ".join(cname[t] for t in above)),
        facts=[x for t in T5 for x in (nin[t], opi[t])], calc="NI > OI", tickers=T5, filters=cf, corpus="peer_10q_cy26q1",
        evidence=[ev("income", mm(nin[t]["value"]), meta=pmeta(t)) for t in above], route="xbrl", traps=["fiscal_calendar"],
        graph_pattern="cross_company")
    QUESTIONS[-1]["status"] = "auto_verified"
    add(q(), "cross_company", "comparative",
        f"What was the combined revenue of {NAMES} for their fiscal quarters that ended in March or April 2026, in USD millions?",
        answer=money(sum(rev[t]["value"] for t in T5), [mm(rev[t]["value"]) for t in T5]), facts=[rev[t] for t in T5], calc="sum(REV)",
        tickers=T5, filters=cf, corpus="peer_10q_cy26q1", traps=["fiscal_calendar"], graph_pattern="cross_company",
        evidence=[ev("income", mm(rev[t]["value"]), meta=pmeta(t) if t != "MSFT" else MSFT) for t in T5])
    add(q(), "cross_company", "basic",
        "NVIDIA's 10-Q covers the quarter ended April 26, 2026. Which fiscal year and fiscal quarter is that, under the Retrieval API rule that the fiscal year is the calendar year in which the fiscal year ends?",
        answer=text(["fiscal year 2027", "Q1"], display="FY2027 Q1"), facts=[rev["NVDA"]], tickers=["NVDA"],
        filters={"ticker": "NVDA", "form": "10-Q"}, corpus="peer_10q_cy26q1", route="metadata", traps=["fiscal_calendar"],
        evidence=[ev("cover", "April 26, 2026", meta=pmeta("NVDA"))],
        notes="Tests fiscal_label(): NVDA fiscal year ends late January, so a quarter ending in April 2026 is FY2027 Q1.")
    QUESTIONS[-1]["status"] = "auto_verified"
    gap = nin["AMZN"]["value"] - opi["AMZN"]["value"]
    add(q(), "cross_company", "comparative",
        "By how much did Amazon's net income exceed its operating income in Q1 2026 (quarter ended March 31, 2026), in USD millions?",
        answer=money(gap, [mm(nin["AMZN"]["value"]), mm(opi["AMZN"]["value"])]), facts=[nin["AMZN"], opi["AMZN"]], calc="NI - OI",
        tickers=["AMZN"], filters=pfilt(["AMZN"]), corpus="peer_10q_cy26q1", graph_pattern="multi_fact_same_filing",
        evidence=[ev("income", mm(nin["AMZN"]["value"]), meta=pmeta("AMZN"))], traps=["sign"])
    add(q(), "cross_company", "comparative",
        "Compare Microsoft's and Meta's operating margins for the quarter ended March 31, 2026. Which is higher, and by how many percentage points?",
        answer={**ratio(margins["MSFT"] - margins["META"], ["Microsoft", pct(margins["MSFT"]), pct(margins["META"])], kind="pp"),
                "display": f"Microsoft higher by {(margins['MSFT'] - margins['META']) * 100:.2f} pp"},
        facts=[opi["MSFT"], rev["MSFT"], opi["META"], rev["META"]], calc="OI/REV MSFT - OI/REV META", tickers=["MSFT", "META"],
        filters={"ticker": ["MSFT", "META"], "form": "10-Q"}, corpus="peer_10q_cy26q1", traps=["pct_vs_pp"], use_case="profitability",
        evidence=[ev("income", mm(opi["META"]["value"]), meta=pmeta("META")), ev("income", "Operating income", mm(oiq["value"]))],
        graph_pattern="cross_company")
    # ---- G. unanswerable, out of scope, false premise (10)
    unans = [
        ("unanswerable", "What was Azure's revenue in dollars for the three months ended March 31, 2026?",
         refusal("The filing gives only Azure's growth rate (40%), not its dollar revenue", ["40%", "does not invent a dollar figure"]),
         "msft_10q_q3fy26", ["not_disclosed"], [ev("quarter_overview", "Azure and other cloud services revenue increased 40%")]),
        ("unanswerable", "What was Microsoft's share price at the close on March 31, 2026?",
         refusal("Share prices are not in the 10-Q"), "msft_10q_q3fy26", ["out_of_scope"], []),
        ("unanswerable", "What revenue will Microsoft report for the quarter ending June 30, 2027?",
         refusal("A forecast; filings report historical results", ["no forecast"]), "none", ["out_of_scope", "future_period"], []),
        ("unanswerable", "What was Tesla's total revenue for the quarter ended March 31, 2026?",
         refusal("Tesla is not in the pilot corpus", ["names corpus scope"]), "none", ["entity_not_in_corpus"], []),
        ("unanswerable", "What was Microsoft's revenue for the three months ended September 30, 2026?",
         refusal("That 10-Q is outside the corpus snapshot", ["no figure from another period"]), "none", ["future_period", "wrong_period_bait"], []),
        ("unanswerable", "How many employees did Microsoft have on March 31, 2026?",
         refusal("The 10-Q says headcount declined year over year but gives no number", ["headcount declined"]), "msft_10q_q3fy26",
         ["not_disclosed"], [ev("opex", "headcount declined year-over-year")]),
        ("unanswerable", "Should I buy Microsoft stock based on this quarter's results?",
         refusal("Investment advice is out of scope", ["can summarize results instead"]), "none", ["out_of_scope", "advice"], []),
        ("false_premise", "Why did Microsoft's total revenue decline in the three months ended March 31, 2026?",
         {"kind": "false_premise", "value": None, "unit": None, "display": "Premise is false: revenue rose 18.30% to USD 82,886 million",
          "required_points": ["rejects the premise", "82,886", "70,066", "increase"]},
         "msft_10q_q3fy26", ["false_premise"], [ev("income", "Total revenue", "82,886", "70,066")]),
        ("false_premise", "How large was Microsoft's net loss for the nine months ended March 31, 2026?",
         {"kind": "false_premise", "value": None, "unit": None, "display": "Premise is false: net income was USD 97,983 million",
          "required_points": ["rejects the premise", "net income", "97,983"]},
         "msft_10q_q3fy26", ["false_premise", "sign"], [ev("income", "Net income", "97,983")]),
        ("false_premise", "What was the operating income of Microsoft's 'Microsoft Cloud' reportable segment for the three months ended March 31, 2026?",
         {"kind": "false_premise", "value": None, "unit": None,
          "display": "Premise is false: Microsoft Cloud is a cross-cutting revenue metric, not a reportable segment; no operating income is reported for it",
          "required_points": ["not a reportable segment", "three segments", "no operating income disclosed"]},
         "msft_10q_q3fy26", ["false_premise", "cross_cutting_vs_segment"], [ev("cloud_definition", "Microsoft Cloud revenue")]),
    ]
    for qtype, question, ans, corpus, traps, evs in unans:
        add(q(), qtype, "basic" if qtype == "unanswerable" else "comparative", question, answer=ans, evidence=evs, route="refusal",
            traps=traps, corpus=corpus, answerable=qtype != "unanswerable", use_case="scope_guidance",
            filters={"ticker": "TSLA"} if "Tesla" in question else None)
        QUESTIONS[-1]["status"] = "auto_verified" if qtype == "unanswerable" else "needs_human_review"
        if QUESTIONS[-1]["filters"] is None:
            QUESTIONS[-1]["filters"] = {"ticker": "MSFT"}


# =========================================================================== write
def to_rag_format(r: dict) -> dict:
    """RAG eval/README.md format: qid, tier, question, filters, gold{chunk_ids, evidence}, expected, quantitative, status."""
    evid = []
    for e in r["rag_evidence"]:
        x = {k: v for k, v in e.items() if k in ("region", "ticker", "form", "accession", "is_table", "contains", "chunk_ids", "section")}
        evid.append(x)
    f = r["filters"]
    exp = {"ticker": f["ticker"] if isinstance(f.get("ticker"), list) else [f.get("ticker")]}
    return {"qid": r["qid"], "tier": r["tier"], "question": r["question"],
            "filters": {k: v for k, v in f.items() if k in ("ticker", "cik", "form", "accession_number", "fiscal_year", "fiscal_period", "is_table")},
            "gold": {"chunk_ids": [], "evidence": evid}, "expected": exp,
            "quantitative": r["answer"]["kind"] in ("money", "percent", "pp", "number"),
            "answerable": r["answerable"], "reference_answer": r["answer"]["display"],
            "required_points": r["answer"]["required_points"], "status": "draft", "notes": f"Gold Set v1 ({r['source']}); type={r['type']}"}


TYPE_TITLES = [("extraction", "Extraction (single fact)"), ("segment", "Segment and disaggregated revenue"),
               ("calculation", "Calculation"), ("comparison", "Comparison"), ("derived", "Derived periods"),
               ("reconciliation", "Reconciliation"), ("definition", "Definition"), ("narrative", "Narrative"),
               ("cross_company", "Cross-company"), ("unanswerable", "Unanswerable / out of scope"), ("false_premise", "False premise")]


def write_markdown(rows):
    out = ["# Gold Set v1: 100 questions", "",
           "Generated by `scripts/build_benchmark_v1.py`; do not edit by hand. `RAG` = from the RAG team's Gold Set v0 "
           "(their wording and id), `new` = added by Eval. Expected answers are computed from SEC XBRL facts.", ""]
    for t, title in TYPE_TITLES:
        qs = [r for r in rows if r["type"] == t]
        out += [f"## {title} ({len(qs)})", "", "| # | Question | Expected answer | Src | Tier |", "|---|---|---|---|---|"]
        for r in qs:
            ans = r["answer"]["display"].replace("|", "/")
            if len(ans) > 160:
                ans = ans[:157] + "..."
            out.append(f"| {r['qid']} | {r['question'].replace('|', '/')} | {ans} | {'RAG' if r['source'] == 'rag_gold_v0' else 'new'} | {r['tier']} |")
        out.append("")
    (DATA / "benchmark_v1_questions.md").write_text("\n".join(out))


def main():
    import_rag_gold()
    build_new()
    assert len(QUESTIONS) == 100, len(QUESTIONS)
    assert len({r["qid"] for r in QUESTIONS}) == 100
    with open(DATA / "benchmark_v1.jsonl", "w") as f:
        for r in QUESTIONS:
            f.write(json.dumps(r) + "\n")
    with open(DATA / "benchmark_v1_rag_format.jsonl", "w") as f:
        for r in QUESTIONS:
            if r["rag_evidence"]:  # RAG's loader skips items without evidence; unanswerables stay in the Eval file
                f.write(json.dumps(to_rag_format(r)) + "\n")
    with open(DATA / "benchmark_v1_questions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "source", "type", "tier", "tickers", "question", "expected_answer", "route", "traps", "corpus", "status"])
        for r in QUESTIONS:
            w.writerow([r["qid"], r["source"], r["type"], r["tier"], " ".join(r["tickers"]), r["question"], r["answer"]["display"],
                        r["route"], " ".join(r["traps"]), r["corpus"], r["status"]])
    write_markdown(QUESTIONS)
    c = Counter(r["type"] for r in QUESTIONS)
    print("[bench] 100 questions:", dict(c))
    print("[bench] tiers:", dict(Counter(r["tier"] for r in QUESTIONS)), " sources:", dict(Counter(r["source"] for r in QUESTIONS)))
    print("[bench] answerable:", sum(r["answerable"] for r in QUESTIONS), " numeric:", sum(r["gold"] is not None for r in QUESTIONS))


if __name__ == "__main__":
    main()
