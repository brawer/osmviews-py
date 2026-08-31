# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""Tests for the WGS84 -> pixel projection, mirroring the Rust crate's
``src/projection.rs`` tests."""

import math

import pytest

from osmviews._projection import project

SIZE = 262_144


def _reference(lng, lat, size):
    """Independent reference implementation of the slippy-tile northing, written
    the "textbook" way with ``ln(tan + sec)`` instead of ``asinh(tan)``."""
    lat_rad = math.radians(lat)
    x = (lng + 180.0) / 360.0 * size
    y = (
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * size
    )
    return (math.floor(x), math.floor(y))


def test_null_island_is_the_centre_pixel():
    assert project(0.0, 0.0, SIZE) == (SIZE // 2, SIZE // 2)


def test_antimeridian_is_the_left_edge():
    assert project(-180.0, 0.0, SIZE)[0] == 0
    assert project(180.0, 0.0, SIZE)[0] == 0
    assert project(-540.0, 0.0, SIZE)[0] == 0


@pytest.mark.parametrize("lng", [-178.0, 0.0, 90.0, 179.9])
def test_longitude_wraps_around_the_globe(lng):
    assert project(lng, 20.0, SIZE) == project(lng + 360.0, 20.0, SIZE)
    assert project(lng, 20.0, SIZE) == project(lng - 360.0, 20.0, SIZE)


def test_182_east_is_178_west():
    assert project(182.0, 0.0, SIZE) == project(-178.0, 0.0, SIZE)


@pytest.mark.parametrize(
    "lng,lat",
    [
        (0.0, 85.06),
        (0.0, -85.06),
        (0.0, 90.0),
        (0.0, -90.0),
        (math.nan, 0.0),
        (0.0, math.inf),
    ],
)
def test_out_of_range_latitudes_and_non_finite_inputs(lng, lat):
    assert project(lng, lat, SIZE) is None


@pytest.mark.parametrize(
    "name,lat,lng,expected",
    [
        ("Tokyo", 35.6586, 139.7016, (232_799, 103_246)),
        ("New York", 40.7128, -74.0060, (77_182, 98_561)),
        ("Sydney", -33.8688, 151.2093, (241_179, 157_310)),
        ("Buenos Aires", -34.6037, -58.3816, (88_559, 157_957)),
    ],
)
def test_matches_reference_in_every_quadrant(name, lat, lng, expected):
    assert project(lng, lat, SIZE) == expected, name
    assert _reference(lng, lat, SIZE) == expected, f"{name} (reference)"
