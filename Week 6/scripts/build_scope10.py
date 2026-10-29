"""Week 6: re-scope the gold set to the Data team's 10 companies (Emma, 10/28).

    python scripts/build_scope10.py
      -> data/scope10_filings.json        the 21 filings Eval assumes are in the DB (10 10-K + 11 10-Q)
      -> data/scope10_facts.jsonl         revenue and net income facts, each read twice from the SEC API
      -> data/benchmark_scope10_new.jsonl new questions (EV2-*) on the 8 added companies + 10-company comparisons
      -> data/benchmark_scope10.jsonl     Gold Set v1 questions still in scope + EV2-* (what round 1 should run)
      -> data/benchmark_scope10_status.csv every v1 question: in scope or retired, and why
      -> results/scope10_checks.json      read-1 vs read-2 agreement, quarter sums, duplicate-period agreement
      -> results/scope10_coverage.json    what the 21 filings support, for the reply to Data

Gold Set v1 itself is not modified (hash unchanged). Values are never typed into questions: every answer is
computed here from data/scope10_facts.jsonl, which is built from two independent reads of
https://data.sec.gov/api/xbrl/companyconcept/ (data/sec_reads/read1_companyconcept.tsv, read2_targeted.tsv;
both read 2026-10-29). The build stops if the two reads disagree or a quarterly identity fails.

Which filings are in the DB: Data reported 21 filings for the 10 companies (10 10-Ks, 11 10-Qs) but did not list
them. GraphRAG listed 5 (AAPL x3, MSFT x2). Eval assumes the rest are each company's latest 10-K and latest 10-Q
filed by 2026-10-13 (the end of Data's window). That reproduces both counts exactly; it is still an assumption
until Data confirms the accession numbers.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES, READS = ROOT / "data", ROOT / "results", ROOT / "data" / "sec_reads"
API = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
REV, NI, PL = ("RevenueFromContractWithCustomerExcludingAssessedTax", "NetIncomeLoss", "ProfitLoss")

# name, cik, fiscal-year-end description, revenue concept, net income concept,
# latest 10-K (accession, fiscal year), latest 10-Q(s) (accession, fiscal year, fiscal quarter)
COMPANIES = {
    "AAPL": ("Apple", "0000320193", "last Saturday of September", REV, NI,
             ("0000320193-25-000079", 2025), [("0000320193-26-000013", 2026, "Q2"), ("0000320193-26-000020", 2026, "Q3")]),
    "CASY": ("Casey's", "0000726958", "April 30", "Revenues", NI,
             ("0000726958-26-000046", 2026), [("0000726958-26-000085", 2027, "Q1")]),
    "MCK": ("McKesson", "0000927653", "March 31", REV, NI,
            ("0000927653-26-000069", 2026), [("0000927653-26-000234", 2027, "Q1")]),
    "MDT": ("Medtronic", "0001613103", "last Friday of April", REV, NI,
            ("0001628280-26-044354", 2026), [("0001628280-26-060473", 2027, "Q1")]),
    "MSFT": ("Microsoft", "0000789019", "June 30", REV, NI,
             ("0001193125-26-323660", 2026), [("0001193125-26-191507", 2026, "Q3")]),
    "MU": ("Micron", "0000723125", "Thursday closest to August 31", REV, NI,
           ("0000723125-25-000028", 2025), [("0000723125-26-000015", 2026, "Q3")]),
    "NKE": ("Nike", "0000320187", "May 31", REV, NI,
            ("0000320187-26-000088", 2026), [("0000320187-26-000193", 2027, "Q1")]),
    "NTAP": ("NetApp", "0001002047", "last Friday of April", REV, NI,
             ("0001193125-26-259683", 2026), [("0001193125-26-380207", 2027, "Q1")]),
    "PH": ("Parker-Hannifin", "0000076334", "June 30", REV, PL,
           ("0000076334-26-000105", 2026), [("0000076334-26-000073", 2026, "Q3")]),
    "TTWO": ("Take-Two", "0000946581", "March 31", REV, NI,
             ("0001628280-26-037434", 2026), [("0001628280-26-054870", 2027, "Q1")]),
}
RETIRED_TICKERS = {"AMZN", "META", "NVDA"}  # Gold Set v1 peers that are not in Data's 10
CORPUS = "scope10_db"
MONTHS = "January February March April May June July August September October November December".split()


def d(s: str) -> date:
    return date.fromisoformat(s)


def long_date(s: str) -> str:
    x = d(s)
    return f"{MONTHS[x.month - 1]} {x.day}, {x.year}"


def days(a: str, b: str) -> int:
    return (d(b) - d(a)).days + 1


# ------------------------------------------------------------------ facts: two reads, checked
def load_tsv(p: Path) -> list[dict]:
    with open(p) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def check_reads():
    r1, r2 = load_tsv(READS / "read1_companyconcept.tsv"), load_tsv(READS / "read2_targeted.tsv")
    for r in r1 + r2:
        r["val"] = int(r["val"])
    idx1 = defaultdict(set)
    for r in r1:
        idx1[(r["ticker"], r["concept"], r["start"], r["end"])].add(r["val"])
    checks = {"read1_rows": len(r1), "read2_rows": len(r2), "agree": [], "read_once": [], "disagree": [],
              "duplicate_periods_disagree": [], "quarter_sums": []}
    # 1. read 2 against read 1
    for r in r2:
        k = (r["ticker"], r["concept"], r["start"], r["end"])
        if k not in idx1:
            checks["read_once"].append({**r, "why": r["note"] or "only in read 2"})
        elif idx1[k] == {r["val"]}:
            checks["agree"].append(k)
        else:
            checks["disagree"].append({"key": k, "read1": sorted(idx1[k]), "read2": r["val"]})
    # 2. the same period reported in two filings must carry one value
    for k, vals in idx1.items():
        if len(vals) > 1:
            checks["duplicate_periods_disagree"].append({"key": k, "values": sorted(vals)})
    # 3. Q1 + Q2 + Q3 = nine-month YTD, for each company's fiscal 2026 (FY2026 for MU = Aug 2025 - May 2026)
    q = defaultdict(dict)
    for r in r1:
        if days(r["start"], r["end"]) < 100:
            q[(r["ticker"], r["concept"])][r["start"]] = r
    for (t, c), qs in q.items():
        ytd = [r for r in r1 if r["ticker"] == t and r["concept"] == c and 250 < days(r["start"], r["end"]) < 290]
        for y in ytd:
            parts = sorted((r for r in qs.values() if r["start"] >= y["start"] and r["end"] <= y["end"]), key=lambda r: r["start"])
            if len(parts) != 3 or parts[0]["start"] != y["start"] or parts[-1]["end"] != y["end"]:
                continue
            s = sum(p["val"] for p in parts)
            # filings round each quarter to USD millions (USD 0.1 million for TTWO, USD 1 thousand for CASY)
            checks["quarter_sums"].append({"ticker": t, "concept": c, "ytd_end": y["end"], "ytd": y["val"], "sum_of_quarters": s,
                                           "diff": y["val"] - s, "holds": abs(y["val"] - s) <= 1_000_000})
    checks["summary"] = {
        "read2_agrees_with_read1": f"{len(checks['agree'])}/{len(r2) - len(checks['read_once'])}",
        "read_once": len(checks["read_once"]), "disagreements": len(checks["disagree"]),
        "duplicate_period_conflicts": len(checks["duplicate_periods_disagree"]),
        "quarter_sums_hold": f"{sum(x['holds'] for x in checks['quarter_sums'])}/{len(checks['quarter_sums'])}",
    }
    if checks["disagree"] or checks["duplicate_periods_disagree"] or not all(x["holds"] for x in checks["quarter_sums"]):
        raise SystemExit(f"scope10 facts failed verification: {json.dumps(checks['summary'])}")
    return r1, r2, checks


def build_facts(r1, r2):
    """One record per (ticker, label). Labels: REV/NI x FY (latest 10-K), FYP (prior year, same 10-K), Q (latest 10-Q)."""
    agreed = {(r["ticker"], r["concept"], r["start"], r["end"]) for r in r2 if not r["note"].startswith("read once")}
    rows = {(r["ticker"], r["concept"], r["accn"], r["start"], r["end"]): r for r in r1 + r2}
    facts = {}
    for t, (name, cik, _fye, rc, nc, (acc_k, fy), qs) in COMPANIES.items():
        for lab, concept in (("REV", rc), ("NI", nc)):
            if t == "MSFT":
                continue  # Microsoft facts come from Gold Set v1 (local XBRL + peer_facts_v1)
            cands = [r for (tt, c, a, s, e), r in rows.items() if tt == t and c == concept and a == acc_k and days(s, e) > 300]
            cands.sort(key=lambda r: r["end"], reverse=True)
            for per, r in zip(("FY", "FYP"), cands[:2]):
                facts[(t, lab, per)] = _fact(t, cik, name, concept, r, acc_k, "10-K", agreed)
            acc_q = qs[-1][0]
            qrows = [r for (tt, c, a, s, e), r in rows.items() if tt == t and c == concept and a == acc_q and days(s, e) < 100]
            qrows.sort(key=lambda r: r["end"], reverse=True)
            if qrows:
                facts[(t, lab, "Q")] = _fact(t, cik, name, concept, qrows[0], acc_q, "10-Q", agreed)
    return facts


def _fact(t, cik, name, concept, r, acc, form, agreed):
    k = (t, concept, r["start"], r["end"])
    return {"fact_id": f"{t}|{concept}|{r['start']}|{r['end']}", "ticker": t, "cik": cik, "company": name,
            "concept": f"us-gaap:{concept}", "period_start": r["start"], "period_end": r["end"], "unit": "USD",
            "value": r["val"], "accession": acc, "form": form,
            "source": API.format(cik=cik, concept=concept),
            "verification": "read twice (2026-10-29), reads agree" if k in agreed else "read once (2026-10-29)",
            "key": {"cik": cik, "accession": acc, "concept": f"us-gaap:{concept}", "period_start": r["start"],
                    "period_end": r["end"], "unit": "USD", "ticker": t, "level": "FACT"}}


def msft_facts():
    """Microsoft FY2026 (10-K) from peer_facts_v1 and FY2025 from the 10-K's own comparatives (Week 6 SEC read)."""
    pf = {r["fact_id"]: r for r in map(json.loads, open(DATA / "peer_facts_v1.jsonl"))}
    out = {}
    for lab, fid in (("REV", "MSFT_REV_FY26"), ("NI", "MSFT_NI_FY26")):
        r = pf[fid]
        out[("MSFT", lab, "FY")] = {**r, "key": {"cik": r["cik"], "accession": r["accession"], "concept": r["concept"],
                                                  "period_start": r["period_start"], "period_end": r["period_end"],
                                                  "unit": "USD", "ticker": "MSFT", "level": "FACT"}}
    # FY2025 revenue as reported in the FY2026 10-K (R110 total, read 2026-10-26; equals the FY2025 10-K's R108 total)
    out[("MSFT", "REV", "FYP")] = {"value": 281_724_000_000, "period_start": "2024-07-01", "period_end": "2025-06-30",
                                   "verification": "FY2026 10-K R110 and FY2025 10-K R108 agree (read 2026-10-26)"}
    return out


