"""call -> parse -> validate -> fallback. analyze() never raises."""
import json
import re
from pydantic import ValidationError
from .schema import AnalysisResult, Finding, ModelOutput
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .providers.base import VisionProvider, ProviderError, MissingCredentials


def _unfence(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return fence.group(1).strip() if fence else text


def extract_json(text: str) -> dict:
    return json.loads(_unfence(text))


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


def parse_model_json(raw: str):
    """Strict parse first. If that fails, retry after removing trailing commas (a common
    small-model slip). Returns (data, repaired). Anything still broken raises."""
    try:
        return extract_json(raw), False
    except json.JSONDecodeError:
        return json.loads(_strip_trailing_commas(_unfence(raw))), True


def _analyze_once(provider: VisionProvider, scan_id: str, viewport: str,
                  width: int, height: int, image_png: bytes,
                  metrics: dict | None = None, timeout: float = 30.0,
                  html: str | None = None) -> AnalysisResult:
    def base():  # evaluated after the call: a fallback chain may switch providers
        return dict(scan_id=scan_id, viewport=viewport, provider=provider.name)

    user_prompt = build_user_prompt(viewport, width, height, metrics or {}, html)
    try:
        raw = provider.analyze(image_png, SYSTEM_PROMPT, user_prompt, timeout)
    except MissingCredentials as e:
        return AnalysisResult(**base(), outcome="no_credentials", error=str(e))
    except ProviderError as e:
        return AnalysisResult(**base(), outcome="provider_error", error=str(e))
    except Exception as e:  # defensive: never crash the scan
        return AnalysisResult(**base(), outcome="provider_error", error=repr(e))
    repaired = False
    try:
        data, repaired = parse_model_json(raw)
        out = ModelOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, AttributeError) as e:
        return AnalysisResult(**base(), outcome="invalid_output",
                              error=f"{type(e).__name__}: {str(e)[:200]} | raw starts: {str(raw)[:300]!r}")
    findings = [Finding(**f.model_dump(), scan_id=scan_id, viewport=viewport,
                        id=f"{scan_id}:{viewport}:{i}")
                for i, f in enumerate(out.findings, 1)]
    return AnalysisResult(**base(), outcome="ok", findings=findings,
                          cannot_determine=out.cannot_determine, json_repaired=repaired)


def analyze(*args, retries: int = 1, **kwargs) -> AnalysisResult:
    """Call once; if the reply was unusable (invalid_output), try again up to `retries` times."""
    result = _analyze_once(*args, **kwargs)
    for _ in range(retries):
        if result.outcome != "invalid_output":
            break
        result = _analyze_once(*args, **kwargs)
    return result
