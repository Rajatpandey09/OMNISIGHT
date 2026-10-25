import json
from vision.pipeline import analyze_scan
from vision.providers.mock import MockProvider
from vision.factory import get_provider

GOOD = json.dumps({"findings": [{
    "issue_type": "horizontal_overflow", "severity": "high",
    "evidence": "scroll_width 1200 > 390", "impact": "sideways scroll",
    "confidence": 0.9}]})


def make_scan(tmp_path, with_mobile_image=True):
    (tmp_path / "desktop.png").write_bytes(b"fake")
    if with_mobile_image:
        (tmp_path / "mobile.png").write_bytes(b"fake")
    scan = {"scan_id": "s1", "results": [
        {"viewport": "desktop", "width": 1366, "height": 768,
         "screenshot": "desktop.png", "metrics": {"scroll_width": 1366}},
        {"viewport": "mobile", "width": 390, "height": 844,
         "screenshot": "mobile.png", "metrics": {"scroll_width": 1200}}]}
    p = tmp_path / "scan_result.json"
    p.write_text(json.dumps(scan))
    return p


def test_pipeline_writes_analysis(tmp_path):
    p = make_scan(tmp_path)
    res = analyze_scan(MockProvider(reply=GOOD), p)
    assert [a["viewport"] for a in res["analyses"]] == ["desktop", "mobile"]
    assert all(a["outcome"] == "ok" for a in res["analyses"])
    assert (tmp_path / "analysis.json").is_file()


def test_missing_screenshot_is_input_error_not_crash(tmp_path):
    p = make_scan(tmp_path, with_mobile_image=False)
    res = analyze_scan(MockProvider(reply=GOOD), p)
    assert res["analyses"][1]["outcome"] == "input_error"
    assert res["analyses"][0]["outcome"] == "ok"


def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("VISION_PROVIDER", raising=False)
    assert get_provider().name == "mock"
