// Word version of Gold Set v2 for reviewers and other teams who don't read jsonl.
//   node scripts/export_gold_v2_docx.js   -> data/benchmark_v2_questions.docx
// Reads data/benchmark_v2_2.jsonl (current; Week 8) and data/snapshot_w7.json, so it always matches what the code scores.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  HeadingLevel, AlignmentType, PageOrientation, BorderStyle, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const raw = fs.readFileSync(path.join(ROOT, "data", "benchmark_v2_2.jsonl"));
const HASH = crypto.createHash("sha256").update(raw).digest("hex").slice(0, 16);
const rows = raw.toString("utf8").split("\n").filter(Boolean).map(JSON.parse);
const snap = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "snapshot_w7.json"), "utf8"));

const NAMES = { MSFT: "Microsoft", AAPL: "Apple", CASY: "Casey's General Stores", MCK: "McKesson", MDT: "Medtronic",
  MU: "Micron Technology", NKE: "Nike", NTAP: "NetApp", PH: "Parker-Hannifin", TTWO: "Take-Two Interactive" };
const ORDER = ["MSFT", "AAPL", "CASY", "MCK", "MDT", "MU", "NKE", "NTAP", "PH", "TTWO"];
const ROUTE = { sql: "Finance data", text: "Text (RAG)", graph: "Relationship (GraphRAG)", multi: "Finance data + text", none: "No tool (scope check)" };
const ANSWER = { exact_numeric: "Exact number", narrative: "Narrative", refusal: "Refuse", false_premise: "Correct premise", exact_categorical: "Exact (text)" };
const STATUS = { auto_verified: "Checked vs SEC data", verified_twice: "Read twice", needs_human_review: "Needs human review" };

const NAVY = "2F3E96", INK = "1E2530", MUTED = "5C6675", HEAD = "E8EBF7", LINE = "C9CED8", ALT = "F7F8FC";
const W = [1550, 4750, 3500, 1300, 1150, 1250]; // landscape letter, 0.75" margins -> 13,500 DXA
const TOTAL = W.reduce((a, b) => a + b, 0);
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const run = (text, o = {}) => new TextRun({ text, font: "Arial", size: o.size || 17, bold: o.bold, color: o.color || INK });
const cell = (text, w, o = {}) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders,
  shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
  margins: { top: 50, bottom: 50, left: 80, right: 80 },
  children: [new Paragraph({ children: [run(String(text), o)] })],
});
const table = (widths, data, headFill = HEAD) => new Table({
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
  rows: data.map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true,
    children: r.map((c, j) => cell(c, widths[j], i === 0 ? { bold: true, fill: headFill, color: NAVY } : { fill: i % 2 ? undefined : ALT })) })),
});
const h1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 300, after: 100 },
  children: [new TextRun({ text: t, font: "Arial", color: NAVY })] });
const para = (parts, after = 100) => new Paragraph({ spacing: { after }, children: parts });
const count = (f) => rows.filter(f).length;

const answerable = count(r => r.answerable);
const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: `Gold Set v2.2: ${rows.length} questions on the Data team's ten companies`, font: "Arial", color: NAVY })] }),
  para([run(`KPMG × Columbia QMSS · Evaluation & Testing · generated from data/benchmark_v2_2.jsonl (sha256 ${HASH}) by scripts/export_gold_v2_docx.js; do not edit by hand. Questions and expected answers are those of v2; v2.1 (11/9) corrected text anchors, v2.2 (11/11) adds the grading fixes from RAG\u2019s end-to-end round 1 (all figures required on 7 multi-part questions, sig-fig floor at printed precision, EV1R-002/006 routed to text, the last 4 anchors)`, { color: MUTED })], 140),
  para([run("What it is. ", { bold: true }),
    run(`The round-1 question set: ${rows.length} questions, ${answerable} answerable, on the ten companies and 21 filings in the Data team's database snapshot of 2026-11-03 ` +
        "(the same 21 filings as Data's round-1 freeze list). It replaces the 139-question round-1 draft; Gold Set v1 (100 questions) stays frozen so earlier scores still compare.")]),
  para([run("Expected answers. ", { bold: true }),
    run("Numbers are computed from SEC XBRL facts and checked against the filings (55/55 re-reads agree; the nine non-Microsoft income statements match). Exhibit 21 " +
        "answers were transcribed and read twice, and agree with GraphRAG's own Exhibit 21 output on all 62 rows we hold. Amounts are USD millions unless stated.")]),
  para([run("Columns. ", { bold: true }),
    run("Route = the tool a question needs (Eval's label, for Agents to review). Answer = exact number, exact text, narrative, refuse, or correct a false premise. " +
        "Status = how the expected answer was checked; \"Needs human review\" marks text answers (mostly the RAG team's v0 wording) still flagged for a person to check against the filing.")], 160),
];

