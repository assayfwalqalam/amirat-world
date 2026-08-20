# -*- coding: utf-8 -*-
"""Bakes the two surfaces the town is actually built of.
    python tools/make_stone_tex.py

WHAT WAS WRONG: sandstone.jpg was flat beige rectangles with a soft edge and
nothing else - no grain, no bedding, no staining, one colour for every block.
mudbrick.jpg was a ruled brick grid, every brick identical, drawn rather than
made. Neither survives being looked at from two metres.

What the real things do:

  SANDSTONE is a compacted beach. It keeps the CROSS-BEDDING - the slanting
  laminations laid down by the current that made it - and those run at an
  angle across a cut face, not along it. Iron in the stone weeps rust down the
  block in streaks. The surface pits where softer grains have gone. And a
  dressed block is never quite the colour of the one beside it, because it
  came out of a different part of the quarry.

  MUD BRICK is made by hand in a mould: every brick is a slightly different
  size and a slightly different colour, the straw temper in it shows as pale
  flecks and hairs, the mortar is the same mud so the joint is a shade rather
  than a line, and the arrises round off because the material is soft. Bricks
  laid in a wall are also laid slightly out of true - the courses wander.

Everything is periodic in both axes, so both tile seamlessly.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_wood_tex import N, smoothstep, tile_noise   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


def unit(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def grid():
    u = np.linspace(0.0, 1.0, N, endpoint=False)
    return np.meshgrid(u, u)


def courses(U, V, rows, per_row, stagger, jitter_seed):
    """Lay blocks in courses and return, per pixel:
       bid   - a number unique to the block it belongs to
       edge  - 1 at the joint, falling to 0 inside the block
       inset - distance in from the nearest edge, 0..1
    """
    rng = np.random.default_rng(jitter_seed)
    row = V * rows
    ri = np.floor(row)
    rf = row - ri
    # every course wanders a little, so the bed joints are not ruled lines
    wob = 0.030 * np.sin(U * 2 * np.pi * 3 + ri * 1.7) \
        + 0.018 * np.sin(U * 2 * np.pi * 7 + ri * 4.1)
    rf = np.clip(rf + wob, 0.0, 1.0)

    col = U * per_row + stagger * (ri % 2.0)
    ci = np.floor(col)
    cf = col - ci

    bid = (ri * 131.0 + ci * 17.0)
    # how far in from the joints, in each direction
    din = np.minimum(rf, 1.0 - rf)
    dcol = np.minimum(cf, 1.0 - cf)
    inset = np.minimum(din * 2.0, dcol * 2.0)
    edge = 1.0 - smoothstep(0.0, 0.22, inset)
    return bid, edge, inset


def block_tone(bid, spread, seed):
    """one value per block, stable, in 0..1"""
    h = np.sin(bid * 12.9898 + seed) * 43758.5453
    return (h - np.floor(h)) * spread


# --------------------------------------------------------------- sandstone
def sandstone():
    U, V = grid()
    ROWS, PER = 5.0, 2.6
    bid, edge, inset = courses(U, V, ROWS, PER, 0.5, 11)

    base = np.array([206, 176, 132], float)
    dark = np.array([150, 118, 82], float)

    # CROSS-BEDDING: slanting laminations, at an angle to the courses.
    # Thirteen of them across the tile at a hard edge came out as thin dark
    # LINES and read as wood grain. Bedding is broad and soft - a few bands to
    # a block, each fading into the next - and it slants steeply, because it
    # is the face of a dune cut through.
    lam = (U * 1.35 + V * 2.2
           + 0.16 * tile_noise(21, 3, aniso=2.0))
    bed = (lam * 3.6) % 1.0
    bed = smoothstep(0.10, 0.50, bed) * (1.0 - smoothstep(0.50, 0.92, bed))
    bed = bed * (0.30 + 0.70 * unit(tile_noise(23, 3, aniso=1.4)))

    # the grain of the sand itself, fine and even
    grain = unit(tile_noise(31, 6, aniso=1.0))

    # pitting where softer grains have gone
    pit = unit(tile_noise(37, 5, aniso=1.0))
    pit = smoothstep(0.72, 0.94, pit)

    # iron weeping DOWN the face, so it must be stretched vertically
    rust = unit(tile_noise(41, 4, aniso=0.10))
    rust = smoothstep(0.58, 0.92, rust)

    tone = 0.86 + 0.28 * block_tone(bid, 1.0, 3.7)
    col = base[None, None, :] * tone[..., None]
    col = col * (1.0 - 0.14 * bed[..., None])
    col = col * (0.90 + 0.20 * grain[..., None])
    col = col * (1.0 - 0.26 * pit[..., None])
    col = col + (np.array([58, 22, -18], float)[None, None, :]
                 * (rust * 0.55)[..., None])
    # the joint: mortar in shadow, and the arris chipped pale above it
    col = col * (1.0 - 0.42 * edge[..., None])
    chip = smoothstep(0.16, 0.30, inset) - smoothstep(0.30, 0.46, inset)
    col = col + np.array([26, 22, 16], float)[None, None, :] * (chip * 0.5)[..., None]
    col = col * (1.0 - 0.10 * (1.0 - unit(tile_noise(47, 2, aniso=1.0))))[..., None]
    return np.clip(col, 0, 255)


# --------------------------------------------------------------- mud brick
def mudbrick():
    U, V = grid()
    ROWS, PER = 13.0, 6.5
    bid, edge, inset = courses(U, V, ROWS, PER, 0.5, 57)

    base = np.array([176, 137, 96], float)

    # STRAW TEMPER: pale hairs lying every which way in the mud
    straw = unit(tile_noise(61, 6, aniso=11.0))
    straw = smoothstep(0.70, 0.93, straw)
    straw2 = unit(tile_noise(67, 6, aniso=0.10))
    straw2 = smoothstep(0.72, 0.94, straw2)

    # the mud itself: coarse, and not the same twice
    mud = unit(tile_noise(71, 5, aniso=1.0))

    # each brick came out of the mould its own colour
    tone = 0.74 + 0.52 * block_tone(bid, 1.0, 9.1)

    col = base[None, None, :] * tone[..., None]
    col = col * (0.86 + 0.28 * mud[..., None])
    # straw shows pale and slightly grey against the mud
    col = col + np.array([52, 47, 33], float)[None, None, :] \
        * ((straw + straw2) * 0.62)[..., None]

    # THE JOINT IS THE SAME MUD, so it is a shade, not a line - and the arris
    # rounds off, because the material is soft
    # A hard edge term on top of a rounding term gave every brick a black
    # border and the wall read as pressed metal. Mud mortar is the same
    # material as the brick, so the joint is barely darker than what it joins,
    # and the rounding does the rest of the work.
    col = col * (1.0 - 0.13 * edge[..., None])
    round_ = smoothstep(0.0, 0.40, inset)
    col = col * (0.90 + 0.10 * round_)[..., None]

    # weathering runs down the wall
    wash = unit(tile_noise(79, 3, aniso=0.16))
    col = col * (0.88 + 0.22 * wash)[..., None]
    return np.clip(col, 0, 255)


def save(name, arr):
    Image.fromarray(arr.astype(np.uint8)).save(
        os.path.join(ASSETS, name), quality=93)
    print("wrote %s" % name)


if __name__ == "__main__":
    save("t_sandstone_d.jpg", sandstone())
    save("t_mudbrick_d.jpg", mudbrick())