# ------------------------------------------------------------------ question helpers
def mmx(v: float) -> str:
    """USD -> millions as a person would quote them: whole millions, or one decimal when the filing has one."""
    m = v / 1e6
    return f"{m:,.0f}" if abs(m - round(m)) < 1e-9 else f"{m:,.1f}"


def money(v, extra=(), sf=None):
    disp = mmx(v)
    # significant figures as displayed, trailing zeros ignored (Week 5 rule), capped at 4 so "17,561 million" passes
    sf = sf or min(4, max(3, len(disp.replace(",", "").replace("-", "").replace(".", "").strip("0"))))
    shown = f"USD {disp} million" if v >= 0 else f"a net loss of USD {mmx(-v)} million"
    return {"kind": "money", "value": v, "unit": "USD", "display": shown, "required_points": [mmx(abs(v)), *extra],
            "min_sig_figs": sf, "tolerance": f"{sf} significant figures"}


def pctv(x, nd=2):
    return f"{x * 100:.{nd}f}%"


def ratio(x, extra=()):
    return {"kind": "percent", "value": round(x * 100, 2), "unit": "%", "display": pctv(x), "required_points": [pctv(x), *extra],
            "min_sig_figs": 3, "tolerance": "±0.01 percentage point after rounding to 2 dp"}


