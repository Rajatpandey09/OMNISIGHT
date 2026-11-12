import os
from .base import VisionProvider, ProviderError, MissingCredentials
from .http import post_json
from ._common import b64

# Token budget per call type.  Keeping these tight is the single biggest lever
# for reducing inference latency — the model stops as soon as the budget runs
# out rather than generating until it feels done.
_NUM_PREDICT = {
    "patch":   300,   # suggest_patches: small JSON object with ≤2 patches
    "verify":  200,   # verify_fix:      tiny JSON verdict object
    "default": 400,   # analyze / pipeline: allow a bit more for findings list
}


class OllamaProvider(VisionProvider):
    """Local model; no API key. Needs Ollama running and a vision-capable model pulled.

    Parameters
    ----------
    mode : "patch" | "verify" | "default"
        Controls which token budget and, optionally, which model is used.
        ``"patch"`` uses PATCH_MODEL (defaults to VISION_MODEL) so a smaller
        text-capable model can handle patch generation while the full VLM is
        reserved for visual before/after comparison (``"verify"``).
    """

    name = "ollama"

    def __init__(self, mode: str = "default"):
        self._mode = mode if mode in _NUM_PREDICT else "default"

    def analyze(self, image_png, system_prompt, user_prompt, timeout=120.0):
        # Pick model: patch generation can use a lighter text model if configured
        if self._mode == "patch":
            model = (os.environ.get("PATCH_MODEL") or
                     os.environ.get("VISION_MODEL", "")).strip()
        else:
            model = os.environ.get("VISION_MODEL", "").strip()
        if not model:
            raise MissingCredentials("VISION_MODEL is not set")

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        num_predict = _NUM_PREDICT[self._mode]

        payload = {
            "model": model,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": num_predict,
                "temperature": 0.1,
            },
        }

        # Text-only models (patch mode with a non-VLM like llama3.2:3b) must NOT
        # receive an images field — they either error or waste time on base64
        # they cannot process. VLM modes always get the screenshot.
        is_text_model = (
            self._mode == "patch"
            and (os.environ.get("PATCH_MODEL") or "").strip()
            and os.environ.get("PATCH_MODEL", "").strip() != os.environ.get("VISION_MODEL", "").strip()
        )
        user_message: dict = {"role": "user", "content": user_prompt}
        if not is_text_model:
            user_message["images"] = [b64(image_png)]

        payload["messages"] = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]
        data = post_json(f"{host}/api/chat", payload, None, timeout)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError):
            raise ProviderError("unexpected Ollama response shape")
