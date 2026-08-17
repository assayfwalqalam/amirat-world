"""Blossom sheets for the flowering giants.

A canopy card carrying open five-petal blossoms among small leaves, so a tree
built from these reads as a mass of bloom rather than green. Four colours, and
two sheets of each so a stand is not made of one repeated stamp.

Supersampled 4x and reduced, for a clean alpha edge.

    python tools/make_blossom_card.py
"""
import math
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets", "src")
S = 512
SS = 4

# petal, petal centre-shade, heart, and the leaf green that goes with it
COLOURS = {
    "pink":    ((246, 168, 198), (232, 126, 168), (250, 226, 150), (86, 116, 62)),
    "white":   ((248, 244, 240), (226, 216, 216), (244, 214, 128), (78, 108, 58)),
    "magenta": ((214, 96, 158), (186, 62, 130), (248, 224, 148), (74, 100, 54)),
    "amber":   ((246, 198, 108), (228, 166, 74), (232, 118, 66), (92, 112, 58)),
}


def petal_flower(dr, cx, cy, r, petal, shade, heart, tilt):
    """One open blossom: five rounded petals round a small heart."""
    n = 5
    for i in range(n):
        a = tilt + i * (6.283 / n)
        px = cx + math.cos(a) * r * 0.62
        py = cy + math.sin(a) * r * 0.62 * 0.88
        rr = r * random.uniform(0.46, 0.56)
        col = petal if (i % 2 == 0) else shade
        dr.ellipse([px - rr, py - rr * 0.92, px + rr, py + rr * 0.92], fill=col + (255,))
    hr = r * 0.20
    dr.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=heart + (255,))


def leaf(dr, x, y, ln, ang, w, col):
    pts = []
    steps = 8
    for i in range(steps + 1):
        t = i / float(steps)
        px = x + math.cos(ang) * ln * t
        py = y + math.sin(ang) * ln * t
        ww = w * math.sin(math.pi * t)
        pts.append((px + math.cos(ang + 1.57) * ww, py + math.sin(ang + 1.57) * ww))
    for i in range(steps, -1, -1):
        t = i / float(steps)
        px = x + math.cos(ang) * ln * t
        py = y + math.sin(ang) * ln * t
        ww = w * math.sin(math.pi * t)
        pts.append((px - math.cos(ang + 1.57) * ww, py - math.sin(ang + 1.57) * ww))
    dr.polygon(pts, fill=col + (255,))


def sheet(path, key, seed):
    petal, shade, heart, green = COLOURS[key]
    random.seed(seed)
    W = S * SS
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)

    # a few twigs first, so the bloom has something to sit on
    for _ in range(9):
        x0 = random.uniform(0, W)
        y0 = random.uniform(W * 0.55, W)
        a = random.uniform(-2.5, -0.7)
        ln = W * random.uniform(0.3, 0.6)
        dr.line([x0, y0, x0 + math.cos(a) * ln, y0 + math.sin(a) * ln],
                fill=(96, 74, 60, 255), width=int(W * 0.006))

    for _ in range(46):
        x = random.uniform(W * 0.05, W * 0.95)
        y = random.uniform(W * 0.05, W * 0.95)
        leaf(dr, x, y, W * random.uniform(0.05, 0.10), random.uniform(0, 6.283),
             W * random.uniform(0.010, 0.019),
             tuple(min(255, int(c * random.uniform(0.82, 1.18))) for c in green))

    for _ in range(34):
        x = random.uniform(W * 0.06, W * 0.94)
        y = random.uniform(W * 0.06, W * 0.94)
        r = W * random.uniform(0.045, 0.085)
        j = random.uniform(0.86, 1.12)
        petal_flower(dr, x, y, r,
                     tuple(min(255, int(c * j)) for c in petal),
                     tuple(min(255, int(c * j)) for c in shade),
                     heart, random.uniform(0, 6.283))

    im = im.resize((S, S), Image.LANCZOS)
    im.save(path)
    print("%-30s %5dkB" % (os.path.basename(path), os.path.getsize(path) // 1024))


if __name__ == "__main__":
    os.makedirs(A, exist_ok=True)
    for i, key in enumerate(COLOURS):
        for v in (1, 2):
            sheet(os.path.join(A, "blossom_%s_%d.png" % (key, v)), key, 100 + i * 17 + v)
