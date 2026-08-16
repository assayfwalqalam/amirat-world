"""The clean pass, after his circled screenshots.

What the circles were:
  scratch lines   boolean "cracks" cut into the walls -- they read as glitches,
                  not as age. Age now lives in the texture only.
  dark smears     the occlusion bake at 12 samples, plus "patch" slabs glued
                  onto the walls. Samples up, patches gone.
  floating dashes roof beams embedded only 9 cm -- the wall waviness recedes
                  past them and they detach. They now run 60 cm into the wall.
  stairs          climbed to a FIXED height while storey heights are RANDOM,
                  and ended at blank wall. Every stair now lands exactly on the
                  upper floor at a real doorway, or through a gap left in the
                  roof parapet.
  floor seam      the slab edge peeking past the eroded wall face. Intermediate
                  floors now stand slightly proud as a deliberate string course.
"""
import pathlib


def slice_replace(s, start_marker, end_marker, replacement):
    i = s.index(start_marker)
    j = s.index(end_marker, i + len(start_marker))
    return s[:i] + replacement + s[j:]


PARAPET = '''def parapet(cx, cy, w, d, z, height=0.95, rails=True, gap=None):
    """The wall round a roof terrace.

    gap=(x, width) leaves the front wall open where a stair arrives, because a
    stair that tops out against a parapet is a stair to nowhere.
    """
    for sy in (-1, 1):
        if sy < 0 and gap is not None:
            gx, gw = gap
            a0, a1 = cx - w / 2, gx - gw / 2
            b0, b1 = gx + gw / 2, cx + w / 2
            if a1 - a0 > 0.05:
                solid(a1 - a0, 0.3, height, ((a0 + a1) / 2, cy - (d / 2 - 0.15), z + height / 2))
            if b1 - b0 > 0.05:
                solid(b1 - b0, 0.3, height, ((b0 + b1) / 2, cy - (d / 2 - 0.15), z + height / 2))
        else:
            solid(w, 0.3, height, (cx, cy + sy * (d / 2 - 0.15), z + height / 2))
    for sx in (-1, 1):
        solid(0.3, d - 0.6, height, (cx + sx * (w / 2 - 0.15), cy, z + height / 2))
    if rails and gap is None and random.random() < 0.72:
        n = max(3, int(w / 1.1))
        for i in range(n):
            if random.random() < 0.12:
                continue
            px = cx - w / 2 + (i + 0.5) * (w / n)
            cyl(0.045, 0.6, (px, cy - d / 2 + 0.15, z + height + 0.3), verts=6)
        solid(w, 0.09, 0.09, (cx, cy - d / 2 + 0.15, z + height + 0.62))


'''

BEAMS = '''def beams(cx, cy, w, d, z, n=None):
    """Projecting roof beams. They run well back into the wall, because a beam
    that only kisses the surface detaches wherever the render wanders."""
    n = n or max(3, int(w / 1.5))
    for i in range(n):
        px = cx - w / 2 + (i + 0.5) * (w / n)
        cyl(0.062, 1.0, (px, cy - d / 2 + 0.1, z), rot=(math.pi / 2, 0, 0), verts=6)


'''

FLOOR_SLAB = '''def floor_slab(cx, cy, w, d, z, thick=0.4, proud=False):
    """A floor. An intermediate floor stands slightly proud of the wall face,
    a string course: the line between storeys is then a deliberate band rather
    than an accident of two surfaces meeting."""
    if proud:
        solid(w + 0.16, d + 0.16, thick, (cx, cy, z + thick / 2))
    else:
        solid(w, d, thick, (cx, cy, z + thick / 2))


'''

WEATHER = '''def weather(*_args, **_kw):
    """Retired. Boolean cracks read as scratched glitches, never as age; the
    age of a wall lives in its texture now, and the structure stays clean."""
    return


'''

PATCH = '''def patch(*_args, **_kw):
    """Retired with weather(): the glued-on render slabs made smears."""
    return None


'''

