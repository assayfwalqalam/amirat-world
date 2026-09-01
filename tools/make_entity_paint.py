# -*- coding: utf-8 -*-
# THE NEBULA over the edge of the field:
#   python tools/make_entity_paint.py  ->  assets/entity_d.png
#
# His final ruling replaced the dust-being with a MASSIVE NEBULA, and the
# sky of that region dressed to match - stars, sparkles, planets. This is
# the nebula itself: a broad diagonal band of curdled dust, a hot rose core
# going blue then violet at the rim, dark lanes cut across it, and its own
# stars burning inside the cloud. Painted as a matte - the same craft as
# the reference imagery - with every element placed deliberately.
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
S = 1024


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


# ------------------------------------------------------------- the cloud
# a broad band running lower-left to upper-right, its heart right of centre
mimg = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(mimg)


def blob(cx, cy, rx, ry):
    d.ellipse([S * cx - S * rx, S * cy - S * ry,
               S * cx + S * rx, S * cy + S * ry], fill=255)


CORE = (0.60, 0.42)
blob(0.60, 0.42, 0.200, 0.150)      # the heart
blob(0.42, 0.52, 0.180, 0.130)
blob(0.26, 0.62, 0.150, 0.110)      # the band falling to the lower-left
blob(0.13, 0.72, 0.110, 0.080)
blob(0.74, 0.32, 0.150, 0.110)      # the band rising to the upper-right
blob(0.86, 0.24, 0.110, 0.080)
blob(0.52, 0.30, 0.130, 0.100)      # a shoulder of dust above the heart
blob(0.68, 0.55, 0.130, 0.095)      # and one below

M = np.asarray(mimg).astype(np.float32) / 255.0
M = blur(M, 30)

# ------------------------------------------------------------- the dust
W1 = fbm(S, seed=11)
W2 = fbm(S, seed=23)
F = warp(fbm(S, seed=5), W1, W2, 100.0)          # curdled billows
FINE = fbm(S, octaves=(64, 128, 256), seed=31)

body = M * (0.28 + 0.72 * F ** 1.25) * (0.60 + 0.40 * FINE)

# DARK LANES: cold dust cut across the bright heart, like the real ones
LANE = warp(fbm(S, octaves=(6, 12, 24), seed=47), W2, W1, 130.0)
lanes = np.clip((LANE - 0.52) * 4.0, 0, 1) * np.clip((M - 0.1) * 2, 0, 1)
body *= (1.0 - 0.72 * lanes)

# the rim wisps away
body *= np.clip((M - 0.06) * 3.2, 0, 1) * 0.7 + 0.3 * np.clip(F - 0.2, 0, 1)
body = np.clip(body, 0, 1)

# ------------------------------------------------------------- the colour
v = blur(body, 1.2)
yy, xx = np.mgrid[0:S, 0:S]
dcore = np.sqrt(((xx / S - CORE[0]) * 1.1) ** 2
                + ((yy / S - CORE[1]) * 1.5) ** 2)
zone = np.clip(dcore / 0.55, 0, 1)               # 0 at the heart, 1 far out

# heart: hot rose-white; mid: magenta-rose to blue; rim: deep violet;
# and a teal pocket breathing in from the lower-left
C_CORE = np.array([255, 222, 238], np.float32)
C_ROSE = np.array([226, 148, 198], np.float32)
C_BLUE = np.array([118, 158, 224], np.float32)
C_VIOL = np.array([96, 82, 158], np.float32)
C_TEAL = np.array([96, 208, 190], np.float32)

w_core = np.clip(1 - zone * 3.2, 0, 1)
w_rose = np.clip(1 - np.abs(zone - 0.28) * 3.4, 0, 1)
w_blue = np.clip(1 - np.abs(zone - 0.60) * 3.0, 0, 1)
w_viol = np.clip((zone - 0.72) * 2.6, 0, 1)
wsum = np.maximum(w_core + w_rose + w_blue + w_viol, 0.35)
rgb = np.zeros((S, S, 3), np.float32)
for c in range(3):
    rgb[:, :, c] = (C_CORE[c] * w_core + C_ROSE[c] * w_rose
                    + C_BLUE[c] * w_blue + C_VIOL[c] * w_viol) / wsum
