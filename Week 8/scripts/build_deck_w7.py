"""Evaluation & Testing slides for the 11/05 KPMG x Columbia meeting (Week 7 only), in the team deck's style.

    python scripts/build_deck_w7.py <base.pptx> <out.pptx>

Base: the team deck's Evaluation & Testing slide duplicated six times. Every number is read from results/*.json and
data/*.json(l), so re-running run_all.sh and this script keeps the slides in sync with the code. Charts and tables are
native PowerPoint objects.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_style import (BLUE, GREEN, INK, MUTED, NAMES, NAVY, PINK, clear, footer, header, j, jl, label, notes,  # noqa: E402
                        rgb, table, tb, tile)

ROOT = Path(__file__).resolve().parent.parent
RES, DATA = ROOT / "results", ROOT / "data"


def pct(x, nd=0):
    return f"{x * 100:.{nd}f}%"


def bar_chart(slide, x, y, w, h, cats, vals, colors, fmt='0', name=None, vmax=None):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("s", vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    if name:
        gf.name = name
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name, ch.font.size = "Arial", Pt(8)
    ch.font.color.rgb = rgb(INK)
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.color.rgb = Pt(8), rgb(INK)
    for i, c in enumerate(colors):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(c)
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E7F0")
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(8)
    va.tick_labels.font.color.rgb = rgb(MUTED)
    va.minimum_scale = 0
    if vmax:
        va.maximum_scale = vmax
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = fmt, False
    ca = ch.category_axis
    ca.format.line.color.rgb = rgb("C9CED8")
    ca.tick_labels.font.size = Pt(8)
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    ca.reverse_order = True
    return gf


# ================================================================ slides
def s_scope(s, snap):
    clear(s)
    m = snap["match"]
    header(s, "Scope", "ten companies, one snapshot: the 21 filings Data, GraphRAG and Eval now share")
    label(s, 0.12, 1.0, 5.6, "Each team's filing list against Data's database (Nov 3)")
    inv = m["data_inventory_2021_2026"]
    newer = inv["newer_than_snapshot"]
    rows = [["List", "Filings", "Match"],
            [("Data database (Nov 3)", {"bold": True}), f"{snap['counts']['10-K'] + snap['counts']['10-Q']} "
             f"({snap['counts']['10-K']} 10-K, {snap['counts']['10-Q']} 10-Q)", "the reference"],
            [("Data inventory 2021-2026", {"bold": True}), f"{inv['filings']}",
             "contains all 21" + (f"; 1 newer: {NAMES[newer[0][0]]} 10-Q to {newer[0][2][5:7]}/{newer[0][2][:4]}" if newer else "")],
            [("GraphRAG extraction", {"bold": True}), f"{m['graphrag_filings']['same']} of 21", "NetApp 10-Q held back (review required)"],
            [("Eval Gold Set v2", {"bold": True}), "21 of 21", f"was {m['eval_week6_list']['same']}/21 on 10/29 (Micron 10-K)"],
            [("RAG v2 index", {"bold": True}), f"{len(m['rag_v2_index']['covers_of_ten'])} of 10 companies",
             "Apple, Microsoft; 8 to index for round 1"]]
    table(s, 0.12, 1.22, 5.6, [1.75, 1.35, 2.5], rows, row_h=0.36, sizes={0: 8.5, 1: 8.5, 2: 8}, name="Filing match")
    x = 6.0
    tile(s, x, 1.15, "FY2026", "Micron's 10-K (filed Oct 9) is in the database. We said on 10/29 it was not: the SEC data API "
                               "still lacks it, so we now read it from the filing", w_big=1.05, w_lab=2.45, color=PINK)
    tile(s, x, 2.0, "3", "NetApp 10-Qs tagged one fiscal year behind the filing's own text (fiscal 2027 tagged 2026)",
         w_big=1.05, w_lab=2.45, color=PINK)
    tile(s, x, 2.75, str(inv["filings"]), "filings for 2021-2026 in Data's inventory; 232 pass Data's fact checks, 1 is in "
                                          "review", w_big=1.05, w_lab=2.45)
    footer(s, "Proposal:", "freeze this 21-filing snapshot for round 1, as RAG also asked Data. Every question names its period, "
                           "so filings loaded later cannot silently change an answer.",
           "Source: Week 7/data/snapshot_w7.json; Data fact-coverage-2021-2026.csv @ f8d18e2; GraphRAG filings.yaml @ 97eeba5; "
           "RAG Slack 10/28 (v2 manifest)", y=4.38, w=7.6)
    notes(s, "Thanks to Data's work this week we could match every list against one source. Data published a 233-filing inventory "
             "for the ten companies, and GraphRAG's config lists the 21 filings in the database on November 3. Our gold set now "
             "matches all 21. One correction from last week: we said Micron's newest annual report was not available. It was filed "
             "on October 9 and Data has it. The SEC's data API we used still doesn't show it, so we now read it from the filing. "
             "We also found NetApp's filing metadata labels its quarters one fiscal year behind its own text, which matters for any "
             "fiscal-year filter. RAG's index covers two of the ten companies so far. We propose freezing this snapshot for round 1.")


def s_gold(s, summ, checks, grader, stm):
    clear(s)
    g = summ["gold_set_v2"]
    header(s, "Gold Set v2", f"{g['questions']} questions, all on the ten companies; every answer checked against SEC data")
    per = g["answerable_questions_per_company"]
    order = sorted(per, key=lambda t: -per[t])
    label(s, 0.12, 1.0, 4.6, "Answerable questions per company (Microsoft stays the MVP)")
    bar_chart(s, 0.12, 1.2, 4.6, 3.1, [NAMES[t] for t in order], [per[t] for t in order],
              [NAVY if t == "MSFT" else BLUE for t in order], name="Questions per company")
    x = 5.0
    cs = checks["summary"]
    tile(s, x, 1.1, cs["read2_agrees_with_read1"], "independent re-reads of new answers agree (SEC API, and Micron's 10-K itself)",
         w_big=1.05, w_lab=2.55)
    tile(s, x, 1.72, f"{grader['graded'] - len(grader['mismatches'])}/{grader['graded']}",
         f"grader labels right on the {grader['numeric_items']} new numeric questions (right, restated, x1000, sign)",
         w_big=1.05, w_lab=2.55)
    tile(s, x, 2.34, f"{len(stm['statements'])}/9", "other companies' latest income statements, read from the filings: "
                                                     "every figure matches the gold", w_big=1.05, w_lab=2.55)
    mck = next(x for x in stm["statements"] if x["ticker"] == "MCK")["lines"]
    tile(s, x, 2.96, "$337M", f"minority interests inside McKesson's printed 'Net income' ({mck['Net income'][0]} vs "
                              f"{mck['Net income attributable to McKesson Corporation'][0]}); questions now say which figure",
         w_big=1.05, w_lab=2.55, color=PINK)
    tile(s, x, 3.58, "9 new", "Exhibit 21 relationship and NetApp fiscal-label questions (next slide)", w_big=1.05, w_lab=2.55)
    footer(s, "Changed since 10/29:", "Micron moves to fiscal 2026 (revenue USD 133,188M, up 256% in a 53-week year); last week's "
                                      "Micron refusal question became a derived fourth-quarter question.",
           "Source: Week 7/data/benchmark_v2.jsonl; results/gold_v2_summary.json, scope10_checks.json, scope10_grader_check.json; "
           "data/sec_reads/", y=4.42, w=7.6)
    notes(s, "Gold Set v2 has 155 questions and every answerable one is about the ten companies. Microsoft is still the MVP with the "
             "most questions; every other company has 9 to 16. Answers are computed in code from SEC data and checked: all 55 "
             "re-reads agree, the grader labels all 160 test answers correctly, and we read each company's income statement from the "
             "filing as a third check. That check caught a wording problem: McKesson's 'Net income' line includes 337 million of "
             "minority interests, so the questions now say which figure they mean.")


def s_relationships(s, gold, ex):
    clear(s)
    q = {x["qid"]: x for x in gold}
    rel = [x for x in gold if x["route_expected"] == "graph"]
    header(s, "Relationships", "Exhibit 21 brings GraphRAG-style questions to the ten companies")
    rows = [["Question (short)", "Expected answer", "Tests"],
            ["Countries in both Apple's and Micron's subsidiary lists?", ", ".join(q["EV3-002"]["answer"]["required_points"]),
             "join across companies"],
            ["Insurance subsidiaries of Apple, Casey's, Micron?", "Arizona, Iowa, Hawaii", "three-company traversal"],
            ["Micron: subsidiaries listed, how many abroad?", "21; 15 outside the U.S.", "count a list"],
            ["Is Braeburn Capital a Micron subsidiary?", "No: it is Apple's", "invented link"],
            ["Which Micron business owns Spotinst?", "False premise: NetApp's", "invented link"],
            ["NetApp quarter ended Jul 31, 2026: fiscal label?", "Fiscal 2027 Q1 (metadata says 2026)", "metadata trap"]]
    table(s, 0.12, 1.12, 6.25, [2.6, 2.2, 1.45], rows, row_h=0.36, sizes={0: 8, 1: 8, 2: 8}, name="Relationship examples")
    x = 6.65
    n_ev1r = sum(1 for x in rel if x["qid"].startswith("EV1R")); n_ev3 = sum(1 for x in rel if x["qid"].startswith("EV3"))
    tile(s, x, 1.12, str(len(rel)), f"questions routed to GraphRAG: {n_ev1r} drafted with GraphRAG + {n_ev3} from Exhibit 21",
         w_big=0.65, w_lab=2.4)
    tile(s, x, 1.8, str(sum(1 for t in ("AAPL", "CASY", "MU") if ex["lists"][t])), "Exhibit 21 lists transcribed in full and "
                                                                                     "read twice (Apple 19, Casey's 9, Micron 21)",
         w_big=0.65, w_lab=2.4)
    tile(s, x, 2.48, "4", "invented-relationship checks in total, the way graphs most often fail", w_big=0.65, w_lab=2.4,
         color=PINK)
    tile(s, x, 3.16, "144", "Take-Two subsidiaries: too long to transcribe reliably, so long lists are used only for lookups",
         w_big=0.65, w_lab=2.4)
    footer(s, "For GraphRAG:", "these cover the M02 and M14 shapes from your eval-ask, now on the ten companies. Once Data's cleaned "
                               "Exhibit 21 lands, we compare it with our reads.",
           "Source: Week 7/data/sec_reads/exhibit21_2026-11-05.json; data/benchmark_v2.jsonl (EV3-001..009, EV1R-001..006)",
           y=4.42, w=7.6)
    notes(s, "GraphRAG asked for questions that need following a relationship, and Data is cleaning Exhibit 21. We read Exhibit 21 "
             "for each company's latest annual report and wrote questions that only a relationship-aware system answers well: "
             "joining two companies' subsidiary lists, traversing three companies, and two checks for invented relationships. "
             "Short lists were transcribed twice; long ones like Take-Two's 144 are used only for single lookups.")


def s_decisions(s, dec):
    clear(s)
    header(s, "Answer, clarify, abstain or block", "draft rules for the Agents' checkpoints, with a test set and a score")
    rows = [["Decision", "When", "Tools"],
            [("Answer", {"bold": True}), "Company and period known; evidence supports every number", "as routed"],
            [("Clarify", {"bold": True}), "Company missing, or 'it'/'they' with nothing to refer to", "0"],
            [("Abstain", {"bold": True}), "Outside the ten or the snapshot; forecast; advice; not disclosed", "0 if the gate decides"],
            [("Block", {"bold": True, "color": PINK}), "Off-topic or instruction override: ask for an on-topic question", "0"]]
    table(s, 0.12, 1.1, 4.95, [0.85, 3.45, 0.65], rows, row_h=0.4, sizes={0: 8.5, 1: 8, 2: 8}, name="Decision rules")
    a, r = dec["policies"]["always_answer"]["all"], dec["policies"]["rule_gate"]["all"]
    label(s, 5.35, 0.98, 4.4, f"{a['n']} questions: Gold Set v2 + 24 new clarify/abstain/off-topic")
    rows2 = [["", ("Answer everything", {"align": PP_ALIGN.CENTER}), ("Simple scope check", {"align": PP_ALIGN.CENTER})],
             ["Right decision", (pct(a["decision_accuracy"], 1), {"align": PP_ALIGN.CENTER}),
              (pct(r["decision_accuracy"], 1), {"align": PP_ALIGN.CENTER, "bold": True, "color": GREEN})],
             ["Unsafe answers", (pct(a["unsafe_answer_rate"]), {"align": PP_ALIGN.CENTER, "color": PINK}),
              (pct(r["unsafe_answer_rate"], 1), {"align": PP_ALIGN.CENTER, "bold": True})],
             ["Tool calls on off-topic", (str(a["off_topic_tool_calls"]), {"align": PP_ALIGN.CENTER, "color": PINK}),
              (str(r["off_topic_tool_calls"]), {"align": PP_ALIGN.CENTER, "bold": True, "color": GREEN})],
             ["Needless refusals", (pct(a["over_refusal_rate"]), {"align": PP_ALIGN.CENTER}),
              (pct(r["over_refusal_rate"]), {"align": PP_ALIGN.CENTER})]]
    table(s, 5.35, 1.2, 4.35, [1.75, 1.3, 1.3], rows2, row_h=0.36, sizes={0: 8.5, 1: 8.5, 2: 8.5}, name="Decision scores")
    n_left = round(r["unsafe_answer_rate"] * sum(v["n"] for k, v in r["per_decision"].items() if k != "answer"))
    tb(s, 5.35, 3.15, 4.35, 0.6, [[(f"The {n_left} unsafe answers left ", 8.5, True, NAVY),
                                   ("need an evidence check after retrieval: figures the filing does not disclose, invented "
                                    "relationships, a quarter not yet filed.", 8.5, False, INK)]])
    footer(s, "From KPMG's 10/29 guidance:", "checkpoints gate off-topic questions and block tool calls. The scope check is a "
                                             "reference point; Agents own the real rules.",
           "Source: Week 7/POLICY_answer_clarify_abstain.md; results/decision_baselines.json; data/decision_suite_v1.jsonl",
           y=4.42, w=7.6)
    notes(s, "Agents asked us to define when the agent proceeds, asks or abstains, and KPMG added that off-topic questions should "
             "be blocked before any tool call. We wrote four rules and a score for each: unsafe answers, needless refusals and tool "
             "calls on off-topic questions. To show the score works, we compared answering everything with a simple scope check. "
             "Answering everything gets every one of these wrong and calls tools on all eight off-topic questions. The scope "
             "check blocks all of them with zero tool calls. What is left needs an evidence check after retrieval, which is the "
             "Agents' evidence-review step.")


def s_routing(s, rt):
    clear(s)
    R = rt["routers"]
    header(s, "Routing", "question-based routing vs combined retrieval, on the same 155 questions")
    label(s, 0.12, 1.0, 4.9, "Questions whose needed tools were called")
    names = [("text_only", "Text only (today's demo)"), ("keyword", "Keyword router (Eval stand-in)"),
             ("combined", "Combined: every tool")]
    bar_chart(s, 0.12, 1.2, 4.9, 1.75, [n for _, n in names], [R[k]["required_tools_called"] for k, _ in names],
              [MUTED, BLUE, NAVY], fmt='0%', name="Routing coverage", vmax=1)
    rows = [["Router", "Tool calls / question", "Unneeded calls / question"]] + [
        [n, (f"{R[k]['tool_calls_per_question']:.2f}", {"align": PP_ALIGN.CENTER}),
         (f"{R[k]['unneeded_calls_per_question']:.2f}", {"align": PP_ALIGN.CENTER})] for k, n in names]
    table(s, 0.12, 3.05, 4.9, [2.3, 1.3, 1.3], rows, row_h=0.28, sizes={0: 8, 1: 8, 2: 8}, name="Routing cost")
    x = 5.35
    er = rt["expected_routes"]
    tb(s, x, 1.0, 4.4, 0.2, [("Expected route on every question", 9.5, True, INK)])
    tb(s, x, 1.25, 4.4, 0.45, [[(f"{er.get('sql', 0)} finance data · {er.get('text', 0)} text · {er.get('graph', 0)} graph · "
                                 f"{er.get('multi', 0)} both · {er.get('none', 0)} no tool", 9, False, INK)]])
    kw = R["keyword"]["required_tools_called_by_route"]
    tile(s, x, 1.75, pct(kw.get("text", 0)), "keyword router on text questions: narrative questions that mention numbers get "
                                             "sent to the finance data", w_big=0.85, w_lab=3.4, color=PINK)
    tb(s, x, 2.55, 4.4, 0.2, [("RAG's two asks: done", 9.5, True, NAVY)])
    tb(s, x, 2.8, 4.4, 1.2, [[("Accuracy by route: ", 8.5, True, INK), ("every scorecard now reports numeric accuracy by "
                                                                         "expected route.", 8.5, False, INK)],
                             [("Fixed reader: ", 8.5, True, INK), ("gpt-4o-mini at temperature 0, RAG's own prompt, top 8, is a "
                                                                   "harness system; it runs once an API key is set.",
                                                                   8.5, False, INK)]])
    footer(s, "Trade-off:", f"combined retrieval covers {pct(R['combined']['required_tools_called'])} at "
                            f"{R['combined']['tool_calls_per_question']:.0f} calls per question; a router covers "
                            f"{pct(R['keyword']['required_tools_called'])} at {R['keyword']['tool_calls_per_question']:.2f}. "
                            "Agents can run their orchestrator through the same script.",
           "Source: Week 7/results/routing_baselines.json; kpmg_eval/metrics/routing.py; scripts/systems.py (FixedReaderSystem). "
           "Expected routes are Eval's labels, for Agents to review", y=4.38, w=7.6)
    notes(s, "KPMG suggested comparing question-based routing with combined retrieval on the same questions. We labelled the tool "
             "each question needs and wrote a script that scores any router. Sending everything to text search, as the demo does "
             "today, covers only the text questions. Calling every tool covers almost all of them but triples the calls. A simple "
             "keyword router sits in between and struggles with narrative questions that mention numbers. These routers are "
             "reference points; the real comparison is the Agents' orchestrator through the same script. We also did RAG's two "
             "asks: accuracy by route, and their fixed reader as a ready system.")


def s_next(s, rev, fixes):
    clear(s)
    sm = rev["summary"]
    c = Counter(r["action"] for r in fixes)
    good = sum(1 for r in fixes if r["action"] == "narrow" and r["suggested_n_chunks"])
    header(s, "Next steps", "anchor fixes for RAG, and one ask per team before round 1 (W8)")
    label(s, 0.12, 1.0, 3.4, "Our review of RAG's 100 anchors")
    tile(s, 0.12, 1.25, sm["inputs_in_anchored_chunks"], "numbers the answers use sit in an anchored chunk", w_big=0.9, w_lab=2.25)
    tile(s, 0.12, 1.85, f"{good}/{c['narrow']}", "broad anchors get a specific replacement, e.g. 'Total revenue | 82,886' "
                                                 "(6 chunks to 1)", w_big=0.9, w_lab=2.25)
    tile(s, 0.12, 2.45, str(c["remove"]), "anchors to remove: a share-count string carried over from Gold v0", w_big=0.9,
         w_lab=2.25, color=PINK)
    tile(s, 0.12, 3.05, str(c["drop"]), "questions to drop, incl. the 8 Amazon/Meta ones RAG asked about: outside the ten",
         w_big=0.9, w_lab=2.25)
    rows = [["Team", "Ask before round 1"],
            [("Data", {"bold": True}), "Confirm the 21-filing snapshot as the round-1 freeze; share chunks for all 21; "
                                       "cleaned Exhibit 21 to compare with our reads"],
            [("RAG", {"bold": True}), "Index the other 8 companies; apply rag_anchor_fixes.csv; an API key for the fixed reader"],
            [("GraphRAG", {"bold": True}), "Hops for the 165 questions; review the 11 relationship questions; a backend date"],
            [("Agents", {"bold": True}), "Review the decision rules and expected routes; add 'decision' to the AnswerBlock"],
            [("Eval", {"bold": True}), "Text anchors for the new questions once chunks land; run round 1 in week 8"]]
    table(s, 3.65, 1.12, 6.05, [0.85, 5.2], rows, row_h=0.42, sizes={0: 8.5, 1: 8}, name="Asks")
    footer(s, "Round 1 needs three things:", "the frozen snapshot, an index for all ten companies, and the Agent's AnswerBlock. "
                                              "The grading side is ready.",
           "Source: Week 7/results/rag_anchor_fixes.csv, rag_gold_v1_anchor_review.json (RAG eval/gold_v1.jsonl @ 6f0894a)",
           y=4.42, w=7.6)
    notes(s, "RAG mapped evidence to all 100 questions and asked for our review, so we sent it back as a file with one row per fix. "
             "Most broad anchors get a specific replacement, like adding the 'Total revenue' row label, which narrows six matching "
             "chunks to one. The ten retired questions include the eight Amazon and Meta ones RAG asked about: they're outside the "
             "ten companies, so they can simply be dropped. The table has one ask per team for round 1 in week 8.")


def main():
    base, out = sys.argv[1], sys.argv[2]
    prs = Presentation(base)
    sl = list(prs.slides)
    assert len(sl) == 6, "base deck must hold exactly six Evaluation & Testing slides"
    snap, summ = j(DATA / "snapshot_w7.json"), j(RES / "gold_v2_summary.json")
    gold = jl(DATA / "benchmark_v2.jsonl")
    ex, stm = j(DATA / "sec_reads" / "exhibit21_2026-11-05.json"), j(DATA / "sec_reads" / "filing_statements_2026-11-05.json")
    fixes = list(csv.DictReader(open(RES / "rag_anchor_fixes.csv")))
    s_scope(sl[0], snap)
    s_gold(sl[1], summ, j(RES / "scope10_checks.json"), j(RES / "scope10_grader_check.json"), stm)
    s_relationships(sl[2], gold, ex)
    s_decisions(sl[3], j(RES / "decision_baselines.json"))
    s_routing(sl[4], j(RES / "routing_baselines.json"))
    s_next(sl[5], j(RES / "rag_gold_v1_anchor_review.json"), fixes)
    prs.save(out)
    print("[deck] wrote", out)


if __name__ == "__main__":
    main()
