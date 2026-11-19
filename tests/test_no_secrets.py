"""Fails if something key-like is committed. Keys belong only in the git-ignored .env."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
PATTERNS = [
    re.compile(r"VISION_API_KEY[ \t]*=[ \t]*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
]


def test_no_key_like_strings_in_repo():
    hits = []
    for f in ROOT.rglob("*"):
        if (not f.is_file() or f.name == ".env" or f == Path(__file__)
                or SKIP_DIRS & set(f.parts)):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat in PATTERNS:
            if pat.search(text):
                hits.append(str(f.relative_to(ROOT)))
    assert not hits, f"possible secrets in: {hits}"
