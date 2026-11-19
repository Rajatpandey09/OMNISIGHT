import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "summarize_runs", Path(__file__).resolve().parent.parent / "eval" / "summarize_runs.py")
summarize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(summarize)


def row(case, status="ok", tp=0, fp=0, fn=0, inc=0):
    return {"case_id": case, "viewport": "mobile", "status": status, "tp": tp, "fp": fp,
            "fn": fn, "inconclusive": inc, "seconds": 1.0, "provider": "p", "error": None}


def run(rows):
    keys = ("tp", "fp", "fn", "inconclusive")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    totals["cases_failed"] = sum(1 for r in rows if r["status"] not in ("ok", "no_data"))
    return {"mode": "screenshot_only", "rows": rows, "totals": totals}


def test_cells_describe_each_outcome():
    assert summarize.cell(row("a", tp=1)) == "found"
    assert summarize.cell(row("a", fn=1)) == "missed"
    assert summarize.cell(row("a", fp=2)) == "2 false flag"
    assert summarize.cell(row("a", inc=1)) == "inconclusive"
    assert summarize.cell(row("a")) == "clean"
    assert summarize.cell(row("a", status="invalid_output")) == "invalid_output"
    assert summarize.cell(None) == "missing"


def test_table_counts_the_runs_that_found_each_bug():
    runs = [run([row("overflow", tp=1), row("hidden", fn=1), row("clean")]),
            run([row("overflow", status="invalid_output"), row("hidden", fn=1), row("clean")]),
            run([row("overflow", tp=1), row("hidden", fn=1), row("clean")])]
    text = summarize.build_table(runs)
    assert "| overflow | found | invalid_output | found | 2/3 |" in text
    assert "| hidden | missed | missed | missed | 0/3 |" in text
    assert "| clean | clean | clean | clean | n/a (no defect expected) |" in text
    assert "Run 1: TP=1 FP=0 FN=1 inconclusive=0 failed=0" in text
    assert "Run 2: TP=0 FP=0 FN=1 inconclusive=0 failed=1" in text


def test_load_runs_reads_files_in_numeric_order(tmp_path):
    import json
    for n in (10, 2, 1):
        (tmp_path / f"run_{n}.json").write_text(json.dumps(run([row(f"case{n}")])))
    names = [r["rows"][0]["case_id"] for r in summarize.load_runs(tmp_path)]
    assert names == ["case1", "case2", "case10"]
