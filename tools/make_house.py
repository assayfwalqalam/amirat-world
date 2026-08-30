# Builds an Aserai-style mud-brick house in Blender and exports .glb + .col.json
#   blender --background --python make_house.py -- <seed> <out.glb> [assets_dir]
#
# Two rules learned the hard way, do not reorder them:
#   1. Cut each solid while it is still a clean box. Joining first shreds it.
#   2. Erode before cutting. Eroding afterwards tears the wall around openings.
#
# The shapes come from the Afghan Ursilat reference shots (shots/ref/ursilat_*):
# walls that lean in as they rise, a stone base course, roof slabs that overhang
# on rows of round timber beams, small deep windows with a lintel and a grille,
# a post-and-plank porch over the door, lower sheds stuck on the side, ladders,
# and parapets that differ from side to side.
#
# Every structural box is also written to a collision file, so what you stand on
# in the game is exactly what you see: parapets lift you, stairs step true, and
# there are no invisible margins.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SEED = int(argv[0]) if argv else 1
OUT = argv[1] if len(argv) > 1 else "house.glb"
ASSETS = argv[2] if len(argv) > 2 else os.path.join(os.path.dirname(OUT), "..", "..", "assets")
random.seed(SEED)

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 28

COLLIDERS = []          # every solid the player can stand on or walk into
SPOTS = []              # flat places where the game may set down props


def solid(sx, sy, sz, loc, collide=True):
    """A box of the building. Recorded for collision at its true size."""
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        # game axes: x right, y up, z toward the viewer (the exporter flips y/z)
        COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                          "h": [round(sx / 2, 3), round(sz / 2, 3), round(sy / 2, 3)]})
    return ob


def cyl(r, depth, loc, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cut(target, cutter):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def weld(ob, dist=0.0006):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=2, fine=0.045, broad=0.075):
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    weld(ob)
    for scale, strength in ((1.2, fine), (3.8, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = scale
        t.noise_depth = 2
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = strength
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)


def batter(ob, specs, z0, h, amt):
    """Lean a wall's outer faces in as they rise, the way mud walls are built.

    specs is a list of (axis, sign, plane): the face standing at that plane
    moves inward. Call it on the clean box, before eroding: the displacement
    then follows the leaning face instead of fighting it.
    """
    if h <= 0.01 or amt <= 0:
        return
    for v in ob.data.vertices:
        t = (v.co.z - z0) / h
        if t <= 0.001:
            continue
        t = min(1.0, t)
        for axis, sign, plane in specs:
            i = 0 if axis == 'x' else 1
            if abs(v.co[i] - plane) < 0.004:
                v.co[i] -= sign * amt * t


def bevel(ob, width, segs=2, angle=35):
    m = ob.modifiers.new("bv", 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return bpy.context.active_object


# ---------------------------------------------------------- proportions
# Three kinds of house, because a street of one proportion reads as a kit.
# In the reference there are square courtyard houses, long low ranges, and
# narrow houses that go up instead of along.
KIND = ("court", "range", "tower")[(SEED * 2246822519) % 100 // 34]
if KIND == "range":
    W = random.uniform(11.0, 12.8)
    D = random.uniform(5.6, 6.9)
    H1 = random.uniform(3.2, 3.9)
elif KIND == "tower":
    W = random.uniform(6.2, 7.4)
    D = random.uniform(5.6, 6.9)
    H1 = random.uniform(3.8, 4.5)
else:
    W = random.uniform(7.5, 10.0)
    D = random.uniform(6.5, 8.5)
    H1 = random.uniform(3.6, 4.4)
H2 = random.uniform(2.9, 3.6)
H3 = random.uniform(2.5, 3.1)
T = 0.45                                   # wall thickness
BAT = 0.036                                # how far a wall leans in per metre
OV = 0.13                                  # how far a roof slab overhangs
has_upper = random.random() < (0.34 if KIND == "range" else 1.0 if KIND == "tower" else 0.78)
has_third = KIND == "tower" and random.random() < 0.45
uw = W * random.uniform(0.62 if KIND != "tower" else 0.86, 0.86 if KIND != "tower" else 1.0)
ud = D * random.uniform(0.66 if KIND != "tower" else 0.88, 0.9 if KIND != "tower" else 1.0)
ox = random.uniform(-1, 1) * (W - uw) * 0.32
oy = random.uniform(-1, 1) * (D - ud) * 0.32
tw = uw * random.uniform(0.68, 0.88)
td = ud * random.uniform(0.70, 0.92)
tx = ox + random.uniform(-1, 1) * (uw - tw) * 0.3
ty = oy + random.uniform(-1, 1) * (ud - td) * 0.3

dw, dh = 1.35, 2.45
dx = random.uniform(-W * 0.18, W * 0.18)

PLINTH = random.uniform(0.5, 0.95)         # the stone base course

shell = []       # the coursed stone of the walls
mud = []         # the smooth mud of roofs and floors
timber = []      # beams, frames, posts, ladders


def window(target, cx, cy, cz, w, h, axis, through):
    """The opening itself: a square-headed hole with a round head."""
    if axis == 'y':
        cut(target, solid(w, through, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2), False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2), rot=(math.pi / 2, 0, 0)))
    else:
        cut(target, solid(through, w, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2), False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2), rot=(0, math.pi / 2, 0)))


