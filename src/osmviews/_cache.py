# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""A small LRU cache of decoded tiles, plus the diagnostic counters.

Both are meant to live behind the single lock that :meth:`OSMViews.rank` takes
for every lookup, so the counters need no synchronisation of their own and add
nothing to the hot path beyond a few integer increments.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
    """Diagnostic counters from an :class:`~osmviews.OSMViews` instance.

    Every field except the ``tiles_cached`` / ``tile_cache_capacity`` gauges
    counts monotonically since ``open``.  The cache's memory footprint is
    ``tiles_cached * 256 KiB``.
    """

    #: Total calls to :meth:`~osmviews.OSMViews.rank`.
    queries: int
    #: Calls whose coordinates fell outside the covered area (returned ``0.0``).
    out_of_range: int
    #: Tile lookups served from the cache.
    tile_cache_hits: int
    #: Tile lookups that missed and triggered a decode.
    tile_cache_misses: int
    #: Tiles actually decoded.
    tiles_decoded: int
    #: Cache entries dropped to make room.  Large relative to the capacity means
    #: the cache is too small for the workload.
    tile_cache_evictions: int
    #: Tiles currently held in the cache.
    tiles_cached: int
    #: Configured cache capacity, in tiles.
    tile_cache_capacity: int
    #: Cumulative wall-clock time, in seconds, spent reading and decoding tiles.
    decode_time: float

    def tile_cache_hit_rate(self):
        """The fraction of tile lookups served from cache, or ``0.0`` before the
        first lookup."""
        lookups = self.tile_cache_hits + self.tile_cache_misses
        return self.tile_cache_hits / lookups if lookups else 0.0


class TileCache:
    """LRU cache of decoded tiles, keyed by the tile's byte offset in the file.

    Keying by offset rather than by grid position collapses the raster's large
    uniform areas (oceans, deserts), which are stored once and referenced from
    many tile-grid positions, onto a single cache entry.
    """

    __slots__ = (
        "_entries",
        "_tick",
        "capacity",
        "decode_time",
        "evictions",
        "hits",
        "misses",
        "out_of_range",
        "queries",
        "tiles_decoded",
    )

    def __init__(self, capacity):
        self.capacity = capacity
        self._tick = 0
        # offset -> [data, used]; smallest ``used`` is least recently used.
        self._entries = {}
        self.queries = 0
        self.out_of_range = 0
        self.hits = 0
        self.misses = 0
        self.tiles_decoded = 0
        self.evictions = 0
        self.decode_time = 0.0

    def record_out_of_range(self):
        """Record a ``rank()`` call whose coordinates fell outside the covered
        area."""
        self.queries += 1
        self.out_of_range += 1

    def lookup(self, offset, pixel):
        """Record a ``rank()`` call and return the requested pixel value if its
        tile is cached, else ``None``."""
        self.queries += 1
        entry = self._entries.get(offset)
        if entry is None:
            self.misses += 1
            return None
        self._tick += 1
        entry[1] = self._tick
        self.hits += 1
        return entry[0][pixel]

    def insert(self, offset, data, decode_time):
        """Insert a freshly decoded tile, evicting the least recently used entry
        if the cache is full."""
        self.tiles_decoded += 1
        self.decode_time += decode_time
        if self.capacity == 0:
            return
        if offset not in self._entries and len(self._entries) >= self.capacity:
            victim = min(self._entries, key=lambda k: self._entries[k][1])
            del self._entries[victim]
            self.evictions += 1
        self._tick += 1
        self._entries[offset] = [data, self._tick]

    def metrics(self):
        return Metrics(
            queries=self.queries,
            out_of_range=self.out_of_range,
            tile_cache_hits=self.hits,
            tile_cache_misses=self.misses,
            tiles_decoded=self.tiles_decoded,
            tile_cache_evictions=self.evictions,
            tiles_cached=len(self._entries),
            tile_cache_capacity=self.capacity,
            decode_time=self.decode_time,
        )
