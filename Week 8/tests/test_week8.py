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
