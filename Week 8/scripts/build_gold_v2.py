"""Week 7: Gold Set v2, the ten Data-team companies only, pinned to one database snapshot.

    python scripts/build_gold_v2.py
      -> data/snapshot_w7.json            the filings Data's database held on 2026-11-03 + how each team's list matches it
      -> data/benchmark_v2.jsonl          Gold Set v2 (what round 1 runs)
      -> data/benchmark_v2_questions.md   readable list (every question, expected answer, expected route)
      -> data/benchmark_v2_questions.csv  same, for the sheet
      -> results/gold_v2_summary.json     counts, changes from Week 6, checks

Gold Set v2 = the Week 6 round-1 set (Gold Set v1 questions on the ten companies + EV2 questions, rebuilt by
build_scope10.py with Micron's FY2026 10-K) + the 6 relationship questions drafted with GraphRAG + EV3 questions new this
week (Exhibit 21 relationships across the ten companies, and NetApp's fiscal labels). Gold Set v1 stays frozen.

Every question carries `route_expected`, the tool a well-routed agent should use first:
  sql    Data's finance views (XBRL facts, filing metadata): exact numbers, calculations, fiscal labels
  text   RAG's text search: definitions, narrative, "not disclosed" checks
  graph  GraphRAG: relationships (subsidiaries, ownership, segment membership, events)
  multi  needs two of the above (the answer combines figures with a filing passage)
  none   the scope gate should answer without any tool (company or period outside the snapshot)
This follows the 10/29 mentor guidance (route numeric parts to the SQL tool, multi-part questions to several tools) and
RAG's proposal that numeric questions go to Data's finance views first.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES, READS = ROOT / "data", ROOT / "results", ROOT / "data" / "sec_reads"
TEN = {"AAPL", "CASY", "MCK", "MDT", "MSFT", "MU", "NKE", "NTAP", "PH", "TTWO"}
SNAPSHOT = "data_db_2026-11-03"

# ---------------------------------------------------------------- the snapshot
# Data's database on 2026-11-03 (GraphRAG extraction_pipeline/config/filings.yaml @ 97eeba5, which lists every 10-K and
# 10-Q of the ten companies loaded with validation_status=passed, and names the one review_required filing).
DB_FILINGS = [
    ("AAPL", "10-K", "2025-09-27", "0000320193-25-000079"), ("AAPL", "10-Q", "2026-03-28", "0000320193-26-000013"),
    ("AAPL", "10-Q", "2026-06-27", "0000320193-26-000020"), ("CASY", "10-K", "2026-04-30", "0000726958-26-000046"),
    ("CASY", "10-Q", "2026-07-31", "0000726958-26-000085"), ("MCK", "10-K", "2026-03-31", "0000927653-26-000069"),
    ("MCK", "10-Q", "2026-06-30", "0000927653-26-000234"), ("MDT", "10-K", "2026-04-24", "0001628280-26-044354"),
    ("MDT", "10-Q", "2026-07-31", "0001628280-26-060473"), ("MSFT", "10-Q", "2026-03-31", "0001193125-26-191507"),
    ("MSFT", "10-K", "2026-06-30", "0001193125-26-323660"), ("MU", "10-Q", "2026-05-28", "0000723125-26-000015"),
    ("MU", "10-K", "2026-09-03", "0000723125-26-000023"), ("NKE", "10-K", "2026-05-31", "0000320187-26-000088"),
    ("NKE", "10-Q", "2026-08-31", "0000320187-26-000193"), ("NTAP", "10-K", "2026-04-24", "0001193125-26-259683"),
    ("NTAP", "10-Q", "2026-07-31", "0001193125-26-380207"), ("PH", "10-Q", "2026-03-31", "0000076334-26-000073"),
    ("PH", "10-K", "2026-06-30", "0000076334-26-000105"), ("TTWO", "10-K", "2026-03-31", "0001628280-26-037434"),
    ("TTWO", "10-Q", "2026-06-30", "0001628280-26-054870"),
]
REVIEW_REQUIRED = {"0001193125-26-380207"}
# RAG's v2 index (Slack 10/28, MANIFEST rag_index_v2_C1_20261028): 9 filings for AAPL, AMZN, META, MSFT, NVDA.
RAG_V2_TICKERS = {"AAPL", "AMZN", "META", "MSFT", "NVDA"}


def snapshot(data_inventory_csv: Path | None) -> dict:
    ev6 = json.load(open(DATA / "scope10_filings_w6.json"))["filings"] if (DATA / "scope10_filings_w6.json").exists() else []
    db = {a for *_, a in DB_FILINGS}
    inv = {}
    if data_inventory_csv and data_inventory_csv.exists():
        inv = {r["accession_number"]: r for r in csv.DictReader(open(data_inventory_csv))}
    eval_w6 = {f["accession"] for f in ev6}
    newer = sorted((r["ticker"], r["form"], r["dei_period_end"], a) for a, r in inv.items()
                   if a not in db and r["dei_period_end"] > max(e for t, f, e, x in DB_FILINGS if t == r["ticker"] and f == r["form"]))
    # fiscal-year labels in filing metadata that disagree with the company's own naming (fiscal year = year it ends)
    return {
        "_doc": "One frozen snapshot for RAG, GraphRAG, Agents and Eval (RAG asked Data the same on 10/28). Questions name "
                "periods explicitly; 'latest' means latest in this snapshot.",
        "snapshot_id": SNAPSHOT, "source": "GraphRAG extraction_pipeline/config/filings.yaml @ 97eeba5 (Data database, 2026-11-03)",
        "filings": [{"ticker": t, "form": f, "period_end": e, "accession": a,
                     "db_status": "review_required" if a in REVIEW_REQUIRED else "passed"} for t, f, e, a in DB_FILINGS],
        "counts": {"10-K": sum(f == "10-K" for _, f, _, _ in DB_FILINGS), "10-Q": sum(f == "10-Q" for _, f, _, _ in DB_FILINGS)},
        "match": {
            "eval_week6_list": {"same": len(eval_w6 & db), "of": len(db),
                                "differs": sorted(eval_w6 - db) + sorted(db - eval_w6) if eval_w6 else "n/a",
                                "note": "Week 6 assumed Micron's FY2025 10-K (0000723125-25-000028); the DB holds FY2026 "
                                        "(0000723125-26-000023, filed 2026-10-09). Week 7 uses the DB's."},
            "data_inventory_2021_2026": {"filings": len(inv), "contains_all_snapshot_filings": db <= set(inv) if inv else None,
                                         "newer_than_snapshot": [list(x) for x in newer],
                                         "source": "data_engineering_kpmg docs/validation/fact-coverage-2021-2026.csv @ f8d18e2"},
            "graphrag_filings": {"same": 20, "of": 21, "note": "GraphRAG extracts the 20 passed filings; NetApp's 10-Q is excluded "
                                                               "as review_required"},
            "rag_v2_index": {"tickers": sorted(RAG_V2_TICKERS), "covers_of_ten": sorted(RAG_V2_TICKERS & TEN),
                             "note": "RAG's v2 index covers 2 of the ten companies; the other 8 need indexing for round 1"},
        },
    }


# ---------------------------------------------------------------- routes
def route_for(q: dict) -> str:
    qid, t, r = q["qid"], q["type"], q.get("route")
    if qid.startswith("EV1R-"):
        return {"EV1R-003": "multi", "EV1R-005": "text"}.get(qid, "graph")
    if t in ("unanswerable",):
        traps = set(q.get("traps", []))
        if traps & {"not_disclosed"}:
            return "text"
        return "none"
    if t == "false_premise":
        return "text" if qid == "EV1-070" else ("graph" if "fabricated_edge" in q.get("traps", []) else "sql")
    if r in ("xbrl", "metadata"):
        return "sql"
    if r == "text":
        return "text"
    return "sql" if q.get("answer_type") == "exact_numeric" else "text"


# ---------------------------------------------------------------- EV3: new this week
def ev3_questions() -> list[dict]:
    ex = json.load(open(READS / "exhibit21_2026-11-05.json"))
    L = ex["lists"]

    def subs(t):
        return L[t]["subsidiaries"]

    def nonus(t):
        return {j for _, j in subs(t) if "U.S." not in j and j not in US_STATES}

    a_mu = sorted(nonus("AAPL") & nonus("MU"))
    assert a_mu == ["China", "India", "Japan", "Singapore"], a_mu
    ins = {t: [(n, j) for n, j in subs(t) if "Insurance" in n] for t in ("AAPL", "CASY", "MU")}
    assert all(len(v) == 1 for v in ins.values()), ins
    casy = Counter(j for _, j in subs("CASY"))
    assert casy.most_common(1)[0] == ("Iowa", 6)
    assert L["MU"]["total"] == len(subs("MU")) == 21 and sum(j in US_STATES for _, j in subs("MU")) == 6
    isr = ex["lookups"]["NTAP"]["israel"]
    assert len(isr) == 5

    def ev(t, contains):
        acc = (L.get(t) or ex["lookups"].get(t))["accession"]
        return [{"region": "exhibit_21", "ticker": t, "form": "10-K", "accession": acc, "contains": contains}]

    def item(n, qtype, tier, tickers, question, answer, evidence, traps, path, notes, answerable=True, route="graph",
             answer_type="exact_categorical"):
        return {"qid": f"EV3-{n:03d}", "source": "eval_w7", "rag_qid": None, "type": qtype, "tier": tier, "question": question,
                "answerable": answerable, "tickers": tickers, "corpus": SNAPSHOT,
                "filters": {"ticker": tickers if len(tickers) > 1 else tickers[0], "form": "10-K"},
                "answer": answer, "gold": None, "facts": [], "fact_values": {}, "calculation": None, "rag_evidence": evidence,
                "route": "text", "traps": traps, "use_case": "relationship", "graph": {"pattern": "relationship", "path": path},
                "status": "verified_twice", "notes": notes, "scope": "comparison" if len(tickers) > 1 else "single_company",
                "answer_type": answer_type, "hops": None, "hops_proposed_by": None, "route_expected": route}

    def text(points, display):
        return {"kind": "text", "value": None, "unit": None, "display": display, "required_points": points}

    src = "Exhibit 21 read twice on 2026-11-05 (data/sec_reads/exhibit21_2026-11-05.json)."
    out = [
        item(1, "relationship", "comparative", ["MU"],
             "In the Exhibit 21 of its fiscal 2026 annual report, how many subsidiaries does Micron list, and how many of them "
             "are organized outside the United States?",
             text(["21", "15 outside the United States", "6 in U.S. states"],
                  "21 subsidiaries: 15 outside the U.S. (UK, Japan x3, Malaysia, Taiwan x3, Singapore x2, Cayman Islands, "
                  "India x2, China, Netherlands) and 6 in U.S. states (Delaware x4, Idaho, Hawaii)"),
             ev("MU", ["Micron Europe Limited", "S-Squared Insurance Company, Inc."]), ["aggregate_a_list", "exhibit_not_body"],
             "Company -FILED-> 10-K -HAS_EXHIBIT-> Exhibit 21 -LISTS-> Subsidiary (x21) -INCORPORATED_IN-> Jurisdiction",
             src + " Exhibit 21 omits subsidiaries that are not significant in aggregate."),
        item(2, "relationship", "deep", ["AAPL", "MU"],
             "Which countries outside the United States appear in both Apple's and Micron's Exhibit 21 subsidiary lists "
             "(Apple fiscal 2025, Micron fiscal 2026)?",
             text(a_mu, "China, India, Japan and Singapore (Hong Kong is Apple only; Taiwan, Malaysia, the UK, the Netherlands "
                        "and the Cayman Islands are Micron only)"),
             ev("AAPL", ["Apple Services Pte. Ltd."]) + ev("MU", ["Micron Semiconductor Asia Pte. Ltd."]),
             ["cross_company_join", "hong_kong_vs_china"],
             "AAPL -LISTS-> Subsidiary -IN-> Jurisdiction <-IN- Subsidiary <-LISTS- MU (join on jurisdiction)",
             src + " GraphRAG M02 shape on the ten-company corpus."),
        item(3, "relationship", "deep", ["AAPL", "CASY", "MU"],
             "Apple, Casey's and Micron each list an insurance company among their subsidiaries. Name each one and where it is "
             "organized.",
             text([n for t in ins for n, _ in ins[t]] + [j.replace(", U.S.", "") for t in ins for _, j in ins[t]],
                  "; ".join(f"{NAMES[t]}: {n} ({j.replace(', U.S.', '')})" for t in ins for n, j in ins[t])),
             ev("AAPL", ["Apple Insurance Company, Inc."]) + ev("CASY", ["CARES Captive Insurance Company"]) +
             ev("MU", ["S-Squared Insurance Company, Inc."]), ["cross_company_join"],
             "Company -LISTS-> Subsidiary (type: captive insurer) -INCORPORATED_IN-> State, for three companies", src),
        item(4, "relationship", "comparative", ["CASY"],
             "In which state are most of the subsidiaries in Casey's Exhibit 21 organized, and how many of the listed "
             "subsidiaries is that?",
             text(["Iowa", "6 of 9"], "Iowa: 6 of the 9 listed subsidiaries (Texas 2, Delaware 1)"),
             ev("CASY", ["Casey's Marketing Company", "Heartland Property Company, LLC"]), ["aggregate_a_list"],
             "CASY -LISTS-> Subsidiary (x9) -ORGANIZED_IN-> State; group and count", src),
        item(5, "relationship", "comparative", ["NTAP"],
             "Which NetApp subsidiaries organized in Israel are listed in its fiscal 2026 Exhibit 21?",
             text(isr, ", ".join(isr) + " (5)"),
             ev("NTAP", ["NetApp Israel R&D Ltd.", "Plexistor Ltd."]), ["filter_a_long_list"],
             "NTAP -LISTS-> Subsidiary -ORGANIZED_IN-> Israel", src + " Targeted lookup in a 76+ row list."),
        item(6, "fabricated_relationship", "comparative", ["MU", "AAPL"],
             "Is Braeburn Capital, Inc. a subsidiary of Micron?",
             {"kind": "refusal", "value": None, "unit": None,
              "display": "No: Braeburn Capital, Inc. (Nevada) is listed in Apple's Exhibit 21, not Micron's",
              "required_points": ["not a Micron subsidiary", "Apple"]},
             ev("AAPL", ["Braeburn Capital, Inc."]), ["fabricated_edge", "entity_in_corpus_wrong_parent"],
             "MU -/LISTS/-> Braeburn Capital; actual: AAPL -LISTS-> Braeburn Capital",
             src + " Pass = does not attach the subsidiary to Micron.", answerable=False, answer_type="refusal"),
        item(7, "fabricated_relationship", "comparative", ["NTAP", "MU"],
             "Which Micron business owns Spotinst Ltd.?",
             {"kind": "false_premise", "value": None, "unit": None,
              "display": "Premise is false: Spotinst Ltd. (Israel) is a NetApp subsidiary, not a Micron business",
              "required_points": ["rejects the premise", "NetApp"]},
             ev("NTAP", ["Spotinst Ltd."]), ["fabricated_edge", "false_premise"],
             "MU -/OWNS/-> Spotinst; actual: NTAP -LISTS-> Spotinst Ltd.", src, answer_type="false_premise"),
        item(8, "fiscal_calendar", "comparative", ["NTAP"],
             "NetApp's 10-Q for the quarter ended July 31, 2026: which fiscal year and quarter does NetApp itself say it covers, "
             "and does the filing's cover-page metadata agree?",
             text(["fiscal 2027", "first quarter", "metadata says fiscal year 2026"],
                  "First quarter of fiscal 2027 (the filing's own text). The cover-page XBRL tags DocumentFiscalYearFocus = 2026, "
                  "so a fiscal_year filter built from metadata misses it."),
             [{"region": "note_1", "ticker": "NTAP", "form": "10-Q", "accession": "0001193125-26-380207",
               "contains": ["Fiscal 2027, ending on April 30, 2027"]}],
             ["fiscal_calendar", "metadata_mislabel"], "NTAP -FILED-> 10-Q (period 2026-07-31) -FISCAL_PERIOD-> FY2027 Q1",
             "Filing text and R1 cover page read 2026-11-05 (data/sec_reads/filing_statements_2026-11-05.json). Same mislabel "
             "on NetApp's Q1 and Q2 FY2026 10-Qs in Data's 233-filing inventory. Filing is review_required in the DB.",
             route="sql"),
        item(9, "fiscal_calendar", "comparative", ["NTAP"],
             "How many weeks are in NetApp's first quarter of fiscal 2027, and why does that matter when comparing it with the "
             "first quarter of fiscal 2026?",
             text(["14 weeks", "53-week year", "13 weeks"],
                  "14 weeks: fiscal 2027 is a 53-week year with the extra week in Q1, while fiscal 2026 had 13 weeks in each "
                  "quarter, so a year-over-year comparison includes one extra week."),
             [{"region": "note_1", "ticker": "NTAP", "form": "10-Q", "accession": "0001193125-26-380207",
               "contains": ["14 weeks included in its first quarter"]}],
             ["53_week_year"], "NTAP -FILED-> 10-Q -STATES-> fiscal calendar note",
             "Quoted from Note 1 of the 10-Q (read 2026-11-05).", route="text", answer_type="narrative"),
    ]
    return out


US_STATES = {"Delaware", "Idaho", "Hawaii", "Iowa", "Texas", "Arizona", "Nevada", "California",
             "Arizona, U.S.", "Delaware, U.S.", "Nevada, U.S."}
NAMES = {"AAPL": "Apple", "CASY": "Casey's", "MU": "Micron"}


def write_hops(gold: list[dict]) -> None:
    """hops sheet for GraphRAG: every Gold Set v1 and v2 question; values already filled in are kept."""
    path = DATA / "hops_v1.csv"
    old = {r["qid"]: r for r in csv.DictReader(open(path))} if path.exists() else {}
    v1 = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
    seen, rows = set(), []
    for q in v1 + gold:
        if q["qid"] in seen:
            continue
        seen.add(q["qid"])
        o = old.get(q["qid"], {})
        rows.append([q["qid"], q["type"], q["tier"], q["question"], o.get("hops", ""), o.get("proposed_by", ""),
                     o.get("reviewed_by", ""), o.get("note", "")])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "type", "tier", "question", "hops", "proposed_by", "reviewed_by", "note"])
        w.writerows(rows)


def main():
    import sys
    inv = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "upstream" / "data_engineering_kpmg" / "docs" / "validation" / "fact-coverage-2021-2026.csv"
    snap = snapshot(inv)
    (DATA / "snapshot_w7.json").write_text(json.dumps(snap, indent=1))
    base = [json.loads(l) for l in open(DATA / "benchmark_scope10.jsonl")]
    rel = [json.loads(l) for l in open(DATA / "benchmark_v1_relationship_draft.jsonl")]
    new = ev3_questions()
    db_acc = {f["accession"]: f for f in snap["filings"]}
    gold = []
    for q in base + rel:
        q = dict(q)
        q["route_expected"] = route_for(q)
        gold.append(q)
    gold += new
    # ten companies only: every answerable question uses only the ten; out-of-scope companies appear only in refusals
    outside = [q["qid"] for q in gold if q["answerable"] and set(q["tickers"]) - TEN]
    assert not outside, outside
    # snapshot status per question: are the filings its evidence names in the DB snapshot?
    for q in gold:
        accs = {e.get("accession") for e in q.get("rag_evidence", []) if e.get("accession")}
        accs |= {k.get("accession") for k in q.get("facts", []) if k.get("accession")}
        if not q["answerable"] and q["route_expected"] == "none":
            q["snapshot_status"] = "out_of_snapshot_by_design"
        elif accs and accs <= set(db_acc):
            q["snapshot_status"] = "review_required" if accs & REVIEW_REQUIRED else "in_snapshot"
        elif accs:
            q["snapshot_status"] = "evidence_outside_snapshot"
            q["snapshot_missing"] = sorted(accs - set(db_acc))
        else:
            q["snapshot_status"] = "no_filing_evidence"
    (DATA / "benchmark_v2.jsonl").write_text("".join(json.dumps(q) + "\n" for q in gold))
    write_hops(gold)
    sha = hashlib.sha256((DATA / "benchmark_v2.jsonl").read_bytes()).hexdigest()[:16]
    with open(DATA / "benchmark_v2_questions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "tickers", "type", "tier", "route_expected", "question", "expected_answer", "status", "snapshot_status"])
        for q in gold:
            w.writerow([q["qid"], " ".join(q["tickers"]), q["type"], q["tier"], q["route_expected"], q["question"],
                        q["answer"]["display"], q["status"], q["snapshot_status"]])
    md = ["# Gold Set v2: ten companies, Data database snapshot of 2026-11-03", "",
          f"{len(gold)} questions. Generated by `scripts/build_gold_v2.py`; do not edit by hand. File hash `{sha}`.", "",
          "| qid | Company | Type | Route | Question | Expected answer |", "|---|---|---|---|---|---|"]
    for q in gold:
        a = q["answer"]["display"].replace("|", "/")
        md.append(f"| {q['qid']} | {' '.join(q['tickers'])} | {q['type']} | {q['route_expected']} | "
                  f"{q['question'].replace('|', '/')} | {a[:200] + ('...' if len(a) > 200 else '')} |")
    (DATA / "benchmark_v2_questions.md").write_text("\n".join(md) + "\n")
    by_t = Counter(t for q in gold for t in q["tickers"] if q["answerable"])
    summary = {
        "gold_set_v2": {"questions": len(gold), "sha256_16": sha, "answerable": sum(q["answerable"] for q in gold),
                        "by_source": dict(Counter(q["source"] for q in gold)), "by_type": dict(Counter(q["type"] for q in gold)),
                        "by_route_expected": dict(Counter(q["route_expected"] for q in gold)),
                        "by_snapshot_status": dict(Counter(q["snapshot_status"] for q in gold)),
                        "answerable_questions_per_company": dict(sorted(by_t.items())),
                        "companies_outside_ten_in_answerable_questions": 0},
        "changes_from_week6": [
            "Micron's 10-K is now FY2026 (in Data's DB): EV2-017/018/038 recomputed, comparisons EV2-040..043 recomputed",
            "EV2-045 was a refusal ('FY2026 10-K not in corpus'); it is now a derived Q4 FY2026 revenue question",
            "EV2-050 added: Micron Q1 FY2027 is outside the snapshot (refusal)",
            "McKesson and Medtronic net income questions name 'excluding noncontrolling interests'; statement totals added as distractors",
            "Comparison questions name the snapshot instead of 'the corpus'",
            "EV3-001..009 added: Exhibit 21 relationships across the ten companies (incl. 2 invented-relationship checks) and "
            "NetApp's fiscal labels",
            "route_expected on every question",
        ],
    }
    RES.mkdir(exist_ok=True)
    (RES / "gold_v2_summary.json").write_text(json.dumps({**summary, "snapshot_match": snap["match"]}, indent=1))
    print(json.dumps(summary["gold_set_v2"], indent=1))
    print(json.dumps(snap["match"], indent=1))


if __name__ == "__main__":
    main()
