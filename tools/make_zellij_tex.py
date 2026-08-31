# The tiled dado of the palace, and the floral band that runs above it.
#   python tools/make_zellij_tex.py  ->  assets/t_zellij_d.jpg
#                                        assets/t_floral_d.jpg
#
# The hall's dado was wearing the DOME's violet - a flat painted stripe that
# read as nothing at eye level. A dado in an Andalusi hall is TILE: small cut
# pieces locked into a star pattern, glazed, and catching the lamplight in
# little facets. And above it runs a band of stems and flowers.
#
# Both tile seamlessly in both directions.
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
SIZE = 512
SS = 3
W = SIZE * SS

# the glaze pot. The first mix ran dark - plum crosses on dark grout read as
# a red-brown wallpaper across a room. Real dado zellij is LIGHT: white and
# honey carry it, green and blue are the accents, the grout is pale lime.
WHITE = (242, 236, 224)
HONEY = (212, 172, 100)
EMER = (62, 128, 104)
SAPPH = (70, 100, 158)
PLUM = (96, 126, 150)   # a soft sky where the plum was
ROSE = (196, 130, 154)
GROUT = (134, 120, 108)  # pale lime between the pieces


def glazed(img, seed=3, chip=1.0):
    """Fired clay under a glaze: uneven colour, a wet sheen, chipped edges."""
    rng = np.random.default_rng(seed)
    a = np.asarray(img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)).astype(np.float32)
    # the glaze pools and thins across each piece
    n = rng.normal(0, 1, (SIZE // 8, SIZE // 8))
    n = np.asarray(Image.fromarray(((n - n.min()) / (np.ptp(n) + 1e-6) * 255).astype(np.uint8))
                   .resize((SIZE, SIZE), Image.BICUBIC)).astype(np.float32)
    a += (n - 128)[:, :, None] * 0.14 * chip
    a += rng.normal(0, 4.0, a.shape)
    a = np.clip(a, 0, 255).astype(np.uint8)
    out = Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.35))
    return out


def bake_zellij():
    im = Image.new("RGB", (W, W), GROUT)
    d = ImageDraw.Draw(im)
    N = 2                                  # two stars across the tile
    cell = W / float(N)
    G = W * 0.0055                          # the grout line

    def star(cx, cy, r, pts=8, body=WHITE, arm=HONEY, eye=SAPPH):
        """An eight point star with its arms, cut as separate pieces."""
        for k in range(pts):
            a0 = k * 2 * math.pi / pts
            a1 = a0 + math.pi / pts
            a2 = a0 + 2 * math.pi / pts
            p = [(cx + math.cos(a0) * r * 0.46, cy + math.sin(a0) * r * 0.46),
                 (cx + math.cos(a1) * r, cy + math.sin(a1) * r),
                 (cx + math.cos(a2) * r * 0.46, cy + math.sin(a2) * r * 0.46),
                 (cx, cy)]
            d.polygon(p, fill=body if k % 2 else arm)
        d.regular_polygon((cx, cy, r * 0.30), pts, fill=eye)
        d.regular_polygon((cx, cy, r * 0.30 - G), pts, fill=WHITE)
        d.regular_polygon((cx, cy, r * 0.15), pts, fill=eye)

    def cross(cx, cy, r, body=EMER):
        """The four armed piece that fills between the stars."""
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            p = [(cx + math.cos(a - 0.5) * r * 0.5, cy + math.sin(a - 0.5) * r * 0.5),
                 (cx + math.cos(a) * r, cy + math.sin(a) * r),
                 (cx + math.cos(a + 0.5) * r * 0.5, cy + math.sin(a + 0.5) * r * 0.5),
                 (cx, cy)]
            d.polygon(p, fill=body)
        d.regular_polygon((cx, cy, r * 0.26), 8, fill=HONEY)

    for gy in range(-1, N + 1):
        for gx in range(-1, N + 1):
            x = (gx + 0.5) * cell
            y = (gy + 0.5) * cell
            star(x, y, cell * 0.46, 8, WHITE, HONEY, SAPPH)
            cross(x + cell * 0.5, y + cell * 0.5, cell * 0.30, EMER)
            cross(x + cell * 0.5, y, cell * 0.19, PLUM)
            cross(x, y + cell * 0.5, cell * 0.19, PLUM)

    out = glazed(im, 3, 1.0)
    p = os.path.abspath(os.path.join(ASSETS, "t_zellij_d.jpg"))
    out.save(p, quality=94)
    return p, out