def text(points, display=None):
    return {"kind": "text", "value": None, "unit": None, "display": display or "; ".join(points), "required_points": list(points)}


def refusal(reason, points=()):
    return {"kind": "refusal", "value": None, "unit": None, "display": reason,
            "required_points": ["declines or says the corpus does not contain it", *points]}


QUESTIONS: list[dict] = []


def add(qtype, tier, question, *, answer, facts=(), tickers, filters, calc=None, traps=(), answerable=True,
        route="xbrl", use_case=None, notes="", pattern=None):
    facts = [f for f in facts if "key" in f]
    numeric = answer.get("value") is not None
    rec = {
        "qid": f"EV2-{len(QUESTIONS) + 1:03d}", "source": "eval_scope10", "rag_qid": None, "type": qtype, "tier": tier,
        "question": question, "answerable": answerable, "tickers": list(tickers), "corpus": CORPUS, "filters": filters,
        "answer": answer, "gold": None, "facts": [f["key"] for f in facts],
        "fact_values": {f["fact_id"]: f["value"] for f in facts if "fact_id" in f}, "calculation": calc,
        # Text anchors need the filing text as Data chunks it; added once the 21 filings' chunks are shared.
        "rag_evidence": [], "route": route, "traps": list(traps), "use_case": use_case,
        "graph": ({"pattern": pattern or ("single_fact" if len(facts) == 1 else "cross_company"),
                   "n_facts": len(facts),
                   "paths": [[[f["key"]["cik"], "FILED", f["key"]["accession"]],
                              [f["key"]["accession"], "REPORTS", f["fact_id"]]] for f in facts]} if facts else None),
        "status": "auto_verified" if (numeric or answer["kind"] in ("refusal", "false_premise") or qtype == "cross_company")
        and all(f.get("verification", "").startswith("read twice") for f in facts) else "needs_human_review",
        "notes": notes or "Answer computed from SEC XBRL facts read twice; text anchor pending the DB chunks.",
        "scope": "single_company" if len(tickers) == 1 else "comparison",
        "answer_type": ("exact_numeric" if numeric else {"refusal": "refusal", "false_premise": "false_premise"}.get(
            answer["kind"], "exact_categorical")),
        "hops": None, "hops_proposed_by": None,
    }
    if numeric:
        rec["gold"] = {"value": answer["value"], "kind": answer["kind"], "min_sig_figs": answer.get("min_sig_figs", 3),
                       "evidence": [f["key"] for f in facts], "distractors": []}
    QUESTIONS.append(rec)
    return rec