def window_deep(target, cx, cy, cz, w, h, axis, sign, face, through):
    """A window as they are actually built: the wall is cut back in a shallow
    frame first, so the opening sits in a reveal with a shadow round it, then
    a timber lintel over, a sill under, and a stick grille across."""
    rd = 0.13                              # how deep the frame is cut back
    if axis == 'y':
        cut(target, solid(w + 0.30, rd * 2, h + 0.24, (cx, face - sign * rd, cz), False))
    else:
        cut(target, solid(rd * 2, w + 0.30, h + 0.24, (face - sign * rd, cy, cz), False))
    window(target, cx, cy, cz, w, h, axis, through)
    # the frame sits INSIDE the reveal, tight to the opening: a lintel across
    # the head, a sill under, and two sticks down the light. Set proud of the
    # wall it reads as loose planks stuck on, which is what the first one did.
    fx = face - sign * (rd - 0.02)
    if axis == 'y':
        timber.append(solid(w + 0.10, 0.13, 0.10, (cx, fx, cz + h / 2 + 0.05), False))
        timber.append(solid(w + 0.10, 0.15, 0.07, (cx, fx + sign * 0.01, cz - h / 2 - 0.035), False))
        for i in range(2):
            gx = cx - w / 6 + i * (w / 3)
            timber.append(solid(0.038, 0.045, h - 0.06, (gx, fx, cz), False))
        for i in range(2):
            gz = cz - h / 6 + i * (h / 3)
            timber.append(solid(w - 0.04, 0.045, 0.038, (cx, fx, gz), False))
    else:
        timber.append(solid(0.13, w + 0.10, 0.10, (fx, cy, cz + h / 2 + 0.05), False))
        timber.append(solid(0.15, w + 0.10, 0.07, (fx + sign * 0.01, cy, cz - h / 2 - 0.035), False))
        for i in range(2):
            gy = cy - w / 6 + i * (w / 3)
            timber.append(solid(0.045, 0.038, h - 0.06, (fx, gy, cz), False))
        for i in range(2):
            gz = cz - h / 6 + i * (h / 3)
            timber.append(solid(0.045, w - 0.04, 0.038, (fx, cy, gz), False))


def storey(cx, cy, w, d, z0, h, front_door, n_win, ceil_hole=None,
           front_open=False):
    """Four wall slabs, so the inside is a real room you can walk into."""
    # the ceiling: a plastered slab across the room at the wall head. Without
    # it you stand inside and look up at the underside of the roof and out
    # through the gap where the roof oversails the wall.
    # FULL width on purpose: its edges bury themselves inside the wall slabs,
    # so there is no line where ceiling meets wall for the night to show
    # through. Sized to the room it leaves a gap at every batter.
    if ceil_hole is None:
        mud.append(solid(w, d, 0.18, (cx, cy, z0 + h - 0.11), False))
    else:
        _cX0, _cX1, _cY0, _cY1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
        for (a0, b0, a1, b1) in ((_cX0, _cY0, _cX1, ceil_hole[2]),
                                 (_cX0, ceil_hole[3], _cX1, _cY1),
                                 (_cX0, ceil_hole[2], ceil_hole[0], ceil_hole[3]),
                                 (ceil_hole[1], ceil_hole[2], _cX1, ceil_hole[3])):
            if a1 - a0 > 0.06 and b1 - b0 > 0.06:
                mud.append(solid(a1 - a0, b1 - b0, 0.18,
                                 ((a0 + a1) / 2, (b0 + b1) / 2, z0 + h - 0.11),
                                 False))
    # WALLS LEAN; ONE BOX CANNOT. batter() draws the outer face inward by
    # BAT*h at the head, but solid() had already recorded a full-thickness
    # box - up to 15cm of invisible stone at head height, against the law's
    # 5cm. Each wall's collision is three stacked bands now, each thinner
    # and further in than the one below, tracking the lean to within ~2cm.
    back = solid(w, T, h, (cx, cy + d / 2 - T / 2, z0 + h / 2), False)
    left = solid(T, d - T * 2, h, (cx - w / 2 + T / 2, cy, z0 + h / 2), False)
    right = solid(T, d - T * 2, h, (cx + w / 2 - T / 2, cy, z0 + h / 2), False)
    _amt0 = BAT * h
    # THE BANDS TELESCOPE. Three stacked thirds each exposed a flat TOP at a
    # third of the wall's height - and the lowest one, 1.41m up, was exactly
    # one engine-step above the plinth: the checker (and the player) climbed
    # onto a ledge inside the wall. Each band runs from its own height to the
    # FULL wall head instead, so the only exposed top is the wall head, and
    # the outer profile still steps inward with the lean (error <= amt/3).
    for _b in range(3):
        _zlo = z0 + h * _b / 3.0
        _t2 = max(0.10, T - _amt0 * (_b / 3.0))
        _hy = (z0 + h - _zlo) / 2.0
        _zc = _zlo + _hy
        COLLIDERS.append({"c": [round(cx, 3), round(_zc, 3),
                                round(-(cy + d / 2 - T + _t2 / 2), 3)],
                          "h": [round(w / 2, 3), round(_hy, 3), round(_t2 / 2, 3)]})
        COLLIDERS.append({"c": [round(cx - w / 2 + T - _t2 / 2, 3),
                                round(_zc, 3), round(-cy, 3)],
                          "h": [round(_t2 / 2, 3), round(_hy, 3),
                                round((d - T * 2) / 2, 3)]})
        COLLIDERS.append({"c": [round(cx + w / 2 - T + _t2 / 2, 3),
                                round(_zc, 3), round(-cy, 3)],
                          "h": [round(_t2 / 2, 3), round(_hy, 3),
                                round((d - T * 2) / 2, 3)]})
    # The front wall carries the doorway, so it must NOT be recorded as one
    # solid slab: the opening would be cut from the geometry while collision
    # still sealed it, and the house could be seen into but never entered.
    # It is recorded below as the pier either side plus the lintel over.
    # front_open: someone else is about to cut a doorway here and lay the
    # collision strips themselves - one solid box would seal what they open
    front = solid(w, T, h, (cx, cy - d / 2 + T / 2, z0 + h / 2),
                  collide=False)
    if not front_door and not front_open:
        for _b2 in range(3):
            _zlo2 = z0 + h * _b2 / 3.0
            _t3 = max(0.10, T - BAT * h * (_b2 / 3.0))
            _hy2 = (z0 + h - _zlo2) / 2.0
            COLLIDERS.append({"c": [round(cx, 3), round(_zlo2 + _hy2, 3),
                                    round(-(cy - d / 2 + T - _t3 / 2), 3)],
                              "h": [round(w / 2, 3), round(_hy2, 3),
                                    round(_t3 / 2, 3)]})
    amt = BAT * h
    fy = cy - d / 2 + T / 2
    by = cy + d / 2 - T / 2
    lx = cx - w / 2 + T / 2
    rx = cx + w / 2 - T / 2
    # each slab leans on the faces that are actually outside, its ends
    # included, or the corners would step where two walls meet
    batter(front, [('y', -1, fy - T / 2), ('x', -1, cx - w / 2), ('x', 1, cx + w / 2)], z0, h, amt)
    batter(back, [('y', 1, by + T / 2), ('x', -1, cx - w / 2), ('x', 1, cx + w / 2)], z0, h, amt)
    batter(left, [('x', -1, lx - T / 2)], z0, h, amt)
    batter(right, [('x', 1, rx + T / 2)], z0, h, amt)
    for wl in (back, left, right, front):
        erode(wl, levels=2)
    if front_door:
        # the doorway sits in a cut-back frame, like the windows
        cut(front, solid(dw + 0.40, 0.26, dh + 0.30, (dx, fy - T / 2 + 0.13, z0 + dh / 2), False))
        cut(front, solid(dw, T + 1.2, dh - dw / 2, (dx, fy, z0 + (dh - dw / 2) / 2), False))
        cut(front, cyl(dw / 2, T + 1.2, (dx, fy, z0 + dh - dw / 2), rot=(math.pi / 2, 0, 0), verts=16))
        # collision for the wall that remains around the opening
        x0, x1 = cx - w / 2, cx + w / 2
        gap0, gap1 = dx - dw / 2, dx + dw / 2
        for a, b in ((x0, gap0), (gap1, x1)):
            if b - a > 0.04:
                COLLIDERS.append({"c": [round((a + b) / 2, 3), round(z0 + h / 2, 3), round(-fy, 3)],
                                  "h": [round((b - a) / 2, 3), round(h / 2, 3), round(T / 2, 3)]})
        # where the leaf hangs, so the game can put a door that opens here
        SPOTS.append({"c": [round(dx - dw / 2, 3), round(z0, 3), round(-fy, 3)],
                      "r": [round(dw, 3), round(dh, 3)], "k": "door"})
        lintel_z0 = z0 + dh
        if h - dh > 0.04:
            COLLIDERS.append({"c": [round(dx, 3), round(lintel_z0 + (h - dh) / 2, 3), round(-fy, 3)],
                              "h": [round(dw / 2, 3), round((h - dh) / 2, 3), round(T / 2, 3)]})
    # windows: kept few and small, spaced along one sill line, as they are there
    sill = z0 + h * random.uniform(0.5, 0.62)
    for i in range(n_win):
        wx = cx + (i - (n_win - 1) / 2) * (w / (n_win + 0.7)) + random.uniform(-0.2, 0.2)
        if front_door and abs(wx - dx) < 1.5:
            wx += 2.2 * (1 if wx >= dx else -1)
        if abs(wx - cx) > w / 2 - 0.9:
            continue
        window_deep(front, wx, fy, sill + 0.5, 0.72, 1.15, 'y', -1, fy - T / 2, T + 1.2)
    if random.random() < 0.7:
        wy = cy + random.uniform(-(d - T * 2) * 0.3, (d - T * 2) * 0.3)
        pick_left = random.random() < 0.5
        side = left if pick_left else right
        sx = lx if pick_left else rx
        sgn = -1 if pick_left else 1
        window_deep(side, sx, wy, z0 + h * random.uniform(0.52, 0.66), 0.68, 1.05,
                    'x', sgn, sx + sgn * T / 2, T + 1.2)
    if random.random() < 0.5:
        bx = cx + random.uniform(-w * 0.3, w * 0.3)
        window_deep(back, bx, by, z0 + h * random.uniform(0.52, 0.66), 0.68, 1.05,
                    'y', 1, by + T / 2, T + 1.2)
    out = []
    for wl in (back, left, right, front):
        weld(wl)
        out.append(wl)
    return out


