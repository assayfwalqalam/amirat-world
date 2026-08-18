# The Humvee to the 97% rule, judged limb by limb against the photographs in
# shots/ref/r_humvee_*.jpg. Slantback armament-carrier body: the seven-slot
# grille between round lamps, the long louvred hood with its centre ridge,
# four framed doors with inset glass, trapezoid flares over 37-inch
# twelve-bolt wheels, shackle bumper, mirrors on door arms, turret ring.
# Saves a .blend beside the export so hand-edits stay cheap.
#   blender --background --python make_humvee97.py -- <out.glb> [assets]
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "humvee.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"

bpy.ops.wm.read_factory_settings(use_empty=True)

COLLIDERS = []
BODY, GLASS, BLACK, TYRE, RIM, LAMP, AMBER = [], [], [], [], [], [], []

# true HMMWV proportions, metres
L, W, H = 4.57, 2.16, 1.83
WHEELBASE, TRACK = 3.30, 1.82
TYRE_R, TYRE_W = 0.465, 0.31
BODY_FLOOR = 0.55                      # high riding


def box(sx, sy, sz, loc, into, yaw=0.0):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    o = bpy.context.active_object
    o.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if yaw:
        o.rotation_euler[2] = yaw
        bpy.ops.object.transform_apply(rotation=True)
    into.append(o)
    return o


def bevel(o, w=0.02):
    m = o.modifiers.new("bv", 'BEVEL')
    m.width = w
    m.segments = 2
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(40)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def wedge(sx, sy, sz, loc, into, tilt, axis=0):
    # THE PIVOT LAW: in this operator flow, applying a rotation to a box that
    # already stands at its place swings it about the WORLD ORIGIN, not its
    # own. Build at the origin, turn it there, and only then move it.
    o = box(sx, sy, sz, (0, 0, 0), into)
    o.rotation_euler[axis] = tilt
    bpy.ops.object.transform_apply(rotation=True)
    o.location = loc
    bpy.ops.object.transform_apply(location=True)
    return o


def cyl(r, depth, loc, into, rot=(0, 0, 0), verts=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    into.append(o)
    return o


def cut(target, sx, sy, sz, loc):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    c = bpy.context.active_object
    c.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)


# =========================================================== the body
# Measured off shots/ref/r_humvee_1.jpg: the HMMWV is very wide and low, the
# bonnet sits BELOW the door tops between two raised wings, the cab is a
# closed box with square windows, and heavy eyebrow flares stand over the
# arches with the wheels tucked under them.
BELT = 1.30                 # top of the body sides / bottom of the windows
ROOF = 1.80
FEND = 1.27                 # top of the front wings
HOOD_C = 1.15               # bonnet centre, well below the wings
HW = W / 2                  # 1.08
TUBW = 1.02                 # body side, before the flares
CABW = 1.00                 # the glasshouse sits nearly flush with the body
NOSE = L / 2                # 2.285
COWL = 0.92                 # where the windscreen stands
ROOF_R = -0.95              # back edge of the roof
TAIL = -L / 2
ax_f = WHEELBASE / 2 + 0.05
ax_r = -WHEELBASE / 2 + 0.05

# ---- the tub: floor to belt, arches cut as rounded openings
tub = box(TUBW * 2, L * 0.96, BELT - BODY_FLOOR, (0, 0.0, BODY_FLOOR + (BELT - BODY_FLOOR) / 2), BODY)
for ay in (ax_f, ax_r):
    for sx in (-1, 1):
        cut(tub, 1.2, (TYRE_R + 0.13) * 2, TYRE_R + 0.5, (sx * TUBW, ay, BODY_FLOOR + 0.10))
        for cs in (-1, 1):
            cut(tub, 1.2, 0.34, 0.34, (sx * TUBW, ay + cs * (TYRE_R + 0.02), BODY_FLOOR + 0.52))
bevel(tub, 0.022)

