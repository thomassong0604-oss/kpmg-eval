"""Week 8: LLM judge for narrative answers (30 questions in Gold Set v2.2), point by point.

    # 1. see exactly what the judge is asked (no key needed); also writes a labelling sheet for the human check
    python scripts/run_narrative_judge.py --answers private/rag_round1_answer_blocks.jsonl \
        --chunks private/chunks_C1.jsonl --dry-run
    # 2. run it (needs OPENAI_API_KEY or ANTHROPIC_API_KEY)
    python scripts/run_narrative_judge.py --answers ... --chunks ... --provider openai --model gpt-4o --tag rag_reader_round1
    # 3. before the score is used as a headline: compare with Eval's hand labels on the same points
    python scripts/run_narrative_judge.py --validate private/narrative_labels.csv --tag rag_reader_round1

Rubric. For each required point of the gold answer the judge returns stated / missing / contradicted, plus the shortest
quote from the answer that states it. Paraphrase counts; numbers must match at the precision written; the opposite
direction ("rose" for "fell") is contradicted. With the cited passages, it also lists claims no cited passage supports.
Deterministic guard: a "stated" verdict whose quote is not in the answer is downgraded to missing.

Scores: point recall (stated / points), pass (every point stated, none contradicted), contradictions, unsupported
claims. Temperature 0. Use a judge model other than the reader's (gpt-4o-mini) to avoid self-preference.
Outputs: results/narrative_judge_<tag>.json (verdicts and ids; no answer or chunk text).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RES, PRIV = ROOT / "data", ROOT / "results", ROOT / "private"
sys.path.insert(0, str(ROOT))

SYSTEM = ("You grade answers to questions about SEC filings against a reference answer. Judge only what the answer "
          "states; do not use outside knowledge. Reply with JSON only.")
TEMPLATE = """Question:
{question}

Reference answer:
{reference}

Required points (the answer must state each one):
{points}

Answer to grade:
{answer}

