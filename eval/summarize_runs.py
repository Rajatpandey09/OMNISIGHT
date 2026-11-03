"""Summarise repeated audit runs into one table.

Usage: python eval/summarize_runs.py [results_dir] [--out table.md]

Reads run_1.json, run_2.json ... (copies of the results made by run_eval.py) and prints a
markdown table: what each run did per case, how many runs found the bug, and the totals per
run. Reports counts, not accuracy.
"""
import argparse
import json
import re
from pathlib import Path


def load_runs(results_dir):
    files = sorted(Path(results_dir).glob("run_*.json"),
                   key=lambda p: int(re.search(r"run_(\d+)", p.name).group(1)))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def cell(row):
    if row is None:
        return "missing"
    if row["status"] != "ok":
        return row["status"]
    parts = []
    if row["tp"]:
        parts.append("found")
    if row["fp"]:
        parts.append(f"{row['fp']} false flag")
    if row["fn"]:
        parts.append("missed")
    if row["inconclusive"]:
        parts.append("inconclusive")
    return ", ".join(parts) or "clean"


def build_table(runs):
    n = len(runs)
    cases = []
    for run in runs:
        for r in run["rows"]:
            if r["case_id"] not in cases:
                cases.append(r["case_id"])
    head = ["case"] + [f"run {i}" for i in range(1, n + 1)] + ["found in"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for cid in cases:
        rows = [next((x for x in run["rows"] if x["case_id"] == cid), None) for run in runs]
        cells = [cell(r) for r in rows]
        has_defect = any(r and (r["tp"] or r["fn"] or r["inconclusive"]) for r in rows)
        found = sum(1 for r in rows if r and r["tp"])
        last = f"{found}/{n}" if has_defect else "n/a (no defect expected)"
        lines.append("| " + " | ".join([cid] + cells + [last]) + " |")
    lines.append("")
    for i, run in enumerate(runs, 1):
        t = run["totals"]
        lines.append(f"Run {i}: TP={t['tp']} FP={t['fp']} FN={t['fn']} "
                     f"inconclusive={t['inconclusive']} failed={t['cases_failed']}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", nargs="?", default="eval/results")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    runs = load_runs(args.results_dir)
    if not runs:
        raise SystemExit(f"no run_*.json files found in {args.results_dir}")
    table = build_table(runs)
    print(table)
    if args.out:
        Path(args.out).write_text(table, encoding="utf-8")
        print(f"saved {args.out}")


if __name__ == "__main__":
    main()