# the rocker: a dark skirt under the doors
box(TUBW * 2 - 0.04, 1.86, 0.11, (0, 0.05, BODY_FLOOR + 0.055), BLACK)

# ---- the front wings, and the bonnet lying between them
for sx in (-1, 1):
    wing = box(0.30, NOSE - COWL, FEND - BELT + 0.14,
               (sx * (HW - 0.09), (NOSE + COWL) / 2, BELT + (FEND - BELT) / 2 - 0.02), BODY)
    bevel(wing, 0.03)
hood_len = NOSE - COWL - 0.02
hood = wedge(0.92 * 2, hood_len, 0.10, (0, (NOSE + COWL) / 2 - 0.01, HOOD_C - 0.02), BODY, 0.075, axis=0)
bevel(hood, 0.02)
for i in range(11):                       # the louvre panel before the screen
    box(0.86, 0.028, 0.022, (0, COWL + 0.20 + i * 0.055, HOOD_C + 0.045), BLACK)
box(1.12, hood_len - 0.30, 0.05, (0, (NOSE + COWL) / 2 - 0.05, HOOD_C + 0.045), BODY)
box(0.98, 0.70, 0.02, (0, COWL + 0.50, HOOD_C + 0.062), BODY)
for sx in (-1, 1):
    cyl(0.03, 0.13, (sx * 0.42, NOSE - 0.30, HOOD_C + 0.06), BLACK, rot=(math.pi / 2, 0, 0), verts=8)

# ---- the face: grille between round lamps, ambers on the wing corners
face = box(0.92 * 2, 0.10, FEND - 0.62, (0, NOSE - 0.05, (FEND + 0.62) / 2 - 0.02), BODY)
cut(face, 0.82, 0.4, 0.36, (0, NOSE - 0.05, 1.00))
for sxl in (-1, 1):                      # the lamps sit IN the face, not behind it
    cut(face, 0.25, 0.4, 0.25, (sxl * 0.62, NOSE - 0.05, 1.00))
bevel(face, 0.02)
box(0.84, 0.07, 0.38, (0, NOSE - 0.12, 1.00), BLACK)
for i in range(7):
    box(0.062, 0.10, 0.34, (-0.33 + i * 0.11, NOSE - 0.08, 1.00), BODY)
for sx in (-1, 1):
    cyl(0.135, 0.07, (sx * 0.62, NOSE - 0.06, 1.00), BLACK, rot=(math.pi / 2, 0, 0), verts=20)
    cyl(0.112, 0.05, (sx * 0.62, NOSE - 0.03, 1.00), LAMP, rot=(math.pi / 2, 0, 0), verts=20)
    box(0.16, 0.12, 0.15, (sx * 0.92, NOSE - 0.10, 1.13), BODY)
    box(0.13, 0.05, 0.11, (sx * 0.95, NOSE - 0.05, 1.13), AMBER)
box(0.92 * 2, 0.09, 0.16, (0, NOSE - 0.05, 0.70), BODY)                  # valance
box(W + 0.06, 0.19, 0.20, (0, NOSE + 0.10, 0.66), BLACK)                 # bumper channel
box(W - 0.30, 0.10, 0.16, (0, NOSE + 0.16, 0.50), BLACK)                 # skid
for sx in (-1, 1):
    box(0.07, 0.10, 0.20, (sx * 0.52, NOSE + 0.20, 0.62), BLACK)
    cyl(0.055, 0.05, (sx * 0.52, NOSE + 0.22, 0.55), BLACK, rot=(0, math.pi / 2, 0), verts=10)