COURT = '''def build_court():
    """Rooms round a walled yard, with a gate: a small compound."""
    W = random.uniform(17, 24)
    D = random.uniform(15, 21)
    h = random.uniform(3.2, 3.9)
    mw, md = W * random.uniform(0.55, 0.8), D * random.uniform(0.34, 0.44)
    mx, my = random.uniform(-W * 0.1, W * 0.1), D / 2 - md / 2
    floor_slab(mx, my, mw, md, 0)
    storey(mx, my, mw, md, 0.4, h, doorway=('S', random.uniform(-mw * 0.2, mw * 0.2), 1.4, 2.4), wins=2)
    floor_slab(mx, my, mw, md, 0.4 + h)
    beams(mx, my, mw, md, 0.4 + h + 0.2)
    stair_x = mx - mw / 2 + 0.95
    parapet(mx, my, mw, md, 0.8 + h, 0.9, gap=(stair_x, 1.8))
    SPOTS.append({"c": [round(mx, 3), round(0.8 + h, 3), round(-my, 3)],
                  "r": [round(mw / 2 - 1.2, 2), round(md / 2 - 1.2, 2)], "k": "roof"})
    # the stair lands exactly on the roof, through the gap in the parapet
    ext_stair(stair_x, my - md / 2 - 2.9, 1.5, 3.0, 0, 0.8 + h)

    # a side wing
    if random.random() < 0.8:
        ww, wd = W * random.uniform(0.22, 0.3), D * random.uniform(0.42, 0.55)
        wx = -W / 2 + ww / 2
        wy = -D / 2 + wd / 2 + 1.0
        floor_slab(wx, wy, ww, wd, 0)
        storey(wx, wy, ww, wd, 0.4, h * 0.92,
               doorway=('E', random.uniform(-wd * 0.2, wd * 0.2), 1.3, 2.2), wins=1)
        floor_slab(wx, wy, ww, wd, 0.4 + h * 0.92)
        parapet(wx, wy, ww, wd, 0.8 + h * 0.92, 0.85)
        SPOTS.append({"c": [round(wx, 3), round(0.8 + h * 0.92, 3), round(-wy, 3)],
                      "r": [round(ww / 2 - 1.0, 2), round(wd / 2 - 1.0, 2)], "k": "roof"})

    # the yard wall, with a gate in the south
    yh = random.uniform(2.1, 2.7)
    gw = 2.2
    goff = random.uniform(-W * 0.15, W * 0.15)
    sy = -D / 2
    wall_s = solid(W, 0.34, yh, (0, sy, yh / 2), collide=False)
    erode(wall_s, 1, 0.02, 0.03)
    arch_cut(wall_s, goff, sy, 0, gw, 2.5, 1.4, 'y')
    rec_wall_with_gap('x', -W / 2, W / 2, sy, 0, yh, goff, gw, 2.5)
    weld(wall_s)
    SPOTS.append({"c": [round(goff - gw / 2, 3), 0.0, round(-sy, 3)],
                  "r": [round(gw, 3), 2.5], "k": "door", "f": 0})
    for sx in (-1, 1):
        w2 = solid(0.34, D, yh * random.uniform(0.92, 1.05), (sx * W / 2, 0, yh / 2))
        erode(w2, 1, 0.02, 0.03)
        weld(w2)
    SPOTS.append({"c": [0.0, 0.05, round(-(-D / 4), 3)],
                  "r": [round(W / 2 - 2.5, 2), round(D / 5, 2)], "k": "court"})


'''

