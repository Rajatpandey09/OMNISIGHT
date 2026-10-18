"""Screenshot-to-JSON pipeline.

ASSUMED input contract from Member 2 (confirm before the Week 2 freeze):
{
  "scan_id": "scan-001",
  "results": [
    {"viewport": "desktop", "width": 1366, "height": 768,
     "screenshot": "desktop.png",          # path relative to this JSON file
     "metrics": {"scroll_width": 1366, "scroll_height": 900,
                 "buttons": [...], "hidden_controls": [...]}},
    {"viewport": "mobile", ...}
  ]
}
"""
import json
from pathlib import Path
from .analyzer import analyze
from .imaging import compact
from .schema import AnalysisResult, Viewport
from typing import get_args

VALID_VIEWPORTS = get_args(Viewport)


def analyze_scan(provider, scan_json_path, out_path=None, timeout: float = 30.0) -> dict:
    scan_file = Path(scan_json_path)
    scan = json.loads(scan_file.read_text(encoding="utf-8"))
    scan_id = str(scan["scan_id"])
    analyses = []
    for item in scan["results"]:
        viewport = item["viewport"]
        if viewport not in VALID_VIEWPORTS:
            raise ValueError(f"unknown viewport {viewport!r} in scan {scan_id}")
        shot = scan_file.parent / item["screenshot"]
        if not shot.is_file():
            analyses.append(AnalysisResult(
                scan_id=scan_id, viewport=viewport, provider=provider.name,
                outcome="input_error", error=f"screenshot not found: {item['screenshot']}"))
            continue
        image = compact(shot.read_bytes())
        analyses.append(analyze(provider, scan_id, viewport, int(item["width"]),
                                int(item["height"]), image, item.get("metrics") or {},
                                timeout))
    result = {"scan_id": scan_id, "analyses": [a.model_dump() for a in analyses]}
    out = Path(out_path) if out_path else scan_file.with_name("analysis.json")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
