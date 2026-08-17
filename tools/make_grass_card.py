"""The grass card, drawn as grass.

The old assets/grass_card.png was a scatter of small olive dots. Sown by the
hundred thousand it read as gravel or woodchips, never as a meadow, and no
amount of making the cards bigger could fix a texture that has no blades in
it. This draws real blades: tapered, curved, leaning, dark at the root and
light at the tip, with a few dry straws among the green.

Supersampled 4x and reduced, so the alpha edge is clean instead of jagged.

    python tools/make_grass_card.py
"""
import math
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
S = 512
SS = 4                      # supersample factor


def blade(dr, x0, y0, height, lean, w0, green, dry):
    """One blade: a tapered curve from root to tip, drawn as a quad strip."""
    # a blade bends: mostly upright at the root, falling away near the tip
    steps = 16
    pts_l, pts_r = [], []
    for i in range(steps + 1):
        t = i / float(steps)
        # quadratic lean, so the base stands and the tip curls over
        x = x0 + lean * t * t
        y = y0 - height * (t - 0.10 * t * t)
        w = w0 * (1.0 - t) ** 0.75
        # the blade's own direction, so width is perpendicular to it
        dx = lean * 2.0 * t
        dy = -height * (1.0 - 0.20 * t)
        n = math.hypot(dx, dy) or 1.0
        px, py = -dy / n, dx / n
        pts_l.append((x + px * w, y + py * w))
        pts_r.append((x - px * w, y - py * w))
    poly = pts_l + pts_r[::-1]
    # root dark, tip light: two passes, the upper half lighter
    dr.polygon(poly, fill=dry if random.random() < 0.22 else green)
    # the lit upper third
    cut = int(steps * 0.55)
    upper = pts_l[cut:] + pts_r[cut:][::-1]
    lift = tuple(min(255, int(c * 1.28)) for c in (dry if random.random() < 0.22 else green)[:3]) + (255,)
    if len(upper) >= 3:
        dr.polygon(upper, fill=lift)


def sheet(path, n_blades, hmin, hmax, seed):
    random.seed(seed)
    im = Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    W = S * SS
    for _ in range(n_blades):
        x0 = random.uniform(W * 0.04, W * 0.96)
        # blades rise from a shallow band, not from one line
        y0 = W - random.uniform(0, W * 0.05)
        height = W * random.uniform(hmin, hmax)
        lean = random.uniform(-0.42, 0.42) * height
        w0 = W * random.uniform(0.006, 0.013)
        g = random.uniform(0.0, 1.0)
        green = (int(52 + 46 * g), int(74 + 62 * g), int(34 + 34 * g), 255)
        dry = (int(126 + 38 * g), int(112 + 34 * g), int(58 + 26 * g), 255)
        blade(dr, x0, y0, height, lean, w0, green, dry)
    im = im.resize((S, S), Image.LANCZOS)
    im.save(path)
    print("%-28s %5dkB" % (os.path.basename(path), os.path.getsize(path) // 1024))


if __name__ == "__main__":
    # the common blade clump, and a taller sparser one for the deep patches
    sheet(os.path.join(A, "grass_card.png"), 150, 0.55, 0.94, 12)
    sheet(os.path.join(A, "grass_card_tall.png"), 96, 0.74, 1.0, 77)
