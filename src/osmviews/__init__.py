# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""A client for `OSMViews <https://osmviews.toolforge.org>`_, a world-wide
ranking of geographic locations by how much they are looked at on
OpenStreetMap-based maps.

OSMViews aggregates a year of OpenStreetMap map-tile access logs into a single
raster covering the whole planet.  This package reads a copy of that raster from
local disk and answers point queries::

    import osmviews

    with osmviews.open("osmviews.tiff") as o:
        # A value from 0.0 (nobody looks here) to 1.0 (one of the most-viewed
        # places).  Coordinates are x, y -- longitude then latitude -- as in
        # GeoJSON.
        shibuya = o.rank(139.7013, 35.6586)
        sahara = o.rank(13.0, 23.0)
        assert shibuya > sahara

The package does not download anything: fetch the raster from
:data:`DOWNLOAD_URL` (regenerated weekly, ~594 MB) however you like, then hand
:func:`open` the path.

An :class:`OSMViews` instance is safe to share across threads.
"""

import array
import builtins
import math
import mmap
import sys
import threading
import time
import zlib

from . import _projection, _tiff
from ._cache import Metrics, TileCache
from ._tiff import FormatError

__all__ = ["DOWNLOAD_URL", "FormatError", "Metrics", "OSMViews", "open"]

#: Where the OSMViews raster is published.
#:
#: This package never downloads anything itself, but exposing the URL as a
#: constant means a change of hosting is a version bump here rather than a string
#: to hunt down in every caller.  The file behind it is regenerated weekly and is
#: roughly 594 MB.
DOWNLOAD_URL = "https://osmviews.toolforge.org/download/osmviews.tiff"

#: Decoded-tile cache capacity used by :func:`open` by default, in tiles.  Each
#: tile is a fixed 256 KiB, so this is about 16 MiB.
DEFAULT_CACHE_TILES = 64

_TILE_BYTES = _tiff.TILE_BYTES


def open(path, cache_tiles=DEFAULT_CACHE_TILES):
    """Open a downloaded OSMViews GeoTIFF from local disk.

    ``cache_tiles`` is the decoded-tile cache capacity; ``0`` disables caching.
    Equivalent to ``OSMViews(path, cache_tiles)``.
    """
    return OSMViews(path, cache_tiles)


class OSMViews:
    """A read-only view of a downloaded OSMViews raster.

    The file is memory-mapped and must not be modified or truncated for as long
    as the ``OSMViews`` is open.  Use it as a context manager, or call
    :meth:`close` when done.
    """

    def __init__(self, path, cache_tiles=DEFAULT_CACHE_TILES):
        # The file stays open for the lifetime of the memory map, so it can't be
        # wrapped in a `with`; `close()` / the context manager release both.
        self._file = builtins.open(path, "rb")  # noqa: SIM115
        try:
            try:
                self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            except ValueError:  # e.g. an empty file
                raise FormatError(
                    "not a readable OSMViews raster: not a TIFF (file too short)"
                ) from None
            try:
                self._header = _tiff.parse(self._mmap)
            except BaseException:
                self._mmap.close()
                raise
        except BaseException:
            self._file.close()
            raise
        self._cache = TileCache(cache_tiles)
        self._lock = threading.Lock()

    def rank(self, lng, lat):
        """How much the location at ``lng``/``lat`` (WGS84 degrees, x then y as
        in GeoJSON) is looked at on OpenStreetMap-based maps.

        The result runs from ``0.0`` (effectively never) to ``1.0`` (among the
        most-viewed places on the planet), derived from a year of OpenStreetMap
        tile-access logs.  Locations near the poles, beyond the map's coverage,
        and non-finite inputs return ``0.0``.  Longitude wraps, so ``181.0`` and
        ``-179.0`` are the same place.
        """
        header = self._header
        xy = _projection.project(lng, lat, header.size)
        if xy is None:
            with self._lock:
                self._cache.record_out_of_range()
            return 0.0

        x, y = xy
        grid_index = (y >> 8) * header.tiles_across + (x >> 8)
        pixel = (y & 255) * 256 + (x & 255)
        offset = header.tile_offsets.get(grid_index)

        with self._lock:
            value = self._cache.lookup(offset, pixel)
            if value is not None:
                return self._scale(value)
            blob_len = header.tile_byte_counts.get(grid_index)

        # Decode the missed tile outside the lock, so concurrent readers don't
        # serialize on slow work.  The worst case is two threads briefly decoding
        # the same tile and producing identical results.  The compressed blob is
        # read as a zero-copy view of the mmap; the `with` releases it (and so
        # keeps `close()` working) before we return.
        started = time.perf_counter()
        with memoryview(self._mmap) as file_view:
            tile = self._decode(file_view[offset : offset + blob_len])
        elapsed = time.perf_counter() - started
        if tile is None:
            return 0.0
        value = tile[pixel]
        with self._lock:
            self._cache.insert(offset, tile, elapsed)
        return self._scale(value)

    def metrics(self):
        """A snapshot of internal counters (:class:`Metrics`), meant to be logged
        once at the end of a long-running job."""
        with self._lock:
            return self._cache.metrics()

    def close(self):
        """Release the memory map and the underlying file."""
        self._mmap.close()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        self.close()

    def _decode(self, raw):
        """Turn one tile's stored bytes (``raw``, a memoryview over the mmap or a
        bytes object) into an ``array('f')`` of 65536 samples, or ``None`` if it
        is not a well-formed tile.

        ``open()`` already caps a tile's stored size, and the decompressor is
        told to stop after one tile's worth of output, so neither the input nor
        the output allocation here can be driven past ~256 KiB by a crafted file.
        """
        if self._header.compression == 8:
            decompressor = zlib.decompressobj()
            try:
                data = decompressor.decompress(raw, _TILE_BYTES + 1)
            except zlib.error:
                return None
            if not decompressor.eof or len(data) != _TILE_BYTES:
                return None
        elif len(raw) == _TILE_BYTES:
            data = raw
        else:
            return None
        tile = array.array("f")
        tile.frombytes(data)
        if sys.byteorder != "little":
            tile.byteswap()
        return tile

    def _scale(self, value):
        max_value = self._header.max_value
        if not math.isfinite(value) or not (max_value > 0.0):
            return 0.0
        ratio = value / max_value
        if ratio <= 0.0:
            return 0.0
        if ratio >= 1.0:
            return 1.0
        return ratio
