import base64
import os
from .base import MissingCredentials


def b64(image_png: bytes) -> str:
    return base64.b64encode(image_png).decode("ascii")


def need_key_and_model():
    key = os.environ.get("VISION_API_KEY", "").strip()
    model = os.environ.get("VISION_MODEL", "").strip()
    if not key:
        raise MissingCredentials("VISION_API_KEY is not set")
    if not model:
        raise MissingCredentials("VISION_MODEL is not set")
    return key, model
