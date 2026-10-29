"""Shared evaluation key (Week 6: + provenance key and version key, agreed with GraphRAG 10/26): one identifier scheme that RAG, GraphRAG, Agents and Eval all resolve to.

GraphRAG's schema (10/8 deck, "Schema decisions") stores six entity types:
Company (CIK) -> Filing (accession) -> Section -> Fact (concept, period, unit), plus Segment and Subsidiary.
RAG's retrieve() contract v0 (PR #3) returns chunks carrying cik, accession_number, section,
fiscal_year, fiscal_period. Eval gold items are written against the same fields, so a single
benchmark scores both retrieval arms and the agent without per-team translation.

Matching levels (coarse -> fine). A gold item declares the level it needs:
  COMPANY  cik
  FILING   cik + accession
  SECTION  cik + accession + section (word-prefix match, "Item 7" matches "Item 7 MD&A")
  FACT     cik + concept + period_start + period_end + unit (accession optional: the same fact
           is re-reported in later filings, e.g. prior-year columns, and either copy is valid evidence)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class Level(IntEnum):
    COMPANY = 1
    FILING = 2
    SECTION = 3
    FACT = 4


def norm_cik(v: Any) -> str | None:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if not s.isdigit():
        raise ValueError(f"CIK must be digits, got {v!r}")
    return s.zfill(10)


def norm_accession(v: Any) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    if s.isdigit() and len(s) == 18:
        s = f"{s[:10]}-{s[10:12]}-{s[12:]}"
    return s


def norm_section(v: Any) -> str | None:
    if not v:
        return None
    return " ".join(str(v).upper().replace(".", " ").split())


def _dim_token(v: Any) -> str:
    """'msft:IntelligentCloudMember', 'Intelligent Cloud', 'us-gaap:StatementBusinessSegmentsAxis' -> comparable token."""
    s = str(v).split(":")[-1]
    for suffix in ("Member", "Axis"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return "".join(ch for ch in s.lower() if ch.isalnum())


def norm_dims(v: Any) -> tuple:
    """dict or tuple of (axis, member) -> sorted tuple of normalised tokens; None/{} -> () (consolidated total).
    GraphRAG's structured arm reports members as labels ("Intelligent Cloud"); gold uses XBRL QNames."""
    if not v:
        return ()
    items = v.items() if isinstance(v, dict) else v
    return tuple(sorted((_dim_token(a), _dim_token(m)) for a, m in items))


@dataclass(frozen=True)
class EvalKey:
    cik: str | None = None
    accession: str | None = None
    section: str | None = None
    concept: str | None = None          # XBRL concept, e.g. us-gaap:NetIncomeLoss
    period_start: str | None = None     # YYYY-MM-DD (None for instant facts)
    period_end: str | None = None
    unit: str | None = None             # USD, USD/shares, pure
    ticker: str | None = field(default=None, compare=False)  # display only; CIK is the identity
    # Week 6: XBRL axis -> member for segment/product facts. Without it, at FACT level "Intelligent Cloud revenue"
    # matched the gold "total revenue" (same concept and period): a false hit for any arm returning segment facts.
    dims: tuple | None = None

    def __post_init__(self):
        object.__setattr__(self, "dims", norm_dims(self.dims))
        object.__setattr__(self, "cik", norm_cik(self.cik))
        object.__setattr__(self, "accession", norm_accession(self.accession))
        object.__setattr__(self, "section", norm_section(self.section))

    @property
    def level(self) -> Level:
        if self.concept:
            return Level.FACT
        if self.section:
            return Level.SECTION
        if self.accession:
            return Level.FILING
        return Level.COMPANY

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None and v != ()}

    # ---------------- constructors from each team's format ----------------
    @classmethod
    def from_rag_chunk(cls, chunk: dict) -> "EvalKey":
        """RAG retrieve() contract v0 RetrievedChunk -> key (filing/section level)."""
        return cls(cik=chunk.get("cik"), accession=chunk.get("accession_number"),
                   section=chunk.get("section"), ticker=chunk.get("ticker"))

    @classmethod
    def from_graph_fact(cls, node: dict) -> "EvalKey":
        """GraphRAG Fact node (properties per the 10/8 schema) -> key (fact level)."""
        return cls(cik=node.get("cik"), accession=node.get("accession"), section=node.get("section"),
                   concept=node.get("concept"), period_start=node.get("period_start"),
                   period_end=node.get("period_end"), unit=node.get("unit"), ticker=node.get("ticker"),
                   dims=node.get("dims") or node.get("dimensions"))

    @classmethod
    def from_xbrl_fact(cls, cik: str, concept: str, fact: dict, unit: str = "USD", ticker: str | None = None) -> "EvalKey":
        """One row of the SEC companyconcept API -> key."""
        return cls(cik=cik, accession=fact.get("accn"), concept=concept, period_start=fact.get("start"),
                   period_end=fact.get("end"), unit=unit, ticker=ticker)


