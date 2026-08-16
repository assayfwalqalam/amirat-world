# Builds one Aserai-style mud-brick building and exports .glb + .col.json.
#   blender --background --python make_building.py -- <family> <seed> <out.glb> [assets]
#
# Families (each seed gives a different building within the family):
#   court  one-storey rooms round a walled yard, with a gate
#   house  one to three storeys, upper floors set back, roof terrace
#   tower  narrow, three or four storeys, lantern or small dome on top
#   shops  arcaded ground floor of open shops, living quarters over
#   riad   two storeys round a small inner court with an arcade
#   block  wide, buttressed, two or three storeys
#
# Two rules learned the hard way, do not reorder them:
#   1. Cut each solid while it is still a clean box. Joining first shreds it.
#   2. Erode before cutting. Eroding afterwards tears the wall around openings.
#
# Every structural box is written to the collision file, so what you stand on is
# exactly what you see. A wall carrying a doorway is NEVER recorded as one slab:
# the piers either side and the lintel over are recorded instead, or the opening
# would be visible but sealed.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FAMILY = argv[0] if argv else "house"
SEED = int(argv[1]) if len(argv) > 1 else 1
OUT = argv[2] if len(argv) > 2 else "building.glb"
ASSETS = argv[3] if len(argv) > 3 else "assets"
random.seed(SEED * 7919 + sum(ord(c) for c in FAMILY) * 131)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 32

COLLIDERS = []
SPOTS = []
parts = []
T = 0.42                      # wall thickness


def rec(loc, hx, hy, hz):
    """Record a collider in game axes (blender x,y,z -> game x, z, -y)."""
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def solid(sx, sy, sz, loc, collide=True, keep=True):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    if keep:
        parts.append(ob)
    return ob


