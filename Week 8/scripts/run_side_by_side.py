"""Week 8: RAG and GraphRAG side by side on one full question set (11/5 minutes, Eval item 1).

    python scripts/run_side_by_side.py   -> results/side_by_side.json, results/side_by_side_per_question.csv

Part A: the Microsoft Q3 FY2026 10-Q question set (all 84 Gold Set v2 questions on that filing). It is the one filing
both teams' code can load here without a network or a database server. Each system runs its own code on the same filing:
  RAG       KPMG_RAG @ 5bfafeb (main, 11/5): rag.chunk.chunk_filing (158 chunks) -> rag.index.build_index ->
            Retriever.search, filters = the question's filters, top 8. "bm25" is RAG's production BM25 exactly. RAG's
            dense model cannot be downloaded here, so "hybrid" uses RAG's own offline LSA stand-in (a lower bound).
  GraphRAG  KPMG-GraphRAG @ 4e89acb (main, 11/11), called through graphrag.backends as their README says:
            structured/fact_loader_v1.py builds the DuckDB fact store from Data's copy of the same filing (1,317 facts),
            then structured_query_v1.structured_search(question, {ticker, accession_number}, top_k=8). This is
            GraphRAG's structured arm. Its graph arm needs Neo4j, which is not reachable from here.
Scored at the evidence level (no reader model, so nothing depends on an LLM):
  needed_in_evidence   numbers: every input number of the gold answer is in the top 8 (RAG: the figure as printed,
                       e.g. "82,886"; GraphRAG: a returned fact has that value). Prose: every gold text anchor is in
                       the top 8 (same check for both; GraphRAG's structured evidence is "concept: value" text).
  distractor_shown     a known wrong-period number for the same line item is also in the top 8 (the reader can pick it)
  returned_nothing     the system returned no evidence (GraphRAG's contract allows an empty list)

Part B: the relationship (traversal) questions, all built on Exhibit 21. RAG indexes each filing's main report
(rag/ingest.py reads `primaryDocument`; its round-1 corpus is Data's report chunks, and Data archives Exhibit 21 files
without chunking them, docs/shortlist-acquisition.md), so RAG's index cannot hold these answers today. GraphRAG's own
Exhibit 21 pipeline (branch alina/ex21-pipeline @ c21fe89, output/graph_edges.csv) gives Parent -HAS_SUBSIDIARY->
Subsidiary rows for all ten companies. Part B loads those rows in memory, answers each question by traversal (Neo4j is
not reachable here), and, for comparison, adds the same rows to RAG's index as text through RAG's own chunker and
checks whether BM25's top 8 holds every row the answer needs. It also checks GraphRAG's rows against Eval's own gold
reads (data/sec_reads/exhibit21_2026-11-05.json), row by row.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
UP = ROOT / "upstream"
DATA, RES = ROOT / "data", ROOT / "results"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(UP / "KPMG_RAG"))
sys.path.insert(0, str(UP / "KPMG-GraphRAG" / "structured"))

ACC = "0001193125-26-191507"
CORPUS = "msft_10q_q3fy26"
K = 8
STORE = UP / "graphrag_store_msft_10q.duckdb"
HTM = UP / "data_engineering_kpmg" / "data" / "raw" / "sec" / ACC / "msft-20260331.htm"
COMMITS = {"KPMG_RAG": "5bfafeb (main, 11/5)", "KPMG-GraphRAG": "4e89acb (main, 11/11; called through graphrag.backends)",
           "KPMG-GraphRAG ex21": "c21fe89 (alina/ex21-pipeline, 11/8)", "data_engineering_kpmg": "f8d18e2"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("—", "-")).lower()


def mm(v: float) -> str:
    return f"{abs(v) / 1e6:,.0f}"


def figures(q: dict) -> list[str]:
    """Input numbers as printed in the filing: USD millions with commas, per-share to cents, ratios as percent."""
    a = q["answer"]
    if q["type"] in ("extraction", "segment") and len(q["facts"]) == 1 and a.get("required_points"):
        # the digits as printed: statements show negatives in parentheses, so "-84,669" is matched as "84,669"
        return [re.sub(r"[^0-9.,%]", "", a["required_points"][0]).strip(".,")]
    out = []
    for k, v in zip(q["facts"], q["fact_values"].values()):
        if k["unit"] == "USD":
            out.append(mm(v))
        elif k["unit"] == "USD/shares":
            out.append(f"{v:.2f}")
        elif k["unit"] == "pure":
            out.append(f"{v * 100:.0f}%")
        else:
            out.append(f"{v:,.0f}")
    return out


def needed_values(q: dict) -> list[float]:
    return [float(v) for v in q["fact_values"].values()]


def kind(q: dict) -> str:
    if not q["answerable"] or q["answer_type"] in ("refusal", "false_premise"):
        return "unanswerable_or_false_premise"
    return "number" if q["answer_type"] == "exact_numeric" else "prose"


# ---------------------------------------------------------------- Part A
def build_rag(chunks: Path, index_dir: Path):
    from rag.index import build_index
    from rag.retrieve import Retriever
    if index_dir.exists():
        shutil.rmtree(index_dir)
    build_index(chunks, index_dir, "lsa")
    return Retriever(index_dir, log_dir=None)


def rag_run(retr, q, method):
    t = time.perf_counter()
    res = retr.search(q["question"], filters=q["filters"], top_k=K, method=method)["results"]
    ms = (time.perf_counter() - t) * 1000
    return [r["text"] for r in res], ms


def gr_structured(top_k=K):
    """GraphRAG's real structured arm the way their README says to call it (11/10): `graphrag.backends`, which runs
    contract validation, ranking and the conformance check around structured_query_v1. Filters: the question's one
    filing as {ticker, accession_number}, which the arm applies (see kpmg_eval/graphrag_filters.py)."""
    from kpmg_eval.graphrag_adapter import load_tools
    _, structured = load_tools(UP / "KPMG-GraphRAG", mock=False)
    return lambda q: structured(q["question"], filters={"ticker": "MSFT", "accession_number": ACC}, top_k=top_k,
                                trace_id=f"sbs:{q['qid']}")


def gr_run(q):
    t = time.perf_counter()
    ev = gr_structured()(q)
    ms = (time.perf_counter() - t) * 1000
    return ev, ms


def score_rag(q, texts):
    blob = norm(" ".join(texts))
    k = kind(q)
    out = {"n_returned": len(texts)}
    if k == "number":
        out["needed_in_evidence"] = all(norm(f) in blob for f in figures(q))
        ds = [d["value"] for d in (q.get("gold") or {}).get("distractors", []) if d.get("value")]
        out["distractor_shown"] = any(mm(d) in blob for d in ds) if ds else None
    elif k == "prose":
        anchors = [c for e in q["rag_evidence"] for c in e["contains"]]
        out["needed_in_evidence"] = all(norm(a) in blob for a in anchors) if anchors else None
    return out


def score_gr(q, ev):
    k = kind(q)
    vals = [e["metadata"]["value_num"] for e in ev if e["metadata"].get("value_num") is not None]
    out = {"n_returned": len(ev)}
    if k == "number":
        out["needed_in_evidence"] = all(any(abs(abs(v) - abs(n)) < 0.5 or (abs(n) < 100 and abs(v - n) < 0.005)
                                            for v in vals) for n in needed_values(q))
        ds = [d["value"] for d in (q.get("gold") or {}).get("distractors", []) if d.get("value")]
        out["distractor_shown"] = any(any(abs(v - d) < 0.5 for v in vals) for d in ds) if ds else None
        top = ev[0]["metadata"].get("value_num") if ev else None
        out["top1_right"] = top is not None and any(abs(top - n) < 0.5 for n in needed_values(q))
        out["top1_wrong_period"] = (top is not None and any(abs(top - d) < 0.5 for d in ds)) if ds else None
    elif k == "prose":
        anchors = [c for e in q["rag_evidence"] for c in e["contains"]]
        blob = norm(" ".join(e["text"] for e in ev))
        out["needed_in_evidence"] = all(norm(a) in blob for a in anchors) if anchors else None
    return out


PERIOD_WORDS = {"three", "six", "nine", "twelve", "months", "quarter"}


def rate(rows, key):
    xs = [r[key] for r in rows if r.get(key) is not None]
    return {"rate": round(sum(xs) / len(xs), 3) if xs else None, "n": len(xs), "hits": sum(xs)}


def part_a(gold):
    qs = [q for q in gold if q["corpus"] == CORPUS]
    retr = build_rag(DATA / "rag_chunks_msft_10q.jsonl", UP / "rag_index_w8")
    os.environ["MSFT_FACT_DB_PATH"] = str(STORE)
    rows = []
    for q in qs:
        base = {"qid": q["qid"], "kind": kind(q), "type": q["type"], "route_expected": q["route_expected"],
                "traps": " ".join(q.get("traps") or []), "question": q["question"]}
        for method in ("bm25", "hybrid"):
            texts, ms = rag_run(retr, q, method)
            rows.append({**base, "system": f"rag_{method}", **score_rag(q, texts), "ms": round(ms, 1)})
        ev, ms = gr_run(q)
        top = ev[0]["text"] if ev else ""
        rows.append({**base, "system": "graphrag_structured", **score_gr(q, ev), "ms": round(ms, 1), "top1": top})
    systems = ("rag_bm25", "rag_hybrid", "graphrag_structured")
    summ = {}
    for s in systems:
        rs = [r for r in rows if r["system"] == s]
        summ[s] = {
            "needed_in_evidence_all": rate([r for r in rs if r["kind"] != "unanswerable_or_false_premise"], "needed_in_evidence"),
            "numbers": rate([r for r in rs if r["kind"] == "number"], "needed_in_evidence"),
            "prose": rate([r for r in rs if r["kind"] == "prose"], "needed_in_evidence"),
            "distractor_shown_on_numbers": rate([r for r in rs if r["kind"] == "number"], "distractor_shown"),
            "top1_right_on_numbers": rate([r for r in rs if r["kind"] == "number"], "top1_right"),
            "top1_wrong_period_on_numbers": rate([r for r in rs if r["kind"] == "number"], "top1_wrong_period"),
            "returned_nothing_on_unanswerable": {
                "hits": sum(r["n_returned"] == 0 for r in rs if r["kind"] == "unanswerable_or_false_premise"),
                "n": sum(r["kind"] == "unanswerable_or_false_premise" for r in rs)},
            "returned_nothing_on_answerable": sum(r["n_returned"] == 0 for r in rs if r["kind"] != "unanswerable_or_false_premise"),
            "median_ms": sorted(r["ms"] for r in rs)[len(rs) // 2],
        }
        by_type = defaultdict(list)
        for r in rs:
            if r["kind"] != "unanswerable_or_false_premise":
                by_type[r["type"]].append(r)
        summ[s]["by_question_type"] = {t: rate(v, "needed_in_evidence") for t, v in sorted(by_type.items())}
    # why GraphRAG's structured arm missed a number: ranked below 8, or its question words never reach the concept
    import concept_match
    diag = Counter()
    diag_q = defaultdict(list)
    for q in qs:
        r = next(x for x in rows if x["qid"] == q["qid"] and x["system"] == "graphrag_structured")
        if r["kind"] != "number" or r["needed_in_evidence"]:
            continue
        deep = gr_structured(50)(q)
        found = score_gr(q, deep)["needed_in_evidence"]
        why = ("in_top50_ranked_below_8" if found else
               "multi_input_not_all_in_top50" if len(q["fact_values"]) > 1 else "single_input_not_in_top50")
        diag[why] += 1
        diag_q[why].append(q["qid"])
        if found:
            # which question words lifted the rows above the needed fact? Period words ("three months") match
            # Microsoft's "Microsoft 365" members (msft:MicrosoftThreeSixFive...), which is not what the user asked
            terms = concept_match.question_terms(q["question"])
            filer = concept_match.filer_words("MSFT", "Microsoft Corporation")
            lifted = {t for e in deep[:K] for d in e["metadata"]["dimensions"] for t in terms
                      if t not in filer and concept_match._matches(t, concept_match.concept_words(d.get("member", "")))}
            if lifted & PERIOD_WORDS:
                diag["ranked_below_8_period_word_matches_member"] += 1
                diag_q["ranked_below_8_period_word_matches_member"].append(q["qid"])
    summ["graphrag_structured"]["number_miss_diagnosis"] = {"counts": dict(diag), "qids": dict(diag_q)}
    # head to head on answerable questions
    idx = {(r["qid"], r["system"]): r for r in rows}
    h2h = Counter()
    lists = defaultdict(list)
    for q in qs:
        if kind(q) == "unanswerable_or_false_premise":
            continue
        a, b = idx[(q["qid"], "rag_bm25")].get("needed_in_evidence"), idx[(q["qid"], "graphrag_structured")].get("needed_in_evidence")
        if a is None or b is None:
            continue
        key = {(True, True): "both", (True, False): "rag_only", (False, True): "graphrag_only", (False, False): "neither"}[(a, b)]
        h2h[key] += 1
        lists[key].append(q["qid"])
    return qs, rows, summ, dict(h2h), {k: v for k, v in lists.items()}


# ---------------------------------------------------------------- Part B
US_STATES = {"alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida",
             "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
             "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
             "nevada", "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio",
             "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas",
             "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming", "united states"}
MSFT_EX21 = [("Microsoft Ireland Research Unlimited Company", "Ireland"), ("Microsoft Global Finance Unlimited Company", "Ireland"),
             ("Microsoft Ireland Operations Limited", "Ireland"), ("Microsoft Online, Inc.", "United States"),
             ("LinkedIn Corporation", "United States"), ("LinkedIn Ireland Unlimited Company", "Ireland"),
             ("Activision Blizzard, Inc.", "United States"), ("Activision Publishing, Inc.", "United States")]


def is_us(j: str) -> bool:
    j = j.lower().replace(", u.s.", "").strip()
    return j in US_STATES or j.endswith("u.s.")


class Ex21Graph:
    """Company -[:OWNS]-> Subsidiary {name, jurisdiction}, as in GraphRAG's ontology decision 2.6."""

    def __init__(self, lists: dict):
        self.owns = defaultdict(list)          # ticker -> [(name, jurisdiction)]
        self.owner_of = {}                     # normalised name -> ticker
        for t, rows in lists.items():
            for name, jur in rows:
                self.owns[t].append((name, jur))
                self.owner_of[norm(name)] = t

    def subs(self, t):
        return self.owns[t]

    def non_us(self, t):
        return [(n, j) for n, j in self.owns[t] if not is_us(j)]

    def countries(self, t):
        return {j for _, j in self.non_us(t)}

    def owner(self, name):
        return self.owner_of.get(norm(name))

    def edge(self, a, b):                      # does Subsidiary a own Subsidiary b? (no sub-to-sub edges in Ex21)
        return False