def _section_match(have: str | None, want: str | None) -> bool:
    if want is None:
        return True
    if have is None:
        return False
    return have == want or have.startswith(want + " ")


def matches(candidate: EvalKey, gold: EvalKey, level: Level | None = None) -> bool:
    """Does `candidate` (what a system retrieved/cited) satisfy `gold` at the given level?"""
    level = level or gold.level
    if gold.cik and candidate.cik != gold.cik:
        return False
    if level >= Level.FILING and level != Level.FACT and gold.accession and candidate.accession != gold.accession:
        return False
    if level >= Level.SECTION and level != Level.FACT and not _section_match(candidate.section, gold.section):
        return False
    if level == Level.FACT:
        for attr in ("concept", "period_start", "period_end", "unit"):
            g = getattr(gold, attr)
            if g is not None and getattr(candidate, attr) != g:
                return False
        if candidate.dims != gold.dims:  # Week 6: segment fact != consolidated total
            return False
    return True


# ---------------- Week 6: provenance key and version key ----------------
# GraphRAG (eval-reply.md §2): their evidence never carries chunk_id. Each result sets exactly one of
# chunk_id (RAG), section_id (graph arm) or metadata.fact_id (structured arm). Every Eval join that used
# chunk_id (citation validity, "was this cited chunk actually retrieved", log joins) now uses this key, so a
# graph-only answer is scored instead of looking uncited.
PROVENANCE_FIELDS = ("chunk_id", "section_id", "fact_id")


def provenance_key(item: dict) -> str | None:
    """chunk_id, else section_id, else metadata.fact_id. Prefixed so ids from different arms never collide."""
    meta = item.get("metadata") or {}
    for field_name, value in (("chunk", item.get("chunk_id")), ("section", item.get("section_id")),
                              ("fact", item.get("fact_id") or meta.get("fact_id"))):
        if value not in (None, ""):
            return f"{field_name}:{value}"
    return None


def as_provenance(cite_id: str | None) -> str | None:
    """A citation id from an AnswerBlock, normalised to the same prefixed form. Accepts an already-prefixed id or a
    bare RAG chunk_id (the AnswerBlock spec predates the prefix, and RAG ids are the only bare ones in use)."""
    if not cite_id:
        return None
    s = str(cite_id)
    return s if s.split(":", 1)[0] in ("chunk", "section", "fact") else f"chunk:{s}"


# GraphRAG (eval-reply.md §3): their rebuilds move extraction_version, not index_version. A rerun is only
# comparable to an earlier run when all three match; keying on index_version alone hides graph rebuilds.
VERSION_FIELDS = ("index_version", "chunking_version", "extraction_version")


def version_key(item: dict) -> tuple:
    """The three version fields of one evidence item (top level or metadata); missing -> None."""
    meta = item.get("metadata") or {}
    return tuple(item.get(f, meta.get(f)) for f in VERSION_FIELDS)


def versions_seen(results: list[dict]) -> dict[str, list]:
    """Distinct values of each version field across a run's retrieved evidence, for the scorecard header."""
    out: dict[str, set] = {f: set() for f in VERSION_FIELDS}
    for r in results:
        for f, v in zip(VERSION_FIELDS, version_key(r)):
            out[f].add(v)
    return {f: sorted(v, key=lambda x: (x is None, str(x))) for f, v in out.items()}


def comparable_runs(a: dict, b: dict) -> tuple[bool, list[str]]:
    """Two scorecards' `versions` blocks -> (comparable, fields that differ). Uses all three version fields plus the
    benchmark hash; a field absent from both runs does not block comparison."""
    diffs = [f for f in ("benchmark_sha256",) + VERSION_FIELDS if a.get(f) != b.get(f)]
    return (not diffs, diffs)


def norm_ws(text: str) -> str:
    """Collapse whitespace runs and trim (GraphRAG eval-ask §Format 3): gold quotes collapse whitespace, rendered
    HTML does not, so `contains` must normalise both sides or exact matches fail for cosmetic reasons."""
    return " ".join(str(text).split())
