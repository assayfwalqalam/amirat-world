# -*- coding: utf-8 -*-
# THE WHOLE SKY over the meadow's edge, as one painting:
#   python tools/make_skyvista.py  ->  assets/skyvista.png (4096x1024)
#
# His two faults with the first vista were exact and both measurable:
#
#   STRETCHED - a 2:1 image was wrapped on a dome whose arc is 3.7:1, so
#   every pixel was smeared 1.85x sideways. The canvas is 4:1 now, which
#   matches the dome (r2780 x 3.6rad arc vs 2700 tall) to within a few
#   percent: a cell of noise is square on the finished sky.
#
#   NO DEPTH, NO DETAIL - the old noise was built on SQUARE grids and then
#   squashed onto the wide canvas, which destroyed the fine structure
#   before it ever rendered, and everything sat in one flat plane. Depth in
#   a real nebula plate comes from three things, and all three are built
#   here deliberately:
#     1. LAYERS - far dust is flat, cool, low-contrast; near dust is sharp,
#        bright, warm. Three of them, composited back to front.
#     2. OCCLUSION - dark lanes of foreground dust cut ACROSS the bright
#        regions. Nothing says "something is in front of that" like a
#        bright thing being blocked by a dark thing.
#     3. SCALE - stars at three depths: a dense dim field dimmed BY the
#        dust, a middle scatter, and a few great flared ones in front.
import math
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")


def fbm2(H, W, base=6, octaves=8, seed=1, gain=0.55, ridged=False):
    """Noise built AT the canvas aspect: grids are (o, o*W/H), so a cell is
    square on the finished sky. `ridged` folds the noise about zero, which
    turns soft billows into the thread-and-filament structure real nebula
    photographs show."""
    rng = np.random.default_rng(seed)
    ar = max(1, int(round(W / float(H))))
    out = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for i in range(octaves):
        gh = base * (2 ** i)
        if gh > H:
            break
        g = rng.normal(0, 1, (gh, gh * ar)).astype(np.float32)
        gi = np.asarray(Image.fromarray(g).resize((W, H), Image.BICUBIC))
        if ridged:
            gi = 1.0 - np.abs(gi / (np.abs(gi).max() + 1e-6))
        out += gi * amp
        tot += amp
        amp *= gain
    out /= max(tot, 1e-6)
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def warp2(field, wx, wy, ax, ay):
    H, W = field.shape
    ys, xs = np.mgrid[0:H, 0:W]
    xs2 = np.clip(xs + (wx - 0.5) * ax, 0, W - 1).astype(np.int32)
    ys2 = np.clip(ys + (wy - 0.5) * ay, 0, H - 1).astype(np.int32)
    return field[ys2, xs2]


