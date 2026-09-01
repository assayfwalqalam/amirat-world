# -*- coding: utf-8 -*-
# The entity's post pass, and the rest of its sky:
#   python tools/make_entity_post.py
#     assets/entity_raw.png -> assets/entity_d.png   (tint, mist, halo)
#     -> assets/aurora_g.png, assets/aurora_p.png    (the curtains)
#     -> assets/meteor.png                           (the falling stars)
#
# The morning-moon look he named: light-blueish, misty, contrast held DOWN -
# a thing so far away the air in between washes it out.
import math
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")


def entity():
    im = Image.open(os.path.join(ASSETS, "entity_raw.png")).convert("RGBA")
    im = im.resize((1024, 1024), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    rgb, alp = a[:, :, :3], a[:, :, 3]

    # the misty wash: lift the blacks, hold the highs, lean blue with a
    # breath of violet in the mids
    v = rgb.mean(axis=2, keepdims=True) / 255.0
    rgb = rgb * 0.72 + 255.0 * 0.28 * v ** 0.5   # soft-contrast
    rgb[:, :, 0] = rgb[:, :, 0] * 0.88 + 14 * (v[:, :, 0] ** 1.5) * 4
    rgb[:, :, 1] = rgb[:, :, 1] * 0.94
    rgb[:, :, 2] = np.clip(rgb[:, :, 2] * 1.10 + 8, 0, 255)

    # translucency of distance: the whole thing slightly see-through
    alp = alp * 0.88

    # the halo: the being's own dust scattered wide
    halo = Image.fromarray(alp.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(26))
    halo_a = np.asarray(halo).astype(np.float32) * 0.30
    alp = np.clip(np.maximum(alp, halo_a), 0, 255)
    hrgb = np.zeros_like(rgb)
    hrgb[:, :, 0] = 120; hrgb[:, :, 1] = 138; hrgb[:, :, 2] = 190
    only_halo = (halo_a > alp * 0.98)[:, :, None]
    rgb = np.where(only_halo, hrgb, rgb)

    out = np.dstack([np.clip(rgb, 0, 255), alp[:, :, None]]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, "entity_d.png"))
    print("WROTE entity_d.png")


