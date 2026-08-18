# Bakes the surfaces the war assets wear. Until now every vehicle and weapon
# was a flat colour with no texture at all, which is why they read as toys
# beside the photographs.
#   python tools/make_wartex.py
#
# -> assets/t_paintsand.jpg   CARC desert paint, chalky, dusty, scuffed
#    assets/t_paintolive.jpg  British olive drab
#    assets/t_rubber.jpg      tyre rubber, fine grain and mould marks
#    assets/t_gunsteel.jpg    parkerised steel, brushed with wear
#    assets/t_gunwood.jpg     AK furniture, orange-red laminate
#    assets/t_canvas.jpg      the tilt over a Land Rover's back
import math, os, random

from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
SIZE = 512


def base(color, grain, seed):
    random.seed(seed)
    im = Image.new("RGB", (SIZE, SIZE), color)
    px = im.load()
    for y in range(SIZE):
        for x in range(SIZE):
            v = random.uniform(-grain, grain)
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, int(r + v))),
                        max(0, min(255, int(g + v))),
                        max(0, min(255, int(b + v))))
    return im


def blotches(im, n, rad, amount, seed):
    """Slow drift of tone, the way paint fades unevenly in the sun."""
    random.seed(seed)
    d = Image.new("L", (SIZE, SIZE), 128)
    dd = ImageDraw.Draw(d)
    for _ in range(n):
        x, y = random.randint(0, SIZE), random.randint(0, SIZE)
        r = random.uniform(rad * 0.5, rad)
        v = 128 + random.uniform(-amount, amount)
        dd.ellipse([x - r, y - r, x + r, y + r], fill=int(v))
    d = d.filter(ImageFilter.GaussianBlur(rad * 0.55))
    px, dpx = im.load(), d.load()
    for y in range(SIZE):
        for x in range(SIZE):
            k = dpx[x, y] / 128.0
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, int(r * k))),
                        max(0, min(255, int(g * k))),
                        max(0, min(255, int(b * k))))
    return im


def scratches(im, n, light, seed, length=60):
    """Edge wear: short bright scars where paint has been rubbed through."""
    random.seed(seed)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = random.randint(0, SIZE), random.randint(0, SIZE)
        a = random.uniform(0, math.pi * 2)
        L = random.uniform(length * 0.3, length)
        w = random.choice([1, 1, 1, 2])
        v = int(light + random.uniform(-14, 14))
        d.line([x, y, x + math.cos(a) * L, y + math.sin(a) * L],
               fill=(v, v, int(v * 0.96)), width=w)
    return im


def streaks(im, n, dark, seed):
    """Dust and rain running down a vertical panel."""
    random.seed(seed)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x = random.randint(0, SIZE)
        y0 = random.randint(0, SIZE // 2)
        h = random.randint(SIZE // 6, SIZE // 2)
        w = random.choice([2, 3, 5, 8])
        v = int(dark + random.uniform(-10, 10))
        d.rectangle([x, y0, x + w, y0 + h], fill=(v, v, v))
    return im.filter(ImageFilter.GaussianBlur(1.6))


def save(im, name):
    im = im.filter(ImageFilter.SMOOTH)
    p = os.path.abspath(os.path.join(OUT, name))
    im.save(p, quality=92)
    from PIL import ImageStat
    s = ImageStat.Stat(im)
    print("WROTE", name, "mean", [round(v) for v in s.mean],
          "std", [round(v) for v in s.stddev])


# ---- desert paint: chalky sand, sun-faded in patches, scuffed at the edges
im = base((166, 150, 118), 3, 11)
im = blotches(im, 18, 130, 7, 12)
im = streaks(im, 12, 154, 13)
im = scratches(im, 26, 178, 14, 30)
im = blotches(im, 30, 30, 4, 15)
save(im, "t_paintsand.jpg")

# ---- olive drab: the British green, greyer and darker
im = base((92, 96, 74), 3, 21)
im = blotches(im, 18, 130, 7, 22)
im = streaks(im, 12, 84, 23)
im = scratches(im, 24, 112, 24, 28)
im = blotches(im, 30, 30, 4, 25)
save(im, "t_paintolive.jpg")

# ---- tyre rubber: nearly black, fine grain, faint mould flash
im = base((44, 44, 46), 4, 31)
im = blotches(im, 18, 90, 10, 32)
random.seed(33)
d = ImageDraw.Draw(im)
for i in range(70):
    y = random.randint(0, SIZE)
    d.line([0, y, SIZE, y + random.randint(-3, 3)], fill=(54, 54, 56), width=1)
save(im, "t_rubber.jpg")

# ---- parkerised steel: dark grey, brushed, worn bright on the high points
im = base((72, 73, 76), 4, 41)
random.seed(42)
d = ImageDraw.Draw(im)
for i in range(240):
    y = random.randint(0, SIZE)
    v = random.randint(60, 96)
    d.line([0, y, SIZE, y + random.randint(-2, 2)], fill=(v, v, v + 2), width=1)
im = blotches(im, 20, 80, 12, 43)
im = scratches(im, 60, 132, 44, 40)
save(im, "t_gunsteel.jpg")

# ---- AK furniture: orange-red laminate with a hard grain
im = base((124, 62, 30), 5, 51)
random.seed(52)
d = ImageDraw.Draw(im)
x = 0
while x < SIZE:
    w = random.randint(4, 18)
    v = random.uniform(-11, 9)
    d.rectangle([x, 0, x + w, SIZE],
                fill=(max(0, min(255, int(124 + v))),
                      max(0, min(255, int(62 + v * 0.8))),
                      max(0, min(255, int(30 + v * 0.6)))))
    x += w
im = blotches(im, 14, 90, 12, 53)
im = im.filter(ImageFilter.GaussianBlur(0.6))
save(im, "t_gunwood.jpg")

# ---- canvas tilt: coarse woven cloth, sun-bleached
im = base((150, 140, 112), 4, 61)
random.seed(62)
d = ImageDraw.Draw(im)
for i in range(0, SIZE, 3):
    d.line([i, 0, i, SIZE], fill=(158, 148, 119), width=1)
    d.line([0, i, SIZE, i], fill=(142, 133, 106), width=1)
im = blotches(im, 22, 100, 13, 63)
im = streaks(im, 26, 128, 64)
save(im, "t_canvas.jpg")

# ---- concrete: grey aggregate, form-board lines, rain stains
im = base((136, 134, 130), 4, 71)
random.seed(72)
d = ImageDraw.Draw(im)
for i in range(0, SIZE, 64):                      # the shutter boards
    d.line([0, i, SIZE, i], fill=(126, 124, 121), width=2)
for _ in range(900):                              # aggregate showing through
    x, y = random.randint(0, SIZE), random.randint(0, SIZE)
    r = random.uniform(0.7, 2.4)
    v = random.randint(112, 158)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, v - 2))
im = blotches(im, 20, 110, 9, 73)
im = streaks(im, 16, 118, 74)
save(im, "t_concrete.jpg")
