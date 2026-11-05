"""Week 7: ten-company Gold Set v2, snapshot match, decision and routing metrics, fixed-reader adapter, RAG anchor fixes."""
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from kpmg_eval.metrics.decision import decision_of, expected_decision, score_decisions
from kpmg_eval.metrics.routing import score_routing

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
TEN = {"AAPL", "CASY", "MCK", "MDT", "MSFT", "MU", "NKE", "NTAP", "PH", "TTWO"}
sys.path.insert(0, str(ROOT / "scripts"))


def gold():
    return [json.loads(l) for l in open(DATA / "benchmark_v2.jsonl")]


def test_gold_v2_is_ten_companies_only():
    for q in gold():
        if q["answerable"]:
            assert set(q["tickers"]) <= TEN, q["qid"]
    assert {t for q in gold() for t in q["tickers"] if q["answerable"]} == TEN


def test_every_question_has_a_route_and_snapshot_status():
    for q in gold():
        assert q["route_expected"] in {"sql", "text", "graph", "multi", "none"}, q["qid"]
        assert q["snapshot_status"] in {"in_snapshot", "review_required", "out_of_snapshot_by_design"}, q["qid"]


def test_snapshot_matches_data_and_graphrag():
    s = json.load(open(DATA / "snapshot_w7.json"))
    assert s["counts"] == {"10-K": 10, "10-Q": 11}
    assert s["match"]["data_inventory_2021_2026"]["contains_all_snapshot_filings"] is True
    assert s["match"]["eval_week6_list"]["same"] == 20


def test_micron_moves_to_fy2026_and_figures_tie():
    q = {x["qid"]: x for x in gold()}
    assert q["EV2-017"]["answer"]["value"] == 133_188_000_000
    assert q["EV2-018"]["answer"]["value"] == 84_969_000_000
    # FY2026 = nine months (from the Q3 10-Q) + derived Q4
    assert q["EV2-045"]["answer"]["value"] == 133_188_000_000 - 78_959_000_000
    assert q["EV2-050"]["answerable"] is False


def test_noncontrolling_interest_wording_and_distractors():
    q = {x["qid"]: x for x in gold()}
    assert "noncontrolling" in q["EV2-010"]["question"] and q["EV2-010"]["answer"]["value"] == 4_762_000_000
    assert any(d["value"] == 5_099_000_000 for d in q["EV2-010"]["gold"]["distractors"])


def test_exhibit21_questions_from_two_agreeing_reads():
    ex = json.load(open(DATA / "sec_reads" / "exhibit21_2026-11-05.json"))
    mu = ex["lists"]["MU"]["subsidiaries"]
    assert len(mu) == 21 and ex["lists"]["AAPL"]["total"] == len(ex["lists"]["AAPL"]["subsidiaries"]) == 19
    q = {x["qid"]: x for x in gold()}
    assert q["EV3-002"]["answer"]["required_points"] == ["China", "India", "Japan", "Singapore"]
    assert q["EV3-006"]["answerable"] is False and q["EV3-006"]["route_expected"] == "graph"


def test_decision_metric():
    cases = [{"expected": "answer", "predicted": "answer"}, {"expected": "off_topic", "predicted": "answer", "tool_calls": 2},
             {"expected": "clarify", "predicted": "clarify"}, {"expected": "abstain", "predicted": "answer", "gate_only": True,
                                                               "tool_calls": 1}]
    s = score_decisions(cases)
    assert s["decision_accuracy"] == 0.5 and s["unsafe_answer_rate"] == round(2 / 3, 3)
    assert s["off_topic_tool_calls"] == 2 and s["gate_violations"] == 1 and s["over_refusal_rate"] == 0.0
    assert decision_of({"answered": False}) == "abstain" and decision_of({"decision": "clarify", "answered": False}) == "clarify"


def test_expected_decisions_from_gold():
    q = {x["qid"]: x for x in gold()}
    assert expected_decision(q["EV2-048"]) == "answer"  # false premise: answer by correcting
    assert expected_decision(q["EV2-050"]) == "abstain"


def test_decision_suite_and_reference_gate():
    from run_decision_baselines import rule_gate
    assert rule_gate("Tell me a joke about accountants.", None) == ("off_topic", 0)
    assert rule_gate("What was revenue last quarter?", None)[0] == "clarify"
    assert rule_gate("What was Amazon's net income for the quarter ended March 31, 2026?", None)[0] == "abstain"
    assert rule_gate("What was Nike's total revenue for fiscal year 2026 (ended May 31, 2026), in USD millions?", "NKE") == ("answer", 1)
    r = json.load(open(RES / "decision_baselines.json"))["policies"]
    assert r["rule_gate"]["all"]["off_topic_tool_calls"] == 0 and r["always_answer"]["all"]["unsafe_answer_rate"] == 1.0


def test_routing_metric():
    s = score_routing([{"expected": "sql", "called": {"sql"}}, {"expected": "multi", "called": {"sql"}},
                       {"expected": "none", "called": set()}, {"expected": "graph", "called": {"sql", "text", "graph"}}])
    assert s["required_tools_called"] == 0.75 and s["exact_route"] == 0.5 and s["unneeded_calls_per_question"] == 0.5


def test_fixed_reader_with_stub_client():
    from systems import FixedReaderSystem

    class Stub:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    assert kw["model"] == "gpt-4o-mini" and kw["temperature"] == 0
                    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                        content="Total revenue was $82,886 million for the three months ended March 31, 2026 [2]."))],
                        usage=SimpleNamespace(prompt_tokens=900, completion_tokens=30))

    chunks = [{"chunk_id": f"c{i}", "text": "x", "ticker": "MSFT", "form": "10-Q"} for i in range(1, 9)]
    a = FixedReaderSystem(client=Stub()).answer({"question": "What was Microsoft's total revenue for the three months ended "
                                                             "March 31, 2026?", "session_ticker": "MSFT"},
                                                lambda q, f, k: chunks[:k])
    assert a["answered"] and a["citations"] == [{"id": "c2", "source": "vector_rag"}] and a["prompt_tokens"] == 900


def test_rag_anchor_fixes_are_specific():
    rows = list(csv.DictReader(open(RES / "rag_anchor_fixes.csv")))
    assert sum(r["action"] == "drop" for r in rows) == 10
    for r in rows:
        if r["action"] == "narrow" and r["suggested_n_chunks"]:
            assert 1 <= int(r["suggested_n_chunks"]) <= 3
