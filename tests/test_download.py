# SPDX-FileCopyrightText: 2022 Sascha Brawer <sascha@brawer.ch>
# SPDX-Licence-Identifier: MIT

import io
import json
import os, os.path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

import osmviews


class TestDownload(unittest.TestCase):

    @patch('urllib.request.urlopen')
    def test_download(self, mock_urlopen):
        cm = MagicMock()
        cm.read.side_effect = [b'some', b'data', None]
        cm.headers.get.side_effect = {'ETag':'E', 'Last-Modified': 'L'}.get
        cm.__enter__.return_value = cm
        mock_urlopen.return_value = cm
        with tempfile.TemporaryDirectory() as dir:
            tiff_path = os.path.join(dir, 'osmviews.tiff')
            osmviews.download(tiff_path)
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_method(), 'GET')
            with open(tiff_path, 'r') as tiff_file:
                self.assertEqual(tiff_file.read(), 'somedata')
            with open(os.path.join(dir, 'osmviews.json'), 'r') as json_file:
                self.assertEqual(json.load(json_file),
                                 {'ETag': 'E', 'Last-Modified': 'L'})

    @patch('urllib.request.urlopen')
    def test_not_modified(self, mock_urlopen):
        with tempfile.TemporaryDirectory() as dir:
            tiff_path = os.path.join(dir, 'notmod.tiff')
            with open(tiff_path, 'w') as f:
                f.write('Cached file content')
            json_path = os.path.join(dir, 'notmod.json')
            with open(json_path, 'w') as f:
                f.write(json.dumps({
                    'ETag': '"1d229271928d3f9e2bb0375bd6ce5db6c6d348d9"',
                    'Last-Modified': 'Tue, 10 May 2022 10:28:59 GMT',
                    'Unused-Attribute': [10, 22]
                }))
            err = HTTPError('url', 304, 'Not Modified', {}, None)
            mock_urlopen.side_effect = err
            osmviews.download(tiff_path)
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_method(), 'GET')
            self.assertEqual(req.headers, {
                'If-modified-since': 'Tue, 10 May 2022 10:28:59 GMT',
                'If-none-match': '"1d229271928d3f9e2bb0375bd6ce5db6c6d348d9"'
            })
            with open(tiff_path, 'r') as f:
                self.assertEqual(f.read(), 'Cached file content')


if __name__ == '__main__':
    unittest.main()
