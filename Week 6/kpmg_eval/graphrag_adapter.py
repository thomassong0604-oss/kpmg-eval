"""Week 6: GraphRAG's two retrieval arms in the Eval harness.

GraphRAG's tools (graphrag/retrieve.py, final signatures; mock in mock/mock_retrieval_tools.py):

    graph_search(query, filters=None, top_k=10, trace_id=None)       -> evidence citing section_id   (chunk_id None)
    structured_search(query, filters=None, top_k=10, trace_id=None)  -> evidence citing metadata.fact_id

This module turns either arm's evidence into Eval keys, so the retrieval metrics score both arms with the same gold:
  graph arm       -> section-level key (cik, accession_number, section), judged with `contains` text
  structured arm  -> fact-level key (cik, accession, concept, period, unit, XBRL dimensions)
and wraps the tools in the `search()` envelope the harness logs (request_id, index/extraction version, results).
"""
from __future__ import annotations

import copy
import importlib
import json
import re
import sys
import time
import uuid
from pathlib import Path

from .keys import EvalKey, provenance_key


def load_tools(repo: Path, mock: bool = True):
    """(graph_search, structured_search) from a GraphRAG checkout. mock=False uses graphrag.retrieve, which raises
    RetrievalUnavailableError until a backend is registered (by design: it never falls back to the mock)."""
    repo = Path(repo)
    for p in (repo, repo / "mock"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    mod = importlib.import_module("mock_retrieval_tools" if mock else "graphrag.retrieve")
    return mod.graph_search, mod.structured_search


def fixture_tools(path: Path):
    """(graph_search, structured_search) over a JSON file of evidence rows (tests/fixtures/graphrag_int0_mock_evidence.json).
    Eval's stand-in: same signatures, filters on filing fields, keyword-overlap score, trace echo. It does not run
    GraphRAG's code; use load_tools() for that."""
    rows = json.loads(Path(path).read_text())
    tok = lambda t: set(re.findall(r"[a-z0-9]+", t.lower()))  # noqa: E731

    def make(arm):
        def search(query, filters=None, top_k=10, trace_id=None):
            out = []
            for r in rows[arm]:
                ok = True
                for k, want in (filters or {}).items():
                    if k in ("ticker", "cik", "form", "accession_number"):
                        wl = want if isinstance(want, list) else [want]
                        ok &= str(r.get(k)).lower() in {str(w).lower() for w in wl}
                if not ok:
                    continue
                q = tok(query)
                score = round(len(q & tok(r["text"] + " " + r["metadata"].get("section_title", ""))) / len(q), 6) if q else 0
                if score > 0:
                    x = copy.deepcopy(r)
                    x["score"], x["metadata"]["trace_id"] = score, trace_id
                    out.append(x)
            out.sort(key=lambda r: (-r["score"], provenance_key(r) or ""))
            for i, r in enumerate(out[:top_k], 1):
                r["rank"] = i
            return out[:top_k]
        return search
    return make("graph"), make("structured")


def _unit(meta: dict) -> str | None:
    u = meta.get("unit") or meta.get("unit_ref")
    return str(u).split(":")[-1] if u else None


def evidence_key(item: dict) -> EvalKey:
    """One GraphRAG evidence object -> EvalKey at the finest level it supports."""
    meta = item.get("metadata") or {}
    if meta.get("fact_id"):
        return EvalKey(cik=item.get("cik"), accession=item.get("accession_number"), section=item.get("section"),
                       concept=meta.get("concept"), period_start=meta.get("period_start"),
                       period_end=meta.get("period_end"), unit=_unit(meta), ticker=item.get("ticker"),
                       dims=meta.get("dimensions") or None)
    return EvalKey.from_rag_chunk(item)


def adapter(results: list[dict]) -> list[tuple[EvalKey, str]]:
    """GraphRAG evidence -> [(key, text)] for metrics.retrieval.score_retrieval."""
    return [(evidence_key(r), r.get("text") or "") for r in results]


class GraphRAGRetriever:
    """Harness-facing wrapper. `arm` is "graph", "structured" or "both" (graph results first, then structured)."""

    def __init__(self, graph_search, structured_search, arm: str = "both", label: str = "graphrag-mock"):
        if arm not in ("graph", "structured", "both"):
            raise ValueError("arm must be graph, structured or both")
        self.g, self.s, self.arm = graph_search, structured_search, arm
        self.meta = {"index_version": label, "embedder": None}

    def search(self, query: str, filters: dict | None = None, top_k: int = 10, method: str | None = None,
               trace_id: str | None = None) -> dict:
        t0 = time.perf_counter()
        results, warnings = [], []
        for name, fn in (("graph", self.g), ("structured", self.s)):
            if self.arm in (name, "both"):
                for r in fn(query, filters=filters, top_k=top_k, trace_id=trace_id):
                    results.append({**r, "metadata": {**(r.get("metadata") or {}), "arm": name}})
        if not results:
            warnings.append("no evidence from either arm")
        versions = sorted({str(r.get("extraction_version")) for r in results})
        return {"request_id": uuid.uuid4().hex, "trace_id": trace_id, "index_version": self.meta["index_version"],
                "extraction_version": versions[0] if len(versions) == 1 else versions,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "warnings": warnings, "results": results}


def contract_checks(results: list[dict], trace_id: str | None) -> dict:
    """What Eval needs from every evidence object, checked per call."""
    return {
        "n": len(results),
        "trace_id_echoed": all((r.get("metadata") or {}).get("trace_id") == trace_id for r in results),
        "one_provenance_key": all(sum(bool(x) for x in (r.get("chunk_id"), r.get("section_id"),
                                                        (r.get("metadata") or {}).get("fact_id"))) == 1 for r in results),
        "provenance_resolves": all(provenance_key(r) for r in results),
        "has_extraction_version": all(r.get("extraction_version") for r in results),
        "fact_has_period_and_concept": all(
            (r.get("metadata") or {}).get(k) for r in results if (r.get("metadata") or {}).get("fact_id")
            for k in ("concept", "period_end")),
    }
