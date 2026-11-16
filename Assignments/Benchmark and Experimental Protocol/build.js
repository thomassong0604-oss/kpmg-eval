const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, PageBreak, Table, TableRow, TableCell, WidthType, BorderStyle, AlignmentType } = require("docx");
const F = "Times New Roman", SZ = 24, K = "000000";
const run = (t, o = {}) => new TextRun({ text: t, font: F, size: SZ, color: K, ...o });
const rich = (t, o = {}) => t.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(s => s.startsWith("**") ? run(s.slice(2, -2), { ...o, bold: true }) : run(s, o));
const p = (t, o = {}) => new Paragraph({ spacing: { after: 100, line: 240 }, alignment: AlignmentType.LEFT, ...o, children: rich(t) });
const h = t => new Paragraph({ keepNext: true, spacing: { before: 140, after: 70 }, children: [run(t, { bold: true })] });
const cap = t => new Paragraph({ keepNext: true, spacing: { before: 40, after: 50 }, children: rich(t) });
const bd = { style: BorderStyle.SINGLE, size: 4, color: K };
const table = (widths, rows) => new Table({ width: { size: widths.reduce((a, b) => a + b), type: WidthType.DXA }, columnWidths: widths,
  rows: rows.map((r, i) => new TableRow({ cantSplit: true, tableHeader: i === 0, children: r.map((c, j) => new TableCell({
    width: { size: widths[j], type: WidthType.DXA }, borders: { top: bd, bottom: bd, left: bd, right: bd },
    margins: { top: 30, bottom: 30, left: 80, right: 80 },
    children: [new Paragraph({ keepNext: i < rows.length - 1, spacing: { line: 240 }, children: rich(c, i === 0 ? { bold: true } : {}) })] })) })) });
const ref = t => new Paragraph({ spacing: { after: 70, line: 240 }, indent: { left: 360, hanging: 360 }, children: rich(t) });
const gap = () => new Paragraph({ spacing: { after: 60 }, children: [] });

const num = t => new Paragraph({ spacing: { after: 50, line: 240 }, indent: { left: 360, hanging: 360 }, children: rich(t) });

