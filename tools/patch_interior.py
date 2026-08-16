"""Gives the buildings an inside worth walking into.

Before this a room was four bare slabs with a flat soffit over it. Now it has
the things a mud-brick room actually has: round timbers carrying the ceiling,
a plastered bench along one wall, blind niches cut into the walls for a lamp or
a jar, and a skirting where wall meets floor.
"""
import pathlib

INSIDE = '''

def niche_cut(target, face, fixed, along, z0, w, h, depth):
    """A blind recess in the inner face of a wall -- not cut through.

    The cutter is pushed toward the room so it only eats `depth` of the wall.
    Cutting straight through would put a window where a niche belongs.
    """
    off = (T - depth) / 2 + 0.001
    if face in ('S', 'N'):
        sgn = 1 if face == 'S' else -1
        cut(target, solid(w, depth, h - w / 2, (along, fixed - sgn * off, z0 + (h - w / 2) / 2),
                          False, False))
        cut(target, cyl(w / 2, depth, (along, fixed - sgn * off, z0 + h - w / 2),
                        rot=(math.pi / 2, 0, 0), verts=12, keep=False))
    else:
        sgn = 1 if face == 'W' else -1
        cut(target, solid(depth, w, h - w / 2, (fixed - sgn * off, along, z0 + (h - w / 2) / 2),
                          False, False))
        cut(target, cyl(w / 2, depth, (fixed - sgn * off, along, z0 + h - w / 2),
                        rot=(0, math.pi / 2, 0), verts=12, keep=False))


def furnish(cx, cy, w, d, z0, h, walls):
    """The inside of a room: beams, a bench, niches, a skirting."""
    fy_s, fy_n = cy - d / 2 + T / 2, cy + d / 2 - T / 2
    fx_w, fx_e = cx - w / 2 + T / 2, cx + w / 2 - T / 2

    # round timbers carrying the ceiling, the way a flat mud roof is built
    n = max(3, int(w / 0.85))
    for i in range(n):
        px = cx - w / 2 + (i + 0.5) * (w / n)
        cyl(0.075 * random.uniform(0.9, 1.1), d - T * 1.6,
            (px, cy, z0 + h - 0.14), rot=(math.pi / 2, 0, 0), verts=7)
    # split cane laid across them, which is what the mud sits on
    for i in range(max(4, int(d / 0.5))):
        py = cy - d / 2 + (i + 0.5) * (d / max(4, int(d / 0.5)))
        cyl(0.028, w - T * 1.6, (cx, py, z0 + h - 0.05), rot=(0, math.pi / 2, 0), verts=5)

    # a skirting where the wall meets the floor
    for sy in (-1, 1):
        solid(w - T * 2, 0.1, 0.16, (cx, cy + sy * (d / 2 - T - 0.05), z0 + 0.08))
    for sx in (-1, 1):
        solid(0.1, d - T * 2 - 0.2, 0.16, (cx + sx * (w / 2 - T - 0.05), cy, z0 + 0.08))

    # a low plastered bench along one wall, for sitting and for setting things on
    if random.random() < 0.8:
        side = random.choice(('N', 'W', 'E'))
        bh = random.uniform(0.42, 0.52)
        if side == 'N':
            solid(w - T * 2 - 0.4, 0.62, bh, (cx, fy_n - 0.36, z0 + bh / 2))
        elif side == 'W':
            solid(0.62, d - T * 2 - 0.4, bh, (fx_w + 0.36, cy, z0 + bh / 2))
        else:
            solid(0.62, d - T * 2 - 0.4, bh, (fx_e - 0.36, cy, z0 + bh / 2))

    # blind niches: where a lamp, a jar or a book goes
    for _ in range(random.randint(2, 4)):
        face = random.choice(('N', 'W', 'E'))
        nz = z0 + random.uniform(0.75, h * 0.55)
        nw = random.uniform(0.4, 0.62)
        nh = nw * random.uniform(1.3, 1.8)
        if face == 'N':
            along = cx + random.uniform(-w * 0.3, w * 0.3)
            niche_cut(walls['N'], 'N', fy_n, along, nz, nw, nh, T * 0.62)
        elif face == 'W':
            along = cy + random.uniform(-d * 0.3, d * 0.3)
            niche_cut(walls['W'], 'W', fx_w, along, nz, nw, nh, T * 0.62)
        else:
            along = cy + random.uniform(-d * 0.3, d * 0.3)
            niche_cut(walls['E'], 'E', fx_e, along, nz, nw, nh, T * 0.62)

    # a shelf across one corner
    if random.random() < 0.55:
        sx = random.choice((-1, 1))
        solid(w * 0.36, 0.3, 0.06, (cx + sx * (w * 0.25), fy_n - 0.18,
                                    z0 + random.uniform(1.3, 1.7)))
'''


def main():
    p = pathlib.Path("tools/make_building.py")
    s = p.read_text(encoding="utf-8")
    if "def furnish(" in s:
        print("already furnished")
        return

    anchor = "# ------------------------------------------------------------ the storey"
    assert anchor in s
    s = s.replace(anchor, INSIDE.lstrip("\n") + "\n\n" + anchor, 1)

    # call it from storey, after the openings are cut and before the weld
    old = """    weather(walls['S'], cx, fy_s, w, d, h, z0, 'y')"""
    new = """    if roomspot:
        furnish(cx, cy, w, d, z0, h, walls)

    weather(walls['S'], cx, fy_s, w, d, h, z0, 'y')"""
    assert old in s
    s = s.replace(old, new, 1)

    p.write_text(s, encoding="utf-8")
    print("interiors furnished")


if __name__ == "__main__":
    main()
