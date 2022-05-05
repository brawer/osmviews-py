# SPDX-FileCopyrightText: 2022 Sascha Brawer <sascha@brawer.ch>
# SPDX-Licence-Identifier: MIT

import os
import unittest

import osmviews


class TestOSMViews(unittest.TestCase):
    def datapath(self, filename):
        return os.path.join(os.path.dirname(__file__), 'data', filename)

    def test_with(self):
        with osmviews.OSMViews(self.datapath('mini.tiff')) as o:
            self.assertAlmostEqual(o.rank(47.391483, 8.488963), 42.42)

    def test_close(self):
        o = osmviews.OSMViews(self.datapath('mini.tiff'))
        self.assertAlmostEqual(o.rank(47.391483, 8.488963), 42.42)
        o.close()

    def test_wrong_file_format(self):
        with self.assertRaises(ValueError):
            osmviews.OSMViews(self.datapath('hello.txt'))


if __name__ == '__main__':
    unittest.main()
