"""Crop each detected finding to its problem area, and optionally ask the model for a close-up check.

Usage: python run_crop.py path/to/scan_result.json [--analysis analysis.json] [--out crops]
           [--check] [--provider ollama] [--timeout 120]

Reads analysis.json (from run_analysis.py) and the scan's screenshots. For each finding marked
"detected" that has a bbox, the cropped image is saved under --out and crops.json is written.
With --check the model also looks at each crop and says confirmed, not_confirmed or inconclusive.
Without --check no model is called. Nothing the model writes is executed.
"""
import argparse
import json
import re
from pathlib import Path

from vision.crop import combine_second_look, crop_region, second_look


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan_json")
    ap.add_argument("--analysis", default=None, help="default: analysis.json next to the scan file")
    ap.add_argument("--out", default="crops")
    ap.add_argument("--check", action="store_true", help="ask the model about each crop")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    scan_file = Path(args.scan_json)
    scan = json.loads(scan_file.read_text(encoding="utf-8"))
    analysis_file = Path(args.analysis) if args.analysis else scan_file.with_name("analysis.json")
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    items = {r["viewport"]: r for r in scan["results"]}
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    provider = None
    if args.check:
        from vision.factory import get_provider
        provider = get_provider(args.provider)

    records = []
    for a in analysis["analyses"]:
        item = items.get(a["viewport"])
        if a["outcome"] != "ok" or item is None:
            continue
        shot = scan_file.parent / item["screenshot"]
        if not shot.is_file():
            print(f"{a['viewport']:8} skipped: screenshot not found ({item['screenshot']})")
            continue
        image = shot.read_bytes()
        for i, f in enumerate(a["findings"]):
            if f.get("status") != "detected":
                continue
            crop = crop_region(image, f.get("bbox"))
            record = {"viewport": a["viewport"], "issue_type": f.get("issue_type"),
                      "element": f.get("element"), "crop": crop.to_dict(), "zoom": None,
                      "label": "single_look"}
            if crop.png is not None:
                name = re.sub(r"[^a-z_]", "", str(f.get("issue_type", "")).lower()) or "finding"
                path = out_dir / f"{a['viewport']}_{i}_{name}.png"
                path.write_bytes(crop.png)
                record["crop_file"] = str(path)
            if provider is not None:
                z = second_look(provider, f, image, scan_id=analysis["scan_id"],
                                viewport=a["viewport"], timeout=args.timeout)
                record["zoom"] = z.to_dict()
                record["label"] = combine_second_look(f.get("status"), z.verdict if z.outcome == "ok" else None)
            print(f"{a['viewport']:8} {str(f.get('issue_type')):20} crop={crop.reason:16}"
                  + (f" zoom={record['zoom']['verdict']} label={record['label']}" if record["zoom"] else ""))
            records.append(record)

    out_file = out_dir / "crops.json"
    out_file.write_text(json.dumps({"scan_id": analysis["scan_id"], "records": records}, indent=2),
                        encoding="utf-8")
    print(f"saved {out_file}")


if __name__ == "__main__":
    main()
