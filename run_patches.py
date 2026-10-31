"""Suggest CSS patches for the findings marked "detected".

Usage: python run_patches.py path/to/scan_result.json [--analysis analysis.json]
           [--source-file page.html] [--provider ollama] [--timeout 120] [--out patches.json]

Reads the scan (screenshots) and the analysis.json made by run_analysis.py.
Suggestions are data only: nothing is applied and nothing the model writes is executed.
The target file comes from the scan item's "source_file" or --source-file, never from the model.
"""
import argparse
import json
from pathlib import Path

from vision.factory import get_provider
from vision.imaging import compact
from vision.patches import suggest_patches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan_json")
    ap.add_argument("--analysis", default=None, help="default: analysis.json next to the scan file")
    ap.add_argument("--source-file", default=None, help="page file the patches would target, e.g. index.html")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    scan_file = Path(args.scan_json)
    scan = json.loads(scan_file.read_text(encoding="utf-8"))
    analysis_file = Path(args.analysis) if args.analysis else scan_file.with_name("analysis.json")
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    items = {r["viewport"]: r for r in scan["results"]}
    provider = get_provider(args.provider)

    results = []
    for a in analysis["analyses"]:
        item = items.get(a["viewport"])
        if a["outcome"] != "ok" or item is None:
            continue
        shot = scan_file.parent / item["screenshot"]
        if not shot.is_file():
            print(f"{a['viewport']:8} skipped: screenshot not found ({item['screenshot']})")
            continue
        image = compact(shot.read_bytes())
        source = item.get("source_file") or args.source_file
        for f in a["findings"]:
            if f.get("status") != "detected":
                continue
            res = suggest_patches(provider, f, image, scan_id=analysis["scan_id"],
                                  viewport=a["viewport"], width=int(item["width"]),
                                  height=int(item["height"]), source_file=source,
                                  html=item.get("relevant_html"), timeout=args.timeout)
            results.append(res.to_dict())
            print(f"{a['viewport']:8} {f['issue_type']:20} outcome={res.outcome:15} "
                  f"patches={len(res.patches)} rejected={len(res.rejected)}"
                  + (f" error={res.error}" if res.error else ""))
            for p in res.patches:
                print(f"           {p.selector} {{ {p.css_after} }}  ({p.confidence:.2f})  {p.rationale}")

    out = Path(args.out) if args.out else scan_file.with_name("patches.json")
    out.write_text(json.dumps({"scan_id": analysis["scan_id"], "results": results}, indent=2),
                   encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
