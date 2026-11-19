import io
import json

from PIL import Image

from vision.patches import (VERDICTS, combine_verdicts, compose_before_after,
                            suggest_patches, verify_fix)
from vision.providers.base import ProviderError, VisionProvider

FINDING = {"issue_type": "horizontal_overflow", "element": "wide banner",
           "severity": "high", "evidence": "banner runs past the right edge"}
GOOD = {"selector": ".banner", "css_before": "width: 1200px",
        "css_after": "max-width: 100%; overflow-x: auto",
        "rationale": "The banner is wider than the screen, so limit its width.",
        "confidence": 0.9}


def reply(*patches, cannot=False):
    return json.dumps({"patches": list(patches), "cannot_determine": cannot})


class Scripted(VisionProvider):
    name = "scripted"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.prompts = []

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        self.calls += 1
        self.prompts.append(user_prompt)
        r = self.replies[min(self.calls - 1, len(self.replies) - 1)]
        if isinstance(r, Exception):
            raise r
        return r


def run(provider, finding=FINDING, **kw):
    kw.setdefault("source_file", "index.html")
    return suggest_patches(provider, finding, b"x", scan_id="s1", viewport="mobile",
                           width=390, height=844, **kw)


def png(w, h, colour="white"):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ patches
def test_valid_patch_is_kept_with_the_callers_file_path():
    res = run(Scripted(reply(GOOD)))
    assert res.outcome == "ok" and len(res.patches) == 1
    p = res.patches[0]
    assert p.file_path == "index.html" and p.selector == ".banner"
    assert p.issue_type == "horizontal_overflow" and p.scan_id == "s1"


def test_model_cannot_choose_the_file_path():
    sneaky = dict(GOOD, file_path="../../etc/passwd")
    res = run(Scripted(reply(sneaky)), source_file="pages/home.css")
    assert res.patches[0].file_path == "pages/home.css"


def test_unsafe_css_is_rejected_and_the_good_patch_is_kept():
    bad1 = dict(GOOD, css_after="background: url(http://evil.example/x.png)")
    bad2 = dict(GOOD, css_after="color: red; } body { display: none")
    bad3 = dict(GOOD, css_after="<script>alert(1)</script>")
    res = run(Scripted(reply(bad1, bad2)), )
    assert res.outcome == "ok" and res.patches == [] and len(res.rejected) == 2
    res = run(Scripted(reply(bad3)))
    assert res.patches == [] and "not allowed" in res.rejected[0]["reason"]
    res = run(Scripted(reply(GOOD, bad1)))
    assert len(res.patches) == 1 and len(res.rejected) == 1


def test_unsafe_selector_is_rejected():
    for sel in (".a { color: red }", "a; b", "body</style>", "a\\62", "x /* c */"):
        res = run(Scripted(reply(dict(GOOD, selector=sel))))
        assert res.patches == [] and len(res.rejected) == 1, sel
    res = run(Scripted(reply(dict(GOOD, selector="form > button.submit[type='submit']"))))
    assert len(res.patches) == 1


def test_non_declaration_css_is_rejected():
    res = run(Scripted(reply(dict(GOOD, css_after="just some words"))))
    assert res.patches == [] and "declaration" in res.rejected[0]["reason"]


def test_bad_confidence_is_rejected():
    for c in (1.5, -0.1, "high", True, None):
        res = run(Scripted(reply(dict(GOOD, confidence=c))))
        assert res.patches == [], c


def test_bad_source_file_is_an_input_error_and_the_model_is_not_called():
    for path in ("../secret.css", "C:/x.css", "/etc/x.css", "run.exe", "a/../../b.html"):
        prov = Scripted(reply(GOOD))
        res = run(prov, source_file=path)
        assert res.outcome == "input_error" and prov.calls == 0, path


def test_no_source_file_still_gives_suggestions_without_a_target():
    res = run(Scripted(reply(GOOD)), source_file=None)
    assert res.patches[0].file_path is None


def test_malformed_reply_is_retried_once():
    prov = Scripted('{"patches": [}', reply(GOOD))
    res = run(prov)
    assert res.outcome == "ok" and prov.calls == 2 and len(res.patches) == 1


def test_gives_up_after_one_retry():
    prov = Scripted("not json")
    res = run(prov)
    assert res.outcome == "invalid_output" and prov.calls == 2


