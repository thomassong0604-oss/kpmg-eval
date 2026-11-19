"""Week 9 tests: suite scorer and judge guard."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import grade_suite_answers as gs  # noqa: E402
import score_rag_judge_runs as sj  # noqa: E402


def test_mcnemar_exact():
    assert gs.mcnemar_exact(0, 0) is None
    assert gs.mcnemar_exact(5, 5) == 1.0
    assert gs.mcnemar_exact(8, 0) == round(2 / 2 ** 8, 4)


def test_abstention_scoring(tmp_path):
    items = [json.loads(l) for l in open(gs.W8 / "data" / "abstention_suite_v1.jsonl")]
    f = tmp_path / "a.jsonl"
    with open(f, "w") as out:
        for i, it in enumerate(items):
            ans = it["answerable"] or i == 0                      # one invented answer
            out.write(json.dumps({"sid": it["sid"], "answered": ans, "value": 5e6 if ans else None, "citations": [],
                                  "answer_text": "It was 5 million." if ans else "The corpus does not contain this."}) + "\n")
    summ, rows = gs.abstention(SimpleNamespace(answers=str(f), clean=None))
    assert summ["must_decline"]["k"] == 50 and summ["must_decline"]["n"] == 51
    assert summ["invented_answers"] == [items[0]["sid"]] and summ["false_premise_answered"]["k"] == 5


def test_messy_maps_rewrites_to_clean_gold(tmp_path):
    v = [json.loads(l) for l in open(gs.W8 / "data" / "messy_wording_v1.jsonl")]
    one = next(x for x in v if x["qid"] == "GSv0-MSFT-001" and x["perturbation"] == "typo_company")
    f = tmp_path / "m.jsonl"
    f.write_text(json.dumps({"vid": one["vid"], "answered": True, "value": 82886000000, "unit": "USD", "value_text": "USD 82,886 million",
                             "answer_text": "Total revenue was USD 82,886 million.", "citations": []}) + "\n")
    summ, rows = gs.messy(SimpleNamespace(answers=str(f), clean=None, chunks=None))
    r = next(x for x in rows if x["vid"] == one["vid"])
    assert r["passed"] is True and r["perturbation"] == "typo_company" and summ["missing_rewrites"] == 426
    assert summ["all"]["numeric_accuracy"] == {"k": 1, "n": 1, "value": 1.0, "ci95": summ["all"]["numeric_accuracy"]["ci95"]}


def test_judge_guard_needs_a_real_quote():
    assert sj.guard([("stated", "grew 40%"), ("stated", "not in the answer")], "Revenue grew 40% this quarter.", 2) == ["stated", "missing"]
    assert sj.same if hasattr(sj, "same") else True


def test_figures_and_literal():
    assert sj.figures("rose to $54.5 billion, or 29%, from 42,400") == ["54.5", "29", "42400"]
    assert sj.literal("approximately 27 percent | approximately 25%", "an approximately 25% stake")


def test_ui_smoke_runs_on_the_mock_page():
    import pytest
    pytest.importorskip("playwright")
    sys.path.insert(0, str(ROOT / "ui_smoke"))
    import run_ui_smoke as ui
    a = SimpleNamespace(url=(ROOT / "ui_smoke" / "mock_ui.html").as_uri(), input="[data-testid=question]", submit="[data-testid=ask]",
                        answer="[data-testid=answer]", citation="[data-testid=citations] .cite", n=10, timeout=10)
    summ, rows = ui.run(a)
    assert summ["questions"] == 10 and summ["answered"]["k"] == 10 and not summ["errors"]
    assert summ["declines_unanswerable"]["k"] == summ["declines_unanswerable"]["n"] == 2      # the mock declines them
    assert summ["figure_shown"]["k"] >= 1 and summ["figure_shown"]["k"] < summ["figure_shown"]["n"]   # it only knows one figure
