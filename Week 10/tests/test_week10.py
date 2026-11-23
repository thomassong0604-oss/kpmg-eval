"""Week 10: checks on the published result files (the private inputs are not in git, so these read results only)."""
import csv
import json
from pathlib import Path

W10 = Path(__file__).resolve().parent.parent
RES = W10 / "results"
FORBIDDEN = {"question", "answer_text", "value_text", "gold", "answer", "required_points", "quote"}


def test_holdout_hash_and_counts():
    d = json.load(open(RES / "holdout_A_final_v1.json"))
    man = json.load(open(W10.parent / "Week 9" / "results" / "holdout_A_manifest.json"))
    assert d["sealed_file_sha256"] == man["sha256"]
    assert d["questions"] == d["answers_received"] == 40
    n = d["numeric"]
    assert n["accuracy"]["n"] == n["normal"]["n"] + n["stress"]["n"] == n["microsoft"]["n"] + n["other_companies"]["n"] == 30
    assert n["accuracy"]["k"] == n["normal"]["k"] + n["stress"]["k"] == 30 - len(n["misses"])
    assert sum(int(v.split("/")[1]) for v in d["narrative"]["per_question"].values()) == d["narrative"]["points_stated"]["n"]


def test_no_question_or_answer_text_is_published():
    for f in RES.glob("*.csv"):
        cols = set(next(csv.reader(open(f))))
        assert not cols & FORBIDDEN, (f.name, cols & FORBIDDEN)
    assert not list(RES.glob("*.jsonl"))


def test_query_rewrite_arms_are_consistent():
    d = json.load(open(RES / "query_rewrite_arms.json"))
    assert set(d["arms"]) == {"none", "precheck", "rag_llm", "agents", "agents_precheck", "gold"}
    for a in d["arms"].values():
        assert a["rewrites"] == 427 and a["missing"] == 0
        na = a["numeric_accuracy"]
        assert na["n"] == d["number_questions"] == sum(v["n"] for v in a["by_perturbation"].values())
        assert na["k"] == sum(v["k"] for v in a["by_perturbation"].values()) == na["n"] - sum(a["numeric_labels_of_misses"].values())
        assert a["numeric_accuracy_incl_out_of_corpus"]["n"] == na["n"] + 3
    g = d["arms"]["gold"]["numeric_accuracy"]["k"]
    for arm, lost in d["right_under_gold_filters_but_wrong_in_arm"].items():
        p = d["pairwise_number_questions"][f"{arm} vs gold"]
        assert p["only_second_right"] == lost and d["arms"][arm]["numeric_accuracy"]["k"] == g - lost + p["only_first_right"]
