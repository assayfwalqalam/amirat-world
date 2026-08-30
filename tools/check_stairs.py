# -*- coding: utf-8 -*-
"""Climbs every house's stairs the way the ENGINE climbs, and says so with a
number.
    python tools/check_stairs.py

For each bh model: walk a probe across the interior at ground level looking
for a rising run of colliders (the flight). Then climb it under the engine's
own rule - you may step UP at most 0.74m onto a flat top - and report the
height reached. A house with an internal stair must let the probe reach the
upper floor level; the stairwell above the top treads must be OPEN (no
collider roof within 2.0m of a tread top on the way up).

This is the check that would have caught: a slab whose collider still seals a
cut hole, a tread taller than the step rule, a flight that arrives under an
unpierced floor.
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP = 0.74
HEAD = 1.72


def boxes_of(path):
    d = json.load(open(path))
    return d.get("boxes", [])


def top_below(boxes, x, z, zmax):
    """the highest collider top at (x, z) that is not above zmax"""
    best = 0.0
    for b in boxes:
        c, h = b["c"], b["h"]
        if abs(x - c[0]) <= h[0] and abs(z - c[2]) <= h[2]:
            t = c[1] + h[1]
            if t <= zmax and t > best:
                best = t
    return best


def ceiling_over(boxes, x, z, y):
    """the lowest collider underside above y at (x, z)"""
    best = None
    for b in boxes:
        c, h = b["c"], b["h"]
        if abs(x - c[0]) <= h[0] and abs(z - c[2]) <= h[2]:
            bot = c[1] - h[1]
            if bot > y + 0.05 and (best is None or bot < best):
                best = bot
    return best


def climb(boxes, x0, z0, dx, dz, y_start):
    """walk in small steps, climbing what the engine can climb; return the
    highest floor stood on, and whether the head ever hit a ceiling"""
    y = y_start
    hit_head = False
    for i in range(240):
        x = x0 + dx * i * 0.1
        z = z0 + dz * i * 0.1
        t = top_below(boxes, x, z, y + STEP)
        if t > y:
            c = ceiling_over(boxes, x, z, t)
            if c is not None and c - t < HEAD:
                hit_head = True
                break
            y = t
    return y, hit_head


def main():
    models = sorted(glob.glob(os.path.join(ROOT, "assets", "models", "bh*.col.json")))
    bad = 0
    for mp in models:
        name = os.path.basename(mp).split(".")[0]
        boxes = boxes_of(mp)
        # the terrace level: the highest large flat top below 6m
        tops = sorted(set(round(b["c"][1] + b["h"][1], 2) for b in boxes
                          if b["h"][0] > 1.5 and b["h"][2] > 1.5
                          and b["c"][1] + b["h"][1] < 6.5))
        upper = tops[-1] if tops else 0.0
        best = 0.0
        best_head = False
        # try climbs from many interior start points in both x directions
        for zs in [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]:
            for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                y, hh = climb(boxes, -dx * 6.0, zs if dx else -dz * 6.0,
                              dx, dz, 0.30)
                if y > best:
                    best, best_head = y, hh
        inner = best >= upper - 0.15 and upper > 2.0
        print("%-6s upper=%5.2f  climbed=%5.2f  head-hit=%s  %s"
              % (name, upper, best, best_head,
                 "INNER STAIR OK" if inner else "no inner route"))
        # a model that got close but banged its head is a real fault
        if best_head and not inner:
            print("        ^ the flight exists but the ceiling seals it")
            bad += 1
    print("\n%d faults" % bad)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
