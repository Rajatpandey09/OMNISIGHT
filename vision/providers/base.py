from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Timeout, quota, network, or API failure."""


class MissingCredentials(ProviderError):
    pass


class VisionProvider(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, image_png: bytes, system_prompt: str,
                user_prompt: str, timeout: float = 30.0) -> str:
        """Return the model's raw text reply. Raise ProviderError on failure."""
