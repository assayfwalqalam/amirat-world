# Builds an Aserai-style mud-brick house in Blender and exports .glb + .col.json
#   blender --background --python make_house.py -- <seed> <out.glb> [assets_dir]
#
# Two rules learned the hard way, do not reorder them:
#   1. Cut each solid while it is still a clean box. Joining first shreds it.
#   2. Erode before cutting. Eroding afterwards tears the wall around openings.
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

def use_vertex_colour(nt, bsdf, tex_node=None, name="ao"):
    """Wire the baked occlusion into Base Color.

    Blender only writes a vertex colour layer into the .glb if the material
    actually reads it. Baking alone is silently dropped on export, which
    leaves every surface flat -- so the layer is multiplied over the texture
    here. glTF stores it as COLOR_0 and the renderer multiplies it back.
    """
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = name
    vc.location = (-700, -140)
    if tex_node is None:
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        return
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    mix.location = (-380, 200)
    nt.links.new(tex_node.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(vc.outputs['Color'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

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
W = random.uniform(7.5, 10.0)
D = random.uniform(6.5, 8.5)
H1 = random.uniform(3.6, 4.4)
H2 = random.uniform(2.9, 3.6)
T = 0.45                                   # wall thickness
has_upper = random.random() < 0.78
uw = W * random.uniform(0.62, 0.86)
ud = D * random.uniform(0.66, 0.9)
ox = random.uniform(-1, 1) * (W - uw) * 0.32
oy = random.uniform(-1, 1) * (D - ud) * 0.32

dw, dh = 1.35, 2.45
dx = random.uniform(-W * 0.18, W * 0.18)

shell = []
timber = []


def window(target, cx, cy, cz, w, h, axis, through):
    if axis == 'y':
        cut(target, solid(w, through, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2), False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2), rot=(math.pi / 2, 0, 0)))
    else:
        cut(target, solid(through, w, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2), False))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2), rot=(0, math.pi / 2, 0)))


def weather(*_args, **_kw):
    """Retired: boolean cracks read as scratched glitches, never as age."""
    return

def patch(cx, cy, cz, w, h, face, depth=0.09):
    """A slab of newer render, laid over an old wall in a rough rectangle."""
    if face == 'y':
        o = solid(w, depth, h, (cx, cy, cz), False)
    else:
        o = solid(depth, w, h, (cx, cy, cz), False)
    o.rotation_euler[1] = random.uniform(-0.05, 0.05)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(rotation=True)
    erode(o, levels=1, fine=0.02, broad=0.03)
    return o


