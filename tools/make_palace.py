# THE QASR - the grand palace, built to the owner's own drawn layout:
# a great centre block carrying the gate and the crowning gold dome, two tall
# thin minaret towers flanking it, and two lower gated wings, symmetric.
# Seven storeys, each one its own idea, judged against the fantasy references
# (fantasy_3 stacked lit mass, fantasy_5 white-gold serenity). Aniconic.
#
#   blender --background --python make_palace.py -- <out.glb> [assets]
import bpy, bmesh, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "qasr.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

stone, gold, wood, glow, earth, water = [], [], [], [], [], []
SEG = 64
COLS = []               # collision boxes, blender coords


def col(cx, cy, cz, hx, hy, hz):
    COLS.append({"c": [round(cx, 2), round(cz, 2), round(-cy, 2)],
                 "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def box(sx, sy, sz, loc, into, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = ob.modifiers.new("bv", 'BEVEL'); m.width = bevel; m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
    into.append(ob)
    return ob


def cyl(r, h, loc, into, verts=SEG):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=verts)
    into.append(bpy.context.active_object)
    return bpy.context.active_object


def onion_profile(n):
    ctrl = [(0.00, 0.72), (0.06, 0.88), (0.16, 1.00), (0.30, 1.02),
            (0.44, 0.94), (0.58, 0.78), (0.70, 0.58), (0.80, 0.40),
            (0.88, 0.25), (0.94, 0.13), (0.98, 0.05), (1.00, 0.0)]
    pts = []
    for i in range(n + 1):
        t = i / n
        r = ctrl[-1][1]
        for k in range(len(ctrl) - 1):
            t0, r0 = ctrl[k]; t1, r1 = ctrl[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0 or 1); f = f * f * (3 - 2 * f)
                r = r0 + (r1 - r0) * f
                break
        pts.append((r, 1.06 * (t ** 0.92)))
    return pts


def dome(cx, cy, base_z, belly_r, height, ribs=16, drum=True, seg=None):
    """A gold onion dome, optionally on its stone drum."""
    if drum:
        cyl(belly_r * 0.74, belly_r * 0.7, (cx, cy, base_z + belly_r * 0.35), stone, verts=40)
        z0 = base_z + belly_r * 0.7
    else:
        z0 = base_z
    prof = onion_profile(max(72, int(belly_r * 14)))
    me = bpy.data.meshes.new("d"); ob = bpy.data.objects.new("d", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new(); rings = []
    nseg = seg or max(SEG, int(belly_r * 18))
    for (rf, zf) in prof:
        ring = []
        for s in range(nseg):
            th = s / nseg * 2 * math.pi
            rib = 1.0 + 0.03 * (0.5 - 0.5 * math.cos(ribs * th)) * max(0.0, 1 - zf) ** 0.5
            rr = belly_r * rf * rib
            ring.append(bm.verts.new((cx + math.cos(th) * rr, cy + math.sin(th) * rr, z0 + zf * height)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(nseg):
            s2 = (s + 1) % nseg
            try:
                bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))
            except ValueError:
                pass
    tip = bm.verts.new((cx, cy, z0 + prof[-1][1] * height + 0.01))
    # the fan must walk the SAME ring count the rings were built with: at a
    # fixed SEG it overran small domes and left a pinhole on big ones
    for s in range(nseg):
        s2 = (s + 1) % nseg
        try:
            bm.faces.new((rings[-1][s], rings[-1][s2], tip))
        except ValueError:
            pass
    bm.normal_update(); bm.to_mesh(me); bm.free()
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    gold.append(ob)
    # the alem finial: stacked balls and a spike
    tz = z0 + prof[-1][1] * height
    for i, br in enumerate((belly_r * 0.06, belly_r * 0.045, belly_r * 0.03)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=br, location=(cx, cy, tz + height * 0.05 + i * belly_r * 0.11),
                                             segments=14, ring_count=8)
        gold.append(bpy.context.active_object)
    cyl(belly_r * 0.018, height * 0.30, (cx, cy, tz + height * 0.16), gold, verts=8)


def ogee(t):
    """The pointed-arch head: two circular arcs meeting at the apex.
    t in 0..1 across the opening -> rise in 0..1."""
    t = 2 * t - 1                      # -1..1
    a = abs(t)
    return math.sqrt(max(0.0, 1 - a * a)) * 0.72 + (1 - a) * 0.28


def arch(cx, cy, z0, w, h, depth, into, frame=0.55, face=(0, -1), lit=True):
    """A pointed-arch opening with an explicit outward FACING.

    The first version built every arch along the world X axis whatever wall
    it sat on, so side-wall arches came out as loose pieces hanging in the
    air - the debris cloud. Parts are built in the arch's own frame now
    (width along local X, facing local -Y) and swung round to the wall.
    The lit panel tucks just behind the frame, never inside the wall, which
    is what tore the light with z-fighting before."""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx) + math.pi / 2
    cs, sn = math.cos(yaw), math.sin(yaw)
    made = []

    def part(sx_, sy_, sz_, lx, ly, lz, bev=0.0):
        ob = box(sx_, sy_, sz_, (0, 0, 0), made, bevel=bev)
        ob.location = (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, lz)
        ob.rotation_euler = (0, 0, yaw)
        return ob

    jh = h * 0.55
    part(frame, depth, jh, -w / 2 + frame / 2, 0, z0 + jh / 2)
    part(frame, depth, jh, w / 2 - frame / 2, 0, z0 + jh / 2)
    NSEG = 9
    for i in range(NSEG):
        t0 = i / NSEG; t1 = (i + 1) / NSEG
        x0 = -w / 2 + w * t0; x1 = -w / 2 + w * t1
        r0 = z0 + jh + ogee(t0) * (h - jh); r1 = z0 + jh + ogee(t1) * (h - jh)
        seg_l = math.hypot(x1 - x0, r1 - r0) + frame * 0.4
        ob = part(seg_l, depth, frame, (x0 + x1) / 2, 0, (r0 + r1) / 2)
        ob.rotation_euler = (0, math.atan2(r0 - r1, x1 - x0), yaw)
    # the panel: its back flush with the frame's back, never past it
    if lit is not None:
        ph = h * 0.97 - frame * 0.3
        part(w - frame * 1.3, 0.25, ph,
             0, -depth * 0.5 + 0.24, z0 + ph / 2 + frame * 0.15)
    for ob in made:
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(rotation=True)
    if lit is None:
        into.extend(made)
    else:
        into.extend(made[:-1])
        (glow if lit else stone).append(made[-1])


def arch_row(x0, x1, y, z0, n, w, h, depth, into, lit=True, face=(0, -1)):
    for i in range(n):
        cx = x0 + (x1 - x0) * (i + 0.5) / n
        arch(cx, y, z0, w, h, depth, into, lit=lit, face=face)


def cornice(hx, hy, z, into, lip=0.7):
    box(hx * 2 + lip * 2, hy * 2 + lip * 2, lip * 0.9, (0, 0, z), into, bevel=0.12)


def parapet(cx, cy, hx, hy, z, into, hh=1.3):
    """A crenellated parapet ring."""
    box(hx * 2, 0.7, hh, (cx, cy - hy, z + hh / 2), into)
    box(hx * 2, 0.7, hh, (cx, cy + hy, z + hh / 2), into)
    box(0.7, hy * 2, hh, (cx - hx, cy, z + hh / 2), into)
    box(0.7, hy * 2, hh, (cx + hx, cy, z + hh / 2), into)
    n = int(hx)
    for i in range(n):
        x = cx - hx + (2 * hx) * (i + 0.5) / n
        box(0.9, 0.75, hh * 0.55, (x, cy - hy, z + hh + hh * 0.27), into)
        box(0.9, 0.75, hh * 0.55, (x, cy + hy, z + hh + hh * 0.27), into)


def minaret(cx, cy, htot):
    """A real minaret, not a prop: the shaft is HOLLOW, a door lets you in,
    a spiral stair climbs a newel column to the lantern stage, and up there
    a lantern burns inside the arcade. Solid everywhere a foot can land."""
    r = 3.1
    wall_t = 0.55
    lz = 2.2 + htot * 0.82                     # the lantern stage
    # socle with its own door gap
    NW = 14
    for k in range(NW):
        a = (k + 0.5) / NW * 2 * math.pi - math.pi / 2
        if abs(a + math.pi / 2) < 0.5:          # the gap faces the front (-y)
            continue
        seg_w = 2 * math.pi * r * 1.5 / NW * 1.08
        b = box(seg_w, 0.8, 2.2, (0, 0, 0), stone)
        b.location = (cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5, 1.1)
        b.rotation_euler = (0, 0, a + math.pi / 2)
        col(cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5, 1.1,
            seg_w / 2 + 0.1, seg_w / 2 + 0.1, 1.1)
    # the door frame
    arch(cx, cy - r * 1.5 - 0.3, 0.0, 2.2, 3.6, 0.8, stone, frame=0.4, lit=None)
    # the shaft: a ring of wall segments, hollow inside, all the way up
    shaft_h = lz - 2.2
    for k in range(NW):
        a = (k + 0.5) / NW * 2 * math.pi - math.pi / 2
        # above door height the ring closes; below it the front stays open
        seg_w = 2 * math.pi * r / NW * 1.10
        if abs(a + math.pi / 2) < 0.5:
            b = box(seg_w, wall_t, shaft_h - 3.6, (0, 0, 0), stone)
            b.location = (cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + 3.6 + (shaft_h - 3.6) / 2)
        else:
            b = box(seg_w, wall_t, shaft_h, (0, 0, 0), stone)
            b.location = (cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + shaft_h / 2)
        b.rotation_euler = (0, 0, a + math.pi / 2)
        col(cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + shaft_h / 2,
            seg_w / 2 + 0.08, seg_w / 2 + 0.08, shaft_h / 2)
    # slim lit slots up the shaft so the stair is not a mineshaft
    for sz_ in range(4):
        zz = 2.2 + shaft_h * (0.22 + 0.19 * sz_)
        arch(cx, cy - r - 0.15, zz, 0.9, 2.2, 0.5, stone, frame=0.22, lit=True)
    # balconies ride outside, as before
    for bz in (htot * 0.42, htot * 0.62):
        cyl(r * 1.45, 0.9, (cx, cy, 2.2 + bz), stone, verts=16)
        cyl(r * 1.28, 1.6, (cx, cy, 2.2 + bz + 1.2), stone, verts=16)
    # THE STAIR: a newel column and a helix of honest steps
    cyl(0.55, shaft_h, (cx, cy, 2.2 + shaft_h / 2), stone, verts=12)
    n_steps = int(shaft_h / 0.30)
    for i in range(n_steps):
        a = i * 0.42 - math.pi / 2
        sx_ = cx + math.cos(a) * 1.45
        sy_ = cy + math.sin(a) * 1.45
        sz2 = 2.2 + i * 0.30
        st = box(1.7, 0.72, 0.13, (0, 0, 0), stone)
        st.location = (sx_, sy_, sz2)
        st.rotation_euler = (0, 0, a + math.pi / 2)
        col(sx_, sy_, sz2, 0.85, 0.85, 0.10)
    # the lantern stage: a floor you stand on, a rail, the arcade, the lamp
    cyl(r * 1.1, 0.8, (cx, cy, lz), stone, verts=16)
    col(cx, cy, lz, r * 1.1, r * 1.1, 0.4)
    cyl(r * 1.12, 1.0, (cx, cy, lz + 0.9), stone, verts=16)    # the rail ring
    for i in range(8):
        a = i / 8 * 2 * math.pi
        box(0.55, 0.55, 3.4, (cx + math.cos(a) * r * 0.88, cy + math.sin(a) * r * 0.88, lz + 1.9), stone)
    # the burning lantern: a gold-crowned lamp on a chain-post
    cyl(0.10, 1.1, (cx, cy, lz + 3.1), gold, verts=8)
    box(0.62, 0.62, 0.95, (cx, cy, lz + 2.25), glow)
    box(0.78, 0.78, 0.14, (cx, cy, lz + 2.86), gold)
    box(0.78, 0.78, 0.14, (cx, cy, lz + 1.68), gold)
    cyl(r * 1.18, 0.8, (cx, cy, lz + 3.9), stone, verts=16)
    dome(cx, cy, lz + 4.3, r * 1.0, r * 2.1, ribs=12, drum=False)


# ================================================================ THE CENTRE
# Seven storeys, each its own idea. Footprint 46 x 34 at the plinth.
S1_H, S2_H, S3_H, S4_H, S5_H, S6_H = 11.0, 8.0, 7.0, 6.0, 7.0, 6.0
z1, z2, z3, z4, z5, z6 = 0.0, 11.0, 19.0, 26.0, 32.0, 39.0
z7 = z6 + S6_H                                     # 45: the crown begins

# S1 - THE GATE, and behind it THE HALL. Not a solid block: a floor, four
# walls, a beamed ceiling, two rows of columns, and hanging lanterns - the
# door is OPEN and the light that spills out is the hall's own.
box(48, 36, 2.0, (0, 0, 1.0), stone, bevel=0.2)                     # plinth skirt
box(46, 34, 0.6, (0, 0, 2.05), stone)                                # the hall floor
WT = 1.7
box(46, WT, S1_H - 2.3, (0, 17 - WT / 2, 2.3 + (S1_H - 2.3) / 2), stone)          # back
for sxw in (-1, 1):
    box(WT, 34, S1_H - 2.3, (sxw * (23 - WT / 2), 0, 2.3 + (S1_H - 2.3) / 2), stone)
    col(sxw * (23 - WT / 2), 0, S1_H / 2, WT / 2, 17, S1_H / 2)
col(0, 17 - WT / 2, S1_H / 2, 23, WT / 2, S1_H / 2)
# front wall in two piers either side of the doorway
for sxw in (-1, 1):
    box(20.4, WT, S1_H - 2.3, (sxw * (2.8 + 10.2), -17 + WT / 2, 2.3 + (S1_H - 2.3) / 2), stone)
    col(sxw * 13.0, -17 + WT / 2, S1_H / 2, 10.2, WT / 2, S1_H / 2)
box(5.6, WT, S1_H - 2.3 - 9.2, (0, -17 + WT / 2, 2.3 + 9.2 + (S1_H - 2.3 - 9.2) / 2), stone)  # lintel band
box(46, 34, 0.9, (0, 0, z1 + S1_H - 0.45), stone)                    # the ceiling slab
for bx in range(-3, 4):
    box(1.1, 30.5, 0.9, (bx * 6.2, 0, z1 + S1_H - 1.25), wood)       # ceiling beams
# two rows of columns holding the hall, each with a little arch ring at top
for sxc in (-1, 1):
    for cyc in (-10.5, -3.5, 3.5, 10.5):
        cyl(1.05, S1_H - 3.4, (sxc * 8.5, cyc, 2.3 + (S1_H - 3.4) / 2), stone, verts=14)
        cyl(1.35, 0.7, (sxc * 8.5, cyc, S1_H - 1.35), stone, verts=14)
        col(sxc * 8.5, cyc, S1_H / 2, 1.1, 1.1, S1_H / 2)
# hanging lanterns down the nave: gold crowns over burning cores
for lyc in (-11, -4.5, 2, 8.5):
    cyl(0.09, 2.6, (0, lyc, z1 + S1_H - 2.6), gold, verts=8)
    box(0.85, 0.85, 1.15, (0, lyc, z1 + S1_H - 4.35), glow)
    box(1.05, 1.05, 0.18, (0, lyc, z1 + S1_H - 3.68), gold)
    box(1.05, 1.05, 0.18, (0, lyc, z1 + S1_H - 5.02), gold)
# a long carpet of light-catching wood down the middle (aniconic, plain)
box(5.4, 26, 0.14, (0, -1, 2.42), wood)
cornice(23, 17, z1 + S1_H, stone)
# the iwan: a hollow tower of a portal - two flanks and a brow, a passage through
for sxw in (-1, 1):
    box(4.6, 4.2, 17.5, (sxw * 5.2, -17.5, 8.75), stone, bevel=0.25)
    col(sxw * 5.2, -17.5, 8.75, 2.3, 2.1, 8.75)
box(15, 4.2, 17.5 - 10.4, (0, -17.5, 10.4 + (17.5 - 10.4) / 2), stone, bevel=0.25)
arch(0, -20.9, 0.6, 9.0, 14.5, 2.8, stone, frame=1.5, lit=None)
# stepped muqarnas-like rings inside the portal head
for i, (mw, mh) in enumerate(((7.6, 13.4), (6.4, 12.4), (5.2, 11.4))):
    arch(0, -21.6 + 0.5 * i, 0.6, mw, mh, 0.6, stone, frame=0.58, lit=None)
arch(0, -19.9, 0.6, 5.6, 9.2, 0.7, stone, frame=0.5, lit=None)    # the OPEN door
# blind arcade left and right of the gate
arch_row(-21, -9, -17.2, 1.6, 3, 2.6, 6.5, 1.0, stone, lit=True)
arch_row(9, 21, -17.2, 1.6, 3, 2.6, 6.5, 1.0, stone, lit=True)
# the sides and the back carry their own arches
for sx in (-1, 1):
    for i in range(4):
        cy1 = -12 + 24 * (i + 0.5) / 4
        arch(sx * 23.25, cy1, 1.6, 2.6, 6.5, 1.0, stone, lit=True, face=(sx, 0))
arch_row(-14, 14, 17.25, 1.6, 5, 2.6, 6.5, 1.0, stone, lit=True, face=(0, 1))   # back

# S2 - THE ARCADE. An open gallery all round: light through every arch.
box(42, 30, S2_H, (0, 0, z2 + S2_H / 2), stone, bevel=0.2)
arch_row(-19, 19, -15.35, z2 + 0.8, 7, 3.4, 6.2, 1.2, stone, lit=True)
arch_row(-19, 19, 15.35, z2 + 0.8, 7, 3.4, 6.2, 1.2, stone, lit=True, face=(0, 1))
for sx in (-1, 1):
    for i in range(5):
        cy2 = -12 + 24 * (i + 0.5) / 5
        arch(sx * 21.35, cy2, z2 + 0.8, 3.2, 6.0, 1.2, stone, lit=True, face=(sx, 0))
cornice(21, 15, z2 + S2_H, stone)
col(0, 0, z2 + S2_H / 2, 21, 15, S2_H / 2)

# S3 - THE MASHRABIYA. Projecting timber screen bays on a stone body.
box(38, 27, S3_H, (0, 0, z3 + S3_H / 2), stone, bevel=0.2)
# oriel bays: a timber body carrying a PAIR of pointed lit windows each -
# the plain bright squares read as televisions, his word was "not fitting"
for sx in (-1, 1):
    for cy3 in (-8, 0, 8):
        box(2.2, 6.0, 5.6, (sx * 19.6, cy3, z3 + 3.3), wood, bevel=0.12)
        for wy in (-1.4, 1.4):
            arch(sx * 20.75, cy3 + wy, z3 + 1.1, 1.5, 3.9, 0.5, wood,
                 frame=0.3, lit=True, face=(sx, 0))
for cx3 in (-14.4, 0, 14.4):
    box(6.0, 2.2, 5.6, (cx3, -14.1, z3 + 3.3), wood, bevel=0.12)
    for wx in (-1.5, 1.5):
        arch(cx3 + wx, -15.25, z3 + 1.1, 1.5, 3.9, 0.5, wood,
             frame=0.3, lit=True, face=(0, -1))
cornice(19, 13.5, z3 + S3_H, stone)
col(0, 0, z3 + S3_H / 2, 19, 13.5, S3_H / 2)

# S4 - THE BAND. Paired lancets and the corner turrets' birth.
box(34, 24, S4_H, (0, 0, z4 + S4_H / 2), stone, bevel=0.2)
arch_row(-14, 14, -12.35, z4 + 0.8, 8, 1.9, 4.4, 1.0, stone, lit=True)
arch_row(-14, 14, 12.35, z4 + 0.8, 8, 1.9, 4.4, 1.0, stone, lit=True, face=(0, 1))
for sx in (-1, 1):
    for i in range(4):
        cy4 = -9 + 18 * (i + 0.5) / 4
        arch(sx * 17.35, cy4, z4 + 0.8, 1.9, 4.4, 1.0, stone, lit=True, face=(sx, 0))
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl(2.0, S4_H + S5_H + 2, (sx * 16, sy * 11, z4 + (S4_H + S5_H) / 2), stone, verts=12)
        cyl(2.3, 0.8, (sx * 16, sy * 11, z4 + S4_H + S5_H + 2.2), stone, verts=12)
        dome(sx * 16, sy * 11, z4 + S4_H + S5_H + 2.5, 2.15, 4.1, ribs=10, drum=False)
cornice(17, 12, z4 + S4_H, stone)
col(0, 0, z4 + S4_H / 2, 17, 12, S4_H / 2)

# S5 - THE OCTAGON. The square turns; niches on every face; corner domes.
me5 = bpy.data.meshes.new("oct"); ob5 = bpy.data.objects.new("oct", me5)
bpy.context.collection.objects.link(ob5)
bm5 = bmesh.new()
r5o, r5i = 15.0, 15.0 * 0.92
ring_a = [bm5.verts.new((math.cos((i + 0.5) / 8 * 2 * math.pi) * r5o,
                         math.sin((i + 0.5) / 8 * 2 * math.pi) * r5o * 0.78, z5)) for i in range(8)]
ring_b = [bm5.verts.new((math.cos((i + 0.5) / 8 * 2 * math.pi) * r5i,
                         math.sin((i + 0.5) / 8 * 2 * math.pi) * r5i * 0.78, z5 + S5_H)) for i in range(8)]
for i in range(8):
    j = (i + 1) % 8
    bm5.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))