EX21_EDGES = UP / "KPMG-GraphRAG-ex21" / "ex21_pipeline" / "output" / "graph_edges.csv"
EX21_ACC = {"AAPL": "0000320193-25-000079", "CASY": "0000726958-26-000046", "MU": "0000723125-26-000023",
            "MSFT": "0001193125-26-323660", "NTAP": "0001193125-26-259683"}       # each company's 10-K in the snapshot


def graphrag_ex21() -> dict:
    """GraphRAG's own Exhibit 21 output (alina/ex21-pipeline): Parent -HAS_SUBSIDIARY-> Subsidiary rows."""
    rows = [e for e in csv.DictReader(open(EX21_EDGES)) if e["relation"] == "HAS_SUBSIDIARY"]
    return {t: [(e["target"], e["target_jurisdiction"]) for e in rows if a in e["evidence"]] for t, a in EX21_ACC.items()}


def ex21_agreement(ours: dict, theirs: dict) -> dict:
    """Row-level check of Eval's gold reads against GraphRAG's parse: same names, same jurisdictions."""
    out = {}
    for t, rows in ours.items():
        on, tn = {norm(n): norm(j) for n, j in rows}, {norm(n): norm(j) for n, j in theirs[t]}
        out[t] = {"eval_rows": len(on), "graphrag_rows": len(tn), "names_in_both": len(set(on) & set(tn)),
                  "same_jurisdiction": sum(on[n] == tn.get(n) for n in on)}
    return out


