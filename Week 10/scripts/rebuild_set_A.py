"""Week 10: recover set_A.jsonl without the seed, and prove it is the same file.

    python scripts/rebuild_set_A.py     -> private/xbrl/out/set_A.jsonl  (only written if its SHA-256 equals the published one)

Set A's questions came back in RAG's per-question files after the run. Each question is a fixed template of one metric row, so
the row can be found again in the saved metric rows and passed through RAG's builder (6b7d53b) to regenerate the exact item.
The result is accepted only if the whole file hashes to the value published in results/xbrl_set_A_manifest.json on 11/25.
"""
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
X = ROOT / "private" / "xbrl"
RAG = ROOT / "upstream" / "KPMG_RAG"


def main():
    spec = importlib.util.spec_from_file_location("bos", RAG / "scripts" / "build_objective_set.py")
    bos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bos)
    want = json.load(open(ROOT / "results" / "xbrl_set_A_manifest.json"))["sha256"]
    rows = json.load(open(X / "in" / "metric_rows.json"))
    frozen = {r["accession_number"].strip() for r in csv.DictReader(open(RAG / "eval" / "round1_filings.csv")) if r.get("validation_status", "passed") == "passed"}
    pool, _ = bos.population(rows, frozen, set(bos.CORE), None, None)      # no exclusion file needed: the drawn rows are in the pool either way
    by_q = {}
    for r in pool:
        by_q.setdefault(bos.question_text(r), []).append(r)
    src = sys.argv[1] if len(sys.argv) > 1 else str(X / "returns" / "xbrl_B_return" / "xbrl_B_gold_per_question.csv")
    qs = sorted(csv.DictReader(open(src)), key=lambda r: r["qid"])
    lines, ambiguous = [], 0
    for q in qs:
        cand = by_q.get(q["question"], [])
        assert cand, f"no metric row for {q['qid']}"
        ambiguous += len(cand) > 1
        r = cand[0]
        it = bos.to_item(r, q["qid"], {"set": "A", "statement": r["statement_type"], "relation": "current" if r["period_end"] == r["reporting_period_end"] else "prior"})
        lines.append(json.dumps(it, ensure_ascii=False) + "\n")
    body = "".join(lines).encode("utf-8")
    got = hashlib.sha256(body).hexdigest()
    print(len(qs), "questions; ambiguous rows:", ambiguous, "; sha256", got[:16], "published", want[:16], "MATCH" if got == want else "NO MATCH")
    if got == want:
        (X / "out").mkdir(parents=True, exist_ok=True)
        (X / "out" / "set_A.jsonl").write_bytes(body)


if __name__ == "__main__":
    main()
