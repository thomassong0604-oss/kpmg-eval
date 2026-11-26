"""Week 10: Eval holds XBRL objective sets A and C. This checks them without anyone reading the questions and writes the public manifests.

    python scripts/check_objective_sets.py            sets A and C as first built on 11/25 (needs their private files)
    python scripts/check_objective_sets.py --only C2  the replacement Set C built on 11/26 with a new seed
        private/xbrl/in/metric_rows.json        RAG's saved pull (11/16), received 11/25
        private/xbrl/out/set_A.jsonl, set_C.jsonl   built with RAG's scripts/build_objective_set.py at 6b7d53b and Eval's private seed
        private/xbrl/seed.txt                   the seed (never published; only its SHA-256)
        -> results/xbrl_set_A_manifest.json, results/xbrl_set_C_manifest.json   (hashes, counts and check results only)

Checks: file hashes; strata counts; rule a (nothing a dev or holdout question uses), by XBRL concept as the builder does and again
by value; rule d (precision floor equals the digits printed in the gold cell; asked unit equals the table's scale); every question
is well formed; for set A, every gold filing is in the frozen round-1 index and the printed figure is present in its chunks;
a dry run of Eval's grader on perfect, slightly wrong, rounded and sign-flipped answers.
"""
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W8, W9 = ROOT.parent / "Week 8", ROOT.parent / "Week 9"
X = ROOT / "private" / "xbrl"
sys.path[:0] = [str(W9 / "scripts")]
import grade_suite_answers as gsa  # noqa: E402
gab, FactIndex = gsa.gab, gsa.FactIndex
from kpmg_eval.normalize import extract_quantities  # noqa: E402

EXCLUDE = [W8 / "data" / "benchmark_v2_2.jsonl", W9 / "private" / "holdout_A.jsonl", W9 / "private" / "holdout_B.jsonl"]
OUTFLOW = {"capital_expenditures", "dividends_paid"}
QPAT = re.compile(r"^What was [^?]{2,80}(?:'s|') [a-z][^?]{3,90} (?:as of|for the (?:fiscal year|three months|six months|nine months) ended) [A-Z][a-z]+ \d{1,2}, 20\d\d\? "
                  r"Answer in USD (?:millions|thousands|per share)\.$")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731


def sig_figs(display):
    m = re.search(NUM, display or "")
    s = m.group(0).replace(",", "")
    d = s.replace(".", "").lstrip("0")
    return len(d.rstrip("0") if "." not in s else d) or 1


def used():
    keys, vals = set(), set()
    for p in [p for p in EXCLUDE if p.exists()]:
        for q in map(json.loads, open(p)):
            for f in (q.get("facts") or []) + ((q.get("gold") or {}).get("evidence") or []):
                if f.get("ticker") and f.get("concept") and f.get("period_end"):
                    keys.add((f["ticker"].upper(), f["concept"].split(":")[-1], str(f["period_end"])[:10]))
            for k, v in (q.get("fact_values") or {}).items():
                vals.add((k.split("|")[0], round(float(v))))
            if q.get("answer_type") == "exact_numeric" and isinstance(q["answer"].get("value"), (int, float)):
                for t in q.get("tickers") or []:
                    vals.add((t, round(float(q["answer"]["value"]))))
    return keys, vals


NUM = r"(?:\d[\d,]*(?:\.\d+)?|\.\d+)"


def trailing_zero_rule(q, block) -> bool:
    """Pre-run rule (11/25): an answer that equals the gold value is correct even when it drops zeros printed after the
    decimal point ("7,043" for a cell printed "7,043.0"). Only looked at when the grader says too_imprecise."""
    cell = re.search(NUM, q["gold_cell"]["display_text"]).group(0)
    if "." not in cell or not cell.endswith("0"):
        return False
    kept = len(cell.split(".")[1].rstrip("0"))
    div = {"USD per share": 1.0, "USD thousands": 1e3, "USD millions": 1e6}[q["answer_unit"]]
    m = re.search(r"(-?)\s*\(?(" + NUM + r")\)?\s*(thousand|million|billion)?", (block.get("value_text") or block.get("answer_text") or "").replace("USD", "").replace("$", ""))
    if not m:
        return False
    said = float(m.group(2).replace(",", "")) * {"thousand": 1e3, "million": 1e6, "billion": 1e9, None: div}[m.group(3)] * (-1 if m.group(1) else 1)
    return abs(said - float(q["answer"]["value"])) <= 0.5 * 10 ** -kept * div * 1e-6 + 1e-9 * div


