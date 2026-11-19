import json
from .base import VisionProvider, ProviderError, MissingCredentials


class MockProvider(VisionProvider):
    """Deterministic provider for tests and offline development."""
    name = "mock"

    def __init__(self, reply=None, fail_with=None):
        self.reply = reply
        self.fail_with = fail_with  # "timeout" | "credentials" | None

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        if self.fail_with == "credentials":
            raise MissingCredentials("no API key configured")
        if self.fail_with == "timeout":
            raise ProviderError("timeout")
        if self.reply is not None:
            return self.reply
        return json.dumps({"findings": [], "cannot_determine": True,
                           "notes": "mock provider"})
