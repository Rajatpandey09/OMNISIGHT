"""Tiny HTTP helper (standard library only). Maps failures to ProviderError."""
import json
import socket
import urllib.error
import urllib.request
from .base import ProviderError, MissingCredentials


def post_json(url: str, payload: dict, headers: dict | None = None,
              timeout: float = 30.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise MissingCredentials(f"authentication failed (HTTP {e.code})")
        if e.code == 429:
            raise ProviderError("rate limit or quota exceeded (HTTP 429)")
        raise ProviderError(f"HTTP {e.code}")
    except (socket.timeout, TimeoutError):
        raise ProviderError("timeout")
    except urllib.error.URLError as e:
        raise ProviderError(f"network error: {e.reason}")
    except json.JSONDecodeError:
        raise ProviderError("provider returned non-JSON response")