def aurora(name, col):
    W2, H2 = 384, 768
    rng = np.random.default_rng(sum(ord(c) for c in name))
    # ray columns: a 1-D noise across, smoothed, each column a curtain ray
    cols = rng.normal(0, 1, W2 // 3)
    cols = np.interp(np.linspace(0, len(cols) - 1, W2),
                     np.arange(len(cols)), cols)
    cols = (cols - cols.min()) / (np.ptp(cols) + 1e-6)
    cols = 0.25 + 0.75 * cols ** 1.6
    y = np.linspace(0, 1, H2)[:, None]
    # an aurora is sharpest at its lower rim and breathes away upward
    prof = np.clip((y - 0.08) / 0.14, 0, 1) * np.clip((1.0 - y) / 0.55, 0, 1) ** 1.4
    alp = (prof * cols[None, :] * 255 * 0.85)
    # feather every edge - a curtain with a visible rectangle is a billboard,
    # and the seams read instantly against the stars
    xs = np.linspace(0, 1, W2)[None, :]
    alp = alp * np.clip(np.sin(math.pi * xs) ** 0.55, 0, 1)
    img = np.zeros((H2, W2, 4), np.uint8)
    for c in range(3):
        img[:, :, c] = col[c]
    img[:, :, 3] = np.clip(alp, 0, 255).astype(np.uint8)
    out = Image.fromarray(img, "RGBA").filter(ImageFilter.GaussianBlur(2.2))
    out.save(os.path.join(ASSETS, name))
    print("WROTE", name)


def meteor():
    W3, H3 = 128, 16
    x = np.linspace(0, 1, W3)[None, :]
    y = np.abs(np.linspace(-1, 1, H3))[:, None]
    body = np.clip((x ** 3.2) * (1.0 - y ** 2), 0, 1)
    img = np.zeros((H3, W3, 4), np.uint8)
    img[:, :, 0] = 235; img[:, :, 1] = 240; img[:, :, 2] = 255
    img[:, :, 3] = (body * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(ASSETS, "meteor.png"))
    print("WROTE meteor.png")


def cluster():
    """A sheet of loose stars and sparkles for the nebula's region - two of
    these at different depths, counter-phased in opacity, make the sky there
    shimmer without a single extra draw call per star."""
    W4 = 768
    rng = np.random.default_rng(15)
    img = np.zeros((W4, W4, 4), np.float32)
    TINTS = [(255, 255, 255), (255, 238, 205), (200, 218, 255),
             (255, 210, 230), (205, 255, 230)]
    yy, xx = np.mgrid[0:W4, 0:W4]
    for i in range(170):
        px, py = rng.integers(30, W4 - 30, 2)
        tint = TINTS[int(rng.integers(0, len(TINTS)))]
        rr = float(rng.uniform(0.6, 2.2))
        amp = float(rng.uniform(0.35, 1.0))
        lo_y, hi_y = max(0, py - 10), min(W4, py + 11)
        lo_x, hi_x = max(0, px - 10), min(W4, px + 11)
        sy, sx = np.mgrid[lo_y:hi_y, lo_x:hi_x]
        gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2) / (2 * rr ** 2))) * amp
        for c in range(3):
            img[lo_y:hi_y, lo_x:hi_x, c] = np.maximum(
                img[lo_y:hi_y, lo_x:hi_x, c], gg * tint[c])
        img[lo_y:hi_y, lo_x:hi_x, 3] = np.maximum(
            img[lo_y:hi_y, lo_x:hi_x, 3], gg * 255)
    for i in range(12):                      # a few big sparkles, cross-flared
        px, py = rng.integers(60, W4 - 60, 2)
        tint = TINTS[int(rng.integers(0, len(TINTS)))]
        r0 = float(rng.uniform(1.8, 3.0))
        gg = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2 * (r0 * 1.8) ** 2)))
        fl = (np.exp(-np.abs(xx - px) / (r0 * 6.0))
              * np.exp(-np.abs(yy - py) / (r0 * 0.8))
              + np.exp(-np.abs(yy - py) / (r0 * 6.0))
              * np.exp(-np.abs(xx - px) / (r0 * 0.8))) * 0.65
        st = np.clip(gg + fl, 0, 1)
        for c in range(3):
            img[:, :, c] = np.maximum(img[:, :, c], st * tint[c])
        img[:, :, 3] = np.maximum(img[:, :, 3], st * 255)
    # feather the sheet edges so no rectangle ever shows
    ex = np.sin(math.pi * np.linspace(0, 1, W4))[None, :] ** 0.5
    ey = np.sin(math.pi * np.linspace(0, 1, W4))[:, None] ** 0.5
    img[:, :, 3] *= ex * ey
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA").save(
        os.path.join(ASSETS, "cluster.png"))
    print("WROTE cluster.png")


def planet(name, radius_px, base, band, ring=None, seed=3):
    """One far planet: a lit disc with soft latitude bands, misty with
    distance; optionally a thin ring. Light falls from the upper-left."""
    W5 = 256
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:W5, 0:W5]
    cx = cy = W5 / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disc = np.clip((radius_px - r) / 2.2, 0, 1)
    # lambert light from upper-left, with a soft terminator
    nx = (xx - cx) / radius_px
    ny = (yy - cy) / radius_px
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    lit = np.clip(nx * -0.5 + ny * -0.35 + nz * 0.85, 0.06, 1)
    # latitude bands, gently warped
    wob = np.sin(yy / W5 * math.pi * rng.uniform(5, 8)
                 + np.sin(xx / W5 * 6.0) * 0.7) * 0.5 + 0.5
    img = np.zeros((W5, W5, 4), np.float32)
    for c in range(3):
        col = base[c] * (1 - 0.4 * wob) + band[c] * (0.4 * wob)
        img[:, :, c] = col * lit
    img[:, :, 3] = disc * 235                        # slightly translucent: far
    if ring:
        # a thin ellipse ring round the disc, in front below, behind above
        ang = -0.5
        rx2 = (xx - cx) * math.cos(ang) - (yy - cy) * math.sin(ang)
        ry2 = ((xx - cx) * math.sin(ang) + (yy - cy) * math.cos(ang)) * 3.4
        rr2 = np.sqrt(rx2 ** 2 + ry2 ** 2)
        band_m = np.exp(-((rr2 - radius_px * 1.55) / 5.5) ** 2)
        behind = (yy < cy) & (r < radius_px)
        band_m[behind] = 0
        for c in range(3):
            img[:, :, c] = np.maximum(img[:, :, c], band_m * ring[c])
        img[:, :, 3] = np.maximum(img[:, :, 3], band_m * 200)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA")
    out = out.filter(ImageFilter.GaussianBlur(0.8))
    out.save(os.path.join(ASSETS, name))
    print("WROTE", name)


