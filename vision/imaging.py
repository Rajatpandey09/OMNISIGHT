"""Make screenshots compact before sending. Falls back to the original bytes."""
import io


def compact(png_bytes: bytes, max_side: int = 1600) -> bytes:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        if max(img.size) <= max_side:
            return png_bytes
        img.thumbnail((max_side, max_side))
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return png_bytes
