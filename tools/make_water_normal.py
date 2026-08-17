"""A real water normal map.

The old assets/water_n.jpg was 256px with a tilt of about eight percent - at
normalScale 0.55 that is no ripple at all, which is why the water read as a
flat plastic sheet however the shader scrolled it.

This bakes a seamless 512 sheet from layered directional wave trains: long
smooth swells with fine capillary detail on top, calm - his word for the
water is smooth - but strong enough to break the moon's glint into shimmer.
Integer wave vectors keep it tileable.

    python tools/make_water_normal.py
"""
import math
import os
import random

import numpy as np
from PIL import Image

S = 512
rnd = random.Random(7)

x = np.linspace(0, 2 * math.pi, S, endpoint=False)
X, Y = np.meshgrid(x, x)

h = np.zeros((S, S))
# long swells: few cycles across the tile, most of the height
for _ in range(6):
    kx, ky = rnd.randint(-3, 3), rnd.randint(-3, 3)
    if kx == 0 and ky == 0:
        kx = 1
    amp = 1.0 / (abs(kx) + abs(ky))
    h += amp * np.sin(kx * X + ky * Y + rnd.uniform(0, 6.28))
# mid chop
for _ in range(10):
    kx, ky = rnd.randint(-9, 9), rnd.randint(-9, 9)
    if abs(kx) + abs(ky) < 4:
        continue
    h += (0.22 / math.sqrt(abs(kx) + abs(ky))) * np.sin(kx * X + ky * Y + rnd.uniform(0, 6.28))
# capillary sparkle
for _ in range(14):
    kx, ky = rnd.randint(-28, 28), rnd.randint(-28, 28)
    if abs(kx) + abs(ky) < 16:
        continue
    h += (0.05) * np.sin(kx * X + ky * Y + rnd.uniform(0, 6.28))

h /= np.percentile(np.abs(h), 96)   # robust: peaks may clip, the body must move

# gradients (wrapped), then the normal
gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
STR = 26.0                     # slope strength: visible shimmer, still calm
nx, ny = -gx * STR, -gy * STR
nz = np.ones_like(h)
ln = np.sqrt(nx * nx + ny * ny + nz * nz)
nx, ny, nz = nx / ln, ny / ln, nz / ln

img = np.stack([
    ((nx * 0.5 + 0.5) * 255),
    ((ny * 0.5 + 0.5) * 255),
    ((nz * 0.5 + 0.5) * 255)
], axis=-1).astype(np.uint8)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "water_n.jpg")
Image.fromarray(img).save(out, quality=95)
a = img.astype(float)
print("wrote %s  %dpx  R std %.1f  G std %.1f (old was ~10)" % (
    out, S, a[..., 0].std(), a[..., 1].std()))