const doc = new Document({ styles: { default: { document: { run: { font: F, size: SZ, color: K } } } },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children: [
  new Paragraph({ spacing: { after: 40 }, children: [run("Benchmark & Experimental Protocol", { bold: true })] }),
  p("**Team:** Evaluation & Testing   **Date:** November 16, 2026", { spacing: { after: 40 } }),
  p("**Contributors:** Chuan-Yeu (Thomas) Song and Binyu Wang (co-leads), Shenyi Feng, Fei Huang, Shuhan Bian, Yupin Wang, Ruofei Duan, Bo Yuan"),

  h("1. Project Component and Evaluation Objectives"),
  p("The KPMG project is an assistant that answers questions about SEC 10-K and 10-Q filings. The Evaluation & Testing team does not build a part of the assistant. We build what tells the other teams, and KPMG, whether its answers can be trusted: a benchmark of questions with verified answers (the Gold Set), a library of graders, and a harness that scores RAG, GraphRAG and the Agents with the same code. Each team runs its own system on our questions and we return a scorecard and a list of misses by cause."),
  p("Three questions drive our testing:"),
  num("1. **Is an answer right, and does the system decline when it should?** For an auditor, a confident wrong number is the costliest failure, so numeric accuracy and correct refusal are KPMG's headline measures."),
  num("2. **Which retrieval method finds the evidence for which kind of question, and does routing send each question to the tool it needs at a reasonable cost?** The Agents must choose between RAG and GraphRAG, or call both, and that choice should rest on measured results."),
  num("3. **Do the results hold on questions nobody tuned on, and on the way people really type?** Every team has tuned on the same 155 questions, so the final report needs a clean test and a robustness check."),
  p("These questions matter beyond our team because every design decision left in the project (routing rules, fallback, the answer format, what the demo may claim) depends on one of them, and because results from different teams are only comparable if one benchmark and one set of graders produce them.", { spacing: { before: 50, after: 100 } }),

  h("2. Benchmark or Validation Approach"),
  p("**Benchmark.** Gold Set v2.2 has 155 questions on ten companies (Apple, Casey's, McKesson, Medtronic, Microsoft, Micron, Nike, NetApp, Parker-Hannifin, Take-Two): 94 with an exact numeric answer, 30 narrative, 12 categorical, 7 with a false premise and 12 that cannot be answered from the corpus. Each question carries the expected route (structured facts 104, text 33, graph 9, none 8, both 1), the filters a system should apply, and the evidence that supports the answer."),
  p("**Reference answers.** Numeric answers are computed in code from XBRL facts (Data's filing instance or the SEC's API, each read twice); none is typed by hand. Each numeric question also stores known wrong figures (another period, another concept) so a wrong answer can be labelled, not only counted. Narrative answers are split into required points, each tied to a passage of the filing. The set is versioned with a hash and a change log: v2.1 corrected 25 anchors and v2.2 fixed the grading rules that RAG's first end-to-end run exposed."),
  p("**Evidence we use.** Data's fact store (20 filings, 24,533 facts), RAG's chunks of the same filings, each team's own code pinned to a commit, and the answers each team returns. Other teams' data stays out of our public repository."),
  p("**Comparisons.** RAG and GraphRAG are compared on the same filing with the same questions and the same number of results. Every scorecard is bracketed by three reference systems: an oracle (1.00), a system that refuses everything (0.00 numeric accuracy, 0.50 balanced refusal) and a simple no-LLM baseline (0.32 numeric accuracy). Routing is compared with three baselines: text search only, a keyword router, and calling every tool."),
  p("**Checks on our own instruments.** We built 389 test answers from 62 questions (correct answers and five kinds of planted error) and the numeric grader gave all 389 the intended label (95% interval 0.990 to 1.00). The repository has 101 automated tests. Narrative answers are graded point by point for coverage and faithfulness, the component-level approach of Es et al. (2024), by an LLM judge that must quote the answer for every point it accepts; two independent judges are compared, and hand labels are the final check (section 5)."),
  p("**Holdout and stress tests.** A sealed set of 40 new questions (batch A) tests RAG's frozen configuration; its hash is published and the questions are not. A second batch of about 30 follows for the next configuration. A suite of 427 rewrites of the gold questions (misspelled company names, misspelled finance terms, casual wording) tests robustness."),
  cap("Table 1. Metrics and proposed success criteria (KPMG has not set targets; these are our proposals)"),
  table([2550, 3760, 3050], [
    ["Metric", "What it measures", "Proposed criterion"],
    ["Numeric answer accuracy", "Right value, unit, period and precision", "At least 0.90 on the holdout set"],
    ["Refusal", "Unanswerable declined; answerable not declined", "No invented figure; balanced score at least 0.90"],
    ["Citation support", "Cited passage exists and contains the figure", "100% exist; at least 95% contain the figure"],
    ["Evidence recall at 10", "Needed evidence in the top 10 results", "At least 0.85"],
    ["Routing coverage and calls", "Every needed tool called; calls per question", "Above the keyword router (82.6% at 1.05 calls)"],
    ["Narrative points", "Required points stated, none contradicted", "Reported once the judge agrees with humans (kappa at least 0.6)"],
  ]),
  gap(),

  h("3. Experimental or Validation Protocol"),
  p("A team member can reproduce every result with the steps below. All paths are in the repository github.com/thomassong0604-oss/kpmg-eval, folders Week 8 and Week 9."),
  num("1. **Set up.** Clone the repository, install requirements.txt (Python 3, pytest, DuckDB) and run scripts/fetch_upstream.sh. It checks out the other teams' code at fixed commits: RAG 5bfafeb, GraphRAG 21f0795 (and a1e7cf7 for the re-score), Data 7040b8a."),
  num("2. **Add the private inputs.** Ask a team lead for RAG's chunks, RAG's answers and the fact store, and put them in the git-ignored private folder. Without them the pipeline still runs and skips those steps."),
  num("3. **Run everything.** bash scripts/run_all.sh (about one minute). It rebuilds the gold set and checks its hash, runs the 101 tests, and re-runs every evaluation and scorecard."),
  num("4. **Score a system's answers.** The owning team runs its system once on the gold file, unchanged, and returns one AnswerBlock per question (answered or not, value, unit, period, answer text, citations). Then: python scripts/grade_answer_blocks.py --answers <file> --chunks <chunks> --tag <name>."),
  num("5. **Score retrieval.** For GraphRAG: python scripts/run_graphrag_round1.py --tag <name>, with the fact store path set. Both arms are called with the top 10 results and filters translated to GraphRAG's vocabulary. The side-by-side comparison (scripts/run_side_by_side.py) uses the top 8 for both systems."),
  num("6. **Score the Agents.** python scripts/run_agent_api.py --base-url <API> --tag <name>, once with fallback and once without, then scripts/grade_agent_run.py for decisions, evidence, citations, filters and the four fallback cases."),
  num("7. **Grade narrative answers.** scripts/run_narrative_judge.py gives a verdict per required point (stated, missing or contradicted). A verdict of \"stated\" without a quote found in the answer is downgraded. The --validate option compares the judge with hand labels."),
  p("**Fixed settings.** Temperature 0 where the model allows it; one run per configuration with no tuning between run and scoring; the holdout set is run once per frozen configuration. The reader is RAG's (gpt-6.1-terra); judges are gpt-6-sol and Claude, neither the reader's model.", { spacing: { before: 60, after: 100 } }),
  p("**Recording results and errors.** Each run writes a summary file and a per-question file under results, holding ids, verdicts and counts but no filing text. Each summary records the gold set's hash, the system's commit and the corpus version. A wrong numeric answer gets a label for the kind of error (wrong period, concept, sign, scale, precision or value, or a false refusal; Appendix C). Two kinds of miss are always listed apart from system errors: questions whose filing is not in the corpus, and infrastructure errors such as a dropped database connection, which are retried three times. Any change to the gold set gets a new version, hash and change-log entry."),

  h("4. Preliminary Results and Observations"),
  cap("Table 2. Results to date (Gold Set v2.2 unless noted; 95% intervals in brackets)"),
  table([3900, 2460, 3000], [
    ["Test", "Result", "Note"],
    ["RAG end to end: numeric accuracy", "89/94 = 0.947 [0.88, 0.98]", "Tuned on these questions"],
    ["RAG end to end: unanswerable declined", "12/12 [0.76, 1.00]", "False premises corrected 6/7"],
    ["RAG citations: cited chunk exists", "185/185", "Figure in a cited chunk 58/59"],
    ["RAG retrieval: evidence in top 10", "105/124 = 0.847 [0.77, 0.90]", "4 misses were our anchors"],
    ["GraphRAG structured search: figure in top 10", "63/93 = 0.677 [0.58, 0.76]", "30 misses mostly need several facts"],
    ["GraphRAG structured search: figure at rank 1", "26/93, then 60/93 after fixes", "No question lost"],
    ["GraphRAG graph search: prose found", "10/38; 10/20 in loaded sections", "18 misses are data not loaded"],
    ["Same filing, numbers: RAG vs GraphRAG", "49/50 vs 25/50", "Microsoft 10-Q, top 8"],
    ["Routing coverage: text only / keyword / all", "21.3% / 82.6% / 94.8%", "1.00 / 1.05 / 3.00 calls"],
    ["Misspelled company name: right decision", "98% to 19%; 94% with loose matching", "129 rewrites"],
    ["Narrative: every point stated (dev)", "17/30; candidate 23/30", "Judges agree on 71/74 points"],
  ]),
  gap(),
  p("**What the evidence suggests.** First, on lookups RAG's reader is accurate and careful: it never invented a figure for an unanswerable question, and every citation points to a real passage. Second, the two retrieval methods are complements. RAG finds almost every number and most prose in a filing; GraphRAG's value is in relationship questions, where its Exhibit 21 traversal matched our reference on 62 of 62 rows, and its ranking now puts the right figure first far more often. Third, a keyword router gets most of the benefit of calling every tool at about a third of the calls, which gives the Agents a concrete bar to beat. Fourth, misspelled company names are the cheapest large risk: one loose-matching step restores almost all of the loss. Fifth, of the 16 answerable questions RAG declined, 10 needed data no team had loaded, so we report misses by cause."),
  p("**Limitations.** The headline accuracy was tuned on the questions it is reported on, which is why the holdout exists. Microsoft has 87 of the 143 answerable questions, so results for other companies have wide intervals. The narrative judge is not yet validated against human labels; two judges agree (kappa 0.84 on RAG's frozen run), but they disagreed on whether a second retrieval variant improved anything, so we report that variant as no measurable change. Latency and cost are not measured end to end. The Agents' API has not been scored, and GraphRAG's graph search has not been re-run on v2.2."),

  h("5. Remaining Work and Integration Plan"),
  cap("Table 3. What remains before the final presentation"),
  table([3350, 2400, 2460, 1150], [
    ["Test or validation", "Owner", "Depends on", "By"],
    ["Hand labels (87 points); judge agreement", "Fei Huang, Thomas Song", "RAG's 20 blind labels", "Nov 18"],
    ["Holdout batch A on RAG's frozen settings", "Shenyi Feng, Shuhan Bian", "RAG runs it once", "Nov 24"],
    ["Holdout batch B (about 30, mostly narrative)", "Thomas Song, Yupin Wang", "RAG tags its next version", "Nov 29"],
    ["Agents API with and without fallback", "Binyu Wang, Yupin Wang", "Agents' first full run", "Nov 24"],
    ["Graph search on v2.2; Exhibit 21 questions", "Ruofei Duan", "GraphRAG loads Exhibit 21", "Nov 24"],
    ["Latency and cost per question", "Bo Yuan", "Token counts from RAG and Agents", "Nov 24"],
  ]),
  gap(),
  p("**Dependencies and how we handle them.** We cannot run the other teams' services ourselves, so each test above is one command that the owning team runs and returns as a file; we then re-score it and, where we hold the data, reproduce it (we matched GraphRAG's structured results on 155 of 155 questions). Each interface has one named liaison on our team. The corpus stays frozen at the 20 filings of round 1 through the holdout runs; three NetApp questions and seven Exhibit 21 questions are reported as \"not in the corpus\" until Data and GraphRAG load them. If a dependency is late, we report that component at the evidence level and say so."),
  p("**Contribution to the final report.** We will supply one scorecard for the whole system: development and holdout results side by side, split by company (Microsoft and others) and by normal and stress questions, with confidence intervals and cost and latency per question. We will add an error analysis by cause, a recommendation on when to route to RAG, to GraphRAG or to both, and a short statement of what the results do not show. A gap between development and holdout is a finding to report, not something to tune away."),

  new Paragraph({ children: [new PageBreak()] }),
  h("References"),
  ref("Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAs: Automated evaluation of retrieval augmented generation. Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations, 150–158."),
  ref("Evaluation & Testing team. (2026). kpmg-eval [repository]. github.com/thomassong0604-oss/kpmg-eval. Week 8: data/benchmark_v2_2.jsonl, GOLD_SET_V2.md, scripts/run_all.sh, scripts/grade_answer_blocks.py, scripts/run_graphrag_round1.py, scripts/run_agent_api.py, scripts/run_narrative_judge.py, results folder. Week 9: scripts/score_rag_judge_runs.py, scripts/compare_judges.py, results/holdout_A_manifest.json."),
  ref("RAG team. (2026). KPMG_RAG [repository]. github.com/Rachel-xs/KPMG_RAG (configs/final_v1.yaml; docs/holdout_request.md; round-1 answers and judge runs)."),
  ref("GraphRAG team. (2026). KPMG-GraphRAG [repository]. github.com/ZiyiClaudiaWang/KPMG-GraphRAG (pull requests #70, #72, #75, #76; round-1 results on the live graph)."),
  ref("Data team. (2026). data_engineering_kpmg [repository]. github.com/michaelliruoxi/data_engineering_kpmg (fact store for 20 filings; validation profiles; NetApp source review)."),
  ref("Agents team. (2026). KPMG Agentic Backbone: API Contract v0.2 [project document]."),
  ref("U.S. Securities and Exchange Commission. (2026). EDGAR application programming interfaces (company facts and company concept). https://www.sec.gov/search-filings/edgar-application-programming-interfaces"),

  h("Appendix A. Gold Set v2.2 at a glance"),
  table([4680, 4680], [
    ["Item", "Value"],
    ["Questions (answerable / not)", "155 (143 / 12)"],
    ["Answer types", "94 numeric, 30 narrative, 12 categorical, 7 false premise, 12 refusal"],
    ["Expected route", "104 structured facts, 33 text, 9 graph, 8 none, 1 both"],
    ["Answerable questions per company", "Microsoft 87; Micron 8; several companies 8; NetApp 6; Take-Two 6; Apple, Casey's, Medtronic, Nike 5 each; McKesson, Parker-Hannifin 4 each"],
    ["Corpus", "Snapshot of November 3: 21 filings; round 1 ran on 20 (NetApp's 10-Q held for review by Data)"],
    ["Version and hash", "v2.2, 416304a91b4aa400 (v2: ed4b42db6fc25ee5; v2.1: 1e104c626c6c9833)"],
  ]),
  gap(),
  h("Appendix B. Holdout batch A (sealed; counts only)"),
  table([4680, 4680], [
    ["Item", "Value"],
    ["Questions", "40: 30 numeric, 5 narrative, 5 unanswerable"],
    ["Microsoft share", "10 of 40 (25%)"],
    ["Stress questions", "14: misspelled name 4, analyst wording 3, multi-step 2, relative period 2, cross-filing 2, narrative across sections 1"],
    ["Source of answers", "Data's fact store; no fact shared with a development question except three derived questions, which are flagged"],
    ["Grader check", "Right answer passes and a 7% error fails on 30 of 30 numeric questions"],
    ["Commitment", "SHA-256 of the file published in Week 9 results/holdout_A_manifest.json on November 16"],
  ]),
  gap(),
  h("Appendix C. Numeric error labels"),
  p("wrong_period (the figure for another period), wrong_concept (another line item), wrong_dimension (a segment figure for a total), wrong_sign, wrong_scale (for example thousands for millions), too_imprecise (fewer digits than the filing prints), wrong_value (none of the above) and false_refusal (declined although answerable). In the planted-error test, 389 of 389 answers received the intended label: 62 correct, 135 wrong dimension, 61 wrong scale, 61 wrong sign, 56 wrong period and 14 wrong concept."),
  ] }] });
Packer.toBuffer(doc).then(b => fs.writeFileSync("Eval_Benchmark_Experimental_Protocol.docx", b));
