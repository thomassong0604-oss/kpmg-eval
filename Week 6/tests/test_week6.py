"""Week 6: provenance-key joins, three-field version keys, whitespace-normalised anchors, relationship draft."""
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
    assert {r["qid"] for r in rows} == v1 | draft
