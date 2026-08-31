# -*- coding: utf-8 -*-
# THE ENTITY, painted the way the reference itself was made - as a matte:
#   python tools/make_entity_paint.py  ->  assets/entity_d.png
#
# The volumetric route (make_entity_tex.py) was tried three times: eight
# minutes a render, and the noise either fused the mass into pudding or tore
# it into bands. A matte gives exact control of the one thing that matters
# here - the SILHOUETTE: a hunched upper body, head lowered toward the
# watcher, the cowled back rising above it, a dust trail streaming away -
# filled with warped nebula filaments so it only faintly resembles a being.
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
S = 1024
rng = np.random.default_rng(77)


def fbm(size, octaves=(8, 16, 32, 64, 128), seed=1):
    r2 = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in octaves:
        g = r2.normal(0, 1, (o, o)).astype(np.float32)
        gi = np.asarray(Image.fromarray(g).resize((size, size),
                                                  Image.BICUBIC))
        out += gi * amp
        tot += amp
        amp *= 0.55
    out /= tot
    out = (out - out.min()) / (np.ptp(out) + 1e-6)
    return out


def warp(field, wx, wy, amt):
    ys, xs = np.mgrid[0:S, 0:S]
    xs2 = np.clip(xs + (wx - 0.5) * amt, 0, S - 1).astype(np.int32)
    ys2 = np.clip(ys + (wy - 0.5) * amt, 0, S - 1).astype(np.int32)
    return field[ys2, xs2]


