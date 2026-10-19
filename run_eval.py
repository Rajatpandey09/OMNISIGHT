"""Score a provider on the labelled cases.

Usage: python run_eval.py --provider heuristic [--data eval/cases_data] [--out eval/results]
Data layout (made with Member 4's bug pages):
  eval/cases_data/<case_id>/screenshot.png   and optionally   metrics.json
Cases with no data folder are reported as no_data (never counted as passes).
"""
import argparse
import json
import time
from pathlib import Path
from vision.analyzer import analyze
from vision.factory import get_provider
from vision.imaging import compact


def evaluate(provider, cases_file, data_dir, timeout=60.0):
    spec = json.loads(Path(cases_file).read_text(encoding="utf-8"))
    rows = []
    for c in spec["cases"]:
        row = {"case_id": c["case_id"], "viewport": c["viewport"], "status": "ok",
               "tp": 0, "fp": 0, "fn": 0, "inconclusive": 0, "seconds": None,
               "provider": None, "error": None}
        d = Path(data_dir) / c["case_id"]
        shot = d / "screenshot.png"
        if not shot.is_file():
            row["status"] = "no_data"
            rows.append(row)
            continue
        mfile = d / "metrics.json"
        metrics = json.loads(mfile.read_text(encoding="utf-8")) if mfile.is_file() else {}
        w, h = spec["viewports"][c["viewport"]]
        t0 = time.perf_counter()
        res = analyze(provider, c["case_id"], c["viewport"], w, h,
                      compact(shot.read_bytes()), metrics, timeout)
        row["seconds"] = round(time.perf_counter() - t0, 2)
        row["provider"] = res.provider
        if res.outcome != "ok":
            row["status"], row["error"] = res.outcome, res.error
            rows.append(row)
            continue
        expected = {e["issue_type"] for e in c["expected"]}
        detected = {f.issue_type for f in res.findings if f.status == "detected"}
        unsure = {f.issue_type for f in res.findings if f.status == "inconclusive"}
        if res.cannot_determine:
            unsure |= expected
        missed = expected - detected
        inc = missed & unsure
        row["tp"] = len(expected & detected)
        row["fp"] = len(detected - expected)
        row["inconclusive"] = len(inc)
        row["fn"] = len(missed - inc)
        rows.append(row)
    keys = ("tp", "fp", "fn", "inconclusive")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    totals["cases_scored"] = sum(1 for r in rows if r["status"] == "ok")
    totals["cases_no_data"] = sum(1 for r in rows if r["status"] == "no_data")
    totals["cases_failed"] = sum(1 for r in rows if r["status"] not in ("ok", "no_data"))
    return {"rows": rows, "totals": totals}


def to_markdown(provider_name, result):
    lines = [f"# Evaluation: {provider_name}", "",
             "| case | viewport | status | TP | FP | FN | inconclusive | seconds |",
             "|---|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['case_id']} | {r['viewport']} | {r['status']} | {r['tp']} | "
                     f"{r['fp']} | {r['fn']} | {r['inconclusive']} | {r['seconds']} |")
    t = result["totals"]
    lines += ["", f"Totals: TP={t['tp']} FP={t['fp']} FN={t['fn']} "
              f"inconclusive={t['inconclusive']}; scored={t['cases_scored']}, "
              f"no data={t['cases_no_data']}, failed={t['cases_failed']}"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None)
    ap.add_argument("--cases", default="eval/labelled_cases.json")
    ap.add_argument("--data", default="eval/cases_data")
    ap.add_argument("--out", default="eval/results")
    a = ap.parse_args()
    provider = get_provider(a.provider)
    result = evaluate(provider, a.cases, a.data)
    label = (a.provider or "default").replace(",", "+")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"results_{label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    md = to_markdown(label, result)
    (out / f"results_{label}.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
