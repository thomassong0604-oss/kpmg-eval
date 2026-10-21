"""Metric validation by fault injection ("does the grader catch what it claims to catch?").

No agent exists yet, so we test the graders themselves. For every answerable benchmark item we write
answers containing one known error each, render them two ways, and check the label the metric assigns:
  * structured AnswerBlock (what we are asking the Agent team to return)
  * free text, in several realistic phrasings
For refusal (RAA) we classify refusals, hedged answers and fabricated answers on unanswerable items.
Outputs: results/fault_injection.json and results/fault_injection_cases.csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kpmg_eval.metrics.numeric import score_numeric  # noqa: E402
from kpmg_eval.metrics.refusal import classify_response  # noqa: E402
from kpmg_eval.stats import wilson  # noqa: E402

items = [json.loads(l) for l in open(ROOT / "data" / "benchmark_v0.jsonl")]
answerable = [i for i in items if i["answerable"]]
unanswerable = [i for i in items if not i["answerable"]]


def _fmt_b(x: float) -> str:
    """Billions with at least 3 significant figures: 57.0, 9.07, 0.146"""
    return f"{x:.1f}" if abs(x) >= 10 else f"{x:.2f}" if abs(x) >= 1 else f"{x:.3f}"


def _fmt_m(x: float) -> str:
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:.3g}"


def money_texts(v: float) -> list[tuple[str, str]]:
    m, b = abs(v) / 1e6, abs(v) / 1e9
    sign = "-" if v < 0 else ""
    big = b >= 1
    return [
        ("millions_comma", f"{sign}${_fmt_m(m)} million"),
        ("billions", f"{sign}${_fmt_b(b)} billion" if big else f"{sign}${_fmt_m(m)} million"),
        ("abbrev_bn", f"{sign}${_fmt_b(b)}bn" if big else f"{sign}${_fmt_m(m)}M"),
        ("abbrev_M", f"{sign}{_fmt_m(m)}M"),
        ("sentence", f"The filing shows {'a net loss of ' if v < 0 else 'net income of '}${_fmt_m(m)} million for the period."),
    ]


def pct_texts(v: float) -> list[tuple[str, str]]:
    return [("pct_symbol", f"{v:.1f}%"), ("pct_word", f"{v:.1f} percent"),
            ("pct_sentence", f"It {'rose' if v >= 0 else 'fell'} {abs(v):.1f}% year over year." if v >= 0 else f"It changed by {v:.1f}% year over year.")]


def render(item, value, kind):
    return pct_texts(value) if kind == "percent" else money_texts(value)


def injections(item):
    g = item["gold"]
    truth, kind = float(g["value"]), g.get("kind", "money")
    yield "correct", truth
    for d in g.get("distractors", []):
        if d["label"] in ("wrong_period", "wrong_concept") and float(d["value"]) != truth:
            yield d["label"], float(d["value"])
    if truth != 0:
        yield "wrong_sign", -truth
    if kind == "money":
        yield "wrong_scale", truth * 1e-3
    yield "wrong_value", truth * 1.07
    yield "too_imprecise", None   # rendered specially
    yield "false_refusal", None


rows = []
for it in answerable:
    g = it["gold"]
    truth, kind = float(g["value"]), g.get("kind", "money")
    for injected, v in injections(it):
        # structured block
        if injected == "false_refusal":
            block = {"answered": False}
            texts = [("refusal", "The provided filings do not contain this information.")]
        elif injected == "too_imprecise":
            if kind == "percent":
                block = {"answered": True, "value_text": f"{round(truth):.0f}%", "unit": "%"}
                texts = [("pct_rounded", f"about {round(truth):.0f}%")]
            else:
                # two significant figures, e.g. $57 billion, $9.1 billion, $150 million
                sf2 = float(f"{truth:.2g}")
                sgn = "-" if sf2 < 0 else ""
                txt = f"{sgn}${abs(sf2)/1e9:g} billion" if abs(sf2) >= 1e9 else f"{sgn}${abs(sf2)/1e6:g} million"
                if abs(sf2 - truth) < 1e-9 * abs(truth):   # value already exact at 2 s.f. -> not imprecise
                    continue
                block = {"answered": True, "value_text": txt, "unit": "USD"}
                texts = [("rounded", f"roughly {txt}")]
        else:
            block = {"answered": True, "value": v, "unit": "%" if kind == "percent" else "USD"}
            texts = render(it, v, kind)
        r = score_numeric(it, block)
        rows.append({"qid": it["qid"], "type": it["type"], "format": "structured", "phrasing": "answer_block",
                     "injected": injected, "predicted": r.label, "ok": r.label == injected})
        for phr, txt in texts:
            r = score_numeric(it, txt)
            rows.append({"qid": it["qid"], "type": it["type"], "format": "free_text", "phrasing": phr, "text": txt,
                         "injected": injected, "predicted": r.label, "ok": r.label == injected})

# ---------------- refusal classification ----------------
REFUSALS = ["The filings provided do not contain this information.",
            "I cannot determine this from the available filings.",
            "This figure is not disclosed in the 10-Q.",
            "Apple doesn't break out that number, so I can't give it.",
            "There is insufficient evidence in the retrieved filings to answer."]
HEDGED = ["The filing does not disclose it, but it is likely around $120 billion.",
          "Not reported directly; my estimate is roughly $5.2 billion.",
          "It isn't disclosed, though approximately 60 million units seems plausible."]
FABRICATED = ["Net income was $64,310 million.", "The company reported $1,402 million for the period."]
raa_rows = []
for it in unanswerable:
    for txt in REFUSALS:
        raa_rows.append({"qid": it["qid"], "case": "refusal", "expected": "refused", "predicted": classify_response(txt), "text": txt})
    for txt in HEDGED:
        raa_rows.append({"qid": it["qid"], "case": "hedged", "expected": "answered", "predicted": classify_response(txt), "text": txt})
    for txt in FABRICATED:
        raa_rows.append({"qid": it["qid"], "case": "fabricated", "expected": "answered", "predicted": classify_response(txt), "text": txt})
for r in raa_rows:
    r["ok"] = r["predicted"] == r["expected"]

# ---------------- summarize ----------------
def acc(rs):
    k, n = sum(r["ok"] for r in rs), len(rs)
    lo, hi = wilson(k, n)
    return {"correct": k, "n": n, "accuracy": k / n if n else None, "ci95": [lo, hi]}


summary = {"n_items": len(answerable), "n_unanswerable": len(unanswerable), "by_format": {}, "by_injected": {}, "confusion": {}}
for fmt in ("structured", "free_text"):
    rs = [r for r in rows if r["format"] == fmt]
    summary["by_format"][fmt] = acc(rs)
    summary["by_injected"][fmt] = {lab: acc([r for r in rs if r["injected"] == lab]) for lab in sorted({r["injected"] for r in rs})}
    conf = defaultdict(Counter)
    for r in rs:
        conf[r["injected"]][r["predicted"]] += 1
    summary["confusion"][fmt] = {k: dict(v) for k, v in conf.items()}
summary["free_text_by_phrasing"] = {p: acc([r for r in rows if r["format"] == "free_text" and r["phrasing"] == p])
                                    for p in sorted({r["phrasing"] for r in rows if r["format"] == "free_text"})}
summary["refusal_classifier"] = {c: acc([r for r in raa_rows if r["case"] == c]) for c in ("refusal", "hedged", "fabricated")}
summary["free_text_misses"] = [{k: r[k] for k in ("qid", "phrasing", "text", "injected", "predicted")}
                               for r in rows if r["format"] == "free_text" and not r["ok"]][:40]

out = ROOT / "results"
out.mkdir(exist_ok=True)
(out / "fault_injection.json").write_text(json.dumps(summary, indent=2))
with open(out / "fault_injection_cases.csv", "w", newline="") as f:
    cols = ["qid", "type", "format", "phrasing", "injected", "predicted", "ok", "text"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(f"cases: {len(rows)} numeric, {len(raa_rows)} refusal")
for fmt, s in summary["by_format"].items():
    print(f"{fmt:11s} label accuracy {s['correct']}/{s['n']} = {s['accuracy']:.1%}  CI95 {s['ci95'][0]:.1%}-{s['ci95'][1]:.1%}")
for fmt in ("structured", "free_text"):
    print(fmt, {k: f"{v['correct']}/{v['n']}" for k, v in summary["by_injected"][fmt].items()})
print("phrasing", {k: f"{v['correct']}/{v['n']}" for k, v in summary["free_text_by_phrasing"].items()})
print("refusal classifier", {k: f"{v['correct']}/{v['n']}" for k, v in summary["refusal_classifier"].items()})
for m in summary["free_text_misses"][:15]:
    print("  MISS", m)
