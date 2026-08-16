# The great house of the town: a colossal dome on a stepped platform, with
# hanging gardens on the terraces and a hall you can walk into.
#   blender --background --python make_grand.py -- <out.glb> [assets] [scale]
#
# This one is deliberately out of scale with everything else. The platform is
# about 120 m across and the finial stands near 80 m, so it reads from the far
# side of the map and closes every street that points at it.
#
# Two materials only: cut stone for the building, and leaf for the gardens.
# Everything is eroded, because a clean edge on this much surface looks moulded.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "grand.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"
random.seed(20260816)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

COLLIDERS = []
SPOTS = []
stone = []          # everything built
leaf = []           # everything planted


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def spot(kind, x, y, z, rx, rz, face=0):
    SPOTS.append({"c": [round(x, 2), round(z, 2), round(-y, 2)],
                  "r": [round(rx, 2), round(rz, 2)], "k": kind, "f": face})


def box(sx, sy, sz, loc, rot=0.0, collide=True, into=None):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    (into if into is not None else stone).append(ob)
    return ob


def cyl(r1, r2, h, loc, rot=(0, 0, 0), verts=24, collide=False, into=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    if collide:
        rec(loc, max(r1, r2) * 0.86, max(r1, r2) * 0.86, h / 2)
    (into if into is not None else stone).append(ob)
    return ob


def sphere(r, loc, seg=20, squash=1.0, into=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=max(4, seg // 2))
    ob = bpy.context.active_object
    if squash != 1.0:
        for v in ob.data.vertices:
            v.co.z *= squash
    (into if into is not None else stone).append(ob)
    return ob


def half_dome(r, loc, seg=24, squash=1.0, into=None):
    ob = sphere(r, loc, seg, 1.0, into)
    for v in ob.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
        else:
            v.co.z *= squash
    return ob


def torus(major, minor, loc, seg=24, rot=(0, 0, 0), into=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc,
                                     major_segments=seg, minor_segments=8, rotation=rot)
    (into if into is not None else stone).append(bpy.context.active_object)
    return bpy.context.active_object


def weld(ob, dist=0.0008):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=1, fine=0.05, broad=0.1):
    bpy.context.view_layer.objects.active = ob
    if levels:
        m = ob.modifiers.new("sub", 'SUBSURF')
        m.subdivision_type = 'SIMPLE'
        m.levels = m.render_levels = levels
        bpy.ops.object.modifier_apply(modifier=m.name)
        weld(ob)
    for sc, st in ((1.4, fine), (5.0, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = sc
        t.noise_depth = 2
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = st
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)


def cut(target, cutter):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    for lst in (stone, leaf):
        if cutter in lst:
            lst.remove(cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)


def arch_through(target, cx, cy, cz, w, h, thick, axis='y'):
    straight = max(0.2, h - w / 2)
    if axis == 'y':
        c = box(w, thick, straight, (cx, cy, cz + straight / 2), 0, False)
        stone.remove(c); cut(target, c)
        c2 = cyl(w / 2, w / 2, thick, (cx, cy, cz + straight), (math.pi / 2, 0, 0), 20, False)
        stone.remove(c2); cut(target, c2)
    else:
        c = box(thick, w, straight, (cx, cy, cz + straight / 2), 0, False)
        stone.remove(c); cut(target, c)
        c2 = cyl(w / 2, w / 2, thick, (cx, cy, cz + straight), (0, math.pi / 2, 0), 20, False)
        stone.remove(c2); cut(target, c2)


# ============================================================ the platform
TIERS = [(120.0, 0.0, 5.0), (100.0, 5.0, 4.4), (82.0, 9.4, 4.0), (66.0, 13.4, 3.6)]
TOP = 17.0                     # the floor the hall stands on

for i, (side, z0, h) in enumerate(TIERS):
    t = box(side, side, h, (0, 0, z0 + h / 2))
    erode(t, 0, 0.05, 0.11)
    # a low kerb round each terrace, so the edge reads and you cannot fall off
    k = box(side + 0.6, side + 0.6, 0.9, (0, 0, z0 + h + 0.45))
    erode(k, 0, 0.03, 0.06)


def great_stair(face_sgn):
    """The broad flight up the front, in four flights with landings."""
    width = 26.0
    steps_total = 34
    rise = TOP / steps_total
    run = 1.5
    x0 = 0.0
    y_start = face_sgn * (TIERS[0][0] / 2 + 6.0)
    for i in range(steps_total):
        h = rise * (i + 1)
        y = y_start - face_sgn * (i * run)
        box(width, run + 0.06, h, (x0, y, h / 2))
    # cheek walls either side, and a lamp standard every few steps
    for sx in (-1, 1):
        c = box(1.6, steps_total * run, TOP * 0.42,
                (sx * (width / 2 + 0.8), y_start - face_sgn * (steps_total * run / 2),
                 TOP * 0.21))
        erode(c, 0, 0.04, 0.08)
        for k in range(4):
            fy = y_start - face_sgn * (k * steps_total * run / 4 + 3)
            fz = rise * (k * steps_total / 4 + 2) + TOP * 0.42 * 0.5
            spot('torch', sx * (width / 2 + 0.8), fy, rise * (k * steps_total / 4 + 2) + 1.2,
                 0.3, 0.3)


great_stair(-1)

# side ramps, narrower
for sx in (-1, 1):
    steps = 26
    rise = TOP / steps
    run = 1.4
    for i in range(steps):
        h = rise * (i + 1)
        box(9.0, run + 0.05, h, (sx * (TIERS[0][0] / 2 - 14), TIERS[0][0] / 2 + 4 - i * run, h / 2))

# ============================================================ the gardens
def planter(cx, cy, w, d, z, tier):
    """A raised bed on a terrace, planted and spilling over the edge."""
    box(w, d, 1.15, (cx, cy, z + 0.575))
    rim = box(w + 0.5, d + 0.5, 0.35, (cx, cy, z + 1.32))
    erode(rim, 0, 0.02, 0.04)
    # the planting: clustered leaf masses, denser at the middle
    n = int(w * d * 0.30)
    for _ in range(n):
        px = cx + random.uniform(-w / 2 + 0.4, w / 2 - 0.4)
        py = cy + random.uniform(-d / 2 + 0.4, d / 2 - 0.4)
        r = random.uniform(0.5, 1.5)
        b = sphere(r, (px, py, z + 1.5 + r * random.uniform(0.2, 0.7)),
                   seg=8, squash=random.uniform(0.5, 0.85), into=leaf)
        for v in b.data.vertices:
            v.co.x += random.uniform(-0.14, 0.14)
            v.co.y += random.uniform(-0.14, 0.14)
            v.co.z += random.uniform(-0.12, 0.12)
    # and what hangs over the side: strands of foliage falling down the face
    for _ in range(int(w * 1.3)):
        hx = cx + random.uniform(-w / 2, w / 2)
        hy = cy - d / 2 - 0.2
        fall = random.uniform(2.2, tier * 0.92)
        steps = max(3, int(fall / 0.85))
        for k in range(steps):
            t = k / float(steps)
            r = random.uniform(0.32, 0.62) * (1.0 - 0.45 * t)
            s = sphere(r, (hx + random.uniform(-0.3, 0.3),
                           hy - random.uniform(0.0, 0.45),
                           z + 1.3 - t * fall),
                       seg=6, squash=0.8, into=leaf)
            for v in s.data.vertices:
                v.co.x += random.uniform(-0.1, 0.1)
                v.co.z += random.uniform(-0.1, 0.1)


# beds along the three free sides of each terrace
for i, (side, z0, h) in enumerate(TIERS[:-1]):
    top_z = z0 + h + 0.9
    inner = TIERS[i + 1][0] / 2
    band = (side / 2 - inner)
    if band < 3.5:
        continue
    mid = inner + band / 2
    tier_h = TIERS[i][2] + 0.9
    planter(0, mid, side * 0.62, band * 0.62, top_z, tier_h)              # back
    for sx in (-1, 1):
        planter(sx * mid, 0, band * 0.62, side * 0.5, top_z, tier_h)      # sides
    for sx in (-1, 1):
        planter(sx * (side / 2 - band / 2), -mid, band * 0.62, band * 0.62, top_z, tier_h)

# a channel of water down the middle of the front, between the flights
box(3.2, 46.0, 0.5, (0, -TIERS[0][0] / 2 - 14, TOP * 0.1), 0, False)

# ================================================================ the hall
HW, HD, HH = 46.0, 46.0, 26.0
floor = box(HW + 8, HD + 8, 1.2, (0, 0, TOP + 0.6))
erode(floor, 0, 0.02, 0.04)
FL = TOP + 1.2

WT = 2.2
walls = {}
walls['S'] = box(HW, WT, HH, (0, -HD / 2 + WT / 2, FL + HH / 2), 0, False)
walls['N'] = box(HW, WT, HH, (0, HD / 2 - WT / 2, FL + HH / 2), 0, False)
walls['W'] = box(WT, HD - WT * 2, HH, (-HW / 2 + WT / 2, 0, FL + HH / 2), 0, False)
walls['E'] = box(WT, HD - WT * 2, HH, (HW / 2 - WT / 2, 0, FL + HH / 2), 0, False)
for w in walls.values():
    erode(w, 0, 0.04, 0.09)

# the great portal: an iwan, a huge recessed arch on the south face
PORT_W, PORT_H = 14.0, 22.0
arch_through(walls['S'], 0, -HD / 2 + WT / 2, FL, PORT_W, PORT_H, WT + 4)
for a, b in ((-HW / 2, -PORT_W / 2), (PORT_W / 2, HW / 2)):
    rec(((a + b) / 2, -HD / 2 + WT / 2, FL + HH / 2), (b - a) / 2, WT / 2, HH / 2)
rec((0, -HD / 2 + WT / 2, FL + PORT_H + (HH - PORT_H) / 2), PORT_W / 2, WT / 2, (HH - PORT_H) / 2)
spot('door', -PORT_W / 2, -HD / 2 + WT / 2, FL, PORT_W, PORT_H, 0)

# the portal's frame, standing proud of the wall
frame = box(PORT_W + 9, 1.6, PORT_H + 8, (0, -HD / 2 - 0.4, FL + (PORT_H + 8) / 2), 0, False)
erode(frame, 0, 0.03, 0.06)
arch_through(frame, 0, -HD / 2 - 0.4, FL, PORT_W + 1.2, PORT_H + 1.0, 4.0)
# stepped niche courses inside the head of the arch, standing for muqarnas
for k in range(5):
    rr = PORT_W / 2 - k * 0.85
    if rr < 1.2:
        break
    n = 9
    for j in range(n):
        a = math.pi * (j + 0.5) / n
        px = math.cos(a) * rr
        pz = FL + PORT_H - PORT_W / 2 + math.sin(a) * rr
        box(0.9, 0.9, 0.9, (px, -HD / 2 + WT / 2 - 0.6 - k * 0.7, pz), 0, False)

# windows high on the other three faces
for face, ax, fixed in (('N', 'x', HD / 2 - WT / 2), ('W', 'y', -HW / 2 + WT / 2),
                        ('E', 'y', HW / 2 - WT / 2)):
    for i in range(5):
        o = -16 + i * 8
        if face == 'N':
            arch_through(walls[face], o, fixed, FL + 13, 3.0, 6.0, WT + 3, 'y')
        else:
            arch_through(walls[face], fixed, o, FL + 13, 3.0, 6.0, WT + 3, 'x')
    # and a doorway at ground level on each side
    if face == 'N':
        arch_through(walls[face], 0, fixed, FL, 6.0, 10.0, WT + 3, 'y')
        rec((-HW / 4 - 1.5, fixed, FL + HH / 2), HW / 4 - 1.5, WT / 2, HH / 2)
        rec((HW / 4 + 1.5, fixed, FL + HH / 2), HW / 4 - 1.5, WT / 2, HH / 2)
        rec((0, fixed, FL + 10 + (HH - 10) / 2), 3.0, WT / 2, (HH - 10) / 2)
        spot('door', -3.0, fixed, FL, 6.0, 10.0, 180)
    else:
        arch_through(walls[face], fixed, 0, FL, 6.0, 10.0, WT + 3, 'x')
        rec((fixed, -HD / 4 - 1.5, FL + HH / 2), WT / 2, HD / 4 - 1.5, HH / 2)
        rec((fixed, HD / 4 + 1.5, FL + HH / 2), WT / 2, HD / 4 - 1.5, HH / 2)
        rec((fixed, 0, FL + 10 + (HH - 10) / 2), WT / 2, 3.0, (HH - 10) / 2)
        spot('door', fixed, -3.0, FL, 6.0, 10.0, 270 if face == 'W' else 90)

for w in walls.values():
    weld(w)

# ---------------------------------------------------------- the interior
# an arcade of great columns carrying the gallery
for i in range(8):
    a = i * math.pi * 2 / 8 + math.pi / 8
    px, py = math.cos(a) * 16.5, math.sin(a) * 16.5
    cyl(1.5, 1.25, 14.0, (px, py, FL + 7.0), verts=16, collide=True)
    cyl(1.9, 1.6, 1.0, (px, py, FL + 0.5), verts=16)
    cyl(1.6, 2.1, 1.4, (px, py, FL + 14.7), verts=16)
    spot('lamp', px, py, FL + 12.5, 0.4, 0.4)
# the gallery floor ring
for i in range(8):
    a = i * math.pi * 2 / 8 + math.pi / 8
    a2 = (i + 1) * math.pi * 2 / 8 + math.pi / 8
    mx, my = (math.cos(a) + math.cos(a2)) / 2 * 19.5, (math.sin(a) + math.sin(a2)) / 2 * 19.5
    box(7.0, 7.0, 0.9, (mx, my, FL + 16.0), a + math.pi / 8)
# the mihrab: a deep niche in the qibla wall
niche = box(7.0, 3.4, 11.0, (0, HD / 2 - WT - 1.4, FL + 5.5), 0, False)
erode(niche, 0, 0.03, 0.05)
arch_through(niche, 0, HD / 2 - WT - 1.4, FL, 4.6, 9.0, 5.0, 'y')
# the floor of the hall, and where the game may lay carpets and lamps
box(HW - WT * 2, HD - WT * 2, 0.3, (0, 0, FL + 0.15))
spot('room', 0, 0, FL + 0.3, HW / 2 - 6, HD / 2 - 6)
spot('room', 0, -10, FL + 0.3, 10, 6)
for i in range(6):
    a = i * math.pi * 2 / 6
    spot('lamp', math.cos(a) * 9, math.sin(a) * 9, FL + 15.0, 0.4, 0.4)

# ================================================================ the dome
DRUM_R = 21.0
DRUM_Z = FL + HH
drum = cyl(DRUM_R, DRUM_R + 0.4, 9.0, (0, 0, DRUM_Z + 4.5), verts=36, collide=True)
erode(drum, 0, 0.03, 0.07)
for i in range(20):
    a = i * math.pi * 2 / 20
    px, py = math.cos(a) * (DRUM_R + 0.6), math.sin(a) * (DRUM_R + 0.6)
    c = cyl(1.1, 1.1, 5.2, (px, py, DRUM_Z + 4.2), (math.pi / 2, 0, -a), 14, False)
    stone.remove(c); cut(drum, c)
weld(drum)
torus(DRUM_R + 1.0, 0.8, (0, 0, DRUM_Z + 9.2), seg=36)

MAIN = half_dome(DRUM_R + 1.6, (0, 0, DRUM_Z + 9.4), seg=40, squash=1.06)
erode(MAIN, 0, 0.05, 0.12)
# ribs running up the dome
for i in range(24):
    a = i * math.pi * 2 / 24
    for k in range(9):
        t = (k + 1) / 10.0
        ang = t * math.pi / 2
        r = (DRUM_R + 1.6) * math.cos(ang)
        zz = DRUM_Z + 9.4 + (DRUM_R + 1.6) * 1.06 * math.sin(ang)
        sphere(0.55 * (1 - t * 0.5), (math.cos(a) * r, math.sin(a) * r, zz), seg=6, squash=0.7)

# the finial
cyl(2.4, 1.6, 2.4, (0, 0, DRUM_Z + 9.4 + (DRUM_R + 1.6) * 1.06 + 1.0), verts=18)
cyl(1.1, 0.7, 4.4, (0, 0, DRUM_Z + 9.4 + (DRUM_R + 1.6) * 1.06 + 4.2), verts=14)
sphere(1.3, (0, 0, DRUM_Z + 9.4 + (DRUM_R + 1.6) * 1.06 + 7.0), seg=14)
cyl(0.5, 0.0, 4.0, (0, 0, DRUM_Z + 9.4 + (DRUM_R + 1.6) * 1.06 + 10.0), verts=10)

# four half domes buttressing the main one
for i in range(4):
    a = i * math.pi / 2 + math.pi / 4
    px, py = math.cos(a) * 21.0, math.sin(a) * 21.0
    cyl(7.5, 7.8, 4.0, (px, py, DRUM_Z + 2.0), verts=20)
    hd = half_dome(8.0, (px, py, DRUM_Z + 4.0), seg=22, squash=0.95)
    erode(hd, 0, 0.03, 0.07)
    cyl(0.7, 0.4, 3.0, (px, py, DRUM_Z + 4.0 + 8.0 * 0.95 + 1.5), verts=10)

# corner domes on the hall roof
for sx in (-1, 1):
    for sy in (-1, 1):
        px, py = sx * (HW / 2 - 5.0), sy * (HD / 2 - 5.0)
        cyl(4.4, 4.6, 3.0, (px, py, FL + HH + 1.5), verts=16)
        d = half_dome(4.7, (px, py, FL + HH + 3.0), seg=18, squash=0.9)
        erode(d, 0, 0.02, 0.05)
        cyl(0.5, 0.3, 2.2, (px, py, FL + HH + 3.0 + 4.7 * 0.9 + 1.1), verts=8)

# ============================================================= minarets
def minaret(px, py, h=54.0):
    cyl(4.2, 4.0, 4.0, (px, py, TOP + 2.0), verts=16, collide=True)
    sh = cyl(3.1, 2.3, h * 0.62, (px, py, TOP + 4.0 + h * 0.31), verts=18, collide=True)
    erode(sh, 0, 0.03, 0.06)
    z1 = TOP + 4.0 + h * 0.62
    cyl(3.9, 3.9, 0.9, (px, py, z1 + 0.45), verts=20)
    gal = cyl(2.6, 2.6, 3.0, (px, py, z1 + 2.4), verts=16, collide=True)
    for i in range(10):
        a = i * math.pi * 2 / 10
        c = cyl(0.5, 0.5, 4.0, (px + math.cos(a) * 3.0, py + math.sin(a) * 3.0, z1 + 2.4),
                (math.pi / 2, 0, -a), 10, False)
        stone.remove(c); cut(gal, c)
    weld(gal)
    for i in range(12):
        a = i * math.pi * 2 / 12
        cyl(0.16, 0.16, 2.4, (px + math.cos(a) * 3.6, py + math.sin(a) * 3.6, z1 + 2.2), verts=6)
    cyl(3.9, 3.9, 0.7, (px, py, z1 + 4.2), verts=20)
    spot('lamp', px, py, z1 + 3.0, 0.5, 0.5)
    z2 = z1 + 4.6
    cyl(2.2, 1.7, h * 0.26, (px, py, z2 + h * 0.13), verts=16)
    z3 = z2 + h * 0.26
    cyl(2.8, 2.8, 0.7, (px, py, z3 + 0.35), verts=18)
    d = half_dome(2.5, (px, py, z3 + 0.7), seg=16, squash=1.15)
    cyl(0.4, 0.0, 3.2, (px, py, z3 + 0.7 + 2.5 * 1.15 + 1.6), verts=10)


for sx in (-1, 1):
    for sy in (-1, 1):
        minaret(sx * (TIERS[3][0] / 2 - 4.5), sy * (TIERS[3][0] / 2 - 4.5))

# lamps and torches round the terrace edge
for i in range(16):
    a = i * math.pi * 2 / 16
    r = TIERS[3][0] / 2 + 1.0
    spot('torch', math.cos(a) * r, math.sin(a) * r, TOP + 1.4, 0.3, 0.3)
for i in range(12):
    a = i * math.pi * 2 / 12
    spot('roof', math.cos(a) * 26, math.sin(a) * 26, TOP + 1.2, 2.0, 2.0)

# =============================================================== assemble
ALL = stone + leaf
n_stone = len(stone)
bpy.ops.object.select_all(action='DESELECT')
for o in ALL:
    o.select_set(True)
bpy.context.view_layer.objects.active = stone[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "grand"
weld(ob, 0.0006)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=3.2)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new("grand")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.95
ob.data.materials.clear()
ob.data.materials.append(mat)
tex_path = os.path.abspath(os.path.join(ASSETS, "t_ashlar_d.jpg"))
tn = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])

while len(ob.data.color_attributes):
    ob.data.color_attributes.remove(ob.data.color_attributes[0])
ob.data.color_attributes.active_color = ob.data.color_attributes.new(
    name="ao", type='FLOAT_COLOR', domain='CORNER')
scene.render.bake.target = 'VERTEX_COLORS'
scene.render.bake.margin = 2
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
try:
    bpy.ops.object.bake(type='AO')
except Exception as e:
    print("bake failed:", e)

# Tint: warm limewash for the stone, and green wherever a vertex sits inside
# one of the planted volumes. One material, two readings, no second texture.
me = ob.data
me.calc_loop_triangles()
data = me.color_attributes["ao"].data
zmax_leaf = {}
verts = me.vertices


def is_leafy(co):
    # planted mass sits on the terraces, outside the hall footprint
    if abs(co.x) < HW / 2 + 2 and abs(co.y) < HD / 2 + 2:
        return False
    if co.z > TOP + 2.5:
        return False
    for i, (side, z0, h) in enumerate(TIERS[:-1]):
        top_z = z0 + h + 0.9
        if top_z - 0.6 < co.z < top_z + 6.5:
            return True
        if z0 - 0.2 < co.z < top_z and (abs(co.x) > TIERS[i + 1][0] / 2 or abs(co.y) > TIERS[i + 1][0] / 2):
            return True
    return False


for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index
        co = verts[vi].co
        ao = 0.30 + 0.66 * data[li].color[0]
        if is_leafy(co):
            g = random.uniform(0.86, 1.14)
            data[li].color = (ao * 0.30 * g, ao * 0.62 * g, ao * 0.24 * g, 1.0)
        else:
            data[li].color = (ao * 1.0, ao * 0.955, ao * 0.878, 1.0)

if tn is not None:
    tn.image.pack()
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = "ao"
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    nt.links.new(tn.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(vc.outputs['Color'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

print("RESULT grand verts=%d tris=%d colliders=%d spots=%d"
      % (len(me.vertices), len(me.loop_triangles), len(COLLIDERS), len(SPOTS)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
