"""Shrink the bark sheets before they are packed into every tree.

make_tree.py packs its bark image INTO each GLB. A 2k sheet therefore costs
about 1.7MB per tree variant, and with sixty variants that is fifty megabytes
of trees to download before the world can start. Bark is a fine repeating
grain, so 512 is plenty at the distance a trunk is ever seen.

    python tools/shrink_bark.py
"""
import os

from PIL import Image

A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
NAMES = ("t_bark", "t_barkpine", "t_barkold", "t_barkpalm")

for name in NAMES:
    src = os.path.join(A, name + "_d.jpg")
    if not os.path.exists(src):
        print("missing %s" % os.path.basename(src))
        continue
    im = Image.open(src).convert("RGB").resize((512, 512), Image.LANCZOS)
    dst = os.path.join(A, name + "512_d.jpg")
    im.save(dst, quality=88)
    print("%-20s %5dkB  ->  %-22s %4dkB" % (
        os.path.basename(src), os.path.getsize(src) // 1024,
        os.path.basename(dst), os.path.getsize(dst) // 1024))

# the big originals and the normal maps are not used at runtime: the material
# only takes the diffuse, and the packed copy is what ships
for name in NAMES:
    for suffix in ("_d.jpg", "_n.jpg"):
        p = os.path.join(A, name + suffix)
        if os.path.exists(p):
            os.remove(p)
            print("removed %s" % os.path.basename(p))