def part_b(gold, ex21):
    ours = {t: [tuple(x) for x in v["subsidiaries"]] for t, v in ex21["lists"].items() if v.get("subsidiaries")}
    ours["MSFT"] = MSFT_EX21
    ntap_isr = ex21["lookups"]["NTAP"]["israel"]
    ours["NTAP"] = [(n, "Israel") for n in ntap_isr]              # Eval read only NetApp's Israel rows
    lists = graphrag_ex21()                                         # both systems below use GraphRAG's rows
    agreement = ex21_agreement(ours, lists)
    g = Ex21Graph(lists)
    gq = {q["qid"]: q for q in gold}

    def mu_answer():
        return f"{len(g.subs('MU'))} subsidiaries, {len(g.non_us('MU'))} outside the U.S."

    def ins():
        out = []
        for t in ("AAPL", "CASY", "MU"):
            out += [f"{n} ({j.replace(', U.S.', '')})" for n, j in g.subs(t) if "insurance" in n.lower()]
        return "; ".join(out)

    def casy():
        c = Counter(j for _, j in g.subs("CASY"))
        j, n = c.most_common(1)[0]
        return f"{j}: {n} of {len(g.subs('CASY'))}"

    traversals = {
        "EV1R-001": ("count subsidiaries, filter by jurisdiction", lambda: f"{len(g.subs('MSFT'))} subsidiaries, {len(g.non_us('MSFT'))} outside the US ({', '.join(sorted(g.countries('MSFT')))})",
                     lambda a: a.startswith("8 subsidiaries, 4 outside") and "Ireland" in a),
        "EV1R-004": ("check an edge between two subsidiaries", lambda: f"edge exists: {g.edge('Activision Blizzard, Inc.', 'LinkedIn Ireland Unlimited Company')}; owners: {g.owner('Activision Blizzard, Inc.')}, {g.owner('LinkedIn Ireland Unlimited Company')}",
                     lambda a: "edge exists: False" in a and a.endswith("MSFT, MSFT")),
        "EV3-001": ("count subsidiaries, filter by jurisdiction", mu_answer, lambda a: a == "21 subsidiaries, 15 outside the U.S."),
        "EV3-002": ("join two companies on jurisdiction", lambda: ", ".join(sorted(g.countries("AAPL") & g.countries("MU"))),
                    lambda a: a == "China, India, Japan, Singapore"),
        "EV3-003": ("filter subsidiaries across three companies", ins,
                    lambda a: all(x in a for x in ("Apple Insurance Company, Inc. (Arizona)", "CARES Captive Insurance Company (Iowa)", "S-Squared Insurance Company, Inc. (Hawaii)"))),
        "EV3-004": ("group by jurisdiction and count", casy, lambda a: a == "Iowa: 6 of 9"),
        "EV3-005": ("filter by jurisdiction", lambda: ", ".join(n for n, j in g.subs("NTAP") if j == "Israel"),
                    lambda a: a.count(",") == 4 and "Spotinst Ltd." in a),
        "EV3-006": ("find the owner of a named subsidiary (fabricated link)", lambda: f"owner: {g.owner('Braeburn Capital, Inc.')}",
                    lambda a: a == "owner: AAPL"),
        "EV3-007": ("find the owner of a named subsidiary (false premise)", lambda: f"owner: {g.owner('Spotinst Ltd.')}",
                    lambda a: a == "owner: NTAP"),
    }
    # RAG side: the same rows as an Exhibit 21 page per company, through RAG's own chunker, indexed with the 10-Q chunks
    from rag.chunk import chunk_filing
    extra = []
    names = {"AAPL": "Apple Inc.", "CASY": "Casey's General Stores, Inc.", "MU": "Micron Technology, Inc.",
             "MSFT": "Microsoft Corporation", "NTAP": "NetApp, Inc."}
    for t, rows in lists.items():
        html = (f"<html><body><p>EXHIBIT 21</p><p>SUBSIDIARIES OF {names[t].upper()}</p><table>"
                + "<tr><td>Name</td><td>Jurisdiction of Incorporation</td></tr>"
                + "".join(f"<tr><td>{n}</td><td>{j}</td></tr>" for n, j in rows) + "</table></body></html>")
        meta = {"ticker": t, "cik": 0, "company": names[t], "form": "10-K", "fiscal_year": 2026, "fiscal_period": "FY",
                "period_of_report": "", "filing_date": "", "accession": f"EX21-{t}", "source_url": ""}
        recs, _ = chunk_filing(meta, html.encode())
        extra += recs
    base = [json.loads(l) for l in open(DATA / "rag_chunks_msft_10q.jsonl")]
    path = UP / "rag_chunks_with_ex21.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in base + extra))
    retr = build_rag(path, UP / "rag_index_w8_ex21")
    need_rows = {
        "EV1R-001": [("MSFT", n) for n, _ in MSFT_EX21],
        "EV1R-004": [("MSFT", "Activision Blizzard, Inc."), ("MSFT", "LinkedIn Ireland Unlimited Company")],
        "EV3-001": [("MU", n) for n, _ in lists["MU"]],
        "EV3-002": [(t, n) for t in ("AAPL", "MU") for n, _ in g.non_us(t)],
        "EV3-003": [("AAPL", "Apple Insurance Company, Inc."), ("CASY", "CARES Captive Insurance Company"),
                    ("MU", "S-Squared Insurance Company, Inc.")],
        "EV3-004": [("CASY", n) for n, _ in lists["CASY"]],
        "EV3-005": [("NTAP", n) for n in ntap_isr],
        "EV3-006": [("AAPL", "Braeburn Capital, Inc.")],
        "EV3-007": [("NTAP", "Spotinst Ltd.")],
    }
    out = []
    for qid, (op, fn, ok) in traversals.items():
        q = gq[qid]
        ans = fn()
        res = retr.search(q["question"], filters=None, top_k=K, method="bm25")["results"]
        got = {(r["ticker"], norm(n)) for r in res for (t, n) in need_rows[qid] if r["ticker"] == t and norm(n) in norm(r["text"])}
        need = {(t, norm(n)) for t, n in need_rows[qid]}
        untested = False                                            # GraphRAG's rows include NetApp's full list
        out.append({"qid": qid, "operation": op, "question": q["question"], "gold": q["answer"]["display"],
                    "graph_answer": ans, "graph_correct": bool(ok(ans)),
                    "rag_current_index_has_exhibit21": False,
                    "rag_with_ex21_rows_needed": len(need), "rag_with_ex21_rows_in_top8": None if untested else len(got & need),
                    "rag_with_ex21_all_rows_in_top8": None if untested else need <= got,
                    "rag_with_ex21_tickers_in_top8": sorted({r["ticker"] for r in res})})
    return out, {"ex21_chunks_added": len(extra), "companies": sorted(lists), "rows_used": "GraphRAG ex21 pipeline",
                 "eval_vs_graphrag_rows": agreement}


