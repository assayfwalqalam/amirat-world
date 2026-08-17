"""The wall surfaces, final recipe. Two variants from one kitchen:

  t_adobe_d.jpg    plain weathered mud -- crazed two-tone cracks, clumped
                   light/dark zones, faint pakhsa joints, a ghost of brick
  t_adobe2_d.jpg   the BANDED wall he asked to keep -- the same cracks and
                   zones over strong pakhsa banding (the "zebra"), organic
                   edges, for a share of the buildings

Sharpness rules learned here: bake at 2048 (1.3 mm per pixel at the 2.6 m
tile), take the crack mask from a lightly-blurred diff so the hairline stays a
hairline, never blur the core, and finish with an unsharp pass. The palette is
measured from the reference screenshot (statistics, not pixels) and lifted
because a screen sample already contains its shading.

    python tools/make_adobe.py
"""
import math
import os
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
S = 2048
rnd = random.Random(11)


def melt(img2k, size):
    """Four differently-rotated quadrants blended, scaled to the canvas."""
    q = [
        img2k.crop((0, 0, 1024, 1024)),
        img2k.crop((1024, 0, 2048, 1024)).rotate(90),
        img2k.crop((0, 1024, 1024, 2048)).rotate(180),
        img2k.crop((1024, 1024, 2048, 2048)).rotate(270),
    ]
    q = [t.resize((size, size), Image.LANCZOS) for t in q]
    out = q[0].copy()
    small = 256
    for k, tile in enumerate(q[1:], 1):
        mask = Image.new("L", (small, small))
        mp = mask.load()
        for y in range(small):
            for x in range(small):
                v = 0.5 + 0.5 * math.sin((x + y * (0.6 + k * 0.3)) * 0.048 + k * 2.1)
                mp[x, y] = int(v * 165)
        out = Image.composite(tile, out, mask.resize((size, size), Image.BICUBIC))
    return out


def bands_mask(mode):
    """Pakhsa lifts, six moods:
      plain    joints and a whisper of tone
      banded   light and dark lifts alternating -- the approved zebra
      light    the whole wall in the lighter lift tone
      dark     the whole wall in the darker lift tone
      darkdom  mainly dark lifts with an occasional lighter one
      mix      every lift its own tone, plus large drifting patches
    """
    b = Image.new("L", (S, S), 128)
    bd = ImageDraw.Draw(b)
    row = 0
    while row < S + 120:
        bh = rnd.randrange(300, 524)
        floor_ = 0.76
        if mode == "banded":
            tone = rnd.choice((-18, -14, -10, 10, 14, 18))
        elif mode == "light":
            tone = rnd.choice((8, 10, 12, 14))
            floor_ = 0.85
        elif mode == "dark":
            tone = rnd.choice((-20, -17, -14, -12))
            floor_ = 0.85
        elif mode == "darkdom":
            tone = rnd.choice((-20, -17, -14, -12, -14, 12, 15))
        elif mode == "mix":
            tone = rnd.choice((-20, -15, -10, -5, 5, 10, 14, 18))
        else:
            tone = rnd.choice((-4, -2, 0, 2, 4))
            floor_ = 0.30
        ph1, ph2 = rnd.uniform(0, 6.3), rnd.uniform(0, 6.3)
        for x in range(S):
            sway = floor_ + (1 - floor_) * (0.5 + 0.5 * math.sin(x * 0.003 + ph1)) \
                                         * (0.5 + 0.5 * math.sin(x * 0.0012 + ph2))
            t = 128 + tone * sway
            edge = int(math.sin(x * 0.01 + row) * 10 + math.sin(x * 0.0035 + row * 3) * 16)
            y0, y1 = row + edge, min(S, row + bh + edge)
            if y1 > max(0, y0):
                bd.line([(x, max(0, y0)), (x, y1 - 1)], fill=int(t))
        for x in range(S):
            yy = (row + int(math.sin(x * 0.01 + row) * 10)) % S
            bd.line([(x, yy), (x, min(S - 1, yy + 3))], fill=116 if mode == "plain" else 112)
        row += bh
    return b.filter(ImageFilter.GaussianBlur(2.2))


