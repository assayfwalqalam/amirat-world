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


# ------------------------------------------------------------- the bakes
def nebula(name, blobs, core, palette, teal_at, seeds, star_n, detail=1.0):
    """One nebula, painted deep: a lobed mask, domain-warped billows, fine
    curdling, dark lanes, a zoned palette from the given core outward, and
    its own stars burning inside. Every parameter is a design choice, so
    each cloud in the sky is its own place."""
    (s_warp1, s_warp2, s_field, s_fine, s_lane, s_star) = seeds
    mimg = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mimg)
    for (cx, cy, rx, ry) in blobs:
        d.ellipse([S * cx - S * rx, S * cy - S * ry,
                   S * cx + S * rx, S * cy + S * ry], fill=255)
    M = np.asarray(mimg).astype(np.float32) / 255.0
    M = blur(M, 30)

    W1 = fbm(S, seed=s_warp1)
    W2 = fbm(S, seed=s_warp2)
    F = warp(fbm(S, seed=s_field), W1, W2, 100.0)
    FINE = fbm(S, octaves=(48, 96, 192, 384), seed=s_fine)

    body = M * (0.24 + 0.76 * F ** 1.25) * (0.42 + 0.58 * FINE ** (1.0 / detail))

    LANE = warp(fbm(S, octaves=(6, 12, 24, 48), seed=s_lane), W2, W1, 130.0)
    lanes = np.clip((LANE - 0.50) * 4.6, 0, 1) * np.clip((M - 0.1) * 2, 0, 1)
    body *= (1.0 - 0.80 * lanes)

    body *= np.clip((M - 0.06) * 3.2, 0, 1) * 0.7 + 0.3 * np.clip(F - 0.2, 0, 1)
    body = np.clip(body, 0, 1)

    v = blur(body, 1.0)
    yy, xx = np.mgrid[0:S, 0:S]
    dcore = np.sqrt(((xx / S - core[0]) * 1.1) ** 2
                    + ((yy / S - core[1]) * 1.5) ** 2)
    zone = np.clip(dcore / 0.55, 0, 1)

    C_CORE, C_MID, C_FAR, C_RIM, C_POCK = [np.array(c, np.float32)
                                           for c in palette]
    w_core = np.clip(1 - zone * 3.2, 0, 1)
    w_mid = np.clip(1 - np.abs(zone - 0.28) * 3.4, 0, 1)
    w_far = np.clip(1 - np.abs(zone - 0.60) * 3.0, 0, 1)
    w_rim = np.clip((zone - 0.72) * 2.6, 0, 1)
    wsum = np.maximum(w_core + w_mid + w_far + w_rim, 0.35)
    rgb = np.zeros((S, S, 3), np.float32)
    for c in range(3):
        rgb[:, :, c] = (C_CORE[c] * w_core + C_MID[c] * w_mid
                        + C_FAR[c] * w_far + C_RIM[c] * w_rim) / wsum
    tpock = np.exp(-(((xx / S - teal_at[0]) / 0.16) ** 2
                     + ((yy / S - teal_at[1]) / 0.13) ** 2))
    for c in range(3):
        rgb[:, :, c] = rgb[:, :, c] * (1 - 0.55 * tpock) + C_POCK[c] * 0.55 * tpock

    glow = np.exp(-(dcore / 0.20) ** 2)
    lum = np.clip(0.26 + 0.95 * v + 0.65 * glow, 0, 1.7)
    rgb = rgb * lum[:, :, None]

    alpha = np.clip(M * 2.1, 0, 1) * (0.46 + 0.54 * np.clip(v * 1.8, 0, 1))
    alpha = np.clip(alpha + glow * 0.35, 0, 1) * 0.96

    r3 = np.random.default_rng(s_star)
    star_layer = np.zeros((S, S), np.float32)
    starcol = np.zeros((S, S, 3), np.float32)
    TINTS = [(255, 255, 255), (255, 236, 200), (196, 216, 255),
             (255, 208, 228)]
    tries = 0
    placed = 0
    while placed < star_n and tries < 6000:
        tries += 1
        px = int(r3.integers(30, S - 30))
        py = int(r3.integers(30, S - 30))
        if M[py, px] < r3.uniform(0.1, 0.8):
            continue
        tint = TINTS[int(r3.integers(0, len(TINTS)))]
        rr = float(r3.uniform(0.5, 1.4))
        amp = float(r3.uniform(0.5, 1.0))
        lo_y, hi_y = max(0, py - 6), min(S, py + 7)
        lo_x, hi_x = max(0, px - 6), min(S, px + 7)
        sy, sx = np.mgrid[lo_y:hi_y, lo_x:hi_x]
        gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2) / (2 * rr ** 2)))
        star_layer[lo_y:hi_y, lo_x:hi_x] = np.maximum(
            star_layer[lo_y:hi_y, lo_x:hi_x], gg * amp)
        for c in range(3):
            starcol[lo_y:hi_y, lo_x:hi_x, c] = np.maximum(
                starcol[lo_y:hi_y, lo_x:hi_x, c], gg * amp * tint[c])
        placed += 1
    for _ in range(11):
        px = int(r3.integers(80, S - 80))
        py = int(r3.integers(80, S - 80))
        if M[py, px] < 0.25:
            continue
        tint = TINTS[int(r3.integers(0, len(TINTS)))]
        r0 = float(r3.uniform(2.0, 3.4))
        gg = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2)
                      / (2 * (r0 * 1.8) ** 2)))
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

    halo = blur(alpha, 32) * 0.32
    alpha = np.maximum(alpha, halo)

    out = np.dstack([np.clip(rgb, 0, 255),
                     (alpha * 255)[:, :, None]]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, name))
    print("WROTE", name)