def main():
    gold = [json.loads(l) for l in open(DATA / "benchmark_v2_2.jsonl")]
    qs, rows, summ, h2h, lists = part_a(gold)
    ex21 = json.load(open(DATA / "sec_reads" / "exhibit21_2026-11-05.json"))
    trav, trav_meta = part_b(gold, ex21)
    kinds = Counter(kind(q) for q in qs)
    out = {
        "_doc": __doc__.strip().splitlines()[0],
        "commits": COMMITS, "top_k": K, "filing": ACC,
        "part_a": {"n_questions": len(qs), "kinds": dict(kinds), "summary": summ, "head_to_head_rag_bm25_vs_graphrag": h2h,
                   "head_to_head_qids": lists},
        "part_b": {"n_questions": len(trav), **trav_meta,
                   "graph_correct": sum(t["graph_correct"] for t in trav),
                   "rag_current_index": "Exhibit 21 not ingested (primaryDocument only), so 0 of these can be retrieved today",
                   "rag_with_ex21_all_rows_in_top8": sum(bool(t["rag_with_ex21_all_rows_in_top8"]) for t in trav),
                   "rag_with_ex21_tested": sum(t["rag_with_ex21_all_rows_in_top8"] is not None for t in trav),
                   "questions": trav},
        "not_run": {"graphrag_graph_arm": "needs Neo4j (graphrag/graph_backend.py); its committed claims cover FY2025 10-Ks "
                                          "(15 claims each for MSFT, AAPL, JPM), none for this 10-Q"},
    }
    RES.mkdir(exist_ok=True)
    (RES / "side_by_side.json").write_text(json.dumps(out, indent=1))
    with open(RES / "side_by_side_per_question.csv", "w", newline="") as f:
        cols = ["qid", "system", "kind", "type", "route_expected", "traps", "needed_in_evidence", "distractor_shown",
                "top1_right", "top1_wrong_period",
                "n_returned", "ms", "top1", "question"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({k: {m: v[m] for m in ("numbers", "prose", "distractor_shown_on_numbers", "returned_nothing_on_unanswerable",
                                            "median_ms")} for k, v in summ.items()}, indent=1))
    print("h2h", h2h)
    print("part B graph correct", out["part_b"]["graph_correct"], "/", len(trav), "| rag+ex21 all rows",
          out["part_b"]["rag_with_ex21_all_rows_in_top8"])
    for t in trav:
        print(" ", t["qid"], t["graph_correct"], t["graph_answer"][:80], "| rag rows", t["rag_with_ex21_rows_in_top8"], "/",
              t["rag_with_ex21_rows_needed"], t["rag_with_ex21_tickers_in_top8"])


if __name__ == "__main__":
    main()
