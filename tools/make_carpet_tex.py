# Bakes the cloth of the palace: the carpets and the curtains.
#   python tools/make_carpet_tex.py   ->  assets/t_carpet_d.jpg
#                                         assets/t_curtain_d.jpg
#
# HIS ORDER (2026-08-19): "soft pink but not too light, just befitting to the
# theme, and also a bit purplish, with perhaps some ornamental gold or emerald
# and sapphire sparkles all around, design on it is simply floral patterns,
# realistic 90% rule too."
#
# So: a rose-mauve ground with a violet lean, a plum border, floral only -
# stems, leaves, buds, palmettes and rosettes - picked out in gold, emerald and
# sapphire, with metal-thread glints scattered through the field. No creatures
# and no faces: the pattern is plant and geometry, which is what an Andalusi
# carpet is anyway.
#
# WHAT MAKES IT READ AS WOOL AND NOT AS A DRAWING (the 90% part):
#   1. every motif is drawn at 3x and shrunk, so the curves are true
#   2. ABRASH - the dyed ground drifts in horizontal bands, as a dye lot does
#   3. the KNOT LATTICE - the colours are snapped to a warp/weft grid so the
#      curves carry the small stagger a knotted curve has
#   4. pile shading - the nap leans one way, so the weft rows catch light
#   5. per-knot colour jitter, then a breath of blur: no vector edges survive
#
# The carpet is SQUARE and complete: one whole carpet, border and all, in one
# texture. The palace lays it with its own UVs (one copy per carpet, or a row
# of copies down a long runner), so nothing is stretched and no border is cut.
# 512 is the cap the model pipeline enforces, so 512 is what we bake.
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
SIZE = 512
SS = 3                      # supersample
W = SIZE * SS

random.seed(1170)

# ------------------------------------------------------------------ the dyes
GROUND = (232, 180, 196)     # BABY PINK - his order; the violet lean is gone
GROUND_D = (218, 164, 184)
FIELD_IN = (208, 150, 172)   # the medallion's own ground, a shade under
PLUM = (188, 120, 150)       # the main border - deep rose, not violet
PLUM_D = (170, 104, 136)
GUARD = (240, 214, 222)      # the pale guard stripes that lift the borders
GOLD = (196, 158, 86)
GOLD_HI = (232, 198, 122)
EMER = (62, 112, 86)
EMER_HI = (98, 148, 112)
SAPPH = (60, 84, 142)
SAPPH_HI = (104, 130, 184)
CREAM = (238, 222, 214)
IVORY = (250, 242, 234)
INK = (150, 98, 118)         # the outline every knotted motif carries, soft


# ------------------------------------------------------------- plant shapes
def _pts(fn, n):
    return [fn(i / float(n)) for i in range(n + 1)]


def petal(d, cx, cy, ang, ln, wd, fill, outline=INK, ow=None):
    """One petal: a lens with a point at the far end and a round shoulder."""
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for side in (1, -1):
        rng = range(0, 21) if side > 0 else range(20, -1, -1)
        for i in rng:
            t = i / 20.0
            # widest at a third out, closing to a point
            w = wd * math.sin(math.pi * t ** 0.72) * (1 - t * 0.30)
            x, y = ln * t, side * w
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    d.polygon(pts, fill=fill, outline=outline,
              width=ow if ow else max(1, int(wd * 0.16)))


def leaf(d, cx, cy, ang, ln, wd, fill, vein=None):
    """A serrated leaf, bent a little along its length."""
    ca, sa = math.cos(ang), math.sin(ang)
    bend = 0.22
    pts = []
    for side in (1, -1):
        rng = range(0, 25) if side > 0 else range(24, -1, -1)
        for i in rng:
            t = i / 24.0
            w = wd * math.sin(math.pi * t ** 0.8)
            if side > 0:
                w *= 1.0 + 0.16 * math.sin(t * 9.0)      # the serration
            else:
                w *= 1.0 + 0.16 * math.sin(t * 9.0 + 1.6)
            x = ln * t
            y = side * w + bend * ln * math.sin(math.pi * t) * 0.5
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    d.polygon(pts, fill=fill, outline=INK, width=max(1, int(wd * 0.14)))
    if vein:
        vp = []
        for i in range(13):
            t = i / 12.0
            x = ln * t
            y = bend * ln * math.sin(math.pi * t) * 0.5
            vp.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        d.line(vp, fill=vein, width=max(1, int(wd * 0.16)))