{passages}For each required point, return its verdict:
- "stated": the answer states it (paraphrase is fine; a number must match at the precision the answer writes it)
- "contradicted": the answer states something incompatible (another number, the opposite direction)
- "missing": otherwise
and "quote": the shortest exact span copied from the answer that states or contradicts it ("" if missing).
{unsupported_rule}
Return: {{"points": [{{"point": 1, "verdict": "...", "quote": "..."}}, ...]{unsupported_key}}}"""
PROMPT_SHA = hashlib.sha256((SYSTEM + TEMPLATE).encode()).hexdigest()[:12]


def build_prompt(q: dict, a: dict, passages: list[str]) -> str:
    pts = q["answer"]["required_points"]
    ptxt = "\n".join(f"{i}. {p.replace(' | ', ' (or) ')}" for i, p in enumerate(pts, 1))
    psg = ""
    if passages:
        psg = "Passages the answer cites:\n" + "\n---\n".join(p[:2500] for p in passages[:6]) + "\n\n"
    return TEMPLATE.format(
        question=q["question"], reference=q["answer"]["display"], points=ptxt, answer=a.get("answer_text") or "",
        passages=psg,
        unsupported_rule=("Also list \"unsupported\": each claim in the answer (a number or a stated reason) that none of "
                          "the cited passages supports." if passages else ""),
        unsupported_key=', "unsupported": ["..."]' if passages else "")


def call(provider: str, model: str, prompt: str) -> dict:
    if provider == "openai":
        from openai import OpenAI
        r = OpenAI().chat.completions.create(model=model, temperature=0, response_format={"type": "json_object"},
                                             messages=[{"role": "system", "content": SYSTEM},
                                                       {"role": "user", "content": prompt}])
        return json.loads(r.choices[0].message.content)
    import anthropic
    r = anthropic.Anthropic().messages.create(model=model, max_tokens=1500, temperature=0, system=SYSTEM,
                                              messages=[{"role": "user", "content": prompt}])
    t = r.content[0].text
    return json.loads(t[t.find("{"): t.rfind("}") + 1])


def guard(verdicts: list[dict], answer_text: str, n_points: int) -> list[str]:
    """One verdict per point; 'stated' or 'contradicted' needs a quote that is really in the answer."""
    low = " ".join(answer_text.lower().split())
    out = ["missing"] * n_points
    for v in verdicts:
        i = int(v.get("point", 0)) - 1
        if 0 <= i < n_points and v.get("verdict") in ("stated", "contradicted"):
            quote = " ".join((v.get("quote") or "").lower().split())
            out[i] = v["verdict"] if quote and quote in low else "missing"
    return out


def load(a):
    gold = {q["qid"]: q for q in map(json.loads, open(DATA / "benchmark_v2_2.jsonl")) if q["answer_type"] == "narrative"}
    answers = {b["qid"]: b for b in map(json.loads, open(a.answers)) if b["qid"] in gold}
    chunks = {}
    if a.chunks:
        for line in open(a.chunks):
            c = json.loads(line)
            chunks[c["chunk_id"]] = c["text"]
    return gold, answers, chunks


def validate(labels_path: str, tag: str):
    """Agreement between the judge and hand labels (Cohen's kappa over the three verdicts)."""
    res = json.loads((RES / f"narrative_judge_{tag}.json").read_text())
    judge = {(r["qid"], i + 1): v for r in res["questions"] for i, v in enumerate(r["verdicts"])}
    pairs = [(row["human_verdict"].strip(), judge[(row["qid"], int(row["point"]))])
             for row in csv.DictReader(open(labels_path)) if row.get("human_verdict", "").strip()
             and (row["qid"], int(row["point"])) in judge]
    n = len(pairs)
    po = sum(h == j for h, j in pairs) / n
    cats = ("stated", "missing", "contradicted")
    pe = sum((sum(h == c for h, _ in pairs) / n) * (sum(j == c for _, j in pairs) / n) for c in cats)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    res["validation"] = {"labels": Path(labels_path).name, "points": n, "agreement": round(po, 3), "kappa": round(kappa, 3),
                         "use_as_headline": kappa >= 0.6}
    (RES / f"narrative_judge_{tag}.json").write_text(json.dumps(res, indent=1))
    print(f"[judge] validation on {n} points: agreement {po:.2f}, kappa {kappa:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers")
    ap.add_argument("--chunks")
    ap.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--tag", default="external")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validate", help="CSV of hand labels: qid, point, human_verdict")
    a = ap.parse_args()
    if a.validate:
        return validate(a.validate, a.tag)
    gold, answers, chunks = load(a)
    prompts = {}
    for qid, q in gold.items():
        b = answers.get(qid)
        if not b or b.get("answered") is False:
            continue
        passages = [chunks[c["id"]] for c in b.get("citations", []) if c.get("id") in chunks]
        prompts[qid] = build_prompt(q, b, passages)
    if a.dry_run:
        PRIV.mkdir(exist_ok=True)
        (PRIV / f"judge_prompts_{a.tag}.jsonl").write_text(
            "".join(json.dumps({"qid": k, "system": SYSTEM, "prompt": v}) + "\n" for k, v in prompts.items()))
        with open(PRIV / f"narrative_labels_{a.tag}_blank.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["qid", "point", "required_point", "answer_text", "human_verdict"])
            for qid in prompts:
                for i, p in enumerate(gold[qid]["answer"]["required_points"], 1):
                    w.writerow([qid, i, p, answers[qid]["answer_text"] if i == 1 else "", ""])
        print(f"[judge] dry run: {len(prompts)} prompts (sha {PROMPT_SHA}) -> private/judge_prompts_{a.tag}.jsonl; "
              f"labelling sheet -> private/narrative_labels_{a.tag}_blank.csv")
        return
    key = "OPENAI_API_KEY" if a.provider == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(key):
        sys.exit(f"[judge] {key} is not set; run with --dry-run to see the prompts")
    rows = []
    for qid, prompt in prompts.items():
        out = call(a.provider, a.model, prompt)
        n = len(gold[qid]["answer"]["required_points"])
        v = guard(out.get("points", []), answers[qid].get("answer_text") or "", n)
        rows.append({"qid": qid, "verdicts": v, "point_recall": round(v.count("stated") / n, 3),
                     "passed": v.count("stated") == n, "contradicted": v.count("contradicted"),
                     "unsupported_claims": len(out.get("unsupported", []))})
    n_all = len(gold)
    summary = {"judge": {"provider": a.provider, "model": a.model, "temperature": 0, "prompt_sha": PROMPT_SHA},
               "narrative_questions": n_all, "judged": len(rows), "not_answered": n_all - len(rows),
               "pass_rate_all": round(sum(r["passed"] for r in rows) / n_all, 3),
               "point_recall_mean_all": round(sum(r["point_recall"] for r in rows) / n_all, 3),
               "answers_with_contradiction": sum(r["contradicted"] > 0 for r in rows),
               "answers_with_unsupported_claims": sum(r["unsupported_claims"] > 0 for r in rows) if chunks else None,
               "validation": None, "questions": rows}
    (RES / f"narrative_judge_{a.tag}.json").write_text(json.dumps(summary, indent=1))
    print(f"[judge] {len(rows)} judged: pass {summary['pass_rate_all']}, point recall {summary['point_recall_mean_all']}")


if __name__ == "__main__":
    main()
