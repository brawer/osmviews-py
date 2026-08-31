# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""WGS84 longitude/latitude -> pixel coordinate in the OSMViews raster.

The OSMViews GeoTIFF is stored in Web Mercator (EPSG:3857) and its pixel grid
lines up exactly with the standard "slippy map" tile scheme at the zoom level
whose world width in pixels equals the raster width.  So the mapping is the
well-known slippy-tile math, done once here in a few lines rather than pulling in
a projection library.
"""

import math

#: The latitude beyond which Web Mercator is not defined.  Locations at or past
#: this latitude (in either hemisphere) have no data.
MAX_LAT = 85.05112877980659


def project(lng: float, lat: float, size: int) -> tuple[int, int] | None:
    """Map ``lng``/``lat`` (WGS84 degrees) to an ``(x, y)`` pixel in a
    ``size`` x ``size`` raster that spans the whole Web Mercator world square.

    Longitude is treated as periodic, so ``182.0`` is the same meridian as
    ``-178.0``.  Returns ``None`` when the inputs are not finite or the latitude
    is outside the Web Mercator range.
    """
    if not math.isfinite(lng) or not math.isfinite(lat) or abs(lat) >= MAX_LAT:
        return None
    x = ((lng + 180.0) % 360.0) / 360.0 * size
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * size
    hi = size - 1
    return (
        min(max(math.floor(x), 0), hi),
        min(max(math.floor(y), 0), hi),
    )