def storey(cx, cy, w, d, z0, h, front_door, n_win):
    """Four wall slabs, so the inside is a real room you can walk into."""
    back = solid(w, T, h, (cx, cy + d / 2 - T / 2, z0 + h / 2))
    left = solid(T, d - T * 2, h, (cx - w / 2 + T / 2, cy, z0 + h / 2))
    right = solid(T, d - T * 2, h, (cx + w / 2 - T / 2, cy, z0 + h / 2))
    # The front wall carries the doorway, so it must NOT be recorded as one
    # solid slab: the opening would be cut from the geometry while collision
    # still sealed it, and the house could be seen into but never entered.
    # It is recorded below as the pier either side plus the lintel over.
    front = solid(w, T, h, (cx, cy - d / 2 + T / 2, z0 + h / 2), collide=not front_door)
    for wl in (back, left, right, front):
        erode(wl, levels=2)
    fy = cy - d / 2 + T / 2
    if front_door:
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
    for i in range(n_win):
        wx = cx + random.uniform(-w * 0.34, w * 0.34)
        if front_door and abs(wx - dx) < 1.5:
            wx += 2.2 * (1 if wx >= dx else -1)
        window(front, wx, fy, z0 + h * random.uniform(0.52, 0.7), 0.74, 1.2, 'y', T + 1.2)
    if random.random() < 0.7:
        wy = cy + random.uniform(-(d - T * 2) * 0.3, (d - T * 2) * 0.3)
        pick_left = random.random() < 0.5
        side = left if pick_left else right
        sx = (cx - w / 2 + T / 2) if pick_left else (cx + w / 2 - T / 2)
        window(side, sx, wy, z0 + h * random.uniform(0.5, 0.68), 0.7, 1.1, 'x', T + 1.2)
    if random.random() < 0.5:
        bx = cx + random.uniform(-w * 0.3, w * 0.3)
        window(back, bx, cy + d / 2 - T / 2, z0 + h * random.uniform(0.52, 0.7), 0.7, 1.1, 'y', T + 1.2)
    weather(front, cx, cy - d / 2 + T / 2, w, d, h, z0, 'y')
    weather(back, cx, cy + d / 2 - T / 2, w, d, h, z0, 'y')
    weather(left, cx - w / 2 + T / 2, cy, w, d, h, z0, 'x')
    weather(right, cx + w / 2 - T / 2, cy, w, d, h, z0, 'x')
    out = []
    for wl in (back, left, right, front):
        weld(wl)
        out.append(wl)
    # a patch or two of newer render, stuck on over the old. NEVER over the
    # doorway: a house-coloured slab across the door was exactly the owner's
    # "the doors do not show" - the door was there, plastered over.
    for i in range(random.randint(1, 3)):
        if random.random() < 0.5:
            pw = random.uniform(1.2, 2.8)
            ph2 = random.uniform(0.9, 2.0)
            px = cx + random.uniform(-w * 0.32, w * 0.32)
            pz = z0 + random.uniform(h * 0.2, h * 0.66)
            if front_door:
                clear = dw / 2 + pw / 2 + 0.35
                if abs(px - dx) < clear and pz - ph2 / 2 < z0 + dh + 0.3:
                    px = dx + clear * (1 if px >= dx else -1)
                    px = max(cx - w / 2 + pw / 2 + 0.3, min(cx + w / 2 - pw / 2 - 0.3, px))
                    if abs(px - dx) < dw / 2 + pw / 2 + 0.2:
                        pz = z0 + dh + 0.5 + ph2 / 2
            out.append(patch(px, cy - d / 2 + T / 2 - 0.04, pz, pw, ph2, 'y'))
        else:
            sgn = 1 if random.random() < 0.5 else -1
            out.append(patch(cx + sgn * (w / 2 - T / 2 + 0.04),
                             cy + random.uniform(-d * 0.3, d * 0.3),
                             z0 + random.uniform(h * 0.2, h * 0.66),
                             random.uniform(1.0, 2.4), random.uniform(0.8, 1.8), 'x'))
    return out


# ground floor, with its room
shell += storey(0, 0, W, D, 0, H1, True, random.randint(1, 2))
SPOTS.append({"c": [0, 0.3, 0], "r": [round(W / 2 - 1.2, 2), round(D / 2 - 1.2, 2)], "k": "room"})
floor = solid(W - T * 2, D - T * 2, 0.3, (0, 0, 0.15))
erode(floor, levels=1, fine=0.02, broad=0.03)
shell.append(floor)

# the roof slab over the ground floor, which is also the terrace
roof1 = solid(W, D, 0.42, (0, 0, H1 + 0.21))
erode(roof1, levels=1, fine=0.02, broad=0.035)
shell.append(roof1)

top_z = H1 + 0.42
if has_upper:
    shell += storey(ox, oy, uw, ud, top_z, H2, False, random.randint(1, 2))
    roof2 = solid(uw, ud, 0.4, (ox, oy, top_z + H2 + 0.2))
    erode(roof2, levels=1, fine=0.02, broad=0.03)
    shell.append(roof2)


