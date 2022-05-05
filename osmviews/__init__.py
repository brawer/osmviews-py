# SPDX-FileCopyrightText: 2022 Sascha Brawer <sascha@brawer.ch>
# SPDX-Licence-Identifier: MIT

import struct

class OSMViews(object):
    def __init__(self, path):
        self.file = open(path, 'rb')
        magic = self.file.read(4)
        if magic == b'II*\0':
            bigendian = False
            self.unpack = lambda format, data: struct.unpack('<'+format, data)
        elif magic == b'MM\0*':
            bigendian = True
            self.unpack = lambda format, data: struct.unpack('>'+format, data)
        else:
            self.file.close()
            raise ValueError('unrecognized file format: %s' % path)
        offset, = self.unpack('I', self.file.read(4))
        self.file.seek(offset)

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, _etype, _eval, _traceback):
        self.close()

    def rank(self, lat, lng):
        return 42.42
