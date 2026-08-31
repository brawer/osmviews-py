# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""A deliberately tiny, read-only parser for the one TIFF layout that the
OSMViews pipeline produces.

We only look at IFD 0 (the full-resolution level; the file also carries
reduced-resolution pyramid levels in later IFDs, which we never need).  Anything
that does not match the expected shape is rejected rather than trying to be a
general TIFF reader.
"""

import math
import struct
from dataclasses import dataclass

TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_BITS_PER_SAMPLE = 258
TAG_COMPRESSION = 259
TAG_SAMPLES_PER_PIXEL = 277
TAG_PLANAR_CONFIG = 284
TAG_PREDICTOR = 317
TAG_TILE_WIDTH = 322
TAG_TILE_LENGTH = 323
TAG_TILE_OFFSETS = 324
TAG_TILE_BYTE_COUNTS = 325
TAG_SAMPLE_FORMAT = 339
TAG_MAX_SAMPLE_VALUE = 341

TYPE_SHORT = 3
TYPE_LONG = 4
TYPE_FLOAT = 11
TYPE_DOUBLE = 12

TILE_SIDE = 256

#: A decoded tile is exactly ``TILE_SIDE * TILE_SIDE`` 32-bit floats = 256 KiB.
TILE_BYTES = TILE_SIDE * TILE_SIDE * 4

#: Upper bound on a tile's *stored* (possibly compressed) size.  A DEFLATE stream
#: can't beat its input by much even in the incompressible worst case -- stored
#: blocks add ~5 bytes per 64 KiB plus the zlib wrapper -- so a blob larger than
#: this is malformed.  Rejecting it at :func:`parse` keeps every allocation in
#: the decode path bounded to one tile.
MAX_TILE_BLOB = TILE_BYTES + 4096

_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_F32 = struct.Struct("<f")
_F64 = struct.Struct("<d")


class TileTable:
    """A ``TileOffsets`` or ``TileByteCounts`` array, kept as a position into the
    memory-mapped file (never copied out)."""

    __slots__ = ("_data", "_elem", "_pos")

    def __init__(self, data, pos, elem_size):
        self._data = data
        self._pos = pos
        self._elem = _U16 if elem_size == 2 else _U32

    def get(self, i):
        """Read the ``i``-th entry.  ``i`` must be within the tile grid; the
        array's extent was bounds-checked against the file in :func:`parse`."""
        return self._elem.unpack_from(self._data, self._pos + i * self._elem.size)[0]


@dataclass
class Header:
    """Everything :meth:`OSMViews.rank` needs from the file header."""

    #: Raster width in pixels (equal to the height).
    size: int
    #: Number of tiles along one axis (``size / 256``).
    tiles_across: int
    #: TIFF compression tag: ``1`` (none) or ``8`` (zlib DEFLATE).
    compression: int
    #: Highest sample value anywhere in the raster (``SMaxSampleValue``).
    max_value: float
    tile_offsets: TileTable
    tile_byte_counts: TileTable


class _Entry:
    __slots__ = ("count", "typ", "value")

    def __init__(self, typ, count, value):
        self.typ = typ
        self.count = count
        self.value = value  # the 4-byte value/offset field, verbatim

    def scalar_int(self):
        if self.count != 1:
            return None
        if self.typ == TYPE_SHORT:
            return _U16.unpack_from(self.value)[0]
        if self.typ == TYPE_LONG:
            return _U32.unpack_from(self.value)[0]
        return None

    def scalar_float(self, data):
        if self.count != 1:
            return None
        if self.typ == TYPE_FLOAT:
            return _F32.unpack_from(self.value)[0]
        if self.typ == TYPE_DOUBLE:
            at = _U32.unpack_from(self.value)[0]
            if at + 8 > len(data):
                return None
            return _F64.unpack_from(data, at)[0]
        return None


class FormatError(ValueError):
    """Raised by :func:`parse` when a file is not a readable OSMViews raster.

    Subclasses :class:`ValueError`, so ``except ValueError`` catches it too.
    """


def _err(msg):
    return FormatError("not a readable OSMViews raster: " + msg)


def parse(data):
    """Parse and validate the header of an OSMViews GeoTIFF held in ``data``
    (typically a memory map of the whole file).  Returns a :class:`Header`;
    raises :class:`ValueError` on anything that is not a raster we can read."""
    try:
        return _parse(data)
    except struct.error as e:  # a truncation the explicit checks didn't catch
        raise _err("malformed TIFF header") from e