def build_questions(F):
    def name(t):
        return COMPANIES[t][0]

    def poss(t):  # "Casey's" is already possessive
        n = name(t)
        return n if n.endswith("'s") else n + "'s"

    def fy(t):
        return COMPANIES[t][5][1]

    def fy_phrase(t):
        f = F[(t, "REV", "FY")]
        return f"fiscal year {fy(t)} (ended {long_date(f['period_end'])})"

    def kfilt(t):
        return {"ticker": t, "form": "10-K", "fiscal_year": fy(t), "fiscal_period": "FY"}

    def qfilt(t):
        _, y, p = COMPANIES[t][6][-1]
        return {"ticker": t, "form": "10-Q", "fiscal_year": y, "fiscal_period": p}

    singles = [t for t in COMPANIES if t != "MSFT"]
    # 1. single-company lookups: FY revenue, FY net income (10-K); latest-quarter net income and revenue (10-Q)
    for t in singles:
        r, n = F[(t, "REV", "FY")], F[(t, "NI", "FY")]
        add("extraction", "basic", f"What was {poss(t)} total revenue for {fy_phrase(t)}, in USD millions?",
            answer=money(r["value"]), facts=[r], tickers=[t], filters=kfilt(t), use_case="compare_revenue",
            traps=["fiscal_calendar"] if t in ("AAPL", "MU", "MDT", "NTAP") else [])
        ni_word = "net income (loss)" if n["value"] < 0 else "net income"
        notes = ""
        traps = ["sign"] if n["value"] < 0 else []
        if t == "PH":
            traps, notes = ["concept_variant"], ("Parker-Hannifin tags net income as us-gaap:ProfitLoss (includes noncontrolling "
                                                 "interests); the SEC API shows no us-gaap:NetIncomeLoss facts in its 10-Ks or "
                                                 "10-Qs filed since June 2025 (read 10/29).")
        add("extraction", "basic", f"What was {poss(t)} {ni_word} for {fy_phrase(t)}, in USD millions?",
            answer=money(n["value"]), facts=[n], tickers=[t], filters=kfilt(t), traps=traps, notes=notes, use_case="profitability")
        for lab, word in (("NI", "net income (loss)" if F[(t, "NI", "FY")]["value"] < 0 else "net income"), ("REV", "revenue")):
            f = F.get((t, lab, "Q"))
            if not f:
                continue
            _, y, p = COMPANIES[t][6][-1]
            add("extraction", "basic",
                f"What was {poss(t)} {word} for the three months ended {long_date(f['period_end'])} "
                f"(fiscal {y} {p}), in USD millions?",
                answer=money(f["value"]), facts=[f], tickers=[t], filters=qfilt(t),
                traps=["quarter_vs_ytd"] if p != "Q1" else [], use_case="compare_revenue" if lab == "REV" else "profitability")

    # 2. fiscal calendar: the company's own label for the quarter its latest 10-Q covers
    for t in ("NKE", "MDT", "MU"):
        f = F[(t, "NI", "Q")]
        _, y, p = COMPANIES[t][6][-1]
        add("fiscal_calendar", "comparative",
            f"{poss(t)} most recent 10-Q covers the quarter ended {long_date(f['period_end'])}. Which fiscal year and "
            f"quarter is that in {poss(t)} own reporting calendar?",
            answer=text([f"fiscal {y}", p], display=f"Fiscal {y} {p} (fiscal year ends {COMPANIES[t][2]})"),
            facts=[f], tickers=[t], filters={"ticker": t, "form": "10-Q"}, route="metadata", traps=["fiscal_calendar"],
            use_case="scope_guidance")

    # 3. derived single-company
    mu, mup = F[("MU", "REV", "FY")], F[("MU", "REV", "FYP")]
    add("calculation", "comparative",
        f"By what percentage did Micron's revenue grow in fiscal 2025 compared with fiscal 2024? Give two decimals.",
        answer=ratio(mu["value"] / mup["value"] - 1, [mmx(mu["value"]), mmx(mup["value"])]), facts=[mu, mup],
        tickers=["MU"], filters=kfilt("MU"), calc="REV_FY / REV_FYP - 1", traps=["fiscal_calendar"], pattern="multi_fact")
    tt, ttp = F[("TTWO", "NI", "FY")], F[("TTWO", "NI", "FYP")]
    add("calculation", "comparative",
        "By how much did Take-Two's net loss narrow from fiscal 2025 to fiscal 2026, in USD millions?",
        answer=money(tt["value"] - ttp["value"], [mmx(-tt["value"]), mmx(-ttp["value"])]), facts=[tt, ttp],
        tickers=["TTWO"], filters=kfilt("TTWO"), calc="NI_FY - NI_FYP (both negative)", traps=["sign"], pattern="multi_fact")

    # 4. ten-company comparisons on each company's latest 10-K in the corpus (fiscal years end in different months)
    T = list(COMPANIES)
    rev = {t: F[(t, "REV", "FY")] for t in T}
    nin = {t: F[(t, "NI", "FY")] for t in T}
    revp = {t: F[(t, "REV", "FYP")] for t in T}
    all10 = "the ten companies in the corpus (" + ", ".join(name(t) for t in T) + ")"
    cf = {"ticker": T, "form": "10-K"}
    best = max(T, key=lambda t: rev[t]["value"])
    second = sorted(T, key=lambda t: -rev[t]["value"])[1]
    add("cross_company", "comparative",
        f"Among {all10}, which reported the highest revenue for its most recent fiscal year in the corpus, and how much?",
        answer={**money(rev[best]["value"], [name(best)]), "display": f"{name(best)}, USD {mmx(rev[best]['value'])} million "
                f"(fiscal {fy(best)}); next is {name(second)} at USD {mmx(rev[second]['value'])} million"},
        facts=list(rev.values()), tickers=T, filters=cf, calc="argmax(REV_FY)", traps=["fiscal_calendar"],
        use_case="compare_revenue", notes="Fiscal years end in different months; each company's latest 10-K in the corpus.")
    losers = [t for t in T if nin[t]["value"] < 0]
    add("cross_company", "comparative", f"Which of {all10} reported a net loss for its most recent fiscal year in the corpus?",
        answer=text([name(t) for t in losers] + [mmx(-nin[t]["value"]) for t in losers],
                    display="; ".join(f"{name(t)} (net loss USD {mmx(-nin[t]['value'])} million, fiscal {fy(t)})" for t in losers)),
        facts=list(nin.values()), tickers=T, filters=cf, calc="NI_FY < 0", traps=["sign"], use_case="profitability")
    margin = {t: nin[t]["value"] / rev[t]["value"] for t in T}
    order = sorted(T, key=lambda t: -margin[t])
    add("cross_company", "deep",
        f"Rank {all10} by net margin (net income / revenue) for each company's most recent fiscal year in the corpus. "
        "Which is highest, and what is its margin to two decimals?",
        answer={**ratio(margin[order[0]], [name(t) for t in order[:3]]),
                "display": " > ".join(f"{name(t)} {pctv(margin[t])}" for t in order)},
        facts=[x for t in T for x in (nin[t], rev[t])], tickers=T, filters=cf, calc="sort(NI_FY / REV_FY)",
        traps=["fiscal_calendar", "concept_variant", "sign"], use_case="profitability",
        notes="Parker-Hannifin's net income is us-gaap:ProfitLoss (see its single-company question).")
    growth = {t: rev[t]["value"] / revp[t]["value"] - 1 for t in T}
    gorder = sorted(T, key=lambda t: -growth[t])
    g_facts = [x for t in T for x in (rev[t], revp[t]) if "key" in x]
    rec = add("cross_company", "deep",
              f"Which of {all10} had the fastest revenue growth in its most recent fiscal year in the corpus versus the year "
              "before, and what was the growth rate to two decimals?",
              answer={**ratio(growth[gorder[0]], [name(gorder[0])]),
                      "display": " > ".join(f"{name(t)} {pctv(growth[t])}" for t in gorder)},
              facts=g_facts, tickers=T, filters=cf, calc="argmax(REV_FY / REV_FYP - 1)", traps=["fiscal_calendar"],
              use_case="compare_revenue",
              notes="Prior-year revenue read once for Apple (FY2024) and taken from the FY2026 10-K's comparatives for Microsoft.")
    rec["status"] = "needs_human_review"
    april = [t for t in T if "April" in COMPANIES[t][2]]
    add("cross_company", "comparative", f"Which of {all10} have a fiscal year that ends in April?",
        answer=text([name(t) for t in april], display=", ".join(f"{name(t)} ({COMPANIES[t][2]})" for t in april)),
        facts=[rev[t] for t in april], tickers=T, filters=cf, route="metadata", traps=["fiscal_calendar"],
        use_case="scope_guidance")

    # 5. unanswerable inside the corpus, and false premises
    mu_q = F[("MU", "REV", "Q")]
    add("unanswerable", "comparative", "What was Micron's total revenue for its full fiscal year 2026?",
        answer=refusal("The corpus has Micron's FY2025 10-K and its fiscal 2026 10-Qs only; the FY2026 10-K is not in it",
                       ["does not sum the quarters into a full year", "may give nine-month revenue USD 78,959 million, labelled as nine months"]),
        tickers=["MU"], filters={"ticker": "MU", "form": "10-K", "fiscal_year": 2026}, answerable=False, route="refusal",
        traps=["missing_filing", "sum_of_quarters_bait"], use_case="scope_guidance", facts=[mu_q])
    add("unanswerable", "basic", "What was Casey's net income for the quarter ended October 31, 2026?",
        answer=refusal("That quarter's 10-Q is not in the corpus (latest Casey's 10-Q: quarter ended July 31, 2026)"),
        tickers=["CASY"], filters={"ticker": "CASY", "form": "10-Q"}, answerable=False, route="refusal",
        traps=["future_period"], use_case="scope_guidance")
    add("unanswerable", "basic", "What was Parker-Hannifin's revenue for the quarter ended September 30, 2026?",
        answer=refusal("Parker-Hannifin's latest 10-Q in the corpus covers the quarter ended March 31, 2026"),
        tickers=["PH"], filters={"ticker": "PH", "form": "10-Q"}, answerable=False, route="refusal",
        traps=["future_period", "stale_latest_filing"], use_case="scope_guidance")
    add("false_premise", "comparative", "Why was Take-Two profitable in fiscal 2026?",
        answer={"kind": "false_premise", "value": None, "unit": None,
                "display": f"Premise is false: Take-Two reported a net loss of USD {mmx(-tt['value'])} million for fiscal 2026",
                "required_points": ["rejects the premise", "net loss", mmx(-tt["value"])]},
        facts=[tt], tickers=["TTWO"], filters=kfilt("TTWO"), route="refusal", traps=["false_premise", "sign"])
    nk, nkp = F[("NKE", "REV", "FY")], F[("NKE", "REV", "FYP")]
    add("false_premise", "comparative", "Why did Nike's revenue fall in fiscal 2026?",
        answer={"kind": "false_premise", "value": None, "unit": None,
                "display": f"Premise is false: revenue rose slightly, from USD {mmx(nkp['value'])} million to "
                           f"USD {mmx(nk['value'])} million ({pctv(nk['value'] / nkp['value'] - 1)})",
                "required_points": ["rejects the premise", mmx(nk["value"]), mmx(nkp["value"])]},
        facts=[nk, nkp], tickers=["NKE"], filters=kfilt("NKE"), route="refusal", traps=["false_premise"])