def beams(cx, cy, w, d, z, sides=('y', 'x'), out_len=0.26):
    """The round roof timbers, poking out of the wall under the roof edge.
    This one row of sticks is what makes a mud house read as built. They are
    short: a hand's length past the wall, tucked under the roof lip."""
    made = []
    if 'y' in sides:
        n = max(3, int(w / 0.95))
        for i in range(n):
            bx = cx - w / 2 + (i + 0.5) * (w / n)
            for sy in (-1, 1):
                made.append(cyl(random.uniform(0.052, 0.070), out_len + 0.45,
                                (bx, cy + sy * (d / 2 + out_len / 2 - 0.05),
                                 z + random.uniform(-0.015, 0.015)),
                                rot=(math.pi / 2, 0, random.uniform(-0.025, 0.025)), verts=6))
    if 'x' in sides:
        n2 = max(3, int(d / 1.05))
        for i in range(n2):
            byy = cy - d / 2 + (i + 0.5) * (d / n2)
            for sx in (-1, 1):
                made.append(cyl(random.uniform(0.050, 0.066), out_len + 0.45,
                                (cx + sx * (w / 2 + out_len / 2 - 0.05), byy,
                                 z + random.uniform(-0.015, 0.015)),
                                rot=(0, math.pi / 2, random.uniform(-0.025, 0.025)), verts=6))
    return made