# ---- the cab: pillars, roof, windscreen
WSB, WST = BELT + 0.02, ROOF - 0.06
for sx in (-1, 1):
    wedge(0.07, 0.09, (WST - WSB) + 0.10, (sx * (CABW - 0.03), COWL - 0.15, (WSB + WST) / 2), BODY, -0.55, axis=0)
    box(0.07, 0.08, WST - WSB, (sx * (CABW - 0.03), 0.02, (WSB + WST) / 2), BODY)
    box(0.07, 0.09, WST - WSB, (sx * (CABW - 0.03), ROOF_R + 0.06, (WSB + WST) / 2), BODY)
    box(0.09, 1.84, 0.06, (sx * (CABW - 0.02), 0.0, WSB - 0.01), BODY)
roof = box(CABW * 2, (COWL - 0.30) - ROOF_R, 0.08, (0, ((COWL - 0.30) + ROOF_R) / 2, ROOF - 0.04), BODY)
bevel(roof, 0.02)
box(CABW * 2 - 0.06, 0.09, 0.09, (0, COWL - 0.32, ROOF - 0.10), BODY)
ws_mid_y = (COWL + (COWL - 0.30)) / 2
ws_mid_z = (WSB + WST) / 2
WSH = WST - WSB
wedge(CABW * 2 - 0.22, 0.05, WSH - 0.02, (0, ws_mid_y, ws_mid_z), GLASS, -0.55, axis=0)
for sxw in (-1, 1):        # the two posts
    wedge(0.08, 0.09, WSH + 0.02, (sxw * (CABW - 0.06), ws_mid_y, ws_mid_z), BODY, -0.55, axis=0)
wedge(CABW * 2 - 0.06, 0.10, 0.07, (0, ws_mid_y - 0.115, WSB + 0.01), BODY, -0.55, axis=0)   # lower rail
wedge(CABW * 2 - 0.06, 0.10, 0.07, (0, ws_mid_y + 0.115, WST - 0.01), BODY, -0.55, axis=0)   # upper rail
wedge(0.05, 0.09, WSH - 0.02, (0, ws_mid_y, ws_mid_z), BODY, -0.55, axis=0)                  # mullion
for sx in (-1, 1):
    cyl(0.012, 0.42, (sx * 0.34, COWL + 0.06, WSB - 0.02), BLACK, rot=(0, math.pi / 2, 0.35), verts=6)

# ---- the doors: panels proud of the tub, with square windows
for sx in (-1, 1):
    for (dy0, dy1) in ((0.86, 0.03), (-0.03, -0.86)):
        mid, dl = (dy0 + dy1) / 2, abs(dy0 - dy1)
        box(0.05, dl - 0.06, BELT - BODY_FLOOR - 0.10,
            (sx * (TUBW + 0.035), mid, BODY_FLOOR + (BELT - BODY_FLOOR) / 2 + 0.02), BODY)
        for eg in (dy0, dy1):            # the shut line either side of the door
            box(0.03, 0.035, BELT - BODY_FLOOR - 0.10,
                (sx * (TUBW + 0.028), eg, BODY_FLOOR + (BELT - BODY_FLOOR) / 2 + 0.02), BLACK)
        for (fz, fh) in ((WSB + 0.02, 0.05), (WST - 0.03, 0.05)):
            box(0.06, dl - 0.10, fh, (sx * (CABW - 0.02), mid, fz), BODY)
        for fy in (dy0 - 0.05, dy1 + 0.05):
            box(0.06, 0.05, WST - WSB, (sx * (CABW - 0.02), fy, (WSB + WST) / 2), BODY)
        box(0.025, dl - 0.20, (WST - WSB) - 0.11, (sx * (CABW - 0.035), mid, (WSB + WST) / 2), GLASS)
        box(0.03, 0.15, 0.035, (sx * (TUBW + 0.05), dy1 + 0.18, 1.06), BLACK)
        for hz in (0.78, 1.14):
            box(0.03, 0.07, 0.05, (sx * (TUBW + 0.05), dy0 - 0.05, hz), BLACK)
    cyl(0.018, 0.30, (sx * (CABW + 0.16), COWL - 0.04, WSB + 0.30), BLACK, rot=(0, math.pi / 2, 0), verts=8)
    box(0.035, 0.13, 0.20, (sx * (CABW + 0.31), COWL - 0.04, WSB + 0.30), BLACK)