def grade_objective(items, blocks):
    """Eval's grader, unchanged, plus the trailing-zero rule. Returns the grader's rows."""
    gold = {q["qid"]: {**q, "route_expected": q.get("route_expected", "sql")} for q in items if q["qid"] in blocks}
    _, rows = gab.grade(gold, blocks, FactIndex.from_jsonl(W8 / "data" / "msft_xbrl_facts.jsonl"), None)
    for r in rows:
        if r["label"] == "too_imprecise" and trailing_zero_rule(gold[r["qid"]], blocks[r["qid"]]):
            r.update(passed=True, label="correct_trailing_zero_dropped")
    return rows


def answer_block(q, value, text):
    return {"qid": q["qid"], "answered": True, "answer_text": text, "value": value, "value_text": text, "unit": q["answer"]["unit"],
            "period_end": q["facts"][0]["period_end"], "citations": []}


def spoken(q, value, digits=None):
    """An answer in the unit the question asks for, as a system would write it."""
    if q["answer_unit"] == "USD per share":
        return f"USD {value:,.2f} per share"
    div, word = (1e3, "thousand") if q["answer_unit"] == "USD thousands" else (1e6, "million")
    v = value / div
    if digits:                      # round to that many significant figures
        from math import floor, log10
        v = round(v, digits - 1 - floor(log10(abs(v))))
    return f"USD {v:,.0f} {word}" if float(v).is_integer() else f"USD {v:,} {word}"


def dry_run(items):
    def run(make):
        blocks = {q["qid"]: make(q) for q in items}
        blocks = {k: v for k, v in blocks.items() if v}
        rows = grade_objective(items, blocks)
        return {"n": len(rows), "passed": sum(bool(r["passed"]) for r in rows), "labels": dict(Counter(r["label"] for r in rows))}
    v = lambda q: float(q["answer"]["value"])  # noqa: E731
    money = lambda q: q["answer_unit"] != "USD per share"  # noqa: E731
    off = lambda q: v(q) * 1.01 if money(q) else v(q) + 0.05  # noqa: E731
    return {"perfect_answer_in_the_asked_unit": run(lambda q: answer_block(q, v(q), spoken(q, v(q)))),
            "value_off_by_1_percent_or_5_cents_per_share": run(lambda q: answer_block(q, off(q), spoken(q, off(q)))),
            "rounded_to_2_significant_figures": run(lambda q: answer_block(q, None, spoken(q, v(q), 2)) if money(q) and q["answer"]["min_sig_figs"] > 2 else None),
            "sign_flipped": run(lambda q: answer_block(q, -v(q), spoken(q, -v(q))))}