def roof_slab(cx, cy, w, d, z, th=0.34, over=OV, hole=None):
    """A roof that reaches past the wall it sits on, with a proud lip.
    Roofs go on the mud list: a terrace is smoothed plaster, and wearing the
    wall's block courses it read as a brick pavement from above.

    hole=(x0, x1, y0, y1) pierces it for a stairwell - and the piercing MUST
    be strips, never a boolean cut: collision is recorded when a solid is
    born, so a cut slab still carries its whole collider and the climber
    bangs his head on air. Four strips each carry their own true box."""
    # the slab SINKS into the wall head. Set exactly on top of it, the two
    # surfaces meet in a hairline and the night shows through the joint -
    # which is the light he could see along the top of every wall.
    out = []
    if hole is None:
        out.append(solid(w + over * 2, d + over * 2, th + 0.10,
                         (cx, cy, z + th / 2 - 0.05)))
        out.append(solid(w + over * 2 + 0.05, d + over * 2 + 0.05, 0.07,
                         (cx, cy, z + th - 0.035), False))
    else:
        X0, X1 = cx - w / 2 - over, cx + w / 2 + over
        Y0, Y1 = cy - d / 2 - over, cy + d / 2 + over
        hx0 = max(X0 + 0.1, hole[0])
        hx1 = min(X1 - 0.1, hole[1])
        hy0 = max(Y0 + 0.1, hole[2])
        hy1 = min(Y1 - 0.1, hole[3])
        for (a0, b0, a1, b1) in ((X0, Y0, X1, hy0), (X0, hy1, X1, Y1),
                                 (X0, hy0, hx0, hy1), (hx1, hy0, X1, hy1)):
            if a1 - a0 > 0.06 and b1 - b0 > 0.06:
                out.append(solid(a1 - a0, b1 - b0, th + 0.10,
                                 ((a0 + a1) / 2, (b0 + b1) / 2, z + th / 2 - 0.05)))
                out.append(solid(a1 - a0 + 0.04, b1 - b0 + 0.04, 0.07,
                                 ((a0 + a1) / 2, (b0 + b1) / 2, z + th - 0.035),
                                 False))
    for o in out:
        erode(o, levels=1, fine=0.018, broad=0.03)
    mud.extend(out)
    return []


def parapet(cx, cy, w, d, z, h, t):
    """A raised roof edge. Solid, so standing on it lifts you. Not every side
    carries one: in the reference some roofs are open to the street."""
    out = []
    sides = []
    for k in range(4):
        r = random.random()
        sides.append(h if r < 0.62 else (0.26 if r < 0.84 else 0.0))
    if sum(1 for s in sides if s > 0.4) < 2:
        sides[0] = h
        sides[2] = h
    place = ((0, cx, cy + d / 2 + t / 2, w + t * 2, t),
             (1, cx, cy - d / 2 - t / 2, w + t * 2, t),
             (2, cx + w / 2 + t / 2, cy, t, d),
             (3, cx - w / 2 - t / 2, cy, t, d))
    for idx, px, py, pw, pd in place:
        hh = sides[idx]
        if hh <= 0.02:
            continue
        o = solid(pw, pd, hh, (px, py, z + hh / 2))
        erode(o, levels=1, fine=0.02, broad=0.03)
        out.append(o)
        # a timber spout to throw the rain clear of the wall
        if hh > 0.4 and random.random() < 0.45:
            if idx < 2:
                sy = 1 if idx == 0 else -1
                timber.append(cyl(0.06, 0.72,
                                  (px + random.uniform(-w * 0.3, w * 0.3), py + sy * 0.34,
                                   z + hh - 0.16), rot=(math.pi / 2, 0, 0), verts=6))
            else:
                sx = 1 if idx == 2 else -1
                timber.append(cyl(0.06, 0.72,
                                  (px + sx * 0.34, py + random.uniform(-d * 0.3, d * 0.3),
                                   z + hh - 0.16), rot=(0, math.pi / 2, 0), verts=6))
    # the terrace itself is somewhere props may stand
    SPOTS.append({"c": [round(cx, 2), round(z, 2), round(-cy, 2)],
                  "r": [round(w / 2 - 0.7, 2), round(d / 2 - 0.7, 2)], "k": "roof"})
    return out


def ladder(x, y_wall, z_top, sgn, lean=0.28):
    """Two poles and a set of rungs, leaning against a wall.

    y_wall is the wall face; sgn says which way its outside points. The foot
    stands out from the wall by the lean, the head rests at the roof edge.
    """
    off = math.tan(lean) * z_top
    L = z_top / math.cos(lean) + 0.45
    for side in (-0.19, 0.19):
        timber.append(cyl(0.048, L, (x + side, y_wall + sgn * (off / 2 + 0.05), z_top / 2),
                          rot=(sgn * lean, 0, 0), verts=6))
    n = max(4, int(z_top / 0.42))
    for i in range(n):
        zz = (i + 0.6) / (n + 0.4) * z_top
        yy = y_wall + sgn * (off * (1 - zz / z_top) + 0.05)
        timber.append(solid(0.40, 0.07, 0.055, (x, yy, zz), False))
    # the volume the game reads to let you climb it, in game axes
    ymid2 = y_wall + sgn * (off / 2 + 0.05)
    SPOTS.append({"c": [round(x, 2), round(z_top / 2, 2), round(-ymid2, 2)],
                  "h": [0.36, round(z_top / 2, 2), round(off / 2 + 0.42, 2)],
                  "k": "climb"})


# ------------------------------------------------- the inner stair, planned
# SOME HOUSES CLIMB FROM INSIDE - his order. The flight runs across the
# house under the back of the upper room, rises through a pierced slab into
# a railed well, and arrives ON the upper floor. Where the upper block
# covers the whole footprint (towers) there is no terrace for an outside
# door, so those houses MUST climb from inside.
_terr_gap = (oy - ud / 2) - (-D / 2) if has_upper else 0.0
INNER = has_upper and (random.random() < 0.55 or _terr_gap < 1.3)
if INNER:
    ST_RISE = H1 + 0.34 - 0.30
    ST_N = max(10, int(math.ceil(ST_RISE / 0.30)))
    ST_YL = min(oy + ud / 2 - T - 0.72, D / 2 - T - 0.72)   # the flight line
    _usable = W - T * 2 - 1.0
    ST_TREAD = min(0.30, (_usable - 0.2) / ST_N)
    ST_RUN = ST_N * ST_TREAD
    ST_DIR = 1 if ox >= 0 else -1
    # ARRIVE NEAR THE MIDDLE OF THE ROOM. Arriving hard against the upper
    # block's edge put the climber's head under whatever the generator had
    # stood there (bh30: a baked box at the wall left 0.34m of headroom).
    # The centre of a room is the one place nothing else claims.
    ST_XE = ox + ST_DIR * min(uw / 2 - T - 1.0, 1.2)
    ST_XS = ST_XE - ST_DIR * ST_RUN                          # the first tread
    # the open well: over the top of the flight, where a head needs air
    _headlen = min(ST_RUN - 0.4, 2.44 / (ST_RISE / ST_N) * ST_TREAD)
    ST_HX0 = min(ST_XE + ST_DIR * 0.06, ST_XE - ST_DIR * _headlen)
    ST_HX1 = max(ST_XE + ST_DIR * 0.06, ST_XE - ST_DIR * _headlen)
    ST_HOLE = (ST_HX0, ST_HX1, ST_YL - 0.66, ST_YL + 0.66)
