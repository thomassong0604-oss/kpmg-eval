"""Week 6: provenance-key joins, three-field version keys, whitespace-normalised anchors, relationship draft."""
import csv
import json
from pathlib import Path

from kpmg_eval.keys import (as_provenance, comparable_runs, norm_ws, provenance_key, version_key,
                            versions_seen)
from kpmg_eval.metrics.citation import score_citations
from kpmg_eval.metrics.retrieval import evidence_satisfied, graph_adapter
from kpmg_eval.keys import EvalKey

DATA = Path(__file__).resolve().parent.parent / "data"

RAG_CHUNK = {"chunk_id": "MSFT-0001193125-26-191507-0025", "section_id": None, "metadata": {},
             "text": "Revenue was $82,886 million.", "index_version": "abc", "chunking_version": "paragraph-v1"}
GRAPH_SECTION = {"chunk_id": None, "section_id": "sec-msft-26q3-note16", "metadata": {"trace_id": "q1"},
                 "text": "More Personal Computing revenue was $13,150 million.", "extraction_version": "x1",
                 "cik": "0000789019", "accession_number": "0001193125-26-191507", "section": "Part I Item 1"}
STRUCT_FACT = {"chunk_id": None, "section_id": None, "metadata": {"fact_id": "msft-rev-q3fy26", "extraction_version": "x1"},
               "text": "us-gaap:Revenue 82886000000"}


def test_provenance_key_takes_whichever_is_set():
    assert provenance_key(RAG_CHUNK) == "chunk:MSFT-0001193125-26-191507-0025"
    assert provenance_key(GRAPH_SECTION) == "section:sec-msft-26q3-note16"
    assert provenance_key(STRUCT_FACT) == "fact:msft-rev-q3fy26"
    assert provenance_key({"chunk_id": None}) is None


def test_bare_rag_ids_still_join():
    assert as_provenance("MSFT-1") == "chunk:MSFT-1"
    assert as_provenance("section:s1") == "section:s1"


def test_graph_only_answer_is_scored_not_uncited():
    """GraphRAG eval-reply §2: an answer built entirely on graph evidence must be scored, not treated as uncited."""
    seen = {provenance_key(c): c["text"] for c in (GRAPH_SECTION, STRUCT_FACT)}
    claims = [{"text": "More Personal Computing revenue was $13,150 million", "cites": ["section:sec-msft-26q3-note16"]}]
    sc = score_citations(claims, seen)
    assert sc["citation_validity"] == 1.0 and sc["numeric_support"] == 1.0
    # the old chunk_id join would have found nothing: every graph result has chunk_id None
    assert score_citations(claims, {None: GRAPH_SECTION["text"]})["citation_validity"] == 0.0


def test_rag_citations_unchanged():
    seen = {provenance_key(RAG_CHUNK): RAG_CHUNK["text"]}
    sc = score_citations([{"text": "Revenue was $82,886 million", "cites": [RAG_CHUNK["chunk_id"]]}], seen)
    assert sc["citation_validity"] == 1.0 and sc["numeric_support"] == 1.0


def test_version_key_reads_all_three_fields():
    assert version_key(RAG_CHUNK) == ("abc", "paragraph-v1", None)
    assert version_key(STRUCT_FACT) == (None, None, "x1")  # extraction_version in metadata
    assert versions_seen([RAG_CHUNK, GRAPH_SECTION])["extraction_version"] == ["x1", None]


def test_graph_rebuild_breaks_comparability_even_with_same_index_version():
    a = {"benchmark_sha256": "h", "index_version": "i", "chunking_version": None, "extraction_version": "x1"}
    b = {**a, "extraction_version": "x2"}
    assert comparable_runs(a, a) == (True, [])
    assert comparable_runs(a, b) == (False, ["extraction_version"])


def test_contains_is_whitespace_normalised():
    ev = {"cik": "0000789019", "contains": ["primarily relate to the dilution gain"]}
    key = EvalKey(cik="0000789019")
    assert evidence_satisfied(ev, key, "primarily relate  to the\n dilution   gain")
    assert norm_ws("  a \n\t b ") == "a b"


def test_graph_adapter_reads_rag_field_names():
    (key, _), = graph_adapter([GRAPH_SECTION])
    assert key.accession == "0001193125-26-191507" and key.cik == "0000789019"


def test_relationship_draft_is_well_formed_and_separate_from_v1():
    v1 = [json.loads(l) for l in open(DATA / "benchmark_v1.jsonl")]
    draft = [json.loads(l) for l in open(DATA / "benchmark_v1_relationship_draft.jsonl")]
    assert len(v1) == 100  # frozen set untouched
    assert {q["qid"] for q in v1}.isdisjoint({q["qid"] for q in draft})
    assert {q["graphrag_shape"] for q in draft} == {"M01", "M04", "M09", "M14", "M17"}
    assert sum(q["type"] in ("fabricated_relationship", "false_premise") for q in draft) == 2  # M14 + a variant
    for q in draft:
        eval_item = next(x for x in v1 if x["source"] == "eval_v1")
        assert set(eval_item) <= set(q), q["qid"]  # same fields as Eval's v1 items (plus hops, graphrag_shape)
        assert q["hops"] is None  # GraphRAG proposes, Eval reviews
        assert all(e["contains"] for e in q["rag_evidence"])


