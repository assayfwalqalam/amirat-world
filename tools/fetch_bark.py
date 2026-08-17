"""Fetch a CC0 bark texture for the trees.

The tree trunks had no image texture at all - their colour came from a
vertex-colour node - which is why they read as smooth blurred tubes. This
pulls real bark from Poly Haven (CC0, no attribution required) and writes
assets/t_bark_d.jpg plus its normal map.

    python tools/fetch_bark.py [list]
"""
import io
import json
import os
import sys
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
UA = {"User-Agent": "amirat-world/1.0 (novivorai@gmail.com)"}

# slug -> the name our trees ask for
WANT = {
    "bark_brown_02": "bark",             # the broadleaf default
    "pine_bark": "barkpine",             # the conifers
    "jolcham_oak_bark_01": "barkold",    # the giants, deep furrowed
    "palm_tree_bark": "barkpalm",
}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()


def listing():
    d = json.loads(get("https://api.polyhaven.com/assets?t=textures"))
    for k in sorted(d):
        tags = " ".join(d[k].get("tags", [])).lower()
        if "bark" in k.lower() or "bark" in tags:
            print(k, "|", ",".join(d[k].get("categories", [])))


def grab(slug, name):
    files = json.loads(get("https://api.polyhaven.com/files/%s" % slug))
    out = {}
    for kind, dest in (("Diffuse", "t_%s_d.jpg" % name), ("nor_gl", "t_%s_n.jpg" % name)):
        node = files.get(kind)
        if not node:
            print("  no %s for %s" % (kind, slug))
            continue
        res = node.get("2k") or node.get("1k")
        if not res:
            continue
        url = (res.get("jpg") or res.get("png") or {}).get("url")
        if not url:
            continue
        raw = get(url)
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if im.size[0] > 2048:
            im = im.resize((2048, 2048), Image.LANCZOS)
        p = os.path.join(A, dest)
        im.save(p, quality=92)
        out[kind] = (dest, os.path.getsize(p) // 1024, im.size)
        print("  %-14s %5dkB %s" % (dest, os.path.getsize(p) // 1024, im.size))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        listing()
    else:
        for slug, name in WANT.items():
            print("%s -> t_%s_d" % (slug, name))
            try:
                grab(slug, name)
            except Exception as e:
                print("  failed: %s" % e)
