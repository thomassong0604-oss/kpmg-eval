"""Tests for the Week-5 additions: Gold Set v1 integrity and the new metrics."""
import json
from pathlib import Path

import pytest

from kpmg_eval.metrics.abstention import auroc, best_threshold
from kpmg_eval.metrics.context import answer_in_context, figure_in
from kpmg_eval.metrics.diagnose import FactIndex, diagnose
from kpmg_eval.metrics.graph import score_fact_extraction
from kpmg_eval.metrics.numeric import score_numeric_diagnosed
from kpmg_eval.metrics.premise import classify_premise
from kpmg_eval.metrics.reasoning import score_steps
from kpmg_eval.metrics.robustness import jaccard_at_k, strip_period

DATA = Path(__file__).resolve().parent.parent / "data"
BENCH = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
BY = {q["qid"]: q for q in BENCH}
INDEX = FactIndex.from_jsonl(DATA / "msft_xbrl_facts.jsonl")


# ---------------- Gold Set v1 integrity ----------------
def test_benchmark_shape():
    assert len(BENCH) == 100 and len(BY) == 100
    assert sum(q["source"] == "rag_gold_v0" for q in BENCH) == 30
    assert all(q["rag_qid"] == q["qid"] for q in BENCH if q["source"] == "rag_gold_v0")
    for q in BENCH:
        if q["answer"]["kind"] in ("money", "percent", "pp", "number"):
            assert q["gold"] and q["gold"]["value"] is not None, q["qid"]
        assert q["filters"], q["qid"]


def test_expected_values_recompute_from_facts():
    # spot checks that the builder computed, not typed, the answers
    assert BY["GSv0-MSFT-001"]["answer"]["value"] == 82_886e6
    assert BY["GSv0-MSFT-013"]["answer"]["value"] == 18.30
    q = next(q for q in BENCH if "operating margin (operating income divided by total revenue)" in q["question"])
    v = q["fact_values"]
    assert round(v["OperatingIncomeLoss|Q|"] / v["RevenueFromContractWithCustomerExcludingAssessedTax|Q|"] * 100, 2) == q["answer"]["value"]


def test_rag_format_file_loads_with_rag_rules():
    rows = [json.loads(l) for l in open(DATA / "benchmark_v1_rag_format.jsonl")]
    for r in rows:
        assert {"qid", "tier", "question", "filters", "gold", "expected", "quantitative", "status"} <= set(r)
        assert r["gold"]["evidence"] and all("contains" in e for e in r["gold"]["evidence"])
        assert set(r["filters"]) <= {"ticker", "cik", "form", "accession_number", "fiscal_year", "fiscal_period", "is_table"}


# ---------------- answer-in-context ----------------
def test_figure_in_whole_token_and_parentheses():
    assert figure_in("4,832", "LinkedIn | 4,832 | 4,311")
    assert not figure_in("4,832", "LinkedIn | 14,832 |")
    assert figure_in("84,669", "Net cash used in investing | ( 84,669) |")
    assert answer_in_context(["82,886", "70,066"], ["Total revenue 82,886", "x", "70,066"], 3) == 1.0
    assert answer_in_context(["82,886", "70,066"], ["Total revenue 82,886", "x", "70,066"], 2) == 0.0


# ---------------- abstention ----------------
def test_auroc():
    assert auroc([3, 4, 5], [1, 2]) == 1.0
    assert auroc([1, 2], [3, 4]) == 0.0
    assert auroc([1, 2], [1, 2]) == 0.5
    assert best_threshold([3, 4, 5], [1, 2])["balanced_accuracy"] == 1.0


# ---------------- reasoning-step accuracy ----------------
def _margin_q():
    return next(q for q in BENCH if "operating margin (operating income divided by total revenue)" in q["question"])


def _steps(q, oi=None, rev=None, result=None):
    (k1, k2), (v1, v2) = q["facts"], list(q["fact_values"].values())
    oi, rev = oi or (k1, v1), rev or (k2, v2)
    s = [{"id": "s1", "op": "lookup", **{x: oi[0][x] for x in ("concept", "period_start", "period_end")}, "value": oi[1]},
         {"id": "s2", "op": "lookup", **{x: rev[0][x] for x in ("concept", "period_start", "period_end")}, "value": rev[1]}]
    s.append({"id": "s3", "op": "divide", "args": ["s1", "s2"], "value": result if result is not None else oi[1] / rev[1]})
    return s


