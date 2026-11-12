"""Evaluation & Testing slides for the week-8 KPMG x Columbia meeting (11/12), in the team deck's template.

    python scripts/build_deck_w8.py <base.pptx> <out.pptx>

Final version (11/11): rebuilt to consulting-deck standards after round 1.
  * every slide title states the conclusion ("Topic | takeaway"), with one message per slide
  * executive summary first, then the 11/5 feedback tracker, the evidence slides, next steps, and an appendix
  * each slide ends with a "So what" line and a source line; each has speaker notes (the script)
Every number is read from results/*.json, so re-running run_all.sh and this script keeps the slides in sync with the
code. Charts and tables are native PowerPoint objects. Base: any deck whose slides are the team's Evaluation & Testing
slide (slides are added by copying the first one).
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_style import BLUE, GREEN, INK, MUTED, NAVY, NS_A, PINK, SUB, clear, j, notes, rgb, table, tb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES, DATA = ROOT / "results", ROOT / "data"
N_SLIDES = 14
C = {"center": {"align": PP_ALIGN.CENTER}}
X0, W, Y0 = 0.2, 9.6, 1.22          # left edge, content width, content top
TINT, GREY = "F1F3FB", "A9B0BD"
DECK = "Evaluation & Testing  ·  Week 8  ·  12 Nov 2026"


def pct(x, nd=0):
    return f"{x * 100:.{nd}f}%"


def kn(d):
    return f"{d['k']}/{d['n']}"


def hn(d):
    return f"{d['hits']}/{d['n']}"


# ---------------------------------------------------------------- frame: title, so-what, source, page tag
def frame(slide, n, topic, message, so_what, source, lead="So what:"):
    """Action title (topic | conclusion), the 'so what' box, the source line and the page tag in the bottom bar."""
    clear(slide)
    tb(slide, X0, 0.6, W, 0.5, [(f"{topic} | ", 13, True, SUB, True), (message, 13, True, SUB, True)], name="Action title")
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(X0), Inches(4.38), Inches(7.45), Inches(0.5))
    box.name = "So what box"
    box.adjustments[0] = 0.12
    box.fill.solid()
    box.fill.fore_color.rgb = rgb("EEF1FA")
    box.line.fill.background()
    box.shadow.inherit = False
    tb(slide, X0 + 0.12, 4.38, 7.2, 0.5, [(lead + " ", 9, True, NAVY), (so_what, 9, False, INK)],
       anchor=MSO_ANCHOR.MIDDLE, name="So what")
    tb(slide, X0, 4.95, 7.45, 0.3, [(source, 7, False, MUTED)], name="Source")
    tb(slide, X0, 5.41, 6.0, 0.16, [(DECK, 7, False, "FFFFFF")], name="Deck tag")
    tb(slide, 9.2, 5.41, 0.6, 0.16, [(str(n), 7.5, True, "FFFFFF")], align=PP_ALIGN.RIGHT, name="Page")


def card(slide, x, y, w, h, big, lab, color=NAVY, big_size=22, lab_size=8.5):
    """Stat card: a big number over a short label, on a light tint."""
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(TINT)
    shp.line.fill.background()
    shp.shadow.inherit = False
    tb(slide, x + 0.12, y + 0.07, w - 0.24, 0.38, [(big, big_size, True, color)], anchor=MSO_ANCHOR.MIDDLE)
    tb(slide, x + 0.12, y + 0.48, w - 0.24, h - 0.52, [(lab, lab_size, False, INK)])


def panel(slide, x, y, w, h):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.05
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(TINT)
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def head(slide, x, y, w, text, color=NAVY, size=10):
    tb(slide, x, y, w, 0.2, [(text, size, True, color)])


def bullets(slide, x, y, w, h, items, size=9, gap=4):
    """Real bullets (hanging indent). items: str, or a list of (text, bold) runs."""
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        for text, bold in (it if isinstance(it, list) else [(it, False)]):
            r = p.add_run()
            r.text = text
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = "Arial", Pt(size), bold, rgb(INK)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(0.14 * 914400)))
        pPr.set("indent", str(-int(0.14 * 914400)))
        etree.SubElement(pPr, f"{{{NS_A}}}buChar").set("char", "•")
    return s


# ---------------------------------------------------------------- charts (one look for every chart in the deck)
def _style(ch, plot, series, fmt, label_size):
    ch.font.name, ch.font.size = "Arial", Pt(8)
    ch.font.color.rgb = rgb(INK)
    ch.has_title = False
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.color.rgb = Pt(label_size), rgb(INK)
    for s, (_, _, col) in zip(plot.series, series):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = rgb(col)


def _axes(ch, fmt, vmax, xtitle, ytitle, unit=None):
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale = 0, vmax
    if unit:
        va.major_unit = unit
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E7F0")
    va.format.line.fill.background()
    va.tick_labels.font.size, va.tick_labels.font.color.rgb = Pt(7.5), rgb(MUTED)
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = fmt, False
    ca = ch.category_axis
    ca.format.line.color.rgb = rgb("C9CED8")
    ca.tick_labels.font.size = Pt(8)
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    for axis, title in ((va, ytitle), (ca, xtitle)):
        axis.has_title = bool(title)
        if title:
            tf = axis.axis_title.text_frame
            tf.text = title
            r = tf.paragraphs[0].runs[0]
            r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(8), True, rgb(MUTED), "Arial"


def col_chart(slide, x, y, w, h, cats, series, xtitle, ytitle, name, fmt="0%", vmax=1.15, label_size=8, legend=True,
              gap=60):
    """Clustered columns with both axes titled. series = [(name, values, colour)]."""
    cd = CategoryChartData()
    cd.categories = cats
    for n, vals, _ in series:
        cd.add_series(n, vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    gf.name = name
    ch = gf.chart
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = gap, -10
    _style(ch, plot, series, fmt, label_size)
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(8)
    _axes(ch, fmt, vmax, xtitle, ytitle, unit=0.2 if vmax > 1 else None)
    return gf


def bar_chart(slide, x, y, w, h, cats, vals, colors, xtitle, name, vmax):
    """Horizontal bars, one series, counts; first category at the top. colors: one per bar."""
    cd = CategoryChartData()
    cd.categories = cats[::-1]
    cd.add_series("Questions", vals[::-1])
    gf = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    gf.name = name
    ch = gf.chart
    plot = ch.plots[0]
    plot.gap_width = 45
    _style(ch, plot, [("", None, NAVY)], "0", 8)
    for i, col in enumerate(colors[::-1]):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(col)
    ch.has_legend = False
    _axes(ch, "0", vmax, None, xtitle, unit=2)
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


# ================================================================ 1. executive summary
def s_summary(s, n, D):
    r1, v22, gs, G = D["r1"]["hybrid_k10"], D["v22"], D["gr"]["structured|translated"], D["mw"]["gate"]
    frame(s, n, "Executive summary",
          "Round 1 ran with all four teams: answers are right when the evidence is found, and each remaining gap has a "
          "named owner",
          "Round 1 gives every team a measured baseline on the same 155 questions, so next week we measure the fixes "
          "instead of debating them.",
          "Source: round-1 files from RAG (11/9, 11/11) and GraphRAG (11/11), re-scored by Eval on Gold Set v2.2 "
          "(155 questions). Detail on the following slides; definitions in the appendix")
    cw, gap = 2.25, 0.2
    cards = [(f"{r1['hits']}/{r1['n']}", f"questions where RAG's search finds all the evidence ({pct(r1['hits'] / r1['n'])})", NAVY),
             (kn(v22["numeric_accuracy"]), f"numbers right in RAG's answers ({v22['numeric_accuracy']['value']:.3f}), scored "
                                           "by our graders", NAVY),
             (v22["refusal"]["unanswerable_refused"], "unanswerable questions correctly refused by RAG's reader", GREEN),
             (f"{gs['numbers']['hits']} → {gs['top1_right']['hits']}", f"of {gs['numbers']['n']} number questions: GraphRAG has "
                                                                      "the right number in its top 10 → ranks it first", PINK)]
    for i, (big, lab, col) in enumerate(cards):
        card(s, X0 + i * (cw + gap), Y0, cw, 0.98, big, lab, col)
    cols = [("What we did", [
                "Ran round 1 with RAG (twice) and GraphRAG (both searches), and reproduced every score from their files",
                "Released Gold Set v2.2: the same 155 questions with fairer grading",
                "Closed all 11/5 feedback and connected the Agents' new API to our grader"]),
            ("What we found", [
                "RAG finds and reads numbers well; 13 of its 16 declined questions are outside its reach today",
                "GraphRAG's gap is ranking and scope, not data: its graph search finds 10 of the 20 answers it holds",
                f"Misspelled company names break the scope check ({pct(G['typo_company|no_session']['clean_acc'])} → "
                f"{pct(G['typo_company|no_session']['messy_acc'])}) unless matched loosely "
                f"({pct(G['typo_company|no_session_fuzzy_names']['messy_acc'])})"]),
            ("What we need next week", [
                [("RAG: ", True), ("run our narrative judge", False)],
                [("GraphRAG: ", True), ("ranking fix; Exhibit 21 in the graph", False)],
                [("Agents: ", True), ("first run of the 155 questions", False)],
                [("Data: ", True), ("Microsoft's FY2024 and FY2025 10-Ks", False)]])]
    cx, cg = 3.05, 0.225
    for i, (h, items) in enumerate(cols):
        x = X0 + i * (cx + cg)
        head(s, x, 2.42, cx, h, size=10.5)
        bullets(s, x, 2.7, cx, 1.6, items, size=9.5, gap=5)
    notes(s, "The short version. Round 1 ran this week with every team. RAG's search finds all the evidence for 105 of 124 "
             "questions, and when it does, its reader gets 89 of 94 numbers right and refuses all 12 unanswerable questions. "
             "GraphRAG already has the right number in its top ten for 63 of 93 questions and ranks it first for 26, which is "
             "the ranking work they have open. We reproduced every score ourselves from the teams' files, fixed our grading "
             "where RAG showed us it was unfair, and closed last week's feedback. On the right is one ask per team for next "
             "week. The rest of the deck is the evidence behind these lines.")


# ================================================================ 2. feedback tracker
def s_tracker(s, n, D):
    sbs, rt, mw = D["sbs"], D["rt"], D["mw"]
    a, b, er, R = sbs["part_a"], sbs["part_b"], rt["expected_routes"], rt["routers"]
    frame(s, n, "Feedback from 11/5",
          "All seven action items are closed, each with a script and a result file in the Week 8 folder",
          "Two corrections matter most for reading last week's chart: the bars show coverage, not accuracy, and the 95% "
          "is calling every tool, not the keyword router.",
          "Source: 11/5 meeting minutes (#6) and mentor feedback; Week 8/README.md maps each item to its script and "
          "result file")
    done = ("Done", {**C["center"], "bold": True, "color": GREEN})
    rows = [["Action item", "What we did", ("Status", C["center"])],
            ["Run round 1 in week 8", "RAG (11/9, 11/11) and GraphRAG (11/11) ran our scoring; we reproduced both", done],
            ["Compare RAG and GraphRAG side by side; show where each does better",
             f"{a['n_questions']} Microsoft 10-Q questions through each team's own code, plus {b['n_questions']} relationship "
             "questions", done],
            ["Label the routing chart; define the keyword router and unneeded calls",
             "Axes titled; both terms defined on the slide with a worked example", done],
            ["Coverage vs accuracy; match each number to its method",
             f"Corrected: every tool {pct(R['combined']['coverage'])}, keyword router {pct(R['keyword']['coverage'])}; "
             "coverage is not answer accuracy", done],
            ["Concrete routing examples; where the router sits", "Three real questions walked through; the keyword router is "
                                                                 "our baseline, not part of the pipeline", done],
            ["State that results are on the current 155 questions only", "Stated on every slide that reports a rate", done],
            ["Test typos and messy wording", f"{mw['n_variants']} rewrites of the 155 questions, scored like the originals", done]]
    table(s, X0, Y0, 7.5, [2.75, 4.05, 0.7], rows, row_h=0.37, sizes={0: 8.5, 1: 8.5, 2: 8.5}, name="Action items")
    panel(s, 7.9, Y0, 1.9, 2.96)
    head(s, 8.02, Y0 + 0.1, 1.66, "How to read every number", size=9.5)
    tb(s, 8.02, Y0 + 0.5, 1.66, 2.3,
       [[(f"All figures use the current {rt['n']} questions (Gold Set v2.2).", 8.5, True, INK)], [(" ", 4, False, INK)],
        [(f"{er['sql']} finance data, {er['text']} text, {er['graph']} relationship, {er['none']} no tool, {er['multi']} both. "
          "Microsoft has 92 of them.", 8.5, False, INK)], [(" ", 4, False, INK)],
        [("Small groups are examples, not estimates. Rates will move as questions are added.", 8.5, False, INK)]])
    notes(s, "Last week's minutes gave us seven items, and all seven are closed. Each one has a script and a result file in the "
             "Week 8 folder, so anyone can re-run it. Two corrections from last week matter most. The routing bars show "
             "coverage, meaning the right tools were called; that is not answer accuracy. And the 95 percent belongs to "
             "calling every tool on every question, not to the keyword router. One caveat for everything that follows: the "
             "numbers come from the 155 questions we have now, which lean on Microsoft and on finance-data questions.")


# ================================================================ 3. round 1: RAG retrieval
def s_retrieval(s, n, D):
    r1, v21 = D["r1"], D["v21"]
    R, h, w = r1["strict_recall"], r1["hybrid_k10"], r1["wrong_period_figure_in_top8"]
    frame(s, n, "Round 1: RAG retrieval",
          f"RAG's hybrid search finds all the evidence for {h['hits']} of {h['n']} questions, and every miss has a named fix",
          f"A wrong-period figure sits in the same top 8 for {pct(w['rate'])} of the {w['of_number_questions_with_distractor']} "
          "number questions that have one, so the reader must be told which column to take.",
          "Source: RAG team, round-1 retrieval run 11/9 with Eval's scoring rules (Week 8/data/round1_rag_2026-11-09.json). "
          "Retrieval only; a hit must come from the right filing")
    col_chart(s, X0, Y0, 4.3, 3.05, ["Top 5", "Top 8", "Top 10"],
              [("Hybrid", [R["hybrid"][f"k{k}"] for k in (5, 8, 10)], NAVY),
               ("Keyword (BM25)", [R["bm25"][f"k{k}"] for k in (5, 8, 10)], BLUE),
               ("Dense", [R["dense"][f"k{k}"] for k in (5, 8, 10)], GREY),
               ("Hybrid, no filter", [R["hybrid_no_filter"][f"k{k}"] for k in (5, 8, 10)], PINK)],
              "Results kept per question", "Questions with all evidence found", "Round 1 retrieval", label_size=6.5)
    x = 4.7
    n_mu = r1["non_msft_single_company"]
    card(s, x, Y0, 2.45, 0.86, f"{h['numbers'][0]}/{h['numbers'][1]}", f"number questions found; text questions "
         f"{h['prose'][0]}/{h['prose'][1]}", NAVY)
    card(s, x + 2.65, Y0, 2.45, 0.86, f"{n_mu[0]}/{n_mu[1]}", "on the nine other companies: adding them did not hurt "
         "retrieval", GREEN)
    short = ["Cross-company ranking: one search cannot hold ten companies",
             "Our own anchors were wrong (four questions)",
             "Needs the 10-K and the 10-Q together",
             "Found by both methods; merging pushed it past 10",
             "Missed by all three methods"]
    fix = ["Agents: one search per company", None, "Agents: one search per form", "RAG: merge weights, keep more results",
           "RAG: ranking"]
    rows = [[f"Why {h['n'] - h['hits']} were missed", ("n", C["center"]), "Fix and owner"]]
    for m, sh, o in zip(r1["misses_by_cause"], short, fix):
        rows.append([sh, (str(m["n"]), C["center"]),
                     (f"Eval: fixed, with all {v21['reanchored_from_region']} similar anchors", {"bold": True, "color": GREEN})
                     if m["owner"] == "Eval" else o])
    table(s, x, 2.24, 5.1, [2.55, 0.35, 2.2], rows, row_h=0.33, sizes={0: 8, 1: 8, 2: 8}, name="Misses")
    notes(s, "Round 1 retrieval. RAG ran our scoring rules on the full question set against its index of the 20 filings. "
             "Hybrid search finds all the evidence for 105 of 124 scored questions when it keeps ten results, and the nine "
             "non-Microsoft companies score at least as well as Microsoft. RAG traced every one of the 19 misses, which was "
             "a real help. Four were our mistake: anchors from an automatic conversion that did not match the question. We "
             "fixed those and all 22 similar ones the same day. Three are cross-company rankings that one search cannot "
             "hold, so the Agents should search once per company. The rest are ranking and merging fixes on the RAG side.")


# ================================================================ 4. round 1: RAG answers
def s_answers(s, n, D):
    v2, v22 = D["v2"], D["v22"]
    sub, c, nar = v2["rag_subset"], v22["citations"], v22["narrative"]
    n_ref = len(v22["refusal"]["answerable_refused"])
    frame(s, n, "Round 1: RAG answers",
          f"With the evidence found, RAG's reader gets {v22['numeric_accuracy']['k']} of {v22['numeric_accuracy']['n']} "
          f"numbers right and refuses all {v22['refusal']['n_unanswerable']} unanswerable questions",
          f"Only 3 of the {n_ref} declined questions are RAG's own to fix; the rest wait on Exhibit 21, one held filing "
          "and per-company search. Narrative scores come next.",
          "Source: RAG's 155 answers (11/11) graded by Eval, Week 8/results/answers_rag_reader_round1.json. Gold Set v2.2; "
          "RAG's answers and passages stay private")
    cw, gap = 2.25, 0.2
    cards = [(kn(v22["numeric_accuracy"]), f"numbers right ({v22['numeric_accuracy']['value']:.3f}); "
                                           f"{kn(v2['numeric_accuracy'])} before our grading fixes", NAVY),
             (v22["refusal"]["unanswerable_refused"], "unanswerable questions refused; balanced refusal score "
                                                      f"{v22['refusal']['balanced_raa_incl_false_premise']:.3f}", GREEN),
             (kn(v22["false_premise_corrected"]), "false-premise questions corrected instead of answered as asked", NAVY),
             (kn(c["lookup_number_in_cited_chunk"]), f"lookups show the number in a cited passage; all "
                                                     f"{c['cited_ids_found_in_chunks']['n']} citations exist", NAVY)]
    for i, (big, lab, col) in enumerate(cards):
        card(s, X0 + i * (cw + gap), Y0, cw, 0.98, big, lab, col)
    head(s, X0, 2.36, 5.3, f"Why {n_ref} answerable questions were declined (blue = RAG's own to fix)")
    bar_chart(s, X0, 2.56, 5.3, 1.72,
              ["Needs Exhibit 21 (GraphRAG's route)", "Needs NetApp's 10-Q (held by Data)", "Cross-company ranking",
               "Answer stated, marked not answered", "Retrieval miss"],
              [7, 3, 3, 2, 1], [GREY, GREY, GREY, BLUE, BLUE], "Questions", "Declined questions", vmax=8)
    head(s, 5.75, 2.36, 4.05, "How we checked")
    bullets(s, 5.75, 2.61, 4.05, 1.6, [
        f"Reproduced RAG's own figures exactly on its subset: numbers {sub['numeric_accuracy']['value']:.3f}, refusal "
        f"{sub['refusal']['balanced_raa_incl_false_premise']:.3f}, unanswerable {sub['refusal']['unanswerable_refused']}",
        "RAG's three grading notes were right; all are fixed in Gold Set v2.2 (appendix)",
        f"{nar['n'] - nar['refused']} of {nar['n']} narrative questions were answered; scoring them waits for the LLM "
        "judge, which is built and needs an API key"], size=9, gap=4)
    notes(s, "Two days later RAG ran its reader end to end and scored it with our graders. First we reproduced their numbers "
             "exactly. On all 155 questions, the reader gets 89 of 94 numbers right and refuses all 12 unanswerable "
             "questions. Citations hold up: every cited passage exists, and 58 of 59 lookups show the number in a cited "
             "passage. RAG also sent three grading notes, and all three were right, so we fixed our grading; that is Gold "
             "Set v2.2 in the appendix. The chart shows why 16 answerable questions were declined. Thirteen are outside "
             "RAG's reach today: seven need Exhibit 21, three need a NetApp filing that Data is still reviewing, and three "
             "are cross-company rankings. Only three are RAG's own. Narrative answers are next; the judge is ready.")


# ================================================================ 5. round 1: GraphRAG
def s_graphrag(s, n, D):
    st, gt, chk = D["gr"]["structured|translated"], D["gr"]["graph|translated"], D["chk"]
    gs, rp = chk["graph_prose_by_scope"], chk["reproduction_structured_translated"]
    n_out = gs["outside_scope"]["n"] + gs["not_in_corpus_or_chunks"]["n"]
    frame(s, n, "Round 1: GraphRAG",
          f"The right number is already in the top 10 for {st['numbers']['hits']} of {st['numbers']['n']} questions; ranking "
          f"it first ({st['top1_right']['hits']} today) is the open step",
          "Two levers: rank by period and break ties (GraphRAG's own issue #68), and add the notes to the statements to "
          "the graph. The data is already there.",
          "Source: GraphRAG team, round 1 on its Aura graph and 20-filing store (11/11), re-run by Eval: "
          "Week 8/results/graphrag_round1_check.json. Retrieval only")
    head(s, X0, Y0, 3.1, f"Number search: {st['numbers']['n']} number questions", size=9.5)
    col_chart(s, X0, Y0 + 0.22, 3.1, 2.85, ["Right number in the top 10", "Right number ranked first"],
              [("Number search", [st["numbers"]["rate"], st["top1_right"]["rate"]], NAVY)],
              None, "Share of questions", "GraphRAG number search", legend=False, gap=90)
    head(s, 3.5, Y0, 3.1, f"Graph search: {gt['prose']['n']} text questions", size=9.5)
    col_chart(s, 3.5, Y0 + 0.22, 3.1, 2.85,
              [f"Text in sections the graph holds ({gs['in_scope']['n']})", f"Text outside them ({n_out})"],
              [("Graph search", [gs["in_scope"]["hits"] / gs["in_scope"]["n"], 0.0], PINK)],
              None, "Share with the needed text found", "GraphRAG graph search", legend=False, gap=90)
    panel(s, 6.8, Y0, 3.0, 2.98)
    head(s, 6.92, Y0 + 0.1, 2.76, "What we checked", size=9.5)
    bullets(s, 6.92, Y0 + 0.38, 2.76, 2.5, [
        f"Our rerun on GraphRAG's own 20-filing store matches its results on all {rp['questions_identical']} questions",
        "Its fix #70, merged the same day, removed all 10 errors on cross-company questions",
        f"The graph holds five section types; {gs['outside_scope']['n']} more answers sit in the notes to the "
        "statements, and 8 in Exhibit 21 or NetApp's 10-Q",
        "Dropped database connections are retried, never scored against GraphRAG"], size=9.5, gap=6)
    notes(s, "GraphRAG ran both of its searches on all 155 questions with our script, the same day we asked. For number "
             "questions, the right number is already in its top ten for 63 of 93, but ranked first for only 26. GraphRAG "
             "named that gap itself as issue 68, so the fix is ranking, not data. Its graph search was scored for the first "
             "time: 10 of 38 text questions. But the graph only holds five section types, and when the answer sits in one "
             "of those sections it finds 10 of 20. The other 18 are outside the graph today: ten in the notes to the "
             "financial statements, eight in Exhibit 21 or a filing Data is still reviewing. We re-ran their number search "
             "on their own store and matched every question.")


# ================================================================ 6. RAG vs GraphRAG
def s_compare(s, n, D):
    a, b = D["sbs"]["part_a"], D["sbs"]["part_b"]
    r, g = a["summary"]["rag_bm25"], a["summary"]["graphrag_structured"]
    frame(s, n, "RAG vs GraphRAG",
          "On the same filing RAG finds more of the evidence, GraphRAG is more exact about the period, and relationship "
          "questions need GraphRAG",
          "Route relationship questions to GraphRAG and explanations to RAG. Numbers can use either once GraphRAG's "
          "ranking fix lands, with its period labels as the check.",
          f"Source: Week 8/results/side_by_side.json: the same {a['n_questions']} Microsoft 10-Q questions through each "
          "team's own code, top 8 results. Retrieval only, no reader model")
    cats = [f"Numbers found ({r['numbers']['n']})", f"Text found ({r['prose']['n']})",
            f"Wrong-period number also shown; lower is better ({r['distractor_shown_on_numbers']['n']})"]
    col_chart(s, X0, Y0, 5.2, 3.05, cats,
              [("RAG (keyword search)", [r["numbers"]["rate"], r["prose"]["rate"], r["distractor_shown_on_numbers"]["rate"]], BLUE),
               ("GraphRAG (number search)", [g["numbers"]["rate"], g["prose"]["rate"], g["distractor_shown_on_numbers"]["rate"]], PINK)],
              "Question group (number of questions)", "Share of questions", "Side by side")
    x = 5.6
    rows = [["", "Better at", "Evidence"],
            [("RAG", {"bold": True, "color": BLUE}), "Finding the right number", f"{hn(r['numbers'])} vs {hn(g['numbers'])}"],
            ["", "Text and explanations", f"{hn(r['prose'])} vs {hn(g['prose'])}: number search holds numbers only"],
            [("GraphRAG", {"bold": True, "color": PINK}), "Exact periods on numbers",
             f"Wrong-period number shown {pct(g['distractor_shown_on_numbers']['rate'])} vs "
             f"{pct(r['distractor_shown_on_numbers']['rate'])}"],
            ["", "Relationship questions", f"{b['graph_correct']}/{b['n_questions']} exact by walking its subsidiary rows; "
                                           "RAG does not index Exhibit 21"]]
    table(s, x, Y0, 4.2, [0.8, 1.5, 1.9], rows, row_h=0.42, sizes={0: 8.5, 1: 8.5, 2: 8}, name="Better at")
    tb(s, x, 3.45, 4.2, 0.8, [[("Neither search returns an empty result ", 8.5, True, INK),
                               (f"on the {g['returned_nothing_on_unanswerable']['n']} unanswerable Microsoft questions, so the "
                                "decision to abstain belongs to the Agents' evidence check.", 8.5, False, INK)]])
    notes(s, "Last week you asked for the two systems side by side. We ran all 84 Microsoft 10-Q questions through each "
             "team's own code on the same filing, and checked whether the returned evidence holds what the answer needs. "
             "RAG finds the numbers for 49 of 50 questions, GraphRAG for 25, and only RAG returns text. GraphRAG's strength "
             "is in the third pair of bars: its facts carry their exact period, so a wrong-period number shows up about "
             "half as often. And all nine relationship questions are answered exactly by walking GraphRAG's subsidiary "
             "rows, which RAG does not index. So the two are complementary: relationships to GraphRAG, explanations to RAG.")


# ================================================================ 7. routing
def s_routing(s, n, D):
    rt = D["rt"]
    R, er = rt["routers"], rt["expected_routes"]
    frame(s, n, "Routing",
          f"Coverage is not accuracy: calling every tool covers {pct(R['combined']['coverage'])} of questions at 3 calls "
          f"each, the keyword router {pct(R['keyword']['coverage'])} at about 1",
          "Coverage rewards calling more tools, so always read it next to calls per question. Answer accuracy is measured "
          "separately, in round 1.",
          f"Source: Week 8/results/routing_baselines.json, {rt['n']} questions (Gold Set v2.2). Needed tools are Eval's "
          "labels, for the Agents to review. 'Both' and 'No tool' rest on "
          f"{er.get('multi', 0)} and {er.get('none', 0)} questions")
    order = [("sql", "Finance data"), ("text", "Text"), ("graph", "Relationship"), ("none", "No tool"), ("multi", "Both")]
    cats = [f"{nm} ({er.get(k, 0)})" for k, nm in order]
    col_chart(s, X0, Y0, 5.2, 3.05, cats,
              [("Text search only", [R["text_only"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], GREY),
               ("Keyword router", [R["keyword"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], BLUE),
               ("Every tool", [R["combined"]["required_tools_called_by_route"].get(k, 0) for k, _ in order], NAVY)],
              "Tool the question needs (number of questions)", "Coverage: needed tools were called", "Routing by route",
              label_size=6.5)
    x = 5.6
    tb(s, x, Y0, 4.2, 0.78, [[("Coverage ", 9, True, NAVY),
                              ("= share of questions where every tool the question needs was called. ", 9, False, INK),
                              ("It is not accuracy: ", 9, True, PINK),
                              ("calling the right tool does not make the final answer right.", 9, False, INK)]])
    rows = [["Method", ("Coverage", C["center"]), ("Calls per question", C["center"]), ("Unneeded calls", C["center"])]] + [
        [(nm, {"bold": True}), (pct(R[k]["coverage"]), C["center"]), (f"{R[k]['tool_calls_per_question']:.2f}", C["center"]),
         (f"{R[k]['unneeded_calls_per_question']:.2f}", C["center"])]
        for k, nm in (("text_only", "Text search only"), ("keyword", "Keyword router"), ("combined", "Every tool"))]
    table(s, x, 2.08, 4.2, [1.35, 0.9, 0.95, 1.0], rows, row_h=0.31, sizes={0: 8.5, 1: 8.5, 2: 8.5, 3: 8.5}, name="Routing cost")
    tb(s, x, 3.42, 4.2, 0.85, [[("Unneeded call ", 9, True, NAVY),
                                ("= a tool called that the question does not need. Total revenue needs finance data only, so "
                                 "calling every tool makes 3 calls and 2 are unneeded.", 9, False, INK)]])
    notes(s, "Two corrections from last week. The bars are coverage, not accuracy. Coverage is the share of questions where "
             "every tool the question needs was called. If a question needs finance data and the method calls finance data, "
             "that counts, even if the final answer later turns out wrong. So 95 percent coverage does not mean 95 of 100 "
             "answers are right. Second, the 95 percent comes from calling every tool on every question; it misses only the "
             f"{er.get('none', 0)} questions that should be blocked with no tool. The keyword router alone covers "
             f"{R['keyword']['coverage'] * 100:.0f} percent. That was 84 last week; two questions moved from relationship to "
             "text after round 1. The table is the cost side: every tool makes 3 calls per question, about 2 of them "
             "unneeded. The keyword router makes about 1.")


TOOL = {"sql": "Finance data", "text": "RAG", "graph": "GraphRAG"}


# ================================================================ 8. routing walkthrough
def s_examples(s, n, D):
    by = {e["qid"]: e for e in D["ex"]}
    frame(s, n, "Routing walkthrough",
          "Three real questions show the trade-off: calling every tool always covers but wastes two calls, while keyword "
          "rules are cheap but can slip",
          "The keyword router is Eval's baseline, not part of the pipeline. The Agents' orchestrator does the real "
          "routing and can be scored on the same 155 questions with one command.",
          "Source: Week 8/results/routing_examples.json; seven worked examples in ROUTING_EXAMPLES.md. For the Agents: "
          "scripts/run_routing_baselines.py --router name=module.py:route")
    picks = [("GSv0-MSFT-001", "1. A number from a statement",
              "What was Microsoft's total revenue for the three months ended March 31, 2026?"),
             ("EV3-001", "2. A relationship question",
              "How many subsidiaries does Micron list in Exhibit 21, and how many are outside the US?"),
             ("GSv0-MSFT-009", "3. Where keyword rules slip",
              "What does revenue allocated to remaining performance obligations include?")]
    need_name = {"sql": "finance data", "text": "RAG text search", "graph": "GraphRAG"}
    method = {"text_only": "Text only", "keyword": "Keyword", "combined": "Every tool"}
    cw, gap = 3.05, 0.225
    for i, (qid, title, q) in enumerate(picks):
        e = by[qid]
        x = X0 + i * (cw + gap)
        head(s, x, Y0, cw, title)
        tb(s, x, Y0 + 0.26, cw, 0.5, [[(f"“{q}”", 8.5, False, INK, True)]])
        tb(s, x, Y0 + 0.8, cw, 0.2, [[("Needs: ", 8.5, True, INK), (", ".join(need_name[t] for t in e["needs"]), 8.5, False, INK)]])
        rows = [["Method", "Calls", ("Covered", C["center"]), ("Unneeded", C["center"])]]
        for k in ("text_only", "keyword", "combined"):
            r = e["routers"][k]
            ok = r["needed_tools_called"]
            rows.append([(method[k], {"bold": True}),
                         ", ".join(TOOL[t] for t in ("sql", "text", "graph") if t in r["called"]) or "none",
                         ("yes" if ok else "no", {**C["center"], "bold": True, "color": GREEN if ok else PINK}),
                         (str(r["unneeded"]), C["center"])])
        table(s, x, Y0 + 1.08, cw, [0.7, 1.03, 0.6, 0.72], rows, row_h=0.36, sizes={0: 8, 1: 7.5, 2: 8, 3: 8},
              name=f"Example {i + 1}")
        why = e["keyword_reason"].replace("->", "→").replace("SQL", "finance data")
        tb(s, x, Y0 + 2.62, cw, 0.4, [[("Keyword router: ", 8, True, MUTED), (why, 8, False, MUTED)]])
    notes(s, "You asked for concrete examples, so here are three real questions. First, Microsoft's total revenue for the "
             "quarter. It needs finance data. Text search alone calls RAG, which is not the tool it needs. The keyword "
             "router sees the word total and calls finance data: covered, nothing wasted. Every tool also covers it, but "
             "makes two calls it does not need. Second, Micron's subsidiaries. It needs GraphRAG. Text only misses; the "
             "keyword router sees Exhibit 21 and calls GraphRAG. Third, where rules slip: what revenue allocated to "
             "remaining performance obligations includes. That is a text question, but the word revenue sends the keyword "
             "router to finance data, so it misses. That is why the keyword router is only our baseline. The Agents' "
             "orchestrator does the real routing, and it should beat this.")


# ================================================================ 9. messy wording
def s_messy(s, n, D):
    mw = D["mw"]
    G, Rv = mw["gate"], mw["retrieval_msft_10q"]
    c, k = G["typo_company|no_session"], G["typo_company|no_session_fuzzy_names"]
    frame(s, n, "Messy wording",
          f"Misspelled company names cut correct scope decisions from {pct(c['clean_acc'])} to {pct(c['messy_acc'])}; "
          f"matching names loosely restores {pct(k['messy_acc'])}",
          "Two inexpensive fixes for the Agents: match tickers and near-miss names before routing, and correct spelling "
          "before search.",
          f"Source: Week 8/results/messy_wording.json: {mw['n_variants']} rewrites of the 155 questions with the same "
          "meaning. Scope check and router are Eval's reference rules, not the Agents' orchestrator")
    kinds = [("typo_company", "Company misspelled"), ("casual", "Casual wording, ticker"), ("typo_terms", "Finance word misspelled")]
    cats = [f"{nm} ({mw['per_perturbation'][kk]})" for kk, nm in kinds]
    col_chart(s, X0, Y0, 5.3, 3.05, cats,
              [("Clean", [G[f"{kk}|no_session"]["clean_acc"] for kk, _ in kinds], GREY),
               ("Messy", [G[f"{kk}|no_session"]["messy_acc"] for kk, _ in kinds], PINK),
               ("Messy, loose name matching", [G[f"{kk}|no_session_fuzzy_names"]["messy_acc"] for kk, _ in kinds], NAVY)],
              "Kind of rewrite (number of questions); no company picked in the interface", "Correct scope decisions",
              "Messy wording")
    x = 5.75
    head(s, x, Y0, 4.05, "Effect on search (Microsoft 10-Q questions)", size=9.5)
    rv = lambda d: f"{pct(d['clean'])} → {pct(d['messy'])}"  # noqa: E731
    rows = [["Rewrite", ("RAG search", C["center"]), ("GraphRAG search", C["center"])],
            ["Finance word misspelled", (rv(Rv["typo_terms|rag_bm25"]), {**C["center"], "bold": True, "color": PINK}),
             (rv(Rv["typo_terms|graphrag_structured"]), {**C["center"], "bold": True, "color": PINK})],
            ["Company misspelled", (rv(Rv["typo_company|rag_bm25"]), C["center"]),
             (rv(Rv["typo_company|graphrag_structured"]), C["center"])],
            ["Casual wording", (rv(Rv["casual|rag_bm25"]), C["center"]), (rv(Rv["casual|graphrag_structured"]), C["center"])]]
    table(s, x, Y0 + 0.24, 4.05, [1.75, 1.1, 1.2], rows, row_h=0.31, sizes={0: 8.5, 1: 8.5, 2: 8.5}, name="Search effect")
    head(s, x, 2.82, 4.05, "Why", size=9.5)
    bullets(s, x, 3.05, 4.05, 1.2, [
        [("Names: ", True), ("the check knows exact names only, so 'Microsfot' or 'msft' becomes 'which company?'", False)],
        [("Finance words: ", True), ("keyword matching does not forgive 'revnue'", False)],
        [("Search ignores name typos ", True), ("because the company arrives as a filter", False)]], size=8.5, gap=3)
    notes(s, "To estimate how real users would fare, we rewrote every question three ways without changing its meaning: a "
             "misspelled company, misspelled finance words, and casual wording with tickers. The biggest drop is company "
             "recognition. If no company is picked in the interface, a simple name check turns most misspelled names into "
             "'which company?', and correct decisions fall from 98 to 19 percent. Matching tickers and near-miss spellings "
             "brings it back to 94. Misspelled finance words cost both searches about ten points, so a spelling step before "
             "search would help both teams. These are our reference rules, not the Agents' orchestrator, so read them as "
             "what to watch for.")


# ================================================================ 10. Agents API
def s_agents(s, n, D):
    fc = D["fc"]["cases"]
    protect = fc["keep"] + fc["must_abstain"]
    frame(s, n, "Agents API v0.2",
          f"The new /query fields plug straight into our grader; round 1 says fallback has {fc['rescue']} question to "
          f"rescue and {protect} to protect",
          "Our runner and grader are ready and tested against the contract's response format. The next step is the "
          "Agents' first run on the 155 questions.",
          "Source: Agents' API Contract v0.2 (11/11); Week 8/AGENTS_API_W8.md; Week 8/data/fallback_cases_w8.csv, built "
          "from RAG's and GraphRAG's round-1 results")
    head(s, X0, Y0, 4.9, "What each API field lets us score", size=9.5)
    rows = [["API field", "What we score"],
            [("status", {"bold": True}), "The decision: answer when answerable, abstain when not"],
            [("evidence", {"bold": True}), "The needed figure or passage is in the evidence"],
            [("citations", {"bold": True}), "Each link points to the right filing"],
            [("filters", {"bold": True}), "Company and period were detected correctly"],
            [("evidence_status, fallback flags", {"bold": True}), "When fallback to GraphRAG fires, and whether it helps"],
            [("answer (empty in v0.2)", {"bold": True}), "Same grader as RAG's reader, once it lands"]]
    table(s, X0, Y0 + 0.24, 4.9, [1.85, 3.05], rows, row_h=0.37, sizes={0: 8.5, 1: 8.5}, name="API fields")
    x = 5.3
    head(s, x, Y0, 4.5, "What round 1 expects from fallback, per question", size=9.5)
    rows = [["Case", ("Questions", C["center"])],
            ["RAG already answers: fallback must not break it", (str(fc["keep"]), {**C["center"], "bold": True})],
            ["Unanswerable: must stay “no evidence”", (str(fc["must_abstain"]), {**C["center"], "bold": True})],
            ["Needs Exhibit 21, not in the graph yet", (str(fc["not_in_graph_yet"]), C["center"])],
            ["Cross-company: one search per company", (str(fc["split"]), C["center"])],
            ["Needs NetApp's 10-Q, held by Data", (str(fc["not_in_corpus"]), C["center"])],
            ["Answer was already in RAG's evidence", (str(fc["answer_in_rag_evidence"]), C["center"])],
            [("GraphRAG can rescue today", {"bold": True, "color": GREEN}),
             (str(fc["rescue"]), {**C["center"], "bold": True, "color": GREEN})]]
    table(s, x, Y0 + 0.24, 4.5, [3.6, 0.9], rows, row_h=0.32, sizes={0: 8.5, 1: 8.5}, name="Fallback cases")
    notes(s, "The Agents sent their API contract yesterday, and thank you, it is very clear. Every field plugs into our "
             "grader as it is. The API does not return answers yet, so for now we score the decision, the evidence, the "
             "citations and the filters, and how the fallback from RAG to GraphRAG behaves. On the right is what round 1 "
             "tells us to expect. Of the questions RAG declined, GraphRAG can rescue one today. So the checks that matter "
             "now are that fallback does not break the 127 questions RAG already answers, and does not turn the 12 "
             "unanswerable questions into answers. Our runner and grader are ready; we need the Agents' first run.")


# ================================================================ 11. next steps
def s_next(s, n, D):
    st, gs, G = D["gr"]["structured|translated"], D["chk"]["graph_prose_by_scope"], D["mw"]["gate"]
    nar = D["v22"]["narrative"]
    frame(s, n, "Next steps", "One ask per team for next week, each tied to a round-1 result",
          "RAG ran round 1 twice and GraphRAG ran both searches, and both traced every miss. That is how we found and "
          "fixed our own errors.",
          "Source: Week 8/FOR_TEAMS_W8.md (one section per team, with file paths) and COMMS_W8.md (replies sent to each "
          "team)", lead="Thank you:")
    c = G["typo_company|no_session"]
    rows = [["Team", "Ask for next week", "Round-1 result behind it"],
            [("RAG", {"bold": True}), "Run our narrative judge with your key; mark answers that state the figure as answered",
             f"{nar['n'] - nar['refused']} narrative answers not yet scored; 2 answers stated but flagged as declined"],
            [("GraphRAG", {"bold": True}), "Rank by period and break ties (#68); add the notes to the statements; load Exhibit 21",
             f"Right number in the top 10 for {hn(st['numbers'])}, first for {st['top1_right']['hits']}; "
             f"{gs['outside_scope']['n']} text answers sit in the notes; 7 questions wait on Exhibit 21"],
            [("Agents", {"bold": True}), "Run the 155 questions through /query v0.2; search once per company; match tickers and "
                                         "near-miss names",
             f"Runner and grader are ready; 3 rankings need per-company search; names {pct(c['clean_acc'])} → "
             f"{pct(c['messy_acc'])}"],
            [("Data", {"bold": True}), "Load Microsoft's FY2024 and FY2025 10-Ks; release NetApp's 10-Q when its review is done",
             "Multi-year questions need them (joint ask with GraphRAG); 3 questions wait on NetApp"],
            [("Eval", {"bold": True}), "Hand-label narrative answers to validate the judge; grade the Agents' first run; add "
                                       "text anchors to the last 40 lookups",
             "The judge counts only after it agrees with our hand labels"]]
    table(s, X0, Y0, W, [0.9, 4.85, 3.85], rows, row_h=0.485, sizes={0: 9, 1: 8.5, 2: 8.5}, name="Asks")
    notes(s, "One ask per team for next week, each tied to a result from this deck. For RAG, run the narrative judge. For "
             "GraphRAG, the ranking fix and Exhibit 21. For the Agents, the first run of the 155 questions through the new "
             "API. For Data, the two Microsoft annual reports. And thank you to RAG and GraphRAG: both ran round 1 on their "
             "side and traced every miss, which is how we found and fixed our own errors this week.")


# ================================================================ appendix
def s_gold(s, n, D):
    v2, v22, g22 = D["v2"], D["v22"], D["g22"]
    frame(s, n, "Appendix: Gold Set v2.2",
          "Same 155 questions and expected answers; six grading changes, three of them raised by RAG",
          f"Numbers right moves from {kn(v2['numeric_accuracy'])} to {kn(v22['numeric_accuracy'])}; the questions do not "
          "change. Earlier versions are kept, so earlier runs stay comparable.",
          f"Source: Week 8/GOLD_SET_V2.md and results/gold_v2_2_changes.json ({g22['questions_changed']} questions touched; "
          f"file hash {g22['sha256_16']})")
    rag = ("RAG", {**C["center"], "bold": True, "color": BLUE})
    ev = ("Eval", C["center"])
    rows = [["Change", "Questions", "Why", ("Raised by", C["center"])],
            ["Precision asked = precision the filing prints", "EV1-015, EV1-027",
             "“$0.91” was failed for having two significant figures, which is all the filing prints", rag],
            ["Every figure required on multi-part questions", f"{len(g22['multi_value_questions'])} questions, e.g. EV1-043",
             "The question asks for three changes; the answer format held one value", rag],
            ["Route moved from relationship to text", "EV1R-002, EV1R-006",
             "RAG answered both from the 10-K text; GraphRAG's review agreed", rag],
            ["A second accepted wording", "EV1R-005",
             "The 10-K says Microsoft holds about 25% of OpenAI; the earlier 10-Q says 27%", ev],
            ["One evidence item per required point", f"{len(g22['anchors_split_one_item_per_point'])} questions",
             "Two sentences in one item could never match once RAG's index split them", ev],
            ["Last text anchors added; two labels corrected", "EV2-035/036/037/044; EV3-008/009",
             "Anchors read from RAG's passages; two fiscal-calendar questions were labelled as relationship", ev]]
    table(s, X0, Y0, W, [2.75, 2.0, 4.05, 0.8], rows, row_h=0.42, sizes={0: 8.5, 1: 8, 2: 8, 3: 8.5}, name="Gold changes")
    notes(s, "Backup. Gold Set v2.2 keeps the same 155 questions and expected answers and changes grading only. RAG raised "
             "three of the six changes, and they were right each time. The others came from checking our anchors against "
             "RAG's passages and from GraphRAG's review.")


def s_graph_detail(s, n, D):
    a, b = D["sbs"]["part_a"], D["sbs"]["part_b"]
    g = a["summary"]["graphrag_structured"]
    d = g["number_miss_diagnosis"]["counts"]
    hs, pa = D["hops"], D["chk"]["part_a_by_store"]
    agr = b["eval_vs_graphrag_rows"]
    same, ours = sum(v["same_jurisdiction"] for v in agr.values()), sum(v["eval_rows"] for v in agr.values())
    frame(s, n, "Appendix: GraphRAG detail",
          f"Most number misses have a specific fix, and GraphRAG's Exhibit 21 rows match our own reads on {same} of {ours}",
          f"On GraphRAG's own 20-filing store the same comparison gives {pa['graphrag_20_filing_store']['numbers']} against "
          f"{pa['eval_one_filing_build']['numbers']} on ours, so the store does not explain the gap; ranking does.",
          "Source: Week 8/results/side_by_side.json (number_miss_diagnosis, part_b), graphrag_round1_check.json, "
          "hops_v2_summary.json; GraphRAG PR #71 and Exhibit 21 branch c21fe89")
    head(s, X0, Y0, 5.6, f"Where the {g['numbers']['n'] - g['numbers']['hits']} number misses on the Microsoft 10-Q come from",
         size=9.5)
    rows = [["Cause", ("n", C["center"]), "Fix"],
            [f"Right number found but ranked below 8; in {d.get('ranked_below_8_period_word_matches_member', 0)}, “three "
             "months” matches Microsoft 365 rows", (str(d.get("in_top50_ranked_below_8", 0)), C["center"]),
             "Treat period words separately; break ties"],
            ["Calculations that need several inputs", (str(d.get("multi_input_not_all_in_top50", 0)), C["center"]),
             "One call per input"],
            ["Wording does not reach the concept", (str(d.get("single_input_not_in_top50", 0)), C["center"]),
             "Two aliases (unearned revenue, share repurchases)"]]
    table(s, X0, Y0 + 0.24, 5.6, [3.0, 0.4, 2.2], rows, row_h=0.44, sizes={0: 8.5, 1: 8.5, 2: 8.5}, name="Number misses")
    tb(s, X0, 3.3, 5.6, 0.95, [[("Hop counts (GraphRAG, PR #71): ", 8.5, True, NAVY),
                               (f"filled for {hs['hops_filled']} questions and left blank on purpose where the answer comes from "
                                "finance data, which the graph does not hold. EV3-002 counts 2 hops in GraphRAG's design and 4 "
                                "in ours: a design difference (country is a property, not a node), not a counting error.",
                                8.5, False, INK)]])
    x = 6.0
    card(s, x, Y0, 1.8, 1.05, f"{b['graph_correct']}/{b['n_questions']}", "relationship questions answered exactly by walking "
         "GraphRAG's subsidiary rows", NAVY)
    card(s, x + 2.0, Y0, 1.8, 1.05, f"{same}/{ours}", "Exhibit 21 rows agree with our own reads of the filings", GREEN)
    card(s, x, Y0 + 1.25, 1.8, 1.05, hn(g["top1_right_on_numbers"]), "right number at rank 1 on the Microsoft 10-Q", PINK)
    card(s, x + 2.0, Y0 + 1.25, 1.8, 1.05, hn(g["top1_wrong_period_on_numbers"]), "wrong-period number at rank 1; GraphRAG "
         "flagged this itself", NAVY)
    notes(s, "Backup for the GraphRAG slides. Most of the 25 number misses on the Microsoft filing have a specific fix. In "
             "six, the words 'three months' match the Microsoft 365 product rows. Ten are calculations that need one call "
             "per input. GraphRAG's Exhibit 21 rows agree with our own reads on every row we checked, and its hop counts "
             "are merged into our sheet.")


def s_defs(s, n, D):
    r1, v22, rt, fc = D["r1"]["hybrid_k10"], D["v22"], D["rt"], D["fc"]["cases"]
    R = rt["routers"]
    frame(s, n, "Appendix: Definitions", "How to read the measures in this deck",
          "Every number re-runs with one command (scripts/run_all.sh, 100 tests). Other teams' code is pinned: RAG "
          "5bfafeb, GraphRAG 21f0795, Data 7040b8a.",
          "Source: Week 8/README.md; kpmg_eval/metrics. No LLM is used in Eval's own results; the teams' round-1 runs are "
          "re-scored from the files they sent", lead="Reproducible:")
    rows = [["Term", "Meaning", "In this deck"],
            [("Gold Set v2.2", {"bold": True}), "Our 155 questions with expected answers, on 10 companies and 21 filings",
             "143 answerable, 12 unanswerable"],
            [("Evidence found", {"bold": True}), "Every figure or passage the answer needs is in the first k results, from "
                                                 "the right filing", f"{r1['hits']}/{r1['n']} at 10 results"],
            [("Numbers right", {"bold": True}), "The stated figure matches the filing at the precision it is written",
             kn(v22["numeric_accuracy"])],
            [("Balanced refusal", {"bold": True}), "Average of refusing unanswerable questions and not refusing answerable ones",
             f"{v22['refusal']['balanced_raa_incl_false_premise']:.3f}"],
            [("Coverage", {"bold": True}), "Every tool the question needs was called; it says nothing about the answer",
             f"{pct(R['combined']['coverage'])} for every tool"],
            [("Unneeded call", {"bold": True}), "A tool called that the question does not need",
             f"{R['combined']['unneeded_calls_per_question']:.2f} per question for every tool"],
            [("False premise", {"bold": True}), "The question assumes something untrue; a good answer corrects it",
             f"{kn(v22['false_premise_corrected'])} corrected"],
            [("Fallback", {"bold": True}), "The Agents try GraphRAG when RAG's evidence is weak or empty",
             f"{fc['rescue']} question to rescue today"]]
    table(s, X0, Y0, W, [1.6, 5.6, 2.4], rows, row_h=0.325, sizes={0: 8.5, 1: 8.5, 2: 8.5}, name="Definitions")
    notes(s, "Backup. The terms used in this deck, each with the number it produced. Everything re-runs with one command.")


def main():
    base, out = sys.argv[1], sys.argv[2]
    prs = Presentation(base)
    add_slides(prs, N_SLIDES)
    ans = j(RES / "answers_rag_reader_round1.json")["by_gold_set"]
    D = {"sbs": j(RES / "side_by_side.json"), "rt": j(RES / "routing_baselines.json"), "mw": j(RES / "messy_wording.json"),
         "v2": ans["v2"], "v22": ans["v2_2"], "g22": j(RES / "gold_v2_2_changes.json"), "v21": j(RES / "gold_v2_1_changes.json"),
         "r1": j(DATA / "round1_rag_2026-11-09.json"), "gr": j(RES / "graphrag_round1_graphrag_aura.json")["summary"],
         "chk": j(RES / "graphrag_round1_check.json"), "ex": j(RES / "routing_examples.json"),
         "fc": j(RES / "fallback_cases_w8.json"), "hops": j(RES / "hops_v2_summary.json")}
    order = [s_summary, s_tracker, s_retrieval, s_answers, s_graphrag, s_compare, s_routing, s_examples, s_messy, s_agents,
             s_next, s_gold, s_graph_detail, s_defs]
    assert len(order) == N_SLIDES
    for i, (slide, fn) in enumerate(zip(prs.slides, order), 1):
        fn(slide, i, D)
    prs.save(out)
    print("[deck] wrote", out, f"({N_SLIDES} slides: 11 main, 3 appendix)")


if __name__ == "__main__":
    main()
