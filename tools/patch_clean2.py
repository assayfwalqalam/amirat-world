"""The second clean pass, after his zoomed crop.

What the crop showed:
  the shades    the ambient-occlusion bake. It stores shading per VERTEX, and
                a wall here has vertices metres apart, so one dark corner at a
                doorway smears diagonally across half the wall. No amount of
                tuning fixes that -- the bake is removed outright. Depth now
                comes from the real-time moon, the shadows and the texture.
  the fences    the parapet railings: straight posts and a straight bar, the
                exact western timber he already rejected. Removed everywhere,
                on his ruling.

Plus the faults found auditing the three previews properly:
  - the setback terrace parapet ringed the OLD footprint, so its side walls
    hung in the air past the face below -> three-sided strip on the terrace
  - the balcony stood on two 4 m poles of 10 cm -> corbel beams into the wall
    and posts a person would trust
  - the court's yard walls butted at corners and the erosion opened seams ->
    piers own every corner and the gate jambs; the yard now also closes
    beside the main range
  - windows sat at random heights and could land BEHIND the stair -> one sill
    line per storey, and no openings in the stair zone
  - the shops arcade was cut into a wall whose collision was one sealed slab
    -> the arcade now carries pier-by-pier collision and can be walked through
  - the riad court had no way in -> an arch from the south range
  - square windows get a timber lintel, which is what holds one up
"""
import pathlib
import re


def slice_replace(s, start_marker, end_marker, replacement):
    i = s.index(start_marker)
    j = s.index(end_marker, i + len(start_marker))
    return s[:i] + replacement + s[j:]