bm5.faces.new(tuple(reversed(ring_a)))
bm5.faces.new(ring_b)
bm5.normal_update(); bm5.to_mesh(me5); bm5.free()
stone.append(ob5)
for i in range(8):
    a5 = (i + 0.5) / 8 * 2 * math.pi
    fx, fy = math.cos(a5), math.sin(a5)
    px, py = fx * r5o * 0.96, fy * r5o * 0.78 * 0.96
    arch(px, py, z5 + 0.9, 2.6, 4.6, 0.9, stone, frame=0.42, lit=True, face=(fx, fy))
col(0, 0, z5 + S5_H / 2, 14, 11, S5_H / 2)

# S6 - THE DRUM GALLERY. A round arcaded drum, glowing all round its ring.
cyl(12.5, S6_H, (0, 0, z6 + S6_H / 2), stone, verts=48)
for i in range(12):
    a6 = i / 12 * 2 * math.pi
    fx, fy = math.cos(a6), math.sin(a6)
    arch(fx * 12.7, fy * 12.7, z6 + 0.9, 2.1, 4.2, 0.9, stone, frame=0.4, lit=True, face=(fx, fy))
cyl(13.4, 0.9, (0, 0, z6 + S6_H + 0.2), gold, verts=48)     # the gold lip
col(0, 0, z6 + S6_H / 2, 12.5, 12.5, S6_H / 2)