HOUSE = '''def build_house(storeys=None):
    storeys = storeys or random.choice([1, 2, 2, 3])
    W = random.uniform(8.5, 12.5)
    D = random.uniform(7.5, 10.5)
    heights = [random.uniform(3.0, 3.7)] + [random.uniform(2.7, 3.3) for _ in range(storeys - 1)]
    want_stair = random.random() < 0.72
    want_balcony = storeys >= 2 and not want_stair and random.random() < 0.45
    stair_x = -W / 2 + 0.95
    setbacks = [(i < storeys - 1 and random.random() < 0.5) for i in range(storeys)]
    if want_stair and storeys >= 2:
        setbacks[0] = False              # the stair lands at a door in this face

    floor_slab(0, 0, W, D, 0)
    z = 0.4
    cw, cd = W, D
    cx, cy = 0.0, 0.0
    for i in range(storeys):
        h = heights[i]
        if i == 0:
            door = ('S', random.uniform(-cw * 0.22, cw * 0.22), 1.4, 2.45)
        elif i == 1 and want_stair:
            door = ('S', stair_x, 1.3, 2.25)      # where the outside stair lands
        elif i == 1 and want_balcony:
            door = ('S', 0.0, 1.3, 2.25)          # onto the balcony
        else:
            door = None
        storey(cx, cy, cw, cd, z, h, doorway=door, wins=random.randint(1, 3))
        floor_slab(cx, cy, cw, cd, z + h, proud=(i < storeys - 1))
        beams(cx, cy, cw, cd, z + h + 0.2)
        z += h + 0.4
        if setbacks[i]:
            back = random.uniform(1.2, 2.4)
            parapet(cx, cy - back / 2, cw, cd, z, 0.85)
            SPOTS.append({"c": [round(cx, 3), round(z, 3), round(-(cy - cd / 2 + back / 2), 3)],
                          "r": [round(cw / 2 - 0.8, 2), round(back / 2 - 0.2, 2)], "k": "balcony"})
            cd -= back
            cy += back / 2
    parapet(cx, cy, cw, cd, z, random.uniform(0.85, 1.15),
            gap=(stair_x, 1.8) if (want_stair and storeys == 1) else None)
    SPOTS.append({"c": [round(cx, 3), round(z, 3), round(-cy, 3)],
                  "r": [round(cw / 2 - 1.0, 2), round(cd / 2 - 1.0, 2)], "k": "roof"})

    if want_stair:
        # to the upper doorway, or through the parapet gap onto the roof
        z1 = (0.4 + heights[0] + 0.4) if storeys >= 2 else (z)
        ext_stair(stair_x, -D / 2 - 2.9, 1.45, 3.0, 0, z1)

    if want_balcony:
        bw = W * 0.5
        by = -D / 2 - 0.9
        bz = 0.4 + heights[0] + 0.4           # exactly the upper floor level
        solid(bw, 1.8, 0.22, (0, by, bz - 0.11))
        for sx in (-1, 1):
            pillar(sx * bw / 2 * 0.86, by - 0.7, 0.0, bz - 0.22, r=0.1, base=False, cap=False)
        parapet(0, by, bw, 1.8, bz, 0.75, rails=True)
        SPOTS.append({"c": [0.0, round(bz, 3), round(-by, 3)],
                      "r": [round(bw / 2 - 0.5, 2), 0.55], "k": "balcony"})


'''

TOWER = '''def build_tower():
    storeys = random.choice([3, 3, 4])
    W = random.uniform(6.0, 7.8)
    D = random.uniform(5.6, 7.2)
    heights = [random.uniform(2.9, 3.4) for _ in range(storeys)]
    stair_x = -W / 2 + 0.85
    floor_slab(0, 0, W, D, 0)
    z = 0.4
    for i in range(storeys):
        h = heights[i]
        if i == 0:
            door = ('S', random.uniform(-W * 0.16, W * 0.16), 1.35, 2.4)
        elif i == 1:
            door = ('S', -W / 2 + 1.05, 1.2, 2.2)     # where the stair lands
        else:
            door = None
        storey(0, 0, W - i * 0.28, D - i * 0.28, z, h, doorway=door, wins=random.randint(1, 2))
        floor_slab(0, 0, W - i * 0.28, D - i * 0.28, z + h, proud=(i < storeys - 1))
        if i == storeys - 2:
            beams(0, 0, W, D, z + h + 0.2)
        z += h + 0.4
    parapet(0, 0, W - storeys * 0.28, D - storeys * 0.28, z, 1.0)
    SPOTS.append({"c": [0.0, round(z, 3), 0.0],
                  "r": [round(W / 2 - 1.4, 2), round(D / 2 - 1.4, 2)], "k": "roof"})
    if random.random() < 0.5:
        small_dome(0, 0, z + 1.0, min(W, D) * 0.34)
    ext_stair(stair_x, -D / 2 - 2.7, 1.35, 2.8, 0, 0.4 + heights[0] + 0.4)


'''

SHOPS = '''def build_shops():
    W = random.uniform(14, 20)
    D = random.uniform(8, 11)
    floor_slab(0, 0, W, D, 0)
    h0 = random.uniform(3.6, 4.2)
    storey(0, 0, W, D, 0.4, h0, doorway=None, wins=0, arcade=True, roomspot=True)
    floor_slab(0, 0, W, D, 0.4 + h0, proud=True)
    beams(0, 0, W, D, 0.4 + h0 + 0.2)
    z = 0.4 + h0 + 0.4
    ups = random.choice([1, 1, 2])
    for i in range(ups):
        h = random.uniform(2.8, 3.3)
        door = ('S', W / 2 - 1.05, 1.25, 2.2) if i == 0 else None   # the stair door
        storey(0, 0, W - 0.3, D - 0.3, z, h, doorway=door, wins=random.randint(2, 4))
        floor_slab(0, 0, W - 0.3, D - 0.3, z + h, proud=(i < ups - 1))
        z += h + 0.4
    parapet(0, 0, W - 0.3, D - 0.3, z, 1.0)
    SPOTS.append({"c": [0.0, round(z, 3), 0.0],
                  "r": [round(W / 2 - 1.2, 2), round(D / 2 - 1.2, 2)], "k": "roof"})
    # awning poles along the shop front
    for i in range(max(2, int(W / 4))):
        px = -W / 2 + (i + 0.5) * (W / max(2, int(W / 4)))
        pillar(px, -D / 2 - 1.0, 0.0, 3.0, r=0.095, base=False, cap=False)
    solid(W * 0.94, 2.0, 0.14, (0, -D / 2 - 1.0, 3.05))
    ext_stair(W / 2 - 0.9, -D / 2 - 2.9, 1.45, 3.0, 0, 0.4 + h0 + 0.4)


'''

