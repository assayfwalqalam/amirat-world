# Caps the loose textures the engine loads by URL.
#   python tools/shrink_loose.py [--dry]
#
# Measured on the live host: 31 loose images, 12 MB, and they were the slowest
# things in the whole load - t_adobe_r took 4.6 seconds, the wall photographs
# are 2048x2048 and there are seven of them. They tile heavily on the buildings
# and the ground, so half the size costs nothing anyone can see, and the
# normal and roughness maps carry even less detail than the colour.
#
# The sky is left alone: it is one image, it fills the whole background, and
# it is already only 0.45 MB.
import os, sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
DRY = "--dry" in sys.argv

KEEP = ("puresky", "moon.png", "flame.png", "glow.png", "ember", "firepool",
        "ray.png", "grass_card", "reed_card", "cloud")

CAP_COLOUR = 1024          # wall and ground photographs
CAP_DATA = 512             # normal and roughness maps: even less detail needed

tb = ta = 0
n = 0
for fn in sorted(os.listdir(A)):
    if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    if any(k in fn for k in KEEP):
        continue
    p = os.path.join(A, fn)
    before = os.path.getsize(p)
    im = Image.open(p)
    w, h = im.size
    cap = CAP_DATA if (fn.endswith("_n.jpg") or fn.endswith("_r.jpg") or "_gn" in fn) else CAP_COLOUR
    if max(w, h) <= cap:
        tb += before
        ta += before
        continue
    r = cap / float(max(w, h))
    im2 = im.resize((max(1, int(w * r)), max(1, int(h * r))), Image.LANCZOS)
    if not DRY:
        if fn.lower().endswith(".png") and im.mode in ("RGBA", "LA", "P"):
            im2.save(p, optimize=True)
        else:
            im2.convert("RGB").save(p, quality=88, optimize=True)
    after = os.path.getsize(p) if not DRY else int(before * r * r)
    tb += before
    ta += after
    n += 1
    print("%-22s %dx%d -> %dx%d   %5d KB -> %5d KB"
          % (fn, w, h, im2.size[0], im2.size[1], before / 1024, after / 1024))

print("\n%d images capped: %.1f MB -> %.1f MB of loose texture%s"
      % (n, tb / 1048576.0, ta / 1048576.0, "  (dry run)" if DRY else ""))