def parapet(cx, cy, w, d, z, h, t, rail=True):
    """A raised roof edge. Solid, so standing on it lifts you.
       Above it goes a timber rail, the way a terrace is fenced."""
    out = []
    out.append(solid(w + t * 2, t, h, (cx, cy + d / 2 + t / 2, z + h / 2)))
    out.append(solid(w + t * 2, t, h, (cx, cy - d / 2 - t / 2, z + h / 2)))
    out.append(solid(t, d, h, (cx + w / 2 + t / 2, cy, z + h / 2)))
    out.append(solid(t, d, h, (cx - w / 2 - t / 2, cy, z + h / 2)))
    for o in out:
        erode(o, levels=1, fine=0.02, broad=0.03)
    if False:                 # railings retired on his ruling
        for sy in (-1, 1):
            n = max(4, int(w / 0.62))
            for i in range(n):
                if random.random() < 0.12:
                    continue          # a post missing, as they are
                bx = cx - w / 2 + (i + 0.5) * (w / n)
                timber.append(solid(0.07, 0.07, 0.62, (bx, cy + sy * (d / 2 + t / 2), z + h + 0.31), False))
            timber.append(solid(w + t * 2, 0.09, 0.09, (cx, cy + sy * (d / 2 + t / 2), z + h + 0.63), False))
        for sx in (-1, 1):
            n2 = max(3, int(d / 0.62))
            for i in range(n2):
                bz = cy - d / 2 + (i + 0.5) * (d / n2)
                timber.append(solid(0.07, 0.07, 0.62, (cx + sx * (w / 2 + t / 2), bz, z + h + 0.31), False))
            timber.append(solid(0.09, d, 0.09, (cx + sx * (w / 2 + t / 2), cy, z + h + 0.63), False))
    # the terrace itself is somewhere props may stand
    SPOTS.append({"c": [round(cx, 2), round(z, 2), round(-cy, 2)],
                  "r": [round(w / 2 - 0.7, 2), round(d / 2 - 0.7, 2)], "k": "roof"})
    return out


shell += parapet(0, 0, W - 0.34, D - 0.34, top_z, 0.85, 0.34)
if has_upper:
    shell += parapet(ox, oy, uw - 0.32, ud - 0.32, top_z + H2 + 0.4, 0.85, 0.32)

# --------------------------------------------------- the outside stair
stair_side = 1 if random.random() < 0.5 else -1
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
body = solid(1.35, flight_len, top_z + 0.42,
             (SX, y0 + (flight_len - run) / 2, (top_z + 0.42) / 2), False)
ang = math.atan2(rise, run)
cutter = solid(3.0, flight_len * 2.2, 8.0,
               (SX, y0 + (flight_len - run) / 2, 0), False)
cutter.rotation_euler[0] = ang
bpy.context.view_layer.objects.active = cutter
bpy.ops.object.transform_apply(rotation=True)
ymid = y0 + (flight_len - run) / 2
cutter.location = (SX, ymid,
                   rise * ((ymid - y0) / run + 1.0) + 4.0 / math.cos(ang) + 0.02)
cut(body, cutter)
shell.append(body)
for i in range(steps):
    h = rise * (i + 1)
    shell.append(solid(1.35, run * 1.03, 0.14, (SX, y0 + i * run, h - 0.07), False))
    COLLIDERS.append({"c": [round(SX, 3), round(h / 2, 3), round(-(y0 + i * run), 3)],
                      "h": [0.675, round(h / 2, 3), round(run / 2, 3)]})
# the cheek wall that carries the flight, closing its open side
timber.append(solid(0.22, steps * run, 0.55,
                    (SX + stair_side * 0.72, -D / 2 + 0.9 + (steps - 1) * run / 2, 0.3), False))

# --------------------------------------------------------------- timber
def beams(cx, cy, w, d, z, n):
    out = []
    for i in range(n):
        bx = cx - w / 2 + (i + 0.5) * (w / n)
        for sy in (-1, 1):
            out.append(cyl(random.uniform(0.055, 0.078), 0.5,
                           (bx, cy + sy * (d / 2 + 0.12), z + random.uniform(-0.03, 0.03)),
                           rot=(math.pi / 2, 0, 0), verts=7))
    return out


timber += beams(0, 0, W * 0.84, D, H1 - 0.3, max(3, int(W / 1.2)))
if has_upper:
    timber += beams(ox, oy, uw * 0.8, ud, top_z + H2 - 0.3, max(3, int(uw / 1.2)))

# a plank door standing in the doorway, and its lintel
timber.append(solid(dw - 0.08, 0.1, dh - 0.55, (dx, -D / 2 + T / 2 - 0.02, (dh - 0.55) / 2), False))
timber.append(solid(dw + 0.6, 0.34, 0.18, (dx, -D / 2 + 0.04, dh + 0.14), False))