def blur2(a, r):
    return np.asarray(Image.fromarray(
        np.clip(a * 255, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0


def skyvista():
    W7, H7 = 4096, 1024
    yy, xx = np.mgrid[0:H7, 0:W7]
    u = xx / float(W7)
    v = yy / float(H7)

    # ---- the ground of the sky: violet zenith to a sunset-orange horizon
    # THE WARM BAND MUST LAND ON THE SKYLINE. On the dome the plate's last
    # rows fall BELOW the horizon, where the ground hides them - the sunset
    # was being buried and the horizon came out a pale lilac. Every stop is
    # lifted so the orange sits at four fifths of the way down, which is
    # exactly where the eye meets the earth.
    STOPS = [(0.00, (26, 16, 52)), (0.24, (74, 34, 96)),
             (0.46, (152, 58, 124)), (0.64, (218, 98, 126)),
             (0.78, (248, 142, 112)), (0.90, (255, 190, 122)),
             (1.00, (255, 208, 142))]
    rgb = np.zeros((H7, W7, 3), np.float32)
    for i in range(len(STOPS) - 1):
        (t0, c0), (t1, c1) = STOPS[i], STOPS[i + 1]
        m = np.clip((v - t0) / (t1 - t0), 0, 1)
        inb = (v >= t0) & ((v < t1) | (i == len(STOPS) - 2))
        for c in range(3):
            rgb[:, :, c] = np.where(inb, c0[c] + (c1[c] - c0[c]) * m,
                                    rgb[:, :, c])

    # ---- the dust river and its three hearts
    # TWO rivers, crossing: the great band, and a fainter branch that
    # leaves it and climbs. One sky, not a row of separate clouds - every
    # heart below sits ON this structure, so they merge instead of
    # floating as patches.
    spine = 0.40 + 0.13 * np.sin(u * math.pi * 1.7 + 0.5)
    band = np.exp(-(((v - spine) / 0.20) ** 2))
    spine2 = 0.30 + 0.20 * np.sin(u * math.pi * 1.1 - 1.3)
    band2 = np.exp(-(((v - spine2) / 0.11) ** 2))         * np.clip(np.sin(math.pi * np.clip((u - 0.05) / 0.75, 0, 1)), 0, 1)
    band = np.clip(band + 0.62 * band2, 0, 1.25)
    # seven hearts of different kinds, spread through the whole width:
    # rose, violet, ember, a cold cyan knot, a small blue one, a deep
    # magenta and a pale gold - each with its own core and halo colour
    # ORDERED FOR THE WALKER. The plate's middle is what faces whoever
    # stands in the meadow, so the two most beautiful hearts - the rose and
    # the gold ember - are set there, with the cooler blue and cyan ones
    # carried out to the flanks where the sky is quieter anyway.
    HEARTS = [(0.06, 0.44, (232, 244, 255), (96, 176, 236)),
              (0.19, 0.32, (255, 240, 252), (150, 120, 246)),
              (0.34, 0.46, (255, 214, 232), (238, 118, 186)),
              (0.47, 0.31, (255, 236, 250), (206, 110, 240)),
              (0.61, 0.45, (255, 238, 214), (242, 158, 96)),
              (0.76, 0.33, (255, 220, 238), (226, 108, 168)),
              (0.91, 0.45, (214, 255, 250), (86, 206, 208))]
    hglow = np.zeros((H7, W7), np.float32)
    hcol = np.zeros((H7, W7, 3), np.float32)
    hnear = np.zeros((H7, W7), np.float32)
    for (hx, hy, ccore, cmid) in HEARTS:
        # each heart its own size: near ones broad, far ones tight - the
        # sky then has scale as well as depth
        sc = 0.72 + 0.62 * ((hx * 7.3) % 1.0)
        dd = np.sqrt(((u - hx) * 3.4) ** 2 + ((v - hy) * 1.15) ** 2)
        core = np.exp(-(dd / (0.042 * sc)) ** 2)
        halo = np.exp(-(dd / (0.155 * sc)) ** 2)
        hglow = np.maximum(hglow, core + halo * 0.5)
        hnear = np.maximum(hnear, halo)
        for c in range(3):
            hcol[:, :, c] = np.maximum(hcol[:, :, c],
                                       core * ccore[c] * 0.80
                                       + halo * 0.5 * cmid[c])

    # ---- LAYER 1, FAR: a flat cool haze, almost no contrast
    fw1 = fbm2(H7, W7, base=4, octaves=5, seed=301)
    fw2 = fbm2(H7, W7, base=4, octaves=5, seed=307)
    far = warp2(fbm2(H7, W7, base=5, octaves=6, seed=311), fw1, fw2, 120, 60)
    far = far * (0.35 + 0.65 * band)
    FARC = np.array([104, 96, 168], np.float32)
    for c in range(3):
        rgb[:, :, c] += far * FARC[c] * 0.34

    # ---- LAYER 2, MID: the body of the river, structured, warm at hearts
    mid = warp2(fbm2(H7, W7, base=6, octaves=8, seed=317), fw1, fw2, 150, 70)
    fine = fbm2(H7, W7, base=24, octaves=5, seed=331)
    mid = (band * 0.95 + hglow * 0.85) * (0.22 + 0.78 * mid ** 1.25) \
        * (0.42 + 0.58 * fine)
    MIDC = np.array([176, 132, 226], np.float32)
    for c in range(3):
        rgb[:, :, c] += mid * MIDC[c] * 0.74
        rgb[:, :, c] += hcol[:, :, c] * mid * 0.85

    # ---- THE DARK LANES: foreground dust cutting across the bright.
    lane = warp2(fbm2(H7, W7, base=4, octaves=6, seed=347), fw2, fw1, 190, 90)
    lanes = np.clip((lane - 0.46) * 4.8, 0, 1)
    lanes *= np.clip(band * 1.5 + hnear * 1.2, 0, 1)
    lanes = blur2(lanes, 2.0)
    rgb *= (1.0 - 0.62 * lanes)[:, :, None]

    # ---- LAYER 3, NEAR: sharp ridged filaments, the closest dust of all
    ridge = warp2(fbm2(H7, W7, base=10, octaves=7, seed=353, ridged=True),
                  fw2, fw1, 90, 45)
    ridge = np.clip((ridge - 0.55) * 2.6, 0, 1) ** 1.4
    near = ridge * np.clip(band * 1.2 + hnear * 1.5, 0, 1) \
        * (0.35 + 0.65 * fine)
    NEARC = np.array([255, 214, 240], np.float32)
    for c in range(3):
        rgb[:, :, c] += near * NEARC[c] * 0.62
        rgb[:, :, c] += hcol[:, :, c] * near * 0.45
    # the hearts' own light, unoccluded - they are the light SOURCE
    for c in range(3):
        rgb[:, :, c] += hcol[:, :, c] * 0.42

    # ---- STARS AT THREE DEPTHS
    TINTS = [(255, 255, 255), (255, 244, 226), (255, 226, 172),
             (255, 196, 150), (206, 222, 255), (168, 198, 255),
             (255, 206, 232), (216, 250, 255), (236, 214, 255)]
    r5 = np.random.default_rng(59)
    occl = np.clip(1.0 - (mid * 1.5 + near * 2.0 + lanes * 1.2), 0.05, 1)

    def sow(n, rmin, rmax, amin, amax, behind):
        lay = np.zeros((H7, W7), np.float32)
        col = np.zeros((H7, W7, 3), np.float32)
        placed, tries = 0, 0
        while placed < n and tries < n * 25:
            tries += 1
            px = int(r5.integers(6, W7 - 6))
            py = int(r5.integers(6, H7 - 6))
            tint = TINTS[int(r5.integers(0, len(TINTS)))]
            rr = float(r5.uniform(rmin, rmax))
            amp = float(r5.uniform(amin, amax))
            k = int(max(4, rr * 4))
            ly, hy2 = max(0, py - k), min(H7, py + k + 1)
            lx, hx2 = max(0, px - k), min(W7, px + k + 1)
            sy, sx = np.mgrid[ly:hy2, lx:hx2]
            gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2)
                          / (2 * rr ** 2))) * amp
            lay[ly:hy2, lx:hx2] = np.maximum(lay[ly:hy2, lx:hx2], gg)
            for c in range(3):
                col[ly:hy2, lx:hx2, c] = np.maximum(col[ly:hy2, lx:hx2, c],
                                                    gg * tint[c])
            placed += 1
        if behind:
            lay = lay * occl
            col = col * occl[:, :, None]
        return lay, col

    l1, c1 = sow(11000, 0.30, 0.62, 0.12, 0.48, 1)  # the deep field
    l2, c2 = sow(3400, 0.50, 1.00, 0.30, 0.80, 1)   # the middle scatter
    l3, c3 = sow(800, 0.75, 1.60, 0.55, 1.00, 0)    # near, in front of all
    stars = np.maximum(np.maximum(l1, l2), l3)
    scol = np.maximum(np.maximum(c1, c2), c3)

    # a few great foreground stars with diffraction spikes, for SCALE
    for _ in range(46):
        px = int(r5.integers(60, W7 - 60))
        py = int(r5.integers(30, H7 - 120))
        tint = TINTS[int(r5.integers(0, len(TINTS)))]
        r0 = float(r5.uniform(1.6, 3.0))
        k = int(r0 * 26)
        ly, hy2 = max(0, py - k), min(H7, py + k + 1)
        lx, hx2 = max(0, px - k), min(W7, px + k + 1)
        sy, sx = np.mgrid[ly:hy2, lx:hx2]
        gg = np.exp(-(((sx - px) ** 2 + (sy - py) ** 2)
                      / (2 * (r0 * 1.7) ** 2)))
        fl = (np.exp(-np.abs(sx - px) / (r0 * 7.0))
              * np.exp(-np.abs(sy - py) / (r0 * 0.75))
              + np.exp(-np.abs(sy - py) / (r0 * 7.0))
              * np.exp(-np.abs(sx - px) / (r0 * 0.75))) * 0.55
        st = np.clip(gg + fl, 0, 1)
        stars[ly:hy2, lx:hx2] = np.maximum(stars[ly:hy2, lx:hx2], st)
        for c in range(3):
            scol[ly:hy2, lx:hx2, c] = np.maximum(scol[ly:hy2, lx:hx2, c],
                                                 st * tint[c])
    rgb = rgb + scol * 0.95

    # ---- HIGHLIGHT ROLL-OFF. Straight addition drove the hearts past
    # 255 and they came out as flat white blobs - the one thing in the sky
    # with no colour and no structure. This is the film curve: mid-tones
    # keep their place, the brightest cores bend under the ceiling instead
    # of hitting it, and the colour survives all the way up.
    rgb = 255.0 * (1.0 - np.exp(-1.386 * (np.clip(rgb, 0, None) / 255.0)))

    # ---- THE GRADE. The roll-off saves the cores from clipping but it
    # pulls every highlight toward grey with them, and spread across
    # sixty-seven degrees of sky that reads as pastel. Measured in the
    # render, the horizon was coming out (182,135,123) - a colour with no
    # conviction. Saturation is pushed back out from luminance and a gentle
    # S-curve returns the contrast, which is the difference between a sky
    # that glows and a sky that is merely lit.
    lum = rgb.mean(axis=2, keepdims=True)
    rgb = lum + (rgb - lum) * 1.52
    x = np.clip(rgb / 255.0, 0, 1)
    x = np.clip(x * x * (3.0 - 2.0 * x) * 0.42 + x * 0.58, 0, 1)
    rgb = np.clip(x * 255.0, 0, 255)

    # ---- the veil: full through the heart, melting at every edge
    # THE VEIL, cut for a HEMISPHERE (the plate is now 360 x 90 degrees):
    #   - across: full through the heart, gone at both ends, and since the
    #     ends meet behind the watcher the seam is two transparent edges
    #     laid on each other - no join to see;
    #   - the top quarter melts away, so the nebula gives out gently into
    #     the ordinary starry night at the zenith instead of ending on a
    #     line (his "does not blend with the top");
    #   - the bottom row IS the horizon now, so it stays nearly full - the
    #     old cut faded the sunset band away just where it should be
    #     strongest.
    alpha = np.full((H7, W7), 0.94, np.float32)
    # a WIDE, gentle fall to nothing: sin(pi*u) still had a third of its
    # strength two degrees from the seam, and that edge read as a stripe.
    # Full through the central third, gone well before the join, so the
    # two transparent edges meet behind the watcher invisibly.
    env = np.clip((1.0 - np.abs(u - 0.5) / 0.46) / 0.62, 0, 1)
    alpha *= env * env * (3.0 - 2.0 * env)
    alpha *= np.clip(v * 3.6, 0, 1) ** 0.9
    alpha *= np.clip((1.08 - v) * 14.0, 0, 1)
    alpha = np.clip(alpha + stars * 0.4, 0, 1)

    out = np.dstack([np.clip(rgb, 0, 255),
                     (alpha * 255)[:, :, None]]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(ASSETS, "skyvista.png"))
    print("WROTE skyvista.png 4096x1024")