# THE MAIN NEBULA: rose heart, blue-violet dust, a teal pocket
nebula("entity_d.png",
       blobs=[(0.60, 0.42, 0.200, 0.150), (0.42, 0.52, 0.180, 0.130),
              (0.26, 0.62, 0.150, 0.110), (0.13, 0.72, 0.110, 0.080),
              (0.74, 0.32, 0.150, 0.110), (0.86, 0.24, 0.110, 0.080),
              (0.52, 0.30, 0.130, 0.100), (0.68, 0.55, 0.130, 0.095)],
       core=(0.60, 0.42),
       palette=[(255, 222, 238), (226, 148, 198), (118, 158, 224),
                (96, 82, 158), (96, 208, 190)],
       teal_at=(0.30, 0.60),
       seeds=(11, 23, 5, 31, 47, 9), star_n=280, detail=1.35)

# THE EMBER NEBULA: the fiery one of his first reference - gold and rust
nebula("nebula_b.png",
       blobs=[(0.50, 0.45, 0.190, 0.160), (0.34, 0.56, 0.150, 0.120),
              (0.66, 0.34, 0.150, 0.120), (0.79, 0.25, 0.100, 0.080),
              (0.44, 0.30, 0.120, 0.100)],
       core=(0.52, 0.44),
       palette=[(255, 236, 205), (244, 176, 108), (196, 104, 74),
                (122, 62, 78), (232, 150, 170)],
       teal_at=(0.68, 0.58),
       seeds=(51, 63, 45, 71, 87, 19), star_n=190, detail=1.35)

# THE JEWEL NEBULA: the vivid one of his second reference - magenta and cyan
nebula("nebula_c.png",
       blobs=[(0.50, 0.46, 0.170, 0.150), (0.38, 0.34, 0.130, 0.110),
              (0.64, 0.58, 0.130, 0.110), (0.58, 0.28, 0.100, 0.085),
              (0.32, 0.58, 0.110, 0.090)],
       core=(0.48, 0.42),
       palette=[(255, 232, 250), (238, 116, 210), (120, 96, 224),
                (70, 66, 150), (98, 224, 235)],
       teal_at=(0.64, 0.34),
       seeds=(91, 103, 85, 111, 127, 29), star_n=170, detail=1.35)