# ---- the slantback: the roof falls away to the tail
sb_len = 1.15
SB_T = 0.30                                   # the slope, measured off the photo
sb = wedge(CABW * 2, sb_len, 0.08,
           (0, ROOF_R - (sb_len / 2) * math.cos(SB_T), ROOF - 0.04 - (sb_len / 2) * math.sin(SB_T)),
           BODY, SB_T, axis=0)
bevel(sb, 0.02)
sb_end_z = ROOF - 0.04 - sb_len * math.sin(SB_T)
for sx in (-1, 1):
    box(0.07, sb_len, (sb_end_z - BELT) + 0.24,
        (sx * (CABW - 0.02), ROOF_R - sb_len / 2, BELT + ((sb_end_z - BELT) + 0.24) / 2 - 0.04), BODY)
box(CABW * 2, 0.09, sb_end_z - BELT + 0.04,
    (0, TAIL + 0.14, BELT + (sb_end_z - BELT) / 2), BODY)
for i in range(4):
    box(0.72, 0.05, 0.03, (0, TAIL + 0.10, BELT + 0.06 + i * 0.07), BLACK)
box(W - 0.20, 0.16, 0.18, (0, TAIL - 0.06, 0.66), BLACK)

# ---- the arch flares: a smooth eyebrow, not a fan of blocks
def arch_flare(sx, ay):
    bpy.ops.mesh.primitive_torus_add(major_radius=TYRE_R + 0.15, minor_radius=0.075,
                                     major_segments=20, minor_segments=6,
                                     location=(0, 0, 0))
    o = bpy.context.active_object
    o.rotation_euler = (0, math.pi / 2, 0)
    bpy.ops.object.transform_apply(rotation=True)
    o.scale = (1.9, 1.0, 1.0)                  # flattened across the body
    bpy.ops.object.transform_apply(scale=True)
    o.location = (sx * (TUBW + 0.02), ay, BODY_FLOOR + 0.02)
    bpy.ops.object.transform_apply(location=True)
    # keep the arch, drop everything below the body line
    m = o.modifiers.new("b", 'BOOLEAN')
    bpy.ops.mesh.primitive_cube_add(size=2, location=(sx * (TUBW + 0.02), ay, BODY_FLOOR - 0.60))
    c = bpy.context.active_object
    c.scale = (0.5, TYRE_R + 0.5, 0.62)
    bpy.ops.object.transform_apply(scale=True)
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)
    BODY.append(o)


for ay in (ax_f, ax_r):
    for sx in (-1, 1):
        arch_flare(sx, ay)
        wx = sx * (TRACK / 2 + 0.09)
        cyl(TYRE_R, TYRE_W, (wx, ay, TYRE_R), TYRE, rot=(0, math.pi / 2, 0), verts=44)
        for tb in range(30):
            a = tb / 30 * 2 * math.pi
            box(TYRE_W + 0.012, 0.06, 0.045,
                (wx, ay + math.cos(a) * (TYRE_R - 0.006), TYRE_R + math.sin(a) * (TYRE_R - 0.006)), TYRE)
        cyl(TYRE_R * 0.58, 0.06, (wx + sx * (TYRE_W / 2 - 0.02), ay, TYRE_R), RIM,
            rot=(0, math.pi / 2, 0), verts=30)
        for bb in range(12):
            a2 = bb / 12 * 2 * math.pi
            cyl(0.022, 0.05, (wx + sx * (TYRE_W / 2 + 0.005),
                              ay + math.cos(a2) * TYRE_R * 0.34,
                              TYRE_R + math.sin(a2) * TYRE_R * 0.34), BLACK,
                rot=(0, math.pi / 2, 0), verts=8)
        cyl(0.085, 0.10, (wx + sx * (TYRE_W / 2 + 0.02), ay, TYRE_R), BLACK,
            rot=(0, math.pi / 2, 0), verts=12)

