"""Week 4: tiles for tall pages, and a measure of what a crop saves.

A full-page screenshot can be thousands of pixels tall. Shrinking it to fit one model call
makes small text unreadable. split_tall cuts it into overlapping tiles that each keep full
detail, and tile_bbox_to_full puts a region found in a tile back onto the full page.

savings() reports how much smaller a crop is than the full image (pixels and bytes), so the
"saves tokens" claim can be shown with numbers. Token counts differ between providers, so
this reports pixels and bytes, which is what the image cost follows.

Wiring tiles into the analysis pipeline (one call per tile, then merging findings) is not
done here.
"""
from __future__ import annotations

import io


def tile_tops(height: int, max_height: int = 1600, overlap: int = 100) -> list[int]:
    """Top edges of the tiles. Every row is covered, the last tile ends at the bottom."""
    if max_height < 1 or overlap < 0 or overlap >= max_height:
        raise ValueError("need max_height >= 1 and 0 <= overlap < max_height")
    if height <= max_height:
        return [0]
    step = max_height - overlap
    tops, top = [], 0
    while True:
        if top + max_height >= height:
            tops.append(height - max_height)
            return tops
        tops.append(top)
        top += step


def split_tall(image_png: bytes, max_height: int = 1600, overlap: int = 100) -> list[tuple[int, bytes]]:
    """(top_pixel, png_bytes) per tile. An unreadable image gives an empty list."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(image_png)).convert("RGB")
    except Exception:
        return []
    tiles = []
    for top in tile_tops(img.height, max_height, overlap):
        piece = img.crop((0, top, img.width, min(top + max_height, img.height)))
        buf = io.BytesIO()
        piece.save(buf, format="PNG")
        tiles.append((top, buf.getvalue()))
    return tiles


def tile_bbox_to_full(bbox: dict, top: int, tile_height: int, full_height: int) -> dict | None:
    """A bbox in fractions of a tile, as a bbox in fractions of the full page."""
    try:
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
    except (KeyError, TypeError):
        return None
    if full_height <= 0 or tile_height <= 0:
        return None
    return {"x": x, "y": (top + y * tile_height) / full_height, "width": w,
            "height": h * tile_height / full_height}


def savings(full_png: bytes, crop_png: bytes) -> dict | None:
    """How much smaller the crop is. None if either image cannot be read."""
    from PIL import Image
    try:
        full = Image.open(io.BytesIO(full_png))
        crop = Image.open(io.BytesIO(crop_png))
    except Exception:
        return None
    pf, pc = full.width * full.height, crop.width * crop.height
    if pf == 0 or not full_png:
        return None
    return {"pixels_full": pf, "pixels_crop": pc, "pixels_saved_pct": round(100 * (1 - pc / pf), 1),
            "bytes_full": len(full_png), "bytes_crop": len(crop_png),
            "bytes_saved_pct": round(100 * (1 - len(crop_png) / len(full_png)), 1)}
