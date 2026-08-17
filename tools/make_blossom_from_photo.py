"""Cut real blossom canopy cards out of photographs.

The drawn version was vector cartoon art and had no business in this world.
These are cut from actual photographs of cherry blossom shot against sky: the
sky is keyed out on how BLUE it is against the warm petals and branches, which
separates cleanly because a petal is never bluer than it is red.

Output: assets/src/blossom_<name>_<n>.png, 512 square, real alpha.

    python tools/make_blossom_from_photo.py
"""
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "shots", "ref")
OUT = os.path.join(ROOT, "assets", "src")
# 512 RGBA of photographic noise is ~440kB, and it is PACKED INTO every
# flowering-tree glb: ten variants came to five megabytes of sheets alone.
# 352 costs a third of that and no one can tell at canopy distance.
S = 352

# source photo -> (output name, list of crop boxes as fractions l,t,r,b)
SOURCES = [
    ("r_sakura_8.jpg", "pink", [(0.00, 0.00, 0.42, 0.42),
                                (0.55, 0.13, 1.00, 0.62),
                                (0.16, 0.42, 0.62, 0.92)]),
    ("r_sakura_5.jpg", "pale", [(0.05, 0.05, 0.55, 0.55),
                                (0.45, 0.30, 0.95, 0.85)]),
    ("r_sakura_3.jpg", "white", [(0.08, 0.08, 0.58, 0.58),
                                 (0.42, 0.35, 0.92, 0.90)]),
    ("r_jacarandabl_2.jpg", "violet", [(0.10, 0.05, 0.55, 0.50),
                                       (0.50, 0.20, 0.95, 0.70)]),
]


def key_sky(im):
    """Alpha from how blue a pixel is against its own red. Sky is far bluer
    than red; petals, buds and bark never are."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = b - r                       # blueness
    # fully opaque where warm, gone where clearly blue, soft between
    alpha = np.clip(1.0 - (d - 2.0) / 20.0, 0.0, 1.0)
    # very bright washed sky can go neutral; cut it by brightness too
    lum = (r * 0.3 + g * 0.55 + b * 0.15)
    washed = np.clip((lum - 205.0) / 40.0, 0.0, 1.0) * np.clip((d + 6.0) / 12.0, 0.0, 1.0)
    alpha = np.clip(alpha - washed, 0.0, 1.0)
    return alpha


def ragged(card, seed):
    """Break the card's OUTLINE. A crop of a photograph is a solid rectangle
    of blossom, so every card in a canopy shows its four straight edges and
    the tree reads as a heap of postage stamps. The alpha is multiplied by a
    torn, noisy mask so the sheet ends in blossom rather than in a border."""
    rng = np.random.default_rng(seed)
    n = 64
    noise = rng.random((n, n)).astype(np.float32)
    nz = np.asarray(Image.fromarray((noise * 255).astype(np.uint8), "L")
                    .resize((S, S), Image.BICUBIC)).astype(np.float32) / 255.0
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = (S - 1) / 2.0
    rad = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
    # The rim wanders in and out; the MIDDLE is left alone. Letting the noise
    # act everywhere punched holes through the card and the blossom came out
    # moth-eaten, so its influence grows with the distance from the centre.
    edge = 1.04 + 0.34 * (nz - 0.5) * 2.0 * np.clip(rad, 0.0, 1.0)
    m = np.clip((edge - rad) / 0.26, 0.0, 1.0)
    m = m * m * (3 - 2 * m)
    a = np.asarray(card)[..., 3].astype(np.float32) / 255.0
    out = np.asarray(card).copy()
    out[..., 3] = np.clip(a * m, 0, 1) * 255
    return Image.fromarray(out, "RGBA")


def to_blossom_pink(card):
    """Lift the crop to the colour blossom actually reads as.

    A photograph carries its own shadow and its dark under-leaves, so a crop
    dropped straight into a canopy comes out dusty brick-red instead of the
    soft pink the tree is famous for. The dark end is raised and warmed toward
    the petal, the light end is left alone."""
    a = np.asarray(card).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3:]
    lum = (rgb[..., 0] * 0.34 + rgb[..., 1] * 0.5 + rgb[..., 2] * 0.16)[..., None]
    # how deep in shadow this pixel is
    dark = np.clip(1.0 - lum / 120.0, 0.0, 1.0)
    petal = np.array([246.0, 186.0, 206.0])          # the colour of the bloom
    rgb = rgb + (petal - rgb) * (dark * 0.30)        # lift only the shadows
    rgb = rgb * 1.04
    # keep it pink rather than magenta or brick
    rgb[..., 2] = np.maximum(rgb[..., 2], rgb[..., 0] * 0.72)
    rgb[..., 1] = np.maximum(rgb[..., 1], rgb[..., 0] * 0.66)
    out = np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def make(src, name, boxes):
    p = os.path.join(REF, src)
    if not os.path.exists(p):
        print("missing %s" % src)
        return
    im = Image.open(p).convert("RGB")
    W, H = im.size
    alpha = key_sky(im)
    rgba = np.dstack([np.asarray(im).astype(np.float32), alpha * 255.0]).astype(np.uint8)
    full = Image.fromarray(rgba, "RGBA")
    # soften the key by a hair so the cut edge is not a staircase
    aa = full.split()[3].filter(ImageFilter.GaussianBlur(0.8))
    full.putalpha(aa)
    for i, (l, t, r2, b2) in enumerate(boxes, 1):
        crop = full.crop((int(l * W), int(t * H), int(r2 * W), int(b2 * H)))
        crop = crop.resize((S, S), Image.LANCZOS)
        crop = ragged(crop, seed=i * 7 + len(name))
        crop = to_blossom_pink(crop)
        cov = np.asarray(crop)[..., 3].mean() / 255.0
        dst = os.path.join(OUT, "blossom_%s_%d.png" % (name, i))
        crop.save(dst, optimize=True)
        print("%-26s %5dkB  coverage %.0f%%" % (os.path.basename(dst),
                                                os.path.getsize(dst) // 1024, cov * 100))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    # the drawn sheets are replaced outright
    for f in os.listdir(OUT):
        if f.startswith("blossom_") and f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    for src, name, boxes in SOURCES:
        make(src, name, boxes)