def test_reasoning_oracle_is_perfect():
    q = _margin_q()
    r = score_steps(q["facts"], list(q["fact_values"].values()), q["answer"]["value"] / 100, _steps(q))
    assert r["input_recall"] == 1.0 and r["arithmetic_valid"] == 1.0 and r["final_correct"] and r["first_error"]["reason"] == "none"


def test_reasoning_wrong_period_input():
    q = _margin_q()
    k = dict(q["facts"][0], period_start="2025-07-01")                  # nine-month operating income
    r = score_steps(q["facts"], list(q["fact_values"].values()), q["answer"]["value"] / 100, _steps(q, oi=(k, 114_634e6)))
    assert r["first_error"]["reason"] == "wrong_period" and not r["final_correct"]


def test_reasoning_bad_arithmetic_and_wrong_value():
    q = _margin_q()
    gold = list(q["fact_values"].values())
    r = score_steps(q["facts"], gold, q["answer"]["value"] / 100, _steps(q, result=0.5))
    assert r["first_error"]["reason"] == "bad_arithmetic"
    r = score_steps(q["facts"], gold, q["answer"]["value"] / 100, _steps(q, oi=(q["facts"][0], 38_000e6)))
    assert r["first_error"]["reason"] == "wrong_fact_value"


# ---------------- false premise ----------------
FP = [q for q in BENCH if q["type"] == "false_premise"]


@pytest.mark.parametrize("resp,label", [
    ("Revenue did not decline. It increased 18.3% to $82,886 million from $70,066 million.", "corrected"),
    ("Actually, revenue rose year over year, so the premise is wrong.", "rejected"),
    ("Revenue declined mainly because of lower Windows OEM sales and weaker Xbox demand.", "accepted"),
])
def test_premise_revenue(resp, label):
    q = next(q for q in FP if "decline" in q["question"])
    assert classify_premise(resp, q["answer"]["required_points"]) == label


def test_premise_segment():
    q = next(q for q in FP if "Microsoft Cloud" in q["question"])
    assert classify_premise("Microsoft Cloud is not a reportable segment; Microsoft has three segments.",
                            q["answer"]["required_points"]) == "corrected"
    assert classify_premise("Microsoft Cloud operating income was $21.4 billion.", q["answer"]["required_points"]) == "accepted"


# ---------------- fact-index diagnosis ----------------
def test_diagnose_dimension_concept_period():
    q = BY["EV1-001"]                                                   # consolidated operating income, 3M
    seg = score_numeric_diagnosed(q, {"answered": True, "value": 20_973e6, "value_text": "20,973 million"}, INDEX)
    assert seg.label == "wrong_dimension"                               # read the PBP segment row
    ytd = score_numeric_diagnosed(q, {"answered": True, "value": 114_634e6, "value_text": "114,634 million"}, INDEX)
    assert ytd.label == "wrong_period"
    q = BY["EV1-011"]                                                   # long-term debt (non-current)
    cur = score_numeric_diagnosed(q, {"answered": True, "value": 8_839e6, "value_text": "8,839 million"}, INDEX)
    assert cur.label == "wrong_concept"
    ok = score_numeric_diagnosed(BY["EV1-001"], {"answered": True, "value": 38_398e6, "value_text": "38,398 million"}, INDEX)
    assert ok.passed


def test_diagnose_returns_none_for_unknown_value():
    assert diagnose(123_457e6, BY["EV1-001"]["gold"]["evidence"][0], INDEX) is None


# ---------------- graph: dims in the fact key ----------------
def test_graph_dims_collision():
    gold = [{"cik": "1", "concept": "c", "period_start": "a", "period_end": "b", "unit": "USD", "value": 10},
            {"cik": "1", "concept": "c", "period_start": "a", "period_end": "b", "unit": "USD", "value": 4, "dims": {"seg": "X"}}]
    assert score_fact_extraction(gold, gold)["f1"] == 1.0
    dropped = [{k: v for k, v in g.items() if k != "dims"} for g in gold]
    r = score_fact_extraction(dropped, gold)
    assert r["n_pred_collisions"] == 1 and r["recall"] == 0.5