def bake_floral():
    """The carved STUCCO field. The gold-on-tan version was the wall he
    condemned - "the gold on the wall is too random and the pattern as well,
    no sense of copying from actual ancient housing". Real Andalusi wall
    fields are carved plaster: cream on cream, the pattern read by the SHADOW
    in the carving, and the gold kept for the one band under it. Same
    endless stem-leaf-rosette net, but in plaster now - the motifs sit a
    shade lighter than the ground and an emboss pass cuts the shadow under
    every edge. It tiles in both directions."""
    GRND = (211, 201, 182)
    SHADE = (168, 156, 136)
    GOLD = (222, 213, 196)      # the raised plaster, not gold any more
    GOLD_HI = (229, 221, 205)
    im = Image.new("RGB", (W, W), GRND)
    d = ImageDraw.Draw(im)
    rnd = random.Random(77)

    def wrapped(fn):
        for ox in (-W, 0, W):
            for oy in (-W, 0, W):
                fn(ox, oy)

    def leaf(dd, x, y, a, ln, wd, fill):
        pts = []
        for side in (1, -1):
            rng = range(0, 17) if side > 0 else range(16, -1, -1)
            for i in rng:
                t = i / 16.0
                w = wd * math.sin(math.pi * t ** 0.8) * side
                pts.append((x + math.cos(a) * ln * t - math.sin(a) * w,
                            y + math.sin(a) * ln * t + math.cos(a) * w))
        dd.polygon(pts, fill=fill, outline=SHADE, width=max(1, int(wd * 0.22)))

    def rosette(dd, x, y, r, n=8):
        for k in range(n):
            a = k * 2 * math.pi / n
            leaf(dd, x + math.cos(a) * r * 0.16, y + math.sin(a) * r * 0.16,
                 a, r * 0.92, r * 0.30, GOLD_HI if k % 2 else GOLD)
        dd.ellipse([x - r * 0.22, y - r * 0.22, x + r * 0.22, y + r * 0.22],
                   fill=GOLD, outline=SHADE, width=2)

    # the stem lattice: a wave running each way, crossing at the rosettes.
    # TWO crossings per tile, not three: with the tile laid at 1.6m the
    # rosettes come out a third of a metre wide - carving, not dots.
    N = 2
    cell = W / float(N)
    for gy in range(N + 1):
        for gx in range(N + 1):
            bx, by = gx * cell, gy * cell + (cell * 0.5 if gx % 2 else 0.0)

            def draw(ox, oy, bx=bx, by=by, gx=gx, gy=gy):
                x, y = bx + ox, by + oy
                if x < -cell or x > W + cell or y < -cell or y > W + cell:
                    return
                dd = ImageDraw.Draw(im)
                # the two stems out of this crossing, bowed
                for (dxs, dys) in ((1, 0), (0, 1)):
                    pts = []
                    for k in range(25):
                        t = k / 24.0
                        pts.append((x + dxs * cell * t - dys * math.sin(t * math.pi) * cell * 0.16,
                                    y + dys * cell * t + dxs * math.sin(t * math.pi) * cell * 0.16))
                    dd.line(pts, fill=GOLD, width=max(3, int(W * 0.0055)), joint="curve")
                    for (t, sgn) in ((0.28, 1), (0.62, -1)):
                        px = pts[int(t * 24)][0]
                        py = pts[int(t * 24)][1]
                        ang = math.atan2(dys, dxs) + sgn * 1.25
                        leaf(dd, px, py, ang, cell * 0.20, cell * 0.062, GOLD_HI)
                        leaf(dd, px, py, ang + sgn * 0.75, cell * 0.14, cell * 0.045, GOLD)
                rosette(dd, x, y, cell * 0.155, 8)
                # a bud in the middle of each square of the net
                leaf(dd, x + cell * 0.5, y + cell * 0.5, -math.pi / 2,
                     cell * 0.17, cell * 0.075, GOLD_HI)
                leaf(dd, x + cell * 0.5, y + cell * 0.5, math.pi / 2,
                     cell * 0.17, cell * 0.075, GOLD)

            wrapped(draw)

    # THE CARVING, CUT INTO REAL PLASTER. The drawn canvas above is only the
    # STENCIL now: its motif mask is lifted and pressed into a photographed
    # lime-plaster scan (PolyHaven CC0, assets/source/plaster_cc0.jpg),
    # re-tinted warm cream. Every pore and trowel mark in the field is real;
    # the relief is read the way real carving is read - by its own shadow.
    lum = np.asarray(im).astype(np.float32).mean(axis=2)
    mask = (lum > (GRND[0] + GRND[1] + GRND[2]) / 3.0 + 4.0).astype(np.float32)
    mimg = Image.fromarray((mask * 255).astype(np.uint8)).resize(
        (SIZE, SIZE), Image.LANCZOS)
    m = np.asarray(mimg).astype(np.float32) / 255.0
    pl = Image.open(os.path.join(ASSETS, "source", "plaster_cc0.jpg"))
    pa = np.asarray(pl.convert("RGB").resize((SIZE, SIZE),
                                             Image.LANCZOS)).astype(np.float32)
    tgt = (209, 201, 185)
    mean = pa.mean(axis=(0, 1))
    for c in range(3):
        pa[:, :, c] *= tgt[c] / max(mean[c], 1.0)
    sh = max(2, SIZE // 170)
    shadow = np.clip(np.roll(np.roll(m, sh, 0), sh, 1) - m, 0, 1)
    lit = np.clip(np.roll(np.roll(m, -sh, 0), -sh, 1) - m, 0, 1)
    pa += m[:, :, None] * 11.0            # the raised motif, a shade lighter
    pa -= shadow[:, :, None] * 58.0       # the undercut
    pa += lit[:, :, None] * 26.0          # the lit arris
    out = Image.fromarray(np.clip(pa, 0, 255).astype(np.uint8))
    p = os.path.abspath(os.path.join(ASSETS, "t_floral_d.jpg"))
    out.save(p, quality=94)
    return p, out


if __name__ == "__main__":
    from PIL import ImageStat
    random.seed(4)
    for (p, img) in (bake_zellij(), bake_floral()):
        print("WROTE", p, "mean", [round(v) for v in ImageStat.Stat(img).mean])
