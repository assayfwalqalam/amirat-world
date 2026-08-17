"""All the non-adobe surfaces, from CC0 photo sources where one exists.

  t_ashlar_d/gn   cut sandstone, from the photographed blocks, with the same
                  two-tone crack treatment as the mud
  t_wood_d        weathered timber (photo)
  t_plank_d       grey planks for fences and carts (photo)
  t_leather_d     book leather, embossed
  t_metal1..3_d   painted vehicle metal, sun-bleached, scratched, rusty
  g_gravel_d      ground: real sandy gravel (photo)
  g_rock_d        ground: real rocky terrain (photo)

    python tools/make_surfaces.py
"""
import math
import os
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
SRC = os.path.join(A, "src")
rnd = random.Random(29)


def crackline_pass(img, strength_core=0.86, strength_halo=0.05):
    """The two-tone crack treatment he approved, applied to any surface."""
    S = img.size[0]
    g = img.convert("L")
    blur = g.filter(ImageFilter.GaussianBlur(10))
    diff = ImageChops.subtract(g, blur, 1, 128)
    core = diff.point(lambda v: 255 if v < 100 else 0)
    halo = core.filter(ImageFilter.GaussianBlur(4.0))
    px, cr, hl = img.load(), core.load(), halo.load()
    for y in range(S):
        for x in range(S):
            pr, pg, pb = px[x, y]
            h = hl[x, y] / 255.0
            if h > 0.10 and cr[x, y] < 128:
                k = min(1.0, h * 1.5)
                pr = int(pr * (1 + strength_halo * k))
                pg = int(pg * (1 + strength_halo * 0.8 * k))
                pb = int(pb * (1 + strength_halo * 0.3 * k))
            if cr[x, y] >= 128:
                pr = int(pr * strength_core)
                pg = int(pg * strength_core)
                pb = int(pb * (strength_core + 0.015))
            px[x, y] = (min(255, pr), min(255, pg), min(255, pb))
    return img


def ashlar():
    S = 2048
    base = Image.open(os.path.join(SRC, "sandstone_blocks_05_diff.jpg")).convert("RGB").resize((S, S), Image.LANCZOS)
    # per-block tone: find the courses roughly by a grid matched to the photo's
    # block size and vary each cell a little
    cell_w, cell_h = 256, 128
    px = base.load()
    for cy in range(0, S, cell_h):
        for cx in range(0, S, cell_w):
            t = 1.0 + rnd.uniform(-0.055, 0.055)
            for y in range(cy, min(S, cy + cell_h)):
                for x in range(cx, min(S, cx + cell_w)):
                    r, g, b = px[x, y]
                    px[x, y] = (min(255, int(r * t)), min(255, int(g * t)), min(255, int(b * t)))
    base = crackline_pass(base, 0.88, 0.04)
    base = base.filter(ImageFilter.UnsharpMask(radius=2.2, percent=80, threshold=2))
    base.save(os.path.join(A, "t_ashlar_d.jpg"), quality=92)
    print("t_ashlar_d from photographed blocks")


def timber():
    for src, dst, q in (("weathered_planks_diff.jpg", "t_wood_d.jpg", 92),
                        ("wood_planks_grey_diff.jpg", "t_plank_d.jpg", 90)):
        p = os.path.join(SRC, src)
        if not os.path.exists(p):
            print("missing", src)
            continue
        im = Image.open(p).convert("RGB").resize((1024, 1024), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=70, threshold=2))
        im.save(os.path.join(A, dst), quality=q)
        print(dst, "from photo")


