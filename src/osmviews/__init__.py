# SPDX-FileCopyrightText: 2022 Sascha Brawer <sascha@brawer.ch>
# SPDX-Licence-Identifier: MIT

import array, functools, math, struct, zlib

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
        ifd = {}
        ntags, = self.unpack('H', self.file.read(2))
        for _ in range(ntags):
            tag, typ, count = self.unpack('HHI', self.file.read(8))
            offval = self.file.read(4)
            format = {2:'s', 3:'H', 4:'I', 11:'f', 12:'d'}.get(typ)
            if format is not None:
                size = {2:1, 3:2, 4:4, 11:4, 12:8}[typ] * count
                if size <= 4:
                    format += 'xxxx'[size:]  # padding
                    ifd[tag], = self.unpack(format, offval)
                else:
                    pos = self.file.tell()
                    self.file.seek(self.unpack('I', offval)[0])
                    arr = array.array({'s':'B'}.get(format, format))
                    arr.fromfile(self.file, count)
                    if format == 's':
                        arr = arr.tobytes().decode('utf-8')
                    ifd[tag] = arr
                    self.file.seek(pos)
        self.__tile_offsets, self.__tile_sizes = ifd[324], ifd[325]
        self.__imageWidth, self.__imageLength = ifd[256], ifd[257]
        self.__tileWidth, self.__tileLength = ifd[322], ifd[323]
        self.__tilesAcross = (self.__imageWidth + self.__tileWidth - 1) // self.__tileWidth
        self.__zoom = int.bit_length(self.__imageWidth - 1)
        self.__shift = int.bit_length(self.__tileWidth - 1)
        self.__mask = (1 << self.__shift) - 1

    def close(self):
        self.file.close()

    def rank(self, lat, lng):
        if lat <= -85.051129 or lat >= 85.051129:
            return 0.0
        lat_rad = math.radians(lat)
        n = 1 << self.__zoom
        x = int((lng + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        tile_index = ((y >> self.__shift) * self.__tilesAcross +
                      (x >> self.__shift))
        tile = self.__tile(tile_index)
        t_x, t_y = x & self.__mask, y & self.__mask
        return tile[t_y * (1 << self.__shift) + t_x]

    @functools.lru_cache(maxsize=512)
    def __tile(self, t):
        self.file.seek(self.__tile_offsets[t])
        raw_data = self.file.read(self.__tile_sizes[t])
        data = zlib.decompress(raw_data, bufsize=262144)
        pixels = array.array('f')
        pixels.frombytes(data)
        return pixels

    def __enter__(self):
        return self

    def __exit__(self, _etype, _eval, _traceback):
        self.close()