else:
    ST_HOLE = None

# ---------------------------------------------------- the ground storey
shell += storey(0, 0, W, D, 0, H1, True,
                random.randint(2, 4) if KIND == 'range' else random.randint(1, 2),
                ceil_hole=ST_HOLE)
SPOTS.append({"c": [0, 0.3, 0], "r": [round(W / 2 - 1.2, 2), round(D / 2 - 1.2, 2)], "k": "room"})
floor = solid(W - T * 2, D - T * 2, 0.3, (0, 0, 0.15))
erode(floor, levels=1, fine=0.02, broad=0.03)
mud.append(floor)

# The stone base course the walls stand on, proud of the wall face. It is a
# RING under the walls, never a filled box: a solid block here would stand
# inside the room up to its own height and seal the house that the doorway
# says you can enter. It carries no collision either - the wall behind it
# already stops you, and the little ledge is something you step over.
_plinth = [(0, D / 2, W + 0.24, 0.45 + 0.24),
           (W / 2, 0, 0.45 + 0.24, D - 0.66),
           (-W / 2, 0, 0.45 + 0.24, D - 0.66)]
# the front run stops either side of the doorway: a base course carried
# across the door stands in front of the leaf and buries its lower half
_gap0, _gap1 = dx - dw / 2 - 0.10, dx + dw / 2 + 0.10
for _a, _b2 in ((-W / 2 - 0.12, _gap0), (_gap1, W / 2 + 0.12)):
    if _b2 - _a > 0.15:
        _plinth.append(((_a + _b2) / 2, -D / 2, _b2 - _a, 0.45 + 0.24))
for _bx, _by, _bw, _bd in _plinth:
    b = solid(_bw, _bd, PLINTH, (_bx, _by, PLINTH / 2), False)
    erode(b, levels=1, fine=0.028, broad=0.04)
    shell.append(b)

# the roof slab over the ground floor, which is also the terrace
timber += beams(0, 0, W - 0.3, D - 0.3, H1 - 0.11)
shell += roof_slab(0, 0, W, D, H1, hole=ST_HOLE)

top_z = H1 + 0.34
if has_upper:
    _upwalls = storey(ox, oy, uw, ud, top_z, H2, False, random.randint(1, 2),
                      front_open=(_terr_gap >= 1.3))
    shell += _upwalls
    _upfront = _upwalls[3]
    timber += beams(ox, oy, uw - 0.3, ud - 0.3, top_z + H2 - 0.11)
    shell += roof_slab(ox, oy, uw, ud, top_z + H2, 0.32, 0.20)

if INNER:
    # THE FLIGHT: one masonry wedge under thin tread caps would be prettier,
    # but the treads ARE the collision, so every one is its own true box -
    # the same rule the outside stair follows. 0.30 of rise a step: the
    # engine climbs 0.74, a person climbs 0.19; a palace climbs shallow.
    _sr = ST_RISE / ST_N
    for _k in range(ST_N):
        _zt = 0.30 + _sr * (_k + 1)
        _xk = ST_XS + ST_DIR * ST_TREAD * (_k + 0.5)
        solid(ST_TREAD * 1.05, 1.24, _zt - 0.28, (_xk, ST_YL, 0.28 + (_zt - 0.28) / 2))
    # the rail down the open side of the flight, segment by segment, so the
    # hand-line climbs with the treads
    for _k in range(0, ST_N, 3):
        _zt = 0.30 + _sr * (_k + 2)
        _xk = ST_XS + ST_DIR * ST_TREAD * (_k + 1.5)
        solid(ST_TREAD * 3.2, 0.09, 0.80, (_xk, ST_YL - 0.66, _zt + 0.40))
    # THE WELL IS RAILED above: across the far end and along the room side.
    # The arrival side stays open - that is where you step off.
    solid(0.09, 1.42, 0.85, (ST_HX0 - 0.045 if ST_DIR > 0 else ST_HX1 + 0.045,
                             ST_YL, top_z + 0.425))
    solid(ST_HX1 - ST_HX0 + 0.18, 0.09, 0.85,
          ((ST_HX0 + ST_HX1) / 2, ST_YL - 0.70, top_z + 0.425))

if has_upper:
    # THE UPPER ROOM IS A ROOM: it gets its own furnishing spot, kept clear
    # of the stairwell band so nothing is ever set down over the hole.
    _ry1 = (ST_YL - 0.95) if INNER else (oy + ud / 2 - T - 0.6)
    _ry0 = oy - ud / 2 + T + 0.6
    if _ry1 - _ry0 > 1.6:
        SPOTS.append({"c": [round(ox, 2), round(top_z + 0.3, 2),
                            round(-(_ry0 + _ry1) / 2, 2)],
                      "r": [round(uw / 2 - 1.15, 2), round((_ry1 - _ry0) / 2, 2)],
                      "k": "room"})
    # and a door onto the terrace wherever there is a terrace to walk out on
    if _terr_gap >= 1.3:
        _ufy = oy - ud / 2 + T / 2
        _udx = ox + random.uniform(-uw * 0.15, uw * 0.15)
        _udw, _udh = 1.25, 2.2
        cut(_upfront, solid(_udw + 0.36, 0.24, _udh + 0.26,
                            (_udx, _ufy - T / 2 + 0.12, top_z + _udh / 2), False))
        cut(_upfront, solid(_udw, T + 1.2, _udh - _udw / 2,
                            (_udx, _ufy, top_z + (_udh - _udw / 2) / 2), False))
        cut(_upfront, cyl(_udw / 2, T + 1.2,
                          (_udx, _ufy, top_z + _udh - _udw / 2),
                          rot=(math.pi / 2, 0, 0), verts=14))
        _ux0, _ux1 = ox - uw / 2, ox + uw / 2
        for _a3, _b3 in ((_ux0, _udx - _udw / 2), (_udx + _udw / 2, _ux1)):
            if _b3 - _a3 > 0.04:
                COLLIDERS.append({"c": [round((_a3 + _b3) / 2, 3),
                                        round(top_z + H2 / 2, 3), round(-_ufy, 3)],
                                  "h": [round((_b3 - _a3) / 2, 3),
                                        round(H2 / 2, 3), round(T / 2, 3)]})
        if H2 - _udh > 0.04:
            COLLIDERS.append({"c": [round(_udx, 3),
                                    round(top_z + _udh + (H2 - _udh) / 2, 3),
                                    round(-_ufy, 3)],
                              "h": [round(_udw / 2, 3), round((H2 - _udh) / 2, 3),
                                    round(T / 2, 3)]})
        SPOTS.append({"c": [round(_udx - _udw / 2, 3), round(top_z, 3),
                            round(-_ufy, 3)],
                      "r": [round(_udw, 3), round(_udh, 3)], "k": "door"})

