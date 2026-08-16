"""The wall surface, final recipe. CC0 photo sources, their palette measured
from the reference he named, and two defences against visible repetition:

  1. the four quadrants of the 2k mud photo are each rotated differently and
     melted across the tile, so no crack loop survives with a recognisable
     shape to spot twice
  2. the tile itself covers 2.6 m of wall (set in the generators), so what
     repeats does so less than half as often

    python tools/make_adobe.py
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
S = 1024
rnd = random.Random(11)


def quadrant_melt(img2k):
    """Four differently-rotated quadrants blended with smooth masks."""
    q = [
        img2k.crop((0, 0, 1024, 1024)),
        img2k.crop((1024, 0, 2048, 1024)).rotate(90),
        img2k.crop((0, 1024, 1024, 2048)).rotate(180),
        img2k.crop((1024, 1024, 2048, 2048)).rotate(270),
    ]
    out = q[0].copy()
    for k, tile in enumerate(q[1:], 1):
        mask = Image.new("L", (S, S))
        mp = mask.load()
        for y in range(S):
            for x in range(S):
                # each layer fades in over a different diagonal wave
                v = 0.5 + 0.5 * math.sin((x + y * (0.6 + k * 0.3)) * 0.006 + k * 2.1)
                mp[x, y] = int(v * 165)
        out = Image.composite(tile, out, mask)
    return out


def main():
    plaster = Image.open(os.path.join(A, "src", "plastered_wall_diff.jpg")).convert("RGB").resize((S, S), Image.LANCZOS)
    mud2k = Image.open(os.path.join(A, "src", "mud_cracked_dry_03_diff.jpg")).convert("L")
    mud = quadrant_melt(mud2k)
    blur = mud.filter(ImageFilter.GaussianBlur(14))
    lowf = mud.filter(ImageFilter.GaussianBlur(52))

    # pakhsa banding as relief: wandering joint shadows, barely-there tone
    bands = Image.new("L", (S, S), 128)
    bd = ImageDraw.Draw(bands)
    bh = 200                       # ~0.5 m per lift at the 2.6 m tile
    for i, row in enumerate(range(0, S + bh, bh)):
        tone = 128 + rnd.choice((-3, -1, 0, 1, 3))
        for x in range(S):
            edge = int(math.sin(x * 0.02 + row) * 5 + math.sin(x * 0.007 + row * 3) * 7)
            for yy in range(row + edge, min(S, row + bh + edge)):
                if 0 <= yy < S:
                    bd.point((x, yy), fill=tone)
        for x in range(S):
            yy = (row + int(math.sin(x * 0.02 + row) * 5)) % S
            bd.point((x, yy), fill=115)
            bd.point((x, (yy + 1) % S), fill=121)
    bands = bands.filter(ImageFilter.GaussianBlur(1.4))

    out = Image.new("RGB", (S, S))
    pp, mp, bp, lp, op, bx = (plaster.load(), mud.load(), blur.load(),
                              lowf.load(), out.load(), bands.load())
    for y in range(S):
        for x in range(S):
            m = 1.0 + (mp[x, y] - bp[x, y]) / 128.0 * 0.40 + (lp[x, y] - 128) / 128.0 * 0.24
            m *= bx[x, y] / 128.0
            pr, pg, pb = pp[x, y]
            op[x, y] = (max(0, min(255, int(pr * m))),
                        max(0, min(255, int(pg * m))),
                        max(0, min(255, int(pb * m))))

    # their palette, measured on the reference panorama's lit foreground wall,
    # lifted because a screen sample already contains the shading
    ref = Image.open(os.path.join(ROOT, "shots", "ref", "ursilat_2.jpg")).convert("RGB")
    patch = list(ref.crop((1620, 760, 1860, 870)).getdata())
    n = len(patch)
    rm = [sum(p[c] for p in patch) / n for c in range(3)]
    rsd = [(sum((p[c] - rm[c]) ** 2 for p in patch) / n) ** 0.5 for c in range(3)]
    src = [op[x, y] for y in range(0, S, 3) for x in range(0, S, 3)]
    k = len(src)
    sm = [sum(p[c] for p in src) / k for c in range(3)]
    ssd = [(sum((p[c] - sm[c]) ** 2 for p in src) / k) ** 0.5 for c in range(3)]
    for y in range(S):
        for x in range(S):
            px = op[x, y]
            op[x, y] = tuple(max(0, min(255, int(
                ((px[c] - sm[c]) * min(1.35, rsd[c] / ssd[c]) + rm[c]) * 1.12))) for c in range(3))
    out.save(os.path.join(A, "t_adobe_d.jpg"), quality=94)

    # the relief follows the same melt, so bumps sit where the marks are
    nor2k = Image.open(os.path.join(A, "src", "mud_nor.jpg")).convert("RGB")
    norq = [
        nor2k.crop((0, 0, 1024, 1024)),
        nor2k.crop((1024, 0, 2048, 1024)).rotate(90),
        nor2k.crop((0, 1024, 1024, 2048)).rotate(180),
        nor2k.crop((1024, 1024, 2048, 2048)).rotate(270),
    ]
    nout = norq[0].copy()
    for k2, tile in enumerate(norq[1:], 1):
        mask = Image.new("L", (S, S))
        mp2 = mask.load()
        for y in range(S):
            for x in range(S):
                v = 0.5 + 0.5 * math.sin((x + y * (0.6 + k2 * 0.3)) * 0.006 + k2 * 2.1)
                mp2[x, y] = int(v * 165)
        nout = Image.composite(tile, nout, mask)
    n1 = Image.open(os.path.join(A, "src", "plastered_wall_nor.jpg")).convert("RGB").resize((S, S), Image.LANCZOS)
    Image.blend(n1, nout, 0.55).save(os.path.join(A, "t_adobe_gn.jpg"), quality=90)
    print("adobe final: quadrant-melted, palette-matched, relief in step")


if __name__ == "__main__":
    main()
