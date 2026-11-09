const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, LevelFormat } = require("docx");

const NAVY = "2F3E96", INK = "1E2530", MUTED = "5C6675";
const border = { style: BorderStyle.SINGLE, size: 4, color: "C9CED8" };
const borders = { top: border, bottom: border, left: border, right: border };
const TW = 9840;

const run = (t, o = {}) => new TextRun({ text: t, font: "Arial", size: o.size || 19, bold: o.bold, italics: o.italics, color: o.color || INK });
function rich(s, size) { // **bold** segments
  return s.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(p => p.startsWith("**") ? run(p.slice(2, -2), { bold: true, size }) : run(p, { size }));
}
const h = t => new Paragraph({ spacing: { before: 200, after: 80 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 2 } },
  children: [run(t, { bold: true, size: 23, color: NAVY })] });
const sub = t => new Paragraph({ spacing: { before: 100, after: 40 }, children: [run(t, { bold: true, size: 19, color: NAVY })] });
const b = (s, lvl = 0) => new Paragraph({ numbering: { reference: "bul", level: lvl }, spacing: { after: 30 }, children: rich(s) });
const p = (s, o = {}) => new Paragraph({ spacing: { after: 60 }, children: rich(s, o.size) });

function table(widths, rows, headFill = NAVY) {
  return new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: widths, rows: rows.map((r, i) => new TableRow({
    cantSplit: true, tableHeader: i === 0, children: r.map((c, j) => new TableCell({
      width: { size: widths[j], type: WidthType.DXA }, borders,
      shading: { fill: i === 0 ? headFill : (j === 0 && widths.length === 2 && headFill === "EEF2FF" ? "EEF2FF" : (i % 2 === 0 ? "F6F7FB" : "FFFFFF")), type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 50, bottom: 50, left: 90, right: 90 },
      children: [new Paragraph({ children: i === 0 ? [run(c, { bold: true, size: 18, color: "FFFFFF" })] : rich(c, 18) })] })) })) });
}
function info(rows) {
  const w = [2100, TW - 2100];
  return new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: w, rows: rows.map(([a, c]) => new TableRow({ children: [
    new TableCell({ width: { size: w[0], type: WidthType.DXA }, borders, shading: { fill: "EEF2FF", type: ShadingType.CLEAR, color: "auto" }, margins: { top: 50, bottom: 50, left: 90, right: 90 }, children: [new Paragraph({ children: [run(a, { bold: true, size: 18 })] })] }),
    new TableCell({ width: { size: w[1], type: WidthType.DXA }, borders, margins: { top: 50, bottom: 50, left: 90, right: 90 }, children: [new Paragraph({ children: rich(c, 18) })] }) ] })) });
}

