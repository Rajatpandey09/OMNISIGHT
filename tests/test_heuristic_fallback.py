import json
import pytest
from vision.analyzer import analyze
from vision.factory import get_provider
from vision.providers.fallback import FallbackProvider
from vision.providers.heuristic import HeuristicProvider
from vision.providers.mock import MockProvider
from vision.providers.base import MissingCredentials


def run(p, vp="mobile", w=390, metrics=None):
    return analyze(p, "s", vp, w, 844, b"x", metrics)


def test_heuristic_overflow_and_offscreen_button():
    r = run(HeuristicProvider(), metrics={"scroll_width": 1200, "buttons": [
        {"selector": "#submit", "x": 350, "width": 120}]})
    kinds = {f.issue_type for f in r.findings}
    assert r.outcome == "ok" and kinds == {"horizontal_overflow", "offscreen_button"}
    assert r.provider == "heuristic"


def test_heuristic_clean_page_has_no_findings():
    r = run(HeuristicProvider(), metrics={"scroll_width": 390, "buttons": [
        {"selector": "#ok", "x": 10, "width": 100}]})
    assert r.outcome == "ok" and r.findings == [] and not r.cannot_determine


def test_heuristic_without_metrics_is_cannot_determine():
    r = run(HeuristicProvider())
    assert r.outcome == "ok" and r.cannot_determine


def test_fallback_moves_on_and_reports_provider():
    chain = FallbackProvider([MockProvider(fail_with="timeout"), HeuristicProvider()])
    r = run(chain, metrics={"scroll_width": 1200})
    assert r.outcome == "ok" and r.provider == "heuristic"


def test_fallback_all_missing_credentials():
    chain = FallbackProvider([MockProvider(fail_with="credentials"),
                              MockProvider(fail_with="credentials")])
    assert run(chain).outcome == "no_credentials"


def test_fallback_all_failed_is_provider_error():
    chain = FallbackProvider([MockProvider(fail_with="credentials"),
                              MockProvider(fail_with="timeout")])
    assert run(chain).outcome == "provider_error"


def test_factory_builds_chain_and_rejects_unknown(monkeypatch):
    p = get_provider("ollama,heuristic")
    assert isinstance(p, FallbackProvider) and len(p.providers) == 2
    with pytest.raises(ValueError):
        get_provider("nonsense")