# ------------------------------------------------------------------ scope status of Gold Set v1, coverage
def v1_status():
    rows = []
    for q in map(json.loads, open(DATA / "benchmark_v1.jsonl")):
        out = sorted(set(q["tickers"]) & RETIRED_TICKERS)
        rows.append({"qid": q["qid"], "type": q["type"], "tickers": " ".join(q["tickers"]),
                     "status": "retired" if out else "in_scope",
                     "reason": f"uses {', '.join(out)}, not in Data's 10 companies" if out else ""})
    return rows


def coverage(F, status):
    T = list(COMPANIES)
    q_ends = {t: F[(t, "NI", "Q")]["period_end"] if t != "MSFT" else "2026-03-31" for t in T}
    fye_month = {t: MONTHS[d(F[(t, "REV", "FY")]["period_end"]).month - 1] for t in T}
    cal_q = {t: f"{d(e).year}Q{(d(e).month - 1) // 3 + 1}" for t, e in q_ends.items()}
    by_cq = Counter(cal_q.values())
    new = Counter(q["type"] for q in QUESTIONS)
    kept = Counter(r["status"] for r in status)
    return {
        "filings_assumed_in_db": {"10-K": 10, "10-Q": 11, "matches_data_team_counts": True,
                                  "basis": "latest 10-K + latest 10-Q per company filed by 2026-10-13; AAPL x3 and MSFT x2 "
                                           "as listed by GraphRAG. Confirm accessions with Data."},
        "fiscal_year_end_month": fye_month,
        "distinct_fiscal_year_end_months": len(set(fye_month.values())),
        "latest_10q_period_end": q_ends,
        "latest_10q_calendar_quarter": cal_q,
        "companies_sharing_a_calendar_quarter": dict(by_cq),
        "supports": {
            "single_company_lookups": "yes, all 10 (one 10-K and at least one 10-Q each)",
            "cross_company_latest_fiscal_year": "yes, but fiscal years end in "
                                                f"{len(set(fye_month.values()))} different months; questions must name each period",
            "same_calendar_quarter_for_all_10": f"no: the latest 10-Qs fall in {len(by_cq)} calendar quarters",
            "year_over_year": "yes, from each 10-K's prior-year comparatives (2 years); not 3+ year trends",
            "multi_year_trends_and_segment_history": "no until historical filings are loaded",
            "subsidiary_relationship_questions": "yes once Exhibit 21 is cleaned for the 10 10-Ks",
            "amendment_restatement_questions": "no: amendments (10-K/A) are excluded by Data's config",
        },
        "gold_set": {"v1_in_scope": kept["in_scope"], "v1_retired": kept["retired"], "new_eval_scope10": len(QUESTIONS),
                     "total_round1": kept["in_scope"] + len(QUESTIONS), "new_by_type": dict(new)},
    }