def main():
    p = pathlib.Path("tools/make_building.py")
    s = p.read_text(encoding="utf-8")

    # ---- the shades: remove the vertex bake, texture straight to the surface
    s = slice_replace(
        s,
        "while len(ob.data.color_attributes)",
        "me = ob.data",
        "if tn is not None:\n    tn.image.pack()\n\n",
    )
    s = re.sub(r",\s*export_vertex_color='ACTIVE'\)", ")", s)

    # ---- the fences: no rails anywhere, on his ruling
    s = s.replace("if rails", "if False and rails")

    # ---- storey(): sill line, stair zones, lintels, honest arcade collision
    s = s.replace(
        "def storey(cx, cy, w, d, z0, h, doorway=None, wins=2, arcade=False, roomspot=True):",
        "def storey(cx, cy, w, d, z0, h, doorway=None, wins=2, arcade=False, roomspot=True, avoid=None):")

    s = s.replace(
        """    walls['S'] = solid(w, T, h, (cx, fy_s, z0 + h / 2), collide=(dface != 'S'))""",
        """    walls['S'] = solid(w, T, h, (cx, fy_s, z0 + h / 2),
                       collide=(dface != 'S' and not arcade))""")

    s = s.replace(
        """        for i in range(n):
            ax = cx - w / 2 + (i + 0.5) * step
            if doorway and doorway[0] == 'S' and abs(ax - (cx + doorway[1])) < 2.2:
                continue
            arch_cut(walls['S'], ax, fy_s, z0 + 0.1, step * 0.62, h * 0.74, T + 1.4, 'y')
            rec((ax - step * 0.5, fy_s, z0 + h / 2), step * 0.19, T / 2, h / 2)
        rec((cx, fy_s, z0 + h * 0.88), w / 2, T / 2, h * 0.12)""",
        """        for i in range(n):
            ax = cx - w / 2 + (i + 0.5) * step
            skip = (doorway and doorway[0] == 'S' and abs(ax - (cx + doorway[1])) < 2.2) or \\
                   (avoid and avoid[0] - 0.4 < ax < avoid[1] + 0.4)
            if skip:
                # this bay stays solid wall, so it must also stay solid to walk into
                rec((ax, fy_s, z0 + h / 2), step * 0.5, T / 2, h / 2)
                continue
            arch_cut(walls['S'], ax, fy_s, z0 + 0.1, step * 0.62, h * 0.74, T + 1.4, 'y')
            rec((ax - step * 0.5, fy_s, z0 + h / 2), step * 0.19, T / 2, h / 2)
        rec((cx + w / 2 - step * 0.19, fy_s, z0 + h / 2), step * 0.19, T / 2, h / 2)
        rec((cx, fy_s, z0 + h * 0.88), w / 2, T / 2, h * 0.12)""")

    s = s.replace(
        """    for i in range(wins):
        wx = cx + random.uniform(-w * 0.34, w * 0.34)
        if doorway and doorway[0] == 'S' and abs(wx - (cx + doorway[1])) < 1.6:
            wx += 2.4 * (1 if random.random() < 0.5 else -1)
        zz = z0 + h * random.uniform(0.46, 0.66)
        if random.random() < 0.55:
            arch_cut(walls['S'], wx, fy_s, zz, 0.72, 1.25, T + 1.4, 'y')
        else:
            slot_cut(walls['S'], wx, fy_s, zz, 0.7, 1.0, T + 1.4, 'y')""",
        """    sill = z0 + h * random.uniform(0.48, 0.58)   # one sill line per storey
    arched = random.random() < 0.55               # one window style per face
    for i in range(wins):
        wx = cx + random.uniform(-w * 0.34, w * 0.34)
        if doorway and doorway[0] == 'S' and abs(wx - (cx + doorway[1])) < 1.6:
            wx += 2.4 * (1 if random.random() < 0.5 else -1)
        if avoid and avoid[0] - 0.55 < wx < avoid[1] + 0.55:
            continue                              # never an opening behind the stair
        if arched:
            arch_cut(walls['S'], wx, fy_s, sill, 0.72, 1.25, T + 1.4, 'y')
        else:
            slot_cut(walls['S'], wx, fy_s, sill, 0.7, 1.0, T + 1.4, 'y')
            solid(0.95, T + 0.14, 0.13, (wx, fy_s, sill + 1.06), collide=False)""")

    s = s.replace(
        """    if random.random() < 0.5:
        slot_cut(walls['N'], cx + random.uniform(-w * 0.3, w * 0.3), fy_n,
                 z0 + h * 0.55, 0.66, 0.95, T + 1.4, 'y')""",
        """    if random.random() < 0.5:
        bx2 = cx + random.uniform(-w * 0.3, w * 0.3)
        slot_cut(walls['N'], bx2, fy_n, z0 + h * 0.55, 0.66, 0.95, T + 1.4, 'y')
        solid(0.9, T + 0.14, 0.13, (bx2, fy_n, z0 + h * 0.55 + 1.01), collide=False)""")

    # ---- house: honest terrace walls, a balcony that would hold, stair zone
    s = s.replace(
        """        if setbacks[i]:
            back = random.uniform(1.2, 2.4)
            parapet(cx, cy - back / 2, cw, cd, z, 0.85)""",
        """        if setbacks[i]:
            back = random.uniform(1.2, 2.4)
            # the terrace is walled on its three OPEN sides only -- a parapet
            # round the whole old footprint left walls hanging in the air
            f_y = cy - cd / 2
            solid(cw, 0.3, 0.85, (cx, f_y + 0.15, z + 0.425))
            for sxp in (-1, 1):
                solid(0.3, back - 0.3, 0.85,
                      (cx + sxp * (cw / 2 - 0.15), f_y + back / 2, z + 0.425))""")

    s = s.replace(
        """        storey(cx, cy, cw, cd, z, h, doorway=door, wins=random.randint(1, 3))""",
        """        av = (-W / 2, -W / 2 + 1.95) if (want_stair and i == 0) else None
        storey(cx, cy, cw, cd, z, h, doorway=door, wins=random.randint(1, 3), avoid=av)""")

    s = s.replace(
        """        solid(bw, 1.8, 0.22, (0, by, bz - 0.11))
        for sx in (-1, 1):
            pillar(sx * bw / 2 * 0.86, by - 0.7, 0.0, bz - 0.22, r=0.1, base=False, cap=False)
        parapet(0, by, bw, 1.8, bz, 0.75, rails=True)""",
        """        solid(bw, 1.8, 0.22, (0, by, bz - 0.11))
        n_c = max(3, int(bw / 1.1))
        for i2 in range(n_c):                 # corbel beams running back into the wall
            px2 = -bw / 2 + (i2 + 0.5) * (bw / n_c)
            cyl(0.07, 2.6, (px2, -D / 2 - 0.55, bz - 0.31), rot=(math.pi / 2, 0, 0), verts=6)
        for sx in (-1, 1):                    # posts a person would trust
            pillar(sx * (bw / 2 - 0.22), by - 0.65, 0.0, bz - 0.22, r=0.15)
        parapet(0, by, bw, 1.8, bz, 0.75, rails=False)""")

    # ---- court: close the yard, own the corners
    s = s.replace(
        """    for sx in (-1, 1):
        w2 = solid(0.34, D, yh * random.uniform(0.92, 1.05), (sx * W / 2, 0, yh / 2))
        erode(w2, 1, 0.02, 0.03)
        weld(w2)""",
        """    for sx in (-1, 1):
        w2 = solid(0.34, D, yh * random.uniform(0.92, 1.05), (sx * W / 2, 0, yh / 2))
        erode(w2, 1, 0.015, 0.022)
        weld(w2)
    # the yard closes beside the main range too
    for a, b in ((-W / 2, mx - mw / 2), (mx + mw / 2, W / 2)):
        if b - a > 0.6:
            w3 = solid(b - a + 0.3, 0.34, yh, ((a + b) / 2, D / 2, yh / 2))
            erode(w3, 1, 0.015, 0.022)
            weld(w3)
    # piers own every corner and the gate jambs: two eroded walls butted at a
    # corner open a seam, a pier covers the joint
    for px3, py3 in ((-W / 2, -D / 2), (W / 2, -D / 2), (-W / 2, D / 2), (W / 2, D / 2),
                     (goff - gw / 2 - 0.2, -D / 2), (goff + gw / 2 + 0.2, -D / 2)):
        p3 = solid(0.72, 0.72, yh + 0.22, (px3, py3, (yh + 0.22) / 2))
        erode(p3, 1, 0.012, 0.02)""")
    s = s.replace("    erode(wall_s, 1, 0.02, 0.03)", "    erode(wall_s, 1, 0.015, 0.022)")

    # ---- riad: no windows behind the stair, and a way into the court
    s = s.replace(
        """        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(2, 4),
               roomspot=(lvl == 0))
        for sy in (-1, 1):
            solid(cw + T * 2, T, h, (0, sy * (cd / 2 + T / 2), z + h / 2))""",
        """        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(2, 4),
               roomspot=(lvl == 0),
               avoid=(-W / 2, -W / 2 + 1.95) if lvl == 0 else None)
        for sy in (-1, 1):
            if lvl == 0 and sy < 0:
                # the way from the south range into the court
                cwall = solid(cw + T * 2, T, h, (0, sy * (cd / 2 + T / 2), z + h / 2),
                              collide=False)
                arch_cut(cwall, 0, sy * (cd / 2 + T / 2), z, 1.6, 2.5, T + 1.2, 'y')
                rec_wall_with_gap('x', -cw / 2 - T, cw / 2 + T, sy * (cd / 2 + T / 2),
                                  z, h, 0, 1.6, 2.5)
                weld(cwall)
            else:
                solid(cw + T * 2, T, h, (0, sy * (cd / 2 + T / 2), z + h / 2))""")

    # ---- tower and block: no openings behind the stair
    s = s.replace(
        """        storey(0, 0, W - i * 0.28, D - i * 0.28, z, h, doorway=door, wins=random.randint(1, 2))""",
        """        storey(0, 0, W - i * 0.28, D - i * 0.28, z, h, doorway=door,
               wins=random.randint(1, 2),
               avoid=(-W / 2, -W / 2 + 1.75) if i == 0 else None)""")
    s = s.replace(
        """        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(3, 5))""",
        """        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(3, 5),
               avoid=(-W / 2, -W / 2 + 1.95) if i == 0 else None)""")

    # ---- shops: the arcade keeps clear of the stair and stays walkable
    s = s.replace(
        """    storey(0, 0, W, D, 0.4, h0, doorway=None, wins=0, arcade=True, roomspot=True)""",
        """    storey(0, 0, W, D, 0.4, h0, doorway=None, wins=0, arcade=True, roomspot=True,
           avoid=(W / 2 - 2.1, W / 2))""")

    p.write_text(s, encoding="utf-8")
    print("make_building.py: bake gone, rails gone, audit fixes in")

    # ---- the town houses carry the same bake and rails
    q = pathlib.Path("tools/make_house.py")
    t = q.read_text(encoding="utf-8")
    i = t.index("while len(house.data.color_attributes)")
    j = t.index("use_vertex_colour(nt, bsdf")
    k = t.index("\n", j)
    t = t[:i] + "if img_tex is not None:\n    img_tex.pack()\n" + t[k + 1:]
    t = re.sub(r",\s*export_vertex_color='ACTIVE'\)", ")", t)
    t = t.replace("if rails", "if False and rails")
    q.write_text(t, encoding="utf-8")
    print("make_house.py: bake gone, rails gone")


if __name__ == "__main__":
    main()