def planet_big():
    """THE GREAT WORLD of his references: a planet that dominates its part
    of the sky - big, detailed, crescent-lit from the horizon glow, its dark
    limb melting into the night. Continents from layered noise, a polar cap,
    limb darkening, and a thin atmosphere rim so it reads as a WORLD in
    space, not a balloon in the air."""
    W6 = 512
    rng = np.random.default_rng(21)
    yy, xx = np.mgrid[0:W6, 0:W6]
    cx = cy = W6 / 2
    R = 225.0
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disc = np.clip((R - r) / 1.6, 0, 1)
    nx = (xx - cx) / R
    ny = (yy - cy) / R
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    # the sun is low to the lower-left, where the world's horizon glow sits
    lit = np.clip(nx * -0.62 + ny * 0.46 + nz * 0.30, 0.0, 1.0) ** 0.8
    # continents: layered value noise, thresholded softly
    n = np.zeros((W6, W6), np.float32)
    amp, tot = 1.0, 0.0
    for o in (8, 16, 32, 64, 128):
        g = rng.normal(0, 1, (o, o)).astype(np.float32)
        gi = np.asarray(Image.fromarray(g).resize((W6, W6), Image.BICUBIC))
        n += gi * amp; tot += amp; amp *= 0.55
    n = (n - n.min()) / (np.ptp(n) + 1e-6)
    land = np.clip((n - 0.52) * 6.0, 0, 1)
    SEA = np.array([84, 108, 146], np.float32)
    LAND = np.array([168, 158, 138], np.float32)
    ICE = np.array([228, 234, 240], np.float32)
    img = np.zeros((W6, W6, 4), np.float32)
    for c in range(3):
        img[:, :, c] = SEA[c] * (1 - land) + LAND[c] * land
    cap = np.clip((np.abs(ny) - 0.72) * 5.0, 0, 1) * (nz > 0)
    for c in range(3):
        img[:, :, c] = img[:, :, c] * (1 - cap) + ICE[c] * cap
    # clouds: bright wisps of their own noise
    cl = np.zeros((W6, W6), np.float32)
    amp = 1.0
    for o in (12, 24, 48, 96):
        g = rng.normal(0, 1, (o, o)).astype(np.float32)
        gi = np.asarray(Image.fromarray(g).resize((W6, W6), Image.BICUBIC))
        cl += gi * amp; amp *= 0.5
    cl = np.clip((cl - cl.mean()) / (cl.std() + 1e-6) * 0.5 + 0.2, 0, 1) * 0.65
    for c in range(3):
        img[:, :, c] = img[:, :, c] * (1 - cl) + 235 * cl
    # light, limb darkening, and the crescent shadow
    limb = np.clip(nz, 0, 1) ** 0.35
    shade_f = np.clip(lit * 1.15 + 0.045, 0, 1) * limb
    for c in range(3):
        img[:, :, c] *= shade_f
    img[:, :, 3] = disc * 255
    # the atmosphere rim: a thin lit haze past the limb, strongest sunward
    rim = np.exp(-((r - R) / 7.0) ** 2) * (r > R * 0.97)
    rimlit = np.clip(nx * -0.62 + ny * 0.46 + 0.45, 0.1, 1)
    RIMC = np.array([170, 200, 255], np.float32)
    for c in range(3):
        img[:, :, c] = np.maximum(img[:, :, c], rim * rimlit * RIMC[c])
    img[:, :, 3] = np.maximum(img[:, :, 3], rim * rimlit * 210)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA")
    out = out.filter(ImageFilter.GaussianBlur(0.7))
    out.save(os.path.join(ASSETS, "planet_big.png"))
    print("WROTE planet_big.png")


if __name__ == "__main__":
    # entity() is retired: the nebula matte (make_entity_paint.py) owns
    # entity_d.png now - running the old post pass here would overwrite it
    aurora("aurora_g.png", (96, 235, 152))
    aurora("aurora_p.png", (172, 116, 240))
    meteor()
    cluster()
    planet("planet_a.png", 62, (214, 178, 150), (176, 132, 118),
           ring=(226, 206, 182), seed=5)
    planet("planet_b.png", 74, (142, 168, 212), (104, 128, 178), seed=9)
    planet("planet_c.png", 54, (216, 168, 190), (172, 122, 152), seed=13)
    planet_big()
    aurora("aurora_k.png", (255, 130, 205))     # the pink curtain
