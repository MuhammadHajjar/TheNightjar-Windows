"""Convert Apple's "crushed" iOS PNGs (CgBI chunk, raw deflate, BGRA) to normal PNGs.

    python tools/cgbi.py in.png out.png [max_height]

With max_height the image is written as several files, out_0.png, out_1.png ...
(used to read the text baked into the About / Cast / Credits scroll images).
"""
import struct
import sys
import zlib


def read_cgbi(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, w = 8, b'', None
    cgbi = False
    while pos < len(data):
        ln, typ = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'CgBI':
            cgbi = True
        elif typ == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
        elif typ == b'IDAT':
            idat += body
        pos += 12 + ln
    raw = zlib.decompress(idat, -15 if cgbi else 15)
    bpp = 4
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _y in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out += line
        prev = line
    if cgbi:                                    # BGRA -> RGBA
        for k in range(0, len(out), 4):
            out[k], out[k + 2] = out[k + 2], out[k]
    return w, h, bytes(out)


def write_png(path, w, h, rgba):
    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    rows = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


if __name__ == '__main__':
    w, h, px = read_cgbi(sys.argv[1])
    mh = int(sys.argv[3]) if len(sys.argv) > 3 else h
    base = sys.argv[2][:-4]
    for n, y in enumerate(range(0, h, mh)):
        hh = min(mh, h - y)
        write_png('%s_%d.png' % (base, n) if mh < h else sys.argv[2], w, hh, px[y * w * 4:(y + hh) * w * 4])
    print(w, h)