top2_z = top_z + H2 + 0.32
if has_upper and has_third:
    shell += storey(tx, ty, tw, td, top2_z, H3, False, 1)
    timber += beams(tx, ty, tw - 0.3, td - 0.3, top2_z + H3 - 0.11)
    shell += roof_slab(tx, ty, tw, td, top2_z + H3, 0.30, 0.18)

shell += parapet(0, 0, W - 0.34 + OV * 2, D - 0.34 + OV * 2, top_z, random.uniform(0.62, 0.95), 0.32)
if has_upper:
    shell += parapet(ox, oy, uw - 0.32 + 0.4, ud - 0.32 + 0.4, top2_z,
                     random.uniform(0.55, 0.85), 0.30)
if has_upper and has_third:
    shell += parapet(tx, ty, tw - 0.3 + 0.36, td - 0.3 + 0.36, top2_z + H3 + 0.30,
                     random.uniform(0.5, 0.8), 0.28)

# ------------------------------------------------- the shed on the side
# A lower mass stuck on one flank, the way a store or a byre is added later.
# It is solid: no room inside, but it breaks the single-box silhouette and
# gives the roofline two levels.
aside = 0
if random.random() < 0.78:
    aside = 1 if random.random() < 0.5 else -1
    aw = random.uniform(2.4, 3.6)
    ad = D * random.uniform(0.5, 0.8)
    ah = random.uniform(2.2, 3.1)
    ay = random.uniform(-1, 1) * (D - ad) * 0.35
    axc = aside * (W / 2 + aw / 2 - 0.2)
    ann = solid(aw, ad, ah, (axc, ay, ah / 2))
    batter(ann, [('x', aside, axc + aside * aw / 2),
                 ('y', -1, ay - ad / 2), ('y', 1, ay + ad / 2)], 0, ah, BAT * ah)
    erode(ann, levels=2)
    # a doorway cut back into its outer face, so it reads as a store
    cut(ann, solid(1.0, 0.3, 1.9, (axc + aside * (aw / 2 - 0.13), ay - ad * 0.18, 0.95), False))
    weld(ann)
    shell.append(ann)
    timber += beams(axc, ay, aw - 0.2, ad - 0.2, ah - 0.10, sides=('y', 'x'), out_len=0.22)
    shell += roof_slab(axc, ay, aw, ad, ah, 0.28, 0.18)
    shell += parapet(axc, ay, aw - 0.2, ad - 0.2, ah + 0.28, random.uniform(0.3, 0.5), 0.24)
    if random.random() < 0.6:
        ladder(axc, ay - ad / 2, ah + 0.28, -1)

# --------------------------------------------------- the porch over the door
has_porch = random.random() < 0.55
if has_porch:
    pw = min(W - 1.5, dw + random.uniform(1.9, 3.0))
    pw = min(pw, 2 * (W / 2 - abs(dx) - 0.55))
    pd = random.uniform(1.7, 2.3)
    pz = random.uniform(2.5, 2.9)
    py = -D / 2 - pd / 2
    npost = max(2, int(round(pw / 1.7)) + 1)
    for ip in range(npost):
        pxp = dx - pw / 2 + ip * (pw / (npost - 1))
        if abs(pxp - dx) < dw / 2 + 0.45:
            continue                     # a post across the door is no door
        timber.append(cyl(0.115, pz, (pxp, py - pd / 2 + 0.12, pz / 2), verts=8))
        sxp = 1 if ip == 0 else (-1 if ip == npost - 1 else 0)
        if sxp:
            br = cyl(0.05, 0.62, (pxp + sxp * 0.17, py - pd / 2 + 0.12, pz - 0.20),
                     rot=(0, math.radians(45), 0), verts=6)
            timber.append(br)
        shell.append(solid(0.34, 0.34, 0.13, (pxp, py - pd / 2 + 0.12, 0.065)))
    timber.append(solid(pw + 0.3, 0.13, 0.16, (dx, py - pd / 2 + 0.12, pz + 0.08), False))
    timber.append(solid(pw + 0.3, 0.13, 0.16, (dx, -D / 2 + 0.06, pz + 0.08), False))
    npl = max(4, int(pw / 0.62))
    for i in range(npl):
        timber.append(cyl(0.058, pd + 0.06,
                          (dx - pw / 2 + (i + 0.5) * (pw / npl), py + 0.05, pz + 0.19),
                          rot=(math.pi / 2, 0, 0), verts=6))
    roofp = solid(pw + 0.36, pd + 0.24, 0.34, (dx, py + 0.03, pz + 0.40))
    erode(roofp, levels=1, fine=0.015, broad=0.02)
    mud.append(roofp)
    # a beam along the open edge, or the roof reads as a thin plate on legs
    timber.append(solid(pw + 0.42, 0.14, 0.12, (dx, py - pd / 2 - 0.06, pz + 0.20), False))
    SPOTS.append({"c": [round(dx, 2), 0.0, round(-py, 2)],
                  "r": [round(pw / 2 - 0.4, 2), round(pd / 2 - 0.3, 2)], "k": "porch"})

