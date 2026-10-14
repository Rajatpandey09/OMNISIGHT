"""call -> parse -> validate -> fallback. analyze() never raises."""
import json
import re
from pydantic import ValidationError
from .schema import AnalysisResult, Finding, ModelOutput
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .providers.base import VisionProvider, ProviderError, MissingCredentials


def extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def analyze(provider: VisionProvider, scan_id: str, viewport: str,
            width: int, height: int, image_png: bytes,
            metrics: dict | None = None, timeout: float = 30.0) -> AnalysisResult:
    base = dict(scan_id=scan_id, viewport=viewport, provider=provider.name)
    user_prompt = build_user_prompt(viewport, width, height, metrics or {})
    try:
        raw = provider.analyze(image_png, SYSTEM_PROMPT, user_prompt, timeout)
    except MissingCredentials as e:
        return AnalysisResult(**base, outcome="no_credentials", error=str(e))
    except ProviderError as e:
        return AnalysisResult(**base, outcome="provider_error", error=str(e))
    except Exception as e:  # defensive: never crash the scan
        return AnalysisResult(**base, outcome="provider_error", error=repr(e))
    try:
        out = ModelOutput.model_validate(extract_json(raw))
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        return AnalysisResult(**base, outcome="invalid_output",
                              error=f"{type(e).__name__}: {str(e)[:200]}")
    findings = [Finding(**f.model_dump(), scan_id=scan_id, viewport=viewport)
                for f in out.findings]
    return AnalysisResult(**base, outcome="ok", findings=findings,
                          cannot_determine=out.cannot_determine)