# S7 - THE CROWN. The great gold onion and its court of four.
dome(0, 0, z7, 11.0, 21.0, ribs=20)
for sx in (-1, 1):
    for sy in (-1, 1):
        dome(sx * 8.5, sy * 8.5, z7 - 1.2, 2.6, 4.8, ribs=10)

# ============================================================ THE COMPOUND
# His order: a fort entire. The dome-crowned block becomes the CURTAIN
# MODULE, repeated on all four faces with no gaps; corner towers a head
# taller; six minarets attached by arched connector walls; and inside, a
# court with riwaq arcades on the haram pattern, garden beds, a fountain.

def module(cx, cy, face, gate=False):
    """One curtain block: three stepped storeys, arcades, dome and two gold
    eggs on the parapet. face = outward unit (0,-1)/(0,1)/(1,0)/(-1,0)."""
    ox, oy = face
    ax, ay = -oy, ox                    # along the wall
    w_hx, w_hy = 15.0, 13.0             # half along, half out
    W1, W2, W3 = 8.5, 7.0, 6.0

    def P(a, o):                        # local (along, out) -> world
        return (cx + a * ax + o * ox, cy + a * ay + o * oy)

    def sized(a_len, o_len):            # box sizes for this orientation
        return (abs(a_len * ax) + abs(o_len * ox), abs(a_len * ay) + abs(o_len * oy))

    for (hw, hd, zz, hh) in ((w_hx, w_hy, 0, W1), (w_hx - 1, w_hy - 1, W1, W2),
                             (w_hx - 2, w_hy - 2, W1 + W2, W3)):
        sx_, sy_ = sized(hw * 2, hd * 2)
        box(sx_, sy_, hh, (cx, cy, zz + hh / 2), stone, bevel=0.2)
    sx_, sy_ = sized(w_hx * 2 + 1.4, w_hy * 2 + 1.4)
    box(sx_, sy_, 1.6, (cx, cy, 0.8), stone, bevel=0.2)
    col(cx, cy, (W1 + W2 + W3) / 2, sized(w_hx * 2, w_hy * 2)[0] / 2,
        sized(w_hx * 2, w_hy * 2)[1] / 2, (W1 + W2 + W3) / 2)

    if gate:
        gx, gy = P(0, w_hy + 0.6)
        sx_, sy_ = sized(7.5, 3.4)
        box(sx_, sy_, 10.5, (gx, gy, 5.25), stone, bevel=0.2)
        agx, agy = P(0, w_hy + 2.45)
        arch(agx, agy, 0.5, 4.6, 8.2, 2.2, stone, frame=0.65, lit=True, face=face)
        for sa in (-1, 1):
            for i in range(2):
                aa = sa * (6 + i * 4.2)
                axp, ayp = P(aa, w_hy + 0.35)
                arch(axp, ayp, 1.4, 2.2, 5.2, 1.0, stone, lit=True, face=face)
    else:
        for i in range(4):
            aa = -11.2 + 22.4 * (i + 0.5) / 4
            axp, ayp = P(aa, w_hy + 0.35)
            arch(axp, ayp, 1.4, 2.4, 5.6, 1.0, stone, lit=True, face=face)
    for i in range(5):
        aa = -12 + 24 * (i + 0.5) / 5
        axp, ayp = P(aa, w_hy - 1 + 0.35)
        arch(axp, ayp, W1 + 0.8, 2.4, 4.6, 1.0, stone, lit=True, face=face)
    for i in range(4):
        aa = -10 + 20 * (i + 0.5) / 4
        axp, ayp = P(aa, w_hy - 2 + 0.35)
        arch(axp, ayp, W1 + W2 + 0.8, 2.2, 4.0, 1.0, stone, lit=True, face=face)
    parapet(cx, cy, sized(w_hx - 2.3, w_hy - 2.3)[0], sized(w_hx - 2.3, w_hy - 2.3)[1],
            W1 + W2 + W3, stone)
    dome(cx, cy, W1 + W2 + W3, 5.2, 9.5, ribs=14, seg=36)
    for sa in (-1, 1):
        ex, ey = P(sa * 9.5, 0)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(ex, ey, W1 + W2 + W3 + 1.7),
                                             segments=16, ring_count=10)
        ob_e = bpy.context.active_object
        ob_e.scale = (1.0, 1.0, 1.35)
        bpy.ops.object.transform_apply(scale=True)
        bpy.ops.object.shade_smooth()
        gold.append(ob_e)


