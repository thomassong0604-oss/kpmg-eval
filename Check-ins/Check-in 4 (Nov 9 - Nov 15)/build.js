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
const h = t => new Paragraph({ keepNext: true, spacing: { before: 200, after: 80 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 2 } },
  children: [run(t, { bold: true, size: 23, color: NAVY })] });
const sub = t => new Paragraph({ keepNext: true, spacing: { before: 100, after: 40 }, children: [run(t, { bold: true, size: 19, color: NAVY })] });
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
    new Paragraph({ spacing: { after: 20 }, children: [run("Weekly Team Check-In 4: Evaluation & Testing", { bold: true, size: 30, color: NAVY })] }),
    new Paragraph({ spacing: { after: 120 }, children: [run("KPMG × Columbia QMSS Practicum (5052) · Since Check-In 3: Nov 9 – Nov 15, 2026 (KPMG meeting 11/12; next meeting 11/19)", { size: 18, color: MUTED })] }),
    info([
      ["Workstream", "Evaluation & Testing: measure whether the SEC-filings assistant's answers can be trusted"],
      ["Team leads", "Chuan-Yeu (Thomas) Song, Binyu Wang"],
      ["Members and roles", "Shenyi Feng (numeric accuracy) · Fei Huang (citation support) · Shuhan Bian (retrieval metrics; RAG liaison) · Yupin Wang (refusal/abstention) · Ruofei Duan (GraphRAG metrics; GraphRAG liaison) · Bo Yuan (latency, cost, consistency) · Binyu Wang (reasoning steps; Agents liaison) · Thomas Song (gold set; Data and KPMG liaison)"],
      ["Where the work is", "GitHub thomassong0604-oss/kpmg-eval → Week 8/ (presented 11/12, re-score added 11/14); 101 automated tests passing; COMMS_W8.md has every message we sent"],
    ]),

    h("1. Progress since the previous check-in"),
    p("**In one line:** round 1 ran with every team, the project has its first answer-level result, and the other teams have already shipped fixes for what round 1 found."),
    sub("Round 1 on the frozen snapshot (Check-In 3, next step 1)"),
    b("**RAG, retrieval (11/9).** RAG ran our scorer on its round-1 corpus. Hybrid search found the evidence for **105/124** questions (numbers 83/93, prose 22/31). Of the 19 misses, 6 need several filings at once, 6 are ranking, 3 are missed by every method, and 4 were our own bad anchors."),
    b("**RAG, end to end (11/11): the first answer-level result.** RAG ran its reader with its own API key and sent us the answers. On Gold Set v2.2: **89/94 numbers right (0.947)**, **12/12** unanswerable questions declined, 6/7 false premises corrected. Citations: 185/185 cited chunks exist and 127/127 answers cite a filing the gold answer uses. We reproduced RAG's own figures exactly (87/93, 0.977, 10/10)."),
    b("**Why 16 answerable questions were declined:** 10 are outside RAG's corpus (7 Exhibit 21, 3 NetApp's 10-Q, held for review by Data), 3 are cross-company rankings, 2 state the right number but flag it as not answered, 1 is a retrieval miss."),
    b("**GraphRAG, both arms (11/11).** GraphRAG ran our script on its live graph and its 20-filing store. Structured search: needed figure in the top 10 for **63/93**, at rank 1 for **26/93**. We re-ran it on their store and matched **155/155** questions. The graph arm was scored for the first time: prose 10/38. That is mostly scope: **10/20** inside the five section types the graph holds, 0/18 outside them (10 in the notes to the statements, 8 on Exhibit 21 or NetApp's 10-Q, which the graph does not hold)."),
    b("**Re-score after GraphRAG's fixes (11/14).** GraphRAG changed its ranking on 11/11 and 11/13 (PRs #72, #76). Same store, same questions, same script: rank 1 is right on **60/93, up from 26/93**, with no question lost; a known wrong figure at rank 1 fell from 5/42 to 2/42; the top 10 is unchanged at 63/93. This matches GraphRAG's own figure (64.5%)."),
    sub("Gold Set v2.1 and v2.2 (next step 2)"),
    b("**v2.1 (11/9):** 25 questions re-anchored after RAG's run flagged 4. **v2.2 (11/11):** same 155 questions and answers; grading only, from RAG's three notes. Precision floor set to what the filing prints (2 questions); all values required on 7 multi-part questions; 2 routes relabelled; one evidence item per point (22 questions); 4 anchors added. Published with a hash and a change log."),
    b("**Hop counts and narrative judge:** GraphRAG's hop file merged with ours (44 questions carry a hop count; the one difference is an ontology choice, not a counting error). An LLM judge for narrative answers is built but not run; it needs an API key (section 4)."),
    sub("Agents' API v0.2 (next step 3)"),
    b("**Runner and grader ready the day the contract arrived (11/11).** One command sends all 155 questions to /query; the grader scores decisions, evidence, citations, filters and the Agents' four fallback cases."),
    b("**Fallback test set from round-1 evidence:** of 155 questions, RAG already answers 127 (fallback must not break them), **1 is a clean rescue**, 2 have the answer in RAG's evidence, 3 need one search per company, 7 wait on Exhibit 21, 3 are not in the corpus, 12 must still abstain."),
    sub("11/5 feedback closed; 11/12 presentation"),
    b("**Routing chart relabelled as coverage, not accuracy:** text search only 21.3% of questions get every tool they need; keyword router 82.6% at 1.05 calls; every tool 94.8% at 3.00 calls (2.05 unneeded)."),
    b("**Messy wording (427 rewrites):** misspelled company names cut right decisions from **98% to 19%**; loose name matching restores **94%**."),
    b("**Presented 11/12:** 6 slides for a 10-minute slot plus 8 appendix slides; every number in the script is checked against the results files at build time."),
    sub("Status of Check-In 3's next steps"),
    table([3000, 1250, 5590], [
      ["Planned", "Status", "Detail"],
      ["1. Run round 1 on the snapshot, by route and type, with latency and cost", "Done, one part open", "RAG at retrieval and answer level; GraphRAG on both arms; run on 20 of 21 filings (NetApp's 10-Q is held by Data). **Open: latency and cost.** Only GraphRAG's structured search is timed (median 96 ms per call); the reader ran on RAG's side, so we have no token counts."],
      ["2. Finish anchors, widen thin areas, publish Gold Set v2.1", "Partly", "v2.1 and v2.2 published with hash and change log. **Not done:** 40 lookups are still scored by figure only (no text anchor); the \"both\" (1) and \"no tool\" (8) routes were not widened; the 427 rewrites are still a separate suite. Round 1 took the week."],
      ["3. Score the Agents' real orchestrator", "Not yet", "Runner, grader and fallback set are ready and the reply is sent (Chinese and English). Waiting on the Agents' first run; v0.2 returns no answer text yet, so it will cover decisions and evidence."],
    ]),
    sub("Feedback received and how we responded"),
    table([4700, 5140], [
      ["Feedback", "Response"],
      ["RAG 11/9: 4 gold anchors cannot be found in the filing text", "They were ours. Re-anchored 25 questions (v2.1); later split anchors to one per point because RAG's chunker separates sentences (v2.2)"],
      ["RAG 11/11: three grading notes (precision stricter than the filing prints; multi-part answers; questions RAG cannot route)", "All three accepted; they became Gold Set v2.2. NAA moved from 87/94 to 89/94"],
      ["GraphRAG 11/11: score the graph arm; send {ticker, accession_number}; do not count a dropped database connection as a failure; two questions mislabelled in our gold", "Graph arm scored; filters translated for every question; dropped connections retried and reported apart; EV3-008/009 relabelled (our mislabel)"],
      ["Agents 11/11: align our gold set and runner with API v0.2; test four fallback cases together", "Field-by-field mapping, runner, grader and a fallback case for every question (AGENTS_API_W8.md)"],
    ]),
    sub("What the other teams shipped in response; our decisions and deliverables"),
    b("**RAG:** contract v1.2 with a multi-filing search (11/11), aimed at the 6 misses that need several filings. **GraphRAG:** list filters (#70), ranking (#72, #76), Exhibit 21 pipeline merged (#75, 11/12), and a search envelope that uses our four decisions: answer, clarify, abstain, block (#66). **Data:** a profile that records a company's tagging errors instead of rejecting the filing (PR #27). This pace is why a re-score is our first priority."),
    b("**Decisions:** Gold Set v2.2 is the round-1 set. Questions whose filing is not in the corpus are reported apart, not as failures. Callers send GraphRAG {ticker, accession_number}. Other teams' data stays out of our public repo, since Data keeps exports off GitHub."),
    b("**Delivered:** deck and script for 11/12; graders for external answers and for the Agents' API; the re-score; replies to RAG (two), GraphRAG (four) and Agents."),

    h("2. Current priorities"),
    b("**Round 2: re-score what the teams changed.** RAG's multi-filing search with the reader, GraphRAG's graph arm on v2.2 and Exhibit 21 once loaded, this time with latency and cost. Shenyi Feng, Shuhan Bian, Ruofei Duan, Bo Yuan."),
    b("**First score of the Agents' API**, with and without fallback. Binyu Wang, Yupin Wang."),
    b("**Grade the narrative answers.** 28 answered narrative questions are still unverified. Hand-label first, then validate and run the judge. Fei Huang, Thomas Song."),
    b("**Gold Set v2.3 and the 11/19 meeting.** Widen the thin routes and add fallback questions; present round 1 against round 2. Thomas Song, Binyu Wang."),

    h("3. Next steps before the next check-in"),
    table([360, 4400, 2350, 2730], [
      ["#", "Action", "Owner(s)", "Done when"],
      ["1", "Round 2 on each team's latest code: RAG with multi-filing search and reader; GraphRAG's graph arm on Gold Set v2.2, and Exhibit 21 questions once the edges are in the served graph. Log latency and token cost per question", "Shenyi Feng (lead), Shuhan Bian (RAG), Ruofei Duan (GraphRAG), Bo Yuan (latency, cost)", "Round 1 vs round 2 table per team on GitHub (Week 9/), with latency and cost for every component that calls a model; changed questions listed by id"],
      ["2", "Score the Agents' API v0.2 on Gold Set v2.2, with and without fallback: decisions, evidence, citations, filters, and the four fallback cases", "Binyu Wang (lead), Yupin Wang (abstention cases)", "Results on GitHub and shared in the Agents thread; rescued and broken questions listed by id"],
      ["3", "Grade narrative answers and publish Gold Set v2.3. Two people hand-label the 28 narrative answers; run the judge and report agreement. v2.3: more \"both\", \"no tool\" and fallback questions, text anchors for the 40 lookups, messy rewrites as a slice", "Thomas Song (lead), Fei Huang (labels, anchors), Yupin Wang (unanswerable questions)", "Agreement (kappa) reported between labellers and with the judge; v2.3 published with a hash and change log"],
    ]),

    h("4. Challenges and blockers"),
    b("**Narrative answers are ungraded.** The judge needs an API key and has not been checked against hand labels. **Risk:** our answer-level result covers numbers and refusals but not prose (30 of 143 answerable questions). **Mitigation:** hand labels need no key and come first; we will ask RAG to run the judge with its key, as it did the reader."),
    b("**We cannot reach the other teams' services.** Our workspace cannot connect to GraphRAG's graph, the Agents' API or Data's database, so those teams run our scripts and send files back. **Risk:** turnaround depends on their time. **Mitigation:** each run is one command; we reproduce what we can on shared stores (155/155 on GraphRAG's) and pin every commit."),
    b("**The corpus can move under the gold set.** NetApp's 10-Q is held, so 3 questions cannot be answered by any team. Data's new profile may release it, which would change the corpus from 20 to 21 filings. Microsoft's FY2024 and FY2025 10-Ks are not loaded, which limits multi-year questions. **Mitigation:** a snapshot hash on every result; a joint request to Data with GraphRAG."),
    b("**Fallback is hard to test with today's questions.** Only 1 of 155 is a clean rescue. **Risk:** the Agents' fallback would look neutral whatever its quality. **Mitigation:** v2.3 adds questions where RAG's evidence is weak and GraphRAG's is strong; meanwhile we score that fallback does not break the 127."),
    b("**Two gaps carried over.** Latency and cost are unmeasured end to end, so we can compare routing options only by call counts (next step 1). The gold set is still skewed: Microsoft has 92 of 143 answerable questions and one question needs both tools (next step 3)."),
    b("**Our own errors this week.** Four bad anchors; a precision rule stricter than the filing; two mislabelled questions; a question to RAG that Data's repo already answered. On 11/14 we also found our number matching was too loose for per-share values: no presented result changed, and one figure sent to GraphRAG (5/36, not 6/36) is corrected. **Mitigation:** each fix has a test and a change-log entry; we now read a team's repo before asking."),

    h("5. Cross-team coordination and support needed"),
    table([1500, 8340], [
      ["From", "Request"],
      ["Data", "Tell us before the corpus changes from the 20 filings used in round 1, and whether NetApp's 10-Q will be released. Load Microsoft's FY2024 and FY2025 10-Ks (joint request with GraphRAG). Thank you: your NetApp source review answered our question before we asked it."],
      ["RAG", "Run round 1 again with the multi-filing search and send the answers, with latency and token counts per question. Run our narrative judge with your key (one command). Two answers state the right number but are flagged not answered (GSv0-MSFT-023, EV1R-005). Thank you: you gave the project its first end-to-end numbers, and your three notes made the gold set fairer."],
      ["GraphRAG", "Run the graph arm once more on Gold Set v2.2. Load the Exhibit 21 edges into the served graph (7 questions wait on it). Two rank-1 cases to look at: EV1-004 (basic EPS ahead of diluted) and EV1-011. Thank you: your ranking fixes landed within two days and moved rank 1 from 26 to 60 of 93."],
      ["Agents", "A first /query run on Gold Set v2.2, with and without fallback (one command; send the file privately). An answer field in the next version so we can score answers. Loose company-name matching before the demo. Thank you for sharing the contract early; it mapped onto our grader unchanged."],
      ["KPMG", "Examples of real analyst wording for the messy-wording set. A target for round 2: does the right figure need to rank first, or only appear in the evidence?"],
      ["Instructor / TAs", "A small API budget or key for the narrative judge (about 30 answers per run). Whether two-person hand labels are enough validation for an LLM judge in this course."],
    ]),
  ] }],
});
Packer.toBuffer(doc).then(buf => fs.writeFileSync("Eval_Weekly_CheckIn_4.docx", buf));