def test_wrong_shape_is_invalid_output():
    assert run(Scripted('["a", "b"]')).outcome == "invalid_output"
    assert run(Scripted('{"patches": "none"}')).outcome == "invalid_output"


def test_only_two_patches_are_kept():
    res = run(Scripted(reply(GOOD, GOOD, GOOD)))
    assert len(res.patches) == 2 and len(res.rejected) == 1


def test_cannot_determine_with_no_patches_is_a_valid_answer():
    res = run(Scripted(reply(cannot=True)))
    assert res.outcome == "ok" and res.patches == [] and res.cannot_determine is True


def test_provider_error_is_labelled_not_raised():
    res = run(Scripted(ProviderError("down")))
    assert res.outcome == "provider_error"
    assert run(Scripted(RuntimeError("boom"))).outcome == "provider_error"


def test_prompt_marks_html_untrusted_and_carries_the_problem():
    prov = Scripted(reply(GOOD))
    run(prov, html="<div class='banner'>hi</div><script>x()</script>")
    prompt = prov.prompts[0]
    assert "untrusted" in prompt and "wide banner" in prompt and "x()" not in prompt


def test_result_serialises_to_plain_json():
    res = run(Scripted(reply(GOOD)))
    assert json.loads(json.dumps(res.to_dict()))["patches"][0]["selector"] == ".banner"


# ------------------------------------------------------------- verification
def test_compose_puts_before_left_and_after_right():
    out = Image.open(io.BytesIO(compose_before_after(png(100, 200, "red"), png(300, 100, "blue"))))
    assert out.size == (100 + 24 + 300, 56 + 200)
    assert out.getpixel((50, 56 + 100)) == (255, 0, 0)
    assert out.getpixel((124 + 150, 56 + 50)) == (0, 0, 255)


def test_compose_shrinks_large_images():
    out = Image.open(io.BytesIO(compose_before_after(png(2000, 3000), png(2000, 3000))))
    assert out.width <= 2100 and out.height <= 1500


def verdict_reply(v="fixed", c=0.9, problems="none"):
    return json.dumps({"verdict": v, "confidence": c, "evidence": "table now fits",
                       "new_problems": problems})


def test_verify_fix_reads_the_models_verdict():
    res = verify_fix(Scripted(verdict_reply()), png(10, 10), png(10, 10),
                     issue_type="horizontal_overflow", element="table")
    assert res.outcome == "ok" and res.verdict == "fixed" and res.confidence == 0.9


def test_verify_fix_rejects_unknown_issue_and_unreadable_images():
    prov = Scripted(verdict_reply())
    assert verify_fix(prov, png(5, 5), png(5, 5), issue_type="nope").outcome == "input_error"
    assert verify_fix(prov, b"junk", png(5, 5), issue_type="other").outcome == "input_error"
    assert prov.calls == 0


def test_verify_fix_bad_verdict_is_invalid_output():
    res = verify_fix(Scripted(verdict_reply("maybe")), png(5, 5), png(5, 5), issue_type="other")
    assert res.outcome == "invalid_output"


def test_verify_fix_retries_malformed_reply_once():
    prov = Scripted("{oops", verdict_reply("not_fixed"))
    res = verify_fix(prov, png(5, 5), png(5, 5), issue_type="other")
    assert res.outcome == "ok" and res.verdict == "not_fixed" and prov.calls == 2


def test_combine_verdicts_never_passes_on_the_model_alone():
    table = [
        ("fixed", True, "fixed"),
        ("fixed", None, "inconclusive"),
        ("fixed", False, "inconclusive"),
        ("not_fixed", True, "inconclusive"),
        ("not_fixed", False, "not_fixed"),
        ("not_fixed", None, "not_fixed"),
        ("inconclusive", True, "inconclusive"),
        ("inconclusive", False, "not_fixed"),
        ("inconclusive", None, "inconclusive"),
    ]
    for model, metrics, expected in table:
        assert combine_verdicts(model, metrics)[0] == expected, (model, metrics)
    assert set(v for _, _, v in table) <= set(VERDICTS)


def test_a_new_problem_blocks_fixed():
    assert combine_verdicts("fixed", True, "button now overlaps the title")[0] == "inconclusive"
    assert combine_verdicts("fixed", True, "none")[0] == "fixed"