CORE = {"AAPL", "CASY", "MCK", "MDT", "MSFT", "MU", "NKE", "NTAP", "PH", "TTWO"}


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    rows_sha = sha(X / "in" / "metric_rows.json")
    assert rows_sha == "7c7bb541375b3afc82880256a1500b86c266bc9831d19effed9fd34b677e8496", "metric rows differ from the hash RAG published"
    keys, vals = used()
    chunks_by_acc = {}
    if only is None:
        for c in map(json.loads, open(W8 / "private" / "chunks_C1.jsonl")):
            chunks_by_acc.setdefault(c["accession"], []).append(c["text"])
    for S in ([only] if only else ["A", "C"]):
        seed = (X / ("seed_C2.txt" if S == "C2" else "seed.txt")).read_text().strip()
        items = [json.loads(l) for l in open(X / "out" / f"set_{S}.jsonl")]
        man = json.load(open(X / "c2" / "set_C_manifest.json" if S == "C2" else X / "out" / f"set_{S}_manifest.json"))
        assert man["seed_sha256"] == hashlib.sha256(seed.encode()).hexdigest()[:16] and man["git_commit"] == "6b7d53b"
        concept_hits = [q["qid"] for q in items if any((f["ticker"].upper(), f["concept"].split(":")[-1], f["period_end"][:10]) in keys for f in q["facts"])]
        value_hits = [q["qid"] for q in items if (q["tickers"][0], round(float(q["answer"]["value"]))) in vals]
        dup = len(items) - len({(q["tickers"][0], q["metric_key"], q["facts"][0]["period_start"], q["facts"][0]["period_end"]) for q in items})
        prec, scale_ok, printed_ok, tz = [], [], [], []
        for q in items:
            cell = q["gold_cell"]["display_text"]
            prec.append(q["answer"]["min_sig_figs"] == sig_figs(cell))
            div = {"USD per share": 1.0, "USD thousands": 1e3, "USD millions": 1e6}[q["answer_unit"]]
            scale_ok.append(q["answer_unit"] == "USD per share" or q["printed_scale"] == div)
            tz.append("." in cell and re.search(NUM, cell).group(0).endswith("0"))
            p = float(re.search(NUM, cell).group(0).replace(",", ""))
            printed_ok.append(abs(abs(float(q["answer"]["value"])) / div - p) <= 0.5 * 10 ** -(len(cell.split(".")[1]) if "." in cell else 0) + 1e-9)
        out = {"_doc": f"XBRL objective set {S}: held by Eval, sealed until the run. Hashes, counts and check results only.",
               "set": S, "file": f"set_{S}.jsonl", "sha256": sha(X / "out" / f"set_{S}.jsonl"), "built": "2026-11-25", "questions": len(items),
               "builder": {"repo": "Rachel-xs/KPMG_RAG", "script": "scripts/build_objective_set.py", "commit": "6b7d53b",
                           "script_sha256": sha(ROOT / "upstream" / "KPMG_RAG" / "scripts" / "build_objective_set.py")},
               "metric_rows": {"sha256": rows_sha, "rows": man["rows_pulled"], "pulled_by_RAG": "2026-11-16"},
               "seed": {"sha256_of_seed": hashlib.sha256(seed.encode()).hexdigest(), "bits": 128, "chosen_by": "Eval, private",
                        "note": "With the seed, the builder at this commit and these rows reproduce the file exactly; the seed is published after the last run."},
               "excluded_question_files": {p.name: sha(p) for p in EXCLUDE if p.name in man["excluded_question_files"]}, "used_keys": man["n_used_keys"],
               "population_after_exclusions": man["population_after_exclusions"], "exclusions": man["exclusions"],
               "by_statement": man["by_statement"], "by_relation": man["by_relation"], "by_answer_unit": man["by_answer_unit"], "by_metric": man["by_metric"],
               "by_form": dict(Counter(q["filters"]["form"] for q in items)), "companies": len({q["tickers"][0] for q in items}),
               "negative_gold_values": sum(float(q["answer"]["value"]) < 0 for q in items),
               "cash_outflow_questions": {"n": sum(q["metric_key"] in OUTFLOW for q in items),
                                          "printed_in_parentheses": sum(q["metric_key"] in OUTFLOW and "(" in (q["gold_cell"]["display_text"] or "") for q in items),
                                          "gold_is_positive": sum(q["metric_key"] in OUTFLOW and float(q["answer"]["value"]) > 0 for q in items)},
               "scoring_rules_fixed_before_the_run": {
                   "grader": "Eval's Week 8 grader, unchanged (grade_answer_blocks.grade), same precision floor and tolerance as the development set",
                   "trailing_zeros": f"an answer equal to the gold value is correct even if it drops zeros printed after the decimal point; {sum(tz)} questions have such a cell",
                   "sign": "strict is the primary score: the gold value carries the XBRL sign (cash paid is positive, a loss is negative). "
                           "A second, labelled score ignores the sign on the cash-outflow questions only, because their cells are printed in parentheses"},
               "checks": {"rule_a_overlap_by_concept": len(concept_hits), "rule_a_overlap_by_value": len(value_hits), "duplicates_within_set": dup,
                          "rule_d_precision_floor_equals_printed_digits": f"{sum(prec)}/{len(items)}",
                          "rule_d_asked_unit_equals_table_scale": f"{sum(scale_ok)}/{len(items)}",
                          "gold_value_equals_printed_figure": f"{sum(printed_ok)}/{len(items)}",
                          "questions_well_formed": f"{sum(bool(QPAT.match(q['question'])) for q in items)}/{len(items)}",
                          "grader_dry_run": dry_run(items)}}
        if S == "A":
            out["by_company"] = man["by_company"]
            accs = {q["facts"][0]["accession"] for q in items}
            out["checks"]["gold_filings"] = len(accs)
            out["checks"]["gold_filing_in_frozen_index"] = f"{sum(q['facts'][0]['accession'] in chunks_by_acc for q in items)}/{len(items)}"
            def in_chunks(q):
                cell = re.search(NUM, q["gold_cell"]["display_text"]).group(0)
                return any(re.search(r"(?<![\d,.])" + re.escape(cell) + r"(?![\d,]|\.\d)", t) for t in chunks_by_acc.get(q["facts"][0]["accession"], []))
            out["checks"]["printed_figure_found_in_the_filings_chunks"] = f"{sum(in_chunks(q) for q in items)}/{len(items)}"
            out["delivery"] = "sent to RAG by DM as a zip at run time; runs on the frozen round-1 index"
        elif S == "C":
            out["delivery"] = "held until RAG has built and recorded index_full (the 412 non-core filings); then sent by DM as a zip"
        else:
            assert not {q["tickers"][0] for q in items} & CORE
            out["set"] = "C"
            out["built"] = "2026-11-26"
            out["replaces"] = {"sha256": "53664be8bfd09d1a4c012c0fee8ad5722d2825d68d13dfbbcc6634782d6d3b13",
                               "why": "The first Set C and the first seed reached RAG by mistake on 11/25, before the run (disclosed by RAG on 11/26; "
                                      "RAG reports the file unopened and the seed unused). Set C was drawn again with a new seed."}
            out["index_fixed_before_this_draw"] = "index_full 37c4eb2f1628 was recorded in RAG's pre-registration at 0ca6fb3 (2026-11-24), before this set was drawn"
            out["exclusion_note"] = ("Built with the development set as the only exclusion file: the holdout files were not in this workspace and cannot "
                                     "affect Set C, which contains no core company (population and exclusion counts are identical to the first build).")
            out["checks"]["core_companies_in_set"] = 0
            out["delivery"] = "sent to RAG by DM as set_C2.zip; runs on index_full"
        # the file travels zipped so a chat preview cannot show a question; fixed timestamp, so the zip hash is reproducible
        zi = zipfile.ZipInfo(f"set_{S}.jsonl", date_time=(2026, 11, 25, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(X / "out" / f"set_{S}.zip", "w") as z:
            z.writestr(zi, (X / "out" / f"set_{S}.jsonl").read_bytes())
        out["zip"] = {"file": f"set_{S}.zip", "sha256": sha(X / "out" / f"set_{S}.zip")}
        out["inspection"] = ("Nobody has read the questions. All checks ran automatically and none flagged an item." if S == "C2" else
                             "Nobody has read the questions. Checks ran automatically; for the items a check flagged (2 in A, 2 in C) "
                             "only the printed figure and value fields were looked at.")
        (ROOT / "results" / f"xbrl_set_{S}_manifest.json").write_text(json.dumps(out, indent=1))
        print(json.dumps({k: out[k] for k in ("set", "sha256", "questions", "companies", "by_form", "negative_gold_values", "cash_outflow_questions", "checks")}, indent=1))
        print("concept hits", concept_hits, "value hits", value_hits, "not well formed", [q["qid"] for q in items if not QPAT.match(q["question"])][:10],
              "printed mismatch", [q["qid"] for q, ok in zip(items, printed_ok) if not ok][:10], "prec mismatch", [q["qid"] for q, ok in zip(items, prec) if not ok][:10])


if __name__ == "__main__":
    main()
