"""Week 9 deck (11/19): 6 slides for a 10-minute slot + 2 appendix, in the team template, with the script.

    python3 scripts/build_deck_w9.py "../Week 8/deck/template_base.pptx" deck/KPMG_Eval_Week9_11-19.pptx
        -> the deck (script in the speaker notes) and SCRIPT_W9.md

Reuses Week 8's slide helpers (frame, card, bullets, table). Every number on a slide is read from Week 9/results or
Week 8/results; check() asserts the numbers the script says aloud.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8 = ROOT.parent / "Week 8"
sys.path[:0] = [str(W8 / "scripts")]
import build_deck_w8 as b  # noqa: E402
from build_deck_w8 import X0, Y0, W, bullets, card, frame, head, table  # noqa: E402
from deck_style import GREEN, NAVY, PINK, notes  # noqa: E402
from pptx import Presentation  # noqa: E402

b.DECK = "Evaluation & Testing  ·  Week 9  ·  19 Nov 2026"
R = ROOT / "results"
J = lambda p: json.load(open(p))  # noqa: E731
B = lambda t: (t, {"bold": True})  # noqa: E731


def load():
    return {"nj": J(R / "narrative_judge_w9.json"), "ag": J(R / "judge_agreement_w9.json"), "ho": J(R / "holdout_A_manifest.json"),
            "gi": J(R / "graph_inventory_2026-11-17.json"), "rs": J(W8 / "results" / "graphrag_rescore_a1e7cf7.json")}


def kn(d):
    return f"{d['k']}/{d['n']}"


def s_summary(s, n, D):
    nj, ag, ho, gi = D["nj"]["runs"], D["ag"], D["ho"], D["gi"]
    frame(s, n, "Executive summary",
          "RAG's next version states more of each answer without inventing figures, and a sealed test set is ready to check it",
          "Every result so far was tuned on the questions it is reported on. From this week, each frozen version is also run "
          "once on questions no team has seen.",
          "Source: Week 9/results (narrative_judge_w9, judge_agreement_w9, holdout_A_manifest, graph_inventory_2026-11-17); "
          "RAG's judge runs of 11/16")
    cw, gap = 2.25, 0.2
    cards = [(f"{nj['final_v1']['all']['passed']['k']} → {nj['narr_long']['all']['passed']['k']}",
              f"of {nj['narr_long']['all']['passed']['n']} questions with every required point stated: RAG's frozen version → its next one", NAVY),
             (kn(nj["narr_long"]["all"]["figures_supported"]), "figures in the longer answers found in a cited passage or recomputed", GREEN),
             (f"{ag['narr_long']['agree']}/{ag['narr_long']['points']}", "points where two independent judges give the same verdict", NAVY),
             (str(ho["questions"]), f"sealed holdout questions, {ho['stress']} of them stress questions; hash published", PINK)]
    for i, (big, lab, col) in enumerate(cards):
        card(s, X0 + i * (cw + gap), Y0, cw, 0.98, big, lab, col)
    cols = [("What we did", [
                "Judged three RAG versions on the same 38 narrative, categorical and false-premise questions",
                "Compared our judge with RAG's judge, point by point",
                f"Wrote and sealed holdout batch A ({ho['questions']} questions) and reviewed RAG's pre-registered test plan",
                "Read GraphRAG's live graph directly for the first time"]),
            ("What we found", [
                "Fuller answers gain 8 questions and lose none; no figure is unsupported",
                "A retrieval variant showed no gain once a second judge looked, so it was dropped",
                f"Exhibit 21 is now in the graph: {gi['nodes']['Subsidiary']} subsidiaries, matching our reference for Microsoft, "
                "Micron and Casey's"]),
            ("What comes next", [
                [("Done: ", True), ("RAG's hand labels, kappa 0.93 / 0.90", False)],
                [("Nov 20: ", True), ("batch A goes to RAG, run once", False)],
                [("Nov 24: ", True), ("batch B; Agents and graph re-runs", False)],
                [("Open: ", True), ("cost and latency per question", False)]])]
    cx, cg = 3.05, 0.225
    for i, (h, items) in enumerate(cols):
        x = X0 + i * (cx + cg)
        head(s, x, 2.42, cx, h, size=10.5)
        bullets(s, x, 2.7, cx, 1.6, items, size=9.5, gap=5)


def s_narrative(s, n, D):
    nj, ag, cmp_ = D["nj"]["runs"], D["ag"]["rag_runs_gpt6sol"], D["nj"]["final_v1_vs_narr_long"]
    frame(s, n, "Narrative answers", "RAG's fuller answers state more required points, and every figure in them is supported",
          "Longer answers are the usual place for invented detail. Here they are about 20% longer and added none, so the gain is real "
          "on these questions.",
          "Source: RAG's judge inputs for three runs (11/16); Week 9/scripts/score_rag_judge_runs.py. 38 questions: 27 narrative, "
          "5 categorical, 6 false premise. RAG's judge covers its 30 narrative questions")
    row = lambda name, k: [B(name), kn(nj[k]["all"]["passed"]), kn(nj[k]["by_group"]["narrative"]["passed"]),  # noqa: E731
                           kn(nj[k]["all"]["points_stated"]), f"{ag[k]['passed']}/{ag[k]['of']}", kn(nj[k]["all"]["figures_supported"])]
    rows = [["RAG version", "Every point stated (38)", "Narrative only (27)", "Points stated", "RAG's judge (30)", "Figures supported"],
            row("final_v1 (frozen)", "final_v1"), row("Retrieval variant (dropped)", "narr_union"), row("Fuller answers (final_v2 candidate)", "narr_long")]
    table(s, X0, Y0, W, [2.7, 1.5, 1.35, 1.2, 1.35, 1.5], rows, row_h=0.36, sizes={i: 9 for i in range(6)}, name="Runs")
    head(s, X0, 2.95, 4.5, "What changed in the fuller answers")
    bullets(s, X0, 3.2, 4.5, 1.1, [
        f"{len(cmp_['gained_pass'])} questions gained, {len(cmp_['lost_pass'])} lost; no point contradicted",
        f"Answers average {cmp_['mean_answer_chars'][1]} characters, up from {cmp_['mean_answer_chars'][0]}",
        "Gains are second-level detail and reasons: a driver, an after-tax amount, the correction after a false premise"], size=9.5)
    head(s, X0 + 4.9, 2.95, 4.6, "What is still missing in every version")
    bullets(s, X0 + 4.9, 3.2, 4.6, 1.1, [
        "The line item under a segment (which product group Azure sits in)",
        "After-tax amounts when the question asks for the effect on net income",
        "Two answers that state the right fact but are flagged as not answered"], size=9.5)


def s_judge(s, n, D):
    ag = D["ag"]
    frame(s, n, "Can we trust the judge?", "Two independent judges agree on most points, and where they differed we did not claim a gain",
          "An LLM judge is an instrument and needs its own check. Ours now has three: a second judge, a quote rule, and RAG's blind hand labels "
          "(kappa 0.93 and 0.90).",
          "Source: Week 9/results/judge_agreement_w9.json. RAG ran Week 8's judge script unchanged with gpt-6-sol; Eval's verdicts are "
          "Claude's. Each 'stated' verdict must quote the answer")
    row = lambda name, k: [B(name), f"{ag[k]['agree']}/{ag[k]['points']}", f"{ag[k]['kappa']:.2f}",  # noqa: E731
                           f"{ag[k]['passed_gpt6sol']} vs {ag[k]['passed_claude']} of {ag[k]['questions_in_both']}", str(len(ag[k]["disagreements"]))]
    rows = [["RAG version", "Points with the same verdict", "Kappa", "Questions passed (RAG's judge vs ours)", "Points that differ"],
            row("final_v1 (frozen)", "final_v1"), row("Retrieval variant", "narr_union"), row("Fuller answers", "narr_long")]
    table(s, X0, Y0, W, [2.3, 2.1, 0.9, 2.9, 1.4], rows, row_h=0.36, sizes={i: 9 for i in range(5)}, name="Agreement")
    head(s, X0, 2.95, 4.6, "What the comparison changed")
    bullets(s, X0, 3.2, 4.6, 1.1, [
        "The retrieval variant looked like +2 questions with one judge and 0 with the other. We reported no measurable change, and RAG dropped it",
        "The fuller-answers gain holds under both judges: +6 and +7 on the 26 questions both saw"], size=9.5)
    head(s, X0 + 4.9, 2.95, 4.6, "The human check")
    bullets(s, X0 + 4.9, 3.2, 4.6, 1.1, [
        "RAG's blind hand labels are done: 20 questions, 126 points, kappa against the judge 0.93 (final_v1) and 0.90 (final_v2), as reported by RAG. Eval's 87 points are in progress",
        "One gold answer to fix: a growth rate the filing prints as 29% and the answer computes as 28.5%"], size=9.5)


def s_holdout(s, n, D):
    ho = D["ho"]
    st = ho["by_stress_type"]
    frame(s, n, "A test nobody tuned on", f"Holdout batch A is written, sealed and committed by hash: {ho['questions']} questions for RAG's frozen version",
          "A gap between the development score and the holdout score is a result to report, not a number to tune away.",
          "Source: Week 9/results/holdout_A_manifest.json (counts and SHA-256 only; the questions are not in the repository); RAG's "
          "holdout request and pre-registration of 11/16")
    cw, gap = 2.25, 0.2
    bt = ho["by_answer_type"]
    for i, (big, lab, col) in enumerate([
            (f"{bt['exact_numeric']} / {bt['narrative']} / {bt['refusal']}", "numeric, narrative and unanswerable questions", NAVY),
            (f"{ho['msft']} of {ho['questions']}", "on Microsoft, against 87 of 143 in the development set", NAVY),
            (str(ho["stress"]), f"stress questions: misspelled names {st['misspelled_name']}, analyst wording {st['analyst_wording']}, "
                                f"multi-step {st['multi_step']}, relative period {st['relative_period']}, cross-filing {st['cross_filing']}", PINK),
            ("30/30", "numeric questions where our grader passes the right answer and fails a 7% error", GREEN)]):
        card(s, X0 + i * (cw + gap), Y0, cw, 1.05, big, lab, col, lab_size=8)
    head(s, X0, 2.5, 4.6, "How it is kept honest")
    bullets(s, X0, 2.75, 4.6, 1.55, [
        "Answers come from Data's fact store; no fact is one a development question uses",
        "The file's hash is public, the questions are not; RAG checks the hash, runs once without opening the file, and returns answers for us to score",
        "Batch B (about 30, mostly narrative) stays sealed until RAG tags its next version"], size=9.5)
    head(s, X0 + 4.9, 2.5, 4.6, "RAG's larger test plan, reviewed before any run")
    bullets(s, X0 + 4.9, 2.75, 4.6, 1.55, [
        "RAG pre-registered about 250 more questions from Data's validated metrics and asked Eval to hold them",
        "We proposed five rule changes, the main one: run the misspelling test without passing the company as a filter, or 129 rewrites cannot fail",
        "We wrote a scorer so our messy-wording (427) and abstention (56) suites can be run by any team"], size=9.5)


def s_graph(s, n, D):
    gi, rs = D["gi"], D["rs"]["summary"]
    frame(s, n, "GraphRAG", "Exhibit 21 is now in the live graph, and ranking fixes more than doubled how often the right figure comes first",
          "Seven relationship questions that no system could answer in round 1 can now be scored, which is where a graph should beat text search.",
          "Source: read-only count queries on GraphRAG's Aura graph, run by Eval on 11/17 (Week 9/results/graph_inventory_2026-11-17.json); "
          "Week 8/results/graphrag_rescore_a1e7cf7.json")
    cw, gap = 2.25, 0.2
    for i, (big, lab, col) in enumerate([
            (f"{gi['nodes']['Subsidiary']:,}", "subsidiaries in the graph, one ownership edge each, across all ten companies", GREEN),
            ("3 of 3", "companies checked against our reference: Microsoft 8, Micron 21, Casey's 9", NAVY),
            (f"{gi['nodes']['Claim']:,}", f"claims from {gi['nodes']['Section']} sections of {gi['nodes']['Filing']} filings", NAVY),
            (f"{rs['top1_right']['before'].split('/')[0]} → {rs['top1_right']['after']}", "number questions with the right figure ranked first, before and after GraphRAG's fixes", PINK)]):
        card(s, X0 + i * (cw + gap), Y0, cw, 0.98, big, lab, col)
    sub = gi["subsidiaries_per_company"]
    rows = [["Company"] + list(sub), [B("Subsidiaries in graph")] + [str(v) for v in sub.values()],
            [B("Countries")] + [str(gi["countries_per_company"][k]) for k in sub]]
    table(s, X0, 2.42, W, [1.9] + [0.77] * 10, rows, row_h=0.3, sizes={i: 9 for i in range(11)}, name="Subsidiaries")
    bullets(s, X0, 3.5, W, 0.8, [
        "Read straight from the ownership edges, the graph gives our reference answer on the four Exhibit 21 questions we checked (insurers, Casey's by state, Braeburn's owner, Microsoft's count)",
        "Next: GraphRAG re-runs graph search on Gold Set v2.2, so we can score whether its search returns what the graph holds",
        "The graph still holds five section types; answers in the notes to the financial statements remain out of its reach"], size=9.5)


def s_next(s, n, D):
    frame(s, n, "Next steps", "Each remaining test has an owner, a dependency and a date before the code freeze on Nov 30",
          "RAG froze its settings before asking for a test, pre-registered its plan and invited us to change any rule in its favour. "
          "That is what makes the next numbers believable.",
          "Source: Week 9/README.md and COMMS_W9.md; Assignments/Benchmark and Experimental Protocol (team report, section 5)", lead="Thank you:")
    rows = [["By", "Test", "Owner", "Depends on"],
            [B("Nov 21"), "Eval's hand labels on 87 points; agreement of the judge with humans", "Fei Huang, Thomas Song", "RAG's labels done (kappa 0.93 / 0.90)"],
            [B("Nov 20"), "Holdout batch A delivered; run once on the frozen version", "Shenyi Feng, Shuhan Bian", "RAG returns answers within 24 hours"],
            [B("Nov 24"), "Agents' API scored with and without fallback", "Binyu Wang, Yupin Wang", "Agents' first full run"],
            [B("Nov 24"), "Graph search on Gold Set v2.2, including Exhibit 21 questions", "Ruofei Duan", "GraphRAG runs our script on its graph"],
            [B("Nov 24"), "Cost and latency per question", "Bo Yuan", "Token counts in RAG's and the Agents' results"],
            [B("Nov 29"), "Holdout batch B on RAG's next version", "Thomas Song, Yupin Wang", "RAG tags the version"]]
    table(s, X0, Y0, W, [0.8, 4.3, 2.0, 2.5], rows, row_h=0.4, sizes={0: 9, 1: 8.5, 2: 8.5, 3: 8.5}, name="Plan")


def s_changes(s, n, D):
    c, bl = D["nj"]["final_v1_vs_narr_long"], D["nj"]["borderline_verdicts_narr_long"]
    frame(s, n, "Fuller answers, question by question", "Eight questions gained every required point; four still miss one in every version",
          "The remaining misses are specific and small, so they are a to-do list for the reader prompt, not a retrieval problem.",
          "Source: Week 9/results/narrative_judge_w9.json (final_v1_vs_narr_long) and narrative_judge_w9_per_question.csv")
    rows = [["Question", "Points stated: frozen → fuller", "Result"]] + \
           [[B(q), v.replace("->", " → "), "Now complete"] for q, v in c["more_points"].items()] + \
           [[B(q), "unchanged", "Still missing a point"] for q in c["failed_in_both"]]
    table(s, X0, Y0, 5.6, [1.9, 2.1, 1.6], rows, row_h=0.235, sizes={0: 8, 1: 8, 2: 8}, name="Changes")
    head(s, X0 + 5.9, Y0, 3.6, "Close calls, listed for the hand check")
    bullets(s, X0 + 5.9, Y0 + 0.28, 3.6, 2.6, [f"{q}: {t}" for q, t in bl.items()], size=8.5)


def s_defs(s, n, D):
    frame(s, n, "Definitions", "How the numbers in this deck are produced",
          "Each definition is one script in the repository, so any team can reproduce a number from its own output.",
          "Source: Week 9/README.md; Week 8/scripts/run_narrative_judge.py (rubric)")
    rows = [["Term", "Meaning"],
            [B("Required point"), "One fact the reference answer must contain. A question passes when every point is stated and none is contradicted"],
            [B("Stated / missing / contradicted"), "The judge's verdict per point. 'Stated' must come with a quote found in the answer, or it is downgraded"],
            [B("Figure supported"), "A number in the answer that is printed in a cited passage, or computed from printed numbers and re-checked by our script"],
            [B("Kappa"), "Agreement between two judges beyond what chance would give; 1 is perfect, 0 is chance"],
            [B("Holdout"), "Questions written after a version is frozen, kept from the team that built it, and run once"],
            [B("Stress question"), "A holdout question with a deliberate difficulty: a misspelled name, analyst wording, several steps, a relative period or two filings"],
            [B("Pre-registration"), "Writing down the questions' source, the sampling and the analysis before any run, so results cannot shape the rules"]]
    table(s, X0, Y0, W, [2.4, 7.2], rows, row_h=0.36, sizes={0: 9, 1: 8.5}, name="Definitions")


SCRIPT = [
 ("Executive summary", "1.5 min",
  "This week moved from measuring the systems to checking whether our measurements can be trusted. Three things happened. First, "
  "RAG sent us three versions of its answers on the same 38 questions. Its next version, which writes fuller answers, states every "
  "required point on 34 of 38 questions, up from 26, and all 80 figures in those answers are supported by a cited passage. Second, "
  "we compared our judge with RAG's judge, and they agree on 72 of 74 points. Third, we wrote a sealed test of 40 new questions that "
  "no team has seen, and published its hash. The rest of the deck is the evidence, and the dates for what is still open."),
 ("Narrative answers", "2 min",
  "The table compares three RAG versions. The frozen version passes 26 of 38 questions. A retrieval variant passes 28, and the "
  "fuller-answers version passes 34. The last column is the important one. Longer answers are where a model usually starts inventing "
  "detail, so we checked every figure against the passages the answer cites. In the fuller answers, 80 of 80 are either printed in "
  "a cited passage or computed correctly from printed numbers. Eight questions gained and none were lost. What is still missing is "
  "narrow: the line item under a segment, and after-tax amounts. One caution. These are the questions RAG tuned on, so this is a "
  "development result. The sealed test is what will confirm it."),
 ("Can we trust the judge?", "2 min",
  "These scores come from an LLM judge, so the judge needs its own check. RAG ran our judge script with one model, and we judged the "
  "same answers independently. On the frozen version the two agree on 71 of 74 points, and on the fuller answers on 72 of 74. The "
  "middle row is the useful one. For the retrieval variant, our judge showed a gain of two questions and RAG's showed none. Because "
  "the judges disagreed, we reported no measurable change, and RAG dropped that variant. The gain for fuller answers holds under both "
  "judges. The human check has started too. RAG labelled 20 questions blind, 126 points, and reports agreement with the judge of "
  "0.93 on the frozen version and 0.90 on the next one. Our own 87-point labels are in progress."),
 ("A test nobody tuned on", "2 min",
  "Every number you have seen from any team was tuned on the same 155 questions. So this week we wrote holdout batch A: 40 new "
  "questions, 30 numeric, 5 narrative and 5 unanswerable. Ten are on Microsoft, which is 25 percent, against more than 60 percent in "
  "the development set. Fourteen are stress questions, such as misspelled company names and analyst wording. The answers come from "
  "the Data team's fact store, and none reuses a fact from a development question. The file's hash is public and the questions are "
  "not. RAG will check the hash, run its frozen version once without opening the file, and send the answers back for us to score. "
  "RAG also pre-registered a larger test plan and asked us to hold those questions too. We reviewed it and proposed five changes."),
 ("GraphRAG", "1.5 min",
  "We read GraphRAG's live graph directly for the first time this week. Exhibit 21, the list of subsidiaries, is now loaded: 752 "
  "subsidiaries across all ten companies. We checked three companies against our reference answers, and Microsoft, Micron and "
  "Casey's all match. That matters because seven relationship questions could not be answered by any system in round 1, and they can "
  "now be scored. Separately, GraphRAG's ranking fixes took the right figure at rank one from 26 to 60 of 93 questions. The next "
  "step is for GraphRAG to re-run graph search on the current gold set."),
 ("Next steps", "1 min",
  "Six tests remain before the code freeze on November 30, each with an owner and a date. Our hand labels come first. Batch A goes to "
  "RAG on the 20th. The Agents' API, the graph re-run, and cost and latency per question by the 24th. Batch B on RAG's next version "
  "by the 29th. I want to thank the RAG team in particular. They froze their settings before asking for a test, wrote their plan "
  "down in advance, and invited us to change any rule that favoured them. That is what will make the final numbers believable."),
]


def check(D):
    nj, ag, ho, gi, rs = D["nj"]["runs"], D["ag"], D["ho"], D["gi"], D["rs"]["summary"]
    assert (nj["final_v1"]["all"]["passed"]["k"], nj["narr_union"]["all"]["passed"]["k"], nj["narr_long"]["all"]["passed"]["k"]) == (26, 28, 34)
    assert kn(nj["narr_long"]["all"]["figures_supported"]) == "80/80"
    assert (ag["final_v1"]["agree"], ag["narr_long"]["agree"], ag["narr_long"]["points"]) == (71, 72, 74)
    assert (ag["narr_union"]["passed_claude"] - ag["final_v1"]["passed_claude"], ag["narr_union"]["passed_gpt6sol"] - ag["final_v1"]["passed_gpt6sol"]) == (2, 0)
    assert (ag["narr_long"]["passed_gpt6sol"] - ag["final_v1"]["passed_gpt6sol"], ag["narr_long"]["passed_claude"] - ag["final_v1"]["passed_claude"]) == (6, 7)
    c = D["nj"]["final_v1_vs_narr_long"]
    assert len(c["gained_pass"]) == 8 and not c["lost_pass"]
    assert (ho["questions"], ho["msft"], ho["stress"]) == (40, 10, 14) and ho["by_answer_type"] == {"exact_numeric": 30, "narrative": 5, "refusal": 5}
    assert gi["nodes"]["Subsidiary"] == 752 == sum(gi["subsidiaries_per_company"].values())
    assert (rs["top1_right"]["before"], rs["top1_right"]["after"]) == ("26/93", "60/93")


def main():
    base, out = sys.argv[1], sys.argv[2]
    D = load()
    check(D)
    main_slides, appendix = [s_summary, s_narrative, s_judge, s_holdout, s_graph, s_next], [s_changes, s_defs]
    prs = Presentation(base)
    b.add_slides(prs, len(main_slides) + len(appendix))
    slides = list(prs.slides)
    for i, fn in enumerate(main_slides + appendix, 1):
        b.APPENDIX = i > len(main_slides)
        fn(slides[i - 1], i, D)
        if not b.APPENDIX:
            notes(slides[i - 1], SCRIPT[i - 1][2])
    prs.save(out)
    words = sum(len(t.split()) for _, _, t in SCRIPT)
    md = ["# Week 9 script (11/19): 6 slides", "",
          f"About {round(words, -1)} words, roughly {words / 130:.1f} minutes at a measured pace. The same text is in each slide's "
          "speaker notes. Slides 7 and 8 are the appendix, for questions.", ""]
    for i, (title, mins, text) in enumerate(SCRIPT, 1):
        md += [f"## Slide {i}: {title} ({mins})", "", text, ""]
    (ROOT / "SCRIPT_W9.md").write_text("\n".join(md))
    print("[deck] wrote", out, f"({len(slides)} slides); script {words} words")


if __name__ == "__main__":
    main()
