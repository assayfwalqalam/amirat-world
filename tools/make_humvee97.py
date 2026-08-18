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
    o = box(sx, sy, sz, loc, into)
    o.rotation_euler[axis] = tilt
    bpy.ops.object.transform_apply(rotation=True)
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


# ---------------------------------------------------------------- the tub
# One low wide slab, floor to belt line; the wheel arches cut out of it.
belt = 1.32                                     # belt line height
tub = box(W, L * 0.94, belt - BODY_FLOOR, (0, 0.05, BODY_FLOOR + (belt - BODY_FLOOR) / 2), BODY)
ax_f = WHEELBASE / 2 + 0.05                     # front axle y (forward = +y)
ax_r = -WHEELBASE / 2 + 0.05
for ay in (ax_f, ax_r):
    for sx in (-1, 1):
        cut(tub, 1.2, TYRE_R * 2 + 0.30, TYRE_R + 0.32, (sx * W / 2, ay, BODY_FLOOR + 0.12))
bevel(tub, 0.025)

# the rocker line: a darker skirt under the doors
box(W - 0.06, 1.9, 0.10, (0, 0.15, BODY_FLOOR + 0.05), BLACK)

# ---------------------------------------------------------------- the hood
# long, wide, nearly flat, with the raised centre plane and louvres
hood_y0 = 0.95                                   # windshield base (the cowl)
nose_y = L / 2 + 0.05
hood_len = (nose_y - 0.06) - hood_y0
hood_mid = (hood_y0 + nose_y - 0.06) / 2
bevel(wedge(W - 0.10, hood_len, 0.15, (0, hood_mid, belt - 0.055), BODY, 0.035, axis=0), 0.03)
wedge(W * 0.44, hood_len * 0.66, 0.07, (0, hood_mid - 0.10, belt + 0.045), BODY, 0.035, axis=0)
for i in range(7):                               # the louvre strip
    box(0.30, 0.035, 0.028, (0.28, hood_y0 + 0.98 + i * 0.075, belt + 0.125), BLACK)
# hood tie-down loop
cyl(0.035, 0.16, (0, hood_y0 + 0.30, belt + 0.13), BLACK, rot=(math.pi / 2, 0, 0), verts=10)

# ------------------------------------------------------------- the face
# grille recess with seven vertical slats
box(0.78, 0.10, 0.42, (0, nose_y - 0.03, 1.02), BLACK)
for i in range(7):
    box(0.055, 0.12, 0.40, (-0.33 + i * 0.11, nose_y - 0.02, 1.02), BODY)
# round headlamps either side
for sx in (-1, 1):
    cyl(0.115, 0.06, (sx * 0.62, nose_y, 1.05), LAMP, rot=(math.pi / 2, 0, 0), verts=18)
    cyl(0.135, 0.05, (sx * 0.62, nose_y - 0.02, 1.05), BLACK, rot=(math.pi / 2, 0, 0), verts=18)
    # amber blinkers above-outboard
    cyl(0.075, 0.05, (sx * 0.86, nose_y - 0.055, 1.21), AMBER, rot=(math.pi / 2, 0, 0), verts=12)
# the face plate the lamps sit in
face = box(W - 0.14, 0.09, 0.52, (0, nose_y - 0.06, 1.04), BODY)
cut(face, 0.80, 0.3, 0.44, (0, nose_y - 0.03, 1.02))
# bumper: heavy channel + shackles + winch drum
box(W + 0.04, 0.17, 0.22, (0, nose_y + 0.09, 0.55), BODY)
for sx in (-1, 1):
    cyl(0.055, 0.16, (sx * 0.55, nose_y + 0.16, 0.74), BLACK, rot=(math.pi / 2, 0, 0), verts=10)
cyl(0.09, 0.5, (0, nose_y + 0.02, 0.72), BLACK, rot=(0, math.pi / 2, 0), verts=12)

# ---------------------------------------------------------- the glasshouse
ws_base = belt + 0.02
ws_h = 0.46
# windshield: two flat panes in a black frame, raked slightly
frame = wedge(W - 0.26, 0.06, ws_h, (0, hood_y0, ws_base + ws_h / 2 - 0.02), BLACK, -0.14, axis=0)
glass = wedge(W - 0.40, 0.03, ws_h - 0.10, (0, hood_y0 - 0.012, ws_base + ws_h / 2 - 0.03), GLASS, -0.14, axis=0)
box(0.05, 0.06, ws_h - 0.06, (0, hood_y0 - 0.02, ws_base + ws_h / 2 - 0.02), BLACK)   # centre mullion
# roof: flat slab from windshield header to the slantback
roof_y1 = -0.55
box(W - 0.22, (hood_y0 - 0.10) - roof_y1, 0.07,
    (0, ((hood_y0 - 0.10) + roof_y1) / 2, ws_base + ws_h - 0.005), BODY)
# the slantback: sloped rear plane down to the tail
sb = wedge(W - 0.24, 1.38, 0.07, (0, roof_y1 - 0.62, ws_base + ws_h - 0.30), BODY, 0.46, axis=0)
wedge(W - 0.44, 0.9, 0.035, (0, roof_y1 - 0.42, ws_base + ws_h - 0.19), GLASS, 0.46, axis=0)
# rear quarter panels flush to the slope
for sx in (-1, 1):
    wedge(0.09, 1.34, 0.62, (sx * (W / 2 - 0.135), roof_y1 - 0.62, belt + 0.26), BODY, 0.0, axis=0)
