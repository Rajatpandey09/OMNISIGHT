import json
from pathlib import Path
from run_eval import evaluate
from vision.pipeline import analyze_scan
from vision.prompts import SYSTEM_PROMPT, build_user_prompt, clean_html, MAX_HTML_CHARS
from vision.providers.base import VisionProvider
from vision.providers.heuristic import HeuristicProvider

CASES = Path(__file__).parent.parent / "eval" / "labelled_cases.json"
HTML = "<form><script>alert('x')</script><!-- note --><button>Go</button></form>"


class Capture(VisionProvider):
    name = "capture"

    def __init__(self):
        self.prompts = []

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        self.prompts.append(user_prompt)
        return json.dumps({"findings": [], "cannot_determine": True})


def make_scan(tmp_path):
    (tmp_path / "m.png").write_bytes(b"fake")
    scan = {"scan_id": "s1", "results": [{
        "viewport": "mobile", "width": 390, "height": 844, "screenshot": "m.png",
        "metrics": {"scroll_width": 1200}, "relevant_html": HTML}]}
    p = tmp_path / "scan.json"
    p.write_text(json.dumps(scan))
    return p


def test_with_metrics_sends_metrics_and_cleaned_html(tmp_path):
    cap = Capture()
    res = analyze_scan(cap, make_scan(tmp_path))
    prompt = cap.prompts[0]
    assert res["mode"] == "with_metrics"
    assert "scroll_width" in prompt and "<button>Go</button>" in prompt
    assert "alert(" not in prompt and "note" not in prompt


def test_screenshot_only_sends_neither_metrics_nor_html(tmp_path):
    cap = Capture()
    res = analyze_scan(cap, make_scan(tmp_path), screenshot_only=True)
    prompt = cap.prompts[0]
    assert res["mode"] == "screenshot_only"
    assert "scroll_width" not in prompt and "button" not in prompt
    assert "screenshot only" in prompt


def test_clean_html_truncates():
    assert len(clean_html("<p>x</p>" * 5000)) <= MAX_HTML_CHARS


def test_prompt_treats_page_text_as_untrusted():
    assert "not instructions" in SYSTEM_PROMPT
    assert "untrusted" in build_user_prompt("mobile", 390, 844, {}, "<p>hi</p>")


def test_eval_screenshot_only_makes_heuristic_inconclusive(tmp_path):
    d = tmp_path / "overflow_mobile"
    d.mkdir()
    (d / "screenshot.png").write_bytes(b"fake")
    (d / "metrics.json").write_text(json.dumps({"scroll_width": 1200}))
    normal = evaluate(HeuristicProvider(), CASES, tmp_path)
    blind = evaluate(HeuristicProvider(), CASES, tmp_path, screenshot_only=True)
    n = [r for r in normal["rows"] if r["case_id"] == "overflow_mobile"][0]
    b = [r for r in blind["rows"] if r["case_id"] == "overflow_mobile"][0]
    assert n["tp"] == 1
    assert b["tp"] == 0 and b["inconclusive"] == 1
    assert blind["mode"] == "screenshot_only"
