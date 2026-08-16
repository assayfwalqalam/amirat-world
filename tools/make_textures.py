"""Bakes the surface textures: adobe, plaster, wood, clay, ashlar, thatch.

The earlier adobe was flattened so hard to cure a blotchy look that it ended up
with almost no structure at all -- a fine standard deviation of under four
levels, which reads as flat cream paint at any distance. The cure for blotchy
is not "featureless": it is detail at the RIGHT scale. Blotchy comes from large
low-frequency blobs; surface comes from fine grain, aggregate, tool marks and
courses. So these have plenty of the second and none of the first.

    python tools/make_textures.py
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
S = 1024


def noise_img(size, scale, octaves=4, seed=0):
    """Value noise built by upsampling, cheap and seamless enough at this size."""
    rnd = random.Random(seed)
    acc = Image.new("F", (size, size), 0.0)
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        n = max(2, int(size / (scale / (2 ** o))))
        small = Image.new("L", (n, n))
        small.putdata([rnd.randrange(256) for _ in range(n * n)])
        # wrap by tiling one row/col so the upscale stays seamless
        big = small.resize((size, size), Image.BICUBIC).convert("F")
        acc = Image.eval(acc, lambda v: v)  # no-op, keeps type
        acc = Image.merge("F", (acc,)).split()[0]
        acc = Image.blend(acc, big, amp / (amp + total) if (amp + total) else 1.0)
        total += amp
        amp *= 0.55
    return acc


def to_L(f, lo=0, hi=255):
    px = f.load()
    w, h = f.size
    out = Image.new("L", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            op[x, y] = max(0, min(255, int(v)))
    return out


def grain(size, amount, seed):
    rnd = random.Random(seed)
    g = Image.new("L", (size, size))
    g.putdata([128 + int(rnd.gauss(0, amount)) for _ in range(size * size)])
    return g


def tint(gray, rgb, contrast=1.0, base=1.0):
    """Turn a grey height/detail map into a coloured surface."""
    px = gray.load()
    w, h = gray.size
    im = Image.new("RGB", (w, h))
    ip = im.load()
    for y in range(h):
        for x in range(w):
            v = base + (px[x, y] - 128) / 128.0 * contrast
            ip[x, y] = (max(0, min(255, int(rgb[0] * v))),
                        max(0, min(255, int(rgb[1] * v))),
                        max(0, min(255, int(rgb[2] * v))))
    return im


def adobe():
    """Mud plaster over brick: fine aggregate, trowel strokes, faint courses."""
    base = grain(S, 24, 11).filter(ImageFilter.GaussianBlur(0.4))
    d = ImageDraw.Draw(base)
    rnd = random.Random(4)
    # Aggregate. The tile covers about 1.7 m of wall, so a two-pixel chip is
    # three millimetres across and invisible from anywhere. Real grit in a mud
    # render is 5-40 mm, which at this scale is 3-24 pixels.
    # Mud render is mostly smooth with grit showing here and there. Too much
    # of it and the wall reads as exposed-aggregate concrete.
    for _ in range(1300):
        x, y = rnd.randrange(S), rnd.randrange(S)
        r = rnd.choice((2, 2, 3, 3, 4))             # 3-7 mm of grit
        v = 128 + rnd.choice((-26, -19, -13, 15, 21, 27))
        d.ellipse([x - r, y - r, x + r, y + r], fill=v)
    for _ in range(14000):         # sand in the render, fine and even
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.point((x, y), fill=128 + rnd.choice((-18, -12, 13, 19)))
    # trowel strokes: long, shallow, and wide enough to see
    for _ in range(150):
        y = rnd.randrange(S)
        x0 = rnd.randrange(-100, S)
        ln = rnd.randrange(160, 620)
        sag = rnd.uniform(-14, 14)
        th = rnd.randrange(3, 9)
        v = 128 + rnd.choice((-15, -10, 11, 16))
        for i in range(ln):
            xx = (x0 + i) % S
            yy = int(y + math.sin(i / ln * math.pi) * sag) % S
            for t in range(th):
                d.point((xx, (yy + t) % S), fill=v)
    # Brick courses showing through the render. A course is about 150 mm, so
    # roughly 90 pixels here, and the joint has to be several pixels wide or it
    # disappears into the grain.
    ch = 96
    for row in range(0, S + ch, ch):
        off = (row // ch % 2) * 92
        for i in range(0, S):
            yy = (row + int(math.sin(i * 0.011 + row) * 4)) % S
            for t in range(4):
                d.point((i, (yy + t) % S), fill=104 + t * 9)
            d.point((i, (yy + 5) % S), fill=150)
        for bx in range(0, S, 184):
            xx = (bx + off) % S
            for j in range(ch):
                for t in range(4):
                    d.point(((xx + t) % S, (row + j) % S), fill=106 + t * 8)
    for _ in range(70):            # hairline cracks wandering down the render
        x, y = rnd.randrange(S), rnd.randrange(S)
        a = rnd.uniform(1.0, 2.2)
        for _ in range(rnd.randrange(50, 260)):
            a += rnd.uniform(-0.30, 0.30)
            x = (x + math.cos(a)) % S
            y = (y + math.sin(a)) % S
            d.point((int(x), int(y)), fill=96)
            if rnd.random() < 0.4:
                d.point((int(x) + 1, int(y)), fill=112)
    im = tint(base, (198, 165, 123), contrast=0.56, base=1.0)
    return im


def plaster():
    base = grain(S, 18, 21).filter(ImageFilter.GaussianBlur(0.5))
    d = ImageDraw.Draw(base)
    rnd = random.Random(9)
    for _ in range(16000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        r = rnd.choice((0, 0, 1))
        d.ellipse([x - r, y - r, x + r, y + r], fill=128 + rnd.choice((-40, -28, 30, 42)))
    # hairline cracks
    for _ in range(90):
        x, y = rnd.randrange(S), rnd.randrange(S)
        a = rnd.uniform(0, 6.283)
        for _ in range(rnd.randrange(30, 160)):
            a += rnd.uniform(-0.35, 0.35)
            x = (x + math.cos(a)) % S
            y = (y + math.sin(a)) % S
            d.point((int(x), int(y)), fill=104)
    return tint(base, (216, 199, 170), contrast=0.5)


def wood():
    """Timber: long grain, growth rings, the odd knot."""
    im = Image.new("L", (S, S), 128)
    d = ImageDraw.Draw(im)
    rnd = random.Random(31)
    # grain running the length
    for y in range(S):
        wander = math.sin(y * 0.013) * 9 + math.sin(y * 0.041) * 4
        for x in range(0, S, 1):
            v = 128
            v += math.sin((x + wander) * 0.031) * 20
            v += math.sin((x + wander) * 0.0092) * 12
            v += rnd.gauss(0, 14)
            im.putpixel((x, y), max(0, min(255, int(v))))
    # knots
    for _ in range(7):
        kx, ky = rnd.randrange(S), rnd.randrange(S)
        kr = rnd.randrange(14, 34)
        for r in range(kr, 0, -1):
            v = 92 + int(28 * (r / kr))
            d.ellipse([kx - r, ky - int(r * 0.7), kx + r, ky + int(r * 0.7)], outline=v)
    # splits along the grain
    for _ in range(60):
        y = rnd.randrange(S)
        x0 = rnd.randrange(S)
        for i in range(rnd.randrange(40, 260)):
            d.point(((x0 + i) % S, (y + int(math.sin(i * 0.02) * 2)) % S), fill=100)
    return tint(im, (112, 80, 52), contrast=0.7)


def clay():
    """Fired earthenware: throwing rings, a little bloom from the kiln."""
    im = Image.new("L", (S, S), 128)
    rnd = random.Random(57)
    for y in range(S):
        ring = math.sin(y * 0.42) * 7 + math.sin(y * 0.13) * 4
        for x in range(S):
            v = 128 + ring * 1.6 + rnd.gauss(0, 11)
            im.putpixel((x, y), max(0, min(255, int(v))))
    d = ImageDraw.Draw(im)
    for _ in range(9000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.point((x, y), fill=128 + rnd.choice((-44, -30, 32, 46)))
    # kiln bloom: broad soft patches, kept gentle so it never reads as blotch
    bloom = Image.new("L", (S // 8, S // 8))
    bloom.putdata([128 + int(rnd.gauss(0, 16)) for _ in range((S // 8) ** 2)])
    bloom = bloom.resize((S, S), Image.BICUBIC).filter(ImageFilter.GaussianBlur(12))
    im = Image.blend(im, bloom, 0.22)
    return tint(im, (172, 108, 70), contrast=0.55)


def ashlar():
    """Cut stone: courses of blocks with recessed joints and pitted faces."""
    base = grain(S, 20, 77).filter(ImageFilter.GaussianBlur(0.4))
    d = ImageDraw.Draw(base)
    rnd = random.Random(88)
    # stone is pitted, not spotted: small shallow marks only
    for _ in range(7000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        r = rnd.choice((1, 1, 2, 2, 3))
        d.ellipse([x - r, y - r, x + r, y + r], fill=128 + rnd.choice((-26, -18, 18, 26)))
    for _ in range(9000):
        x, y = rnd.randrange(S), rnd.randrange(S)
        d.point((x, y), fill=128 + rnd.choice((-22, -15, 16, 24)))
    ch = 128
    for row in range(0, S, ch):
        off = (row // ch % 2) * 96
        for t in range(3):
            d.line([(0, row + t), (S, row + t)], fill=96 + t * 10)
        for bx in range(0, S, 192):
            xx = (bx + off) % S
            for t in range(3):
                d.line([(xx + t, row), (xx + t, row + ch)], fill=96 + t * 10)
        # a shallow chamfer along the top of each course
        for t in range(4, 9):
            d.line([(0, row + t), (S, row + t)], fill=150 - t * 3)
    return tint(base, (200, 184, 157), contrast=0.6)


def cloth():
    """Woven cloth for awnings and tents: warp and weft, a little sag."""
    im = Image.new("L", (S, S), 128)
    rnd = random.Random(123)
    for y in range(S):
        for x in range(S):
            v = 128
            v += 10 if (x // 3) % 2 == 0 else -10
            v += 8 if (y // 3) % 2 == 0 else -8
            v += rnd.gauss(0, 9)
            im.putpixel((x, y), max(0, min(255, int(v))))
    return tint(im, (190, 168, 132), contrast=0.45)


JOBS = [
    ("t_adobe_d.jpg", adobe),
    ("t_plaster_d.jpg", plaster),
    ("t_wood_d.jpg", wood),
    ("t_clay_d.jpg", clay),
    ("t_ashlar_d.jpg", ashlar),
    ("t_cloth_d.jpg", cloth),
]

if __name__ == "__main__":
    for name, fn in JOBS:
        im = fn()
        path = os.path.join(OUT, name)
        im.save(path, quality=94)
        g = im.convert("L")
        px = list(g.getdata())
        mean = sum(px) / len(px)
        var = sum((v - mean) ** 2 for v in px) / len(px)
        sm = g.resize((16, 16))
        vals = list(sm.getdata())
        print("%-18s mean %3.0f  fine sd %4.1f  block spread %3d"
              % (name, mean, var ** 0.5, max(vals) - min(vals)))