def rosette(d, cx, cy, r, n=8, pet=GOLD, heart=SAPPH, ring=None, phase=0.0):
    """A flat flower seen from above: n petals round a heart."""
    for k in range(n):
        a = phase + k * 2 * math.pi / n
        petal(d, cx + math.cos(a) * r * 0.20, cy + math.sin(a) * r * 0.20,
              a, r * 0.86, r * 0.30, pet)
    if ring:
        d.ellipse([cx - r * 0.34, cy - r * 0.34, cx + r * 0.34, cy + r * 0.34],
                  outline=ring, width=max(1, int(r * 0.09)))
    d.ellipse([cx - r * 0.24, cy - r * 0.24, cx + r * 0.24, cy + r * 0.24], fill=heart)
    d.ellipse([cx - r * 0.09, cy - r * 0.09, cx + r * 0.09, cy + r * 0.09], fill=CREAM)


def palmette(d, cx, cy, ang, r, body, edge=None):
    """The fan of lobes that ends every carpet stem."""
    ca, sa = math.cos(ang), math.sin(ang)
    lobes = 7
    pts = []
    for i in range(41):
        t = i / 40.0
        th = (t - 0.5) * math.pi * 1.06
        rr = r * (0.62 + 0.38 * math.cos(th * 0.94)) * \
            (1.0 + 0.11 * math.cos(th * lobes))
        x, y = math.cos(th) * rr, math.sin(th) * rr
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    pts.append((cx - r * 0.18 * ca, cy - r * 0.18 * sa))
    d.polygon(pts, fill=body, outline=edge, width=2)
    d.ellipse([cx - r * 0.20, cy - r * 0.20, cx + r * 0.20, cy + r * 0.20], fill=CREAM)


def bud(d, cx, cy, ang, r, body, tip=None):
    """A closed bud on its stalk: three lobes in a cup."""
    ca, sa = math.cos(ang), math.sin(ang)
    for off, sc in ((-0.55, 0.72), (0.0, 1.0), (0.55, 0.72)):
        petal(d, cx, cy, ang + off, r * sc, r * 0.30 * sc, body)
    if tip:
        d.ellipse([cx + ca * r * 0.9 - r * 0.13, cy + sa * r * 0.9 - r * 0.13,
                   cx + ca * r * 0.9 + r * 0.13, cy + sa * r * 0.9 + r * 0.13], fill=tip)


