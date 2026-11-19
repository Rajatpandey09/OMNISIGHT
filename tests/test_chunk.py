import io

from PIL import Image

from vision.chunk import savings, split_tall, tile_bbox_to_full, tile_tops


def png(w, h, colour="white"):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, format="PNG")
    return buf.getvalue()


def test_a_short_image_is_one_tile():
    assert tile_tops(1200, 1600, 100) == [0]
    assert tile_tops(1600, 1600, 100) == [0]


def test_tall_image_tiles_overlap_and_cover_every_row():
    tops = tile_tops(4000, 1600, 100)
    assert tops == [0, 1500, 2400]
    covered = set()
    for t in tops:
        covered.update(range(t, t + 1600))
    assert covered == set(range(4000))
    for height in (1601, 2500, 3199, 5000, 12345):
        t = tile_tops(height, 1600, 100)
        assert t[0] == 0 and t[-1] + 1600 == height
        assert all(b > a for a, b in zip(t, t[1:]))
        assert all(b - a <= 1500 for a, b in zip(t, t[1:]))


def test_bad_tile_settings_are_rejected():
    for args in ((1000, 0, 0), (1000, 100, 100), (1000, 100, -1)):
        try:
            tile_tops(*args)
        except ValueError:
            continue
        raise AssertionError(args)


def test_split_tall_returns_the_tiles_with_their_positions():
    tiles = split_tall(png(300, 4000), 1600, 100)
    assert [t for t, _ in tiles] == [0, 1500, 2400]
    sizes = [Image.open(io.BytesIO(b)).size for _, b in tiles]
    assert all(s == (300, 1600) for s in sizes)
    assert split_tall(b"junk") == []
    assert len(split_tall(png(300, 800))) == 1


def test_a_region_in_a_tile_maps_back_to_the_full_page():
    # tile starts at 1500, is 1600 tall; the region sits at 50% of the tile, 10% tall
    got = tile_bbox_to_full({"x": 0.2, "y": 0.5, "width": 0.4, "height": 0.1}, 1500, 1600, 4000)
    assert abs(got["y"] - (1500 + 800) / 4000) < 1e-9 and abs(got["height"] - 160 / 4000) < 1e-9
    assert got["x"] == 0.2 and got["width"] == 0.4
    assert tile_bbox_to_full({"x": 0.2}, 0, 100, 100) is None
    assert tile_bbox_to_full({"x": 0, "y": 0, "width": 1, "height": 1}, 0, 100, 0) is None


def test_savings_reports_how_much_smaller_the_crop_is():
    s = savings(png(1000, 2000), png(500, 400))
    assert s["pixels_full"] == 2_000_000 and s["pixels_crop"] == 200_000
    assert s["pixels_saved_pct"] == 90.0
    assert s["bytes_crop"] < s["bytes_full"] and s["bytes_saved_pct"] > 0
    assert savings(b"junk", png(5, 5)) is None and savings(png(5, 5), b"junk") is None