# --------------------------------------------------- the outside stair
stair_side = -aside if aside else (1 if random.random() < 0.5 else -1)
steps = 11
rise = (top_z + 0.42) / steps
run = 0.46
SX = stair_side * (W / 2 + 0.68)
# One continuous wedge of masonry under the flight - a comb of separate
# blocks showed a straight seam falling from every tread. The diagonal is
# cut from a single mass; thin tread caps give the stepped top; collision
# stays per-step so the climb is true.
y0 = -D / 2 + 0.9
flight_len = steps * run
ang = math.atan2(rise, run)
ymid = y0 + (flight_len - run) / 2


def slope_cut(ob, extra=0.0):
    """Take the diagonal off a solid mass so its top follows the flight.
    One cut on one block: the stair and its wall are each a single piece of
    masonry, never a comb of separate blocks."""
    # THE PIVOT LAW, again: a box that already stands at its place swings
    # about the WORLD ORIGIN when its rotation is applied, so this cutter was
    # landing nowhere near the stair and cutting nothing - which is why the
    # side wall stayed a blank full-height slab with the flight buried behind
    # it. Build at the origin, turn it there, then move it.
    cutter = solid(3.4, flight_len * 2.2, 8.0, (0, 0, 0), False)
    cutter.rotation_euler[0] = ang
    bpy.context.view_layer.objects.active = cutter
    bpy.ops.object.transform_apply(rotation=True)
    cutter.location = (SX, ymid,
                       rise * ((ymid - y0) / run + 1.0) + 4.0 / math.cos(ang) + 0.02 + extra)
    bpy.ops.object.transform_apply(location=True)
    cut(ob, cutter)


# the flight itself: one mass, cut to the slope, and SOLID - collision per
# step so the climb is true, plus the body under it so there is no hollow
STW = 1.35
body = solid(STW, flight_len, top_z + 0.42,
             (SX, ymid, (top_z + 0.42) / 2), False)
for _i in range(steps):
    cut(body, solid(STW + 0.4, run * 1.04, 14.0,
                    (SX, y0 + _i * run, rise * (_i + 1) + 7.0), False))
shell.append(body)
for i in range(steps):
    h = rise * (i + 1)
    shell.append(solid(STW, run * 1.03, 0.14, (SX, y0 + i * run, h - 0.07), False))
    COLLIDERS.append({"c": [round(SX, 3), round(h / 2, 3), round(-(y0 + i * run), 3)],
                      "h": [round(STW / 2, 3), round(h / 2, 3), round(run / 2, 3)]})

# HIS RULING: the SIDE and the BACK are walled, and the wall follows the
# height of each step. Nothing else is closed in - the flight is open to the
# air on the way up and open at the top.
# HIS RULING, EXACTLY: the wall is there, and IT ENDS AT EACH STEP'S HEIGHT.
# Carried a metre above the treads it becomes a five-metre triangle that
# buries the whole flight - which is what he was looking at. Its top is the
# stair line itself, so from the side the steps show, climbing.
side_x = SX + stair_side * (STW / 2 + 0.16)
cheek = solid(0.34, flight_len, top_z + 0.42, (side_x, ymid, (top_z + 0.42) / 2))
# Cut it STEP BY STEP rather than with one rotated plane. A rotated cutter
# depends on which way its pivot swings and how its own half-height projects;
# eleven upright boxes cannot be misread. Each removes everything above its
# own step, so the wall's top IS the stair, tread by tread.
for _i in range(steps):
    cut(cheek, solid(1.2, run * 1.04, 14.0,
                     (side_x, y0 + _i * run, rise * (_i + 1) + 7.0), False))
erode(cheek, levels=1, fine=0.02, broad=0.03)
shell.append(cheek)
# the back wall, at the head of the flight, no taller than the roof it meets
back_h = top_z + 0.42
shell.append(solid(STW + 0.64, 0.32, back_h, (SX, y0 + flight_len - 0.16, back_h / 2)))

# the little room at the head of the stair, where it comes out on the roof
if random.random() < 0.5:
    bw, bd, bh = random.uniform(1.7, 2.2), random.uniform(1.5, 1.9), random.uniform(1.4, 1.8)
    bx = SX - stair_side * (0.9 + bw / 2)
    by = y0 + flight_len - bd / 2 - 0.1
    bk = solid(bw, bd, bh, (bx, by, top_z + 0.34 + bh / 2))
    erode(bk, levels=1, fine=0.025, broad=0.035)
    cut(bk, solid(0.9, 0.28, 1.5, (bx, by - bd / 2 + 0.14, top_z + 0.34 + 0.75), False))
    weld(bk)
    shell.append(bk)
    shell += roof_slab(bx, by, bw, bd, top_z + 0.34 + bh, 0.2, 0.14)

# --------------------------------------------------------------- timber
# The doorway is left EMPTY. The game hangs the real door here, on its hinge,
# and a plank in the model as well meant every house had two doors - one in
# the opening and one standing across it, which is what he was looking at.
timber.append(solid(dw + 0.52, 0.22, 0.15, (dx, -D / 2 + 0.14, dh + 0.14), False))
timber.append(solid(dw + 0.4, 0.34, 0.10, (dx, -D / 2 + 0.12, 0.05), False))     # the threshold

# a ladder up the front, and a few poles left lying on the roof
if not has_porch and random.random() < 0.5:
    ladder(dx + W * 0.32, -D / 2, top_z, -1)
for i in range(random.randint(0, 3)):
    timber.append(cyl(0.05, random.uniform(1.6, 2.8),
                      (random.uniform(-W * 0.3, W * 0.3), random.uniform(-D * 0.3, D * 0.3),
                       top_z + 0.06),
                      rot=(math.pi / 2, 0, random.uniform(0, 3.14)), verts=6))

