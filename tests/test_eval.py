import json
from pathlib import Path
from run_eval import evaluate, to_markdown
from vision.providers.heuristic import HeuristicProvider

CASES = Path(__file__).parent.parent / "eval" / "labelled_cases.json"


def make_case(root, case_id, metrics):
    d = root / case_id
    d.mkdir(parents=True)
    (d / "screenshot.png").write_bytes(b"fake")
    (d / "metrics.json").write_text(json.dumps(metrics))


def test_eval_scores_tp_fp_and_no_data(tmp_path):
    make_case(tmp_path, "overflow_mobile", {"scroll_width": 1200})
    make_case(tmp_path, "clean_mobile", {"scroll_width": 390})
    make_case(tmp_path, "overlap_text_mobile", {"scroll_width": 390})
    res = evaluate(HeuristicProvider(), CASES, tmp_path)
    by = {r["case_id"]: r for r in res["rows"]}
    assert by["overflow_mobile"]["tp"] == 1 and by["overflow_mobile"]["fn"] == 0
    assert by["clean_mobile"]["fp"] == 0 and by["clean_mobile"]["tp"] == 0
    assert by["overlap_text_mobile"]["fn"] == 1      # heuristic cannot see overlap
    assert by["hidden_control_mobile"]["status"] == "no_data"
    t = res["totals"]
    assert t["cases_scored"] == 3 and t["cases_no_data"] == 6
    assert "Totals:" in to_markdown("heuristic", res)
