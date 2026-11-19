import os
from .base import VisionProvider, ProviderError, MissingCredentials
from .http import post_json
from ._common import b64


class OllamaProvider(VisionProvider):
    """Local model; no API key. Needs Ollama running and a vision-capable model pulled."""
    name = "ollama"

    def analyze(self, image_png, system_prompt, user_prompt, timeout=120.0):
        model = os.environ.get("VISION_MODEL", "").strip()
        if not model:
            raise MissingCredentials("VISION_MODEL is not set")
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        payload = {
            "model": model, "stream": False, "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt, "images": [b64(image_png)]},
            ],
        }
        data = post_json(f"{host}/api/chat", payload, None, timeout)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError):
            raise ProviderError("unexpected Ollama response shape")
