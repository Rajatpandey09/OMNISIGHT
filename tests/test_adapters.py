import io
import urllib.error
import pytest
from vision.providers import ollama
from vision.providers.base import MissingCredentials, ProviderError
from vision.providers.http import post_json


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("VISION_MODEL", "test-model")


def call(fake):
    ollama.post_json = fake
    return ollama.OllamaProvider().analyze(b"img", "sys", "user")


def test_ollama_parse():
    assert call(lambda u, p, h, t: {"message": {"content": "{}"}}) == "{}"


def test_bad_shape_is_provider_error():
    with pytest.raises(ProviderError):
        call(lambda u, p, h, t: {})


def test_missing_model(monkeypatch):
    monkeypatch.delenv("VISION_MODEL")
    with pytest.raises(MissingCredentials):
        ollama.OllamaProvider().analyze(b"x", "s", "u")


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, io.BytesIO(b""))


@pytest.mark.parametrize("code,exc", [(401, MissingCredentials), (429, ProviderError), (500, ProviderError)])
def test_http_errors_mapped(monkeypatch, code, exc):
    def boom(*a, **k):
        raise _http_error(code)
    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(exc):
        post_json("http://x", {})