const doc = new Document({
  numbering: { config: [{ reference: "bul", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 300, hanging: 220 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 640, hanging: 220 } } } } ] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 860, bottom: 860, left: 1200, right: 1200 } } }, children: [
    new Paragraph({ spacing: { after: 20 }, children: [run("Weekly Team Check-In 2: Evaluation & Testing", { bold: true, size: 30, color: NAVY })] }),
    new Paragraph({ spacing: { after: 120 }, children: [run("KPMG × Columbia QMSS Practicum (5052) · Since the midpoint presentation, Oct 26 – Nov 1, 2026", { size: 18, color: MUTED })] }),
    info([
      ["Workstream", "Evaluation & Testing: measure whether the SEC-filings assistant's answers can be trusted"],
      ["Team leads", "Chuan-Yeu (Thomas) Song, Binyu Wang"],
      ["Members and roles", "Shenyi Feng (numeric accuracy) · Fei Huang (citation support) · Shuhan Bian (retrieval metrics; RAG liaison) · Yupin Wang (refusal/abstention) · Ruofei Duan (GraphRAG metrics; GraphRAG liaison) · Bo Yuan (latency, cost, consistency) · Binyu Wang (reasoning steps; Agents liaison) · Thomas Song (gold set; Data and KPMG liaison)"],
      ["Where the work is", "GitHub thomassong0604-oss/kpmg-eval → Week 6/ (code, data, results; 63 automated tests passing)"],
    ]),

    h("1. Progress since the previous check-in"),
    sub("Narrowed the gold set to the Data team's 10 companies"),
    b("Data screened its database (448 filings) and proposed **AAPL, CASY, MCK, MDT, MSFT, MU, NKE, NTAP, PH, TTWO** (21 filings: 10 10-Ks, 11 10-Qs). We rebuilt the gold set around them within a day."),
    b("**Round-1 gold set: 139 questions** = 90 kept from Gold Set v1 + **49 new** questions on the added companies (34 lookups, 5 ten-company comparisons, 3 fiscal-calendar, 2 calculations, 5 unanswerable/false-premise). 10 questions that needed Amazon, Meta or NVIDIA were retired."),
    b("Every new answer is computed in code from SEC XBRL data, **read twice: 53/53 values agree**, and **18/18** quarterly figures add up to the reported nine-month totals."),
    b("Grader re-validated on the new questions: **156/156** right and wrong test answers labelled correctly (including negative values and scale errors)."),
    sub("Integrated the GraphRAG team's work"),
    b("Implemented GraphRAG's scoring requests from their eval-ask / eval-reply docs: citations now join on chunk, section or fact id; reruns compare on all three version fields."),
    b("Wired both GraphRAG retrieval arms into our harness on their mock: **87 questions, 174 calls, 0 errors, 87/87 pass our contract checks**."),
    b("Drafted **6 relationship questions** with GraphRAG (subsidiaries, segment changes, acquisitions), including **2 that test invented relationships**, the main way graphs fail. Shared a 155-question hop-count sheet and a one-page summary (Week 6/EVAL_GRAPHRAG.md)."),
    b("Found and fixed a bug in our own scoring: segment figures could count as company totals (27 false matches removed)."),
    sub("Worked with the RAG team"),
    b("Reviewed RAG's evidence anchors for our 100 questions: **97/99** numbers our answers use are covered; returned 2 non-matching and 33 over-broad anchors with fixes."),
    b("RAG ran its retriever on our gold set (their report, 10/28): **recall@8 0.852** overall, 1.00 on segment questions, **0.69 on narrative** (weakest, consistent with our wording-robustness finding)."),
    sub("Decisions and deliverables"),
    b("Gold Set v1 stays frozen (file hash unchanged) so earlier scores remain comparable; Microsoft stays the MVP company; every cross-company question names each company's own fiscal period."),
    b("Delivered: 5 Eval slides for the 10/29 KPMG meeting, Week 6 code and data on GitHub, Slack updates to Data, RAG and GraphRAG."),
    sub("Feedback received and how we responded"),
    table([3300, 6540], [
      ["Feedback", "Response"],
      ["GraphRAG: no question requires following a relationship; no check for invented links", "6 relationship questions drafted, 2 test fabricated links; hops sheet shared for their input"],
      ["GraphRAG: score graph answers by section/fact id, not chunk id", "Done in code and tested"],
      ["RAG: single-number anchors make recall too generous", "Our review confirms it (33 broad anchors); fixes returned"],
      ["RAG: add a fixed reader to measure numeric accuracy, report it by route", "Accepted; next step 1 below"],
    ]),

    h("2. Current priorities"),
    b("**Numeric accuracy on RAG's real retriever** with the fixed reader RAG proposed (GPT-4o-mini, temperature 0), reported overall and by route (structured data vs. text). Shenyi Feng, Shuhan Bian, Bo Yuan."),
    b("**Finishing the round-1 gold set:** evidence anchors for the 49 new questions once Data shares the filing text; human review of 8 flagged items. Thomas Song, Fei Huang, Yupin Wang."),
    b("**GraphRAG and Agents integration:** agree a hop definition, review the relationship questions, agree the Agent's structured answer format (AnswerBlock with trace_id). Ruofei Duan, Binyu Wang."),

    h("3. Next steps before the next check-in"),
    table([360, 4300, 2450, 2730], [
      ["#", "Action", "Owner(s)", "Done when"],
      ["1", "Plug RAG's fixed reader into the harness; score numeric accuracy on the 139-question set, overall and by route; log cost and latency per question", "Shenyi Feng (lead), Shuhan Bian, Bo Yuan", "Scorecard on GitHub and shared with RAG in Slack"],
      ["2", "Complete the round-1 gold set: anchors for the 49 new questions, review of unanswerable/false-premise items, the 10 retired questions removed from RAG's anchor file", "Thomas Song (lead), Fei Huang, Yupin Wang", "All 139 questions have verified anchors; status = reviewed"],
      ["3", "GraphRAG and Agent hand-offs: hop definition agreed and hops filled; harness pointed at GraphRAG's real retriever when ready; AnswerBlock agreed with Agents", "Ruofei Duan (GraphRAG), Binyu Wang (Agents)", "Hop values in hops_v1.csv; written AnswerBlock spec both teams accept"],
    ]),

    h("4. Challenges and blockers"),
    b("**Filing list not yet confirmed.** Data shared counts, not accession numbers. Our assumed list (each company's latest 10-K and 10-Q) reproduces their count exactly, but anchors could target the wrong filing if it differs. **Mitigation:** confirmation requested; rebuild is one script."),
    b("**Six fiscal calendars.** The ten fiscal years end in six different months and the latest 10-Qs fall in three calendar quarters, so all ten cannot be compared on one quarter. **Mitigation:** every comparison question states each company's period."),
    b("**Round 1 (W8) depends on parts still in progress:** GraphRAG's real backend (we tested on their mock) and the Agent's structured answers. If either is late, round 1 reports retrieval only for that component."),
    b("**SEC data quirks** found while building questions: Micron's FY2026 10-K is not in scope, Parker-Hannifin reports net income under a different XBRL tag, Nike and NetApp changed their revenue tag. Each is now a test question, but they also affect the other teams' extraction."),
    b("**Recall can look better than it is** when anchors are bare numbers that appear in several tables (RAG raised this too). Until anchors are fixed, we report recall with that caveat."),
    b("**LLM cost:** the fixed reader and the two LLM-judge metrics need an API key and budget."),
    b("**Team ramp-up:** eight members with mixed coding experience; everyone now needs to clone the repo and join the Slack channels. Thomas and Binyu are running setup help this week."),

    h("5. Cross-team coordination and support needed"),
    table([1500, 8340], [
      ["From", "Request"],
      ["Data", "Confirm the 21 accession numbers; share text chunks for all 21 filings; Exhibit 21 (subsidiaries) for the ten 10-Ks. Thank you for the screening work, which unblocked every team."],
      ["RAG", "Fixed-reader spec and access; fix the 2 non-matching and 33 broad anchors; trace_id and cited chunk ids in the logs."],
      ["GraphRAG", "Hop definition and values; a date for the real backend; 3 small fixes to the output format (units, segment names, unique ids)."],
      ["Agents", "Return the AnswerBlock (value, unit, period, citations, answered/refused) with trace_id."],
      ["KPMG", "Confirm the 10-company scope; what accuracy level counts as \"good enough\" for a numeric answer."],
      ["Instructor / TAs", "Guidance on an API budget for the fixed reader and LLM-judge metrics; whether round 1 may report retrieval-only scores for components not ready by W8."],
    ]),
  ] }],
});
Packer.toBuffer(doc).then(buf => fs.writeFileSync("Eval_Weekly_CheckIn_2.docx", buf));