def blur(a, r):
    return np.asarray(Image.fromarray(
        np.clip(a * 255, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0


# ---------------------------------------------------------------- the mask
# Image space: the being faces RIGHT (toward the far light and the watcher).
mimg = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(mimg)


def blob(cx, cy, rx, ry, v=255):
    d.ellipse([S * cx - S * rx, S * cy - S * ry,
               S * cx + S * rx, S * cy + S * ry], fill=v)


blob(0.640, 0.400, 0.075, 0.088)     # the head, lowered, forward
blob(0.560, 0.330, 0.105, 0.095)     # the cowl behind it
blob(0.440, 0.300, 0.130, 0.115)     # the hunched back, ABOVE the head line
blob(0.330, 0.345, 0.130, 0.110)     # the back mass
blob(0.220, 0.420, 0.115, 0.090)     # the trail
blob(0.130, 0.490, 0.085, 0.062)     # the trail thinning
blob(0.600, 0.520, 0.105, 0.110)     # the chest under the head
blob(0.620, 0.665, 0.085, 0.075)     # the near arm, folded under
blob(0.480, 0.520, 0.130, 0.120)     # the core
blob(0.390, 0.640, 0.120, 0.105)     # the lower drift
blob(0.500, 0.760, 0.110, 0.095)     # the fade-out below

M = np.asarray(mimg).astype(np.float32) / 255.0
M = blur(M, 26)

# a vertical fade: the being dissolves downward into the sky
ys = np.linspace(0, 1, S)[:, None]
M *= np.clip(1.35 - 1.3 * np.clip((ys - 0.55) / 0.38, 0, 1), 0, 1)

# ------------------------------------------------------------- the nebula
W1 = fbm(S, seed=11)
W2 = fbm(S, seed=23)
F = fbm(S, seed=5)
F = warp(F, W1, W2, 90.0)                       # curdled filaments
FINE = fbm(S, octaves=(64, 128, 256), seed=31)

body = M * (0.30 + 0.70 * F ** 1.35) * (0.55 + 0.45 * FINE)

# directional drift: the dust streams up-left, like the reference
drift = body
for (dx, dy, w) in ((-3, -1, 0.55), (-7, -3, 0.32), (-12, -5, 0.20)):
    drift = np.maximum(drift, np.roll(np.roll(body, dy, 0), dx, 1) * w)
body = np.clip(drift, 0, 1)

# the edges break into wisps: eat the rim with noise
rim = np.clip((M - 0.12) * 3.0, 0, 1)
body *= np.clip(rim + 0.55 * (F - 0.35), 0, 1)
body = np.clip(body, 0, 1)

# ------------------------------------------------------- light and colour
# The reference is nearly monochrome and lives on CONTRAST: a mass dark as
# the sky it hangs in, rim-lit on the side that faces the horizon glow.
v = blur(body, 1.2)
interior = blur(M, 34)
# rim: edges that face down-right, where the world's glow comes from
Msoft = blur(M, 8)
rim = np.clip(np.roll(np.roll(Msoft, 6, 0), 8, 1) - Msoft, 0, 1)
rim = blur(rim * (0.4 + 0.6 * F), 3) * 3.2
# the body value: dark in the core, filament texture carrying the light
# PALE, not dark: against this world's luminous night sky a dark mass
# vanishes. The morning-moon look he named is bright mist - the being is
# LIGHTER than the sky, its structure carried by the filaments and hollow.
val = 0.30 + v * (0.95 - 0.30 * interior) + np.clip(rim, 0, 1) * 0.55
val = np.clip(val, 0, 1)

# the cowl's shadow: a hollow of darkness where the face would be, so the
# two stars burn out of a cavity - the reference's exact read
yyh, xxh = np.mgrid[0:S, 0:S]
hollow = np.exp(-(((xxh - S * 0.648) / (S * 0.062)) ** 2
                  + ((yyh - S * 0.408) / (S * 0.048)) ** 2))
val = np.clip(val * (1.0 - 0.60 * hollow), 0, 1)

rgb = np.zeros((S, S, 3), np.float32)
base = np.array([104, 114, 152], np.float32)
high = np.array([228, 236, 254], np.float32)
viol = np.array([140, 118, 188], np.float32)
for c in range(3):
    rgb[:, :, c] = base[c] + (high[c] - base[c]) * (val ** 1.05)
mid = np.clip(1.0 - np.abs(val - 0.40) * 3.4, 0, 1) * 0.16
for c in range(3):
    rgb[:, :, c] = rgb[:, :, c] * (1 - mid) + viol[c] * mid

# alpha: a DENSE core, wisping only at the rim - even the dark parts stand
# against the stars, exactly like the reference mass
# the core is SOLID: the morning moon is misty at its edge, never through
# its heart - at mean alpha 0.45 the whole being was fog
alpha = np.clip(M * 2.3, 0, 1) * (0.66 + 0.34 * np.clip(v * 1.8, 0, 1))
alpha = np.clip(alpha, 0, 1) * 0.97

# the two points of light - stars where eyes would be, nothing more
for (ex, ey, r0, s0) in ((0.615, 0.402, 3.2, 1.0), (0.665, 0.408, 2.8, 0.9)):
    yy, xx = np.mgrid[0:S, 0:S]
    dd = ((xx - S * ex) ** 2 + (yy - S * ey) ** 2)
    g = np.exp(-dd / (2 * (r0 * 2.2) ** 2)) * s0
    flare = (np.exp(-np.abs(xx - S * ex) / (r0 * 5.0))
             * np.exp(-np.abs(yy - S * ey) / (r0 * 0.9)) * 0.5
             + np.exp(-np.abs(yy - S * ey) / (r0 * 5.0))
             * np.exp(-np.abs(xx - S * ex) / (r0 * 0.9)) * 0.5) * s0 * 0.55
    star = np.clip(g + flare, 0, 1)
    for c in range(3):
        rgb[:, :, c] = np.clip(rgb[:, :, c] + star * 235, 0, 255)
    alpha = np.clip(alpha + star * 0.9, 0, 1)

# the halo of its own scattered dust
halo = blur(alpha, 30) * 0.30
alpha = np.maximum(alpha, halo)

out = np.dstack([np.clip(rgb, 0, 255),
                 (alpha * 255)[:, :, None]]).astype(np.uint8)
Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, "entity_d.png"))
print("WROTE entity_d.png (matte)")