# shutters standing in some of the windows
for i in range(random.randint(1, 3)):
    sx2 = random.uniform(-W * 0.34, W * 0.34)
    sz2 = H1 * random.uniform(0.52, 0.7)
    timber.append(solid(0.36, 0.07, 1.0, (sx2, -D / 2 + 0.2, sz2), False))

# balcony over the door
if random.random() < 0.85:
    BW = random.uniform(3.6, 4.6)
    BD = 1.75
    by = -D / 2 - BD / 2 + 0.15
    bz = top_z + 0.1
    shell.append(solid(BW, BD, 0.18, (dx, by, bz)))
    # a rail all the way round the open sides
    n = max(6, int(BW / 0.4))
    for i in range(n):
        timber.append(solid(0.075, 0.075, 0.72, (dx - BW / 2 + (i + 0.5) * (BW / n), by - BD / 2, bz + 0.45), False))
    timber.append(solid(BW, 0.11, 0.11, (dx, by - BD / 2, bz + 0.84), False))
    for sx in (-1, 1):
        for i in range(3):
            timber.append(solid(0.075, 0.075, 0.72, (dx + sx * BW / 2, by - BD / 2 + (i + 0.5) * (BD / 3), bz + 0.45), False))
        timber.append(solid(0.11, BD, 0.11, (dx + sx * BW / 2, by, bz + 0.84), False))
        timber.append(cyl(0.06, 1.15, (dx + sx * (BW / 2 - 0.25), by + 0.1, bz - 0.5),
                          rot=(math.radians(54), 0, 0), verts=6))
    SPOTS.append({"c": [round(dx, 2), round(bz + 0.09, 2), round(-by, 2)],
                  "r": [round(BW / 2 - 0.5, 2), round(BD / 2 - 0.35, 2)], "k": "balcony"})

# ------------------------------------------------------------- assemble
for o in shell:
    bevel(o, 0.026, 2, 35)
for o in timber:
    bevel(o, 0.012, 1, 40)

house = join(shell + timber)
house.name = "house"
weld(house, 0.0004)

# ------------------------------------------------- texture and occlusion
bpy.context.view_layer.objects.active = house
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=2.6)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new("adobe")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1.0
house.data.materials.clear()
house.data.materials.append(mat)

# about two buildings in five wear the banded pakhsa wall
_w = (SEED * 2654435761) % 100
# all six walls he approved: plain 24, banded 24, light 12, dark 14, darkdom 12, mix 14
if _w < 18:   tex_name = "t_ashlar_d.jpg"   # the mosque's stone, his pick
elif _w < 24: tex_name = "t_adobe_d.jpg"
elif _w < 48: tex_name = "t_adobe2_d.jpg"
elif _w < 60: tex_name = "t_adobe3_d.jpg"
elif _w < 74: tex_name = "t_adobe4_d.jpg"
elif _w < 86: tex_name = "t_adobe5_d.jpg"
else:         tex_name = "t_adobe6_d.jpg"
tex_path = os.path.abspath(os.path.join(ASSETS, tex_name))
if not os.path.exists(tex_path):
    tex_path = os.path.abspath(os.path.join(ASSETS, "t_adobe_d.jpg"))
img_tex = None
if os.path.exists(tex_path):
    img_tex = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img_tex
    tn.location = (-700, 300)
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
else:
    print("no adobe texture at", tex_path)
    bsdf.inputs["Base Color"].default_value = (0.82, 0.69, 0.50, 1)

nor_path = os.path.abspath(os.path.join(ASSETS, "t_adobe_gn.jpg"))
if os.path.exists(nor_path) and img_tex is not None:
    nimg = bpy.data.images.load(nor_path)
    nimg.colorspace_settings.name = 'Non-Color'
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nimg
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = 0.85
    nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    nimg.pack()

if img_tex:
    img_tex.pack()

me = house.data
me.calc_loop_triangles()
print("RESULT verts=%d tris=%d colliders=%d" % (len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

bpy.ops.object.select_all(action='DESELECT')
house.select_set(True)
try:
    # 'ACTIVE' writes the baked occlusion layer regardless of the node tree.
    # The default only exports it if the exporter can trace it to Base Color,
    # which silently loses the bake and leaves everything flat.
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)

with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