for sx in (-1, 1):
    for i in range(4):
        box(0.02, 0.05, 0.15, (sx * (TUBW + 0.03), ax_f - TYRE_R - 0.40 - i * 0.09, 1.05), BLACK)

ring = cyl(0.40, 0.035, (0, 0.02, ROOF + 0.005), BODY, verts=24)
cut(ring, 0.60, 0.60, 0.2, (0, 0.02, ROOF + 0.02))

belt = BELT
ws_base, ws_h = WSB, WST - WSB

# ------------------------------------------------------------- collision
COLLIDERS.append({"c": [0, (BODY_FLOOR + belt) / 2, -0.05], "h": [W / 2, (belt - BODY_FLOOR) / 2 + 0.1, L / 2 * 0.94]})
COLLIDERS.append({"c": [0, ws_base + 0.25, 0.2], "h": [W / 2 - 0.15, 0.35, 1.05]})

# ------------------------------------------------------------- materials
# ---------------------------------------------------------------- surfaces
# A flat colour is why these read as toys beside the photographs. Each family
# of parts gets a photographed-looking sheet instead: chalky desert paint,
# olive drab, tyre rubber, parkerised steel, gun furniture, canvas. The sheet
# goes STRAIGHT into Base Color - a colour multiplied over it in the node tree
# is dropped by the glTF exporter every time - so the tone is baked in.
_TEXCACHE = {}


def surface(mat, tex_file, uv_scale, ob=None):
    if not tex_file:
        return mat
    path = os.path.abspath(os.path.join(ASSETS, tex_file))
    if not os.path.exists(path):
        print("no war texture at", path)
        return mat
    # never hold an Image across a scene reset: the datablock is freed and the
    # python handle throws "StructRNA of type Image has been removed"
    img = bpy.data.images.get(os.path.basename(path))
    if img is None:
        img = bpy.data.images.load(path)
        img.pack()
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    tn.location = (-620, 240)
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    if ob is not None:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=uv_scale)
        bpy.ops.object.mode_set(mode='OBJECT')
    return mat


def finish(objs, name, base, rough, metal, emis=None, tex=None, uv=1.0):
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
        b2.inputs["Emission Strength"].default_value = 0.4
    ob.data.materials.clear()
    ob.data.materials.append(m)
    surface(m, tex, uv, ob)
    return ob


parts = [
    finish(BODY, "body", (0.352, 0.337, 0.271, 1), 0.74, 0.12, tex="t_paintsand.jpg", uv=1.7),     # sand-olive paint
    finish(GLASS, "glass", (0.36, 0.43, 0.52, 1), 0.05, 0.0, emis=(0.10, 0.14, 0.19, 1)),
    finish(BLACK, "black", (0.045, 0.045, 0.048, 1), 0.82, 0.10, tex="t_gunsteel.jpg", uv=0.5),
    finish(TYRE, "tyre", (0.052, 0.052, 0.055, 1), 0.96, 0.0, tex="t_rubber.jpg", uv=0.35),
    finish(RIM, "rim", (0.16, 0.155, 0.14, 1), 0.55, 0.5, tex="t_gunsteel.jpg", uv=0.3),
    finish(LAMP, "lamp", (0.75, 0.78, 0.80, 1), 0.25, 0.4),
    finish(AMBER, "amber", (0.85, 0.48, 0.10, 1), 0.35, 0.2, emis=(0.6, 0.3, 0.05, 1)),
]
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "humvee"

me = ob.data
me.calc_loop_triangles()
print("RESULT humvee verts=%d tris=%d" % (len(me.vertices), len(me.loop_triangles)))

blend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blend")
os.makedirs(blend_dir, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blend_dir, "humvee.blend"))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
