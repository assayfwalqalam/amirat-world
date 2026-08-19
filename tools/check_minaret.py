# Walks the minaret galleries in the EXPORTED collision, not in the picture.
#   python tools/check_minaret.py
#
# The fault this exists to catch: the stair used to climb a hundred and sixty
# steps into a solid stone plug. A picture of a lantern stage looks the same
# whether or not there is a hole in its floor, so the hole is measured here.
#
# Everything is asked in the model's own collision space: c = [x, z, -y] and
# h = [hx, hz, hy], both already multiplied by the palace's 1.4.
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COL = os.path.join(ROOT, "assets", "models", "palace", "qasr.col.json")
QS = 1.4

# where the six minarets stand, and how tall, straight out of make_palace.py
MINARETS = [(sx * 23, -24, 58.0) for sx in (-1, 1)] + \
           [(sx * 120, 75, 52.0) for sx in (-1, 1)] + \
           [(sx * 23, 140, 52.0) for sx in (-1, 1)]

boxes = json.load(open(COL))["boxes"]


def solid(bx, by, bz):
    """is the point (blender x, y, z) inside any collision box?"""
    px, py, pz = bx * QS, bz * QS, -by * QS
    for b in boxes:
        c, h = b["c"], b["h"]
        if abs(px - c[0]) <= h[0] and abs(py - c[1]) <= h[1] and abs(pz - c[2]) <= h[2]:
            return True
    return False


def top_under(bx, by, z_from, z_to, step=0.05):
    """the highest solid surface between two heights, or None"""
    z = z_from
    found = None
    while z <= z_to:
        if solid(bx, by, z):
            found = z
        z += step
    return found


fails = 0
for (mx, my, htot) in MINARETS:
    lz = 2.2 + htot * 0.82
    GR = 3.1 * 1.75
    name = "minaret(%.0f,%.0f)" % (mx, my)

    # 1. THE WAY OUT. Above the top tread, where a man's body has to pass,
    #    there must be nothing but air up to well over his head.
    blocked = []
    for oy in (2.1, 2.6, 3.0):
        for ox in (-0.7, 0.0, 0.7):
            for z in (lz + 0.25, lz + 0.9, lz + 1.6, lz + 2.1):
                if solid(mx + ox, my + oy, z):
                    blocked.append((ox, oy, round(z - lz, 2)))
    # 2. THE FLOOR you step out onto: solid all the way round the ring
    holes = []
    for a in range(0, 360, 15):
        ra = math.radians(a)
        for rr in (3.0, 3.8, 4.6, 5.2):
            fx, fy = mx + math.cos(ra) * rr, my + math.sin(ra) * rr
            if not solid(fx, fy, lz - 0.22):
                holes.append((a, rr))
    # 3. HEADROOM over the ring: nothing to bump into for 2.5 m
    bumps = []
    for a in range(0, 360, 30):
        ra = math.radians(a)
        fx, fy = mx + math.cos(ra) * 3.8, my + math.sin(ra) * 3.8
        for z in (lz + 0.9, lz + 1.6, lz + 2.4, lz + 3.2):
            if solid(fx, fy, z):
                bumps.append((a, round(z - lz, 1)))
    # 4. THE PARAPET must stop you: solid at chest height on the rim
    gaps = []
    for a in range(0, 360, 10):
        ra = math.radians(a)
        fx, fy = mx + math.cos(ra) * (GR - 0.20), my + math.sin(ra) * (GR - 0.20)
        if not solid(fx, fy, lz + 0.55):
            gaps.append(a)
    # 5. THE WELL RAIL: chest high all the way round EXCEPT the one gap the
    #    stair comes out of, so nobody walks into the shaft by accident
    rail_open = []
    for a in range(0, 360, 10):
        ra = math.radians(a)
        fx, fy = mx + math.cos(ra) * 2.48, my + math.sin(ra) * 2.48
        near_exit = abs(((ra - math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < 0.62
        if not solid(fx, fy, lz + 0.55) and not near_exit:
            rail_open.append(a)
    # 6. THE TOP TREAD: its face must be level with the gallery floor
    tread = top_under(mx, my + 2.2, lz - 0.9, lz + 0.30)

    ok = (not blocked and not holes and not bumps and not gaps and not rail_open
          and tread is not None and abs(tread - lz) < 0.22)
    fails += 0 if ok else 1
    print("%-20s %s  way-out blocked=%d  floor holes=%d  headroom bumps=%d  "
          "parapet gaps=%d  rail open=%d  top tread=%s" %
          (name, "OK  " if ok else "FAIL",
           len(blocked), len(holes), len(bumps), len(gaps), len(rail_open),
           ("%.2f (%+.2f vs the floor)" % (tread, tread - lz)) if tread else "MISSING"))
    if blocked:
        print("     blocked at (dx,dy,dz rel. floor):", blocked[:8])
    if holes:
        print("     floor missing at (deg, radius):", holes[:8])
    if bumps:
        print("     head hits at (deg, dz):", bumps[:8])
    if gaps:
        print("     you can walk off the edge at (deg):", gaps[:12])
    if rail_open:
        print("     you can fall down the well at (deg):", rail_open[:12])

print("\n%d of %d galleries fail" % (fails, len(MINARETS)))
sys.exit(1 if fails else 0)
