# SPDX-FileCopyrightText: 2022 Sascha Brawer <sascha@brawer.ch>
# SPDX-Licence-Identifier: MIT

import os
import unittest

import osmviews


class TestOSMViews(unittest.TestCase):
    def datapath(self, filename):
        return os.path.join(os.path.dirname(__file__), 'data', filename)

    def test_rank(self):
        # Our test file only has data (at very low resolution) around Zurich.
        # We want to get the same values like the gdallocation tool from GDAL:
        # $ gdallocationinfo -xml -wgs84 mini.tiff 7.587757 47.558131
        with osmviews.open(self.datapath('mini.tiff')) as o:
            self.assertAlmostEqual(o.rank(-54.80735, -68.307313), 0.0)
            self.assertAlmostEqual(o.rank(0, 0), 0.0)
            self.assertAlmostEqual(o.rank(47.391483, 8.488963), 1140.70043945)
            self.assertAlmostEqual(o.rank(47.558131, 7.587757), 46.4292183)
            self.assertAlmostEqual(o.rank(-90.0, 0), 0.0)  # South Pole
            self.assertAlmostEqual(o.rank(+90.0, 0), 0.0)  # North Pole

    def test_open_wrong_file_format(self):
        with self.assertRaises(ValueError):
            osmviews.open(self.datapath('hello.txt'))


if __name__ == '__main__':
    unittest.main()
