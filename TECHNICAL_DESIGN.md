<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

# Technical design: the `osmviews` Python package

## Objective

Provide a small, dependency-free Python library that, given a locally available
copy of the OSMViews raster, answers:

> How much is the location at this longitude/latitude looked at on
> OpenStreetMap-based maps, on a scale from 0.0 to 1.0?

The library reads a file path and nothing else — no network, no configuration, no
third-party packages.

## Background

[OSMViews](https://osmviews.toolforge.org) is a weekly pipeline
([brawer/osmviews](https://github.com/brawer/osmviews)) that aggregates roughly a
year of OpenStreetMap map-tile access logs into a single Cloud-Optimized GeoTIFF.
Each pixel holds a 32-bit float: the density of map views for that patch of the
planet. The file is about 594 MB and covers the whole world at ~150 m resolution.

Being able to score a location by “how much do people look here” is a useful
signal wherever geographic results need to be ranked by real-world importance.

A [Rust client](https://github.com/brawer/osmviews-rs) also exists. This package
predates it; the two now share the same behaviour and documentation but not code.

## Design

**Input.** `osmviews.open(path)` memory-maps the file (`mmap` from the standard
library) and parses its header. Mapping avoids copying the ~8 MB of tile-index
tables into the process and lets the OS page in only the tiles a workload
actually touches. The cost is a documented contract: the file must not change on
disk while an `OSMViews` is open.

**TIFF parsing.** Hand-written, in `src/osmviews/_tiff.py`. It reads only IFD 0
(the full-resolution level; the file also carries reduced-resolution pyramid
levels that this package never needs) and validates that the file is the exact
shape the OSMViews pipeline produces — little-endian classic TIFF, 256×256 tiles,
single-band 32-bit float, DEFLATE or no compression, no predictor. Anything else
is rejected with a `ValueError` (`osmviews.FormatError`). A general TIFF library
would be far more code and surface area for a format we fully control.

**Projection.** The OSMViews grid is Web Mercator (EPSG:3857) and lines up
exactly with the standard “slippy map” tile scheme, so mapping
longitude/latitude to a pixel is about ten lines of arithmetic in
`src/osmviews/_projection.py` — no projection library. Longitude wraps; latitudes
past the Web Mercator limit, and non-finite inputs, return `0.0`.

**Decompression.** Tiles are zlib-compressed, so the package uses `zlib` from the
standard library. Decompression is bounded to one tile’s worth of output
(256 KiB + 1 byte) and the result is rejected unless it is exactly 256 KiB and
the zlib stream ended cleanly, so a malformed or zip-bomb tile cannot exhaust
memory.

**Tile cache.** Decoding a tile is the expensive step, so decoded tiles are kept
in a small LRU cache (default 64 tiles ≈ 16 MB, configurable; `0` disables it).
The cache is **keyed by the tile’s byte offset in the file, not by its grid
position**, because the raster is sparse: its ~1 million grid positions resolve
to only about 100 000 distinct tiles, and two “empty” tiles alone back most of
the oceans. Keying by offset means a sweep across open water occupies a single
cache entry instead of evicting everything useful.

**Concurrency.** `rank()` takes a `threading.Lock` only to read or update the
cache and its counters; the tile decode of a miss happens outside the lock, so
concurrent readers don’t serialize on slow work. The worst case is two threads
briefly decoding the same tile and producing identical results. One `OSMViews`
instance can therefore serve many threads (subject, as always in CPython, to the
GIL).

**Output.** `rank()` returns a `float` in `0.0..1.0`. Internally this is the raw
sample divided by the raster’s embedded planetary maximum (`SMaxSampleValue`),
clamped; that scaling is an implementation detail and not part of the API
contract.

**Observability.** `metrics()` returns a `Metrics` dataclass — query count, cache
hit rate, evictions, cumulative decode time — meant to be logged once at the end
of a long-running job. The counters live under the lock that every query already
takes, so they add nothing measurable to the hot path.

## Non-goals

- **Downloading or refreshing** the dataset. Callers fetch the file themselves;
  the package only exposes `DOWNLOAD_URL`.
- **On-demand tile loading over the network.** The file genuinely is a
  Cloud-Optimized GeoTIFF and per-tile HTTP range requests would be feasible, but
  this package targets pipelines that download the whole file up front.
- **Writing GeoTIFFs**, reading other coordinate reference systems, or reading
  rasters other than OSMViews.
- **Exposing raw pixel values** or a dataset date (the file carries no date).
- **High performance.** It’s pure Python. The Rust client exists for that.

## Security

- **No runtime dependencies**: standard library only, so there is no third-party
  supply chain to audit.
- **`pip-audit`** and **CodeQL** run in CI; **OpenSSF Scorecard** tracks the
  repository’s supply-chain posture. Dependabot proposes dev-dependency and
  GitHub Actions updates as grouped monthly pull requests.
- **Bounded decompression**: a tile inflates to at most 256 KiB + 1 byte before
  being validated, so a crafted tile cannot exhaust memory.
- **All header parsing is bounds-checked**, and a corrupt file is rejected at
  `open()` so that `rank()` cannot raise on bad data.
- **Releases** publish to PyPI via Trusted Publishing (short-lived OIDC token, no
  stored secret), carry PEP 740 attestations, and ship SLSA v1.0 Build Level 3
  provenance. See [RELEASING.md](RELEASING.md).
