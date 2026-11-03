"""Show what cropping saves: pixels and bytes sent to the model, and optionally seconds.

Usage: python run_savings.py path/to/scan_result.json [--analysis analysis.json]
           [--time] [--provider ollama] [--timeout 120]

For each detected finding that has a bbox, compares the full screenshot (as the pipeline sends it)
with the crop around the problem. Pixels and bytes need no model. With --time the model is called
once on the full image and once on the crop, with the same question, and the seconds are compared.
One timing per case is a sample, not a benchmark: repeat it before quoting a number.
"""
import argparse
import json
import time
from pathlib import Path

from vision.chunk import savings
from vision.crop import ZOOM_SYSTEM_PROMPT, build_zoom_prompt, crop_region
from vision.imaging import compact


def timed(provider, image, finding, viewport, timeout):
    t0 = time.perf_counter()
    try:
        provider.analyze(image, ZOOM_SYSTEM_PROMPT, build_zoom_prompt(finding, viewport), timeout)
    except Exception as e:  # report and carry on
        return None, f"{type(e).__name__}"
    return round(time.perf_counter() - t0, 2), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan_json")
    ap.add_argument("--analysis", default=None)
    ap.add_argument("--time", action="store_true", help="also time one model call each")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    scan_file = Path(args.scan_json)
    scan = json.loads(scan_file.read_text(encoding="utf-8"))
    analysis_file = Path(args.analysis) if args.analysis else scan_file.with_name("analysis.json")
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    items = {r["viewport"]: r for r in scan["results"]}
    provider = None
    if args.time:
        from vision.factory import get_provider
        provider = get_provider(args.provider)

    rows = []
    for a in analysis["analyses"]:
        item = items.get(a["viewport"])
        if a["outcome"] != "ok" or item is None:
            continue
        shot = scan_file.parent / item["screenshot"]
        if not shot.is_file():
            continue
        original = shot.read_bytes()
        full = compact(original)  # what the pipeline sends today
        for f in a["findings"]:
            if f.get("status") != "detected":
                continue
            crop = crop_region(original, f.get("bbox"))
            if crop.png is None:
                print(f"{a['viewport']:8} {str(f.get('issue_type')):20} no crop ({crop.reason})")
                continue
            s = savings(full, crop.png)
            row = {"viewport": a["viewport"], "issue_type": f.get("issue_type"), **(s or {})}
            if provider is not None:
                row["seconds_full"], _ = timed(provider, full, f, a["viewport"], args.timeout)
                row["seconds_crop"], _ = timed(provider, crop.png, f, a["viewport"], args.timeout)
            rows.append(row)
            line = (f"{a['viewport']:8} {str(f.get('issue_type')):20} pixels {s['pixels_full']:>9} -> "
                    f"{s['pixels_crop']:>9} ({s['pixels_saved_pct']}% fewer)  bytes "
                    f"{s['bytes_full']} -> {s['bytes_crop']} ({s['bytes_saved_pct']}% fewer)")
            if provider is not None:
                line += f"  seconds {row.get('seconds_full')} -> {row.get('seconds_crop')}"
            print(line)

    out = scan_file.with_name("savings.json")
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
