"""Shared evaluation key: one identifier scheme that RAG, GraphRAG, Agents and Eval all resolve to.

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

    def __post_init__(self):
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
        return {k: v for k, v in asdict(self).items() if v is not None}

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
                   period_end=node.get("period_end"), unit=node.get("unit"), ticker=node.get("ticker"))

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
    return True
