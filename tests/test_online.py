# SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

"""Test against the real ~594 MB OSMViews dataset.

Skipped by default.  Provide the file via the ``OSMVIEWS_TIFF`` environment
variable or by dropping ``osmviews.tiff`` in the repository root, then::

    OSMVIEWS_TIFF=$PWD/osmviews.tiff uv run --with pytest pytest -k online

Assertions check only relative order and coarse thresholds, never absolute
values: the dataset is regenerated weekly and drifts.
"""

import datetime
import math
import os

import pytest

import osmviews

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


def _dataset_path():
    from_env = os.environ.get("OSMVIEWS_TIFF")
    if from_env and os.path.isfile(from_env):
        return from_env
    in_repo = os.path.join(_REPO_ROOT, "osmviews.tiff")
    return in_repo if os.path.isfile(in_repo) else None


pytestmark = pytest.mark.skipif(
    _dataset_path() is None,
    reason="needs the ~594 MB osmviews.tiff (set OSMVIEWS_TIFF or drop it in the repo root)",
)


def test_ranks_reflect_how_the_planet_is_viewed():
    with osmviews.open(_dataset_path()) as o:
        rank = o.rank

        # (lng, lat)
        london_centre = rank(-0.1281, 51.5080)  # Trafalgar Square
        london_inner = rank(-0.0553, 51.5452)  # Hackney
        london_outer = rank(0.1730, 51.6217)  # Havering-atte-Bower
        bern_centre = rank(7.4474, 46.9480)
        ushuaia = rank(-68.3030, -54.8019)

        # Cross-region ordering of city centres.
        assert london_centre > bern_centre > ushuaia

        # The dataset's ~150 m resolution resolves the fall-off across one city.
        assert london_centre > london_inner > london_outer

        # Remote / empty places: well below any inhabited point, but not
        # necessarily exactly zero, and not ordered against each other.
        for name, value in [
            ("Sahara", rank(13.0, 23.0)),
            ("remote S Pacific", rank(-140.0, -30.0)),
            ("Birdsville", rank(139.3508, -25.8975)),
        ]:
            assert value < 0.1, f"{name} = {value}"
            assert value < ushuaia, (
                f"{name} = {value}, expected below Ushuaia {ushuaia}"
            )

        # Poles and non-finite inputs.
        assert rank(0.0, 90.0) == 0.0
        assert rank(0.0, -90.0) == 0.0
        assert rank(math.nan, 0.0) == 0.0

        m = o.metrics()
        assert m.out_of_range == 3  # the two poles + the NaN
        assert m.tiles_decoded >= 1


def test_exposes_a_plausible_last_tile_log_day():
    with osmviews.open(_dataset_path()) as o:
        horizon = datetime.date.today() + datetime.timedelta(days=14)
        assert datetime.date(2020, 1, 1) <= o.date <= horizon
