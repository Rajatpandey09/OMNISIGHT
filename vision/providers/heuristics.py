"""Offline, no-key provider that reads the METRICS only. It is NOT a vision model.

It never looks at the screenshot, so it cannot judge overlapping text or contrast.
Its results are labelled provider="heuristic" so nobody mistakes them for AI output.
Useful for demos and for testing the whole pipeline without any key.

ASSUMED metrics shape (confirm with Member 2): scroll_width (int);
buttons: list of {"selector"|"text", "x", "width"}; hidden_controls: list of names.
"""
import json
import re
from .base import VisionProvider


class HeuristicProvider(VisionProvider):
    name = "heuristic"

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        vp = re.search(r"Viewport: \w+ \((\d+)x(\d+)\)", user_prompt)
        mt = re.search(r"Metrics: (.*)", user_prompt)
        width = int(vp.group(1)) if vp else 0
        try:
            metrics = json.loads(mt.group(1)) if mt else {}
        except json.JSONDecodeError:
            metrics = {}
        if not metrics or not width:
            return json.dumps({"findings": [], "cannot_determine": True,
                               "notes": "heuristic: no usable metrics"})
        findings = []
        sw = metrics.get("scroll_width")
        if isinstance(sw, (int, float)) and sw > width + 1:
            findings.append({
                "issue_type": "horizontal_overflow", "element": "page",
                "severity": "high",
                "evidence": f"scroll_width {sw} exceeds viewport width {width}",
                "impact": "page scrolls sideways", "confidence": 0.95,
                "summary": "The page is wider than the screen.",
                "suggested_fix": "Constrain the widest element with max-width: 100%."})
        for b in metrics.get("buttons") or []:
            if isinstance(b, dict) and "x" in b and "width" in b:
                if b["x"] < 0 or b["x"] + b["width"] > width:
                    label = b.get("selector") or b.get("text") or "button"
                    findings.append({
                        "issue_type": "offscreen_button", "element": str(label),
                        "severity": "medium",
                        "evidence": f"button spans x={b['x']}..{b['x'] + b['width']} "
                                    f"but viewport width is {width}",
                        "impact": "control may be unreachable", "confidence": 0.9,
                        "summary": f"The {label} is partly off the screen."})
        for h in metrics.get("hidden_controls") or []:
            findings.append({
                "issue_type": "hidden_control", "element": str(h), "severity": "medium",
                "evidence": f"{h} reported hidden in metrics",
                "impact": "control not usable", "confidence": 0.8,
                "summary": f"The {h} is hidden."})
        return json.dumps({"findings": findings, "cannot_determine": False,
                           "notes": "heuristic: metrics only; cannot assess overlap or contrast"})
