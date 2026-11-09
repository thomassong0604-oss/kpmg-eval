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
    new Paragraph({ spacing: { after: 20 }, children: [run("Weekly Team Check-In 3: Evaluation & Testing", { bold: true, size: 30, color: NAVY })] }),
    new Paragraph({ spacing: { after: 120 }, children: [run("KPMG × Columbia QMSS Practicum (5052) · Since Check-In 2: Nov 2 – Nov 8, 2026 (KPMG meeting 11/5; next meeting 11/12)", { size: 18, color: MUTED })] }),
    info([
      ["Workstream", "Evaluation & Testing: measure whether the SEC-filings assistant's answers can be trusted"],
      ["Team leads", "Chuan-Yeu (Thomas) Song, Binyu Wang"],
      ["Members and roles", "Shenyi Feng (numeric accuracy) · Fei Huang (citation support) · Shuhan Bian (retrieval metrics; RAG liaison) · Yupin Wang (refusal/abstention) · Ruofei Duan (GraphRAG metrics; GraphRAG liaison) · Bo Yuan (latency, cost, consistency) · Binyu Wang (reasoning steps; Agents liaison) · Thomas Song (gold set; Data and KPMG liaison)"],
      ["Where the work is", "GitHub thomassong0604-oss/kpmg-eval → Week 7/ (presented 11/5) and Week 8/ (for 11/12); 82 automated tests passing; FOR_TEAMS_W8.md has one section per team"],
    ]),

    h("1. Progress since the previous check-in"),
    sub("Moved the gold set onto the Data team's ten companies and database (Gold Set v2)"),
    b("**Matched our filing list to Data's database** (21 filings as of 11/03). Our earlier list matched 20/21; the difference was Micron's FY2026 10-K (filed 10/09), which we had as FY2025. Gold Set v2 matches **21/21**, and all 21 are in Data's 233-filing 2021–2026 inventory."),
    b("**Gold Set v2: 155 questions, 143 answerable**, replacing the 139-question round-1 draft. Every answerable question is on the ten companies (Microsoft, the MVP, has 92; the others 9–16 each). Each question now records the route it needs: **104 finance data, 31 text, 11 relationship, 8 no tool, 1 both**."),
    b("**7 relationship questions from Exhibit 21** (subsidiary lists: Apple 19, Casey's 9, Micron 21, each transcribed and read twice). With the 4 drafted with GraphRAG, **11 questions now require GraphRAG**; 4 of them test invented or false links."),
    b("**Checks:** 55/55 re-reads agree; 18/18 quarterly figures sum to the reported totals; 160/160 grader labels right on the new numeric questions; all nine other companies' income statements, read from the filings, match the gold."),
    b("**SEC data issues turned into test questions:** NetApp tags 3 of its 10-Qs one fiscal year behind its own text; McKesson's and Medtronic's statement net income includes noncontrolling interests (McKesson 5,099 vs 4,762), so questions now say which one and the other is scored as a wrong answer."),
    sub("Measured the Agents' decisions and routing (KPMG 10/29 request)"),
    b("**Answer / clarify / abstain / block:** drafted the rules (POLICY_answer_clarify_abstain.md; no tool calls on off-topic questions, as KPMG asked) and a 24-item test suite. On 179 questions, answering everything gives **100% unsafe answers** on questions that should not be answered and 8 off-topic tool calls; a simple scope check gives **96.1% right decisions**, 0 off-topic calls, 0 needless refusals, 13.9% unsafe (5 questions left)."),
    b("**Routing:** scorer for any router. Text search only: 20% of questions get the tool they need; our keyword router: 84% at 1.05 calls/question; calling every tool: 95% at 3.00 calls (2.05 unneeded)."),
    sub("RAG and GraphRAG side by side; real-user wording (KPMG 11/5 requests)"),
    b("**Same filing, each team's own code, 84 Microsoft 10-Q questions.** Needed figures in the top 8: **RAG 49/50, GraphRAG 25/50**; prose passages: **18/27 vs 0/27** (GraphRAG's structured search stores numbers only). GraphRAG shows the wrong-period figure less often (**19/36 vs 33/36**) because its facts carry their period."),
    b("**Where each does better:** relationship questions favour GraphRAG. RAG does not index Exhibit 21, while traversing GraphRAG's own Exhibit 21 rows answers all 9 exactly (their rows match our gold reads 62/62). RAG is better at prose and at finding numbers. We traced GraphRAG's 25 misses so it can fix them: 13 ranked just below the top 8 (total revenue ranks 10th behind \"Microsoft 365\" product rows), 10 calculations needing several facts from one call, 2 wording."),
    b("**Typos and messy wording:** 427 rewrites with the same meaning. With no company selected, the scope check drops from **98% to 19%** on misspelled names; matching tickers and near-miss spellings restores **94%**. Misspelled finance words (\"revnue\") cost both searches 9 of 70 questions."),
    b("**Routing for the demo:** chart axes labelled, keyword router and \"unneeded call\" defined (we corrected the minutes' wording), 7 worked examples, and every rate labelled as based on the current 155 questions."),
    sub("Status of Check-In 2's next steps"),
    table([3000, 1250, 5590], [
      ["Planned", "Status", "Detail"],
      ["1. Score numeric accuracy with RAG's fixed reader, by route", "Partly", "Reader built and tested with a stub (gpt-4o-mini, temperature 0, RAG's prompt); every scorecard reports accuracy by route. **Not yet run: no API key** (see blockers)."],
      ["2. Complete round-1 gold set and anchors", "Re-scoped", "Replaced by Gold Set v2. RAG's draft anchors reviewed (results/rag_anchor_fixes.csv: 10 drop incl. 8 Amazon/Meta, 2 remove, 25 narrow, 17 with ready replacements); Exhibit 21 anchors in. Text anchors for new lookups wait on Data's chunks."],
      ["3. GraphRAG and Agents hand-offs", "Partly", "Hops sheet extended to 165 questions; GraphRAG's real fact loader and search now run in our harness (no longer only the mock), and their Exhibit 21 output checks out against our reads (62/62); graph arm still needs a database. Decision rules sent to Agents with a request for a decision field in the AnswerBlock."],
    ]),
    sub("Feedback received and how we responded"),
    table([3500, 6340], [
      ["Feedback", "Response"],
      ["KPMG 10/29: match the filing list with Data; bring in Exhibit 21", "21/21 match; Micron corrected; 7 Exhibit 21 questions"],
      ["KPMG 10/29: when should the Agent answer, ask, or abstain; compare routing with combined retrieval", "Rules, 24-item suite and two scorers delivered; results above"],
      ["KPMG 11/5: run RAG and GraphRAG side by side; show where each is better", "Done on the full Microsoft 10-Q set plus 9 relationship questions"],
      ["KPMG 11/5: label routing axes; define keyword router and unneeded calls; demo examples; say results use 155 questions", "Done (Week 8 slides 4–5, ROUTING_EXAMPLES.md)"],
      ["KPMG 11/5: test typos and messy wording", "427 rewrites through scope check, router and both searches"],
      ["RAG: what to do with 8 Amazon/Meta questions; freeze a data snapshot", "Drop them (outside the ten); proposed Data's 11/03 database as the round-1 snapshot"],
    ]),
    sub("Decisions and deliverables"),
    b("**Decisions:** Gold Set v2 is the round-1 set (Gold Set v1 stays frozen for comparability); comparison questions name the 11/03 snapshot date so later loads cannot change answers; results are reported at evidence level, labelled as such, until a reader can run; every result pins the commit of each team's code it used."),
    b("**Delivered:** 6 Eval slides for 11/5, 7 for 11/12 (with speaker notes); Week 7 and Week 8 code, data and results on GitHub; FOR_TEAMS notes per week; Slack updates to RAG (anchor review, snapshot) and GraphRAG (how their retrieval reads the database, where our files are)."),

    h("2. Current priorities"),
    b("**Round 1 on the frozen snapshot (week 8):** score RAG and GraphRAG on Gold Set v2 by route and question type, with cost and latency. Shenyi Feng, Shuhan Bian, Ruofei Duan, Bo Yuan."),
    b("**11/12 KPMG meeting:** present the side-by-side and walk through the routing examples. Thomas Song, Binyu Wang."),
    b("**Gold set coverage:** text anchors for new questions; more questions where the set is thin; the messy rewrites as a robustness slice. Thomas Song, Fei Huang, Yupin Wang."),

    h("3. Next steps before the next check-in"),
    table([360, 4400, 2350, 2730], [
      ["#", "Action", "Owner(s)", "Done when"],
      ["1", "Run round 1 on the 21-filing snapshot: RAG (retriever + fixed reader if a key is available) and GraphRAG's structured search on Gold Set v2, by route and question type; log latency and cost per question", "Shenyi Feng (lead), Shuhan Bian (RAG), Ruofei Duan (GraphRAG), Bo Yuan (cost, latency)", "Round-1 scorecard on GitHub (Week 9/) and shared in the RAG and GraphRAG threads; answer-level if a key exists, otherwise evidence-level, labelled"],
      ["2", "Finish anchors and widen thin areas: text anchors once Data's chunks land; more questions on non-Microsoft companies and on the \"both\" (1) and \"no tool\" (8) routes; add the 427 rewrites as a robustness slice", "Thomas Song (lead), Fei Huang (anchors), Yupin Wang (unanswerable)", "Every answerable question has a verified anchor; Gold Set v2.1 published with a hash and change log"],
      ["3", "Score the Agents' real orchestrator instead of our stand-in rules: routing and decision scorers, agreed expected routes, ticker and near-miss name matching", "Binyu Wang (lead), Yupin Wang", "Orchestrator scores next to our reference rules on the same 179 questions"],
    ]),

    h("4. Challenges and blockers"),
    b("**No API key yet.** The fixed reader is ready but cannot run, so all results are at evidence level (is the right number or passage in what the system retrieved?). **Risk:** round 1 cannot report answer accuracy, KPMG's headline metric. **Mitigation:** evidence-level results are exact and reproducible; key requested (section 5)."),
    b("**GraphRAG's graph cannot be scored yet.** It needs a Neo4j database we cannot reach. Their new Exhibit 21 output for the ten companies (pushed 11/8 on a branch) agrees with our gold reads on all 62 rows we hold, but is not yet merged or loaded into the graph. **Mitigation:** we scored the structured arm with their own code (latest main), traverse their Exhibit 21 rows ourselves, and pin the exact commits."),
    b("**Thin, skewed gold set.** Microsoft has 92 of 143 answerable questions; only 1 question needs both tools and 8 need none, so per-route rates on these are examples, not estimates. KPMG asked us to say this, and every number is labelled. Next step 2 addresses it."),
    b("**Side-by-side limited to one filing.** RAG built its round-1 corpus for all 21 filings on 11/5 (its freeze list matches ours 21/21), but the chunks live in Data's database, not the repo. Getting them unblocks both text anchors and a ten-company comparison."),
    b("**SEC data pitfalls, including one we got wrong.** The SEC data API lagged Micron's FY2026 10-K, so on 10/29 we said it was not in the corpus; we corrected this on 11/5 and now check the filing documents, not the API alone. NetApp's mislabelled fiscal year can mislead every team's filters."),
    b("**Real-user wording.** Misspelled company names and finance words break simple matching (above). The fixes are small but sit with Agents, RAG and GraphRAG before the demo."),
    b("**Coordination.** Our expected routes and decision rules are Eval's labels until Agents review them. The 11/5 minutes described \"unneeded calls\" differently from our metric; we clarified it in writing so no team optimises the wrong thing."),

    h("5. Cross-team coordination and support needed"),
    table([1500, 8340], [
      ["From", "Request"],
      ["Data", "Keep the 11/03 freeze list (21 filings, matches ours 21/21) fixed through round 1, with no reloads. Thank you for the 233-filing inventory, which made the filing match possible."],
      ["RAG", "Share the round-1 chunks for the 21 filings (privately; Data keeps exports off GitHub); let the router send Exhibit 21 questions to GraphRAG; an API key for the fixed reader (or who holds one). Thank you: your retriever ran in our harness unchanged."],
      ["GraphRAG", "A Neo4j endpoint so we can score the graph arm; merge and load the new Exhibit 21 output; treat \"three/six months\" as period words (they match Microsoft 365 rows and push totals out of the top 8); two concept aliases. Thank you: your fact loader ran unchanged and your Exhibit 21 rows matched ours."],
      ["Agents", "Run your orchestrator through our routing and decision scorers; review our expected routes; ticker and near-miss name matching in the scope check; a decision field in the AnswerBlock."],
      ["KPMG", "Confirm the unneeded-call definition and demo examples show what you want; examples of real analyst wording or common misspellings, to make the messy-wording set realistic; a target accuracy for round 1, if you have one."],
      ["Instructor / TAs", "An API budget or key for the fixed reader; whether round 1 may report evidence-level scores for components without a reader."],
    ]),
  ] }],
});
Packer.toBuffer(doc).then(buf => fs.writeFileSync("Eval_Weekly_CheckIn_3.docx", buf));
