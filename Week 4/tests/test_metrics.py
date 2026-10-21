import json
from pathlib import Path

import pytest

from kpmg_eval.keys import EvalKey, Level, matches
from kpmg_eval.metrics.citation import score_citations
from kpmg_eval.metrics.graph import entity_linking_accuracy, path_recall, score_edges, score_fact_extraction
from kpmg_eval.metrics.numeric import score_numeric
from kpmg_eval.metrics.ops import ops_metrics, run_to_run_consistency
from kpmg_eval.metrics.refusal import classify_response, score_raa
from kpmg_eval.metrics.retrieval import rag_adapter, score_retrieval
from kpmg_eval.normalize import extract_quantities
from kpmg_eval.stats import paired_bootstrap_diff, wilson

DATA = Path(__file__).resolve().parent.parent / "data"
BENCH = {json.loads(l)["qid"]: json.loads(l) for l in open(DATA / "benchmark_v0.jsonl")}


# ---------------- normalize ----------------
@pytest.mark.parametrize("text,value,kind", [
    ("$21,155 million", 21_155e6, "money"),
    ("$21.2bn", 21.2e9, "money"),
    ("21,155M", 21_155e6, "money"),
    ("$(412)", -412, "money"),
    ("down 5.9%", 5.9, "percent"),
    ("a 3.6 percentage point gain", 3.6, "pp"),
])
def test_extract(text, value, kind):
    q = extract_quantities(text)[0]
    assert q.value == pytest.approx(value) and q.kind == kind


def test_identifiers_are_not_numbers():
    assert extract_quantities("10-Q filed 2026-08-06, accession 0001628280-26-054343, Q2 FY2026") == []


# ---------------- keys ----------------
def test_rag_chunk_and_graph_fact_share_keys():
    chunk = {"cik": "19617", "accession_number": "000162828026054343", "section": "Part I Item 2 MD&A"}
    k = EvalKey.from_rag_chunk(chunk)
    assert k.cik == "0000019617" and k.accession == "0001628280-26-054343"
    assert matches(k, EvalKey(cik="19617", accession="0001628280-26-054343", section="Part I Item 2"), Level.SECTION)
    assert not matches(k, EvalKey(cik="19617", accession="0001628280-26-054343", section="Part II"), Level.SECTION)


def test_fact_level_ignores_which_filing_restated_it():
    g = EvalKey(cik="1", accession="A", concept="us-gaap:NetIncomeLoss", period_start="2024-01-01", period_end="2024-12-31", unit="USD")
    c = EvalKey(cik="1", accession="B", concept="us-gaap:NetIncomeLoss", period_start="2024-01-01", period_end="2024-12-31", unit="USD")
    assert matches(c, g)


# ---------------- numeric accuracy ----------------
@pytest.mark.parametrize("answer,label", [
    ({"answered": True, "value": 21_155e6, "unit": "USD"}, "correct"),
    ("JPMorgan earned $21.2 billion in Q2 2026.", "correct"),
    ("Net income was $21,155 million.", "correct"),
    ({"answered": True, "value": 37_649e6, "unit": "USD"}, "wrong_period"),     # six-month figure
    ({"answered": True, "value": 21_155e3, "unit": "USD"}, "wrong_scale"),
    ("About $21 billion.", "too_imprecise"),
    ({"answered": False}, "false_refusal"),
    ("Net income was $19.8 billion.", "wrong_value"),
])
def test_naa_labels(answer, label):
    assert score_numeric(BENCH["E02"], answer).label == label


def test_naa_sign_and_percent():
    assert score_numeric(BENCH["T06"], "Honeywell lost $115 million in Q4 2025: -$115 million.").passed
    assert score_numeric(BENCH["T06"], {"answered": True, "value": 115e6, "unit": "USD"}).label == "wrong_sign"
    assert score_numeric(BENCH["T03"], "Up 7.0% year over year.").passed
    assert score_numeric(BENCH["T03"], "Up about 7%.").label == "too_imprecise"


def test_naa_concept_confusion():
    assert score_numeric(BENCH["E05"], {"answered": True, "value": 14_452e6, "unit": "USD"}).label == "wrong_concept"


# ---------------- refusal ----------------
def test_hedged_answer_counts_as_answered():
    assert classify_response("The 10-Q does not disclose units, but Apple likely sold around 60 million iPhones.") == "answered"
    assert classify_response("Apple does not report unit sales; iPhone net sales were $54,252 million.") == "refused"


