<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

# osmviews

[![PyPI](https://img.shields.io/pypi/v/osmviews.svg)](https://pypi.org/project/osmviews/)
[![Python versions](https://img.shields.io/pypi/pyversions/osmviews.svg)](https://pypi.org/project/osmviews/)
[![CI](https://github.com/brawer/osmviews-py/actions/workflows/test-build.yml/badge.svg)](https://github.com/brawer/osmviews-py/actions/workflows/test-build.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/brawer/osmviews-py/badge)](https://scorecard.dev/viewer/?uri=github.com/brawer/osmviews-py)

Python client for [OSMViews](https://osmviews.toolforge.org), a world-wide ranking
of geographic locations by how much they are looked at on OpenStreetMap-based
maps. See the [main project](https://github.com/brawer/osmviews) for background.

OSMViews aggregates a year of OpenStreetMap map-tile access logs into a single
raster covering the whole planet. This package reads a copy of that raster from
local disk and answers point queries.

## Usage

```python
# pip install osmviews
import osmviews

with osmviews.open("osmviews.tiff") as o:
    # rank() is 0.0 (nobody looks here) to 1.0 (one of the most-viewed places on
    # Earth). Coordinates are x, y — longitude then latitude, as in GeoJSON;
    # values drift weekly.
    shibuya = o.rank(139.7013, 35.6586)  # Tokyo, Shibuya     ~0.69
    altstetten = o.rank(8.4889, 47.3915)  # Zürich, Altstetten ~0.66
    ushuaia = o.rank(-68.3030, -54.8019)  # Ushuaia            ~0.56
    sahara = o.rank(13.0000, 23.0000)  # Sahara             ~0.00
    assert shibuya > altstetten > ushuaia > sahara
```

The package does **not** download anything. Fetch the dataset (~594 MB,
regenerated weekly) from `osmviews.DOWNLOAD_URL` however you like, then pass the
path to `osmviews.open`.

An `OSMViews` instance is safe to share across threads: every query takes a lock
only briefly, and tile decoding happens outside it. Decoded tiles are kept in a
small LRU cache (`osmviews.open(path, cache_tiles=...)`, `0` disables it), so
queries clustered in one region stay fast. `o.metrics()` returns a snapshot of
counters (cache hit rate, decode time, …) worth logging at the end of a long run.

The file is memory-mapped, so it must not be modified or truncated while an
`OSMViews` is open.

## Performance

Rough numbers on an Apple M5, CPython 3.13 (from `benchmarks/bench.py`): `rank()`
returns in ~0.5 µs when the tile is already cached and ~57 µs on a miss that has
to read and inflate one. Each decoded tile is 256 KiB; the default LRU holds 64
of them (~16 MiB), and the GeoTIFF is memory-mapped rather than read onto the
heap. For bulk lookups, submit points in roughly spatial order (e.g. sorted by
tile or by S2 cell ID) so neighbouring queries reuse cached tiles.

This is pure Python; it is not trying to be fast. If throughput matters, the
[Rust client](https://github.com/brawer/osmviews-rs) answers the same query in
tens of nanoseconds.

## No dependencies

Pure Python 3.11+, standard library only (`mmap`, `zlib`, `struct`, `array`).
The TIFF header parsing and the map projection are done in-package.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The design and
its rationale are written up in [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md).

## Sponsoring

This package and the [OSMViews](https://github.com/brawer/osmviews) pipeline
behind it are maintained by [Sascha Brawer](https://github.com/brawer) as a
volunteer effort. If your project relies on them, please consider sponsoring
continued maintenance and future development via
[GitHub Sponsors](https://github.com/sponsors/brawer).

## License

MIT — see [LICENSE](LICENSE).