def cyl(r, depth, loc, rot=(0, 0, 0), verts=12, keep=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    if keep:
        parts.append(ob)
    return ob


def dome(r, loc, seg=20, squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    ob = bpy.context.active_object
    for v in ob.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
        else:
            v.co.z *= squash
    parts.append(ob)
    return ob


def cut(target, cutter):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    if cutter in parts:
        parts.remove(cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)


def weld(ob, dist=0.0006):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=1, fine=0.02, broad=0.035):
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    weld(ob)
    for sc, st in ((1.2, fine), (3.8, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = sc
        t.noise_depth = 2
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = st
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)


def bevel(ob, width=0.02, segs=2, angle=35):
    m = ob.modifiers.new("bv", 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


# ------------------------------------------------------------- openings
def arch_cut(target, cx, cy, cz, w, h, through, axis='y'):
    """A round-headed opening cut clean through a wall."""
    straight = max(0.15, h - w / 2)
    if axis == 'y':
        cut(target, solid(w, through, straight, (cx, cy, cz + straight / 2), False, False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + straight),
                        rot=(math.pi / 2, 0, 0), verts=16, keep=False))
    else:
        cut(target, solid(through, w, straight, (cx, cy, cz + straight / 2), False, False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + straight),
                        rot=(0, math.pi / 2, 0), verts=16, keep=False))


def slot_cut(target, cx, cy, cz, w, h, through, axis='y'):
    """A plain square window."""
    if axis == 'y':
        cut(target, solid(w, through, h, (cx, cy, cz + h / 2), False, False))
    else:
        cut(target, solid(through, w, h, (cx, cy, cz + h / 2), False, False))


def rec_wall_with_gap(axis, along0, along1, fixed, z0, h, gap_c, gap_w, gap_h):
    """Collision for a wall that has one opening in it: the piers and the lintel."""
    for a, b in ((along0, gap_c - gap_w / 2), (gap_c + gap_w / 2, along1)):
        if b - a > 0.05:
            if axis == 'x':
                rec(((a + b) / 2, fixed, z0 + h / 2), (b - a) / 2, T / 2, h / 2)
            else:
                rec((fixed, (a + b) / 2, z0 + h / 2), T / 2, (b - a) / 2, h / 2)
    if h - gap_h > 0.05:
        if axis == 'x':
            rec((gap_c, fixed, z0 + gap_h + (h - gap_h) / 2), gap_w / 2, T / 2, (h - gap_h) / 2)
        else:
            rec((fixed, gap_c, z0 + gap_h + (h - gap_h) / 2), T / 2, gap_w / 2, (h - gap_h) / 2)


# --------------------------------------------------------------- surface
def weather(*_args, **_kw):
    """Retired. Boolean cracks read as scratched glitches, never as age; the
    age of a wall lives in its texture now, and the structure stays clean."""
    return


def patch(*_args, **_kw):
    """Retired with weather(): the glued-on render slabs made smears."""
    return None


def parapet(cx, cy, w, d, z, height=0.95, rails=True, gap=None):
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
    if False and rails and gap is None and random.random() < 0.72:
        n = max(3, int(w / 1.1))
        for i in range(n):
            if random.random() < 0.12:
                continue
            px = cx - w / 2 + (i + 0.5) * (w / n)
            cyl(0.045, 0.6, (px, cy - d / 2 + 0.15, z + height + 0.3), verts=6)
        solid(w, 0.09, 0.09, (cx, cy - d / 2 + 0.15, z + height + 0.62))


def beams(cx, cy, w, d, z, n=None):
    """Projecting roof beams. They run well back into the wall, because a beam
    that only kisses the surface detaches wherever the render wanders."""
    n = n or max(3, int(w / 1.5))
    for i in range(n):
        px = cx - w / 2 + (i + 0.5) * (w / n)
        cyl(0.062, 1.0, (px, cy - d / 2 + 0.1, z), rot=(math.pi / 2, 0, 0), verts=6)


def ext_stair(x0, y0, w, run_d, z0, z1, along='y'):
    """An outside stair climbing a wall, solid to the ground."""
    steps = max(5, int((z1 - z0) / 0.33))
    rise = (z1 - z0) / steps
    run = run_d / steps
    for i in range(steps):
        h = z0 + rise * (i + 1)
        if along == 'y':
            solid(w, run + 0.04, h, (x0, y0 + i * run, h / 2))
        else:
            solid(run + 0.04, w, h, (x0 + i * run, y0, h / 2))
    return z1


def pillar(cx, cy, z0, h, r=0.3, base=True, cap=True, collide=True):
    """A round, eroded pillar standing on the ground.

    Square posts read as scaffolding, and a cylinder made at z=0 sits half
    under the floor -- both mistakes were visible in the first block.
    """
    if base:
        b = cyl(r * 1.45, 0.22, (cx, cy, z0 + 0.11), verts=12)
        erode(b, 1, 0.015, 0.025)
    shaft = cyl(r, h, (cx, cy, z0 + h / 2), verts=14)
    # taper it slightly toward the top, the way a mud pier is built
    for v in shaft.data.vertices:
        t = (v.co.z - (z0 + h / 2)) / h + 0.5
        v.co.x = cx + (v.co.x - cx) * (1.0 - 0.16 * t)
        v.co.y = cy + (v.co.y - cy) * (1.0 - 0.16 * t)
    erode(shaft, 1, 0.02, 0.035)
    if cap:
        c = cyl(r * 1.3, 0.2, (cx, cy, z0 + h + 0.1), verts=12)
        erode(c, 1, 0.015, 0.025)
    if collide:
        rec((cx, cy, z0 + h / 2), r * 0.92, r * 0.92, h / 2)
    return shaft


def small_dome(cx, cy, z, r):
    cyl(r * 0.94, 0.5, (cx, cy, z + 0.25), verts=14)
    d = dome(r, (cx, cy, z + 0.5), 18, 0.86)
    erode(d, 1, 0.02, 0.03)
    cyl(0.09, 0.5, (cx, cy, z + 0.5 + r * 0.86 + 0.2), verts=8)


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


# ------------------------------------------------------------ the storey
def storey(cx, cy, w, d, z0, h, doorway=None, wins=2, arcade=False, roomspot=True, avoid=None):
    """Four wall slabs, so the inside is a real room you can walk into.

    doorway: None, or (face, offset, width, height) where face is 'S','N','E','W'
    """
    walls = {}
    fy_s, fy_n = cy - d / 2 + T / 2, cy + d / 2 - T / 2
    fx_w, fx_e = cx - w / 2 + T / 2, cx + w / 2 - T / 2
    dface = doorway[0] if doorway else None

    walls['S'] = solid(w, T, h, (cx, fy_s, z0 + h / 2),
                       collide=(dface != 'S' and not arcade))
    walls['N'] = solid(w, T, h, (cx, fy_n, z0 + h / 2), collide=(dface != 'N'))
    walls['W'] = solid(T, d - T * 2, h, (fx_w, cy, z0 + h / 2), collide=(dface != 'W'))
    walls['E'] = solid(T, d - T * 2, h, (fx_e, cy, z0 + h / 2), collide=(dface != 'E'))
    for wl in walls.values():
        erode(wl, 1)

    if doorway:
        face, off, dw, dh = doorway
        if face in ('S', 'N'):
            fy = fy_s if face == 'S' else fy_n
            arch_cut(walls[face], cx + off, fy, z0, dw, dh, T + 1.4, 'y')
            rec_wall_with_gap('x', cx - w / 2, cx + w / 2, fy, z0, h, cx + off, dw, dh)
            SPOTS.append({"c": [round(cx + off - dw / 2, 3), round(z0, 3), round(-fy, 3)],
                          "r": [round(dw, 3), round(dh, 3)], "k": "door",
                          "f": (0 if face == 'S' else 180)})
        else:
            fx = fx_w if face == 'W' else fx_e
            arch_cut(walls[face], fx, cy + off, z0, dw, dh, T + 1.4, 'x')
            rec_wall_with_gap('y', cy - d / 2 + T, cy + d / 2 - T, fx, z0, h, cy + off, dw, dh)
            SPOTS.append({"c": [round(fx, 3), round(z0, 3), round(-(cy + off - dw / 2), 3)],
                          "r": [round(dw, 3), round(dh, 3)], "k": "door",
                          "f": (270 if face == 'W' else 90)})

    if arcade:
        # a run of open arches along the south face, the shop fronts
        n = max(2, int(w / 3.4))
        step = w / n
        for i in range(n):
            ax = cx - w / 2 + (i + 0.5) * step
            skip = (doorway and doorway[0] == 'S' and abs(ax - (cx + doorway[1])) < 2.2) or \
                   (avoid and avoid[0] - 0.4 < ax < avoid[1] + 0.4)
            if skip:
                # this bay stays solid wall, so it must also stay solid to walk into
                rec((ax, fy_s, z0 + h / 2), step * 0.5, T / 2, h / 2)
                continue
            arch_cut(walls['S'], ax, fy_s, z0 + 0.1, step * 0.62, h * 0.74, T + 1.4, 'y')
            rec((ax - step * 0.5, fy_s, z0 + h / 2), step * 0.19, T / 2, h / 2)
        rec((cx + w / 2 - step * 0.19, fy_s, z0 + h / 2), step * 0.19, T / 2, h / 2)
        rec((cx, fy_s, z0 + h * 0.88), w / 2, T / 2, h * 0.12)

    sill = z0 + h * random.uniform(0.48, 0.58)   # one sill line per storey
    arched = random.random() < 0.55               # one window style per face
    if wins > 0:
        # windows take evenly spaced slots with a little jitter. Fully random
        # placement let two arches land on top of each other, or shift into
        # the very doorway they were dodging.
        span = w * 0.72
        seg = span / wins
        for i in range(wins):
            wx = cx - span / 2 + (i + 0.5) * seg + random.uniform(-0.2, 0.2)
            if doorway and doorway[0] == 'S' and abs(wx - (cx + doorway[1])) < 1.55:
                continue
            if avoid and avoid[0] - 0.55 < wx < avoid[1] + 0.55:
                continue
            if arched:
                arch_cut(walls['S'], wx, fy_s, sill, 0.72, 1.25, T + 1.4, 'y')
            else:
                slot_cut(walls['S'], wx, fy_s, sill, 0.7, 1.0, T + 1.4, 'y')
                solid(0.95, T + 0.14, 0.13, (wx, fy_s, sill + 1.06), collide=False)
    if random.random() < 0.75:
        side = 'W' if random.random() < 0.5 else 'E'
        arch_cut(walls[side], fx_w if side == 'W' else fx_e,
                 cy + random.uniform(-d * 0.3, d * 0.3), z0 + h * 0.55, 0.68, 1.15, T + 1.4, 'x')
    if random.random() < 0.5:
        bx2 = cx + random.uniform(-w * 0.3, w * 0.3)
        slot_cut(walls['N'], bx2, fy_n, z0 + h * 0.55, 0.66, 0.95, T + 1.4, 'y')
        solid(0.9, T + 0.14, 0.13, (bx2, fy_n, z0 + h * 0.55 + 1.01), collide=False)

    if roomspot:
        furnish(cx, cy, w, d, z0, h, walls)

    weather(walls['S'], cx, fy_s, w, d, h, z0, 'y')
    weather(walls['N'], cx, fy_n, w, d, h, z0, 'y')
    weather(walls['W'], fx_w, cy, w, d, h, z0, 'x')
    weather(walls['E'], fx_e, cy, w, d, h, z0, 'x')
    for wl in walls.values():
        weld(wl)

    for _ in range(random.randint(1, 3)):
        if random.random() < 0.55:
            patch(cx + random.uniform(-w * 0.3, w * 0.3), fy_s - 0.04,
                  z0 + random.uniform(h * 0.2, h * 0.7),
                  random.uniform(1.1, 2.6), random.uniform(0.8, 1.9), 'y')
        else:
            sg = 1 if random.random() < 0.5 else -1
            patch(cx + sg * (w / 2 - T / 2 - 0.04), cy + random.uniform(-d * 0.3, d * 0.3),
                  z0 + random.uniform(h * 0.2, h * 0.7),
                  random.uniform(1.0, 2.2), random.uniform(0.8, 1.8), 'x')

    if roomspot:
        SPOTS.append({"c": [round(cx, 3), round(z0 + 0.3, 3), round(-cy, 3)],
                      "r": [round(w / 2 - 1.1, 2), round(d / 2 - 1.1, 2)], "k": "room"})
    # where a torch bracket belongs: flush on the front face
    SPOTS.append({"c": [round(cx + w * 0.3, 3), round(z0 + 2.5, 3), round(-(cy - d / 2), 3)],
                  "r": [0.2, 0.2], "k": "torch", "f": 0})
    return walls


def floor_slab(cx, cy, w, d, z, thick=0.4, proud=False):
    """A floor. An intermediate floor stands slightly proud of the wall face,
    a string course: the line between storeys is then a deliberate band rather
    than an accident of two surfaces meeting."""
    if proud:
        solid(w + 0.16, d + 0.16, thick, (cx, cy, z + thick / 2))
    else:
        solid(w, d, thick, (cx, cy, z + thick / 2))


def bulkhead(cx, cy, z):
    """The little room over a stair head, standard furniture of these roofs
    (study: every second roof in the reference panorama carries one)."""
    bw, bd, bh = 2.1, 2.1, 2.2
    solid(bw, T, bh, (cx, cy + bd / 2 - T / 2, z + bh / 2))
    solid(T, bd - T * 2, bh, (cx - bw / 2 + T / 2, cy, z + bh / 2))
    solid(T, bd - T * 2, bh, (cx + bw / 2 - T / 2, cy, z + bh / 2))
    fy = cy - bd / 2 + T / 2
    for sgn in (-1, 1):
        solid(0.3, T, bh, (cx + sgn * (bw / 2 - 0.15), fy, z + bh / 2))
    solid(bw, T, 0.35, (cx, fy, z + bh - 0.175))
    cap = solid(bw + 0.5, bd + 0.5, 0.3, (cx, cy, z + bh + 0.15))
    erode(cap, 1, 0.015, 0.025)


# =============================================================== families
def build_court():
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
    erode(wall_s, 1, 0.015, 0.022)
    arch_cut(wall_s, goff, sy, 0, gw, 2.5, 1.4, 'y')
    rec_wall_with_gap('x', -W / 2, W / 2, sy, 0, yh, goff, gw, 2.5)
    weld(wall_s)
    SPOTS.append({"c": [round(goff - gw / 2, 3), 0.0, round(-sy, 3)],
                  "r": [round(gw, 3), 2.5], "k": "door", "f": 0})
    for sx in (-1, 1):
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
        erode(p3, 1, 0.012, 0.02)
    SPOTS.append({"c": [0.0, 0.05, round(-(-D / 4), 3)],
                  "r": [round(W / 2 - 2.5, 2), round(D / 5, 2)], "k": "court"})


def build_house(storeys=None):
    storeys = storeys or random.choice([1, 2, 2, 3])
    W = random.uniform(8.5, 12.5)
    D = random.uniform(7.5, 10.5)
    heights = [random.uniform(3.0, 3.7)] + [random.uniform(2.7, 3.3) for _ in range(storeys - 1)]
    want_stair = random.random() < 0.72
    want_balcony = storeys >= 2 and not want_stair and random.random() < 0.45
    stair_x = -W / 2 + 0.95
    setbacks = [(i < storeys - 1 and random.random() < 0.5) for i in range(storeys)]
    if (want_stair or want_balcony) and storeys >= 2:
        # the stair or the balcony meets a door in this face, so this face
        # must not step back from under it
        setbacks[0] = False

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
        av = (-W / 2, -W / 2 + 1.95) if (want_stair and i == 0) else None
        storey(cx, cy, cw, cd, z, h, doorway=door, wins=random.randint(1, 3), avoid=av)
        floor_slab(cx, cy, cw, cd, z + h, proud=(i < storeys - 1))
        beams(cx, cy, cw, cd, z + h + 0.2)
        z += h + 0.4
        if setbacks[i]:
            back = random.uniform(1.2, 2.4)
            # the terrace is walled on its three OPEN sides only -- a parapet
            # round the whole old footprint left walls hanging in the air
            f_y = cy - cd / 2
            solid(cw, 0.3, 0.85, (cx, f_y + 0.15, z + 0.425))
            for sxp in (-1, 1):
                solid(0.3, back - 0.3, 0.85,
                      (cx + sxp * (cw / 2 - 0.15), f_y + back / 2, z + 0.425))
            SPOTS.append({"c": [round(cx, 3), round(z, 3), round(-(cy - cd / 2 + back / 2), 3)],
                          "r": [round(cw / 2 - 0.8, 2), round(back / 2 - 0.2, 2)], "k": "balcony"})
            cd -= back
            cy += back / 2
    parapet(cx, cy, cw, cd, z, random.uniform(0.85, 1.15),
            gap=(stair_x, 1.8) if (want_stair and storeys == 1) else None)
    SPOTS.append({"c": [round(cx, 3), round(z, 3), round(-cy, 3)],
                  "r": [round(cw / 2 - 1.0, 2), round(cd / 2 - 1.0, 2)], "k": "roof"})
    if storeys >= 2 and random.random() < 0.6:
        bulkhead(cx + cw / 2 - 1.6, cy + cd / 2 - 1.6, z)

    if want_stair:
        # to the upper doorway, or through the parapet gap onto the roof
        z1 = (0.4 + heights[0] + 0.4) if storeys >= 2 else (z)
        ext_stair(stair_x, -D / 2 - 2.9, 1.45, 3.0, 0, z1)

    if want_balcony:
        bw = W * 0.5
        by = -D / 2 - 0.9
        bz = 0.4 + heights[0] + 0.4           # exactly the upper floor level
        solid(bw, 1.8, 0.22, (0, by, bz - 0.11))
        n_c = max(3, int(bw / 1.1))
        for i2 in range(n_c):                 # corbel beams running back into the wall
            px2 = -bw / 2 + (i2 + 0.5) * (bw / n_c)
            cyl(0.07, 2.6, (px2, -D / 2 - 0.55, bz - 0.31), rot=(math.pi / 2, 0, 0), verts=6)
        for sx in (-1, 1):                    # posts a person would trust
            pillar(sx * (bw / 2 - 0.22), by - 0.65, 0.0, bz - 0.22, r=0.15)
        # walls on the three OPEN sides only -- a fourth ran straight across
        # the doorway, waist high
        solid(bw, 0.26, 0.75, (0, by - 0.9 + 0.13, bz + 0.375))
        for sx in (-1, 1):
            solid(0.26, 1.8 - 0.26, 0.75, (sx * (bw / 2 - 0.13), by + 0.13, bz + 0.375))
        SPOTS.append({"c": [0.0, round(bz, 3), round(-by, 3)],
                      "r": [round(bw / 2 - 0.5, 2), 0.55], "k": "balcony"})


def build_tower():
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
        storey(0, 0, W - i * 0.28, D - i * 0.28, z, h, doorway=door,
               wins=random.randint(1, 2),
               avoid=(-W / 2, -W / 2 + 1.75) if i == 0 else None)
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


def build_shops():
    W = random.uniform(14, 20)
    D = random.uniform(8, 11)
    floor_slab(0, 0, W, D, 0)
    h0 = random.uniform(3.6, 4.2)
    storey(0, 0, W, D, 0.4, h0, doorway=None, wins=0, arcade=True, roomspot=True,
           avoid=(W / 2 - 2.1, W / 2))
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
    if random.random() < 0.5:
        bulkhead(W / 2 - 1.8, D / 2 - 1.8, z)
    # awning poles along the shop front
    for i in range(max(2, int(W / 4))):
        px = -W / 2 + (i + 0.5) * (W / max(2, int(W / 4)))
        pillar(px, -D / 2 - 1.0, 0.0, 3.0, r=0.095, base=False, cap=False)
    solid(W * 0.94, 2.0, 0.14, (0, -D / 2 - 1.0, 3.05))
    ext_stair(W / 2 - 0.9, -D / 2 - 2.9, 1.45, 3.0, 0, 0.4 + h0 + 0.4)


def build_riad():
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


def build_block():
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
        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(3, 5),
               avoid=(-W / 2, -W / 2 + 1.95) if i == 0 else None)
        floor_slab(0, 0, W, D, z + h, proud=(i < storeys - 1))
        if i == 0:
            beams(0, 0, W, D, z + h + 0.2)
        z += h + 0.4
    parapet(0, 0, W, D, z, 1.1)
    SPOTS.append({"c": [0.0, round(z, 3), 0.0],
                  "r": [round(W / 2 - 1.4, 2), round(D / 2 - 1.4, 2)], "k": "roof"})
    if random.random() < 0.65:
        bulkhead(-W / 2 + 1.6, D / 2 - 1.6, z)
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


BUILDERS = {"court": build_court, "house": build_house, "tower": build_tower,
            "shops": build_shops, "riad": build_riad, "block": build_block}
BUILDERS.get(FAMILY, build_house)()

# ------------------------------------------------------------- assemble
for o in parts:
    bevel(o, 0.02)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = FAMILY
weld(ob, 0.0004)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=2.6)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new("adobe")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1.0
ob.data.materials.clear()
ob.data.materials.append(mat)

tex_path = os.path.abspath(os.path.join(ASSETS, "t_adobe_d.jpg"))
tn = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
else:
    bsdf.inputs["Base Color"].default_value = (0.82, 0.69, 0.50, 1)

nor_path = os.path.abspath(os.path.join(ASSETS, "t_adobe_gn.jpg"))
if os.path.exists(nor_path) and tn is not None:
    nimg = bpy.data.images.load(nor_path)
    nimg.colorspace_settings.name = 'Non-Color'
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nimg
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = 1.2
    nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    nimg.pack()

if tn is not None:
    tn.image.pack()

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%d verts=%d tris=%d colliders=%d spots=%d"
      % (FAMILY, SEED, len(me.vertices), len(me.loop_triangles), len(COLLIDERS), len(SPOTS)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