# tailgate
box(W - 0.20, 0.07, 0.55, (0, -L / 2 + 0.10, BODY_FLOOR + 0.42), BODY)

# ------------------------------------------------------------- the doors
# four framed doors with inset dark glass; visible panel lines by standing
# each door 12 mm proud of the tub
door_w = 0.05
for sx in (-1, 1):
    for (dy0, dy1, glass_w) in ((0.92, 0.02, 0.62), (0.02, -0.85, 0.60)):
        mid = (dy0 + dy1) / 2
        dl = abs(dy0 - dy1)
        box(door_w, dl - 0.05, belt - BODY_FLOOR - 0.06,
            (sx * (W / 2 + 0.006), mid, BODY_FLOOR + (belt - BODY_FLOOR) / 2), BODY)
        # window frame above the belt
        box(door_w, dl - 0.10, 0.42, (sx * (W / 2 - 0.02), mid, belt + 0.21), BLACK)
        box(0.02, glass_w, 0.32, (sx * (W / 2 - 0.02), mid, belt + 0.20), GLASS)
        # hinges and handle
        for hz in (0.75, 1.05):
            box(0.022, 0.08, 0.045, (sx * (W / 2 + 0.028), dy0 - 0.06, hz), BLACK)
        box(0.022, 0.14, 0.038, (sx * (W / 2 + 0.028), dy1 + 0.16, 1.02), BLACK)
# mirrors on door-frame arms
for sx in (-1, 1):
    cyl(0.02, 0.34, (sx * (W / 2 + 0.17), 0.86, belt + 0.34), BLACK, rot=(0, math.pi / 2, 0), verts=8)
    box(0.03, 0.16, 0.22, (sx * (W / 2 + 0.34), 0.86, belt + 0.34), BLACK)

# ------------------------------------------------------- flares and wheels
for ay in (ax_f, ax_r):
    for sx in (-1, 1):
        # trapezoid flare: a real eyebrow of body-work, thick and proud
        box(0.17, TYRE_R * 2 + 0.36, 0.13, (sx * (W / 2 + 0.045), ay, TYRE_R + 0.47), BODY)
        wedge(0.17, 0.55, 0.12, (sx * (W / 2 + 0.04), ay + TYRE_R + 0.36, TYRE_R + 0.27), BODY, -0.55, axis=0)
        wedge(0.17, 0.55, 0.12, (sx * (W / 2 + 0.04), ay - TYRE_R - 0.36, TYRE_R + 0.27), BODY, 0.55, axis=0)
        # the wheel: tyre, chevron tread, rim dish, twelve bolts, hub
        wx = sx * (TRACK / 2 + 0.10)
        cyl(TYRE_R, TYRE_W, (wx, ay, TYRE_R), TYRE, rot=(0, math.pi / 2, 0), verts=28)
        for tb in range(28):
            a = tb / 28 * 2 * math.pi
            box(TYRE_W + 0.015, 0.055, 0.05,
                (wx, ay + math.cos(a) * (TYRE_R - 0.008), TYRE_R + math.sin(a) * (TYRE_R - 0.008)),
                TYRE, yaw=0)
        cyl(TYRE_R * 0.58, 0.06, (wx + sx * (TYRE_W / 2 - 0.02), ay, TYRE_R), RIM,
            rot=(0, math.pi / 2, 0), verts=20)
        for bb in range(12):
            a2 = bb / 12 * 2 * math.pi
            cyl(0.022, 0.05, (wx + sx * (TYRE_W / 2 + 0.005),
                              ay + math.cos(a2) * TYRE_R * 0.34,
                              TYRE_R + math.sin(a2) * TYRE_R * 0.34), BLACK,
                rot=(0, math.pi / 2, 0), verts=8)
        cyl(0.09, 0.10, (wx + sx * (TYRE_W / 2 + 0.02), ay, TYRE_R), BLACK,
            rot=(0, math.pi / 2, 0), verts=12)

# side vents behind the front arch (the little gill strip)
for sx in (-1, 1):
    for i in range(4):
        box(0.02, 0.05, 0.16, (sx * (W / 2 + 0.01), ax_f - TYRE_R - 0.42 - i * 0.09, 1.06), BLACK)

# the turret ring on the roof
cyl(0.42, 0.10, (0, 0.05, ws_base + ws_h + 0.08), BODY, verts=22)
cut(BODY[-1], 0.62, 0.62, 0.3, (0, 0.05, ws_base + ws_h + 0.10))

# ------------------------------------------------------------- collision
COLLIDERS.append({"c": [0, (BODY_FLOOR + belt) / 2, -0.05], "h": [W / 2, (belt - BODY_FLOOR) / 2 + 0.1, L / 2 * 0.94]})
COLLIDERS.append({"c": [0, ws_base + 0.25, 0.2], "h": [W / 2 - 0.15, 0.35, 1.05]})

# ------------------------------------------------------------- materials
def finish(objs, name, base, rough, metal, emis=None):
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
    return ob


parts = [
    finish(BODY, "body", (0.352, 0.337, 0.271, 1), 0.74, 0.12),     # sand-olive paint
    finish(GLASS, "glass", (0.06, 0.08, 0.10, 1), 0.10, 0.55),
    finish(BLACK, "black", (0.045, 0.045, 0.048, 1), 0.82, 0.10),
    finish(TYRE, "tyre", (0.052, 0.052, 0.055, 1), 0.96, 0.0),
    finish(RIM, "rim", (0.16, 0.155, 0.14, 1), 0.55, 0.5),
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