RIAD = '''def build_riad():
    """Two storeys of rooms wrapped round a small inner court."""
    W = random.uniform(17, 22)
    D = random.uniform(15, 20)
    cw = W * random.uniform(0.30, 0.38)
    cd = D * random.uniform(0.30, 0.38)
    h = random.uniform(3.2, 3.8)

    floor_slab(0, 0, W, D, 0)

    for lvl in range(2):
        z = 0.4 + lvl * (h + 0.4)
        if lvl == 0:
            door = ('S', random.uniform(-W * 0.18, W * 0.18), 1.6, 2.6)
        else:
            door = ('S', -W / 2 + 1.05, 1.3, 2.25)     # where the stair lands
        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(2, 4),
               roomspot=(lvl == 0))
        for sy in (-1, 1):
            solid(cw + T * 2, T, h, (0, sy * (cd / 2 + T / 2), z + h / 2))
        for sx in (-1, 1):
            solid(T, cd, h, (sx * (cw / 2 + T / 2), 0, z + h / 2))
        band_d = (D - cd) / 2
        band_w = (W - cw) / 2
        for sy in (-1, 1):
            floor_slab(0, sy * (cd / 2 + band_d / 2), W, band_d, z + h, proud=(lvl == 0))
        for sx in (-1, 1):
            floor_slab(sx * (cw / 2 + band_w / 2), 0, band_w, cd, z + h, proud=(lvl == 0))
        if lvl == 0:
            beams(0, -(cd / 2 + band_d / 2), W, band_d, z + h + 0.2)
            SPOTS.append({"c": [0.0, round(z, 3), round(cd / 2 + band_d / 2, 3)],
                          "r": [round(W / 2 - 2, 2), round(band_d / 2 - 1.2, 2)], "k": "room"})
        else:
            SPOTS.append({"c": [0.0, round(z, 3), round(-(cd / 2 + band_d / 2), 3)],
                          "r": [round(W / 2 - 2, 2), round(band_d / 2 - 1.2, 2)], "k": "balcony"})

    ztop = 0.4 + 2 * (h + 0.4)
    for sy in (-1, 1):
        band_d = (D - cd) / 2
        parapet(0, sy * (cd / 2 + band_d / 2), W, band_d, ztop, 0.95, rails=(sy < 0))
        SPOTS.append({"c": [0.0, round(ztop, 3), round(-sy * (cd / 2 + band_d / 2), 3)],
                      "r": [round(W / 2 - 1.4, 2), round(band_d / 2 - 1.0, 2)], "k": "roof"})
    for sx in (-1, 1):
        band_w = (W - cw) / 2
        parapet(sx * (cw / 2 + band_w / 2), 0, band_w, cd, ztop, 0.95, rails=False)
    for sy in (-1, 1):
        solid(cw + 1.0, 0.28, 0.55, (0, sy * (cd / 2 + 0.14), ztop + 0.28))
    for sx in (-1, 1):
        solid(0.28, cd, 0.55, (sx * (cw / 2 + 0.14), 0, ztop + 0.28))

    n_x = max(2, int(cw / 2.4))
    n_y = max(2, int(cd / 2.4))
    for i in range(n_x + 1):
        px = -cw / 2 + i * (cw / n_x)
        for sy in (-1, 1):
            pillar(px, sy * (cd / 2 - 0.55), 0.4, h - 0.35, r=0.24)
    for i in range(1, n_y):
        py = -cd / 2 + i * (cd / n_y)
        for sx in (-1, 1):
            pillar(sx * (cw / 2 - 0.55), py, 0.4, h - 0.35, r=0.24)

    cyl(1.05, 0.42, (0, 0, 0.61), verts=16)
    rec((0, 0, 0.61), 1.0, 1.0, 0.21)
    cyl(0.85, 0.1, (0, 0, 0.83), verts=16)
    cyl(0.16, 0.5, (0, 0, 1.05), verts=10)
    SPOTS.append({"c": [0.0, 0.4, 0.0],
                  "r": [round(cw / 2 - 0.9, 2), round(cd / 2 - 0.9, 2)], "k": "court"})
    ext_stair(-W / 2 + 0.9, -D / 2 - 2.9, 1.5, 3.0, 0, 0.4 + h + 0.4)


'''

