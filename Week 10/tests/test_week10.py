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


def test_holdout_B_and_hand_labels():
    d = json.load(open(RES / "holdout_B_final_v2.json"))
    man = json.load(open(W10.parent / "Week 9" / "results" / "holdout_B_manifest.json"))
    assert d["sealed_file_sha256"] == man["sha256"] and d["questions"] == d["answers_received"] == 30
    nar = d["narrative"]
    assert nar["every_point_stated"]["n"] == nar["normal"]["n"] + nar["stress"]["n"] == 18
    assert nar["every_point_stated_excluding_previewed"]["n"] == 18 - len(nar["previewed_before_run"])
    j = json.load(open(RES / "judge_vs_hand_labels.json"))
    assert j["labels"]["points"] == 126 == j["gpt6sol"]["both_runs"]["points"]
    for judge in ("claude", "gpt6sol"):
        for run in ("final_v1", "narr_long"):
            x = j[judge][run]
            assert x["points"] - x["agree"] == len(x["disagreements"])
            assert all(v["human"] != "stated" and v["judge"] == "stated" for v in x["disagreements"])   # judges only ever over-credit
    c = j["eval_pass_counts_with_hand_labels_applied"]
    assert all(v["with_hand_labels"] <= v["judge_only"] for v in c.values())


def test_clean_pairs_add_up():
    d = json.load(open(RES / "query_rewrite_followups.json"))
    arms = json.load(open(RES / "query_rewrite_arms.json"))["arms"]
    for arm, x in d["clean_vs_messy_numbers"]["arms"].items():
        assert x["both_right"] + x["only_clean_right"] + x["only_rewrite_right"] + x["neither"] == x["pairs"] == 264
        assert x["both_right"] + x["only_rewrite_right"] == arms[arm]["numeric_accuracy"]["k"]
    n = d["narrative_rewrites_judged_by_rag"]
    for arm in ("precheck", "agents"):
        a = n["arms"][arm]
        assert a["answers_citing_a_gold_filing"]["n"] + a["answers_citing_only_other_filings"]["n"] == a["answered"]
        assert not a["citation_flag_differs_from_ours"] and not a["answered_flag_differs_from_our_file"]


def test_xbrl_manifests():
    for S, n in (("A", 150), ("C", 100), ("C2", 100)):
        d = json.load(open(RES / f"xbrl_set_{S}_manifest.json"))
        c = d["checks"]
        assert d["questions"] == n and d["builder"]["commit"] == "6b7d53b" and len(d["sha256"]) == 64 and len(d["seed"]["sha256_of_seed"]) == 64
        assert d["metric_rows"]["sha256"].startswith("7c7bb541") and c["rule_a_overlap_by_concept"] == c["rule_a_overlap_by_value"] == c["duplicates_within_set"] == 0
        for k in ("rule_d_precision_floor_equals_printed_digits", "rule_d_asked_unit_equals_table_scale", "gold_value_equals_printed_figure", "questions_well_formed"):
            assert c[k] == f"{n}/{n}", k
        g = c["grader_dry_run"]
        assert g["perfect_answer_in_the_asked_unit"]["passed"] == n and g["sign_flipped"]["passed"] == 0 and g["value_off_by_1_percent_or_5_cents_per_share"]["passed"] == 0
        assert "seed.txt" not in json.dumps(d) and "question" not in {k for k in d if k != "questions"}
    assert "by_company" not in json.load(open(RES / "xbrl_set_C_manifest.json"))
    c, c2 = (json.load(open(RES / f"xbrl_set_{S}_manifest.json")) for S in ("C", "C2"))
    assert c["status"].startswith("RETIRED") and c2["replaces"]["sha256"] == c["sha256"] != c2["sha256"]
    assert c2["seed"]["sha256_of_seed"] != c["seed"]["sha256_of_seed"] and "by_company" not in c2


def test_xbrl_B_score():
    d = json.load(open(RES / "xbrl_B_final_v1.json"))
    assert d["question_file_sha256"] == json.load(open(RES / "xbrl_set_A_manifest.json"))["sha256"] and d["questions"] == 150
    p = d["gold_vs_precheck_filters"]
    assert p["both_right"] + p["only_gold_filters_right"] + p["only_precheck_right"] + p["neither"] == 150
    for cfg, x in d["configs"].items():
        s = x["numeric_accuracy_strict"]
        assert s["n"] == 150 == sum(x["labels"].values()) and x["declined"] + x["answered"]["k"] == 150
        assert s["k"] == sum(v["k"] for v in x["by_company"].values()) == x["answered"]["k"] - x["wrong_answers_given"]
        assert x["numeric_accuracy_sign_insensitive_on_cash_outflow"]["k"] == s["k"] + x["cash_outflow_questions"]["wrong_sign"]
        assert not x["differs_from_rags_own_grader"]
    assert d["configs"]["gold"]["numeric_accuracy_strict"]["k"] == p["both_right"] + p["only_gold_filters_right"]