def leather():
    S = 1024
    im = Image.new("RGB", (S, S), (96, 62, 36))
    px = im.load()
    for y in range(S):
        for x in range(S):
            v = 8 * math.sin(x * 0.07 + math.sin(y * 0.05) * 3) + rnd.gauss(0, 5)
            g = 4 * math.sin(y * 0.11 + x * 0.013)
            r0, g0, b0 = 96 + v + g, 62 + v * 0.8, 36 + v * 0.5
            px[x, y] = (max(0, min(255, int(r0))), max(0, min(255, int(g0))), max(0, min(255, int(b0))))
    d = ImageDraw.Draw(im)
    # blind-tooled border and centre lozenge, the classic binding
    for k in (40, 56):
        d.rectangle([k, k, S - k, S - k], outline=(66, 40, 22), width=5)
    cx = S // 2
    pts = [(cx, S // 2 - 190), (cx + 150, S // 2), (cx, S // 2 + 190), (cx - 150, S // 2)]
    d.polygon(pts, outline=(66, 40, 22))
    d.polygon([(p[0] * 0.97 + cx * 0.03, p[1] * 0.97 + S // 2 * 0.03) for p in pts], outline=(150, 108, 54))
    im = im.filter(ImageFilter.SMOOTH)
    im.save(os.path.join(A, "t_leather_d.jpg"), quality=92)
    print("t_leather_d embossed")


def metal():
    cols = [(122, 128, 118), (140, 110, 70), (86, 100, 120)]
    for i, c in enumerate(cols, 1):
        S = 1024
        im = Image.new("RGB", (S, S), c)
        px = im.load()
        # broad weather: bleached panels, grimy panels, a dusty cast low down
        blot = Image.new("L", (8, 8))
        blot.putdata([rnd.randrange(0, 255) for _ in range(64)])
        blot = blot.resize((S, S), Image.BICUBIC).load()
        dust = Image.new("L", (6, 6))
        dust.putdata([rnd.randrange(0, 255) for _ in range(36)])
        dust = dust.resize((S, S), Image.BICUBIC).load()
        for y in range(S):
            for x in range(S):
                v = rnd.gauss(0, 5) + 6 * math.sin(y * 0.01 + x * 0.002)
                b = blot[x, y]
                if b > 175:
                    v += (b - 175) * 0.30          # sun-bleach
                elif b < 85:
                    v -= (85 - b) * 0.28           # grime
                du = dust[x, y]
                dr = (du - 128) * 0.10 if du > 128 else 0
                r0 = c[0] + v + dr * 1.3
                px[x, y] = (max(0, min(255, int(r0))),
                            max(0, min(255, int(c[1] + v * 0.95 + dr))),
                            max(0, min(255, int(c[2] + v * 0.9 + dr * 0.5))))
        d = ImageDraw.Draw(im)
        for _ in range(240):                     # scratches
            x0, y0 = rnd.randrange(S), rnd.randrange(S)
            ln = rnd.randrange(20, 160)
            a = rnd.uniform(0, 6.3)
            for k in range(ln):
                d.point((int(x0 + math.cos(a) * k) % S, int(y0 + math.sin(a) * k) % S),
                        fill=(min(255, c[0] + 44), min(255, c[1] + 44), min(255, c[2] + 40)))
        for _ in range(90):                      # rust runs
            x0, y0 = rnd.randrange(S), rnd.randrange(S)
            ln = rnd.randrange(30, 190)
            w = rnd.randrange(2, 6)
            for k in range(ln):
                for t in range(w):
                    px[(x0 + t + int(math.sin(k * 0.06) * 2)) % S, (y0 + k) % S] = (
                        108 + rnd.randrange(0, 30), 62 + rnd.randrange(0, 18), 30)
        im = im.filter(ImageFilter.SMOOTH)
        im.save(os.path.join(A, "t_metal%d_d.jpg" % i), quality=90)
    print("t_metal1..3_d painted, scratched, rusted")


def ground():
    for src, dst in (("sandy_gravel_02_diff.jpg", "g_gravel_d.jpg"),
                     ("rocks_ground_06_diff.jpg", "g_rock_d.jpg")):
        p = os.path.join(SRC, src)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((1024, 1024), Image.LANCZOS)
            im.save(os.path.join(A, dst), quality=90)
            print(dst, "from photo")


if __name__ == "__main__":
    ashlar()
    timber()
    leather()
    metal()
    ground()
