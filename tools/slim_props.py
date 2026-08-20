# Cuts every prop in the town down to a triangle count that matches its size.
#   python tools/slim_props.py [--dry]
#
# WHY: measured in the live town from a street, the welded geometry pushed 6.7
# million triangles a frame and the biggest single contributor was not a
# building. It was a BOWL - p_bowl is 4,264 triangles and there are a hundred
# and twenty of them on the tables of the town, which is 542,000 triangles of
# crockery. Stones were 6,598 apiece, barrels 4,192, cushions and jars a third
# of a million each across the town.
#
# None of that detail is visible: these things are 20 cm across and are seen
# from two metres away at best, at night. The budgets below are what the shape
# actually needs to read.
#
# The original is kept beside it as <name>.hi.glb, which is the convention the
# lantern and the torches already follow, so nothing is lost.
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "assets", "models")
BLENDER = r"C:\Users\sandk\tools\blender-4.2.1-windows-x64\blender.exe"
SLIM = os.path.join(ROOT, "tools", "slim_glb.py")
DRY = "--dry" in sys.argv

# what a thing is allowed to cost, by what it is
BUDGET = {
    # set down on a table and looked at from two metres
    "p_bowl": 320, "p_cup": 260, "p_inkset": 420, "p_bread": 320,
    "p_books": 520, "p_scrolls": 420, "p_oillamp": 320, "p_mashaf": 520,
    # carried, stacked, sat on
    "p_jars": 620, "p_pot": 520, "p_waterjug": 480, "p_basket": 480,
    "p_cushions": 520, "p_stool": 420, "p_sacks": 620, "p_crates": 560,
    "p_barrel": 520, "p_barrels": 760, "p_plantpot": 380, "p_bowarrows": 620,
    # furniture and the bigger street things
    "p_stones": 900, "p_firewood": 800, "p_ropecoil": 620, "p_cart": 1400,
    "p_bench": 700, "p_chest": 700, "p_table": 800, "p_awning": 700,
    "p_stall": 1200, "p_pergola": 1100, "p_well": 1400, "p_brazier": 800,
    "p_broom": 300, "p_ladder": 400, "p_carpet": 300,
    # a heap of rock does not need twenty-four thousand triangles
    "rock_c": 2400, "rock_a": 2000, "rock_b": 2000, "rock_d": 2000,
    "rock_small": 700,
}
# the whole market kit, by shape
for k in ("booth_cloth", "booth_metal", "booth_spice"):
    BUDGET["stall/" + k] = 900
for k in ("canopy_bread", "canopy_fruit", "canopy_grain", "canopy_spice"):
    BUDGET["stall/" + k] = 800
for k in ("leanto_bread", "leanto_pottery", "leanto_wood"):
    BUDGET["stall/" + k] = 700
for k in ("rack_cloth", "rack_rope"):
    BUDGET["stall/" + k] = 800
for k in ("trestle_basket", "trestle_metal", "trestle_pottery"):
    BUDGET["stall/" + k] = 600
for k in ("mat_basket", "mat_rope", "mat_spice"):
    BUDGET["stall/" + k] = 420
for k in ("barrow_fruit", "barrow_grain"):
    BUDGET["stall/" + k] = 700


def tri_count(path):
    """read the triangle count out of the glb's accessors, without Blender"""
    import json
    import struct
    d = open(path, "rb").read()
    if d[:4] != b"glTF":
        return 0
    n = struct.unpack("<I", d[12:16])[0]
    js = json.loads(d[20:20 + n])
    acc = js.get("accessors", [])
    total = 0
    for m in js.get("meshes", []):
        for pr in m.get("primitives", []):
            if pr.get("mode", 4) != 4:
                continue
            if "indices" in pr:
                total += acc[pr["indices"]]["count"] // 3
            elif "POSITION" in pr.get("attributes", {}):
                total += acc[pr["attributes"]["POSITION"]]["count"] // 3
    return total


# A MODEL THAT IS ALREADY LEAN MUST BE LEFT ALONE. Decimating a 500 triangle
# carpet down to 300 saved nothing and smeared its UVs, so the whole pattern -
# which is the only reason the object exists - came out as a pale sheet. The
# same danger applies to any flat panel whose value is its texture. Below this
# many triangles there is nothing worth taking and everything to lose.
WORTH_SLIMMING = 1300

# AND NOTHING MAY LOSE MORE THAN THIS SHARE OF ITSELF. A solid shape - a bowl,
# a pot - collapses beautifully and still reads at 8% of its triangles. A shape
# made of thin twisted strands does not: stall/mat_rope went from 3,152 to 420
# and came out as a scatter of loose shards with the coils gone. There is no
# reliable way to tell the two apart from the outside, so every model keeps at
# least this much of itself and the saving is taken where it is safe.
KEEP_AT_LEAST = 0.45


def restore(key):
    """put the original back from the copy kept beside it"""
    src = os.path.join(MODELS, key.replace("/", os.sep) + ".glb")
    hi = src[:-4] + ".hi.glb"
    if os.path.exists(hi):
        open(src, "wb").write(open(hi, "rb").read())
        os.remove(hi)
        return True
    return False


def main():
    if "--restore-all" in sys.argv:
        n = 0
        for key in sorted(BUDGET):
            if restore(key):
                print("  restored %s" % key)
                n += 1
        print("\n%d models put back" % n)
        return
    if "--restore-lean" in sys.argv:
        n = 0
        for key in sorted(BUDGET):
            src = os.path.join(MODELS, key.replace("/", os.sep) + ".glb")
            hi = src[:-4] + ".hi.glb"
            if not os.path.exists(hi):
                continue
            if tri_count(hi) < WORTH_SLIMMING:
                if restore(key):
                    print("  restored %-22s (%d tris - never worth cutting)"
                          % (key, tri_count(src)))
                    n += 1
        print("\n%d models put back" % n)
        return
    done = saved = 0
    for key in sorted(BUDGET):
        src = os.path.join(MODELS, key.replace("/", os.sep) + ".glb")
        if not os.path.exists(src):
            print("  (missing) %s" % key)
            continue
        have = tri_count(src)
        want = BUDGET[key]
        if have < WORTH_SLIMMING:
            print("  %-22s %6d tris - too lean to touch" % (key, have))
            continue
        want = max(want, int(have * KEEP_AT_LEAST))
        if have <= want * 1.25:
            print("  %-22s %6d tris - already lean" % (key, have))
            continue
        hi = src[:-4] + ".hi.glb"
        if DRY:
            print("  %-22s %6d -> %d" % (key, have, want))
            continue
        if not os.path.exists(hi):
            open(hi, "wb").write(open(src, "rb").read())
        r = subprocess.run([BLENDER, "--background", "--python", SLIM, "--",
                            hi, src, str(want)],
                           capture_output=True, text=True)
        now = tri_count(src)
        ok = now > 0 and now <= want * 1.6
        print("  %-22s %6d -> %6d  %s" % (key, have, now, "" if ok else "CHECK"))
        if ok:
            done += 1
            saved += have - now
    print("\n%d models slimmed, %d triangles off every copy in the world"
          % (done, saved))


if __name__ == "__main__":
    main()
