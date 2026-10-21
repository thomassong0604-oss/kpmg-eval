"""What Eval asks the Agent team to return with every answer (proposal for Contract v0 sign-off).

Why: in our grader stress test, pattern-matching free-text answers agreed with human judgment on
2 of 10 realistic phrasings. Scoring these fields instead is exact and needs no LLM judge.
"""
from __future__ import annotations

ANSWER_BLOCK_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AnswerBlock",
    "type": "object",
    "required": ["trace_id", "answered", "answer_text", "citations"],
    "properties": {
        "trace_id": {"type": "string", "description": "Same id passed to retrieve(trace_id=...) and written to every log line"},
        "qid": {"type": ["string", "null"], "description": "Benchmark question id when run by the eval harness"},
        "answered": {"type": "boolean", "description": "false = the agent declined because evidence was insufficient"},
        "answer_text": {"type": "string"},
        "value": {"type": ["number", "null"], "description": "Headline number in base units (dollars, not millions)"},
        "value_text": {"type": ["string", "null"], "description": "The number exactly as shown to the user, e.g. '$21.2 billion'"},
        "unit": {"enum": ["USD", "USD/shares", "%", "pp", "count", None]},
        "period_start": {"type": ["string", "null"], "format": "date"},
        "period_end": {"type": ["string", "null"], "format": "date"},
        "entity_cik": {"type": ["string", "null"], "pattern": "^[0-9]{10}$"},
        "concept": {"type": ["string", "null"], "description": "XBRL concept if the value came from a fact, e.g. us-gaap:NetIncomeLoss"},
        "citations": {
            "type": "array",
            "items": {"type": "object", "required": ["id", "source"],
                      "properties": {"id": {"type": "string", "description": "chunk_id (RAG) or node id (GraphRAG)"},
                                     "source": {"enum": ["vector_rag", "graph_rag", "xbrl_tool"]},
                                     "accession": {"type": "string"}, "section": {"type": "string"}}},
        },
        "claims": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}}}},
    },
}

TRACE_FIELDS = ["trace_id", "timestamp_utc", "tool", "status", "latency_ms", "prompt_tokens",
                "completion_tokens", "cost_usd", "request_id", "retry_of"]


def validate_answer_block(b: dict) -> list[str]:
    """Light validation without a jsonschema dependency; returns a list of problems (empty = ok)."""
    errs = [f"missing {k}" for k in ANSWER_BLOCK_SCHEMA["required"] if k not in b]
    if b.get("answered") and b.get("value") is None and b.get("unit") not in (None, "count"):
        errs.append("answered numeric question without value")
    if b.get("answered") is False and b.get("value") is not None:
        errs.append("declined but still reports a value (hedged answer)")
    if b.get("entity_cik") and not (len(b["entity_cik"]) == 10 and b["entity_cik"].isdigit()):
        errs.append("entity_cik must be 10 digits")
    for c in b.get("citations", []):
        if c.get("source") not in ("vector_rag", "graph_rag", "xbrl_tool"):
            errs.append(f"bad citation source {c.get('source')!r}")
    return errs
