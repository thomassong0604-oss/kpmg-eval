"""Week 6: draft relationship tranche for Gold Set v1, built with GraphRAG (eval-ask.md, 10/22; agreed 10/26).

    python scripts/build_relationship_draft.py
      -> data/benchmark_v1_relationship_draft.jsonl   (same item format as benchmark_v1.jsonl)
      -> data/hops_v1.csv                             (hops sidecar for all v1 + draft questions, for GraphRAG to fill)

Division of work agreed with GraphRAG: they propose the shape, graph path and filing; Eval writes the wording and the
gold evidence and validates it against the filing; Business/UI checks each is a question an analyst would ask.
Gold Set v1 itself is not modified (its hash stays the frozen one). These items are run only with
`run_harness.py --with-relationship-draft` until the team signs them off.

Stage 1 (now): questions answerable from filings already in, or about to be in, the Microsoft corpus.
  M01 -> EV1R-001   M04 -> EV1R-002   M09 -> EV1R-003   M14 family -> EV1R-004, EV1R-005   M17 -> EV1R-006
Not yet written:
  M06 (new Item 1A risk factors, FY25 vs FY26): Eval could not read both Item 1A sections in full yet, so the
      set difference is not verified. Next.
  M02, M12, M13, M18, M19 and M14 with an Apple subsidiary: stage 2, after Data confirms the corpus (merge decision).

Verification:
  * 10-Q items: every `contains` anchor and literal answer point is checked here against RAG's chunks of the Q3 FY26 10-Q
    (data/rag_chunks_msft_10q.jsonl), so the build fails if the filing text does not support the gold.
  * 10-K items: values were read from SEC EDGAR on 2026-10-26 (URLs in SEC_READS) and are asserted for internal
    consistency below (segment sums, year-over-year arithmetic). They stay `needs_human_review` until a second reader
    confirms them, and their anchors are checked once the 10-K is in the shared corpus.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MSFT = {"ticker": "MSFT", "cik": "0000789019"}
ACC_10Q = "0001193125-26-191507"   # Q3 FY2026 10-Q (in the shared index)
ACC_10K26 = "0001193125-26-323660"  # FY2026 10-K (in filing_pool_v1; not yet in the shared index)
ACC_10K25 = "0000950170-25-100235"  # FY2025 10-K (GraphRAG pilot corpus; needs the corpus merge)
BASE = "https://www.sec.gov/Archives/edgar/data/789019"

# Values Eval read from SEC EDGAR, 2026-10-26. USD millions.
SEC_READS = {
    "ex21_fy26": {"url": f"{BASE}/000119312526323660/msft-ex21.htm", "subsidiaries": [
        ("Microsoft Ireland Research Unlimited Company", "Ireland"),
        ("Microsoft Global Finance Unlimited Company", "Ireland"),
        ("Microsoft Ireland Operations Limited", "Ireland"),
        ("Microsoft Online, Inc.", "United States"),
        ("LinkedIn Corporation", "United States"),
        ("LinkedIn Ireland Unlimited Company", "Ireland"),
        ("Activision Blizzard, Inc.", "United States"),
        ("Activision Publishing, Inc.", "United States"),
    ]},
    # FY2025 Exhibit 21 lists the same eight names and jurisdictions.
    "ex21_fy25": {"url": f"{BASE}/000095017025100235/msft-ex21.htm", "same_as": "ex21_fy26"},
    "segments_fy26_10k": {"url": f"{BASE}/000119312526323660/R107.htm", "revenue": {
        "Productivity and Business Processes": {2026: 139_996, 2025: 120_810, 2024: 106_820},
        "Intelligent Cloud": {2026: 137_791, 2025: 106_265, 2024: 87_464},
        "More Personal Computing": {2026: 54_052, 2025: 54_649, 2024: 50_838},
    }, "total": {2026: 331_839, 2025: 281_724, 2024: 245_122}},
    "segments_fy25_10k": {"url": f"{BASE}/000095017025100235/R105.htm", "revenue": {
        "Productivity and Business Processes": {2025: 120_810, 2024: 106_820, 2023: 94_151},
        "Intelligent Cloud": {2025: 106_265, 2024: 87_464, 2023: 72_944},
        "More Personal Computing": {2025: 54_649, 2024: 50_838, 2023: 44_820},
    }, "total": {2025: 281_724, 2024: 245_122, 2023: 211_915}},
    "products_fy25_10k": {"url": f"{BASE}/000095017025100235/R108.htm", "Gaming": {2025: 23_455, 2024: 21_503, 2023: 15_466}},
    "products_fy26_10k": {"url": f"{BASE}/000119312526323660/R110.htm", "XBOX": {2026: 21_790, 2025: 23_455, 2024: 21_503}},
    "business_combinations_fy25": {"url": f"{BASE}/000095017025100235/R17.htm", "purchase_price": 75_408},
    "item1_fy26": {"url": f"{BASE}/000119312526323660/msft-20260630.htm",
                   "quotes": ["XBOX (formerly Gaming)", "Search advertising (formerly Search and news advertising)"]},
    "item1_fy25": {"url": f"{BASE}/000095017025100235/msft-20250630.htm",
                   "quotes": ["Gaming, including Xbox hardware and Xbox content and services"]},
}


def _consistency_checks():
    s26, s25 = SEC_READS["segments_fy26_10k"], SEC_READS["segments_fy25_10k"]
    for s in (s26, s25):  # segments sum to total in every year
        for y, tot in s["total"].items():
            assert sum(v[y] for v in s["revenue"].values()) == tot, (s["url"], y)
    for seg in s26["revenue"]:  # FY2025 and FY2024 figures are unchanged between the two 10-Ks -> no recast
        for y in (2025, 2024):
            assert s26["revenue"][seg][y] == s25["revenue"][seg][y], (seg, y)
    assert set(s26["revenue"]) == set(s25["revenue"])  # same three segments
    g25, x26 = SEC_READS["products_fy25_10k"]["Gaming"], SEC_READS["products_fy26_10k"]["XBOX"]
    assert g25[2025] == x26[2025] and g25[2024] == x26[2024]  # XBOX is the renamed Gaming line, same figures
    assert sum(j != "United States" for _, j in SEC_READS["ex21_fy26"]["subsidiaries"]) == 4


def _item(qid, gp, qtype, tier, question, answer, answer_type, corpus, evidence, traps, graph, status, notes,
          answerable=True, route="text", use_case="relationship"):
    return {
        "qid": qid, "source": "eval_v1_relationship", "graphrag_shape": gp, "rag_qid": None, "type": qtype, "tier": tier,
        "question": question, "answerable": answerable, "tickers": ["MSFT"], "corpus": corpus,
        "filters": {"ticker": "MSFT"}, "answer": answer, "gold": None, "facts": [], "fact_values": {}, "calculation": None,
        "rag_evidence": evidence, "route": route, "traps": traps, "use_case": use_case, "graph": graph,
        "status": status, "notes": notes, "scope": "mvp_single_company", "answer_type": answer_type,
        "hops": None, "hops_proposed_by": None,  # GraphRAG proposes, Eval reviews (agreed 10/26)
    }


def build() -> list[dict]:
    _consistency_checks()
    subs = SEC_READS["ex21_fy26"]["subsidiaries"]
    g25 = SEC_READS["products_fy25_10k"]["Gaming"]
    d_gaming = g25[2025] - g25[2024]
    pct_gaming = 100 * d_gaming / g25[2024]
    assert d_gaming == 1_952 and round(pct_gaming) == 9

    items = [
        _item("EV1R-001", "M01", "relationship", "comparative",
              "In its fiscal year 2026 annual report, which subsidiaries does Microsoft list in Exhibit 21, "
              "and how many of them are incorporated outside the United States?",
              {"kind": "text", "value": None, "unit": None,
               "display": "Eight subsidiaries; four are incorporated outside the US, all in Ireland: "
                          + "; ".join(f"{n} ({j})" for n, j in subs) + ".",
               "required_points": [n for n, _ in subs] + ["four outside the United States", "Ireland"]},
              "exact_categorical", "msft_10k_fy26",
              [{"region": "exhibit_21", **{"ticker": "MSFT", "form": "10-K"}, "accession": ACC_10K26,
                "contains": ["Microsoft Ireland Research Unlimited Company", "Activision Publishing, Inc."]}],
              ["exhibit_not_body", "aggregate_a_list"],
              {"pattern": "list_aggregate", "path": "Company -FILED-> Filing -HAS_EXHIBIT-> Exhibit 21 -LISTS-> Subsidiary (x8)"},
              "needs_human_review",
              f"Read from {SEC_READS['ex21_fy26']['url']} on 2026-10-26. Exhibit 21 omits subsidiaries that are not "
              "significant in aggregate; an answer may say so but must not add names. FY2025 Exhibit 21 is identical."),
        _item("EV1R-002", "M04", "relationship", "deep",
              "Did Microsoft change its reportable segments between fiscal year 2025 and fiscal year 2026, "
              "and did it rename any of its revenue categories?",
              {"kind": "text", "value": None, "unit": None,
               "display": "No segment change: Productivity and Business Processes, Intelligent Cloud and More Personal "
                          "Computing in both years, and fiscal 2025 segment revenue is not recast (e.g. Productivity and "
                          "Business Processes USD 120,810 million in both 10-Ks). Two revenue categories were renamed: "
                          "Gaming became XBOX, and Search and news advertising became Search advertising.",
               "required_points": ["no change to the reportable segments", "Productivity and Business Processes",
                                   "Intelligent Cloud", "More Personal Computing", "Gaming renamed XBOX",
                                   "Search and news advertising renamed Search advertising"]},
              "narrative", "msft_10k_fy26",
              [{"region": "item1_segment_description", "ticker": "MSFT", "form": "10-K", "accession": ACC_10K26,
                "contains": ["XBOX (formerly Gaming)"]},
               {"region": "segment_note", "ticker": "MSFT", "form": "10-K", "accession": ACC_10K26,
                "contains": ["More Personal Computing", "54,649"]}],
              ["rename_is_not_realignment", "compare_two_filings"],
              {"pattern": "cross_period", "path": "Filing FY25 -REPORTS-> Segment x3 ; Filing FY26 -REPORTS-> Segment x3 ; "
                                                  "ProductLine -RENAMED_FROM-> ProductLine"},
              "needs_human_review",
              f"Segments and figures from {SEC_READS['segments_fy26_10k']['url']} and {SEC_READS['segments_fy25_10k']['url']}; "
              f"renames quoted from Item 1 of the FY2026 10-K. Answerable from the FY2026 10-K alone (it carries FY2025 "
              "comparatives); stronger with the FY2025 10-K in the corpus."),
        _item("EV1R-003", "M09", "event", "deep",
              "How did Microsoft's net gains or losses from its investments in OpenAI change between the nine months "
              "ended March 31, 2025 and the nine months ended March 31, 2026, and what event drove the change?",
              {"kind": "text", "value": None, "unit": None,
               "display": "Other income (expense), net included USD 5.9 billion of net gains from OpenAI investments in "
                          "the nine months ended March 31, 2026, against USD 2.7 billion of net losses a year earlier. "
                          "The gains primarily relate to the dilution gain from the OpenAI Recapitalization. Net of tax, "
                          "that raised net income by USD 4,483 million versus a USD 2,045 million reduction a year earlier.",
               "required_points": ["$5.9 billion of net gains", "$2.7 billion of net losses", "dilution gain",
                                   "OpenAI Recapitalization", "4,483", "2,045"]},
              "narrative", "msft_10q_q3fy26",
              [{"region": "other_income_note", "ticker": "MSFT", "form": "10-Q", "accession": ACC_10Q,
                "contains": ["primarily relate to the dilution gain from the OpenAI Recapitalization"]},
               {"region": "non_gaap_reconciliation", "ticker": "MSFT", "form": "10-Q", "accession": ACC_10Q,
                "contains": ["Net (gains) losses from investments in OpenAI", "(4,483)"]}],
              ["quarter_vs_ytd", "gain_vs_loss_sign"],
              {"pattern": "event_effect", "path": "Event (OpenAI Recapitalization) -AFFECTS-> Investment (OpenAI, equity method) "
                                                  "-REPORTED_IN-> Other income (expense), net -FLOWS_TO-> Net income"},
              "auto_verified", "All anchors and figures checked against RAG's chunks of the Q3 FY2026 10-Q by this script."),
        _item("EV1R-004", "M14", "fabricated_relationship", "comparative",
              "Is LinkedIn Ireland Unlimited Company a subsidiary of Activision Blizzard, Inc.?",
              {"kind": "refusal", "value": None, "unit": None,
               "display": "The filing does not show that. Exhibit 21 lists both as subsidiaries of Microsoft and states "
                          "no ownership between them.",
               "required_points": ["does not say Activision Blizzard owns LinkedIn Ireland",
                                   "both listed as Microsoft subsidiaries in Exhibit 21"]},
              "refusal", "msft_10k_fy26",
              [{"region": "exhibit_21", "ticker": "MSFT", "form": "10-K", "accession": ACC_10K26,
                "contains": ["LinkedIn Ireland Unlimited Company", "Activision Blizzard, Inc."]}],
              ["fabricated_edge", "both_names_in_corpus"],
              {"pattern": "absent_edge", "path": "Subsidiary (Activision Blizzard) -/OWNS/-> Subsidiary (LinkedIn Ireland): no such edge"},
              "needs_human_review",
              "Both names are in the same exhibit, so retrieval surfaces them together; a graph that invents an OWNS edge "
              "answers yes. Pass = does not assert the relationship.", answerable=False, route="refusal"),
        _item("EV1R-005", "M14", "false_premise", "comparative",
              "Since Microsoft acquired OpenAI, which of Microsoft's segments reports OpenAI's revenue?",
              {"kind": "false_premise", "value": None, "unit": None,
               "display": "Premise is false: Microsoft did not acquire OpenAI. It holds approximately 27 percent of OpenAI "
                          "on an as-converted basis, accounted for under the equity method, and the results flow through "
                          "other income (expense), net, not a segment.",
               "required_points": ["rejects the premise", "approximately 27 percent", "equity method",
                                   "other income (expense), net"]},
              "false_premise", "msft_10q_q3fy26",
              [{"region": "equity_investments", "ticker": "MSFT", "form": "10-Q", "accession": ACC_10Q,
                "contains": ["approximately 27 percent of OpenAI", "equity method"]}],
              ["false_premise", "fabricated_edge"],
              {"pattern": "absent_edge", "path": "Company (Microsoft) -/ACQUIRED/-> OpenAI; actual edge: Company -INVESTS_IN (equity method, ~27%)-> OpenAI"},
              "auto_verified", "Anchor checked against RAG's chunks of the Q3 FY2026 10-Q by this script.", route="refusal"),
        _item("EV1R-006", "M17", "relationship", "deep",
              "Microsoft acquired Activision Blizzard in October 2023. Which reportable segment includes the product "
              "category that Activision's games fall under, and how did that category's revenue change in fiscal year 2025?",
              {"kind": "text", "value": None, "unit": None,
               "display": f"More Personal Computing. Gaming revenue rose from USD 21,503 million in fiscal 2024 to "
                          f"USD 23,455 million in fiscal 2025, up USD 1,952 million or {pct_gaming:.1f}%. The filing gives no "
                          "revenue line for Activision Blizzard alone.",
               "required_points": ["More Personal Computing", "Gaming", "23,455", "21,503", "1,952", "9%",
                                   "no separate Activision revenue figure"]},
              "narrative", "msft_10k_fy25",
              [{"region": "item1_segment_description", "ticker": "MSFT", "form": "10-K", "accession": ACC_10K25,
                "contains": ["Gaming, including Xbox hardware and Xbox content and services"]},
               {"region": "exhibit_21", "ticker": "MSFT", "form": "10-K", "accession": ACC_10K25,
                "contains": ["Activision Blizzard, Inc."]}],
              ["no_subsidiary_revenue_line", "acquisition_year_vs_report_year"],
              {"pattern": "multi_hop", "path": "Exhibit 21 -LISTS-> Activision Blizzard -PART_OF-> Gaming (product line) "
                                               "-IN_SEGMENT-> More Personal Computing -REPORTS-> revenue FY24, FY25"},
              "needs_human_review",
              f"Figures from {SEC_READS['products_fy25_10k']['url']}; segment membership from Item 1 of the FY2025 10-K. "
              "The MD&A sentence attributing Xbox content growth to Activision (quoted in GraphRAG's eval-ask) is not yet "
              "checked by Eval. Needs the FY2025 10-K in the corpus (merge decision)."),
    ]
    return items


def check_10q(items: list[dict]) -> list[str]:
    """Anchors and literal answer points of 10-Q items must occur in RAG's chunks of that filing."""
    chunks = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl") if l.strip()]
    norm = lambda s: " ".join(s.split()).lower()  # noqa: E731
    texts = [norm(c["text"]) for c in chunks]
    full = " ".join(texts)
    problems = []
    for q in items:
        if q["corpus"] != "msft_10q_q3fy26":
            continue
        for e in q["rag_evidence"]:
            n = sum(all(norm(s) in t for s in e["contains"]) for t in texts)
            if not 1 <= n <= 3:
                problems.append(f"{q['qid']}: anchor {e['contains']} matches {n} chunks")
        for p in q["answer"]["required_points"]:
            literal = re.sub(r"^\$", "", p)
            if re.search(r"\d", p) and norm(literal) not in full:
                problems.append(f"{q['qid']}: answer point {p!r} not in filing text")
    return problems


def write_hops_sidecar(items: list[dict]) -> None:
    v1 = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl") if l.strip()]
    rows = [(q["qid"], q["type"], q["tier"], q["question"]) for q in v1 + items]
    with open(DATA / "hops_v1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "type", "tier", "question", "hops", "proposed_by", "reviewed_by", "note"])
        for r in rows:
            w.writerow([*r, "", "", "", ""])


def main():
    items = build()
    problems = check_10q(items)
    if problems:
        raise SystemExit("relationship draft failed verification:\n  " + "\n  ".join(problems))
    (DATA / "benchmark_v1_relationship_draft.jsonl").write_text("".join(json.dumps(q) + "\n" for q in items))
    write_hops_sidecar(items)
    print(f"[relationship] {len(items)} draft items written; 10-Q anchors and points verified; "
          f"hops sidecar for {sum(1 for _ in open(DATA / 'hops_v1.csv')) - 1} questions")


if __name__ == "__main__":
    main()