BLOCK = '''def build_block():
    W = random.uniform(16, 23)
    D = random.uniform(11, 15)
    storeys = random.choice([2, 3])
    heights = [random.uniform(3.1, 3.7) for _ in range(storeys)]
    floor_slab(0, 0, W, D, 0)
    z = 0.4
    for i in range(storeys):
        h = heights[i]
        if i == 0:
            door = ('S', random.uniform(-W * 0.25, W * 0.25), 1.6, 2.6)
        elif i == 1:
            door = ('S', -W / 2 + 1.05, 1.3, 2.3)      # where the stair lands
        else:
            door = None
        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(3, 5))
        floor_slab(0, 0, W, D, z + h, proud=(i < storeys - 1))
        if i == 0:
            beams(0, 0, W, D, z + h + 0.2)
        z += h + 0.4
    parapet(0, 0, W, D, z, 1.1)
    SPOTS.append({"c": [0.0, round(z, 3), 0.0],
                  "r": [round(W / 2 - 1.4, 2), round(D / 2 - 1.4, 2)], "k": "roof"})
    # Buttresses: round piers standing on the ground and touching the wall.
    n = max(2, int(W / 5.5))
    for i in range(n):
        bx = -W / 2 + (i + 0.5) * (W / n)
        for sy in (-1, 1):
            bh = z * random.uniform(0.52, 0.76)
            by = sy * (D / 2 - 0.12)
            pillar(bx, by, 0.0, bh, r=random.uniform(0.42, 0.56))
            sh = cyl(0.34, 0.9, (bx, by + sy * -0.1, bh + 0.35), verts=10)
            sh.rotation_euler = (sy * 0.5, 0, 0)
            bpy.ops.object.transform_apply(rotation=True)
    ext_stair(-W / 2 + 0.9, -D / 2 - 3.1, 1.5, 3.2, 0, 0.4 + heights[0] + 0.4)


'''


def main():
    p = pathlib.Path("tools/make_building.py")
    s = p.read_text(encoding="utf-8")

    # gentler erosion: waviness, not tearing
    s = s.replace("def erode(ob, levels=2, fine=0.045, broad=0.075):",
                  "def erode(ob, levels=1, fine=0.02, broad=0.035):")
    s = s.replace("        erode(wl, 2)", "        erode(wl, 1)")
    # a smoother occlusion bake
    s = s.replace("scene.cycles.samples = 12", "scene.cycles.samples = 32")
    s = s.replace("scene.render.bake.margin = 2", "scene.render.bake.margin = 4")

    s = slice_replace(s, "def weather(", "\ndef patch(", WEATHER.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def patch(", "\ndef parapet(", PATCH.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def parapet(", "\ndef beams(", PARAPET.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def beams(", "\ndef ext_stair(", BEAMS.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def floor_slab(", "\n# =====", FLOOR_SLAB.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_court():", "\ndef build_house", COURT.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_house(", "\ndef build_tower", HOUSE.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_tower(", "\ndef build_shops", TOWER.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_shops(", "\ndef build_riad", SHOPS.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_riad(", "\ndef build_block", RIAD.rstrip("\n") + "\n\n")
    s = slice_replace(s, "def build_block(", "\nBUILDERS", BLOCK.rstrip("\n") + "\n\n")

    p.write_text(s, encoding="utf-8")
    print("make_building.py cleaned")

    # the old town houses carry the same scratches
    q = pathlib.Path("tools/make_house.py")
    t = q.read_text(encoding="utf-8")
    i = t.index("def weather(")
    j = t.index("\ndef ", i + 5)
    t = t[:i] + WEATHER.rstrip("\n") + "\n" + t[j:]
    t = t.replace("scene.cycles.samples = 12", "scene.cycles.samples = 28")
    q.write_text(t, encoding="utf-8")
    print("make_house.py cleaned")


if __name__ == "__main__":
    main()
