import json
from vision.analyzer import analyze
from vision.providers.base import VisionProvider


class Flaky(VisionProvider):
    name = "flaky"

    def __init__(self):
        self.calls = 0

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        self.calls += 1
        if self.calls == 1:
            return '{"findings": [}'
        return json.dumps({"findings": [], "cannot_determine": True})


class AlwaysBad(Flaky):
    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        self.calls += 1
        return "not json"


def test_retry_recovers_from_one_malformed_reply():
    p = Flaky()
    res = analyze(p, "s", "mobile", 390, 844, b"x")
    assert res.outcome == "ok" and p.calls == 2


def test_gives_up_after_one_retry():
    p = AlwaysBad()
    res = analyze(p, "s", "mobile", 390, 844, b"x")
    assert res.outcome == "invalid_output" and p.calls == 2