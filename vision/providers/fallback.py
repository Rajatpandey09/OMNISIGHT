from .base import VisionProvider, ProviderError, MissingCredentials


class FallbackProvider(VisionProvider):
    """Try providers in order; move on when one fails (no key, quota, timeout, offline)."""

    def __init__(self, providers):
        self.providers = list(providers)
        self._used = self.providers[0].name

    @property
    def name(self):
        return self._used

    def analyze(self, image_png, system_prompt, user_prompt, timeout=30.0):
        errors, all_creds = [], True
        for p in self.providers:
            try:
                out = p.analyze(image_png, system_prompt, user_prompt, timeout)
                self._used = p.name
                return out
            except MissingCredentials as e:
                errors.append(f"{p.name}: {e}")
            except ProviderError as e:
                all_creds = False
                errors.append(f"{p.name}: {e}")
        self._used = self.providers[-1].name
        exc = MissingCredentials if all_creds else ProviderError
        raise exc("; ".join(errors))