# the teal pocket
tpock = np.exp(-(((xx / S - 0.30) / 0.16) ** 2 + ((yy / S - 0.60) / 0.13) ** 2))
for c in range(3):
    rgb[:, :, c] = rgb[:, :, c] * (1 - 0.55 * tpock) + C_TEAL[c] * 0.55 * tpock

# the dust carries the light: brightness from the filaments, lit heart
glow = np.exp(-(dcore / 0.20) ** 2)
lum = np.clip(0.30 + 0.85 * v + 0.65 * glow, 0, 1.6)
rgb = rgb * lum[:, :, None]

alpha = np.clip(M * 2.1, 0, 1) * (0.52 + 0.48 * np.clip(v * 1.7, 0, 1))
alpha = np.clip(alpha + glow * 0.35, 0, 1) * 0.96

# ------------------------------------------------------- its own stars
r3 = np.random.default_rng(9)
star_layer = np.zeros((S, S), np.float32)
starcol = np.zeros((S, S, 3), np.float32)
TINTS = [(255, 255, 255), (255, 236, 200), (196, 216, 255), (255, 208, 228)]
tries = 0
placed = 0
while placed < 240 and tries < 4000:
    tries += 1
    px = int(r3.integers(40, S - 40))
    py = int(r3.integers(40, S - 40))
    if M[py, px] < r3.uniform(0.1, 0.8):
        continue
    tint = TINTS[int(r3.integers(0, len(TINTS)))]
    rr = float(r3.uniform(0.5, 1.4))
    lo_y, hi_y = max(0, py - 6), min(S, py + 7)
    lo_x, hi_x = max(0, px - 6), min(S, px + 7)
    sy, sx = np.mgrid[lo_y:hi_y, lo_x:hi_x]
    gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2) / (2 * rr ** 2)))
    amp = float(r3.uniform(0.5, 1.0))
    star_layer[lo_y:hi_y, lo_x:hi_x] = np.maximum(
        star_layer[lo_y:hi_y, lo_x:hi_x], gg * amp)
    for c in range(3):
        starcol[lo_y:hi_y, lo_x:hi_x, c] = np.maximum(
            starcol[lo_y:hi_y, lo_x:hi_x, c], gg * amp * tint[c])
    placed += 1
for _ in range(9):                                   # the bright ones, flared
    px = int(r3.integers(80, S - 80))
    py = int(r3.integers(80, S - 80))
    if M[py, px] < 0.25:
        continue
    tint = TINTS[int(r3.integers(0, len(TINTS)))]
    r0 = float(r3.uniform(2.0, 3.4))
    gg = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2 * (r0 * 1.8) ** 2)))
    fl = (np.exp(-np.abs(xx - px) / (r0 * 5.5))
          * np.exp(-np.abs(yy - py) / (r0 * 0.8))
          + np.exp(-np.abs(yy - py) / (r0 * 5.5))
          * np.exp(-np.abs(xx - px) / (r0 * 0.8))) * 0.6
    st = np.clip(gg + fl, 0, 1)
    star_layer = np.maximum(star_layer, st)
    for c in range(3):
        starcol[:, :, c] = np.maximum(starcol[:, :, c], st * tint[c])

rgb = np.clip(rgb + starcol * 0.9, 0, 255)
alpha = np.clip(alpha + star_layer * 0.9, 0, 1)

# the halo of scattered light
halo = blur(alpha, 32) * 0.32
alpha = np.maximum(alpha, halo)

out = np.dstack([np.clip(rgb, 0, 255),
                 (alpha * 255)[:, :, None]]).astype(np.uint8)
Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, "entity_d.png"))
print("WROTE entity_d.png (nebula)")
