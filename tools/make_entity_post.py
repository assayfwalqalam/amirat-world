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


if __name__ == "__main__":
    entity()
    aurora("aurora_g.png", (96, 235, 152))
    aurora("aurora_p.png", (172, 116, 240))
    meteor()
