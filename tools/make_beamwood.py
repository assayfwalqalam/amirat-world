# Bakes the pale, sun-bleached timber used for roof beams, ladders, porch
# posts and window frames.  ->  assets/t_beam_d.jpg
#
# Why this exists: t_wood_d.jpg means (80,67,59) while the wall stone means
# (174,154,131).  A beam wearing it reads black against the wall, like an iron
# spike.  In the reference the projecting beams are bleached timber, a little
# darker than the wall and never black.  Vertex colour and baseColorFactor can
# only DARKEN a texture in glTF, so the light has to be baked in here.
import math, os, random, sys
from PIL import Image, ImageFilter

SIZE = 512
KIND = sys.argv[1] if len(sys.argv) > 1 else "beam"
# beam: bleached roof timber. prop: the barrels, carts, stalls and shutters,
# a little darker and warmer but still light enough to read by moonlight.
BASE = (160, 140, 115) if KIND == "beam" else (116, 90, 66)
OUT = os.path.join(os.path.dirname(__file__), "..", "assets",
                   "t_beam_d.jpg" if KIND == "beam" else "t_woodp_d.jpg")
random.seed(41 if KIND == "beam" else 77)

im = Image.new("RGB", (SIZE, SIZE), BASE)
px = im.load()

# the grain runs down the image; each stripe is a fibre with its own tone
stripe = [0.0] * SIZE
x = 0
while x < SIZE:
    w = random.randint(2, 9)
    t = random.uniform(-16, 12) * (1.0 if KIND == "beam" else 1.7)
    for i in range(w):
        if x + i < SIZE:
            stripe[x + i] = t
    x += w

for y in range(SIZE):
    # a slow drift along the length, so a long pole is not one flat tone
    drift = 7.0 * math.sin(y / SIZE * math.pi * 2) + 4.0 * math.sin(y / SIZE * math.pi * 6)
    for xx in range(SIZE):
        v = stripe[xx] + drift + random.uniform(-4.5, 4.5)
        # fine cross-grain checks, as weathered wood splits
        if random.random() < 0.004:
            v -= random.uniform(10, 26)
        r = max(0, min(255, int(BASE[0] + v)))
        g = max(0, min(255, int(BASE[1] + v * 0.94)))
        b = max(0, min(255, int(BASE[2] + v * 0.86)))
        px[xx, y] = (r, g, b)

# knots: a dark eye with the grain bending round it
for _ in range(7):
    kx = random.randint(0, SIZE - 1)
    ky = random.randint(0, SIZE - 1)
    kr = random.uniform(5, 13)
    for dy in range(int(-kr * 2.4), int(kr * 2.4) + 1):
        for dx in range(int(-kr * 1.6), int(kr * 1.6) + 1):
            d = math.hypot(dx / 1.6, dy / 2.4)
            if d > kr:
                continue
            xx = (kx + dx) % SIZE
            yy = (ky + dy) % SIZE
            f = 1.0 - d / kr
            r, g, b = px[xx, yy]
            k = 1.0 - 0.45 * f * f
            px[xx, yy] = (int(r * k), int(g * k), int(b * k))

im = im.filter(ImageFilter.SMOOTH)
im.save(OUT, quality=93)

from PIL import ImageStat
s = ImageStat.Stat(im)
print("WROTE", os.path.abspath(OUT), "mean", [round(v) for v in s.mean],
      "std", [round(v) for v in s.stddev])
