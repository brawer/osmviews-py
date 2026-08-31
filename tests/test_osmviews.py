# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""Offline tests: build small OSMViews-shaped GeoTIFFs in a temp file and
exercise open / rank / metrics end to end.  Mirrors the Rust crate's
``tests/offline.rs``."""

import os
import threading

import pytest

import osmviews
from osmviews._tiff import MAX_TILE_BLOB
from tests._fixtures import (
    TILE_BYTE_COUNTS_POS,
    TILE_OFFSETS_POS,
    build_tiff,
    temp_tiff,
)

# Points that land in a known grid tile of a build_tiff raster (size 512, two
# tiles per axis).  Western hemisphere -> left column, northern -> top row.
TOP_LEFT = (-90.0, 45.0)
TOP_RIGHT = (90.0, 45.0)
BOTTOM_LEFT = (-90.0, -45.0)
BOTTOM_RIGHT = (90.0, -45.0)


def _datapath(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)


def test_download_url_points_at_a_tiff():
    assert osmviews.DOWNLOAD_URL.startswith("https://")
    assert osmviews.DOWNLOAD_URL.endswith(".tiff")


def test_version_is_exposed():
    assert isinstance(osmviews.__version__, str)
    assert osmviews.__version__[0].isdigit()


def test_format_error_is_a_value_error():
    assert issubclass(osmviews.FormatError, ValueError)


def test_ranks_scale_against_the_planetary_maximum():
    with temp_tiff(build_tiff(8, [3.0, 0.0, 10.0, 10.0], 10.0)) as path:
        with osmviews.open(path) as o:
            assert o.rank(*TOP_LEFT) == pytest.approx(0.3)
            assert o.rank(*TOP_RIGHT) == 0.0
            assert o.rank(*BOTTOM_LEFT) == 1.0
            # Null Island falls in the bottom-right tile of this raster.
            assert o.rank(0.0, 0.0) == 1.0
            # Beyond the Web Mercator latitude limit.
            assert o.rank(0.0, 89.0) == 0.0


def test_ranks_clamp_to_the_unit_interval():
    # Declared maximum is 10.0, but the tiles carry a value well above it and one
    # below zero.
    with temp_tiff(build_tiff(8, [25.0, -4.0, 10.0, 6.0], 10.0)) as path:
        with osmviews.open(path) as o:
            assert o.rank(*TOP_LEFT) == 1.0  # 25.0 -> clamped
            assert o.rank(*TOP_RIGHT) == 0.0  # -4.0 -> clamped
            assert o.rank(*BOTTOM_LEFT) == 1.0  # exactly the max
            assert o.rank(*BOTTOM_RIGHT) == pytest.approx(0.6)


def test_shared_tiles_use_one_cache_entry():
    # Bottom-left and bottom-right tiles have the same value -> one blob.
    with temp_tiff(build_tiff(8, [3.0, 0.0, 7.0, 7.0], 10.0)) as path:
        with osmviews.open(path) as o:
            o.rank(*BOTTOM_LEFT)
            o.rank(*BOTTOM_RIGHT)
            m = o.metrics()
            assert m.tiles_cached == 1
            assert m.tiles_decoded == 1
            assert m.tile_cache_misses == 1
            assert m.tile_cache_hits == 1


def test_uncompressed_tiles_are_supported():
    with temp_tiff(build_tiff(1, [5.0, 5.0, 5.0, 5.0], 10.0)) as path:
        with osmviews.open(path) as o:
            assert o.rank(*TOP_LEFT) == pytest.approx(0.5)


def test_metrics_track_queries_evictions_and_hit_rate():
    with temp_tiff(build_tiff(8, [1.0, 2.0, 3.0, 4.0], 10.0)) as path:
        with osmviews.open(path, cache_tiles=2) as o:
            o.rank(*TOP_LEFT)
            o.rank(*TOP_RIGHT)
            o.rank(*BOTTOM_LEFT)
            o.rank(*BOTTOM_RIGHT)
            o.rank(0.0, 89.0)  # out of range
            m = o.metrics()
            assert m.queries == 5
            assert m.out_of_range == 1
            assert m.tile_cache_misses == 4
            assert m.tile_cache_hits == 0
            assert m.tiles_cached == 2
            assert m.tile_cache_capacity == 2
            assert m.tile_cache_evictions == 2
            assert m.decode_time > 0.0
            assert m.tile_cache_hit_rate() == 0.0


def test_disabled_cache_still_answers_and_never_stores():
    with temp_tiff(build_tiff(8, [3.0, 0.0, 7.0, 7.0], 10.0)) as path:
        with osmviews.open(path, cache_tiles=0) as o:
            assert o.rank(*TOP_LEFT) == pytest.approx(0.3)
            assert o.rank(*TOP_LEFT) == pytest.approx(0.3)
            m = o.metrics()
            assert m.tiles_cached == 0
            assert m.tiles_decoded == 2
            assert m.tile_cache_hits == 0


def test_rejects_non_tiff():
    with pytest.raises(ValueError):
        osmviews.open(_datapath("hello.txt"))


def test_rejects_big_endian():
    b = bytearray(build_tiff(8, [1.0, 1.0, 1.0, 1.0], 10.0))
    b[0:2] = b"MM"
    with temp_tiff(bytes(b)) as path, pytest.raises(ValueError):
        osmviews.open(path)


def test_rejects_bigtiff_version():
    b = bytearray(build_tiff(8, [1.0, 1.0, 1.0, 1.0], 10.0))
    b[2] = 43
    b[3] = 0
    with temp_tiff(bytes(b)) as path, pytest.raises(ValueError):
        osmviews.open(path)


def test_rejects_truncated_file():
    b = build_tiff(8, [1.0, 2.0, 3.0, 4.0], 10.0)
    with temp_tiff(b[: len(b) // 2]) as path, pytest.raises(ValueError):
        osmviews.open(path)


def test_rejects_tile_offset_past_end_of_file():
    b = bytearray(build_tiff(8, [1.0, 2.0, 3.0, 4.0], 10.0))
    b[TILE_OFFSETS_POS : TILE_OFFSETS_POS + 4] = (0xFFFFFF00).to_bytes(4, "little")
    with temp_tiff(bytes(b)) as path, pytest.raises(ValueError):
        osmviews.open(path)


def test_rejects_oversized_tile_blob():
    # A tile whose stored size exceeds what a 256 KiB tile could compress to is
    # rejected at open(), so rank()'s decode allocations stay bounded.
    b = bytearray(build_tiff(8, [1.0, 2.0, 3.0, 4.0], 10.0))
    b[TILE_BYTE_COUNTS_POS : TILE_BYTE_COUNTS_POS + 4] = (MAX_TILE_BLOB + 1).to_bytes(
        4, "little"
    )
    with temp_tiff(bytes(b)) as path:
        with pytest.raises(ValueError, match="implausibly large"):
            osmviews.open(path)


def test_shared_across_threads():
    with temp_tiff(build_tiff(8, [1.0, 2.0, 3.0, 4.0], 10.0)) as path:
        with osmviews.open(path, cache_tiles=4) as o:
            results = []

            def worker(thread):
                total = 0.0
                for i in range(2000):
                    lng = -90.0 + thread + (i % 5) * 0.01
                    lat = 45.0 if i % 2 == 0 else -45.0
                    total += o.rank(lng, lat)
                results.append(total)

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert all(r >= 0.0 for r in results)
            m = o.metrics()
            assert m.queries == 8 * 2000
            assert m.out_of_range == 0
            assert m.tile_cache_hits + m.tile_cache_misses == m.queries - m.out_of_range
            assert m.tiles_decoded >= m.tile_cache_misses
