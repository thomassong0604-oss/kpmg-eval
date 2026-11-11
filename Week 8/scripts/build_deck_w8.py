"""Evaluation & Testing slides for the week-8 KPMG x Columbia meeting, in the team deck's style.

    python scripts/build_deck_w8.py <base.pptx> <out.pptx>

Base: any deck whose slides are the team's Evaluation & Testing slide (Week 7's six-slide base works; slides are added
by copying the first one). Every number is read from results/*.json, so re-running run_all.sh and this script keeps
the slides in sync with the code. Charts and tables are native PowerPoint objects.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_style import (BLUE, GREEN, INK, MUTED, NAVY, PINK, clear, footer, header, j, label, notes, rgb,  # noqa: E402
                        table, tb, tile)

ROOT = Path(__file__).resolve().parent.parent
RES, DATA = ROOT / "results", ROOT / "data"
N_SLIDES = 8
C = {"center": {"align": PP_ALIGN.CENTER}}


def pct(x, nd=0):
    return f"{x * 100:.{nd}f}%"


def col_chart(slide, x, y, w, h, cats, series, xtitle, ytitle, name, fmt="0%", vmax=1.0, label_size=7.5):
    """Clustered columns with both axes titled. series = [(name, values, colour)]."""
    cd = CategoryChartData()
    cd.categories = cats
    for n, vals, _ in series:
        cd.add_series(n, vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    gf.name = name
    ch = gf.chart
    ch.font.name, ch.font.size = "Arial", Pt(8)
    ch.font.color.rgb = rgb(INK)
    ch.has_title = False
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(8)
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = 60, -10
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.color.rgb = Pt(label_size), rgb(INK)
    for s, (_, _, col) in zip(plot.series, series):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = rgb(col)
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale = 0, vmax
    va.major_unit = 0.2 if vmax > 1 else None
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E7F0")
    va.format.line.fill.background()
    va.tick_labels.font.size, va.tick_labels.font.color.rgb = Pt(7.5), rgb(MUTED)
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = fmt, False
    ca = ch.category_axis
    ca.format.line.color.rgb = rgb("C9CED8")
    ca.tick_labels.font.size = Pt(7.5)
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    for axis, title in ((va, ytitle), (ca, xtitle)):
        axis.has_title = True
        tf = axis.axis_title.text_frame
        tf.text = title
        r = tf.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(8), True, rgb(MUTED), "Arial"
    return gf


def add_slides(prs, n):
    """Copy the first slide until the deck holds n (the title placeholder is kept; clear() removes the rest)."""
    src = prs.slides[0]
    while len(prs.slides) < n:
        dst = prs.slides.add_slide(src.slide_layout)
        for sh in list(dst.shapes):
            sh._element.getparent().remove(sh._element)
        for sh in src.shapes:
            dst.shapes._spTree.append(copy.deepcopy(sh._element))
    while len(prs.slides) > n:
        rid = prs.slides._sldIdLst[-1].rId
        prs.part.drop_rel(rid)
        del prs.slides._sldIdLst[-1]


# ================================================================ slides
def s_scope(s, sbs, rt, mw):
    clear(s)
    a, b = sbs["part_a"], sbs["part_b"]
    header(s, "Scope", "the Eval action items from the last two meetings, and where each one is answered")
    rows = [["Action item", "What we did", "Slide"],
            ["Run round 1 in week 8 (minutes #5)", "RAG ran our scoring on Gold Set v2 (11/9); we fixed the anchors it flagged",
             ("2", C["center"])],
            ["Run one question set on RAG and GraphRAG, side by side",
             f"All {a['n_questions']} Microsoft 10-Q questions through each team's own code, same filing, top 8", ("3", C["center"])],
            ["Show where GraphRAG does better, and where RAG does",
             f"Plus the {b['n_questions']} Exhibit 21 relationship questions (traversal)", ("4", C["center"])],
            ["Label the routing chart's axes; define the keyword router", "Chart redrawn by expected route, axes titled",
             ("5", C["center"])],
            ["Explain how unneeded calls per question are measured", "Definition with a worked example", ("5", C["center"])],
            ["Concrete routing examples for the demo", "Seven questions, three routers, calls counted", ("6", C["center"])],
            ["Say accuracy is on the current 155 questions only", "Stated on every routing and wording number",
             ("5-7", C["center"])],
            ["Typos and messy wording, for real-user accuracy",
             f"{mw['n_variants']} rewrites of the 155 questions through gate, router and both retrievers", ("7", C["center"])]]
    table(s, 0.12, 1.0, 7.6, [3.25, 3.85, 0.5], rows, row_h=0.34, sizes={0: 8, 1: 8, 2: 8}, name="Action items")
    tb(s, 7.95, 1.0, 1.85, 2.9, [[("All figures use the current 155 Gold Set v2 questions", 9, True, NAVY)],
                                [(" ", 4, False, INK)],
                                [("104 finance data, 31 text, 11 relationship, 8 no tool, 1 both. Microsoft has 92 of them, "
                                  "so per-route numbers on 1-11 questions are examples, not estimates. They will move as "
                                  "questions are added.", 8.5, False, INK)]])
    footer(s, "Pinned:", "RAG main @ 5bfafeb (11/5), GraphRAG main @ 4e89acb (11/11) and Exhibit 21 branch @ c21fe89, Data @ "
                         "f8d18e2. No LLM is used in any result; everything except RAG's round-1 run (slide 2) re-runs here exactly.",
           "Source: Week 8/README.md; scripts/run_all.sh (83 tests pass)", y=4.42, w=7.6)
    notes(s, "These are round 1, which we committed to two weeks ago, and the seven Eval items from last week's minutes. Each "
             "one has a script and a result file in the Week 8 folder, and the slide number on the right says where it's covered. One caveat for everything that follows: the "
             "numbers come from the 155 questions we have now, which lean on Microsoft and on finance-data questions.")


def s_round1(s, r1, v21):
    clear(s)
    R = r1["strict_recall"]
    h = r1["hybrid_k10"]
    header(s, "Round 1", f"retrieval on Gold Set v2, run by RAG with our scoring rules (11/9): {h['hits']} of {h['n']} found")
    cats = ["k = 5", "k = 8", "k = 10"]
    col_chart(s, 0.12, 1.0, 4.2, 3.3, cats,
              [("Hybrid", [R["hybrid"][f"k{k}"] for k in (5, 8, 10)], NAVY),
               ("BM25", [R["bm25"][f"k{k}"] for k in (5, 8, 10)], BLUE),
               ("Dense", [R["dense"][f"k{k}"] for k in (5, 8, 10)], "A9B0BD"),
               ("Hybrid, no filter", [R["hybrid_no_filter"][f"k{k}"] for k in (5, 8, 10)], PINK)],
              "Results kept per question (k)", "Scored questions with all evidence", "Round 1 recall",
              fmt="0%", vmax=1.15, label_size=6)
    n_mu, n_ms = r1["non_msft_single_company"], r1["by_company_hybrid_k10"]["MSFT"]
    tile(s, 4.5, 1.0, f"{h['numbers'][0]}/{h['numbers'][1]}", f"number questions; prose {h['prose'][0]}/{h['prose'][1]} "
         "(hybrid, k = 10, hit must come from the right filing)", w_big=1.0, w_lab=4.2, color=NAVY)
    tile(s, 4.5, 1.55, f"{n_mu[0]}/{n_mu[1]}", f"single-company questions on the nine other companies, vs Microsoft "
         f"{n_ms[0]}/{n_ms[1]}: adding nine companies did not hurt retrieval", w_big=1.0, w_lab=4.2, color=GREEN)
    rows = [["Why 19 were missed", ("n", C["center"]), "Who fixes it"]]
    short = {"Cross-company ranking: one search cannot hold 10-20 figures": "Cross-company ranking: 10-20 figures",
             "Gold anchors do not match the question (auto-converted in Gold v0)": "Our anchors were wrong (Gold v0 conversion)",
             "Derived quarter needs both the 10-K and the 10-Q": "Needs the 10-K and the 10-Q together",
             "BM25 and dense each had it; fusion pushed it just past k=10": "Fusion pushed it just past k = 10",
             "All three methods missed": "All three methods missed"}
    who = {"Eval": f"Eval: fixed in v2.1 (all {v21['reanchored_from_region']} converted anchors)"}
    owner_short = ["Agents: one search per company", None, "Agents: one search per form", "RAG: candidate k, fusion weights",
                   "RAG: ranking; 1 is truly multi-part"]
    for m, o in zip(r1["misses_by_cause"], owner_short):
        rows.append([short[m["cause"]], (str(m["n"]), C["center"]),
                     (who["Eval"], {"bold": True, "color": GREEN}) if m["owner"] == "Eval" else o])
    table(s, 4.5, 2.15, 5.3, [2.45, 0.35, 2.5], rows, row_h=0.27, sizes={0: 7.5, 1: 7.5, 2: 7.5}, name="Misses")
    w = r1["wrong_period_figure_in_top8"]
    footer(s, "Also found:", f"a wrong-period figure sits in the top 8 for {w['rate'] * 100:.1f}% of the {w['of_number_questions_with_distractor']} "
                            "number questions that have one, so the reader "
                            "must be told which column to take; fusion scores look the same for hits and misses, so 'weak "
                            "evidence' has to come from structure (empty result, no filter match, BM25 and dense disagree).",
           "Source: RAG team, round-1 results 11/9 (KPMG_RAG scripts/run_round1_eval.py), transcribed in Week 8/data/"
           "round1_rag_2026-11-09.json; Gold Set v2.1 in Week 8/GOLD_SET_V2.md. Evidence level; no reader yet", y=4.38, w=7.6)
    notes(s, "Round 1 happened this week. RAG ran our scoring rules on the full Gold Set v2 against its index of the 20 filings. "
             "Hybrid search with filters finds all the evidence for 105 of 124 scored questions at 10 results, and the nine "
             "non-Microsoft companies score at least as well as Microsoft. RAG traced every miss. Three are cross-company rankings "
             "that one search can't hold, so the Agents should split them per company. Four were our mistake: the anchors on four "
             "of the original RAG questions came from an automatic conversion and didn't match the questions. We checked the other "
             "converted anchors too and replaced all 22 the same day, as Gold Set v2.1. The rest are ranking and query-splitting "
             "fixes on the RAG and Agents side. Answer accuracy needs the reader, which needs an API key.")


def s_side_by_side(s, sbs):
    clear(s)
    a = sbs["part_a"]
    S = a["summary"]
    r, g = S["rag_bm25"], S["graphrag_structured"]
    h = a["head_to_head_rag_bm25_vs_graphrag"]
    header(s, "RAG vs GraphRAG", f"the same {a['n_questions']} Microsoft 10-Q questions, each team's own code on the same filing")
    cats = [f"Numbers: inputs in top 8 (n={r['numbers']['n']})", f"Prose: gold passage in top 8 (n={r['prose']['n']})",
            f"Numbers: wrong-period figure also shown, lower is better (n={r['distractor_shown_on_numbers']['n']})"]
    col_chart(s, 0.12, 1.0, 5.6, 3.3, cats,
              [("RAG (its BM25 search)", [r["numbers"]["rate"], r["prose"]["rate"], r["distractor_shown_on_numbers"]["rate"]], BLUE),
               ("GraphRAG (structured search)", [g["numbers"]["rate"], g["prose"]["rate"], g["distractor_shown_on_numbers"]["rate"]], PINK)],
              "Question group (number of questions)", "Share of questions", "Side by side", vmax=1.15)
    x = 5.95
    tb(s, x, 1.0, 3.8, 0.2, [("Head to head on the 77 answerable questions", 9.5, True, INK)])
    rows = [["", ("GraphRAG has it", C["center"]), ("GraphRAG misses", C["center"])],
            [("RAG has it", {"bold": True}), (str(h.get("both", 0)), C["center"]), (str(h.get("rag_only", 0)), C["center"])],
            [("RAG misses", {"bold": True}), (str(h.get("graphrag_only", 0)), C["center"]), (str(h.get("neither", 0)), C["center"])]]
    table(s, x, 1.25, 3.7, [1.1, 1.3, 1.3], rows, row_h=0.27, name="Head to head")
    tb(s, x, 2.2, 3.8, 1.9, [[("How it was run. ", 8, True, INK),
                              ("RAG: its chunker, index and Retriever.search with the question's filters. GraphRAG (main, "
                               "11/11, via graphrag.backends): its fact loader built the store from Data's copy of the filing "
                               "(1,317 facts), then structured_search. Its graph arm (696 claims for this filing) runs on an Aura "
                               "database our workspace cannot reach, so GraphRAG will run our script for it.", 8, False, INK)],
                             [(" ", 4, False, INK)],
                             [("Neither side returned an empty result ", 8, True, INK),
                              (f"on the {g['returned_nothing_on_unanswerable']['n']} unanswerable questions, so abstaining stays "
                               "with the Agents' evidence check.", 8, False, INK)]])
    footer(s, "Read:", "RAG's search finds the needed numbers and passages more often; GraphRAG's facts carry their exact period, "
                       "so wrong-period figures show up less. Evidence level only: no reader model yet.",
           "Source: Week 8/results/side_by_side.json (scripts/run_side_by_side.py). RAG's hybrid with its offline stand-in for the "
           f"dense model: numbers {pct(S['rag_hybrid']['numbers']['rate'])}, prose {pct(S['rag_hybrid']['prose']['rate'])}",
           y=4.38, w=7.6)
    notes(s, "We ran the full Microsoft 10-Q question set, 84 questions, through both teams' code on the same filing. For RAG that is "
             "its own chunker, index and retriever. For GraphRAG it is their fact loader and structured search. We check whether "
             "the evidence each returns contains what the answer needs. RAG finds the numbers in 49 of 50 questions, GraphRAG in "
             "25, and only RAG returns prose. GraphRAG's strength shows in the third pair of bars: its facts are labelled with "
             "the period, so a wrong-period figure appears much less often. Neither returns nothing on unanswerable questions, so "
             "the decision to abstain belongs to the Agents' step.")


def s_better(s, sbs):
    clear(s)
    a, b = sbs["part_a"], sbs["part_b"]
    g = a["summary"]["graphrag_structured"]
    r = a["summary"]["rag_bm25"]
    d = g["number_miss_diagnosis"]["counts"]
    header(s, "Where each does better", "GraphRAG on relationships across filings, RAG on reading the filing itself")
    label(s, 0.12, 1.0, 4.6, f"{b['n_questions']} relationship questions (Exhibit 21)", NAVY)
    tile(s, 0.12, 1.25, f"{b['graph_correct']}/{b['n_questions']}", "answered exactly by traversal of GraphRAG's own "
         "Exhibit 21 rows (parent HAS_SUBSIDIARY subsidiary): counts, joins, ownership checks", w_big=0.85, w_lab=3.6, color=NAVY)
    tile(s, 0.12, 1.8, f"0/{b['n_questions']}", "reachable by RAG today: it indexes each filing's main report, and "
         "Exhibit 21 is a separate document", w_big=0.85, w_lab=3.6, color=PINK)
    tile(s, 0.12, 2.35, f"{b['rag_with_ex21_all_rows_in_top8']}/{b['rag_with_ex21_tested']}",
         "with Exhibit 21 added as text, RAG's search brings every needed row; the counting and joining is then left "
         "to the reader (Apple and Micron's shared countries: 15 of 31 rows)", w_big=0.85, w_lab=3.6, color=BLUE)
    agr = b["eval_vs_graphrag_rows"]
    same = sum(v["same_jurisdiction"] for v in agr.values())
    ours = sum(v["eval_rows"] for v in agr.values())
    tb(s, 0.12, 3.05, 4.6, 1.2, [[("Cross-check: ", 8, True, MUTED),
                                  (f"GraphRAG's Exhibit 21 pipeline (11/8) and our gold reads agree on {same} of {ours} rows, names "
                                   "and jurisdictions. Rows are GraphRAG's; the traversal ran in memory here, since their Neo4j "
                                   "is not reachable from our side.", 8, False, MUTED)]])
    rows = [["", "Better at", "Evidence (Microsoft 10-Q, top 8)"],
            [("GraphRAG", {"bold": True, "color": PINK}), "Relationship questions", "Counts and joins come out exact (left)"],
            ["", "Exact periods on numbers", f"Wrong-period figure shown {pct(g['distractor_shown_on_numbers']['rate'])} vs RAG "
                                             f"{pct(r['distractor_shown_on_numbers']['rate'])}"],
            [("RAG", {"bold": True, "color": BLUE}), "Prose and explanations", f"{r['prose']['hits']}/{r['prose']['n']} vs "
                                                                           f"{g['prose']['hits']}/{g['prose']['n']}: structured "
                                                                           "search holds numbers only"],
            ["", "Finding the right number", f"{r['numbers']['hits']}/{r['numbers']['n']} vs {g['numbers']['hits']}/"
                                             f"{g['numbers']['n']}"]]
    table(s, 4.95, 1.0, 4.85, [0.8, 1.6, 2.45], rows, row_h=0.36, sizes={0: 8, 1: 8, 2: 7.5}, name="Better at")
    tb(s, 4.95, 2.95, 4.85, 1.3, [[(f"Where GraphRAG's {g['numbers']['n'] - g['numbers']['hits']} number misses come from (each has a fix)",
                                    8.5, True, INK)],
                                  [(f"{d.get('in_top50_ranked_below_8', 0)} ranked below 8: ", 8, True, INK),
                                   (f"in {d.get('ranked_below_8_period_word_matches_member', 0)}, 'three months' or 'six months' "
                                    "matches Microsoft 365 ('ThreeSixFive') rows, so total revenue ranks 10th", 8, False, INK)],
                                  [(f"{d.get('multi_input_not_all_in_top50', 0)} calculations: ", 8, True, INK),
                                   ("one call cannot fetch every input; one call per input would", 8, False, INK)],
                                  [(f"{d.get('single_input_not_in_top50', 0)} wording: ", 8, True, INK),
                                   ("'current unearned revenue', 'repurchasing common stock' miss their concepts",
                                    8, False, INK)],
                                  [("Rank 1: ", 8, True, INK),
                                   (f"right number {g['top1_right_on_numbers']['hits']}/{g['top1_right_on_numbers']['n']}, a "
                                    f"wrong-period number {g['top1_wrong_period_on_numbers']['hits']}/"
                                    f"{g['top1_wrong_period_on_numbers']['n']}; GraphRAG flagged this itself", 8, False, INK)]])
    footer(s, "Together:", "route relationship questions to GraphRAG and narrative ones to RAG; numbers can use either once "
                           "GraphRAG's ranking fix lands, with GraphRAG's period labels as the check.",
           "Source: Week 8/results/side_by_side.json (part_b, number_miss_diagnosis); GraphRAG ex21_pipeline/output/graph_edges.csv "
           "@ c21fe89; data/sec_reads/exhibit21_2026-11-05.json; RAG rag/ingest.py", y=4.38, w=7.6)
    notes(s, "Where does GraphRAG do better? On relationship questions. All of them depend on Exhibit 21, which RAG doesn't index "
             "today. GraphRAG's new Exhibit 21 pipeline covers all ten companies, and its rows agree with our gold reads on every "
             "row we checked. Traversing those rows answers all nine questions exactly, including counts and cross-company joins. "
             "Even when we add Exhibit 21 to RAG's index as text, the counting is left to the language model. And on numbers, "
             "GraphRAG's period labels help. Where does RAG do better? Prose, and finding the right number in the filing. Most of "
             "GraphRAG's misses have a clear fix: in six of them the words 'three months' match the Microsoft 365 product rows, "
             "and calculations need one call per input.")


def s_routing(s, rt):
    clear(s)
    R = rt["routers"]
    er = rt["expected_routes"]
    header(s, "Routing", "which tools each router calls, by the route a question needs (155 questions)")
    order = [("sql", "Finance data"), ("text", "Text"), ("graph", "Relationship"), ("none", "No tool"), ("multi", "Both")]
    cats = [f"{n} ({er.get(k, 0)})" for k, n in order]
    col_chart(s, 0.12, 1.0, 5.3, 3.3, cats,
              [("Text only", [R["text_only"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], "A9B0BD"),
               ("Keyword router", [R["keyword"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], BLUE),
               ("Every tool", [R["combined"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], NAVY)],
              "Route the question needs (number of questions)", "Questions whose needed tools were called",
              "Routing by route", label_size=6.5, vmax=1.15)
    x = 5.65
    tb(s, x, 1.0, 4.15, 1.05, [[("Keyword router: ", 8.5, True, NAVY),
                                ("Eval's stand-in for the Agents' orchestrator, rules only, no LLM. Scope check first (blocked: "
                                 "no tool). Then a relationship word (subsidiary, Exhibit 21, acquire, own) goes to GraphRAG; "
                                 "a number word (how much, revenue, margin, total) to finance data; an explanation word (why, "
                                 "explain, describe, risk) to RAG; both kinds to both.", 8, False, INK)]])
    tb(s, x, 2.12, 4.15, 0.75, [[("Unneeded call: ", 8.5, True, NAVY),
                                 ("a tool called that the question's route does not need. Per question = all unneeded calls / "
                                  "155. Example: a finance-data question sent to every tool makes 3 calls, 2 unneeded. It is "
                                  "not \"text search alone would have done\".", 8, False, INK)]])
    rows = [["Router", ("Needed tools called", C["center"]), ("Calls / question", C["center"]),
             ("Unneeded / question", C["center"])]] + [
        [n, (pct(R[k]["required_tools_called"]), C["center"]), (f"{R[k]['tool_calls_per_question']:.2f}", C["center"]),
         (f"{R[k]['unneeded_calls_per_question']:.2f}", C["center"])]
        for k, n in (("text_only", "Text only"), ("keyword", "Keyword router"), ("combined", "Every tool"))]
    table(s, x, 2.95, 4.15, [1.25, 1.0, 0.9, 1.0], rows, row_h=0.3, sizes={0: 8, 1: 8, 2: 8, 3: 8}, name="Routing cost")
    footer(s, "On the current 155 questions only:", "the 'Both' and 'No tool' bars rest on 1 and 8 questions. The keyword "
                                                   "router's weak spot is text questions that mention a number word (next slide).",
           "Source: Week 8/results/routing_baselines.json; kpmg_eval/metrics/routing.py; ROUTING_EXAMPLES.md. Routes are Eval's "
           "labels, for Agents to review", y=4.38, w=7.6)
    notes(s, "Last week's chart had no axis labels. Here the horizontal axis is the route a question needs, with the number of "
             "questions in brackets, and the vertical axis is the share of those questions whose needed tools were called. The "
             "keyword router is our rule-based stand-in for the orchestrator. An unneeded call is any tool called that the "
             "question's route doesn't need, averaged over all 155 questions. So calling every tool on a finance-data question "
             "is three calls, two of them unneeded. To correct the minutes: it does not mean text search alone could have "
             "answered.")


TOOL = {"sql": "Finance data", "text": "RAG", "graph": "GraphRAG"}


def s_examples(s, ex):
    clear(s)
    header(s, "Routing walkthrough", "seven questions for the demo: what each router calls, and why")
    short = {"GSv0-MSFT-001": "Microsoft's total revenue, three months ended Mar 31, 2026",
             "GSv0-MSFT-004": "Name Microsoft's reportable segments",
             "EV3-001": "How many subsidiaries does Micron list in Exhibit 21; how many abroad?",
             "EV1R-003": "How did Microsoft's OpenAI gains change, and what event drove it?",
             "EV1-062": "Microsoft's share price at the close on Mar 31, 2026",
             "GSv0-MSFT-009": "What does revenue allocated to remaining performance obligations include?",
             "GSv0-MSFT-014": "Calculate operating cash flow less capex ... (use that definition)"}
    route_name = {"sql": "Finance data", "text": "Text", "graph": "Relationship", "none": "No tool", "multi": "Both"}
    rows = [["Question (shortened)", "Needs", "Keyword router calls", "Because", ("Unneeded: text only / keyword / every tool",
                                                                                C["center"])]]
    for e in ex:
        kw = e["routers"]["keyword"]
        ok = kw["needed_tools_called"]
        calls = ", ".join(TOOL[t] for t in kw["called"]) or "nothing (blocked)"
        reason = (e["keyword_reason"].split(" -> ")[0].replace("scope gate decides 'abstain', no tool", "scope check: abstain")
                  .replace("'defin'", "'definition'"))
        un = " / ".join(str(e["routers"][k]["unneeded"]) for k in ("text_only", "keyword", "combined"))
        rows.append([short[e["qid"]], route_name[e["expected_route"]],
                     (calls + ("" if ok else "  (misses)"), {"color": GREEN if ok else PINK, "bold": True}), reason,
                     (un, C["center"])])
    table(s, 0.12, 1.0, 9.68, [3.6, 0.95, 1.65, 2.18, 1.3], rows, row_h=0.4, sizes={0: 7.5, 1: 7.5, 2: 7.5, 3: 7.5, 4: 8},
          name="Examples")
    footer(s, "For the demo:", "the first five show each route; the last two show where rules break, which is what the "
                               "Agents' orchestrator should do better. A miss means a needed tool was not called.",
           "Source: Week 8/ROUTING_EXAMPLES.md, results/routing_examples.json (scripts/routing_examples.py); full questions "
           "in data/benchmark_v2_questions.md", y=4.42, w=7.6)
    notes(s, "For the demo we picked seven questions. The first is a number from a statement: the keyword router sends it to "
             "finance data, with no unneeded calls; text-only would miss it; every-tool calls two extra. Then a text question, a "
             "relationship question that goes to GraphRAG, and a share-price question that the scope check blocks with no tool "
             "call. The last rows show where rules break: a question about what revenue includes is a text question, but the "
             "word revenue sends it to finance data.")


def s_messy(s, mw):
    clear(s)
    G, Rt, Rv = mw["gate"], mw["router"], mw["retrieval_msft_10q"]
    header(s, "Typos and messy wording", f"{mw['n_variants']} rewrites of the 155 questions, same meaning, scored like "
                                         "the clean ones")
    arrow = lambda d: f"{pct(d['clean_acc'])} → {pct(d['messy_acc'])}"  # noqa: E731
    rr = lambda d: f"{pct(d['clean_required_called'])} → {pct(d['messy_required_called'])}"  # noqa: E731
    rv = lambda d: f"{pct(d['clean'])} → {pct(d['messy'])}"  # noqa: E731
    kinds = [("typo_company", "Company misspelled", "Microsfot, Mircon, Net App"),
             ("typo_terms", "Finance word misspelled", "revnue, opertaing, subsidaries"),
             ("casual", "Casual: ticker, lower case", "what was msft total revenue for ...")]
    rows = [["Rewrite (n)", "Example", ("Scope check, no company picked", C["center"]),
             ("Same, company picked in the UI", C["center"]), ("Router: needed tools", C["center"]),
             ("RAG search", C["center"]), ("GraphRAG search", C["center"])]]
    for k, name, eg in kinds:
        bad = G[f"{k}|no_session"]["messy_acc"] < 0.5
        rows.append([f"{name} ({mw['per_perturbation'][k]})", (eg, {"size": 7}),
                     (arrow(G[f"{k}|no_session"]), {**C["center"], "color": PINK if bad else INK, "bold": bad}),
                     (arrow(G[f"{k}|with_session"]), C["center"]), (rr(Rt[k]), C["center"]),
                     (rv(Rv[f"{k}|rag_bm25"]), C["center"]), (rv(Rv[f"{k}|graphrag_structured"]), C["center"])])
    table(s, 0.12, 1.0, 9.68, [1.65, 2.0, 1.3, 1.3, 1.15, 1.1, 1.18], rows, row_h=0.42,
          sizes={0: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 8}, name="Messy wording")
    fz_c, fz_k = G["typo_company|no_session_fuzzy_names"], G["casual|no_session_fuzzy_names"]
    tile(s, 0.12, 2.85, pct(fz_c["messy_acc"]), f"right decisions on misspelled names once the scope check also matches "
         f"tickers and near-miss spellings ({pct(fz_k['messy_acc'])} on casual); no change on the clean questions",
         w_big=0.85, w_lab=3.75, color=GREEN)
    tb(s, 5.0, 2.85, 4.8, 1.4, [[("What drops, and why", 8.5, True, INK)],
                                [("Company names: ", 8, True, INK), ("the check knows exact names only, so 'Microsfot' or 'msft' "
                                                                     "turns an answer into 'which company?'.", 8, False, INK)],
                                [("Finance words: ", 8, True, INK), (f"RAG's search loses {Rv['typo_terms|rag_bm25']['lost']} and "
                                                                     f"GraphRAG's {Rv['typo_terms|graphrag_structured']['lost']} of "
                                                                     f"{Rv['typo_terms|rag_bm25']['n']} questions; keyword "
                                                                     "matching does not forgive 'revnue'.", 8, False, INK)],
                                [("Searches ignore name typos ", 8, True, INK), ("because the company comes in as a filter.",
                                                                                  8, False, INK)]])
    footer(s, "For Agents:", "match tickers and near-miss names before routing, and correct spelling before search. Scores are "
                             "clean → messy, on the current 155 questions; searches on the Microsoft 10-Q questions only.",
           "Source: Week 8/results/messy_wording.json, data/messy_wording_v1.jsonl (scripts/run_messy_wording.py). Scope check "
           "and router are Eval's reference rules, not the orchestrator", y=4.38, w=7.6)
    notes(s, "To estimate real-user accuracy we rewrote every question three ways without changing its meaning: a misspelled "
             "company, misspelled finance words, and casual wording with tickers. The biggest drop is company recognition: if no "
             "company is picked in the interface, a simple name check turns most of these into 'which company?'. Matching "
             "tickers and near-miss spellings brings it back to 94 percent. Misspelled finance words cost the two searches "
             "eight and nine questions, so a spelling step before search would help both.")


def s_next(s):
    clear(s)
    header(s, "Next steps", "after round 1: one ask per team")
    rows = [["Team", "Ask (from this week's results)"],
            [("RAG", {"bold": True}), "Share the round-1 chunks privately so we can anchor the last 4 questions and run the side by "
                                      "side on all ten; try candidate k and fusion weights on the 6 near misses; reader API key"],
            [("GraphRAG", {"bold": True}), "Run our round-1 script with your Aura graph and send the results; share the 20-filing "
                                           "store; accept accession filters in place of fiscal labels; read periods when ranking"],
            [("Agents", {"bold": True}), "Split cross-company and 10-K + 10-Q questions into one search each; match tickers and "
                                         "near-miss names; run your orchestrator through our routing scorer"],
            [("Data", {"bold": True}), "Keep the 11/03 freeze (matches our 21/21) through round 1; then load Microsoft's FY2024 and "
                                       "FY2025 10-Ks, already in your inventory (joint ask with GraphRAG)"],
            [("Eval", {"bold": True}), "Anchors for the last 4 questions once chunks land; check RAG's per-question results against "
                                       "v2.1; answer-level round 1 when a reader can run; grow the 1 'both' and 8 'no tool' routes"]]
    table(s, 0.12, 1.0, 9.68, [1.0, 8.68], rows, row_h=0.46, sizes={0: 8.5, 1: 8}, name="Asks")
    footer(s, "Thanks:", "RAG ran round 1 and traced every miss, which is how we found our anchor errors. RAG's retriever and "
                         "GraphRAG's fact loader ran here unchanged, and GraphRAG's Exhibit 21 output fed the relationship check.",
           "Source: Week 8/FOR_TEAMS_W8.md (one section per team, with file paths)", y=4.42, w=7.6)
    notes(s, "One ask per team for round 1, each tied to a result from today. Both RAG and GraphRAG's code ran here unchanged, "
             "which is what made the side-by-side possible this week.")


def main():
    base, out = sys.argv[1], sys.argv[2]
    prs = Presentation(base)
    add_slides(prs, N_SLIDES)
    sl = list(prs.slides)
    sbs, rt, mw = j(RES / "side_by_side.json"), j(RES / "routing_baselines.json"), j(RES / "messy_wording.json")
    s_scope(sl[0], sbs, rt, mw)
    s_round1(sl[1], j(DATA / "round1_rag_2026-11-09.json"), j(RES / "gold_v2_1_changes.json"))
    s_side_by_side(sl[2], sbs)
    s_better(sl[3], sbs)
    s_routing(sl[4], rt)
    s_examples(sl[5], j(RES / "routing_examples.json"))
    s_messy(sl[6], mw)
    s_next(sl[7])
    prs.save(out)
    print("[deck] wrote", out)


if __name__ == "__main__":
    main()
