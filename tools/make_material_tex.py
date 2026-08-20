# -*- coding: utf-8 -*-
"""Bakes the three surfaces the market is mostly made of.
    python tools/make_material_tex.py

WHAT WAS WRONG, looked at side by side in the assets folder:

  t_canvas.jpg   was not canvas. It was olive-green with vertical BLUE-GREY
                 BARS scattered over it, and it is what every basket and every
                 coil of rope in the town is wearing.
  t_clay_d.jpg   was flat horizontal corrugation at one spacing over the whole
                 tile, one colour throughout - closer to corrugated plastic
                 than to a fired pot.
  t_cloth_d.jpg  was a single flat tan with a faint regular grid. Nothing to
                 catch the eye, so a bale of it read as a blank shape.

What the real things look like:

  Fired earthenware keeps the RINGS the potter's fingers left going up the
  wall, but they are uneven and they fade where the pot was smoothed. It is
  never one colour: the kiln clouds it, the flame side goes darker and greyer,
  and the clay is full of grog that speckles the surface. Edges chip pale.

  Basketry is a PLAIT: the weft passes over one stake and under the next, and
  each row is offset from the last, so the light catches alternate ribs.
  Every rod is a different shade because every rod is a different withy.

  Sackcloth is a plain weave of thick uneven yarn - slubs, thick and thin -
  and it is dirty in patches, never uniform.

Everything is periodic in both axes, so all three tile seamlessly.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_wood_tex import N, smoothstep, tile_noise, unit   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


def grid():
    u = np.linspace(0.0, 1.0, N, endpoint=False)
    return np.meshgrid(u, u)


def save(name, arr):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
        os.path.join(ASSETS, name), quality=93)
    print("wrote %s" % name)


# ------------------------------------------------------------------- clay
def clay():
    U, V = grid()
    base = np.array([176, 104, 66], float)     # terracotta, fired
    dark = np.array([118, 62, 40], float)      # where the flame licked it

    # the potter's rings: uneven spacing, and they fade where it was smoothed
    wob = 0.010 * tile_noise(3, 3, aniso=0.35)
    ring = ((V + wob) * 34.0) % 1.0
    ring = smoothstep(0.55, 0.78, ring) * (1.0 - smoothstep(0.90, 1.0, ring))
    fade = unit(tile_noise(5, 2, aniso=0.6))            # smoothed in places
    ring = ring * (0.22 + 0.62 * fade)

    # Kiln clouding: big soft patches of smoke. It has to stay FAINT. At half
    # strength it stopped reading as smoke on a pot and started reading as a
    # smear of dark paint across the tile, which is worse than the flat colour
    # it replaced.
    cloud = unit(tile_noise(9, 3, aniso=1.0))
    cloud = smoothstep(0.34, 0.92, cloud) * 0.42

    # grog: the sand in the clay body, a fine speckle
    grog = unit(tile_noise(17, 6, aniso=1.0))
    grog = (smoothstep(0.72, 0.92, grog) - smoothstep(0.10, 0.30, grog)) * 0.5

    col = base[None, None, :] * (1.0 - cloud[..., None]) \
        + dark[None, None, :] * cloud[..., None]
    col = col * (1.0 - 0.20 * ring[..., None])           # rings sit in shadow
    col = col * (1.0 + 0.10 * grog[..., None])
    # a general warm-to-cool drift, so no two areas match
    drift = 0.94 + 0.12 * unit(tile_noise(23, 2, aniso=1.4))
    col = col * drift[..., None]

    # chips: where it has knocked, the raw pale body shows
    chip = unit(tile_noise(31, 5, aniso=1.0))
    chip = smoothstep(0.965, 1.0, chip) * 0.7
    col = col * (1.0 - chip[..., None]) + \
        np.array([192, 146, 112], float)[None, None, :] * chip[..., None]
    return col


# ---------------------------------------------------------------- basketry
def basketry():
    U, V = grid()
    ROWS, STAKES = 22.0, 26.0
    row = V * ROWS
    ri = np.floor(row)
    rf = row - ri
    # every other row starts half a stake over, which is what makes a plait
    col_ = U * STAKES + 0.5 * (ri % 2.0)
    cf = col_ - np.floor(col_)

    # the withy itself: a rounded rod, so shade it round its own width
    rod = np.sin(np.pi * np.clip(rf, 0, 1)) ** 0.55
    over = (np.floor(col_) + ri) % 2.0 < 1.0        # over a stake, or under it

    # the stake showing through where the weft passes behind
    stake = np.sin(np.pi * np.clip(cf, 0, 1)) ** 0.55

    shade = np.where(over, 0.70 + 0.62 * rod, 0.36 + 0.44 * stake)

    # no two withies are the same colour
    tone = 0.84 + 0.32 * unit(tile_noise(41, 2, aniso=0.25))
    fibre = 1.0 - 0.12 * unit(tile_noise(47, 6, aniso=0.18))   # grain along it

    base = np.array([172, 137, 88], float)
    col = base[None, None, :] * (shade * tone * fibre)[..., None]
    # the shadow in the gap between rows
    gap = smoothstep(0.92, 1.0, rf) + smoothstep(0.08, 0.0, rf)
    col = col * (1.0 - 0.30 * np.clip(gap, 0, 1)[..., None])
    return col


# ------------------------------------------------------------------- cloth
def sackcloth():
    U, V = grid()
    WARP, WEFT = 118.0, 112.0
    a = (U * WARP) % 1.0
    b = (V * WEFT) % 1.0
    # a plain weave: warp on top on alternate crossings
    up = ((np.floor(U * WARP) + np.floor(V * WEFT)) % 2.0) < 1.0
    ya = np.sin(np.pi * a) ** 0.6
    yb = np.sin(np.pi * b) ** 0.6
    weave = np.where(up, 0.78 + 0.30 * ya, 0.62 + 0.30 * yb)

    # SLUBS: hand-spun yarn is thick here and thin there, and that is most of
    # what tells the eye it is cloth and not paper
    slub = unit(tile_noise(53, 4, aniso=9.0))
    slub2 = unit(tile_noise(59, 4, aniso=0.11))
    weave = weave * (0.90 + 0.20 * slub) * (0.92 + 0.16 * slub2)

    dirt = unit(tile_noise(61, 3, aniso=1.0))
    dirt = smoothstep(0.35, 0.95, dirt)

    base = np.array([203, 180, 138], float)
    soil = np.array([146, 126, 96], float)
    col = base[None, None, :] * (1.0 - 0.55 * dirt[..., None]) \
        + soil[None, None, :] * (0.55 * dirt[..., None])
    return col * weave[..., None]


if __name__ == "__main__":
    save("t_clay_d.jpg", clay())
    save("t_canvas.jpg", basketry())
    save("t_cloth_d.jpg", sackcloth())
