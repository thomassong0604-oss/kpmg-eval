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
    assert compatibility(gold["GSv0-MSFT-001"]["filters"])["graph_refuses"] == ["fiscal_period", "fiscal_year"]
    f, how = translate(gold["EV2-040"], snap)
    assert "ticker" not in f and how.endswith("ticker_list_dropped")


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
