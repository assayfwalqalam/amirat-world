# -*- coding: utf-8 -*-
"""Bakes the relic carpet's design.
    python tools/make_rug_tex.py

The carpet had no design on it at all - only raised bosses lit from within -
so it read as a lightbox with dots rather than as a carpet. A carpet is its
PATTERN; the pile and the glow are what the pattern is carried on.

The layout is the one every knotted carpet in this tradition uses, because it
is the one that works: a bordered frame with a guard stripe either side of a
main border, and inside it a field with a central medallion, pendants above
and below it, and spandrels filling the four corners. Everything is mirrored
about both axes, which is what makes a rug read as woven rather than printed:
a weaver counting knots outward from the centre cannot help producing that.

His five colours: purple, pink, blue, white and gold, on a pink ground.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_wood_tex import tile_noise   # noqa: E402


def smoothstep(a, b, x):
    """The one in make_wood_tex takes scalar edges. Here the edges are ARRAYS -
    a petal outline is a different radius at every angle - so the guard against
    a zero-width edge has to be elementwise or numpy refuses to say whether an
    array is small."""
    d = np.where(np.abs(np.asarray(b) - np.asarray(a)) > 1e-6,
                 np.asarray(b) - np.asarray(a), 1e-6)
    t = np.clip((x - a) / d, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
NX, NY = 1024, 680          # a carpet is not square and its texture should not be

# his palette
GROUND = (168, 78, 132)     # the pink field
DEEP = (86, 44, 118)        # purple
BLUE = (66, 96, 176)
GOLD = (214, 168, 82)
CREAM = (238, 228, 236)
ROSE = (232, 132, 186)


def unit(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def rug():
    u = np.linspace(0.0, 1.0, NX)
    v = np.linspace(0.0, 1.0, NY)
    U, V = np.meshgrid(u, v)
    # distance from the centre, in units where the field is roughly square
    CX, CY = (U - 0.5), (V - 0.5) * (NY / float(NX)) * (NX / float(NY)) * 0.66
    R = np.sqrt(CX * CX + CY * CY)
    TH = np.arctan2(CY, CX)

    col = np.zeros((NY, NX, 3), float)
    col[:] = GROUND

    def lay(mask, rgb, soft=0.0):
        c = np.array(rgb, float)
        m = mask if soft <= 0 else mask
        col[:] = col * (1 - m[..., None]) + c[None, None, :] * m[..., None]

    def band(lo, hi, edge=0.004):
        """a frame band between two insets from the edge"""
        d = np.minimum(np.minimum(U, 1 - U), np.minimum(V, 1 - V))
        return (smoothstep(lo - edge, lo + edge, d)
                * (1 - smoothstep(hi - edge, hi + edge, d)))

    # ---- the borders, from the outside in
    lay(band(0.000, 0.018), np.array(DEEP) * 0.75)          # the selvedge
    lay(band(0.018, 0.032), GOLD)                            # outer guard
    lay(band(0.032, 0.092), DEEP)                            # the main border
    lay(band(0.092, 0.104), GOLD)                            # inner guard
    lay(band(0.104, 0.118), CREAM)

    # the running vine in the main border: a wave with rosettes on it
    d = np.minimum(np.minimum(U, 1 - U), np.minimum(V, 1 - V))
    inb = band(0.034, 0.090, 0.003)
    # a coordinate that runs ALONG the border, whichever side you are on
    along = np.where(np.minimum(U, 1 - U) < np.minimum(V, 1 - V), V, U)
    wave = np.sin(along * math.pi * 2 * 11) * 0.012
    mid = 0.062 + wave
    vine = (1 - smoothstep(0.0, 0.010, np.abs(d - mid))) * inb
    lay(vine, GOLD)
    rose = (np.sin(along * math.pi * 2 * 11) ** 2) > 0.985
    lay(((1 - smoothstep(0.0, 0.020, np.abs(d - mid))) * inb * rose), ROSE)

    # ---- the field
    field = 1 - smoothstep(0.116, 0.122, -d + 0.238) if False else band(0.118, 1.0, 0.003)

    # the repeating motif: an eight-petal rosette on a lattice, mirrored
    LX, LY = 9.0, 6.0
    fu = (U * LX) % 1.0 - 0.5
    fv = (V * LY) % 1.0 - 0.5
    fr = np.sqrt(fu * fu + fv * fv)
    fth = np.arctan2(fv, fu)
    petal = 0.26 + 0.13 * np.cos(fth * 8)
    lay(field * (1 - smoothstep(petal - 0.03, petal + 0.03, fr)), BLUE)
    lay(field * (1 - smoothstep(0.10, 0.13, fr)), GOLD)
    # the lattice the rosettes sit on
    lat = ((1 - smoothstep(0.004, 0.012, np.abs(np.abs(fu) - np.abs(fv))))
           * (1 - smoothstep(0.30, 0.40, fr)))
    lay(field * lat * 0.7, ROSE)

    # ---- the medallion, its pendants and the spandrels
    petals = 0.150 + 0.052 * np.cos(TH * 16) + 0.016 * np.cos(TH * 4)
    med = 1 - smoothstep(petals - 0.006, petals + 0.006, R)
    lay(field * med, DEEP)
    lay(field * (1 - smoothstep(petals * 0.80 - 0.005, petals * 0.80 + 0.005, R)), CREAM)
    lay(field * (1 - smoothstep(petals * 0.58 - 0.005, petals * 0.58 + 0.005, R)), ROSE)
    lay(field * (1 - smoothstep(petals * 0.30 - 0.005, petals * 0.30 + 0.005, R)), GOLD)
    # the outline that makes it sit on the field rather than float over it
    ring = ((1 - smoothstep(0.0, 0.006, np.abs(R - petals))) * field)
    lay(ring, GOLD)

    for sgn in (-1, 1):
        PY = (V - 0.5) - sgn * 0.235
        PR = np.sqrt(CX * CX + (PY * 0.66) ** 2)
        pp = 0.052 + 0.020 * np.cos(np.arctan2(PY, CX) * 10)
        lay(field * (1 - smoothstep(pp - 0.005, pp + 0.005, PR)), DEEP)
        lay(field * (1 - smoothstep(pp * 0.5 - 0.004, pp * 0.5 + 0.004, PR)), GOLD)

    # spandrels: quarter fans in each corner of the field
    for (ax, ay) in ((0, 0), (1, 0), (0, 1), (1, 1)):
        dx, dy = (U - ax), (V - ay) * 0.66
        rr = np.sqrt(dx * dx + dy * dy)
        sp = 0.185 + 0.030 * np.cos(np.arctan2(dy, dx) * 12)
        lay(field * (1 - smoothstep(sp - 0.006, sp + 0.006, rr)), DEEP)
        lay(field * (1 - smoothstep(sp * 0.86 - 0.004, sp * 0.86 + 0.004, rr)), GOLD)

    # ---- and then it is made of wool, not of paint
    # ABRASH: the dye lot changes as the weaver works up the rug, in bands
    ab = 0.93 + 0.14 * unit(tile_noise(5, 3, aniso=0.08))[:NY, :NX] \
        if False else 0.93 + 0.14 * np.repeat(
            unit(np.sin(np.linspace(0, 9.0, NY)) + 0.4 * np.sin(np.linspace(0, 23.0, NY)))[:, None],
            NX, axis=1)
    col *= ab[..., None]
    # the knots themselves
    knot = (0.88 + 0.24 * ((np.arange(NX)[None, :] % 3) / 2.0)) \
        * (0.90 + 0.20 * ((np.arange(NY)[:, None] % 2)))
    col *= (0.94 + 0.06 * knot)[..., None]
    # and the pile lies one way, so it is lighter along the nap
    nap = 0.94 + 0.12 * np.repeat(
        (0.5 + 0.5 * np.sin(np.linspace(0, 140.0, NY)))[:, None], NX, axis=1)
    col *= nap[..., None]

    return np.clip(col, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    a = rug()
    p = os.path.join(ASSETS, "t_rug_d.jpg")
    Image.fromarray(a).save(p, quality=94)
    print("wrote t_rug_d.jpg  %dx%d" % (NX, NY))
