"""Week 8 tests: side-by-side scoring, Exhibit 21 traversal, messy wording, routing definitions."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import run_messy_wording as mw  # noqa: E402
import run_side_by_side as sbs  # noqa: E402
from kpmg_eval.metrics.routing import score_routing  # noqa: E402


def q_num(values, distractors=()):
    return {"answerable": True, "answer_type": "exact_numeric", "type": "calculation", "answer": {},
            "facts": [{"unit": "USD"} for _ in values], "fact_values": {str(i): v for i, v in enumerate(values)},
            "gold": {"distractors": [{"value": d} for d in distractors]}, "rag_evidence": []}


def ev(*vals):
    return [{"text": f"x: {v}", "metadata": {"value_num": v}} for v in vals]


def test_graphrag_needs_every_input_value():
    q = q_num([82886e6, 70066e6], distractors=[241832e6])
    assert sbs.score_gr(q, ev(82886e6, 70066e6))["needed_in_evidence"] is True
    assert sbs.score_gr(q, ev(82886e6))["needed_in_evidence"] is False
    assert sbs.score_gr(q, ev(82886e6, 70066e6, 241832e6))["distractor_shown"] is True


def test_rag_figures_match_printed_millions():
    q = q_num([82886e6])
    out = sbs.score_rag(q, ["Total revenue 82,886 70,066"])
    assert out["needed_in_evidence"] is True


def test_unanswerable_kind():
    assert sbs.kind({"answerable": False, "answer_type": "refusal"}) == "unanswerable_or_false_premise"
    assert sbs.kind({"answerable": True, "answer_type": "false_premise"}) == "unanswerable_or_false_premise"


def test_ex21_graph_join_and_owner():
    g = sbs.Ex21Graph({"A": [("A Japan KK", "Japan"), ("A Inc.", "Delaware, U.S.")],
                       "B": [("B Japan", "Japan"), ("B UK", "United Kingdom"), ("B LLC", "Idaho")]})
    assert g.countries("A") & g.countries("B") == {"Japan"}
    assert len(g.non_us("B")) == 2
    assert g.owner("B UK") == "B" and g.owner("Nobody") is None


def test_perturbations_keep_meaning_words():
    q = "What was Microsoft's total revenue for the three months ended March 31, 2026? State the amount in USD millions."
    assert "Microsfot" in mw.typo_company(q)
    assert "revnue" in mw.typo_terms(q)
    c = mw.casual(q)
    assert c == "what was msft total revenue for the three months ended march 31 2026"


def test_fuzzy_names_catch_typos_not_off_topic():
    assert mw.companies_in_fuzzy("whats mircon revenue") == ["MU"]
    assert mw.companies_in_fuzzy("msft operating income") == ["MSFT"]
    assert mw.companies_in_fuzzy("What is the capital of Australia?") == []


def test_unneeded_calls_definition():
    # combined on a sql question: 3 calls, 2 not needed; keyword exact: 0
    r = score_routing([{"expected": "sql", "called": {"sql", "text", "graph"}}, {"expected": "sql", "called": {"sql"}}])
    assert r["unneeded_calls_per_question"] == 1.0 and r["tool_calls_per_question"] == 2.0


def test_gold_v2_1_changes_only_anchors():
    import json
    a = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v2.jsonl")]
    b = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v2_1.jsonl")]
    assert [q["qid"] for q in a] == [q["qid"] for q in b]
    for x, y in zip(a, b):
        assert {k: v for k, v in x.items() if k != "rag_evidence"} == {k: v for k, v in y.items() if k != "rag_evidence"}
    # no auto-converted region anchors remain; the four RAG flagged now point at the right sentences
    assert not any(e.get("anchor_source") == "region" for q in b for e in q["rag_evidence"])
    by = {q["qid"]: [c for e in q["rag_evidence"] for c in e["contains"]] for q in b}
    assert "development across the portfolio." not in by["GSv0-MSFT-019"]
    assert any("relatively unchanged" in c for c in by["GSv0-MSFT-019"])
    assert "194,370" not in by["GSv0-MSFT-027"]


def test_dims_from_mock_real_and_gold_give_one_key():
    from kpmg_eval.keys import norm_dims
    mock = {"StatementBusinessSegmentsAxis": "Intelligent Cloud"}
    real = [{"axis": "us-gaap:StatementBusinessSegmentsAxis", "member": "msft:IntelligentCloudMember", "type": "explicit"}]
    gold = (("us-gaap:StatementBusinessSegmentsAxis", "msft:IntelligentCloudMember"),)
    assert norm_dims(mock) == norm_dims(real) == norm_dims(gold)
    assert norm_dims([]) == norm_dims(None) == ()


def test_structured_key_does_not_need_section():
    from kpmg_eval.graphrag_adapter import evidence_key
    from kpmg_eval.keys import Level
    k = evidence_key({"cik": "0000789019", "accession_number": "0001193125-26-191507", "section": None,
                      "section_id": None, "metadata": {"fact_id": "f1", "concept": "us-gaap:Revenues",
                                                       "period_start": "2026-01-01", "period_end": "2026-03-31",
                                                       "unit": "iso4217:USD", "dimensions": []}})
    assert k.level == Level.FACT and k.section is None


def test_graphrag_filter_translation():
    import json
    from kpmg_eval.graphrag_filters import compatibility, load_snapshot, translate
    snap = load_snapshot(ROOT / "data" / "snapshot_w7.json")
    gold = {json.loads(l)["qid"]: json.loads(l) for l in open(ROOT / "data" / "benchmark_v2_1.jsonl")}
    f, how = translate(gold["GSv0-MSFT-001"], snap)
    assert f == {"ticker": "MSFT", "accession_number": "0001193125-26-191507"} and how == "one_filing"
    c = compatibility(gold["GSv0-MSFT-001"]["filters"])
    assert c["graph_refused_at_4e89acb"] == ["fiscal_period", "fiscal_year"] and c["graph_refuses"] == []
    assert c["graph_ignores"] == ["fiscal_period", "fiscal_year"]          # GraphRAG #70
    f, how = translate(gold["EV2-040"], snap)                              # cross-company: lists, an IN on both arms
    assert how == "several_filings" and isinstance(f["ticker"], list) and len(f["accession_number"]) == 10


def test_agents_can_plug_their_router_into_the_routing_script(tmp_path):
    import json
    import run_routing_baselines as rrb
    mod = tmp_path / "orch.py"
    mod.write_text("def route(question, session):\n    return ['structured_search'] if 'revenue' in question.lower() else ['sec_filing_search']\n")
    fn = rrb.load_router(f"{mod}:route")
    assert fn("Total revenue?", "MSFT") == {"sql"} and fn("Why?", None) == {"text"}
    gold = [{"qid": "Q1", "question": "a"}, {"qid": "Q2", "question": "b"}]
    calls = tmp_path / "calls.jsonl"
    calls.write_text(json.dumps({"qid": "Q1", "tools": ["graph_search", "retrieve"]}) + "\n")
    fn = rrb.load_calls(str(calls), gold)
    assert fn("a", None) == {"graph", "text"} and fn("b", None) == set()


# ---- Week 8, 11/11: RAG's end-to-end round 1 (grading notes) -> Gold Set v2.2
def _gold(v):
    import json
    return {json.loads(l)["qid"]: json.loads(l) for l in open(ROOT / "data" / f"benchmark_{v}.jsonl")}


def test_gold_v2_2_changes_only_grading_fields():
    a, b = _gold("v2_1"), _gold("v2_2")
    assert list(a) == list(b)
    for qid in a:
        x, y = a[qid], b[qid]
        assert x["question"] == y["question"] and x["answerable"] == y["answerable"]
        assert x["gold"] is None or x["gold"]["value"] == y["gold"]["value"]
        strip = lambda q: {k: v for k, v in q.items() if k not in ("rag_evidence", "route_expected", "route_note", "gold", "answer")}  # noqa: E731
        if qid in ("EV3-008", "EV3-009"):           # graph-pattern label only (fiscal_label, not relationship)
            assert y["graph"]["pattern"] == "fiscal_label"
            x, y = {**x, "graph": None}, {**y, "graph": None}
        assert strip(x) == strip(y)
    assert [q for q in b if b[q]["route_expected"] != a[q]["route_expected"]] == ["EV1R-002", "EV1R-006"]
    assert sum("values" in (q["gold"] or {}) for q in b.values()) == 7
    assert b["EV1-015"]["gold"]["min_sig_figs"] == 2 and b["EV1-027"]["gold"]["min_sig_figs"] == 2
    # no answerable question is left without a text anchor except the ones with no text (routes none) or by design
    assert all(b[q]["rag_evidence"] for q in ("EV2-035", "EV2-036", "EV2-037", "EV2-044"))
    # v2.1 put two sentences in one evidence item; RAG's chunker splits them, so v2.2 has one item per point
    assert all(len(e["contains"]) == 1 for e in b["GSv0-MSFT-019"]["rag_evidence"])


def test_sig_fig_floor_is_the_printed_precision():
    from kpmg_eval.metrics.numeric import score_numeric
    ans = {"answered": True, "value": 0.91, "value_text": "$0.91 per share", "unit": "USD/shares"}
    assert score_numeric(_gold("v2")["EV1-015"], ans).label == "too_imprecise"
    assert score_numeric(_gold("v2_2")["EV1-015"], ans).passed


def test_multi_value_question_needs_every_figure():
    from kpmg_eval.metrics.numeric import score_numeric
    q = _gold("v2_2")["EV1-043"]
    text = ("More Personal Computing revenue fell $179 million, while operating income rose $146 million. "
            "Cost of revenue fell $584 million.")
    assert score_numeric(q, {"answered": True, "value": None, "answer_text": text}).passed      # EV1-043 as RAG wrote it
    r = score_numeric(q, {"answered": True, "value": 146e6, "value_text": "$146 million",
                          "answer_text": "Operating income rose $146 million; revenue fell $179 million."})
    assert not r.passed and r.label == "partial_values" and r.values_stated == (2, 3)
    # a wrong headline value fails even if the text has the figures
    assert not score_numeric(q, {"answered": True, "value": 3672e6, "value_text": "$3,672 million", "answer_text": text}).passed
    # structured values are sign-sensitive
    vals = [{"value": 146e6, "unit": "USD"}, {"value": -179e6, "unit": "USD"}, {"value": -584e6, "unit": "USD"}]
    assert score_numeric(q, {"answered": True, "value": 146e6, "values": vals}).passed
    vals[1]["value"] = 179e6
    assert not score_numeric(q, {"answered": True, "value": 146e6, "values": vals}).passed


def test_premise_rejections_seen_in_round1():
    from kpmg_eval.metrics.premise import classify_premise
    g = _gold("v2_2")
    assert classify_premise("Take-Two was not profitable in fiscal 2026: it reported a net loss of $298.2 million.",
                            g["EV2-048"]["answer"]["required_points"]) == "corrected"
    assert classify_premise("Microsoft did not acquire OpenAI; it reported an approximately 25% investment.",
                            g["EV1R-005"]["answer"]["required_points"]) == "corrected"


def test_categorical_answers_normalise_quarters_and_quotes():
    from kpmg_eval.metrics.categorical import score_categorical
    assert score_categorical(["fiscal 2027", "Q1"], "The quarter ended August 31, 2026 was Nike’s first quarter of fiscal 2027.")["passed"]
    assert score_categorical(["fiscal 2027", "Q1"], "It is the first quarter of Medtronic’s fiscal year 2027 (FY2027 Q1).")["passed"]
    assert score_categorical(["Casey's", "NetApp"], "Casey’s and NetApp end in April.")["passed"]
    assert not score_categorical(["fiscal 2026", "Q3"], "It is Micron's fiscal 2026 second quarter.")["passed"]


def test_judge_guard_needs_a_real_quote():
    import run_narrative_judge as nj
    v = nj.guard([{"point": 1, "verdict": "stated", "quote": "Azure grew"},
                  {"point": 2, "verdict": "stated", "quote": "not in the answer"}], "Revenue rose as Azure grew 40%.", 3)
    assert v == ["stated", "missing", "missing"]


def test_round1_numbers_reproduced_when_private_files_present():
    import json
    import subprocess
    import pytest
    ans = ROOT / "private" / "rag_round1_answer_blocks.jsonl"
    if not ans.exists():
        pytest.skip("RAG's round-1 answers are private (not in the repo)")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "grade_answer_blocks.py"), "--answers", str(ans),
                    "--tag", "pytest_tmp"], check=True, capture_output=True)
    out = json.loads((ROOT / "results" / "answers_pytest_tmp.json").read_text())
    for f in ROOT.glob("results/answers_pytest_tmp*"):
        f.unlink()
    sub = out["by_gold_set"]["v2"]["rag_subset"]          # RAG's own figures, 11/11
    assert (sub["numeric_accuracy"]["k"], sub["numeric_accuracy"]["n"]) == (87, 93)
    assert sub["refusal"]["balanced_raa_incl_false_premise"] == 0.977 and sub["refusal"]["unanswerable_refused"] == "10/10"


def test_routing_doc_numbers_come_from_the_results():
    import json
    rb = json.loads((ROOT / "results" / "routing_baselines.json").read_text())
    md = (ROOT / "ROUTING_EXAMPLES.md").read_text()
    for k in ("combined", "keyword", "text_only"):
        assert f"{rb['routers'][k]['coverage'] * 100:.1f}% ({rb['routers'][k]['n_covered']}/{rb['n']})" in md


# ---- Week 8, 11/11: GraphRAG's round 1 (Aura + 20-filing store) checked against Eval's rerun
def test_graphrag_round1_reproduced_question_by_question():
    import json
    chk = json.loads((ROOT / "results" / "graphrag_round1_check.json").read_text())
    r = chk["reproduction_structured_translated"]
    assert r["questions"] == 155 and r["questions_identical"] == 155
    assert chk["structured_gold_filters_before_after_70"]["all_differences_on_list_filter_questions"]
    # GraphRAG's own results file carries no host or local path
    meta = json.loads((ROOT / "results" / "graphrag_round1_graphrag_aura.json").read_text())
    assert all(v == "registered" for v in meta["backend_status"].values())


def test_hops_sheet_merges_graphrag_and_keeps_both_ontologies():
    import csv
    rows = {r["qid"]: r for r in csv.DictReader(open(ROOT / "data" / "hops_v2.csv"))}
    assert len(rows) == 155
    assert sum(r["graph_note"].startswith("XBRL facts are not in the graph") and not r["hops"] for r in rows.values()) == 95
    assert rows["EV3-002"]["hops"] == "2" and rows["EV3-002"]["eval_reference_edges"] == "4"   # ontology, not counting
    assert rows["EV1R-002"]["route_expected"] == "text"                                         # v2.2 route kept
    # after GraphRAG's PR #71 (Eval's row check acted on): false premises take their route's support, EV1R-001 blocked
    assert rows["EV1-068"]["eval_check"] == "ok" and rows["EV1R-001"]["graph_support"] == "blocked"
    # Eval's checks now: NetApp's 10-Q is not in the corpus; anchors in the notes are outside the graph's sections
    assert "not in the 20-filing corpus" in rows["EV3-008"]["eval_check"]
    assert "outside the five section types" in rows["GSv0-MSFT-006"]["eval_check"]


def test_dropped_connections_are_infra_not_arm_failures():
    import run_graphrag_round1 as r1
    assert r1.is_transient("ServiceUnavailable: Failed to read from defunct connection IPv4Address(('x', 7687))")
    assert not r1.is_transient("FilterNotSupportedError: the graph arm cannot filter on fiscal_year")


def test_graph_arm_prose_split_by_section_scope():
    import json
    g = json.loads((ROOT / "results" / "graphrag_round1_check.json").read_text())["graph_prose_by_scope"]
    assert (g["in_scope"]["hits"], g["in_scope"]["n"]) == (10, 20)
    assert g["outside_scope"]["hits"] == 0 and g["not_in_corpus_or_chunks"]["hits"] == 0


# ---- Week 8, 11/11: the Agents' API v0.2 (/query) graded at decision and evidence level, with the fallback cases
def _resp(qid, status, es, trig=False, used=False, text="", url=None, filters=None, reasons=()):
    return {"trace_id": f"t:{qid}", "status": status, "evidence_status": es, "weak_reasons": list(reasons),
            "fallback_triggered": trig, "fallback_used": used, "filters": filters or {}, "answer": None,
            "evidence": [{"text": text, "metadata": {"source_url": url}}] if text else [],
            "citations": [{"source_url": url}] if url else [], "logs": [], "error": None}


def test_agent_api_v02_responses_grade_into_decisions_evidence_and_fallback_cases():
    import json
    import grade_agent_run as ga
    from kpmg_eval.agent_api import accession_from_url, qid_of
    url = "https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm"
    assert accession_from_url(url) == "0001193125-26-191507"
    gold = {q["qid"]: q for q in map(json.loads, open(ROOT / "data" / "benchmark_v2_2.jsonl"))}
    assert qid_of({"trace_id": "agents_v02:EV1-062"}, gold, {}) == "EV1-062"
    gf = gold["GSv0-MSFT-001"]["filters"]
    rs = {"GSv0-MSFT-001": _resp("GSv0-MSFT-001", "SUCCESS", "ok", text="Total revenue 82,886 70,066", url=url, filters=gf),
          "GSv0-MSFT-019": _resp("GSv0-MSFT-019", "SUCCESS", "weak", True, True, reasons=["methods_disagree"],
                                 text=" ".join(c for e in gold["GSv0-MSFT-019"]["rag_evidence"] for c in e["contains"])),
          "EV1-062": _resp("EV1-062", "NO_EVIDENCE", "empty", True, False, reasons=["filter_no_match"]),
          "GSv0-MSFT-023": _resp("GSv0-MSFT-023", "NO_EVIDENCE", "ok"),
          "GSv0-MSFT-002": {**_resp("GSv0-MSFT-002", "ERROR", None), "error": "backend"}}
    import csv
    cases = {r["qid"]: r for r in csv.DictReader(open(ROOT / "data" / "fallback_cases_w8.csv"))}
    rows = []
    for qid, r in rs.items():
        row = ga.grade_one(gold[qid], r, cases[qid])
        row["_kind"] = ga.sbs.kind(gold[qid])
        rows.append(row)
    s = ga.summarise(rows)
    assert s["errors_not_scored"] == ["GSv0-MSFT-002"]
    assert s["decision"]["unanswerable_abstained"]["k"] == 1 and s["evidence"]["number"]["k"] == 1
    assert s["citations_cite_a_gold_filing"]["k"] == 1 and s["filters"]["all_keys_match"]["k"] == 1
    oc = s["fallback"]["observed_cases"]
    assert set(oc) >= {"1_empty_to_graphrag", "2_weak_to_graphrag", "3_ok_but_no_evidence", "rag_only"}
    assert cases["GSv0-MSFT-019"]["case"] == "rescue" and cases["GSv0-MSFT-023"]["case"] == "answer_in_rag_evidence"
    # case 4: the same question without fallback was a miss, with it right -> rescued
    base = [dict(rows[0]), {**rows[1], "decision": "abstain", "decision_correct": False, "needed_in_evidence": None}]
    assert ga.compare(rows, base)["rescued_qids"] == ["GSv0-MSFT-019"]


def test_same_figure_tolerance_small_values():
    """11/14: per-share values and rates are matched to half a cent, amounts to half a unit."""
    import run_side_by_side as sbs
    assert sbs.same(4.27, 4.27) and not sbs.same(4.28, 4.27)          # basic EPS is not diluted EPS
    assert not sbs.same(0.83, 0.91) and not sbs.same(0.0, 0.2)
    assert sbs.same(31423000000.4, 31423000000.0) and not sbs.same(40152000000.0, 31423000000.0)
    q = {"qid": "x", "type": "extraction", "answerable": True, "answer_type": "exact_numeric", "fact_values": {"f1": 4.27},
         "gold": {"value": 4.27, "kind": "money", "distractors": [{"label": "wrong_concept", "value": 4.28}]}}
    ev = [{"metadata": {"value_num": 4.28}, "text": ""}]
    r = sbs.score_gr(q, ev)
    assert r["needed_in_evidence"] is False and r["top1_right"] is False and r["top1_wrong_period"] is True