# ===================================================== ONE WHOLE SKY
def skyvista():
    """The whole quarter of sky as ONE painting, wrapped on a curved dome in
    the engine - his ruling: not patches in different spots, one massive sky.
    A night that is purple, pink and sunset-orange near the earth; three
    nebula hearts joined by a single running river of dust; dark lanes;七
    hundred stars. 2048x1024, feathered at every edge so it melts into the
    night around it."""
    W7, H7 = 2048, 1024
    yy, xx = np.mgrid[0:H7, 0:W7]
    u = xx / W7
    v = yy / H7

    # --- the gradient of that sky: violet -> purple -> magenta -> ember
    STOPS = [(0.00, (34, 20, 62)), (0.34, (110, 54, 134)),
             (0.60, (208, 88, 154)), (0.82, (252, 142, 122)),
             (1.00, (255, 198, 122))]
    rgb = np.zeros((H7, W7, 3), np.float32)
    for i in range(len(STOPS) - 1):
        (t0, c0), (t1, c1) = STOPS[i], STOPS[i + 1]
        m = np.clip((v - t0) / (t1 - t0), 0, 1)
        band = ((v >= t0) & (v < t1)) | ((i == len(STOPS) - 2) & (v >= t1))
        for c in range(3):
            val = c0[c] + (c1[c] - c0[c]) * m
            rgb[:, :, c] = np.where(band, val, rgb[:, :, c])

    # --- the river of dust: one band winding through the whole width,
    #     carrying three hearts - rose, jewel, ember - in a single sky
    def sq(size, seed, octs=(8, 16, 32, 64, 128)):
        return fbm(size, octaves=octs, seed=seed)

    def wide(a):
        return np.asarray(Image.fromarray(
            np.clip(a * 255, 0, 255).astype(np.uint8)).resize(
            (W7, H7), Image.BICUBIC)).astype(np.float32) / 255.0

    W1 = wide(sq(1024, 211))
    W2 = wide(sq(1024, 223))
    F = wide(sq(1024, 205))
    ys2, xs2 = np.mgrid[0:H7, 0:W7]
    xs3 = np.clip(xs2 + (W1 - 0.5) * 110, 0, W7 - 1).astype(np.int32)
    ys3 = np.clip(ys2 + (W2 - 0.5) * 110, 0, H7 - 1).astype(np.int32)
    F = F[ys3, xs3]
    FINE = wide(sq(1024, 231, octs=(48, 96, 192, 384)))

    # the band's spine: a slow sine across the sky
    spine = 0.40 + 0.14 * np.sin(u * math.pi * 1.6 + 0.6)
    band = np.exp(-(((v - spine) / 0.16) ** 2))
    # the three hearts swell the band where they sit
    HEARTS = [(0.26, 0.40, (255, 214, 232), (226, 148, 198)),
              (0.55, 0.32, (255, 232, 250), (200, 110, 220)),
              (0.80, 0.46, (255, 236, 205), (238, 160, 100))]
    heart_glow = np.zeros((H7, W7), np.float32)
    heart_col = np.zeros((H7, W7, 3), np.float32)
    for (hx, hy, ccore, cmid) in HEARTS:
        dd = np.sqrt(((u - hx) * 2.0) ** 2 + ((v - hy) * 1.2) ** 2)
        g = np.exp(-(dd / 0.075) ** 2)
        gm = np.exp(-(dd / 0.20) ** 2)
        heart_glow = np.maximum(heart_glow, g + gm * 0.55)
        for c in range(3):
            heart_col[:, :, c] = np.maximum(
                heart_col[:, :, c], g * ccore[c] + gm * 0.55 * cmid[c])

    dust = (band * 1.05 + heart_glow * 1.1) * (0.26 + 0.74 * F ** 1.15)         * (0.30 + 0.70 * FINE ** 1.3)
    LANE = wide(sq(1024, 247, octs=(6, 12, 24, 48)))
    lanes = np.clip((LANE - 0.50) * 4.4, 0, 1) * np.clip(band * 1.6, 0, 1)
    dust *= (1.0 - 0.78 * lanes)
    dust = np.clip(dust, 0, 1)

    # dust colour: violet-blue far, warmed near the hearts
    DUSTC = np.array([168, 136, 232], np.float32)
    for c in range(3):
        rgb[:, :, c] += dust * DUSTC[c] * 0.75
        rgb[:, :, c] += heart_col[:, :, c] * dust * 1.1
        rgb[:, :, c] += heart_col[:, :, c] * 0.55

    # --- stars: seven hundred through the whole sky, denser along the band
    r5 = np.random.default_rng(59)
    stars = np.zeros((H7, W7), np.float32)
    starc = np.zeros((H7, W7, 3), np.float32)
    TINTS = [(255, 255, 255), (255, 238, 205), (200, 218, 255),
             (255, 210, 230)]
    n_placed = 0
    tries = 0
    while n_placed < 700 and tries < 12000:
        tries += 1
        px = int(r5.integers(8, W7 - 8))
        py = int(r5.integers(8, H7 - 8))
        keep = 0.25 + 0.75 * band[py, px]
        if r5.uniform(0, 1) > keep:
            continue
        tint = TINTS[int(r5.integers(0, len(TINTS)))]
        rr = float(r5.uniform(0.4, 1.3))
        amp = float(r5.uniform(0.35, 1.0))
        lo_y, hi_y = max(0, py - 5), min(H7, py + 6)
        lo_x, hi_x = max(0, px - 5), min(W7, px + 6)
        sy, sx = np.mgrid[lo_y:hi_y, lo_x:hi_x]
        gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2) / (2 * rr ** 2)))
        stars[lo_y:hi_y, lo_x:hi_x] = np.maximum(
            stars[lo_y:hi_y, lo_x:hi_x], gg * amp)
        for c in range(3):
            starc[lo_y:hi_y, lo_x:hi_x, c] = np.maximum(
                starc[lo_y:hi_y, lo_x:hi_x, c], gg * amp * tint[c])
        n_placed += 1
    for _ in range(16):
        px = int(r5.integers(60, W7 - 60))
        py = int(r5.integers(40, H7 - 200))
        tint = TINTS[int(r5.integers(0, len(TINTS)))]
        r0 = float(r5.uniform(1.8, 3.2))
        gg = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2)
                      / (2 * (r0 * 1.8) ** 2)))
        fl = (np.exp(-np.abs(xx - px) / (r0 * 6.0))
              * np.exp(-np.abs(yy - py) / (r0 * 0.8))
              + np.exp(-np.abs(yy - py) / (r0 * 6.0))
              * np.exp(-np.abs(xx - px) / (r0 * 0.8))) * 0.6
        st = np.clip(gg + fl, 0, 1)
        stars = np.maximum(stars, st)
        for c in range(3):
            starc[:, :, c] = np.maximum(starc[:, :, c], st * tint[c])
    rgb = rgb + starc * 0.95

    # --- the veil: full through its heart, melting at every edge
    alpha = np.full((H7, W7), 0.93, np.float32)
    env_u = np.clip(np.sin(math.pi * u) * 1.9, 0, 1) ** 0.7
    alpha *= env_u
    alpha *= np.clip(v * 5.2, 0, 1) ** 0.8              # melts at the top
    alpha *= np.clip((1.02 - v) * 8.0, 0, 1)            # and above the ground
    alpha = np.clip(alpha + stars * 0.5 * env_u[:, :], 0, 1)

    out = np.dstack([np.clip(rgb, 0, 255),
                     (alpha * 255)[:, :, None]]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, "skyvista.png"))
    print("WROTE skyvista.png")


skyvista()