def build(mode, out_name):
    plaster = Image.open(os.path.join(A, "src", "plastered_wall_diff.jpg")).convert("RGB").resize((S, S), Image.LANCZOS)
    mud2k = Image.open(os.path.join(A, "src", "mud_cracked_dry_03_diff.jpg")).convert("L")
    mud = melt(mud2k, S)
    blur = mud.filter(ImageFilter.GaussianBlur(10))
    lowf = mud.filter(ImageFilter.GaussianBlur(80))

    bands = bands_mask(mode)

    # the cracks: dark hairline core inside a paler dust rim, masks from the
    # photo itself so the shapes stay organic. The core is NEVER blurred.
    diff = ImageChops.subtract(mud, blur, 1, 128)
    core = diff.point(lambda v: 255 if v < 96 else 0)
    halo_src = core.filter(ImageFilter.GaussianBlur(4.5))
    zone_src = lowf.filter(ImageFilter.GaussianBlur(14))

    # exposed brick, faint
    brick = Image.new("L", (S, S), 0)
    bkd = ImageDraw.Draw(brick)
    for _ in range(rnd.randrange(2, 4)):
        cx0, cy0 = rnd.randrange(S), rnd.randrange(S)
        rw, rh = rnd.randrange(240, 600), rnd.randrange(180, 420)
        blob = []
        for a in range(0, 360, 18):
            rr = 1.0 + rnd.uniform(-0.34, 0.34)
            blob.append((cx0 + math.cos(math.radians(a)) * rw * rr / 2,
                         cy0 + math.sin(math.radians(a)) * rh * rr / 2))
        bkd.polygon(blob, fill=184)
    brick = brick.filter(ImageFilter.GaussianBlur(18))

    courses = Image.new("L", (S, S), 128)
    cd2 = ImageDraw.Draw(courses)
    bh2, bw2 = 84, 192
    for row2 in range(0, S + bh2, bh2):
        off = (row2 // bh2 % 2) * (bw2 // 2)
        for x in range(S):
            yy = (row2 + int(math.sin(x * 0.015) * 4)) % S
            cd2.line([(x, yy), (x, min(S - 1, yy + 2))], fill=102)
        for bx2 in range(0, S, bw2):
            xx = (bx2 + off) % S
            cd2.line([(xx, row2), (xx, min(S - 1, row2 + bh2))], fill=104)
    courses = courses.filter(ImageFilter.GaussianBlur(1.0))

    def sstep(a, b, v):
        t = max(0.0, min(1.0, (v - a) / (b - a)))
        return t * t * (3 - 2 * t)

    out = Image.new("RGB", (S, S))
    pp, mp, bp, lp, op, bx = (plaster.load(), mud.load(), blur.load(),
                              lowf.load(), out.load(), bands.load())
    bk, cs = brick.load(), courses.load()
    cr, hl, zn = core.load(), halo_src.load(), zone_src.load()
    patch2 = lowf.rotate(90).filter(ImageFilter.GaussianBlur(26))
    pz2 = patch2.load()
    for y in range(S):
        for x in range(S):
            m = 1.0 + (mp[x, y] - bp[x, y]) / 128.0 * 0.26 + (lp[x, y] - 128) / 128.0 * 0.14
            m *= bx[x, y] / 128.0
            if mode == "mix":
                z2 = pz2[x, y]
                m *= 1.0 + 0.11 * sstep(150, 168, z2) - 0.12 * sstep(106, 88, z2)
            z = zn[x, y]
            m *= 1.0 + 0.07 * sstep(138, 148, z) - 0.09 * sstep(120, 110, z)

            pr, pg, pb = pp[x, y]
            h = hl[x, y] / 255.0
            if h > 0.10 and cr[x, y] < 128:
                k2 = min(1.0, h * 1.5)
                pr *= 1.0 + 0.05 * k2
                pg *= 1.0 + 0.04 * k2
                pb *= 1.0 + 0.015 * k2
            if cr[x, y] >= 128:
                pr *= 0.84
                pg *= 0.84
                pb *= 0.855

            w2 = bk[x, y] / 255.0
            if w2 > 0.02:
                cm = cs[x, y] / 128.0
                pr = pr * (1 - w2) + pr * cm * 0.985 * w2
                pg = pg * (1 - w2) + pg * cm * 0.945 * w2
                pb = pb * (1 - w2) + pb * cm * 0.905 * w2
            op[x, y] = (max(0, min(255, int(pr * m))),
                        max(0, min(255, int(pg * m))),
                        max(0, min(255, int(pb * m))))

    # their palette, measured, lifted for shading
    ref = Image.open(os.path.join(ROOT, "shots", "ref", "ursilat_2.jpg")).convert("RGB")
    patch = list(ref.crop((1620, 760, 1860, 870)).getdata())
    n = len(patch)
    rm = [sum(p[c] for p in patch) / n for c in range(3)]
    rsd = [(sum((p[c] - rm[c]) ** 2 for p in patch) / n) ** 0.5 for c in range(3)]
    src = [op[x, y] for y in range(0, S, 5) for x in range(0, S, 5)]
    k = len(src)
    sm = [sum(p[c] for p in src) / k for c in range(3)]
    ssd = [(sum((p[c] - sm[c]) ** 2 for p in src) / k) ** 0.5 for c in range(3)]
    for y in range(S):
        for x in range(S):
            px = op[x, y]
            op[x, y] = tuple(max(0, min(255, int(
                ((px[c] - sm[c]) * min(1.35, rsd[c] / ssd[c]) + rm[c]) * 1.12))) for c in range(3))

    # the palette match pulls every variant to the same mean, which erased
    # the very difference these moods exist for -- restore it afterwards
    GAIN = {"light": 1.07, "dark": 0.80, "darkdom": 0.87}.get(mode, 1.0)
    if GAIN != 1.0:
        out = out.point(lambda v: max(0, min(255, int(v * GAIN))))

    # the sharpening he asked for
    out = out.filter(ImageFilter.UnsharpMask(radius=2.4, percent=95, threshold=2))
    out.save(os.path.join(A, out_name), quality=92)
    print(out_name, "baked at", S)


def main():
    build("plain", "t_adobe_d.jpg")
    build("banded", "t_adobe2_d.jpg")
    build("light", "t_adobe3_d.jpg")
    build("dark", "t_adobe4_d.jpg")
    build("darkdom", "t_adobe5_d.jpg")
    build("mix", "t_adobe6_d.jpg")

    # one relief map serves both, melted the same way as the marks
    nor2k = Image.open(os.path.join(A, "src", "mud_nor.jpg")).convert("RGB")
    NS = 1024
    nout = melt(nor2k.convert("RGB").resize((2048, 2048)), NS) if False else None
    norq = [
        nor2k.crop((0, 0, 1024, 1024)),
        nor2k.crop((1024, 0, 2048, 1024)).rotate(90),
        nor2k.crop((0, 1024, 1024, 2048)).rotate(180),
        nor2k.crop((1024, 1024, 2048, 2048)).rotate(270),
    ]
    norq = [t.resize((NS, NS), Image.LANCZOS) for t in norq]
    nres = norq[0].copy()
    small = 256
    for k2, tile in enumerate(norq[1:], 1):
        mask = Image.new("L", (small, small))
        mp2 = mask.load()
        for y in range(small):
            for x in range(small):
                v = 0.5 + 0.5 * math.sin((x + y * (0.6 + k2 * 0.3)) * 0.048 + k2 * 2.1)
                mp2[x, y] = int(v * 165)
        nres = Image.composite(tile, nres, mask.resize((NS, NS), Image.BICUBIC))
    n1 = Image.open(os.path.join(A, "src", "plastered_wall_nor.jpg")).convert("RGB").resize((NS, NS), Image.LANCZOS)
    Image.blend(n1, nres, 0.55).save(os.path.join(A, "t_adobe_gn.jpg"), quality=90)
    print("relief map in step with both")


if __name__ == "__main__":
    main()