def vine(d, p0, p1, bow, col, wd, curl=0.0):
    """A stem drawn as a bowed line, so nothing in the field is straight."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    nx, ny = -dy, dx
    ln = math.hypot(dx, dy) or 1.0
    nx, ny = nx / ln, ny / ln
    pts = []
    for i in range(25):
        t = i / 24.0
        b = math.sin(math.pi * t) * bow
        c = math.sin(2 * math.pi * t) * curl
        pts.append((x0 + dx * t + nx * (b + c), y0 + dy * t + ny * (b + c)))
    d.line(pts, fill=col, width=wd, joint="curve")
    return pts


# ------------------------------------------------------- the woven finishing
def weave(img, knots, nap=0.55, jitter=8.0, warp=0.30, seed=5):
    """Turn a painted picture into a knotted pile.

    knots  - how many knots across (the warp count)
    nap    - how hard the pile leans (the weft rows catching light)
    jitter - per-knot colour drift, the thing that kills the vector look
    """
    rng = np.random.default_rng(seed)
    a = np.asarray(img.convert("RGB").resize((knots, knots), Image.LANCZOS)).astype(np.float32)

    # every knot is its own tuft of wool: it takes the dye a little differently
    a += rng.normal(0.0, jitter, a.shape)

    # ABRASH: the dye lot drifts across the weaving, in bands
    band = np.cumsum(rng.normal(0.0, 1.0, knots))
    band = band / (np.abs(band).max() + 1e-6) * 7.0
    a += band[:, None, None]

    # the pile leans: one side of every weft row is lit, the other shaded
    yy = np.arange(knots)
    row = (np.sin(yy * math.pi) * 0.0 + ((yy % 2) * 2.0 - 1.0)) * nap * 4.0
    a += row[:, None, None]

    # the warp threads show through the pile as a fine vertical grain
    xx = np.arange(knots)
    a += (((xx % 2) * 2.0 - 1.0) * warp * 4.0)[None, :, None]

    a = np.clip(a, 0, 255).astype(np.uint8)
    out = Image.fromarray(a).resize((SIZE, SIZE), Image.NEAREST)   # knot blocks
    out = out.filter(ImageFilter.GaussianBlur(0.62))               # wool is soft
    # the last of the fibre: a fine grain over the whole cloth
    b = np.asarray(out).astype(np.float32)
    b += rng.normal(0.0, 3.4, b.shape)
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))


def glints(d, n, box, cols, rmin, rmax, seed):
    """Metal thread: the gold, emerald and sapphire sparks 'all around'."""
    r = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        gx = r.uniform(x0, x1)
        gy = r.uniform(y0, y1)
        rr = r.uniform(rmin, rmax)
        c = cols[r.randrange(len(cols))]
        d.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], fill=c)
        if r.random() < 0.4:                      # the four-point star of a glint
            d.line([gx - rr * 2.3, gy, gx + rr * 2.3, gy], fill=c, width=1)
            d.line([gx, gy - rr * 2.3, gx, gy + rr * 2.3], fill=c, width=1)


# ============================================================== THE CARPET
def bake_carpet():
    im = Image.new("RGB", (W, W), GROUND)
    d = ImageDraw.Draw(im)

    OUTER = int(W * 0.015)      # the selvage
    G1 = int(W * 0.015)         # outer guard stripe
    BAND = int(W * 0.072)       # the main border
    G2 = int(W * 0.013)         # inner guard stripe
    F0 = OUTER + G1 + BAND + G2
    F1 = W - F0

    # ---- the field ground, one shade different inside the border
    d.rectangle([F0, F0, F1, F1], fill=GROUND)

    # ---- the field ornament, drawn once and mirrored into four quarters so
    #      the carpet is symmetric about both axes, as a real one is
    q = Image.new("RGBA", (W // 2, W // 2), (0, 0, 0, 0))
    qd = ImageDraw.Draw(q)
    H = W // 2
    cx0, cy0 = H, H            # the carpet's centre, at this quarter's corner

    # the great arabesque: two stems sweeping out of the centre, carrying
    # leaves, buds and palmettes - the all-over that fills the pink ground
    stems = [
        ((cx0 - F0 * 0.30, cy0 - F0 * 0.30), (F0 * 0.55, F0 * 0.62), 0.16 * W),
        ((cx0 - F0 * 0.10, cy0 - F0 * 0.55), (F0 * 1.05, F0 * 0.20), 0.11 * W),
        ((cx0 - F0 * 0.55, cy0 - F0 * 0.10), (F0 * 0.20, F0 * 1.05), 0.11 * W),
    ]
    for (p0, p1, bow) in stems:
        pts = vine(qd, p0, p1, bow, EMER, max(2, int(W * 0.0052)), curl=bow * 0.22)
        for k in (4, 9, 14, 19):
            px, py = pts[k]
            a = math.atan2(pts[min(k + 2, 24)][1] - pts[k - 2][1],
                           pts[min(k + 2, 24)][0] - pts[k - 2][0])
            leaf(qd, px, py, a + 1.35, W * 0.052, W * 0.017, EMER, EMER_HI)
            leaf(qd, px, py, a - 1.35, W * 0.046, W * 0.015, EMER_HI, EMER)
        for k in (6, 16):
            px, py = pts[k]
            a = math.atan2(pts[k + 2][1] - pts[k][1], pts[k + 2][0] - pts[k][0])
            bud(qd, px, py, a + 1.6, W * 0.030, SAPPH, GOLD_HI)
        px, py = pts[-1]
        a = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
        palmette(qd, px, py, a, W * 0.058, GOLD, GOLD_HI)

    # rosettes scattered on the ground between the stems
    for (fx, fy, rr, pc, hc) in ((0.30, 0.30, 0.052, IVORY, SAPPH),
                                 (0.62, 0.16, 0.040, GOLD_HI, EMER),
                                 (0.16, 0.62, 0.040, GOLD_HI, EMER),
                                 (0.72, 0.60, 0.046, IVORY, PLUM),
                                 (0.44, 0.72, 0.034, SAPPH_HI, GOLD),
                                 (0.72, 0.42, 0.034, SAPPH_HI, GOLD)):
        rosette(qd, F0 + (H - F0) * fx, F0 + (H - F0) * fy, W * rr,
                n=8, pet=pc, heart=hc, ring=GOLD)

    # small leaf sprays filling what is left, so no wide bald pink
    rr2 = random.Random(31)
    for _ in range(44):
        lx = rr2.uniform(F0 + W * 0.02, H - W * 0.01)
        ly = rr2.uniform(F0 + W * 0.02, H - W * 0.01)
        a = rr2.uniform(0, 6.283)
        leaf(qd, lx, ly, a, W * 0.030, W * 0.010, EMER if rr2.random() < 0.6 else EMER_HI)
        leaf(qd, lx, ly, a + 2.2, W * 0.024, W * 0.008, EMER_HI)
        if rr2.random() < 0.5:
            bud(qd, lx, ly, a - 1.9, W * 0.017,
                GOLD if rr2.random() < 0.5 else SAPPH_HI)

    # the corner spandrel: a quarter medallion sitting in the field's corner
    sp = W * 0.135
    qd.pieslice([F0 - sp, F0 - sp, F0 + sp, F0 + sp], 0, 90, fill=FIELD_IN)
    qd.pieslice([F0 - sp, F0 - sp, F0 + sp, F0 + sp], 0, 90, outline=GOLD,
                width=max(2, int(W * 0.005)))
    for k in range(5):
        a = math.radians(8 + k * 18.5)
        petal(qd, F0 + math.cos(a) * sp * 0.30, F0 + math.sin(a) * sp * 0.30,
              a, sp * 0.52, sp * 0.16, GOLD_HI if k % 2 else IVORY)
    rosette(qd, F0 + sp * 0.16, F0 + sp * 0.16, W * 0.030, n=6, pet=IVORY,
            heart=SAPPH, ring=GOLD)

    # mirror the quarter into all four
    im.paste(q, (0, 0), q)
    im.paste(q.transpose(Image.FLIP_LEFT_RIGHT), (H, 0), q.transpose(Image.FLIP_LEFT_RIGHT))
    im.paste(q.transpose(Image.FLIP_TOP_BOTTOM), (0, H), q.transpose(Image.FLIP_TOP_BOTTOM))
    im.paste(q.transpose(Image.ROTATE_180), (H, H), q.transpose(Image.ROTATE_180))
    d = ImageDraw.Draw(im)

    # ---- the centre medallion, over the join of the four quarters
    C = W // 2
    MR = W * 0.152
    for k in range(16):                          # the lobed outline
        a = k * math.pi / 8
        petal(d, C + math.cos(a) * MR * 0.52, C + math.sin(a) * MR * 0.52,
              a, MR * 0.60, MR * 0.20, PLUM if k % 2 else FIELD_IN)
    d.ellipse([C - MR * 0.74, C - MR * 0.74, C + MR * 0.74, C + MR * 0.74],
              fill=FIELD_IN, outline=GOLD, width=max(2, int(W * 0.006)))
    d.ellipse([C - MR * 0.62, C - MR * 0.62, C + MR * 0.62, C + MR * 0.62],
              fill=GROUND, outline=GOLD_HI, width=max(1, int(W * 0.003)))
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        leaf(d, C + math.cos(a) * MR * 0.16, C + math.sin(a) * MR * 0.16,
             a, MR * 0.46, MR * 0.13, EMER, EMER_HI)
    for k in range(8):
        a = k * math.pi / 4
        petal(d, C + math.cos(a) * MR * 0.12, C + math.sin(a) * MR * 0.12,
              a, MR * 0.44, MR * 0.15, GOLD_HI if k % 2 else IVORY)
    rosette(d, C, C, MR * 0.26, n=8, pet=IVORY, heart=SAPPH, ring=GOLD)
    # the two pendants, north and south of the medallion
    for sgn in (-1, 1):
        py = C + sgn * MR * 0.98
        palmette(d, C, py, math.pi / 2 if sgn > 0 else -math.pi / 2,
                 MR * 0.34, PLUM, GOLD)
        palmette(d, py, C, 0.0 if sgn > 0 else math.pi,
                 MR * 0.34, PLUM, GOLD)

    # ---- the borders
    d.rectangle([0, 0, W - 1, OUTER], fill=INK)
    d.rectangle([0, W - 1 - OUTER, W - 1, W - 1], fill=INK)
    d.rectangle([0, 0, OUTER, W - 1], fill=INK)
    d.rectangle([W - 1 - OUTER, 0, W - 1, W - 1], fill=INK)

    def band(a, b, fill):
        d.rectangle([a, a, W - 1 - a, b], fill=fill)
        d.rectangle([a, W - 1 - b, W - 1 - a, W - 1 - a], fill=fill)
        d.rectangle([a, a, b, W - 1 - a], fill=fill)
        d.rectangle([W - 1 - b, a, W - 1 - a, W - 1 - a], fill=fill)

    band(OUTER, OUTER + G1, GUARD)
    band(OUTER + G1, OUTER + G1 + BAND, PLUM)
    band(OUTER + G1 + BAND, F0, GUARD)

    # the running guard: a chain of small buds
    for gpos, gw in ((OUTER + G1 * 0.5, G1), (OUTER + G1 + BAND + G2 * 0.5, G2)):
        step = int(W * 0.036)
        for t in range(0, W, step):
            for (gx, gy, ang) in ((t + step / 2, gpos, 0),
                                  (t + step / 2, W - gpos, 0),
                                  (gpos, t + step / 2, math.pi / 2),
                                  (W - gpos, t + step / 2, math.pi / 2)):
                bud(d, gx, gy, ang, gw * 0.42, GOLD_HI)
                bud(d, gx, gy, ang + math.pi, gw * 0.42, GOLD_HI)

    # the main border: a scroll of palmettes on a vine, and it turns the corner
    MB = OUTER + G1 + BAND * 0.5
    step = int(W * 0.088)
    n = max(4, int((W - 2 * (OUTER + G1)) / step))
    step = (W - 2 * (OUTER + G1)) / n
    for i in range(n):
        t = OUTER + G1 + step * (i + 0.5)
        amp = BAND * 0.26 * (1 if i % 2 == 0 else -1)
        for (bx, by, rot) in ((t, MB, 0), (t, W - MB, 0),
                              (MB, t, math.pi / 2), (W - MB, t, math.pi / 2)):
            ca, sa = math.cos(rot), math.sin(rot)

            def P(u, v):
                return (bx + u * ca - v * sa, by + u * sa + v * ca)

            vine(d, P(-step * 0.55, amp), P(step * 0.55, -amp), BAND * 0.20,
                 GOLD, max(2, int(W * 0.0042)))
            palmette(d, *P(0, -amp * 0.55), rot + (math.pi / 2 if amp > 0 else -math.pi / 2),
                     BAND * 0.30, IVORY if i % 2 else GOLD_HI, GOLD)
            leaf(d, *P(-step * 0.28, amp * 0.5), rot + 2.5, BAND * 0.34, BAND * 0.10,
                 EMER_HI)
            leaf(d, *P(step * 0.28, -amp * 0.5), rot - 0.6, BAND * 0.34, BAND * 0.10,
                 EMER_HI)
            bud(d, *P(-step * 0.42, -amp * 0.35), rot + 1.2, BAND * 0.16, SAPPH_HI)
    # a rosette knots the border at each corner
    for (cxx, cyy) in ((MB, MB), (W - MB, MB), (MB, W - MB), (W - MB, W - MB)):
        rosette(d, cxx, cyy, BAND * 0.40, n=8, pet=IVORY, heart=SAPPH, ring=GOLD)

    # ---- the sparks, all around: gold thread in the field, jewel points in
    #      the border. Small and many - a glint, never a bead.
    glints(d, 340, (F0, F0, W - F0, W - F0), (GOLD_HI, GOLD, IVORY, SAPPH_HI, EMER_HI),
           W * 0.0016, W * 0.0036, 7)
    glints(d, 200, (OUTER, OUTER, W - OUTER, W - OUTER),
           (GOLD_HI, SAPPH_HI, EMER_HI), W * 0.0014, W * 0.0028, 11)

    out = weave(im, 232, nap=0.6, jitter=8.5, warp=0.34, seed=5)
    p = os.path.abspath(os.path.join(ASSETS, "t_carpet_d.jpg"))
    out.save(p, quality=94)
    return p, out


# ============================================================= THE CURTAIN
def _redye(src_name, lo, hi, size=512):
    """A photographed cloth re-dyed. The scan's luminance drives a two-tone
    ramp - every thread and slub of the real weave survives, only the colour
    changes. This is how the studios do it: scan first, dye after."""
    from PIL import ImageOps
    src = Image.open(os.path.join(ASSETS, "source", src_name)).convert("L")
    src = src.resize((size, size), Image.LANCZOS)
    src = ImageOps.autocontrast(src, cutoff=1)
    a = np.asarray(src).astype(np.float32) / 255.0
    out = np.zeros((size, size, 3), np.float32)
    for c in range(3):
        out[:, :, c] = lo[c] + (hi[c] - lo[c]) * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def bake_curtain():
    """REAL CLOTH AT LAST. The hand-drawn ogee lattice is retired - his
    verdict stood against every redraw. The drape now wears a photographed
    woven jacquard (PolyHaven CC0, assets/source/jacquard_cc0.jpg): actual
    thread, actual raised acanthus, re-dyed to the palace rose. Seamless
    because the scan is."""
    out = _redye("jacquard_cc0.jpg", (112, 60, 80), (198, 142, 162))
    p = os.path.abspath(os.path.join(ASSETS, "t_curtain_d.jpg"))
    out.save(p, quality=94)
    return p, out


def bake_avatar():
    """The avatar's abaya cloth: the same real jacquard, dyed nearly WHITE
    with the baby pink living in the weave's shadows - his correction: the
    mid-rose gown read as a grandmother's housecoat."""
    out = _redye("jacquard_cc0.jpg", (206, 168, 180), (250, 243, 245))
    p = os.path.abspath(os.path.join(ASSETS, "t_avatar_d.jpg"))
    out.save(p, quality=94)
    return p, out


def bake_cushion():
    """The majlis cushion in the same real jacquard, a shade brighter - the
    carpet-weave version at prop scale read as mottled STONES on the floor
    (his words, twice)."""
    out = _redye("jacquard_cc0.jpg", (150, 98, 118), (226, 180, 194))
    p = os.path.abspath(os.path.join(ASSETS, "t_cushion_d.jpg"))
    out.save(p, quality=94)
    return p, out


if __name__ == "__main__":
    from PIL import ImageStat
    for (p, img) in (bake_carpet(), bake_curtain(), bake_cushion(), bake_avatar()):
        st = ImageStat.Stat(img)
        print("WROTE", p, "mean", [round(v) for v in st.mean],
              "stddev", [round(v) for v in st.stddev])
