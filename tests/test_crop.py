import io
import json

from PIL import Image, ImageDraw

from vision.crop import (bbox_to_pixels, box_from_page_pixels, choose_bbox,
                         combine_second_look, crop_region, second_look, valid_bbox)
from vision.providers.base import ProviderError, VisionProvider

FINDING = {"issue_type": "horizontal_overflow", "element": "pricing table",
           "evidence": "table runs past the right edge",
           "bbox": {"x": 0.30, "y": 0.40, "width": 0.20, "height": 0.20}}


def png(w=1000, h=2000, red_box=None):
    img = Image.new("RGB", (w, h), "white")
    if red_box:
        ImageDraw.Draw(img).rectangle(red_box, fill=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Scripted(VisionProvider):
    name = "scripted"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.prompts = []
        self.images = []

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        self.calls += 1
        self.prompts.append(user_prompt)
        self.images.append(image_png)
        r = self.replies[min(self.calls - 1, len(self.replies) - 1)]
        if isinstance(r, Exception):
            raise r
        return r


def verdict(v="confirmed", c=0.9):
    return json.dumps({"verdict": v, "confidence": c, "evidence": "table is cut off"})


# ------------------------------------------------------------------ regions
def test_valid_bbox_accepts_fractions_and_rejects_the_rest():
    assert valid_bbox({"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4})
    for bad in (None, "x", {}, {"x": 0.1}, {"x": -0.1, "y": 0, "width": 0.2, "height": 0.2},
                {"x": 1.0, "y": 0, "width": 0.2, "height": 0.2},
                {"x": 0.1, "y": 0.1, "width": 0, "height": 0.2},
                {"x": "0.1", "y": 0.1, "width": 0.2, "height": 0.2},
                {"x": True, "y": 0.1, "width": 0.2, "height": 0.2}):
        assert not valid_bbox(bad), bad


def test_bbox_to_pixels_adds_a_margin_and_stays_inside_the_image():
    left, top, right, bottom = bbox_to_pixels(FINDING["bbox"], (1000, 2000), margin=0.04)
    assert (left, top, right, bottom) == (260, 720, 540, 1280)
    edge = bbox_to_pixels({"x": 0.0, "y": 0.0, "width": 0.3, "height": 0.1}, (1000, 2000))
    assert edge[0] == 0 and edge[1] == 0


def test_a_tiny_region_is_widened_to_the_minimum_size():
    box = bbox_to_pixels({"x": 0.5, "y": 0.5, "width": 0.01, "height": 0.005}, (1000, 2000), margin=0)
    assert box[2] - box[0] >= 200 and box[3] - box[1] >= 200
    corner = bbox_to_pixels({"x": 0.0, "y": 0.0, "width": 0.01, "height": 0.005}, (1000, 2000), margin=0)
    assert corner[0] == 0 and corner[1] == 0 and corner[2] >= 200


def test_a_region_covering_nearly_the_whole_image_is_not_cropped():
    assert bbox_to_pixels({"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.95}, (1000, 2000)) is None


def test_scanner_pixels_become_fractions_of_the_screenshot():
    # 390 px wide viewport, screenshot drawn at 2x: 780 x 1688
    got = box_from_page_pixels({"x": 20, "y": 100, "width": 100, "height": 50}, 390, (780, 1688))
    assert abs(got["x"] - 40 / 780) < 1e-9 and abs(got["y"] - 200 / 1688) < 1e-9
    assert abs(got["width"] - 200 / 780) < 1e-9 and abs(got["height"] - 100 / 1688) < 1e-9
    assert box_from_page_pixels({"x": 1}, 390, (780, 1688)) is None
    assert box_from_page_pixels({"x": 1, "y": 1, "width": 0, "height": 5}, 390, (780, 1688)) is None
    assert box_from_page_pixels({"x": 1, "y": 1, "width": 5, "height": 5}, 0, (780, 1688)) is None


def test_a_measured_box_beats_the_models_estimate():
    measured = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
    assert choose_bbox(FINDING["bbox"], measured) == measured
    assert choose_bbox(FINDING["bbox"], None) == FINDING["bbox"]
    assert choose_bbox(None, {"x": 5}) is None


# --------------------------------------------------------------------- crops
def test_crop_region_cuts_the_right_area():
    image = png(1000, 2000, red_box=(300, 800, 500, 1200))
    crop = crop_region(image, FINDING["bbox"], margin=0)
    assert crop.reason == "ok" and crop.box == (300, 800, 500, 1200)
    out = Image.open(io.BytesIO(crop.png))
    assert out.getpixel((out.width // 2, out.height // 2)) == (255, 0, 0)


def test_a_small_crop_is_enlarged_so_text_stays_readable():
    crop = crop_region(png(1000, 2000), {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.1}, margin=0)
    out = Image.open(io.BytesIO(crop.png))
    assert max(out.size) >= 600


def test_crop_problems_come_back_as_reasons_not_errors():
    assert crop_region(png(), None).reason == "no_bbox"
    assert crop_region(png(), {"x": 2}).reason == "no_bbox"
    assert crop_region(b"not an image", FINDING["bbox"]).reason == "unreadable_image"
    whole = crop_region(png(), {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0})
    assert whole.reason == "whole_image" and whole.png is None


# ---------------------------------------------------------------- second look
def test_second_look_sends_the_crop_not_the_full_image():
    prov = Scripted(verdict())
    res = second_look(prov, FINDING, png(), scan_id="s1", viewport="mobile")
    assert res.outcome == "ok" and res.verdict == "confirmed" and res.confidence == 0.9
    assert res.box is not None and prov.calls == 1
    sent = Image.open(io.BytesIO(prov.images[0]))
    assert sent.size != (1000, 2000)
    assert "pricing table" in prov.prompts[0]


def test_second_look_without_a_region_skips_the_model():
    prov = Scripted(verdict())
    res = second_look(prov, dict(FINDING, bbox=None), png(), scan_id="s1", viewport="mobile")
    assert res.outcome == "no_crop" and res.error == "no_bbox" and prov.calls == 0


def test_second_look_uses_the_scanners_box_when_given():
    prov = Scripted(verdict())
    measured = {"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.1}
    res = second_look(prov, FINDING, png(), scan_id="s1", viewport="mobile", measured_bbox=measured)
    assert res.box[0] <= 500 <= res.box[2]


def test_second_look_handles_bad_replies_and_errors():
    assert second_look(Scripted(verdict("maybe")), FINDING, png(),
                       scan_id="s", viewport="m").outcome == "invalid_output"
    assert second_look(Scripted(json.dumps({"verdict": "confirmed", "confidence": 3})), FINDING, png(),
                       scan_id="s", viewport="m").outcome == "invalid_output"
    prov = Scripted("{oops", verdict("not_confirmed"))
    res = second_look(prov, FINDING, png(), scan_id="s", viewport="m")
    assert res.outcome == "ok" and res.verdict == "not_confirmed" and prov.calls == 2
    assert second_look(Scripted(ProviderError("down")), FINDING, png(),
                       scan_id="s", viewport="m").outcome == "provider_error"
    assert second_look(Scripted(RuntimeError("boom")), FINDING, png(),
                       scan_id="s", viewport="m").outcome == "provider_error"
    assert second_look(Scripted(verdict()), "not a finding", png(),
                       scan_id="s", viewport="m").outcome == "input_error"


def test_labels_never_drop_a_finding():
    assert combine_second_look("detected", "confirmed") == "confirmed"
    assert combine_second_look("detected", "not_confirmed") == "needs_review"
    assert combine_second_look("detected", "inconclusive") == "single_look"
    assert combine_second_look("detected", None) == "single_look"
    assert combine_second_look("inconclusive", "confirmed") == "confirmed"


def test_result_serialises_to_plain_json():
    res = second_look(Scripted(verdict()), FINDING, png(), scan_id="s1", viewport="mobile")
    assert json.loads(json.dumps(res.to_dict()))["verdict"] == "confirmed"
    assert json.loads(json.dumps(crop_region(png(), FINDING["bbox"]).to_dict()))["reason"] == "ok"
