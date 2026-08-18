# Walks into every house on paper and says whether it can be entered.
#   python tools/check_house.py [bh21 bh22 ...]
#
# It reads the collision file only - the same boxes the game uses - and steps
# from outside the door to the middle of the room, asking at each step whether
# anything solid stands in the way at knee, chest and head height, and how big
# a step up the floor asks for.  A house that looks open but is sealed is the
# oldest bug in this project; this catches it before it ships.
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets", "models")
STEP_MAX = 0.74            # what the engine can step up
names = sys.argv[1:] or sorted(
    os.path.basename(p)[:-9] for p in glob.glob(os.path.join(M, "bh*.col.json")))


def inside(b, x, y, z, pad=0.0):
    return (abs(x - b["c"][0]) < b["h"][0] + pad and
            abs(y - b["c"][1]) < b["h"][1] + pad and
            abs(z - b["c"][2]) < b["h"][2] + pad)


def floor_at(boxes, x, z, ceiling):
    top = 0.0
    for b in boxes:
        if (abs(x - b["c"][0]) < b["h"][0] and abs(z - b["c"][2]) < b["h"][2]):
            t = b["c"][1] + b["h"][1]
            if t <= ceiling and t > top:
                top = t
    return top


bad = 0
for name in names:
    p = os.path.join(M, name + ".col.json")
    j = json.load(open(p))
    boxes, spots = j["boxes"], j.get("spots", [])
    door = next((s for s in spots if s.get("k") == "door"), None)
    room = next((s for s in spots if s.get("k") == "room"), None)
    if not door or not room:
        print("%-6s NO DOOR/ROOM SPOT" % name)
        bad += 1
        continue
    dwid = door["r"][0]
    dx = door["c"][0] + dwid / 2          # the middle of the opening
    dz = door["c"][2]
    rx, rz = room["c"][0], room["c"][2]
    # the door faces outward along +z in game axes; walk from outside to inside
    problems = []
    last_floor = 0.0
    # straight through the opening first, and only then turn for the middle
    # of the room: cutting the corner walks into the pier beside the door,
    # which is a fault in the walk, not in the house.
    for i in range(0, 15):
        t = i / 14.0
        turn = max(0.0, (t - 0.45) / 0.55)
        x = dx + (rx - dx) * turn
        z = (dz + 1.4) + ((rz) - (dz + 1.4)) * t
        for h in (0.35, 0.95, 1.60):
            for b in boxes:
                if inside(b, x, h, z):
                    problems.append("solid at %.1fm in, height %.2f" % (t * 3, h))
                    break
            else:
                continue
            break
        f = floor_at(boxes, x, z, 2.0)
        if f - last_floor > STEP_MAX:
            problems.append("step of %.2fm at %.0f%% of the way" % (f - last_floor, t * 100))
        last_floor = f
    seen = []
    for pr in problems:
        if pr not in seen:
            seen.append(pr)
    if seen:
        bad += 1
        print("%-6s BLOCKED: %s" % (name, "; ".join(seen[:3])))
    else:
        print("%-6s enterable, floor rises %.2fm" % (name, last_floor))

print("checked %d, %d blocked" % (len(names), bad))
sys.exit(1 if bad else 0)