def test_hops_sidecar_covers_every_question():
    import csv
    rows = list(csv.DictReader(open(DATA / "hops_v1.csv")))
    v1 = {json.loads(l)["qid"] for l in open(DATA / "benchmark_v1.jsonl")}
    draft = {json.loads(l)["qid"] for l in open(DATA / "benchmark_v1_relationship_draft.jsonl")}
    v2 = {json.loads(l)["qid"] for l in open(DATA / "benchmark_scope10_new.jsonl")}
    assert v1 | draft | v2 <= {r["qid"] for r in rows}  # Week 7 adds EV3


# ---------------- Week 6 (10/29): GraphRAG wiring, XBRL dimensions, 10-company scope ----------------
from kpmg_eval.graphrag_adapter import GraphRAGRetriever, adapter, contract_checks, evidence_key, fixture_tools  # noqa: E402
from kpmg_eval.keys import Level, matches  # noqa: E402
from kpmg_eval.metrics.retrieval import score_retrieval  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "graphrag_int0_mock_evidence.json"
TOTAL_REV_GOLD = {"cik": "0000789019", "accession": "0001193125-26-191507",
                  "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                  "period_start": "2026-01-01", "period_end": "2026-03-31", "unit": "USD", "level": "FACT"}


def test_segment_fact_does_not_satisfy_total_gold():
    gs, ss = fixture_tools(FIX)
    rows = ss("Intelligent Cloud revenue three months", {"ticker": "MSFT"}, 10, "q")
    ic = [r for r in rows if r["metadata"]["dimensions"]][0]
    k = evidence_key(ic)
    assert k.dims == (("statementbusinesssegments", "intelligentcloud"),)
    assert not matches(k, EvalKey(**{x: y for x, y in TOTAL_REV_GOLD.items() if x != "level"}), Level.FACT)
    seg_gold = {**TOTAL_REV_GOLD, "dims": {"us-gaap:StatementBusinessSegmentsAxis": "msft:IntelligentCloudMember"}}
    assert matches(k, EvalKey(**{x: y for x, y in seg_gold.items() if x != "level"}), Level.FACT)  # label == QName


def test_structured_arm_scores_at_fact_level():
    gs, ss = fixture_tools(FIX)
    rows = ss("Microsoft total revenue three months ended March 31 2026", {"ticker": "MSFT"}, 10, "GSv0-MSFT-001")
    s = score_retrieval([TOTAL_REV_GOLD], adapter(rows), ks=(1, 10))
    assert s["hit@10"] == 1.0


def test_graphrag_envelope_and_contract_checks():
    gs, ss = fixture_tools(FIX)
    env = GraphRAGRetriever(gs, ss, "both").search("Intelligent Cloud revenue", {"ticker": "MSFT"}, 10, trace_id="t1")
    assert env["results"] and env["extraction_version"] == "mock-v0"
    c = contract_checks(env["results"], "t1")
    assert all(v for k, v in c.items() if k != "n")
    assert {r["metadata"]["arm"] for r in env["results"]} == {"graph", "structured"}
    assert ss("revenue", {"ticker": "AAPL"}, 10, None) == []  # filters honoured


def test_repeated_section_id_keeps_both_texts():
    """Two graph rows share section_id sec-msft-26q3-note16; the harness must not drop one when joining citations."""
    rows = json.loads(FIX.read_text())["graph"]
    keys = [provenance_key(r) for r in rows]
    assert keys.count("section:sec-msft-26q3-note16") == 2


def test_scope10_gold_is_computed_and_verified():
    new = [json.loads(l) for l in open(DATA / "benchmark_scope10_new.jsonl")]
    status = list(csv.DictReader(open(DATA / "benchmark_scope10_status.csv")))
    assert sum(r["status"] == "retired" for r in status) == 10
    assert all(set(r["tickers"].split()) & {"AMZN", "META", "NVDA"} for r in status if r["status"] == "retired")
    assert {t for q in new for t in q["tickers"]} == {"AAPL", "CASY", "MCK", "MDT", "MSFT", "MU", "NKE", "NTAP", "PH", "TTWO"}
    checks = json.load(open(DATA.parent / "results" / "scope10_checks.json"))
    assert not checks["disagree"] and all(x["holds"] for x in checks["quarter_sums"])
    facts = {f["fact_id"]: f for f in map(json.loads, open(DATA / "scope10_facts.jsonl"))}
    for q in new:  # every numeric answer equals a fact or a computation over the question's own facts
        if q["answer_type"] == "exact_numeric" and q["type"] == "extraction":
            assert q["answer"]["value"] in {facts[fid]["value"] for fid in q["fact_values"]}


def test_scope10_numeric_grader_check_is_clean():
    r = json.load(open(DATA.parent / "results" / "scope10_grader_check.json"))
    assert r["graded"] == 4 * r["numeric_items"] and not r["mismatches"]