# ---------------- robustness ----------------
def test_strip_period_and_jaccard():
    assert strip_period("What was Microsoft's operating income for the three months ended March 31, 2026, in USD millions?") == \
        "What was Microsoft's operating income, in USD millions?"
    assert strip_period("What were Microsoft's total assets as of March 31, 2026, in USD millions?") == \
        "What were Microsoft's total assets, in USD millions?"
    assert jaccard_at_k(["a", "b"], ["b", "c"], 2) == pytest.approx(1 / 3)


# ---------------- grader bugs found by the oracle run of the grading pipeline ----------------
def test_zero_truth_is_not_wrong_sign():
    q = next(q for q in BENCH if q["gold"] and q["gold"]["value"] == 0)
    assert score_numeric_diagnosed(q, {"answered": True, "value": 0.0, "value_text": "0 million"}, INDEX).passed


def test_trailing_zero_sig_figs():
    q = next(q for q in BENCH if q["gold"] and q["gold"]["value"] == 93_500e6)
    assert q["gold"]["min_sig_figs"] == 3
    assert score_numeric_diagnosed(q, {"answered": True, "value": 93_500e6, "value_text": "93,500 million"}, INDEX).passed


def test_whole_percent_when_filing_states_whole_percent():
    q = next(q for q in BENCH if "effective tax rate did Microsoft report for the nine months" in q["question"])
    assert score_numeric_diagnosed(q, {"answered": True, "value": 20.0, "value_text": "20%"}, INDEX).passed
    assert not score_numeric_diagnosed(q, {"answered": True, "value": 19.0, "value_text": "19%"}, INDEX).passed


def test_citation_support_per_share_and_parenthesised_outflows():
    from kpmg_eval.metrics.citation import score_citations
    assert score_citations([{"text": "4.27", "cites": ["c"]}], {"c": "| Diluted | $ 4.27 | $ 3.46 |"})["numeric_support"] == 1.0
    assert score_citations([{"text": "30,876 million", "cites": ["c"]}], {"c": "| Additions | ( 30,876) | ( 16,745) |"})["numeric_support"] == 1.0
    assert score_citations([{"text": "30,877 million", "cites": ["c"]}], {"c": "| Additions | ( 30,876) |"})["numeric_support"] == 0.0


# ---------------- filters ----------------
def test_filters_extraction_and_filing_pr():
    import sys
    sys.path.insert(0, str(DATA.parent / "scripts"))
    from rag_fiscal import fiscal_label
    from kpmg_eval.filters import extract_filters, filing_filter_pr
    scope = json.loads((DATA.parent / "config" / "scope.json").read_text())
    f = extract_filters("What was NVIDIA's revenue for its fiscal Q1 2027 (quarter ended April 26, 2026)?", scope, fiscal_label)
    assert f["ticker"] == "NVDA" and f["fiscal_year"] == 2027 and f["fiscal_period"] == "Q1"
    f = extract_filters("What was Microsoft's operating income for the three months ended March 31, 2026?", scope, fiscal_label)
    assert (f["fiscal_year"], f["fiscal_period"]) == (2026, "Q3")
    assert extract_filters("Which segment includes LinkedIn?", scope, fiscal_label) == {}
    assert extract_filters("Which segment includes LinkedIn?", scope, fiscal_label, session_ticker="MSFT") == {"ticker": "MSFT"}
    pool = [{"accession": "a", "ticker": "MSFT", "form": "10-Q", "fiscal_year": 2026, "fiscal_period": "Q3"},
            {"accession": "b", "ticker": "MSFT", "form": "10-Q", "fiscal_year": 2026, "fiscal_period": "Q2"}]
    assert filing_filter_pr({"ticker": "MSFT", "form": "10-Q"}, pool, {"a"}) == {"kept": 2, "gold_in_pool": 1, "recall": 1.0, "precision": 0.5}
    assert filing_filter_pr({"ticker": "MSFT", "fiscal_period": "Q2"}, pool, {"a"})["recall"] == 0.0