# balcony over the door, where no porch already stands there
if not has_porch and random.random() < 0.6:
    BW = random.uniform(3.6, 4.6)
    BD = 1.75
    by2 = -D / 2 - BD / 2 + 0.15
    bz = top_z + 0.1
    mud.append(solid(BW, BD, 0.18, (dx, by2, bz)))
    for sx in (-1, 1):
        timber.append(cyl(0.06, 1.15, (dx + sx * (BW / 2 - 0.25), by2 + 0.1, bz - 0.5),
                          rot=(math.radians(54), 0, 0), verts=6))
    SPOTS.append({"c": [round(dx, 2), round(bz + 0.09, 2), round(-by2, 2)],
                  "r": [round(BW / 2 - 0.5, 2), round(BD / 2 - 0.35, 2)], "k": "balcony"})

# ------------------------------------------------------------- assemble
for o in shell + mud:
    bevel(o, 0.026, 1, 35)
for o in timber:
    bevel(o, 0.012, 1, 40)


def uv_project(ob, size):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=size)
    bpy.ops.object.mode_set(mode='OBJECT')


stone = join(shell)
stone.name = "house"
weld(stone, 0.0004)
uv_project(stone, 2.2)

roofs = join(mud)
roofs.name = "roofs"
weld(roofs, 0.0004)
uv_project(roofs, 3.6)

wood = join(timber)
wood.name = "timber"
weld(wood, 0.0004)
uv_project(wood, 0.75)

# ------------------------------------------------- texture and occlusion
def image_mat(name, tex_name, normal=None, rough=1.0):
    """Texture x vertex colour into Base Color.

    The house's own tone rides on the vertex colour, NOT on a MixRGB constant:
    the glTF exporter silently drops a MixRGB tint (checked by parsing the
    exported file - baseColorFactor came out absent and every house shipped
    the same colour). Texture x ShaderNodeVertexColor exports as
    baseColorTexture x COLOR_0, which the game multiplies back.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    path = os.path.abspath(os.path.join(ASSETS, tex_name))
    if not os.path.exists(path):
        print("no texture at", path)
        bsdf.inputs["Base Color"].default_value = (0.82, 0.69, 0.50, 1)
        return mat
    img = bpy.data.images.load(path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    tn.location = (-700, 300)
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = "tint"
    vc.location = (-700, -60)
    tmix = nt.nodes.new('ShaderNodeMixRGB')
    tmix.blend_type = 'MULTIPLY'
    tmix.inputs['Fac'].default_value = 1.0
    tmix.location = (-480, 300)
    nt.links.new(tn.outputs['Color'], tmix.inputs['Color1'])
    nt.links.new(vc.outputs['Color'], tmix.inputs['Color2'])
    nt.links.new(tmix.outputs['Color'], bsdf.inputs['Base Color'])
    img.pack()
    if normal:
        npath = os.path.abspath(os.path.join(ASSETS, normal))
        if os.path.exists(npath):
            nimg = bpy.data.images.load(npath)
            nimg.colorspace_settings.name = 'Non-Color'
            ntex = nt.nodes.new('ShaderNodeTexImage')
            ntex.image = nimg
            nmap = nt.nodes.new('ShaderNodeNormalMap')
            nmap.inputs['Strength'].default_value = 0.85
            nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
            nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
            nimg.pack()
    return mat


# HIS ORDER 2026-08-18: every house wears the brick-stone. The texture is
# one; the COLOUR still varies house to house, through the tint below.
# A vertex colour can only darken, so the palette runs from the bare stone
# down; the stone photo itself is the palest house.
_w = (SEED * 2654435761) % 100
if _w < 20:   TINT = (1.00, 0.90, 0.76)        # warm sand
elif _w < 38: TINT = (1.00, 0.97, 0.92)        # pale bone
elif _w < 54: TINT = (1.00, 0.86, 0.75)        # rosy earth
elif _w < 70: TINT = (0.82, 0.83, 0.86)        # cool grey
elif _w < 86: TINT = (1.00, 0.87, 0.60)        # gold dust
else:         TINT = (0.73, 0.71, 0.68)        # smoke-dark
WOODC = (0.98, 0.96, 0.92)

tex_name = "t_ashlar_d.jpg"
if not os.path.exists(os.path.abspath(os.path.join(ASSETS, tex_name))):
    tex_name = "t_adobe_d.jpg"
stone.data.materials.clear()
stone.data.materials.append(image_mat("adobe", tex_name, "t_adobe_gn.jpg"))
wood.data.materials.clear()
wood.data.materials.append(image_mat("houswood", "t_beam_d.jpg", None, 0.86))
roofs.data.materials.clear()
roofs.data.materials.append(image_mat("housmud", "t_adobe_d.jpg", "t_adobe_gn.jpg"))

house = join([stone, roofs, wood])
house.name = "house"

# paint the tint on: stone verts wear the house colour, timber stays pale.
# One flat value per vertex - never a baked gradient, which smears across
# walls whose vertices are metres apart.
me0 = house.data
for ca in list(me0.color_attributes):
    me0.color_attributes.remove(ca)
col = me0.color_attributes.new(name="tint", type='FLOAT_COLOR', domain='POINT')
wood_names = ("houswood",)
ROOFC = (0.96, 0.92, 0.86)
wood_v = set()
for poly in me0.polygons:
    if me0.materials[poly.material_index].name.startswith(wood_names):
        wood_v.update(poly.vertices)
roof_v = set()
for poly in me0.polygons:
    if me0.materials[poly.material_index].name.startswith("housmud"):
        roof_v.update(poly.vertices)
for i in range(len(me0.vertices)):
    if i in wood_v:
        c = WOODC
    elif i in roof_v:
        c = (TINT[0] * ROOFC[0], TINT[1] * ROOFC[1], TINT[2] * ROOFC[2])
    else:
        c = TINT
    col.data[i].color = (c[0], c[1], c[2], 1.0)
me0.color_attributes.active_color = col
me0.attributes.active_color = col

me = house.data
me.calc_loop_triangles()
print("RESULT verts=%d tris=%d colliders=%d spots=%d"
      % (len(me.vertices), len(me.loop_triangles), len(COLLIDERS), len(SPOTS)))

bpy.ops.object.select_all(action='DESELECT')
house.select_set(True)
try:
    # 'ACTIVE' writes the tint layer whatever the node tree does. The default
    # only exports a colour layer the exporter can trace to Base Color, and
    # loses it silently otherwise.
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True,
                              export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)

with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
