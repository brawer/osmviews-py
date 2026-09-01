# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""Helpers shared by the tests: a builder for minimal-but-real OSMViews-shaped
GeoTIFFs, and a self-deleting temp file."""

import contextlib
import datetime
import os
import struct
import tempfile
import zlib

#: Date written into the ``DateTime`` tag (306) unless a test overrides it.
DEFAULT_DATE = datetime.date(2026, 1, 15)

#: Number of IFD entries :func:`build_tiff` writes (12 raster tags + ``DateTime``).
ENTRY_COUNT = 13

#: ``DateTime`` is 20 bytes ("YYYY:MM:DD HH:MM:SS" + NUL) and sits right after
#: the IFD, ahead of the tile tables.
_IFD_END = 8 + 2 + ENTRY_COUNT * 12 + 4
#: File offset of the ``DateTime`` string in a :func:`build_tiff` file.
DATETIME_POS = _IFD_END
#: File offset of the ``TileOffsets`` array in a :func:`build_tiff` file.
TILE_OFFSETS_POS = DATETIME_POS + 20
#: File offset of the ``TileByteCounts`` array in a :func:`build_tiff` file.
TILE_BYTE_COUNTS_POS = TILE_OFFSETS_POS + 16

_TYPE_ASCII = 2
_TYPE_SHORT = 3
_TYPE_LONG = 4
_TYPE_FLOAT = 11

_TILE = 256 * 256


def _entry(tag, typ, count, value):
    return struct.pack("<HHI", tag, typ, count) + value


def _short(v):
    return struct.pack("<H", v) + b"\x00\x00"


def build_tiff(compression, tile_values, max_value, date=DEFAULT_DATE):
    """Build a 512x512 single-level GeoTIFF laid out like the real OSMViews file:
    four 256x256 tiles, out-of-line ``TileOffsets`` / ``TileByteCounts``, 32-bit
    float samples, ``SMaxSampleValue = max_value``, and a ``DateTime`` tag.

    ``tile_values[g]`` is the uniform value of grid tile ``g`` (order: top-left,
    top-right, bottom-left, bottom-right).  Tiles with an equal value share one
    compressed blob and therefore one file offset, exercising the dedup cache.

    ``compression`` is ``8`` (zlib) or ``1`` (none).  ``date`` is a
    :class:`datetime.date` for the ``DateTime`` tag, or ``None`` to omit it.
    """
    assert len(tile_values) == 4
    blobs = []
    blob_bits = []
    grid_to_blob = []
    for value in tile_values:
        bits = struct.pack("<f", value)
        if bits in blob_bits:
            grid_to_blob.append(blob_bits.index(bits))
            continue
        raw = bits * _TILE
        blob = zlib.compress(raw, 6) if compression == 8 else raw
        blobs.append(blob)
        blob_bits.append(bits)
        grid_to_blob.append(len(blobs) - 1)

    n_entries = 13 if date is not None else 12
    ifd_end = 8 + 2 + n_entries * 12 + 4
    datetime_bytes = b""
    if date is not None:
        datetime_bytes = date.strftime("%Y:%m:%d 00:00:00").encode("ascii") + b"\x00"
        assert len(datetime_bytes) == 20
    tile_offsets_pos = ifd_end + len(datetime_bytes)
    tile_byte_counts_pos = tile_offsets_pos + 16

    blob_pos = []
    cursor = tile_byte_counts_pos + 16
    for blob in blobs:
        blob_pos.append(cursor)
        cursor += len(blob)
    tile_offsets = [blob_pos[grid_to_blob[g]] for g in range(4)]
    tile_byte_counts = [len(blobs[grid_to_blob[g]]) for g in range(4)]

    entries = [
        _entry(256, _TYPE_LONG, 1, struct.pack("<I", 512)),
        _entry(257, _TYPE_LONG, 1, struct.pack("<I", 512)),
        _entry(258, _TYPE_SHORT, 1, _short(32)),
        _entry(259, _TYPE_SHORT, 1, _short(compression)),
        _entry(277, _TYPE_SHORT, 1, _short(1)),
        _entry(284, _TYPE_SHORT, 1, _short(1)),
        # TIFF tags must appear in ascending order; 306 belongs here.
        *(
            [_entry(306, _TYPE_ASCII, 20, struct.pack("<I", ifd_end))]
            if date is not None
            else []
        ),
        _entry(322, _TYPE_SHORT, 1, _short(256)),
        _entry(323, _TYPE_SHORT, 1, _short(256)),
        _entry(324, _TYPE_LONG, 4, struct.pack("<I", tile_offsets_pos)),
        _entry(325, _TYPE_LONG, 4, struct.pack("<I", tile_byte_counts_pos)),
        _entry(339, _TYPE_SHORT, 1, _short(3)),
        _entry(341, _TYPE_FLOAT, 1, struct.pack("<f", max_value)),
    ]
    assert len(entries) == n_entries

    buf = bytearray()
    buf += b"II"
    buf += struct.pack("<H", 42)
    buf += struct.pack("<I", 8)
    buf += struct.pack("<H", n_entries)
    for e in entries:
        buf += e
    buf += struct.pack("<I", 0)  # no next IFD
    assert len(buf) == ifd_end
    buf += datetime_bytes
    assert len(buf) == tile_offsets_pos
    for v in tile_offsets:
        buf += struct.pack("<I", v)
    for v in tile_byte_counts:
        buf += struct.pack("<I", v)
    for blob in blobs:
        buf += blob
    assert len(buf) == cursor
    return bytes(buf)


@contextlib.contextmanager
def temp_tiff(data):
    """Write ``data`` to a temp file, yield its path, delete it on exit."""
    fd, path = tempfile.mkstemp(suffix=".tiff", prefix="osmviews-test-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)
