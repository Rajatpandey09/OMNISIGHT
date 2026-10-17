"""Pick a provider from VISION_PROVIDER (default: mock)."""
import os
from .providers.base import VisionProvider

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_provider(name: str | None = None) -> VisionProvider:
    """name may be one provider or a comma list, e.g. "gemini,ollama,heuristic"."""
    raw = (name or os.environ.get("VISION_PROVIDER", "mock")).strip().lower()
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if len(names) > 1:
        from .providers.fallback import FallbackProvider
        return FallbackProvider([_build(n) for n in names])
    return _build(names[0] if names else "mock")


def _build(name: str) -> VisionProvider:
    if name == "heuristic":
        from .providers.heuristic import HeuristicProvider
        return HeuristicProvider()
    if name == "mock":
        from .providers.mock import MockProvider
        return MockProvider()
    if name == "gemini":
        from .providers.gemini import GeminiProvider
        return GeminiProvider()
    if name == "openai":
        from .providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "anthropic":
        from .providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "ollama":
        from .providers.ollama import OllamaProvider
        return OllamaProvider()
    raise ValueError(f"unknown provider: {name!r}")
