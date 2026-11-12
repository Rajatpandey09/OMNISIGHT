"""Pick a provider from VISION_PROVIDER (default: mock)."""
import os
from .providers.base import VisionProvider

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_provider(name: str | None = None, mode: str = "default") -> VisionProvider:
    """name may be one provider or a comma list, e.g. "gemini,ollama,heuristic".

    mode controls token budgets and model selection inside OllamaProvider:
      "patch"   — lighter model (PATCH_MODEL env), 300-token cap
      "verify"  — full VLM, 200-token cap (just a JSON verdict)
      "default" — full VLM, 400-token cap (findings list)
    """
    raw = (name or os.environ.get("VISION_PROVIDER", "mock")).strip().lower()
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if len(names) > 1:
        from .providers.fallback import FallbackProvider
        return FallbackProvider([_build(n, mode) for n in names])
    return _build(names[0] if names else "mock", mode)


def _build(name: str, mode: str = "default") -> VisionProvider:
    if name == "heuristic":
        from .providers.heuristic import HeuristicProvider
        return HeuristicProvider()
    if name == "mock":
        from .providers.mock import MockProvider
        return MockProvider()
    if name == "ollama":
        from .providers.ollama import OllamaProvider
        return OllamaProvider(mode=mode)
    raise ValueError(f"unknown provider: {name!r}")
