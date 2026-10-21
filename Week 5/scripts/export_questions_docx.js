// Word version of Gold Set v1 for reviewers who don't read jsonl.
//   node scripts/export_questions_docx.js   -> data/benchmark_v1_questions.docx
// Reads data/benchmark_v1.jsonl, so it always matches the benchmark the code scores.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  HeadingLevel, AlignmentType, PageOrientation, BorderStyle, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const rows = fs.readFileSync(path.join(ROOT, "data", "benchmark_v1.jsonl"), "utf8")
  .split("\n").filter(Boolean).map(JSON.parse);

const TYPES = [
  ["extraction", "Extraction (single fact)"], ["segment", "Segment and disaggregated revenue"],
  ["calculation", "Calculation"], ["comparison", "Comparison"], ["derived", "Derived periods"],
  ["reconciliation", "Reconciliation"], ["definition", "Definition"], ["narrative", "Narrative"],
  ["cross_company", "Cross-company"], ["unanswerable", "Unanswerable / out of scope"], ["false_premise", "False premise"],
];
const NAVY = "2F3E96", INK = "1E2530", MUTED = "5C6675", HEAD = "E8EBF7", LINE = "C9CED8";
const W = [1700, 5000, 3600, 900, 1150, 1150]; // landscape letter, 0.75" margins -> 13,500 DXA
const TOTAL = W.reduce((a, b) => a + b, 0);
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };

const run = (text, o = {}) => new TextRun({ text, font: "Arial", size: o.size || 18, bold: o.bold, color: o.color || INK, italics: o.italics });
const cell = (text, w, o = {}) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders,
  shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
  margins: { top: 60, bottom: 60, left: 90, right: 90 },
  children: [new Paragraph({ children: [run(text, o)] })],
});
const header = () => new TableRow({
  tableHeader: true,
  children: ["ID", "Question", "Expected answer", "Source", "Scope", "Answer"].map((h, i) => cell(h, W[i], { bold: true, fill: HEAD, color: NAVY })),
});

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: "Gold Set v1: 100 benchmark questions", font: "Arial", color: NAVY })] }),
  new Paragraph({ spacing: { after: 120 }, children: [run("KPMG × Columbia QMSS · Evaluation & Testing workstream · generated from data/benchmark_v1.jsonl", { color: MUTED })] }),
  new Paragraph({ spacing: { after: 120 }, children: [
    run("Source column: ", { bold: true }),
    run("RAG = from the RAG team's Gold Set v0, kept under their ID and wording; New = added by Eval. "),
    run("Scope: ", { bold: true }), run("MVP = single-company (Microsoft); Comparison = needs the other pilot companies. "),
    run("Answer: ", { bold: true }), run("Exact number vs Narrative explanation (Business/UI split); Refuse / Correct premise for unanswerable and false-premise questions. "),
    run("Expected answers are computed from SEC XBRL facts (Microsoft Q3 FY2026 10-Q via the Data team's XBRL instance; peers and Microsoft's FY2026 10-K via the SEC API, each value read twice). Amounts are USD millions unless stated."),
  ] }),
];

// summary table
const sumW = [4500, 1500, 1500, 1500];
const sumRow = (cells, o = {}) => new TableRow({ children: cells.map((c, i) => cell(String(c), sumW[i], o)) });
const sumRows = [sumRow(["Type", "RAG", "New", "Total"], { bold: true, fill: HEAD, color: NAVY })];
for (const [t, title] of TYPES) {
  const qs = rows.filter(r => r.type === t);
  sumRows.push(sumRow([title, qs.filter(r => r.source === "rag_gold_v0").length, qs.filter(r => r.source === "eval_v1").length, qs.length]));
}
sumRows.push(sumRow(["All questions", rows.filter(r => r.source === "rag_gold_v0").length, rows.filter(r => r.source === "eval_v1").length, rows.length], { bold: true }));
children.push(new Table({ width: { size: sumW.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: sumW, rows: sumRows }));

for (const [t, title] of TYPES) {
  const qs = rows.filter(r => r.type === t);
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, keepLines: true, spacing: { before: 360, after: 120 },
    children: [new TextRun({ text: `${title} (${qs.length})`, font: "Arial", color: NAVY })] }));
  const trs = [header()];
  qs.forEach((r, i) => {
    const fill = i % 2 ? "F7F8FC" : undefined;
    trs.push(new TableRow({ cantSplit: true, children: [
      cell(r.qid, W[0], { fill, bold: true }), cell(r.question, W[1], { fill }), cell(r.answer.display, W[2], { fill }),
      cell(r.source === "rag_gold_v0" ? "RAG" : "New", W[3], { fill }),
      cell(r.scope === "mvp_single_company" ? "MVP" : "Comparison", W[4], { fill }),
      cell({ exact_numeric: "Exact number", narrative: "Narrative", refusal: "Refuse", false_premise: "Correct premise", exact_categorical: "Exact (text)" }[r.answer_type] || r.answer_type, W[5], { fill }),
    ] }));
  });
  children.push(new Table({ width: { size: TOTAL, type: WidthType.DXA }, columnWidths: W, rows: trs }));
}

const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 18 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 36, bold: true }, paragraph: { spacing: { after: 80 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true }, paragraph: { outlineLevel: 0 } },
    ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE },
      margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ children: ["Page ", PageNumber.CURRENT], font: "Arial", size: 16, color: MUTED })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(b => {
  const out = path.join(ROOT, "data", "benchmark_v1_questions.docx");
  fs.writeFileSync(out, b);
  console.log("[docx] wrote", out, rows.length, "questions");
});
