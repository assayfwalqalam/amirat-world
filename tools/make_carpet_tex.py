# Bakes the carpet the palace lays on its floors.
#   python tools/make_carpet_tex.py   ->  assets/t_carpet_d.jpg
#
# The runner was wearing t_door_d - the panelled, studded, arched DOOR sheet -
# so the great hall had a row of doors lying down its middle. This is a carpet:
# a deep madder ground, a framed border, and a field of small repeated
# medallions. No creatures, no faces: the pattern is geometry and leaf only.
import math, os, random

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "t_carpet_d.jpg")
random.seed(19)

GROUND = (104, 30, 28)
BORDER = (30, 46, 58)
GOLD = (176, 142, 68)
CREAM = (198, 178, 140)

im = Image.new("RGB", (SIZE, SIZE), GROUND)
d = ImageDraw.Draw(im)

# the weave: fine vertical warp showing through the pile
px = im.load()
for y in range(SIZE):
    for x in range(SIZE):
        v = random.uniform(-7, 7) + (4 if (x % 3 == 0) else 0)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, int(r + v))),
                    max(0, min(255, int(g + v))),
                    max(0, min(255, int(b + v))))

# the border: two guard stripes and a wide band of running leaf
B = 54
d.rectangle([0, 0, SIZE - 1, B], fill=BORDER)
d.rectangle([0, SIZE - 1 - B, SIZE - 1, SIZE - 1], fill=BORDER)
d.rectangle([0, 0, B, SIZE - 1], fill=BORDER)
d.rectangle([SIZE - 1 - B, 0, SIZE - 1, SIZE - 1], fill=BORDER)
for off in (B - 8, SIZE - B + 8):
    d.line([0, off, SIZE, off], fill=GOLD, width=3)
    d.line([off, 0, off, SIZE], fill=GOLD, width=3)

# running leaf along the border band
for t in range(0, SIZE, 34):
    for (cx, cy) in ((t + 17, B // 2), (t + 17, SIZE - B // 2), (B // 2, t + 17), (SIZE - B // 2, t + 17)):
        d.ellipse([cx - 9, cy - 6, cx + 9, cy + 6], outline=GOLD, width=2)
        d.line([cx - 12, cy, cx + 12, cy], fill=CREAM, width=1)

# the field: a grid of medallions, each an eight-point star in a lobed frame
STEP = 96
for gy in range(B + STEP // 2, SIZE - B, STEP):
    for gx in range(B + STEP // 2, SIZE - B, STEP):
        R = 30
        for k in range(8):
            a0 = k * math.pi / 4
            a1 = a0 + math.pi / 4
            d.line([gx + math.cos(a0) * R, gy + math.sin(a0) * R,
                    gx + math.cos(a1) * R * 0.42, gy + math.sin(a1) * R * 0.42],
                   fill=GOLD, width=2)
            d.line([gx + math.cos(a1) * R * 0.42, gy + math.sin(a1) * R * 0.42,
                    gx + math.cos(a1) * R, gy + math.sin(a1) * R],
                   fill=GOLD, width=2)
        d.ellipse([gx - 9, gy - 9, gx + 9, gy + 9], outline=CREAM, width=2)
        d.ellipse([gx - 3, gy - 3, gx + 3, gy + 3], fill=GOLD)
        # the little corner leaves between medallions
        for (ox, oy) in ((-STEP // 2, -STEP // 2), (STEP // 2, -STEP // 2)):
            lx, ly = gx + ox, gy + oy
            if B < lx < SIZE - B and B < ly < SIZE - B:
                d.ellipse([lx - 7, ly - 4, lx + 7, ly + 4], outline=CREAM, width=1)

im = im.filter(ImageFilter.SMOOTH)
im.save(OUT, quality=93)
from PIL import ImageStat
print("WROTE", os.path.abspath(OUT), "mean", [round(v) for v in ImageStat.Stat(im).mean])