def test_raa_rates():
    r = score_raa([(True, "Net income was $5.0B"), (True, "I cannot determine this."), (False, "Not disclosed."), (False, "$120 billion")])
    assert r["raa"] == 0.5 and r["appropriate_refusal_rate"] == 0.5 and r["unnecessary_refusal_rate"] == 0.5
    assert r["balanced_raa"] == 0.5 and r["critical_flags"] == 1


# ---------------- retrieval ----------------
def test_retrieval_metrics():
    gold = [{"cik": "1", "accession": "A", "section": "Item 7", "contains": ["64,809"], "level": "SECTION"},
            {"cik": "2", "accession": "B", "level": "FILING"}]
    ranked = rag_adapter([
        {"cik": "1", "accession_number": "A", "section": "Item 1A", "text": "risk"},
        {"cik": "1", "accession_number": "A", "section": "Item 7", "text": "Total net revenue 64,809"},
        {"cik": "2", "accession_number": "B", "section": "Item 2", "text": "anything"},
    ])
    s = score_retrieval(gold, ranked, ks=(1, 3), expected_ciks={"0000000001", "0000000002"})
    assert s["mrr"] == 0.5 and s["hit@1"] == 0 and s["evidence_recall@3"] == 1.0
    assert 0 < s["ndcg@3"] < 1 and s["provenance@3"] == 1.0


# ---------------- citations ----------------
def test_numeric_citation_support():
    retrieved = {"c1": "Net income $ 31,778 $ 25,824 (In millions)", "c2": "Revenue increased $12.8 billion or 18%"}
    claims = [{"text": "Net income was $31.8 billion.", "cites": ["c1"]},
              {"text": "Revenue grew 18%.", "cites": ["c2"]},
              {"text": "Revenue grew 22%.", "cites": ["c2"]},
              {"text": "Margins rose.", "cites": ["c9"]}]
    s = score_citations(claims, retrieved)
    assert s["numeric_support"] == pytest.approx(2 / 3)
    assert s["citation_validity"] == pytest.approx(3 / 4)


# ---------------- graph ----------------
def test_graph_metrics():
    gold = [{"cik": "1", "concept": "c", "start": "2025-01-01", "end": "2025-12-31", "value": 100},
            {"cik": "1", "concept": "c", "start": "2024-01-01", "end": "2024-12-31", "value": 90}]
    pred = [{"cik": "1", "concept": "c", "start": "2025-01-01", "end": "2025-12-31", "value": 100},
            {"cik": "1", "concept": "c", "start": "2024-01-01", "end": "2024-12-31", "value": 95},
            {"cik": "1", "concept": "x", "start": "2024-01-01", "end": "2024-12-31", "value": 1}]
    s = score_fact_extraction(pred, gold)
    assert s["tp"] == 1 and s["key_recall"] == 1.0 and s["value_accuracy"] == 0.5
    e = score_edges([("1", "FILED", "A"), ("1", "FILED", "B")], [("1", "FILED", "A")])
    assert e["precision"] == 0.5 and e["recall"] == 1.0
    assert entity_linking_accuracy([("Citi", "831001"), ("JPM", None)], {"Citi": "0000831001", "JPM": "19617"})["accuracy"] == 0.5
    assert path_recall({("1", "FILED", "A")}, [("1", "FILED", "A"), ("A", "REPORTS", "f")]) == 0.5


# ---------------- consistency / ops / stats ----------------
def test_consistency_and_ops():
    r = run_to_run_consistency({"q1": ["$5.0 billion", "$5.0 billion"], "q2": ["$5.0 billion", "Not disclosed."]})
    assert r["rrc"] == 0.5 and r["inconsistent_qids"] == ["q2"]
    o = ops_metrics([{"trace_id": "t1", "tool": "retrieve", "latency_ms": 100, "status": "ok", "cost_usd": 0.01},
                     {"trace_id": "t1", "tool": "llm", "latency_ms": 900, "status": "ok", "cost_usd": 0.02},
                     {"trace_id": "t2", "tool": "retrieve", "latency_ms": 300, "status": "timeout", "cost_usd": 0.0}])
    assert o["n_queries"] == 2 and o["tool_call_error_rate"] == pytest.approx(1 / 3)
    assert o["cost_per_query_usd"] == pytest.approx(0.015)


def test_stats():
    lo, hi = wilson(18, 20)
    assert lo < 0.9 < hi
    d = paired_bootstrap_diff([1, 1, 1, 0] * 5, [1, 0, 0, 0] * 5)
    assert d["mean_diff"] == 0.5 and d["ci95"][0] > 0
