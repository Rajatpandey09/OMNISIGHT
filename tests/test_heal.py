import io
import json

from PIL import Image

from vision.heal import Rescan, build_css, heal
from vision.providers.base import ProviderError, VisionProvider

FINDING = {"issue_type": "horizontal_overflow", "element": "pricing table",
           "severity": "high", "evidence": "table runs past the right edge"}
PATCH = {"selector": ".table", "css_before": None, "css_after": "max-width: 100%",
         "rationale": "Limit the table to the screen width.", "confidence": 0.8}
PATCH2 = {"selector": ".table", "css_before": None, "css_after": "overflow-x: auto",
          "rationale": "Let the table scroll inside its box.", "confidence": 0.7}


def patch_reply(*patches, cannot=False):
    return json.dumps({"patches": list(patches), "cannot_determine": cannot})


def verdict_reply(v, problems="none"):
    return json.dumps({"verdict": v, "confidence": 0.9, "evidence": f"model says {v}",
                       "new_problems": problems})


class Router(VisionProvider):
    """Answers patch requests and verify requests from two separate queues."""
    name = "router"

    def __init__(self, patch_replies, verify_replies):
        self.patch, self.verify = list(patch_replies), list(verify_replies)
        self.patch_calls = self.verify_calls = 0
        self.patch_prompts = []

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        if "front-end reviewer" in system_prompt:
            self.patch_calls += 1
            self.patch_prompts.append(user_prompt)
            r = self.patch[min(self.patch_calls - 1, len(self.patch) - 1)]
        else:
            self.verify_calls += 1
            r = self.verify[min(self.verify_calls - 1, len(self.verify) - 1)]
        if isinstance(r, Exception):
            raise r
        return r


def png():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


def make_rescan(*metrics):
    calls = []

    def fn(css):
        calls.append(css)
        return Rescan(png(), metrics[min(len(calls) - 1, len(metrics) - 1)])
    fn.calls = calls
    return fn


def run(provider, rescan, **kw):
    kw.setdefault("source_file", "index.html")
    return heal(provider, FINDING, png(), scan_id="s1", viewport="mobile", width=390,
                height=844, apply_and_rescan=rescan, **kw)


def test_css_is_built_from_the_validated_patches():
    from vision.patches import PatchSuggestion
    ps = [PatchSuggestion("s", "m", "x", "e", None, ".a", None, "color: red", "r", 0.5),
          PatchSuggestion("s", "m", "x", "e", None, "p > b", None, "margin: 0; padding: 0", "r", 0.5)]
    assert build_css(ps) == ".a { color: red }\np > b { margin: 0; padding: 0 }"


def test_fixed_on_the_first_attempt_when_model_and_metrics_agree():
    rescan = make_rescan(True)
    res = run(Router([patch_reply(PATCH)], [verdict_reply("fixed")]), rescan)
    assert res.status == "fixed" and len(res.attempts) == 1
    assert res.final_css == ".table { max-width: 100% }" and rescan.calls == [res.final_css]
    assert res.source_file == "index.html"


def test_a_failed_attempt_is_retried_with_feedback():
    prov = Router([patch_reply(PATCH), patch_reply(PATCH2)],
                  [verdict_reply("not_fixed"), verdict_reply("fixed")])
    rescan = make_rescan(False, True)
    res = run(prov, rescan)
    assert res.status == "fixed" and len(res.attempts) == 2
    assert res.attempts[0].verdict == "not_fixed" and res.final_css == ".table { overflow-x: auto }"
    assert "did NOT fix it" not in prov.patch_prompts[0]
    assert "max-width: 100%" in prov.patch_prompts[1] and "did NOT fix it" in prov.patch_prompts[1]
    assert len(rescan.calls) == 2


def test_it_gives_up_after_the_attempt_limit():
    prov = Router([patch_reply(PATCH)], [verdict_reply("not_fixed")])
    res = run(prov, make_rescan(False), max_attempts=3)
    assert res.status == "not_fixed" and len(res.attempts) == 3 and prov.patch_calls == 3
    assert res.final_css is None


def test_the_attempt_limit_is_capped():
    prov = Router([patch_reply(PATCH)], [verdict_reply("not_fixed")])
    assert len(run(prov, make_rescan(False), max_attempts=99).attempts) == 5
    prov = Router([patch_reply(PATCH)], [verdict_reply("not_fixed")])
    assert len(run(prov, make_rescan(False), max_attempts=0).attempts) == 1
    prov = Router([patch_reply(PATCH)], [verdict_reply("not_fixed")])
    assert len(run(prov, make_rescan(False), max_attempts="x").attempts) == 1


def test_a_model_only_fixed_stays_inconclusive_and_stops():
    prov = Router([patch_reply(PATCH)], [verdict_reply("fixed")])
    res = run(prov, make_rescan(None))
    assert res.status == "inconclusive" and len(res.attempts) == 1 and prov.patch_calls == 1
    assert "metrics" in res.message


def test_disagreement_between_model_and_metrics_is_inconclusive():
    res = run(Router([patch_reply(PATCH)], [verdict_reply("fixed")]), make_rescan(False))
    assert res.status == "inconclusive"


def test_a_new_problem_blocks_fixed():
    res = run(Router([patch_reply(PATCH)], [verdict_reply("fixed", "button now overlaps")]),
              make_rescan(True))
    assert res.status == "inconclusive" and res.attempts[0].new_problems == "button now overlaps"


def test_no_patch_means_nothing_is_applied():
    rescan = make_rescan(True)
    res = run(Router([patch_reply(cannot=True)], [verdict_reply("fixed")]), rescan)
    assert res.status == "no_patch" and rescan.calls == []


def test_only_unsafe_patches_means_nothing_is_applied():
    bad = dict(PATCH, css_after="background: url(http://evil.example/x.png)")
    rescan = make_rescan(True)
    res = run(Router([patch_reply(bad)], [verdict_reply("fixed")]), rescan)
    assert res.status == "no_patch" and rescan.calls == []


def test_a_failing_rescan_is_an_error_not_a_crash():
    def boom(css):
        raise RuntimeError("browser crashed")
    res = run(Router([patch_reply(PATCH)], [verdict_reply("fixed")]), boom)
    assert res.status == "error" and "browser crashed" in res.message and res.attempts == []

    def wrong(css):
        return "not a Rescan"
    assert run(Router([patch_reply(PATCH)], [verdict_reply("fixed")]), wrong).status == "error"


def test_a_failing_patch_step_is_an_error():
    rescan = make_rescan(True)
    res = run(Router([ProviderError("down")], [verdict_reply("fixed")]), rescan)
    assert res.status == "error" and "patch step failed" in res.message and rescan.calls == []


def test_an_unreadable_verify_reply_is_inconclusive_unless_metrics_say_not_fixed():
    res = run(Router([patch_reply(PATCH)], ["not json"]), make_rescan(None))
    assert res.status == "inconclusive"
    res = run(Router([patch_reply(PATCH)], ["not json"]), make_rescan(False), max_attempts=1)
    assert res.status == "not_fixed"


def test_a_bad_source_file_stops_before_the_model_is_called():
    prov = Router([patch_reply(PATCH)], [verdict_reply("fixed")])
    res = run(prov, make_rescan(True), source_file="../secret.css")
    assert res.status == "error" and prov.patch_calls == 0


def test_result_serialises_to_plain_json():
    res = run(Router([patch_reply(PATCH)], [verdict_reply("fixed")]), make_rescan(True))
    data = json.loads(json.dumps(res.to_dict()))
    assert data["status"] == "fixed" and data["attempts"][0]["verdict"] == "fixed"
