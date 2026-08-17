"""Pull real reference photographs onto disk, so every build can be judged
against the thing itself instead of against my own opinion.

Sources are Wikimedia Commons (free licences, real photographs).  They are
reference only: they live in shots/ref/ which is gitignored, and nothing is
ever traced or extracted from them - they are looked at and measured.

    python tools/fetch_refs.py            # the whole list
    python tools/fetch_refs.py ak rpg     # only these keys
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "shots", "ref")
UA = "AmiratWorldRefFetch/1.0 (contact: novivorai@gmail.com)"

API = "https://commons.wikimedia.org/w/api.php"

# key -> (search terms, how many to keep)
WANT = {
    # the land
    "cliff":     ("sandstone cliff rock face", 5),
    "cliffwall": ("cliff strata layered rock erosion", 5),
    "scree":     ("scree talus slope rock debris", 4),
    "desertrock": ("desert rock formation canyon", 4),
    # the vehicles
    "humvee":    ("HMMWV humvee military", 6),
    "landrover": ("Land Rover Wolf British Army", 5),
    "technical": ("Toyota Hilux pickup truck", 4),
    "wreck":     ("destroyed burnt car wreck", 4),
    # the weapons
    "ak":        ("AKM Kalashnikov rifle", 6),
    "rpg":       ("RPG-7 launcher", 5),
    "mortar":    ("mortar 82 mm infantry", 4),
    "dshk":      ("DShK heavy machine gun", 4),
    # the structures
    "hesco":     ("HESCO bastion barrier", 4),
    "twall":     ("concrete T-wall blast barrier", 4),
    "tower":     ("military guard tower base perimeter", 4),
    "sandbag":   ("sandbag fortification position", 3),
    # real blossom, for cutting canopy cards from photographs
    "sakura":    ("cherry blossom branch sky", 8),
    "blossomtree": ("flowering cherry tree full bloom", 6),
    "almondbl":  ("almond blossom branch", 5),
    "jacarandabl": ("jacaranda tree flowering purple", 5),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def search(query, limit):
    q = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrlimit": str(limit * 3),
        "gsrsearch": query + " filetype:bitmap",
        "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1600",
    }
    j = json.loads(get(API + "?" + urllib.parse.urlencode(q)).decode("utf-8"))
    pages = list((j.get("query") or {}).get("pages", {}).values())
    # search order is lost in the dict, so put it back
    pages.sort(key=lambda p: p.get("index", 999))
    out = []
    for p in pages:
        title = p.get("title", "")
        low = title.lower()
        if any(low.endswith(e) for e in (".pdf", ".djvu", ".svg", ".gif", ".tif", ".tiff")):
            continue
        ii = (p.get("imageinfo") or [{}])[0]
        src = ii.get("thumburl") or ii.get("url")
        if not src:
            continue
        # a photograph, not a diagram or a tiny icon
        if (ii.get("width") or 0) < 800:
            continue
        out.append((title.replace("File:", ""), src))
        if len(out) >= limit:
            break
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    keys = sys.argv[1:] or list(WANT)
    for key in keys:
        if key not in WANT:
            print("unknown key %s" % key)
            continue
        query, n = WANT[key]
        try:
            hits = search(query, n)
        except Exception as e:
            print("SEARCH FAILED %-11s %s" % (key, e))
            continue
        for i, (title, src) in enumerate(hits, 1):
            ext = os.path.splitext(urllib.parse.urlparse(src).path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            dest = os.path.join(OUT, "r_%s_%d%s" % (key, i, ext))
            try:
                data = get(src)
            except Exception as e:
                print("  FAIL %s: %s" % (title[:50], e))
                continue
            with open(dest, "wb") as f:
                f.write(data)
            print("  %-14s %6dkB  %s" % (os.path.basename(dest), len(data) // 1024, title[:60]))
            time.sleep(0.15)
    print("done -> %s" % OUT)


if __name__ == "__main__":
    main()
