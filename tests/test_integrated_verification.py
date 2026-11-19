"""Contract tests for the integrated VLM + deterministic verification rules."""
from vision_api import _metrics_fixed
from vision.patches import combine_verdicts


def test_overflow_requires_metrics_to_be_clear():
    assert _metrics_fixed("horizontal_overflow", "", {"has_horizontal_overflow": False}) is True
    assert _metrics_fixed("horizontal_overflow", "", {"has_horizontal_overflow": True}) is False


def test_offscreen_button_uses_selector_or_available_button_evidence():
    metrics = {"buttons": [{"selector": "#save-profile-btn", "is_off_screen": False}]}
    assert _metrics_fixed("offscreen_button", "#save-profile-btn", metrics) is True
    assert _metrics_fixed("offscreen_button", ".model-described-button", metrics) is True


def test_hidden_control_uses_hidden_control_metrics():
    assert _metrics_fixed("hidden_control", "#checkout", {"hidden_controls": ["checkout-btn"]}) is False
    assert _metrics_fixed("hidden_control", "#checkout", {"hidden_controls": []}) is True


def test_unmeasured_visual_issue_does_not_claim_metric_success():
    assert _metrics_fixed("overlapping_text", ".heading", {}) is None


def test_verified_requires_both_vlm_and_metric_signals():
    verdict, _ = combine_verdicts("fixed", True, "none")
    assert verdict == "fixed"


def test_model_only_success_remains_inconclusive():
    verdict, _ = combine_verdicts("fixed", None, "none")
    assert verdict == "inconclusive"


def test_conflicting_signals_remain_inconclusive():
    verdict, _ = combine_verdicts("fixed", False, "none")
    assert verdict == "inconclusive"