def main():
    r1, r2, checks = check_reads()
    F = {**build_facts(r1, r2), **msft_facts()}
    build_questions(F)
    status = v1_status()
    RES.mkdir(exist_ok=True)
    (RES / "scope10_checks.json").write_text(json.dumps(checks, indent=1, default=list))
    facts = [f for f in F.values() if "fact_id" in f]
    (DATA / "scope10_facts.jsonl").write_text("".join(json.dumps(f) + "\n" for f in facts))
    filings = [{"ticker": t, "company": c[0], "cik": c[1], "fiscal_year_end": c[2], "form": "10-K", "accession": c[5][0],
                "fiscal_year": c[5][1]} for t, c in COMPANIES.items()]
    filings += [{"ticker": t, "company": c[0], "cik": c[1], "fiscal_year_end": c[2], "form": "10-Q", "accession": a,
                 "fiscal_year": y, "fiscal_period": p} for t, c in COMPANIES.items() for a, y, p in c[6]]
    (DATA / "scope10_filings.json").write_text(json.dumps(
        {"_doc": "Filings Eval assumes are in Data's DB for the 10 companies (see build_scope10.py docstring). "
                 "Confirm with Data.", "n_10k": sum(f["form"] == "10-K" for f in filings),
         "n_10q": sum(f["form"] == "10-Q" for f in filings), "filings": filings}, indent=1))
    (DATA / "benchmark_scope10_new.jsonl").write_text("".join(json.dumps(q) + "\n" for q in QUESTIONS))
    keep = {r["qid"] for r in status if r["status"] == "in_scope"}
    v1 = [q for q in map(json.loads, open(DATA / "benchmark_v1.jsonl")) if q["qid"] in keep]
    (DATA / "benchmark_scope10.jsonl").write_text("".join(json.dumps(q) + "\n" for q in v1 + QUESTIONS))
    with open(DATA / "benchmark_scope10_status.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "type", "tickers", "status", "reason"])
        w.writeheader()
        w.writerows(status)
    cov = coverage(F, status)
    cov["fact_checks"] = checks["summary"]
    (RES / "scope10_coverage.json").write_text(json.dumps(cov, indent=1))
    print(f"[scope10] facts {len(facts)} | checks {json.dumps(checks['summary'])}")
    print(f"[scope10] gold set: {json.dumps(cov['gold_set'])}")


if __name__ == "__main__":
    main()
