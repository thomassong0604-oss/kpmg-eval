"""Evaluation & Testing slides for the 10/29 KPMG x Columbia meeting (Week 6 only), in the team deck's style.

    python scripts/build_deck_w6.py <base.pptx> <out.pptx>

Input: the 10/22 team deck reduced to its first Evaluation & Testing slide, duplicated to five (same master, layout,
title placeholder and footer art, so the slides paste into the team deck unchanged). Every number on the slides is
read from results/*.json and data/*.jsonl, so re-running run_all.sh and this script keeps the deck in sync with the
code. Charts and tables are native PowerPoint objects (editable).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
RES, DATA = ROOT / "results", ROOT / "data"
INK, MUTED, NAVY, BLUE, PINK, GREEN, SUB = "1E2530", "5C6675", "2F3E96", "3D52C4", "D9447A", "16825D", "0655C9"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NAMES = {"AAPL": "Apple", "CASY": "Casey's", "MCK": "McKesson", "MDT": "Medtronic", "MSFT": "Microsoft", "MU": "Micron",
         "NKE": "Nike", "NTAP": "NetApp", "PH": "Parker-Hannifin", "TTWO": "Take-Two"}
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def rgb(h):
    return RGBColor.from_string(h)


def j(p):
    return json.loads(Path(p).read_text())


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def mdy(s):  # 2026-04-30 -> Apr 30, 2026
    y, m, d = s.split("-")
    return f"{MON[int(m) - 1]} {int(d)}, {y}"


def my(s):  # 2026-04-30 -> Apr 2026
    y, m, _ = s.split("-")
    return f"{MON[int(m) - 1]} {y}"


# ---------------------------------------------------------------- drawing helpers (same as the Week 5 builder)
def tb(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if runs and isinstance(runs[0], list) else [runs]
    for i, pr in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for r in pr:
            text, size, bold, color = r[:4]
            run = p.add_run()
            run.text = text
            f = run.font
            f.name, f.size, f.bold, f.color.rgb = "Arial", Pt(size), bold, rgb(color)
            f.italic = r[4] if len(r) > 4 else False
    return s


def clear(slide):
    for sh in list(slide.shapes):
        if sh.is_placeholder and sh.has_text_frame and sh.text_frame.text.strip() == "Evaluation & Testing":
            continue
        sh._element.getparent().remove(sh._element)


def header(slide, bold, rest):
    tb(slide, 0.12, 0.62, 9.7, 0.24, [(f"{bold} | {rest}", 14, True, SUB, True)], name="Subtitle")


def footer(slide, bold, rest, source, y=4.42, w=7.5):
    tb(slide, 0.12, y, w, 0.42, [(bold + " ", 9, True, INK), (rest, 9, False, MUTED)], name="Takeaway")
    tb(slide, 0.12, 4.98, 7.5, 0.13, [(source, 7.5, False, MUTED)], name="Source")


def label(slide, x, y, w, text, color=INK):
    tb(slide, x, y, w, 0.16, [(text, 9.5, True, color)])


def tile(slide, x, y, big, lab, w_big=0.95, w_lab=2.3, color=NAVY):
    tb(slide, x, y, w_big, 0.36, [(big, 20, True, color)], anchor=MSO_ANCHOR.MIDDLE)
    tb(slide, x + w_big + 0.06, y + 0.01, w_lab, 0.36, [(lab, 9, False, INK)], anchor=MSO_ANCHOR.MIDDLE)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def cell(c, text, size=8.5, bold=False, color=INK, fill="FFFFFF", align=PP_ALIGN.LEFT):
    c.fill.solid()
    c.fill.fore_color.rgb = rgb(fill)
    c.margin_left = c.margin_right = Inches(0.05)
    c.margin_top = c.margin_bottom = Inches(0.025)
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = c.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = "Arial", Pt(size), bold, rgb(color)


def white_borders(table):
    for row in table.rows:
        for c in row.cells:
            tcPr = c._tc.get_or_add_tcPr()
            for tag in ("lnL", "lnR", "lnT", "lnB"):
                ln = etree.SubElement(tcPr, f"{{{NS_A}}}{tag}", w="19050")
                sf = etree.SubElement(ln, f"{{{NS_A}}}solidFill")
                etree.SubElement(sf, f"{{{NS_A}}}srgbClr", val="FFFFFF")
            fill = tcPr.find(f"{{{NS_A}}}solidFill")
            if fill is not None:  # schema order: borders before fill
                tcPr.remove(fill)
                tcPr.append(fill)


def table(slide, x, y, w, col_w, rows, header_fill=NAVY, row_h=0.27, sizes=None, name=None):
    """rows[0] is the header. rows[i] = list of str or (str, opts dict)."""
    shp = slide.shapes.add_table(len(rows), len(col_w), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    if name:
        shp.name = name
    t = shp.table
    t.first_row = False
    t.horz_banding = False
    for i, cw in enumerate(col_w):
        t.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        t.rows[r].height = Inches(row_h)
        for c, v in enumerate(row):
            text, o = (v if isinstance(v, tuple) else (v, {}))
            if r == 0:
                cell(t.cell(r, c), text, size=8.5, bold=True, color="FFFFFF", fill=header_fill, align=o.get("align", PP_ALIGN.LEFT))
            else:
                cell(t.cell(r, c), text, size=o.get("size", (sizes or {}).get(c, 8.5)), bold=o.get("bold", False),
                     color=o.get("color", INK), fill=o.get("fill", "F4F6FC" if r % 2 == 0 else "FFFFFF"),
                     align=o.get("align", PP_ALIGN.LEFT))
    white_borders(t)
    return shp


def ramp(n):
    if n == 0:
        return "F4F6FC", MUTED
    if n <= 3:
        return "CDD2F1", INK
    if n <= 10:
        return "9AA4DE", INK
    if n <= 25:
        return "5E6BC4", "FFFFFF"
    return NAVY, "FFFFFF"


# ================================================================ slides
def slide_scope(s, cov, filings):
    clear(s)
    header(s, "Data's 10 companies", "enough for round 1: single-company and year-over-year, not same-quarter")
    label(s, 0.12, 1.02, 5.6, "What Eval assumes is in the DB (reproduces Data's count: 10 10-Ks, 11 10-Qs)")
    q_end = cov["latest_10q_period_end"]
    k = {f["ticker"]: f for f in filings if f["form"] == "10-K"}
    k_end = {}
    for f in jl(DATA / "scope10_facts.jsonl"):
        if f["form"] == "10-K":
            k_end[f["ticker"]] = max(k_end.get(f["ticker"], ""), f["period_end"])
    rows = [["Company", "Fiscal year ends", "Latest 10-K", ("Latest 10-Q quarter", {"align": PP_ALIGN.LEFT})]]
    for t in NAMES:
        fye = k[t]["fiscal_year_end"].replace("last Friday of April", "last Fri of Apr").replace(
            "last Saturday of September", "last Sat of Sep").replace("Thursday closest to August 31", "Thu near Aug 31")
        stale = t in ("MU", "PH", "MSFT")
        rows.append([(NAMES[t], {"bold": True}), fye, f"FY{k[t]['fiscal_year']} ({my(k_end[t])})",
                     (f"{mdy(q_end[t])}" + ("  *" if stale else ""), {"color": PINK if stale else INK})])
    table(s, 0.12, 1.24, 5.55, [1.25, 1.3, 1.45, 1.55], rows, row_h=0.255, name="Scope table")
    tb(s, 0.12, 4.12, 5.55, 0.15, [("* latest 10-Q is older than other companies' (quarter ended March or May 2026)", 7.5, False, PINK)])
    x = 6.05
    tile(s, x, 1.18, str(cov["distinct_fiscal_year_end_months"]), "months in which the ten fiscal years end: every comparison must name each period")
    tile(s, x, 1.83, str(len(cov["companies_sharing_a_calendar_quarter"])),
         "calendar quarters across the latest 10-Qs: no quarter that all ten share")
    tile(s, x, 2.48, "2 yrs", "per company, from each 10-K's prior-year column: year-over-year yes, trends no")
    tile(s, x, 3.13, "0", "10-K/A amendments in scope, so restatement questions (GraphRAG M12, M13) drop")
    footer(s, "Answer to Data: yes, enough for round 1.",
           "Asks: confirm the 21 accession numbers, share chunks for all 21 filings, and clean Exhibit 21 for the ten 10-Ks.",
           "Source: Week 6/results/scope10_coverage.json, data/scope10_filings.json; fiscal periods from SEC companyconcept API (read 10/29)")
    notes(s, "Emma asked whether the ten companies are enough. Short answer yes for round 1. Data gave counts but not accession numbers, "
             "so we assumed each company's latest 10-K and latest 10-Q filed by Oct 13, plus Apple's two 10-Qs and Microsoft's two filings "
             "that GraphRAG listed. That reproduces 10 and 11 exactly, but we need Data to confirm. The catch is calendars: fiscal years end in "
             "six different months and the latest 10-Qs fall in three calendar quarters, so 'last quarter' comparisons across all ten are not "
             "possible and every cross-company question names each company's own period.")


def slide_gold(s, cov, checks, grader, status, new, draft):
    clear(s)
    g = cov["gold_set"]
    header(s, "Gold Set v1.1", f"{g['total_round1']} questions for round 1: {g['v1_in_scope']} kept, {g['v1_retired']} retired, "
                              f"{g['new_eval_scope10']} new on the added companies")

    def grp(t):
        return {"extraction": "Extraction", "segment": "Extraction", "calculation": "Calculation & derived",
                "comparison": "Calculation & derived", "derived": "Calculation & derived", "reconciliation": "Calculation & derived",
                "definition": "Definition & narrative", "narrative": "Definition & narrative", "cross_company": "Cross-company",
                "fiscal_calendar": "Fiscal calendar", "unanswerable": "Unanswerable & false premise",
                "false_premise": "Unanswerable & false premise"}[t]
    v1 = {q["qid"]: q for q in jl(DATA / "benchmark_v1.jsonl")}
    c = Counter()
    for q in v1.values():
        c[(grp(q["type"]), "kept" if status[q["qid"]] == "in_scope" else "retired")] += 1
    for q in new:
        c[(grp(q["type"]), "new")] += 1
    order = ["Extraction", "Calculation & derived", "Definition & narrative", "Cross-company", "Fiscal calendar",
             "Unanswerable & false premise"]
    rows = [["", ("v1 kept", {"align": PP_ALIGN.CENTER}), ("Retired", {"align": PP_ALIGN.CENTER}),
             ("New (EV2)", {"align": PP_ALIGN.CENTER}), ("Round 1", {"align": PP_ALIGN.CENTER})]]
    for grp_name in order:
        r = [(grp_name, {"bold": True})]
        for col in ("kept", "retired", "new"):
            n = c[(grp_name, col)]
            fill, col_ink = ramp(n) if col != "retired" else (("F8D7E3", INK) if n else ("F4F6FC", MUTED))
            r.append((str(n) if n else "", {"fill": fill, "color": col_ink, "align": PP_ALIGN.CENTER}))
        r.append((str(c[(grp_name, "kept")] + c[(grp_name, "new")]), {"bold": True, "align": PP_ALIGN.CENTER}))
        rows.append(r)
    tot = {k2: sum(c[(gname, k2)] for gname in order) for k2 in ("kept", "retired", "new")}
    rows.append([("All questions", {"bold": True, "color": BLUE})] +
                [(str(tot[k2]), {"bold": True, "color": BLUE, "align": PP_ALIGN.CENTER}) for k2 in ("kept", "retired", "new")] +
                [(str(tot["kept"] + tot["new"]), {"bold": True, "color": BLUE, "align": PP_ALIGN.CENTER})])
    table(s, 0.12, 1.08, 5.55, [1.95, 0.9, 0.9, 0.9, 0.9], rows, row_h=0.33, name="Gold composition")
    pending = sum(1 for q in new)
    cs = checks["summary"]
    x = 6.05
    tile(s, x, 1.08, cs["read2_agrees_with_read1"], "new answers re-read from the SEC API: both reads agree", w_big=1.05, w_lab=2.2)
    tile(s, x, 1.70, cs["quarter_sums_hold"], "Q1 + Q2 + Q3 = nine-month total, per company and line item", w_big=1.05, w_lab=2.2)
    tile(s, x, 2.32, f"{grader['graded'] - len(grader['mismatches'])}/{grader['graded']}",
         f"grader labels right on the {grader['numeric_items']} new numeric questions (exact, restated, x1000, sign)",
         w_big=1.05, w_lab=2.2)
    tile(s, x, 2.94, str(len(draft)), "relationship questions drafted with GraphRAG, all on their 5 filings this week", w_big=1.05, w_lab=2.2)
    tile(s, x, 3.56, str(pending), "new questions wait for Data's chunks to get text anchors", w_big=1.05, w_lab=2.2, color=PINK)
    footer(s, "Retired:", "the 10 questions that need Amazon, Meta or NVIDIA. Microsoft stays the MVP (89 questions); every added "
                          "company gets 3 to 7 questions, plus 5 that compare all ten.",
           "Source: Week 6/data/benchmark_scope10.jsonl, benchmark_scope10_status.csv; results/scope10_checks.json, scope10_grader_check.json")
    notes(s, "Gold Set v1 stays frozen with the same file hash, so last week's scores still compare. For round 1 we keep the 90 questions "
             "that only need companies in Data's list, retire the 10 that need Amazon, Meta or NVIDIA, and add 49. Every new answer is "
             "computed in code from SEC XBRL facts, each read twice from the SEC API: all 53 re-reads agreed, and the quarterly figures "
             "add up to the nine-month totals for every company. We also ran the grader on the new questions with right and wrong answers: "
             "156 of 156 labelled correctly, including negative numbers like Take-Two's loss.")


def slide_calendars(s, facts_by, cov):
    clear(s)
    header(s, "Comparisons", "ten companies, six fiscal calendars: a 'latest year' ranking spans Aug 2025 to Jun 2026")
    margin = {}
    for t in NAMES:
        r, n = facts_by[(t, "REV")], facts_by[(t, "NI")]
        margin[t] = n["value"] / r["value"]
    order = sorted(NAMES, key=lambda t: margin[t])
    cd = CategoryChartData()
    cd.categories = [f"{NAMES[t]} (FY ends {my(facts_by[(t, 'REV')]['period_end'])})" for t in order]
    cd.add_series("Net margin, latest fiscal year in the corpus", [round(margin[t] * 100, 1) for t in order])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.12), Inches(1.2), Inches(4.75), Inches(3.15), cd)
    gf.name = "Net margin chart"
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name, ch.font.size = "Arial", Pt(8)
    ch.font.color.rgb = rgb(INK)
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = '0.0"%"', False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.color.rgb = Pt(8), rgb(INK)
    ser = plot.series[0]
    for i, t in enumerate(order):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(PINK if margin[t] < 0 else NAVY)
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E7F0")
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(8)
    va.tick_labels.font.color.rgb = rgb(MUTED)
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.minimum_scale, va.maximum_scale = -20, 50
    ca = ch.category_axis
    ca.format.line.color.rgb = rgb("C9CED8")
    ca.tick_labels.font.size = Pt(8)
    from pptx.enum.chart import XL_TICK_LABEL_POSITION
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    label(s, 0.12, 1.0, 4.7, "Net margin, each company's latest fiscal year in the corpus")

    x, w = 5.15, 2.55
    label(s, x, 1.0, w + 2.0, "Traps the new questions test")
    items = [
        ("Missing year.", f"Micron's latest 10-K is FY2025. 'FY2026 revenue' must be refused, not built from three 10-Q "
                          f"quarters (EV2-045)."),
        ("Line-item name.", "Parker-Hannifin tags net income as ProfitLoss; no NetIncomeLoss facts in its 10-Ks or 10-Qs filed since June 2025."),
        ("Sign.", f"Take-Two lost USD {-facts_by[('TTWO', 'NI')]['value'] / 1e6:,.1f}M in FY2026; 'why was it profitable?' "
                  "is a false premise (EV2-048)."),
        ("Changed tag.", "Nike's and NetApp's latest 10-Q revenue is not under the tag their 10-Ks use (SEC API, 10/29)."),
    ]
    y = 1.27
    for b, t in items:
        tb(s, x, y, 4.6, 0.5, [(b + " ", 9, True, NAVY), (t, 9, False, INK)])
        y += 0.58
    footer(s, "Why it matters:", "an agent that ranks 'latest results' without naming each period compares different years. Each "
                                 "comparison question states every company's period, and the scope check refuses years that are "
                                 "not in the corpus.",
           "Source: Week 6/data/scope10_facts.jsonl (SEC companyconcept API, read twice 10/29); questions EV2-040 to EV2-049",
           y=4.42, w=7.6)
    notes(s, "This is the kind of comparison the new questions ask. Note the fiscal years: Micron's latest 10-K ends August 2025, "
             "Microsoft's June 2026. A system that answers 'latest year' without naming periods is comparing different years. "
             "Four traps came straight out of the SEC data, and each one is now a question. Take-Two is the only company with a loss.")


def slide_graphrag(s, wire, draft):
    clear(s)
    header(s, "GraphRAG", "both retrieval arms now score against the same gold set as RAG, through one harness")
    sc = wire["scored"]
    checks = wire["contract_checks"]
    n_ok = min(v for k2, v in checks.items() if k2.endswith(":ok")) if checks else 0
    label(s, 0.12, 1.0, 4.4, "Wired on the INT-0 mock's rows (tests the plumbing, not the graph)")
    tile(s, 0.12, 1.25, f"{wire['questions']}", f"Microsoft questions through both arms: {wire['calls']} calls, "
                                                 f"{sum(wire['errors'].values()) if wire['errors'] else 0} errors", w_big=0.75, w_lab=3.4)
    tile(s, 0.12, 1.83, f"{n_ok}/{wire['questions']}", "pass all 5 checks: trace_id echoed, one provenance key, versions, fact period",
         w_big=0.75, w_lab=3.4)
    tile(s, 0.12, 2.41, str(wire["segment_fact_vs_total_pairs_rejected_by_dims"]),
         "segment-vs-total false matches now rejected: fact keys carry XBRL dimensions (an Eval bug, fixed)", w_big=0.75, w_lab=3.4)
    tile(s, 0.12, 2.99, f"{len(draft)}", "relationship questions drafted; all use the MSFT 10-Q or FY2026 10-K GraphRAG loads",
         w_big=0.75, w_lab=3.4)
    tile(s, 0.12, 3.57, "155", "questions in hops_v1.csv for GraphRAG to label; Eval reviews", w_big=0.75, w_lab=3.4)

    rows = [["Finding in GraphRAG's output", "Ask"],
            ["Fact values are in USD millions (82,886) while the unit says USD", "Return the XBRL unit value, or add a scale field"],
            ["Segments are labels ('Intelligent Cloud'), not XBRL members", "Carry the member name; Eval matches labels for now"],
            ["Two evidence rows share one section_id", "One id per evidence row, so citations stay distinct"]]
    label(s, 4.75, 1.0, 4.9, "Findings for GraphRAG")
    table(s, 4.75, 1.25, 4.95, [2.6, 2.35], rows, row_h=0.42, sizes={0: 8, 1: 8}, name="GraphRAG findings")
    tb(s, 4.75, 3.1, 2.95, 0.95, [[("Agreed 10/26, now in code: ", 9, True, NAVY),
                                    ("citations join on chunk, section or fact id; reruns key on all three version fields; "
                                     "anchors ignore whitespace.", 9, False, INK)]])
    footer(s, "Next:", "point the harness at graphrag.retrieve once GraphRAG registers a backend; scores then measure the graph.",
           "Source: Week 6/results/graphrag_wiring.json; kpmg_eval/graphrag_adapter.py; data/benchmark_v1_relationship_draft.jsonl, hops_v1.csv",
           y=4.42, w=7.6)
    notes(s, "GraphRAG gave us their mock with the final signatures. We wired both arms into the same harness RAG uses: graph results "
             "are scored by section and text, structured results by XBRL fact. Every call passed the five checks we join on. "
             "This is the mock's handful of rows, so the hit rates mean nothing about the graph yet. One thing we caught in our own code: "
             "fact keys ignored segments, so 'Intelligent Cloud revenue' counted as 'total revenue'. Fixed and tested. "
             "Three asks for GraphRAG on the right. Note we ran Eval's stand-in over their mock's rows; their own mock module runs with --tools mock.")


def slide_next(s, rev, cov):
    clear(s)
    sm = rev["summary"]
    header(s, "Next steps", f"RAG's anchors reach every input for {sm['numeric_questions_with_all_inputs_anchored']} "
                            "numeric questions; one ask per team")
    label(s, 0.12, 1.0, 3.6, "Review of RAG's Gold v1 anchors (their PR #10)")
    tile(s, 0.12, 1.25, sm["inputs_in_anchored_chunks"], "numbers the answers use sit in an anchored chunk", w_big=0.9, w_lab=2.0)
    tile(s, 0.12, 1.83, str(sm["anchors_vs_chunks"].get("no_match", 0)),
         "anchors match no chunk: a share-count string from Gold v0 on two questions", w_big=0.9, w_lab=2.0, color=PINK)
    tile(s, 0.12, 2.41, str(sm["anchors_vs_chunks"].get("broad", 0)), "anchors match 4+ chunks: bare numbers such as '82,886'",
         w_big=0.9, w_lab=2.0, color=PINK)
    tile(s, 0.12, 2.99, str(sm["retired_questions_still_in_rag_file"]), "retired questions (Amazon, Meta, NVIDIA) to drop",
         w_big=0.9, w_lab=2.0)
    tile(s, 0.12, 3.57, str(sm["rows_with_ticker_form_filters_only"]), "rows filter on ticker + form only; add fiscal year and quarter",
         w_big=0.9, w_lab=2.0)

    rows = [["Team", "Ask before round 1 (W8)"],
            [("Data", {"bold": True}), "Confirm the 21 accession numbers; share chunks for all 21; clean Exhibit 21 for the ten 10-Ks"],
            [("GraphRAG", {"bold": True}), "Propose hops for the 155 questions; a date for a real backend; the 3 findings on the GraphRAG slide"],
            [("RAG", {"bold": True}), "Fix 2 anchors, add row labels to the 33 broad ones; trace_id and cited chunk ids in the logs"],
            [("Agents", {"bold": True}), "Return the AnswerBlock with trace_id and cited chunk, section or fact ids"],
            [("Eval", {"bold": True}), "Text anchors for the 49 new questions once chunks land; human review of 8 flagged items"]]
    label(s, 3.7, 1.0, 4.0, "Asks")
    table(s, 3.7, 1.25, 6.0, [0.85, 5.15], rows, row_h=0.4, sizes={0: 8.5, 1: 8}, name="Asks")
    footer(s, "Where Eval stands:", "the harness runs RAG and both GraphRAG arms. Round 1 now waits on Data's chunks, GraphRAG's "
                                      "backend and the Agent's AnswerBlock.",
           "Source: Week 6/results/rag_gold_v1_anchor_review.json (RAG eval/gold_v1.jsonl @ 6f0894a, read as data); scope10_coverage.json",
           y=4.42, w=7.6)
    notes(s, "RAG mapped evidence anchors to our 100 questions and asked us to review them; we did it against our copy of the 10-Q as "
             "RAG chunks it. Coverage is good: 97 of 99 numbers the answers need sit in an anchored chunk. Two anchors never match because "
             "they carry a share-count string from Gold v0 that belongs to neither question, and 33 are bare numbers that appear in four or "
             "more chunks, which makes recall too easy. The table lists one concrete ask per team before round 1 in week 8.")


def main():
    base, out = sys.argv[1], sys.argv[2]
    prs = Presentation(base)
    sl = list(prs.slides)
    assert len(sl) == 5, "base deck must hold exactly five Evaluation & Testing slides"
    cov, checks, grader = j(RES / "scope10_coverage.json"), j(RES / "scope10_checks.json"), j(RES / "scope10_grader_check.json")
    filings = j(DATA / "scope10_filings.json")["filings"]
    status = {l.split(",")[0]: l.split(",")[3] for l in list(open(DATA / "benchmark_scope10_status.csv"))[1:]}
    new, draft = jl(DATA / "benchmark_scope10_new.jsonl"), jl(DATA / "benchmark_v1_relationship_draft.jsonl")
    facts_by = {}
    for f in jl(DATA / "scope10_facts.jsonl"):
        if f["form"] != "10-K" and f["ticker"] != "MSFT":
            continue
        lab = "REV" if "Revenue" in f["concept"] else "NI"
        cur = facts_by.get((f["ticker"], lab))
        if cur is None or f["period_end"] > cur["period_end"]:
            facts_by[(f["ticker"], lab)] = f
    slide_scope(sl[0], cov, filings)
    slide_gold(sl[1], cov, checks, grader, status, new, draft)
    slide_calendars(sl[2], facts_by, cov)
    slide_graphrag(sl[3], j(RES / "graphrag_wiring.json"), draft)
    slide_next(sl[4], j(RES / "rag_gold_v1_anchor_review.json"), cov)
    prs.save(out)
    print("[deck] wrote", out)


if __name__ == "__main__":
    main()