// summaries
const routes = ["sql", "text", "graph", "multi", "none"];
const byCo = [["Company", "Questions", "Answerable", ...routes.map(r => ROUTE[r])]];
for (const t of ORDER) {
  const qs = rows.filter(r => r.tickers.length === 1 && r.tickers[0] === t);
  byCo.push([`${NAMES[t]} (${t})`, qs.length, qs.filter(r => r.answerable).length, ...routes.map(x => qs.filter(r => r.route_expected === x).length)]);
}
const multi = rows.filter(r => r.tickers.length !== 1);
byCo.push(["Across companies", multi.length, multi.filter(r => r.answerable).length, ...routes.map(x => multi.filter(r => r.route_expected === x).length)]);
byCo.push(["All", rows.length, answerable, ...routes.map(x => count(r => r.route_expected === x))]);
children.push(h1("Summary by company and route"), table([2600, 1050, 1150, 1300, 1150, 1950, 1700, 1700], byCo));

const types = [...new Set(rows.map(r => r.type))];
const byType = [["Question type", "Questions", "Exact number", "Exact (text)", "Narrative", "Refuse", "Correct premise", "Needs human review"]];
for (const t of types) {
  const qs = rows.filter(r => r.type === t);
  byType.push([t.replace(/_/g, " "), qs.length, ...["exact_numeric", "exact_categorical", "narrative", "refusal", "false_premise"].map(a => qs.filter(r => r.answer_type === a).length),
    qs.filter(r => r.status === "needs_human_review").length]);
}
children.push(h1("Summary by question type"), table([2600, 1050, 1300, 1300, 1200, 1100, 1450, 1700], byType));

const fil = [["Company", "Form", "Period end", "Accession", "Database status"]];
for (const f of snap.filings) fil.push([`${NAMES[f.ticker]} (${f.ticker})`, f.form, f.period_end, f.accession, f.db_status]);
children.push(h1(`The ${snap.filings.length} filings (Data database snapshot 2026-11-03)`), table([3200, 1000, 1500, 3000, 2000], fil));

// questions by company, then cross-company
const head = ["ID", "Question", "Expected answer", "Route", "Answer", "Status"];
const qRow = r => [r.qid, r.question, r.answer.display || "", ROUTE[r.route_expected] || r.route_expected,
  ANSWER[r.answer_type] || r.answer_type, STATUS[r.status] || r.status];
for (const t of ORDER) {
  const qs = rows.filter(r => r.tickers.length === 1 && r.tickers[0] === t);
  children.push(h1(`${NAMES[t]} (${qs.length})`), table(W, [head, ...qs.map(qRow)]));
}
children.push(h1(`Across companies (${multi.length})`), table(W, [head, ...multi.map(qRow)]));

const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 17 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 34, bold: true }, paragraph: { spacing: { after: 80 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true }, paragraph: { outlineLevel: 0 } },
    ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE },
      margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ children: [`Gold Set v2.2 · ${HASH} · Page `, PageNumber.CURRENT], font: "Arial", size: 16, color: MUTED })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(b => {
  const out = path.join(ROOT, "data", "benchmark_v2_questions.docx");
  fs.writeFileSync(out, b);
  console.log("[docx] wrote", out, rows.length, "questions, hash", HASH);
});
