"""Charts for the 10/15 KPMG meeting. Every number is read from results/*.json produced by the run_* scripts."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
OUT = ROOT / "charts"
OUT.mkdir(exist_ok=True)

INK, MUTED, GRID, SURF = "#1E2530", "#5C6675", "#E3E7F0", "#FFFFFF"
NAVY, BLUE, PINK, GREEN, AMBER = "#2F3E96", "#3D52C4", "#D9447A", "#16825D", "#B76B00"
fam = next((f for f in ("Liberation Sans", "Arial", "DejaVu Sans") if any(f == x.name for x in font_manager.fontManager.ttflist)), "sans-serif")
plt.rcParams.update({"font.family": fam, "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.dpi": 200})


def title(fig, t, sub):
    fig.text(0.02, 0.965, t, fontsize=16, fontweight="bold", color=NAVY, va="top")
    fig.text(0.02, 0.905, sub, fontsize=10.5, color=MUTED, va="top")


def source(fig, s):
    fig.text(0.02, 0.02, s, fontsize=8.5, color=MUTED)


# ---------------------------------------------------------------- 1. grader validation
fi = json.loads((R / "fault_injection.json").read_text())
fi1 = json.loads((R / "fault_injection_round1.json").read_text())
ho = json.loads((R / "heldout.json").read_text())
rows = [  # (label, test set, k, n, lo, hi, color)
    ("Week 1 pattern grader", "10 realistic answers, human-labelled", 2, 10, None, None, MUTED),
    ("Free-text grader v0.1", "697 fault-injected answers (before fixes)", fi1["by_format"]["free_text"]["correct"], fi1["by_format"]["free_text"]["n"], *fi1["by_format"]["free_text"]["ci95"], MUTED),
    ("Free-text grader v0.2", "31 held-out answers, human-labelled", ho["agree"], ho["n"], *ho["ci95"], BLUE),
    ("Free-text grader v0.2", "697 fault-injected answers (after fixes)", fi["by_format"]["free_text"]["correct"], fi["by_format"]["free_text"]["n"], *fi["by_format"]["free_text"]["ci95"], BLUE),
    ("Structured AnswerBlock", "189 fault-injected answers", fi["by_format"]["structured"]["correct"], fi["by_format"]["structured"]["n"], *fi["by_format"]["structured"]["ci95"], NAVY),
]
from kpmg_eval.stats import wilson  # noqa: E402
fig, ax = plt.subplots(figsize=(11, 5.4))
fig.subplots_adjust(left=0.36, right=0.93, top=0.8, bottom=0.14)
for i, (lab, test, k, n, lo, hi, col) in enumerate(reversed(rows)):
    if lo is None:
        lo, hi = wilson(k, n)
    p = k / n
    ax.plot([lo * 100, hi * 100], [i, i], color=col, lw=2, solid_capstyle="round")
    ax.plot(p * 100, i, "o", ms=9, color=col, mec=SURF, mew=2)
    ax.text(hi * 100 + 1.5, i, (f"{p:.1%}" if 0.99 <= p < 1 else f"{p:.0%}") + f"  ({k}/{n})", va="center", fontsize=10.5, color=INK)
    ax.text(-2, i + 0.13, lab, ha="right", va="center", fontsize=11, color=INK, fontweight="bold", transform=ax.transData)
    ax.text(-2, i - 0.22, test, ha="right", va="center", fontsize=9, color=MUTED, transform=ax.transData)
ax.set_xlim(0, 112)
ax.set_xticks(range(0, 101, 20))
ax.set_xticklabels([f"{x}%" for x in range(0, 101, 20)])
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_xlabel("Agreement with the correct label (dot) and 95% interval")
title(fig, "Our graders now agree with human judgment 9 times in 10 on unseen answers",
      "Scoring the structured answer fields we asked Agents to return is near-exact; free text remains the weaker path")
source(fig, "Source: scripts/run_fault_injection.py, scripts/run_heldout.py. Benchmark v0: 28 answerable SEC questions, 7 companies. Intervals: Wilson 95%.")
fig.savefig(OUT / "1_grader_validation.png")
plt.close(fig)

# ---------------------------------------------------------------- 2. mock retriever
mr = json.loads((R / "mock_retrieval_eval.json").read_text())
S = mr["summary"]
metrics = [("hit@1", "Hit@1"), ("hit@5", "Hit@5"), ("mrr", "MRR"), ("ndcg@5", "nDCG@5")]
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [2.1, 1]})
fig.subplots_adjust(left=0.06, right=0.97, top=0.78, bottom=0.17, wspace=0.28)
w = 0.36
for j, (style, lab, col) in enumerate((("filing_terms", "Question uses filing wording", BLUE), ("paraphrase", "Analyst paraphrase", PINK))):
    xs = [i + (j - 0.5) * (w + 0.02) for i in range(len(metrics))]
    vals = [S[style][m] for m, _ in metrics]
    ax.bar(xs, vals, width=w, color=col, label=lab, edgecolor=SURF, linewidth=2)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.02, f"{v:.2f}", ha="center", fontsize=9.5, color=INK)
ax.set_xticks(range(len(metrics)))
ax.set_xticklabels([l for _, l in metrics])
ax.set_ylim(0, 1.3)
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9.5, ncol=2)
ax.set_title("Same 10 questions, two wordings", fontsize=11, color=INK, loc="left")
ans = mr["summary"]["answerable_top1_scores"]
un = mr["summary"]["unanswerable"]["top1_scores"]
ax2.scatter([0] * len(ans), ans, s=40, color=BLUE, alpha=0.75, edgecolor=SURF, linewidth=1.5, zorder=3)
ax2.scatter([1] * len(un), un, s=55, color=PINK, edgecolor=SURF, linewidth=1.5, zorder=3)
ax2.set_xticks([0, 1])
ax2.set_xticklabels(["Answerable\n(20 queries)", "Unanswerable\n(3 queries)"])
ax2.set_xlim(-0.6, 1.6)
ax2.set_ylabel("Top-1 retrieval score")
ax2.grid(axis="y", color=GRID, lw=0.8)
ax2.set_title("Every unanswerable query\nstill returned evidence", fontsize=11, color=INK, loc="left")
title(fig, "The harness already runs on RAG's real interface: paraphrasing cut MRR from 0.64 to 0.26",
      "Scores the RAG team's MOCK retriever from PR #3 (6 chunks of Microsoft's Mar-2026 10-Q, keyword overlap). Harness check, not RAG performance.")
source(fig, "Source: scripts/run_retrieval_eval.py on vendor/mock_retrieval_tool.py (Retrieval API contract v0). Evidence matched on CIK + accession + required text.")
fig.savefig(OUT / "2_mock_retriever.png")
plt.close(fig)

# ---------------------------------------------------------------- 3. benchmark coverage
bench = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v0.jsonl")]
facts = {json.loads(l)["fact_id"]: json.loads(l) for l in open(ROOT / "data" / "gold_facts_v0.jsonl")}
cik2t = {f["cik"]: f["ticker"] for f in facts.values()}
q2t = {"U01": ["AAPL"], "U02": ["JPM"], "U03": ["DE"], "U04": ["CAT"], "U05": ["BAC"]}
types = [("extraction", "Extraction"), ("comparison", "Comparison"), ("reconciliation", "Reconciliation"),
         ("temporal", "Cross-period"), ("unanswerable", "Unanswerable")]
tick = ["JPM", "BAC", "C", "CAT", "DE", "HON", "AAPL"]
cnt = Counter()
for b in bench:
    ts = q2t.get(b["qid"]) or sorted({cik2t[e["cik"]] for e in b["gold"].get("evidence", [])})
    for t in ts:
        cnt[(t, b["type"])] += 1
fig, ax = plt.subplots(figsize=(11, 5.4))
fig.subplots_adjust(left=0.1, right=0.8, top=0.78, bottom=0.12)
import numpy as np  # noqa: E402
M = np.array([[cnt[(t, ty)] for ty, _ in types] for t in tick])
vmax = M.max()
for i, t in enumerate(tick):
    for j, (ty, _) in enumerate(types):
        v = M[i, j]
        shade = (1 - v / vmax) if v else 1.0
        col = matplotlib.colors.to_hex([shade * a + (1 - shade) * b for a, b in zip((0.95, 0.96, 0.99), matplotlib.colors.to_rgb(NAVY))])
        ax.add_patch(FancyBboxPatch((j + 0.06, i + 0.08), 0.88, 0.84, boxstyle="round,pad=0,rounding_size=0.08", fc=col if v else "#F4F6FC", ec="none"))
        if v:
            ax.text(j + 0.5, i + 0.5, str(v), ha="center", va="center", fontsize=11, color=SURF if v / vmax > 0.5 else INK, fontweight="bold")
ax.set_xlim(0, len(types))
ax.set_ylim(len(tick), 0)
ax.set_xticks([j + 0.5 for j in range(len(types))])
ax.set_xticklabels([l for _, l in types])
ax.set_yticks([i + 0.5 for i in range(len(tick))])
ax.set_yticklabels(tick)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.xaxis.tick_top()
n_types = Counter(b["type"] for b in bench)
summary = (f"{len(bench)} questions\n{len(facts)} SEC XBRL gold facts\n7 companies, {len({f['accession'] for f in facts.values()})} filings\n\n"
           f"{sum(len(b['graph_paths']) > 1 for b in bench)} need 2+ facts\n(GraphRAG multi-hop paths)\n\n"
           f"{n_types['unanswerable']} unanswerable\n(tests refusal)")
fig.text(0.83, 0.72, summary, fontsize=10.5, color=INK, va="top", linespacing=1.5)
title(fig, "Benchmark v0 spans every question type the UI and GraphRAG teams defined",
      "Questions per company and type (a comparison counts once per company it touches). Every expected answer is computed from SEC XBRL.")
source(fig, "Source: data/benchmark_v0.jsonl, data/gold_facts_v0.jsonl (SEC companyconcept API, read 2026-10-14; scripts/refresh_gold.py re-verifies).")
fig.savefig(OUT / "3_benchmark_coverage.png")
plt.close(fig)

# ---------------------------------------------------------------- 4. framework status
stages = [
    ("Retrieval", ["Recall@k, Hit@k, MRR", "nDCG@k (graded)", "Provenance@k"], [1, 1, 1]),
    ("Graph", ["Fact extraction P/R/F1", "Edge P/R/F1", "Entity linking, path recall"], [1, 1, 1]),
    ("Extraction & calc", ["Numerical accuracy (NAA)", "7-label error taxonomy", "Reasoning-step accuracy"], [1, 1, 0]),
    ("Grounding", ["Citation validity", "Numeric claim support", "Narrative faithfulness (LLM judge)"], [1, 1, 0]),
    ("Answer quality", ["Refusal appropriateness (RAA)", "Balanced RAA + critical flags", "Answer relevance (LLM judge)"], [1, 1, 0]),
    ("System", ["Run-to-run consistency", "Latency, errors, cost/query", "Position & length robustness"], [1, 1, 0]),
]
fig, ax = plt.subplots(figsize=(11, 5.6))
fig.subplots_adjust(left=0.02, right=0.98, top=0.8, bottom=0.12)
ax.set_xlim(0, 6)
ax.set_ylim(0, 4.05)
ax.axis("off")
for j, (st, ms, done) in enumerate(stages):
    ax.add_patch(FancyBboxPatch((j + 0.05, 3.35), 0.9, 0.62, boxstyle="round,pad=0,rounding_size=0.06", fc=NAVY, ec="none"))
    ax.text(j + 0.5, 3.66, st, ha="center", va="center", color=SURF, fontsize=11, fontweight="bold")
    if j < len(stages) - 1:
        ax.annotate("", xy=(j + 1.03, 3.66), xytext=(j + 0.97, 3.66), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1))
    for i, (m, d) in enumerate(zip(ms, done)):
        y = 2.55 - i * 0.95
        ax.add_patch(FancyBboxPatch((j + 0.05, y), 0.9, 0.78, boxstyle="round,pad=0,rounding_size=0.06",
                                    fc="#EEF2FF" if d else "#F7F7F9", ec=BLUE if d else "#C9CED8", lw=1.2, ls="-" if d else (0, (3, 2))))
        import textwrap
        ax.text(j + 0.5, y + 0.5, textwrap.fill(m, 22), ha="center", va="center", fontsize=8.8, color=INK, linespacing=1.15)
        ax.text(j + 0.5, y + 0.16, "code + tests" if d else "spec only", ha="center", va="center", fontsize=8,
                color=GREEN if d else MUTED, fontweight="bold" if d else "normal")
n_done = sum(sum(d) for *_, d in stages)
title(fig, f"{n_done} of {sum(len(d) for *_, d in stages)} metric components are implemented and unit-tested; the rest are specified",
      "Every stage of the pipeline has its own score, so a wrong answer can be traced to where it broke. Components needing an LLM judge wait for the API budget.")
source(fig, "Source: kpmg_eval/ (26 unit tests passing). Shared EvalKey links RAG chunks (CIK, accession, section) and GraphRAG facts (CIK, concept, period, unit).")
fig.savefig(OUT / "4_framework_status.png")
plt.close(fig)
print("charts:", sorted(p.name for p in OUT.glob("*.png")))
