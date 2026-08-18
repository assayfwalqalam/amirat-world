# Lists which models actually carry a collision, door or firefly file.
#   python tools/make_assetindex.py   ->  assets/models/index.json
#
# Why: the game asked for three side files per model - .col.json, .door.json
# and .fx.json - for every model it loads. Only 270 collision files exist, one
# door file and one firefly file, so nearly six hundred of those requests were
# 404s. A browser opens six connections to a host; six hundred misses stand in
# front of the models that actually have to arrive, and the world takes ten to
# twenty seconds to appear. With this list the game asks only for what is
# there.
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets", "models")

out = {"col": [], "door": [], "fx": []}
for dirpath, dirnames, filenames in os.walk(M):
    for fn in filenames:
        rel = os.path.relpath(os.path.join(dirpath, fn), M).replace("\\", "/")
        for suffix, key in ((".col.json", "col"), (".door.json", "door"), (".fx.json", "fx")):
            if rel.endswith(suffix):
                out[key].append(rel[:-len(suffix)])

for k in out:
    out[k].sort()

path = os.path.join(M, "index.json")
with open(path, "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("WROTE %s  col=%d door=%d fx=%d" % (path, len(out["col"]), len(out["door"]), len(out["fx"])))