def corner_tower(cx, cy):
    """A head taller than the curtain: octagonal, arcaded crown, dome."""
    H = 30.0
    cyl(10.2, 2.0, (cx, cy, 1.0), stone, verts=8)
    cyl(9.0, H, (cx, cy, 2.0 + H / 2), stone, verts=8)
    for i in range(8):
        a8 = (i + 0.5) / 8 * 2 * math.pi
        fx8, fy8 = math.cos(a8), math.sin(a8)
        arch(cx + fx8 * 9.1, cy + fy8 * 9.1, H - 6.5, 2.2, 4.6, 0.9, stone,
             frame=0.4, lit=True, face=(fx8, fy8))
    cyl(9.9, 1.2, (cx, cy, 2.0 + H + 0.4), stone, verts=8)
    parapet(cx, cy, 7.4, 7.4, 2.0 + H + 1.0, stone, hh=1.1)
    dome(cx, cy, 2.0 + H + 1.0, 6.0, 11.0, ribs=14, seg=40)
    col(cx, cy, 1.0 + H / 2, 9.4, 9.4, H / 2 + 1)


def connector(x0, y0, x1, y1, h=7.5):
    """The arched wall that ties a minaret to the curtain: solid above,
    one open arch below, so it reads bound, not butted."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    yaw = math.atan2(dy, dx)
    b = box(ln + 1.5, 1.6, h * 0.45, (0, 0, 0), stone)
    b.location = (mx, my, h * 0.55 + h * 0.225)
    b.rotation_euler = (0, 0, yaw)
    fx9, fy9 = -dy / ln, dx / ln
    arch(mx, my, 0.4, min(3.2, ln * 0.55 + 1.2), h * 0.62, 1.6, stone, frame=0.5,
         lit=None, face=(fx9, fy9))
    col(mx, my, h * 0.5, abs(dx) / 2 + 0.8, abs(dy) / 2 + 0.8, h * 0.5)


# ---- the four faces (the front keeps the great centre block standing proud)
for sxm in (-1, 1):
    for i in range(3):
        module(sxm * (38 + 30 * i), 0, (0, -1), gate=(i == 0))
for i in range(4):                                   # the flanks
    for sxm in (-1, 1):
        module(sxm * 100, 30 + 30 * i, (sxm, 0))
for i in range(5):                                   # the back
    module(-60 + 30 * i, 120, (0, 1), gate=(i == 2))

for sxm in (-1, 1):                                  # the corner towers
    corner_tower(sxm * 109, -19)
    corner_tower(sxm * 109, 129)

# ---- six minarets, every one tied in by its arched wall
for sxm in (-1, 1):
    minaret(sxm * 23, -24, 58.0)                     # the front pair, at the seams
    minaret(sxm * 120, 75, 52.0)                     # the flank pair
    connector(sxm * 113, 75, sxm * 118, 75)
    minaret(sxm * 23, 140, 52.0)                     # the back pair
    connector(sxm * 23, 133, sxm * 23, 138)

# ============================================================ THE COURT
# Bounded by the curtains: x +-87, y 17..107. The riwaq runs round it on
# the haram pattern: a colonnade of pointed arches under a flat roof.
RW_D = 5.5                                           # riwaq depth

def riwaq_run(x0, y0, x1, y1, face):
    """A straight riwaq: columns and open arches on the court side, a roof
    slab back to the curtain, a little parapet over."""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    fx0, fy0 = face
    n = max(2, int(ln / 5.2))
    for i in range(n + 1):
        px = x0 + ux * (ln * i / n)
        py = y0 + uy * (ln * i / n)
        cyl(0.55, 6.4, (px, py, 3.2), stone, verts=10)
        col(px, py, 3.2, 0.6, 0.6, 3.2)
    for i in range(n):
        px = x0 + ux * (ln * (i + 0.5) / n)
        py = y0 + uy * (ln * (i + 0.5) / n)
        arch(px, py, 0.0, ln / n - 0.9, 6.4, 0.8, stone, frame=0.42, lit=None, face=face)
    bx3, by3 = (x0 + x1) / 2 - fx0 * RW_D / 2, (y0 + y1) / 2 - fy0 * RW_D / 2
    sx3 = abs(dx) + (RW_D if fx0 else 1.6)
    sy3 = abs(dy) + (RW_D if fy0 else 1.6)
    box(max(sx3, RW_D), max(sy3, RW_D), 0.8, (bx3, by3, 7.0), stone)
    box(max(sx3, RW_D) + 0.6, max(sy3, RW_D) + 0.6, 0.9,
        (bx3, by3, 7.75), stone, bevel=0.1)

riwaq_run(-81, 24.5, 81, 24.5, (0, 1))               # along the front curtain
riwaq_run(-81, 99.5, 81, 99.5, (0, -1))              # along the back curtain
riwaq_run(-80.5, 25, -80.5, 99, (1, 0))              # west
riwaq_run(80.5, 25, 80.5, 99, (-1, 0))               # east

# the garden: four kerbed beds of earth round the fountain court
for sxg in (-1, 1):
    for syg in (-1, 1):
        bx2, by2 = sxg * 40, 62 + syg * 22
        box(46, 15, 1.0, (bx2, by2, 2.55), stone, bevel=0.1)
        box(43.5, 12.5, 1.05, (bx2, by2, 2.62), earth)
        col(bx2, by2, 0.5, 23, 7.5, 0.55)

# THE FOUNTAIN: an octagonal double basin with a lit heart of water
cyl(7.0, 1.4, (0, 62, 2.7), stone, verts=8)
cyl(6.1, 1.5, (0, 62, 2.85), water, verts=8)
cyl(1.1, 2.6, (0, 62, 4.3), stone, verts=10)
cyl(3.4, 0.9, (0, 62, 5.8), stone, verts=8)
cyl(2.8, 1.0, (0, 62, 5.95), water, verts=8)
cyl(0.5, 1.6, (0, 62, 6.9), stone, verts=10)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, location=(0, 62, 7.9), segments=16, ring_count=10)
gold.append(bpy.context.active_object)
col(0, 62, 1.75, 7.2, 7.2, 1.75)

# ============================================================ MATERIALS
def finish(objs, name, base, rough, metal, tex=None, tint=None, emis=None, estr=0.5, uv=3.0):
    if not objs:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    if tex:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=uv)
        bpy.ops.object.mode_set(mode='OBJECT')
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b2 = m.node_tree.nodes["Principled BSDF"]
    b2.inputs["Base Color"].default_value = base
    b2.inputs["Roughness"].default_value = rough
    b2.inputs["Metallic"].default_value = metal
    if emis:
        try:
            b2.inputs["Emission Color"].default_value = emis
        except KeyError:
            b2.inputs["Emission"].default_value = emis
        b2.inputs["Emission Strength"].default_value = estr
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = m.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
            if tint:
                mix = m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0; mix.inputs['Color2'].default_value = tint
                m.node_tree.links.new(tn.outputs['Color'], mix.inputs['Color1'])
                m.node_tree.links.new(mix.outputs['Color'], b2.inputs['Base Color'])
            else:
                m.node_tree.links.new(tn.outputs['Color'], b2.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


tops = []
for coll, nm in ((stone, "stone"), (gold, "gold"), (wood, "wood"), (glow, "glow")):
    for o in coll:
        try:
            zs = [(o.matrix_world @ __import__("mathutils").Vector(c)).z for c in o.bound_box]
            tops.append((max(zs), nm, o.name))
        except Exception:
            pass
tops.sort(reverse=True)
for t in tops[:3]:
    print("TOP %.1f %s %s" % t)

parts = []
parts.append(finish(stone, "stone", (0.86, 0.82, 0.74, 1), 0.72, 0.0,
                    tex="t_ashlar_d.jpg", tint=(1.42, 1.34, 1.18, 1), uv=6.0))
parts.append(finish(gold, "gold", (1.0, 0.78, 0.28, 1), 0.20, 0.85,
                    emis=(0.62, 0.44, 0.13, 1), estr=0.75))
parts.append(finish(wood, "wood", (0.52, 0.38, 0.24, 1), 0.85, 0.0,
                    tex="t_door_d.jpg", uv=1.4))
# the lit windows: the lived palace showing through every arch
parts.append(finish(glow, "glow", (1.0, 0.76, 0.38, 1), 0.9, 0.0,
                    emis=(1.0, 0.62, 0.22, 1), estr=3.0))
parts.append(finish(earth, "earth", (0.30, 0.22, 0.15, 1), 1.0, 0.0))
parts.append(finish(water, "water", (0.35, 0.55, 0.75, 1), 0.15, 0.0,
                    emis=(0.30, 0.48, 0.62, 1), estr=0.5))
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "qasr"

QSCALE = 1.4
ob.scale = (QSCALE, QSCALE, QSCALE)
bpy.ops.object.transform_apply(scale=True)
for c in COLS:
    c["c"] = [round(v * QSCALE, 2) for v in c["c"]]
    c["h"] = [round(v * QSCALE, 2) for v in c["h"]]

me = ob.data
me.calc_loop_triangles()
print("RESULT qasr verts=%d tris=%d" % (len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)

import json
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLS}, f)
print("WROTE", OUT)