def _parse(data):
    n_bytes = len(data)
    if n_bytes < 8:
        raise _err("not a TIFF (file too short)")
    if data[0:2] == b"MM":
        raise _err("big-endian TIFF is not supported")
    if data[0:2] != b"II":
        raise _err("not a TIFF")
    version = _U16.unpack_from(data, 2)[0]
    if version == 43:
        raise _err("BigTIFF is not supported")
    if version != 42:
        raise _err("not a TIFF (unrecognized version)")

    ifd = _U32.unpack_from(data, 4)[0]
    if ifd + 2 > n_bytes:
        raise _err("truncated file")
    n = _U16.unpack_from(data, ifd)[0]
    # Entry table plus the trailing 4-byte "next IFD" pointer.
    if ifd + 2 + n * 12 + 4 > n_bytes:
        raise _err("truncated IFD")

    fields = {}
    tile_offsets_entry = None
    tile_byte_counts_entry = None
    max_value = None
    for i in range(n):
        at = ifd + 2 + i * 12
        tag, typ, count = struct.unpack_from("<HHI", data, at)
        entry = _Entry(typ, count, data[at + 8 : at + 12])
        if tag == TAG_TILE_OFFSETS:
            tile_offsets_entry = entry
        elif tag == TAG_TILE_BYTE_COUNTS:
            tile_byte_counts_entry = entry
        elif tag == TAG_MAX_SAMPLE_VALUE:
            max_value = entry.scalar_float(data)
        else:
            fields[tag] = entry.scalar_int()

    width = fields.get(TAG_IMAGE_WIDTH)
    length = fields.get(TAG_IMAGE_LENGTH)
    if width is None or length is None:
        raise _err("missing image dimensions")
    if width != length:
        raise _err("raster is not square")
    size = width
    if size < TILE_SIDE or (size & (size - 1)) != 0:
        raise _err("unexpected raster size")
    if (
        fields.get(TAG_TILE_WIDTH) != TILE_SIDE
        or fields.get(TAG_TILE_LENGTH) != TILE_SIDE
    ):
        raise _err("unexpected tile size")
    if fields.get(TAG_BITS_PER_SAMPLE) != 32 or fields.get(TAG_SAMPLE_FORMAT) != 3:
        raise _err("samples are not 32-bit float")
    if fields.get(TAG_SAMPLES_PER_PIXEL) != 1:
        raise _err("expected a single sample per pixel")
    if fields.get(TAG_PLANAR_CONFIG) != 1:
        raise _err("unexpected planar configuration")
    compression = fields.get(TAG_COMPRESSION)
    if compression not in (1, 8):
        raise _err("unsupported compression")
    if fields.get(TAG_PREDICTOR) not in (None, 1):
        raise _err("TIFF predictor is not supported")
    if max_value is None:
        raise _err("missing SMaxSampleValue")
    if not math.isfinite(max_value):
        raise _err("SMaxSampleValue is not finite")

    tiles_across = size // TILE_SIDE
    grid = tiles_across * tiles_across

    if tile_offsets_entry is None:
        raise _err("missing TileOffsets")
    if tile_byte_counts_entry is None:
        raise _err("missing TileByteCounts")
    tile_offsets = _tile_table(data, tile_offsets_entry, grid)
    tile_byte_counts = _tile_table(data, tile_byte_counts_entry, grid)

    # One sequential pass so that a corrupt file is rejected here rather than
    # making rank() fallible.
    for i in range(grid):
        off = tile_offsets.get(i)
        blob_len = tile_byte_counts.get(i)
        if blob_len == 0 or off < 8:
            raise _err("invalid tile entry")
        if blob_len > MAX_TILE_BLOB:
            raise _err("tile blob is implausibly large")
        if off + blob_len > n_bytes:
            raise _err("tile data extends past end of file")

    return Header(
        size=size,
        tiles_across=tiles_across,
        compression=compression,
        max_value=max_value,
        tile_offsets=tile_offsets,
        tile_byte_counts=tile_byte_counts,
    )


def _tile_table(data, entry, grid):
    if entry.typ == TYPE_SHORT:
        elem_size = 2
    elif entry.typ == TYPE_LONG:
        elem_size = 4
    else:
        raise _err("unexpected tile-table element type")
    if entry.count != grid:
        raise _err("tile-table length does not match the tile grid")
    total = grid * elem_size
    if total <= 4:
        # Would be stored inline in the entry; the OSMViews pipeline never emits
        # a single-tile image, so we don't implement that path.
        raise _err("inline tile table not supported")
    pos = _U32.unpack_from(entry.value)[0]
    if pos + total > len(data):
        raise _err("tile table extends past end of file")
    return TileTable(data, pos, elem_size)
