import json
from vision.analyzer import analyze
from vision.providers.mock import MockProvider

GOOD = json.dumps({"findings": [{
    "issue_type": "horizontal_overflow", "element": ".hero-banner",
    "severity": "high", "evidence": "scroll_width 1200 > viewport 390",
    "impact": "page scrolls sideways", "confidence": 0.9,
    "suggested_fix": "max-width: 100%"}]})


def run(p):
    return analyze(p, "scan-1", "mobile", 390, 844, b"png", {"scroll_width": 1200})


def test_valid_output():
    r = run(MockProvider(reply=GOOD))
    assert r.outcome == "ok" and r.findings[0].viewport == "mobile"
    assert r.findings[0].scan_id == "scan-1"


def test_fenced_json():
    assert run(MockProvider(reply=f"```json\n{GOOD}\n```")).outcome == "ok"


def test_invalid_json():
    assert run(MockProvider(reply="not json")).outcome == "invalid_output"


def test_schema_violation():
    bad = json.dumps({"findings": [{"issue_type": "bogus"}]})
    assert run(MockProvider(reply=bad)).outcome == "invalid_output"


def test_missing_credentials():
    assert run(MockProvider(fail_with="credentials")).outcome == "no_credentials"


def test_timeout():
    assert run(MockProvider(fail_with="timeout")).outcome == "provider_error"


def test_cannot_determine_is_not_a_crash():
    r = run(MockProvider())
    assert r.outcome == "ok" and r.cannot_determine and r.findings == []


def test_summary_and_bbox_optional_and_valid():
    ok = json.dumps({"findings": [{
        "issue_type": "offscreen_button", "severity": "medium",
        "evidence": "button cut off", "impact": "cannot tap", "confidence": 0.8,
        "summary": "The Submit button is cut off.",
        "bbox": {"x": 0.7, "y": 0.1, "width": 0.4, "height": 0.08}}]})
    r = run(MockProvider(reply=ok))
    assert r.outcome == "ok" and r.findings[0].bbox.x == 0.7
    bad = ok.replace('"x": 0.7', '"x": 7')
    assert run(MockProvider(reply=bad)).outcome == "invalid_output"