def aurora_band(name, col, seed):
    """A curtain, painted at the aspect its arc actually has (1.3:1), with
    the fine vertical striation a real aurora shows. The old 0.5:1 sheet was
    stretched 2.6x across its band - fat smeared rays, no detail."""
    W8, H8 = 1280, 768
    rng = np.random.default_rng(seed)

    def rays(n, sharp):
        c = rng.normal(0, 1, n)
        c = np.interp(np.linspace(0, n - 1, W8), np.arange(n), c)
        c = (c - c.min()) / (np.ptp(c) + 1e-6)
        return c ** sharp

    # three scales of ray: broad folds, rays, and fine threads
    cols = (0.45 * rays(14, 1.4) + 0.38 * rays(48, 1.7)
            + 0.22 * rays(150, 2.1))
    cols = (cols - cols.min()) / (np.ptp(cols) + 1e-6)
    cols = 0.16 + 0.84 * cols ** 1.35

    y = np.linspace(0, 1, H8)[:, None]
    # sharp at the lower rim, breathing away upward, with the rays
    # lengthening irregularly so the top edge is never a line
    top = 0.42 + 0.34 * np.interp(np.linspace(0, 1, W8),
                                  np.linspace(0, 1, 24),
                                  rng.uniform(0, 1, 24))[None, :]
    prof = np.clip((y - 0.06) / 0.10, 0, 1) * np.clip((top - y) / 0.42, 0, 1) ** 1.5
    alp = prof * cols[None, :] * 255 * 0.9
    # the feathered ends - no rectangle may ever show
    xs = np.linspace(0, 1, W8)[None, :]
    alp *= np.clip(np.sin(math.pi * xs) ** 0.5, 0, 1)

    img = np.zeros((H8, W8, 4), np.float32)
    for c in range(3):
        img[:, :, c] = col[c]
    # the lower rim runs hotter, as a real curtain does
    hot = np.clip((0.26 - y) / 0.20, 0, 1) * prof
    for c in range(3):
        img[:, :, c] = np.minimum(255, img[:, :, c] + hot * 90)
    img[:, :, 3] = np.clip(alp, 0, 255)
    out = Image.fromarray(img.astype(np.uint8), "RGBA").filter(
        ImageFilter.GaussianBlur(1.5))
    out.save(os.path.join(ASSETS, name))
    print("WROTE", name)


