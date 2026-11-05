"""Deck style shared by the weekly Eval slide builders (from build_deck_w6.py): the team template's fonts, colours,
tables and tiles."""
from __future__ import annotations

import json
from pathlib import Path

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

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


