# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""Dependency-free micro-benchmarks for ``osmviews.OSMViews.rank``.

Run with::

    python benchmarks/bench.py

It builds a small synthetic OSMViews-shaped GeoTIFF (so it needs no dataset
download) and reports ``ns/call`` for a cache hit and for the re-decode path.
The numbers are informational, not pass/fail.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import osmviews
from tests._fixtures import build_tiff, temp_tiff


def bench_rank_cached(path, iterations=1_000_000):
    with osmviews.open(path) as o:
        o.rank(-90.0, 45.0)  # warm the tile
        acc = 0.0
        start = time.perf_counter()
        for i in range(iterations):
            # Sweep within the (already cached) top-left tile.
            acc += o.rank(-120.0 + (i % 60), 45.0)
        elapsed = time.perf_counter() - start
        m = o.metrics()
        print(
            f"rank(), cached tile:          {elapsed / iterations * 1e9:8.1f} ns/call  "
            f"({iterations:,} calls, hit rate {m.tile_cache_hit_rate():.5f})"
        )


def bench_rank_uncached(path, iterations=20_000):
    with osmviews.open(path, cache_tiles=0) as o:
        acc = 0.0
        start = time.perf_counter()
        for _ in range(iterations):
            acc += o.rank(-90.0, 45.0)
        elapsed = time.perf_counter() - start
        print(
            f"rank(), re-decoding every call: {elapsed / iterations * 1e9:7.0f} ns/call  "
            f"({iterations:,} calls)"
        )


def main():
    print(f"Python {sys.version.split()[0]} on {sys.platform}")
    with temp_tiff(build_tiff(8, [3.0, 0.0, 7.0, 7.0], 10.0)) as path:
        bench_rank_cached(path)
        bench_rank_uncached(path)


if __name__ == "__main__":
    main()
