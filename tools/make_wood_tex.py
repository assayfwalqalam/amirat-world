# -*- coding: utf-8 -*-
"""Bakes the wood every wooden thing in the town is wearing.
    python tools/make_wood_tex.py

WHY: the old t_woodp_d.jpg was a barcode - perfectly straight parallel
stripes, evenly spaced, running the whole height of the tile with no figure,
no knots and no change of colour anywhere. On a market trestle that reads as
striped plastic laminate, and since almost every prop in the town is wooden it
was a large part of what looked bland.

Real sawn wood, from photographs of it:
  * The rings are ARCS, not lines. A board is a flat slice through a cone of
    growth rings, so the face shows long nested parabolas - what a joiner
    calls cathedral figure - and they are only straight where the cut happens
    to run through the middle of the log.
  * Each ring is two woods, not one. Earlywood grows fast and pale in spring;
    latewood grows slow, dense and dark at the end of the season. The dark
    band is the THIN one, and it has a hard edge on its outer side and a soft
    fade on its inner side. Even spacing is what gives the game away.
  * A branch leaves a knot, and the grain does not ignore it: it sweeps around
    it for some distance on both sides.
  * Along the grain run the pores - fine broken lines, much finer than the
    rings and quite separate from them.
  * No board is one colour end to end.

Everything here is periodic in both axes, so the tile is seamless: the noise
is built out of whole-numbered sine frequencies rather than sampled, which
wraps exactly by construction.
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
N = 512


def tile_noise(seed, octaves=5, aniso=1.0):
    """Seamless turbulence: whole-numbered frequencies wrap by construction.

    aniso stretches the features along the board (y), which is what makes
    grain look like grain rather than like clouds.
    """
    rng = np.random.default_rng(seed)
    ax = np.linspace(0.0, 2.0 * np.pi, N, endpoint=False)
    X, Y = np.meshgrid(ax, ax)
    out = np.zeros((N, N))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        f = 2 ** o
        # SIX waves per octave, not three, and the y frequency may run either
        # way. With three all going one way the low octaves are simply a few
        # big sinusoids, and everything drawn with them - kiln smoke on a pot,
        # colour drift down a board - came out as obvious diagonal banding
        # rather than as soft irregular patches.
        for _ in range(6):
            a = float(rng.uniform(0.55, 1.45)) * amp
            fx = f * int(rng.integers(1, 4))
            fy = max(1, int(round(f * int(rng.integers(1, 4)) / aniso)))
            if rng.random() < 0.5:
                fy = -fy
            ph = float(rng.uniform(0.0, 2.0 * np.pi))
            out += a * np.sin(fx * X + fy * Y + ph)
            total += a
        amp *= 0.52
    return out / max(total, 1e-6)


def smoothstep(a, b, x):
    # b may be BELOW a on purpose - that is how you ask for a falling edge -
    # so the denominator must keep its sign. Clamping it to a small positive
    # number turned every reversed call into a step at zero, which quietly
    # multiplied the whole board by 0.38 and made oak look like bog wood.
    d = b - a
    d = d if abs(d) > 1e-6 else 1e-6
    t = np.clip((x - a) / d, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def unit(a):
    """Turbulence built from sines cancels towards zero, so its useful range
    is nothing like -1..1. Anything downstream that wants a 0..1 signal has to
    be handed one, or a smoothstep across 0.10..0.55 simply never fires and
    the feature it was drawing silently does not exist."""
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def wood(seed, rings, pith, base, late, sat=1.0, knots=3):
    """One board's worth of flat-sawn figure."""
    u = np.linspace(0.0, 1.0, N, endpoint=False)
    U, V = np.meshgrid(u, u)                      # U across the board, V along

    # the log's centre sits off the board, so the rings cut the face as arcs
    dx = (U - pith)
    dy = (V - 0.5) * 0.30                         # squashed: the arcs are long
    r = np.sqrt(dx * dx + dy * dy)

    # the tree did not grow true, and the saw did not run true either
    r = r + 0.055 * tile_noise(seed + 11, 4, aniso=3.5) \
          + 0.016 * tile_noise(seed + 12, 5, aniso=6.0)

    # KNOTS: the grain sweeps round a branch, it does not pass through it.
    # A knot is not a drilled hole either: it is the end of a branch cut
    # through at an angle, so it is an ELLIPSE, it is ringed with its own
    # dark collar, and its middle is lighter than the collar. Round black
    # dots read as woodworm.
    kn = np.zeros_like(r)         # the collar
    kc = np.zeros_like(r)         # the lighter heart inside it
    rng = np.random.default_rng(seed + 91)
    for k in range(knots):
        kx = float(rng.uniform(0.08, 0.92))
        ky = float(rng.uniform(0.05, 0.95))
        kr = float(rng.uniform(0.013, 0.028))
        el = float(rng.uniform(1.5, 2.6))            # cut on the slant
        ddx = np.abs(U - kx); ddx = np.minimum(ddx, 1.0 - ddx)
        ddy = np.abs(V - ky); ddy = np.minimum(ddy, 1.0 - ddy)
        d = np.sqrt(ddx * ddx + (ddy / el) ** 2)
        r -= 0.055 * np.exp(-(d / (kr * 5.0)) ** 2)     # the sweep around it
        kn = np.maximum(kn, smoothstep(kr * 1.55, kr * 0.85, d))
        kc = np.maximum(kc, smoothstep(kr * 0.80, kr * 0.35, d))

    ring = (r * rings) % 1.0

    # LATEWOOD IS THE THIN DARK BAND, hard on its outer edge, soft on its
    # inner one. An even black-and-white split is what makes stripes read as
    # print rather than as timber.
    band = smoothstep(0.70, 0.76, ring) * (1.0 - smoothstep(0.94, 0.985, ring))
    band = band * (0.72 + 0.28 * tile_noise(seed + 21, 3, aniso=4.0))

    # A SECOND, FINER SET OF LINES. One ring spacing over the whole board is
    # a drawing of wood; real timber has the season's rings and, inside them,
    # much finer figure that only shows close to.
    fine = (r * rings * 4.7 + 0.31) % 1.0
    fine = smoothstep(0.80, 0.90, fine) * (1.0 - smoothstep(0.96, 1.0, fine))

    # the pores: fine broken lines along the grain, nothing to do with rings
    pore = unit(tile_noise(seed + 31, 6, aniso=16.0))
    pore = smoothstep(0.52, 0.86, pore) * 0.42

    # and no board is one colour from end to end
    wash = 0.86 + 0.24 * (0.5 + 0.5 * tile_noise(seed + 41, 2, aniso=2.2))

    base = np.array(base, float)
    late = np.array(late, float)
    col = base[None, None, :] * (1.0 - band[..., None]) \
        + late[None, None, :] * band[..., None]
    col = col * (1.0 - 0.085 * fine[..., None])
    col = col * wash[..., None]
    col = col * (1.0 - pore[..., None] * 0.30)

    # the knot: a dark collar with a lighter heart inside it
    col = col * (1.0 - 0.46 * kn[..., None])
    col = col * (1.0 + 0.30 * kc[..., None])

    if sat != 1.0:
        g = col.mean(axis=2, keepdims=True)
        col = g + (col - g) * sat

    return np.clip(col, 0, 255).astype(np.uint8)


def save(name, arr):
    p = os.path.join(ASSETS, name)
    Image.fromarray(arr).save(p, quality=92)
    print("wrote %-18s %s" % (name, p))


if __name__ == "__main__":
    # planed furniture wood: what the tables, benches, stalls and carts wear
    save("t_woodp_d.jpg",
         wood(seed=7, rings=15.0, pith=-1.35,
              base=(166, 124, 82), late=(104, 71, 42), sat=0.94, knots=2))
    # rougher structural timber: beams, posts, fences
    save("t_wood_d.jpg",
         wood(seed=23, rings=11.0, pith=-0.55,
              base=(144, 107, 70), late=(86, 58, 34), sat=0.90, knots=3))
