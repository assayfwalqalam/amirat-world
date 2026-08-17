"""Look for REAL blossom source: photographed plant atlases and models.

A hand-drawn petal is vector cartoon art and has no business in this world.
What is wanted is a photographed cut-out with a real alpha channel, or a
scanned flowering plant we can bake cards off, the same way the ground
flowers were done.

    python tools/find_blossom.py
"""
import json
import urllib.request

UA = {"User-Agent": "amirat-world/1.0 (novivorai@gmail.com)"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def polyhaven(kind):
    d = json.loads(get("https://api.polyhaven.com/assets?t=%s" % kind))
    for k in sorted(d):
        tags = " ".join(d[k].get("tags", [])).lower()
        cats = " ".join(d[k].get("categories", [])).lower()
        blob = (k + " " + tags + " " + cats).lower()
        if any(w in blob for w in ("blossom", "flower", "cherry", "sakura", "magnolia",
                                   "bougainvillea", "jacaranda", "wisteria", "almond")):
            print("  PH %-10s %-34s | %s" % (kind, k, cats[:44]))


def ambientcg():
    d = json.loads(get("https://ambientcg.com/api/v2/full_json?type=Atlas&limit=300"))
    for a in d.get("foundAssets", []):
        aid = a.get("assetId", "")
        tags = " ".join(a.get("tags", []) or []).lower()
        blob = (aid + " " + tags).lower()
        if any(w in blob for w in ("blossom", "flower", "cherry", "petal", "magnolia")):
            print("  ACG atlas  %-34s | %s" % (aid, tags[:44]))
    print("  --- all atlases (for context) ---")
    for a in d.get("foundAssets", [])[:40]:
        print("    %s" % a.get("assetId", ""))


if __name__ == "__main__":
    print("Poly Haven:")
    for k in ("models", "textures"):
        try:
            polyhaven(k)
        except Exception as e:
            print("  %s failed: %s" % (k, e))
    print("ambientCG:")
    try:
        ambientcg()
    except Exception as e:
        print("  failed: %s" % e)