def star_sprite():
    """One star, for the engine's living field: a tight core, a soft bloom
    and a four-point flare. The painted stars in the vista cannot twinkle -
    a painting is fixed - so the sky gets a real animated field on top of
    it, and this is the sprite it is drawn with."""
    N = 64
    yy, xx = np.mgrid[0:N, 0:N]
    cx = cy = (N - 1) / 2.0
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    core = np.exp(-(r / 1.7) ** 2)
    bloom = np.exp(-(r / 6.5) ** 2) * 0.42
    flare = (np.exp(-np.abs(xx - cx) / 1.4) * np.exp(-np.abs(yy - cy) / 11.0)
             + np.exp(-np.abs(yy - cy) / 1.4) * np.exp(-np.abs(xx - cx) / 11.0))
    a = np.clip(core + bloom + flare * 0.30, 0, 1)
    img = np.zeros((N, N, 4), np.uint8)
    img[:, :, 0] = img[:, :, 1] = img[:, :, 2] = 255
    img[:, :, 3] = (a * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(ASSETS, "star_sprite.png"))
    print("WROTE star_sprite.png")


if __name__ == "__main__":
    star_sprite()
    skyvista()
    aurora_band("aurora_g.png", (96, 235, 152), 11)
    aurora_band("aurora_p.png", (172, 116, 240), 23)
    aurora_band("aurora_k.png", (255, 130, 205), 37)
