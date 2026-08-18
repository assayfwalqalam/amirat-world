# The rest of the wheeled fleet to the 97 rule, one run: the Land Rover Wolf
# (r_landrover_2: raised bonnet over flat wings, horizontal-slat grille
# between caged lamps, near-vertical two-pane screen, canvas rear over hoops,
# eyebrow arches, green steel rims), the technical (Hilux bed + DShK pintle),
# and two burnt wrecks derived from the same bodies. Saves .blends.
#   blender --background --python make_fleet97.py -- <models_dir> [assets]
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MDIR = argv[0] if argv else "assets/models/veh"
ASSETS = argv[1] if len(argv) > 1 else "assets"

BLEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blend")
os.makedirs(BLEND_DIR, exist_ok=True)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(sx, sy, sz, loc, into, yaw=0.0, tiltx=0.0):
    # THE PIVOT LAW: applying a rotation to a box that already stands at its
    # place swings it about the WORLD ORIGIN in this operator flow, not about
    # itself. Build at the origin, turn it, then move it.
    if tiltx or yaw:
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
        o = bpy.context.active_object
        o.scale = (sx / 2, sy / 2, sz / 2)
        bpy.ops.object.transform_apply(scale=True)
        o.rotation_euler = (tiltx, 0, yaw)
        bpy.ops.object.transform_apply(rotation=True)
        o.location = loc
        bpy.ops.object.transform_apply(location=True)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
        o = bpy.context.active_object
        o.scale = (sx / 2, sy / 2, sz / 2)
        bpy.ops.object.transform_apply(scale=True)
    into.append(o)
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


def bevel(o, w=0.02, ang=40):
    m = o.modifiers.new("bv", 'BEVEL')
    m.width = w
    m.segments = 2
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(ang)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
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
        b2.inputs["Emission Strength"].default_value = 0.35
    ob.data.materials.clear()
    ob.data.materials.append(m)
    surface(m, tex, uv, ob)
    return ob


def export(parts, name, colliders, blend, slump=None):
    parts = [p for p in parts if p]
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    if slump:
        ob.rotation_euler = slump
        bpy.ops.object.transform_apply(rotation=True)
    me = ob.data
    me.calc_loop_triangles()
    print("RESULT %s verts=%d tris=%d" % (name, len(me.vertices), len(me.loop_triangles)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND_DIR, blend))
    out = os.path.join(MDIR, name + ".glb")
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
    with open(os.path.splitext(out)[0] + ".col.json", "w") as f:
        json.dump({"boxes": colliders}, f)
    print("WROTE", out)


# =========================================================== the Land Rover
def wheel_lr(GRN, TYRE, BLACK, wx, ay, r=0.375, w=0.21, sx=1):
    cyl(r, w, (wx, ay, r), TYRE, rot=(0, math.pi / 2, 0), verts=40)
    for tb in range(22):
        a = tb / 22 * 2 * math.pi
        box(w + 0.012, 0.045, 0.04,
            (wx, ay + math.cos(a) * (r - 0.006), r + math.sin(a) * (r - 0.006)), TYRE)
    cyl(r * 0.55, 0.05, (wx + sx * (w / 2 - 0.015), ay, r), GRN, rot=(0, math.pi / 2, 0), verts=28)
    for bb in range(5):
        a2 = bb / 5 * 2 * math.pi
        cyl(0.02, 0.045, (wx + sx * (w / 2 + 0.005), ay + math.cos(a2) * r * 0.30,
                          r + math.sin(a2) * r * 0.30), BLACK, rot=(0, math.pi / 2, 0), verts=8)
    cyl(0.065, 0.09, (wx + sx * (w / 2 + 0.012), ay, r), BLACK, rot=(0, math.pi / 2, 0), verts=10)


def build_landrover(burnt=False):
    fresh()
    GRN, CANVAS, BLACK, GLASS, TYRE, LAMP, AMBER = [], [], [], [], [], [], []
    COL = []
    L, W, H = 4.60, 1.79, 2.03
    WB, TR = 2.79, 1.49
    R = 0.375
    floor = 0.48
    belt = 1.24
    nose = L / 2
    # chassis rails and bumper bar on frame horns
    for sx in (-1, 1):
        box(0.09, L * 0.94, 0.12, (sx * 0.42, 0, 0.42), BLACK)
    box(W + 0.14, 0.13, 0.14, (0, nose + 0.10, 0.52), BLACK)
    # tub: narrow slab sides, cab + rear body
    tub = box(W, L * 0.90, belt - floor, (0, -0.06, floor + (belt - floor) / 2), GRN)
    ax_f, ax_r = WB / 2 + 0.28, -WB / 2 + 0.28
    for ay in (ax_f, ax_r):
        for sx in (-1, 1):
            cut(tub, 0.9, R * 2 + 0.22, R + 0.25, (sx * W / 2, ay, floor + 0.05))
    bevel(tub, 0.018)
    # the flat WINGS with lamp panels, and the raised bonnet between them
    wing_top = belt + 0.02
    for sx in (-1, 1):
        box(0.44, 1.05, 0.05, (sx * (W / 2 - 0.22), nose - 0.55, wing_top), GRN)
    bon = box(0.86, 1.06, 0.17, (0, nose - 0.56, wing_top + 0.065), GRN)
    bevel(bon, 0.025)
    # the face: grille of horizontal slats between headlamps in the wings
    box(0.86, 0.06, 0.40, (0, nose - 0.035, belt - 0.16), BLACK)
    for i in range(6):
        box(0.80, 0.07, 0.030, (0, nose - 0.03, belt - 0.335 + i * 0.062), GRN)
    for sx in (-1, 1):
        cyl(0.095, 0.05, (sx * (W / 2 - 0.22), nose - 0.01, belt - 0.12), LAMP,
            rot=(math.pi / 2, 0, 0), verts=16)
        cyl(0.05, 0.04, (sx * (W / 2 - 0.22), nose - 0.01, belt - 0.30), AMBER,
            rot=(math.pi / 2, 0, 0), verts=10)
        # the wire lamp cage
        for gy in (-0.10, 0.0, 0.10):
            box(0.26, 0.015, 0.015, (sx * (W / 2 - 0.22), nose + 0.05, belt - 0.12 + gy), BLACK)
        for gx in (-0.10, 0.0, 0.10):
            box(0.015, 0.015, 0.30, (sx * (W / 2 - 0.22) + gx, nose + 0.05, belt - 0.12), BLACK)
    # near-vertical two-pane screen AT THE COWL; a wreck keeps the frame
    # and mullion but the glass is gone
    ws0 = 1.13
    # the frame is a RING, not a slab: a full black panel behind the glass
    # made the screen read as a blank wall, which is what it did
    if not burnt:
        box(W - 0.26, 0.03, 0.58, (0, ws0 - 0.01, belt + 0.335), GLASS, tiltx=0.10)
    for sxw in (-1, 1):
        box(0.055, 0.05, 0.64, (sxw * (W / 2 - 0.10), ws0, belt + 0.335), BLACK, tiltx=0.10)
    box(W - 0.18, 0.06, 0.055, (0, ws0 - 0.032, belt + 0.035), BLACK, tiltx=0.10)
    box(W - 0.18, 0.06, 0.06, (0, ws0 + 0.030, belt + 0.635), BLACK, tiltx=0.10)
    box(0.035, 0.05, 0.58, (0, ws0 - 0.02, belt + 0.335), BLACK, tiltx=0.10)
    for sxw in (-1, 1):        # wipers on the screen
        cyl(0.010, 0.34, (sxw * 0.30, ws0 - 0.05, belt + 0.09), BLACK, rot=(0, math.pi / 2, 0.30), verts=6)
    # hard doors under the screen, sliding glass in canvas above
    for sx in (-1, 1):
        box(0.04, 0.92, belt - floor - 0.04, (sx * (W / 2 + 0.005), 0.55, floor + (belt - floor) / 2), GRN)
        box(0.04, 0.86, 0.42, (sx * (W / 2 - 0.01), 0.55, belt + 0.21), BLACK)
        box(0.018, 0.70, 0.32, (sx * (W / 2 - 0.01), 0.55, belt + 0.20), GLASS)
        box(0.02, 0.10, 0.035, (sx * (W / 2 + 0.025), 0.14, 1.02), BLACK)
        # mirror on the screen side
        cyl(0.016, 0.24, (sx * (W / 2 + 0.12), 1.08, belt + 0.30), BLACK, rot=(0, math.pi / 2, 0), verts=8)
        box(0.025, 0.12, 0.17, (sx * (W / 2 + 0.24), 1.08, belt + 0.30), BLACK)
    if burnt:
        # the canvas burned away: bare hoops over an open tray
        for i in range(4):
            hy = 0.62 - i * 0.80
            box(0.05, 0.05, 0.62, (-(W / 2 - 0.10), hy, belt + 0.31), BLACK)
            box(0.05, 0.05, 0.62, ((W / 2 - 0.10), hy, belt + 0.31), BLACK)
            box(W - 0.14, 0.05, 0.05, (0, hy, belt + 0.62), BLACK)
    else:
        # the canvas: a roof running header to tail, its SIDES cut away over
        # the doors - the Wolf's glass shows under the canvas, not behind it
        roofc = box(W - 0.10, 3.30, 0.12, (0, -0.62, belt + 0.72), CANVAS)
        bevel(roofc, 0.05, ang=20)
        for sxc in (-1, 1):
            sw = box(0.06, 2.30, 0.62, (sxc * (W / 2 - 0.06), -1.20, belt + 0.35), CANVAS)
            bevel(sw, 0.03, ang=25)
            box(0.02, 0.5, 0.3, (sxc * (W / 2 - 0.045), -0.85, belt + 0.34), BLACK)
        back = box(W - 0.10, 0.06, 0.62, (0, -2.32, belt + 0.35), CANVAS)
        bevel(back, 0.03, ang=25)
        for i in range(4):
            box(W - 0.06, 0.05, 0.05, (0, 0.62 - i * 0.80, belt + 0.80), CANVAS)
    # eyebrow arches
    for ay in (ax_f, ax_r):
        for sx in (-1, 1):
            box(0.06, R * 2 + 0.24, 0.05, (sx * (W / 2 + 0.02), ay, R + 0.33), BLACK)
    # wheels - a wreck has lost its front-left and sits on the hub
    for ay in (ax_f, ax_r):
        for sx in (-1, 1):
            if burnt and ay == ax_f and sx == -1:
                cyl(0.09, 0.14, (-(TR / 2 + 0.14), ay, 0.16), BLACK, rot=(0, math.pi / 2, 0), verts=10)
                continue
            wheel_lr(GRN, TYRE, BLACK, sx * (TR / 2 + 0.14), ay, sx=sx)
    COL.append({"c": [0, (floor + belt) / 2, 0.06], "h": [W / 2, (belt - floor) / 2 + 0.1, L / 2 * 0.9]})
    COL.append({"c": [0, belt + 0.35, 1.05], "h": [W / 2 - 0.1, 0.42, 1.15]})
    if burnt:
        parts = [
            finish(GRN + CANVAS, "burnt", (0.055, 0.05, 0.045, 1), 0.95, 0.05),
            finish(BLACK + TYRE, "char", (0.03, 0.03, 0.03, 1), 0.98, 0.0),
            finish(LAMP + AMBER, "dead", (0.10, 0.09, 0.08, 1), 0.9, 0.1),
            finish(GLASS, "gone", (0.02, 0.02, 0.02, 1), 0.98, 0.0),
        ]
        export(parts, "wreck_truck", COL, "wreck_truck.blend", slump=(0.035, 0.06, 0.02))
    else:
        parts = [
            finish(GRN, "green", (0.208, 0.24, 0.166, 1), 0.72, 0.15, tex="t_paintolive.jpg", uv=1.5),
            finish(CANVAS, "canvas", (0.34, 0.33, 0.26, 1), 0.95, 0.0, tex="t_canvas.jpg", uv=1.1),
            finish(BLACK, "black", (0.045, 0.045, 0.048, 1), 0.85, 0.08, tex="t_gunsteel.jpg", uv=0.5),
            finish(GLASS, "glass", (0.06, 0.08, 0.10, 1), 0.10, 0.55),
            finish(TYRE, "tyre", (0.052, 0.052, 0.055, 1), 0.96, 0.0, tex="t_rubber.jpg", uv=0.35),
            finish(LAMP, "lamp", (0.75, 0.78, 0.80, 1), 0.25, 0.4),
            finish(AMBER, "amber", (0.85, 0.48, 0.10, 1), 0.35, 0.2, emis=(0.5, 0.25, 0.04, 1)),
        ]
        export(parts, "landrover", COL, "landrover.blend")


# ============================================================ the technical
def build_technical(burnt=False):
    fresh()
    PAINT, BLACK, GLASS, TYRE, RIM, GUN, LAMP = [], [], [], [], [], [], []
    COL = []
    L, W = 5.33, 1.80
    WB, TR = 3.08, 1.55
    R = 0.36
    floor = 0.42
    belt = 1.05
    cab_r = 1.62                       # cab roof height
    nose = L / 2
    tub = box(W, L * 0.92, belt - floor, (0, 0, floor + (belt - floor) / 2), PAINT)
    ax_f, ax_r = WB / 2 + 0.35, -WB / 2 + 0.35
    for ay in (ax_f, ax_r):
        for sx in (-1, 1):
            cut(tub, 0.9, R * 2 + 0.20, R + 0.22, (sx * W / 2, ay, floor + 0.04))
    bevel(tub, 0.02)
    # bonnet sloping to a lower nose; grille + lamps
    bon = box(W - 0.16, 1.15, 0.14, (0, nose - 0.62, belt + 0.02), PAINT, tiltx=0.055)
    bevel(bon, 0.03)
    box(W - 0.30, 0.05, 0.26, (0, nose - 0.02, belt - 0.14), BLACK)
    for i in range(3):
        box(W - 0.38, 0.06, 0.03, (0, nose - 0.015, belt - 0.22 + i * 0.075), PAINT)
    for sx in (-1, 1):
        box(0.26, 0.05, 0.13, (sx * (W / 2 - 0.24), nose - 0.02, belt - 0.10), LAMP if not burnt else BLACK)
    box(W + 0.06, 0.14, 0.16, (0, nose + 0.06, 0.55), BLACK)
    # THE CAB, built as a cab: A-pillars carrying a raked screen, B-pillar
    # wall with its rear screen, a roof that RESTS on them, doors under.
    cab_f, cab_b = 0.95, -0.28
    scr_h = cab_r - belt - 0.02
    box(W - 0.20, 0.05, scr_h + 0.06, (0, cab_f - 0.10, belt + scr_h / 2), BLACK, tiltx=-0.30)
    box(W - 0.34, 0.025, scr_h - 0.06, (0, cab_f - 0.115, belt + scr_h / 2 - 0.01), GLASS, tiltx=-0.30)
    for sx in (-1, 1):
        box(0.06, 0.06, scr_h + 0.04, (sx * (W / 2 - 0.10), cab_f - 0.10, belt + scr_h / 2), PAINT, tiltx=-0.30)
        box(0.07, 0.07, scr_h, (sx * (W / 2 - 0.06), cab_b + 0.03, belt + scr_h / 2), PAINT)
    box(W - 0.20, 0.06, scr_h, (0, cab_b, belt + scr_h / 2), PAINT)
    box(W - 0.40, 0.025, scr_h - 0.16, (0, cab_b - 0.032, belt + scr_h / 2), GLASS)
    box(W - 0.16, cab_f - cab_b + 0.14, 0.06, (0, (cab_f + cab_b) / 2 - 0.04, cab_r + 0.03), PAINT)
    for sx in (-1, 1):
        box(0.045, 1.05, belt - floor - 0.05, (sx * (W / 2 + 0.004), (cab_f + cab_b) / 2 - 0.05, floor + (belt - floor) / 2), PAINT)
        box(0.04, 0.95, scr_h - 0.08, (sx * (W / 2 - 0.01), (cab_f + cab_b) / 2 - 0.05, belt + scr_h / 2 - 0.02), BLACK)
        box(0.018, 0.80, scr_h - 0.18, (sx * (W / 2 - 0.01), (cab_f + cab_b) / 2 - 0.05, belt + scr_h / 2 - 0.03), GLASS)
        cyl(0.015, 0.18, (sx * (W / 2 + 0.09), cab_f - 0.16, belt + 0.34), BLACK, rot=(0, math.pi / 2, 0), verts=8)
        box(0.024, 0.10, 0.14, (sx * (W / 2 + 0.18), cab_f - 0.16, belt + 0.34), BLACK)
    # the bed: low walls from the cab back, tailgate
    for sx in (-1, 1):
        box(0.05, 2.0, 0.34, (sx * (W / 2 - 0.03), -1.40, belt + 0.17), PAINT)
    box(W - 0.06, 0.05, 0.34, (0, -2.38, belt + 0.17), PAINT)
    box(W - 0.16, 1.95, 0.05, (0, -1.40, belt + 0.02), BLACK)
    # the DShK on a pintle tripod in the bed
    if not burnt:
        cyl(0.05, 0.75, (0, -1.35, belt + 0.42), GUN, verts=10)
        for a3 in range(3):
            aa = a3 / 3 * 2 * math.pi + 0.5
            cyl(0.03, 0.62, (0 + math.cos(aa) * 0.22, -1.35 + math.sin(aa) * 0.22, belt + 0.28), GUN,
                rot=(0.6 * math.cos(aa + 1.57), 0.6 * math.sin(aa + 1.57), 0), verts=8)
        cyl(0.045, 1.15, (0, -0.78, belt + 0.86), GUN, rot=(math.pi / 2 - 0.12, 0, 0), verts=12)
        cyl(0.065, 0.42, (0, -1.18, belt + 0.80), GUN, rot=(math.pi / 2 - 0.12, 0, 0), verts=12)
        box(0.22, 0.30, 0.16, (0, -1.32, belt + 0.74), GUN)
        cyl(0.085, 0.16, (0.15, -1.32, belt + 0.76), GUN, rot=(0, math.pi / 2, 0), verts=12)
    # wheels: simple steel rims; the wreck sits on a bare rear hub
    for ay in (ax_f, ax_r):
        for sx in (-1, 1):
            if burnt and ay == ax_r and sx == -1:
                cyl(0.08, 0.13, (-(TR / 2 + 0.12), ay, 0.15), BLACK, rot=(0, math.pi / 2, 0), verts=10)
                continue
            wx = sx * (TR / 2 + 0.12)
            cyl(R, 0.22, (wx, ay, R), TYRE, rot=(0, math.pi / 2, 0), verts=40)
            for tb in range(20):
                a = tb / 20 * 2 * math.pi
                box(0.235, 0.04, 0.038, (wx, ay + math.cos(a) * (R - 0.006), R + math.sin(a) * (R - 0.006)), TYRE)
            cyl(R * 0.52, 0.05, (wx + sx * 0.10, ay, R), RIM, rot=(0, math.pi / 2, 0), verts=26)
            cyl(0.05, 0.08, (wx + sx * 0.115, ay, R), BLACK, rot=(0, math.pi / 2, 0), verts=10)
    COL.append({"c": [0, (floor + belt) / 2, 0], "h": [W / 2, (belt - floor) / 2 + 0.08, L / 2 * 0.92]})
    COL.append({"c": [0, belt + 0.30, -0.75], "h": [W / 2 - 0.1, 0.38, 0.62]})
    if burnt:
        parts = [
            finish(PAINT, "burnt", (0.06, 0.055, 0.05, 1), 0.95, 0.05),
            finish(BLACK + TYRE + GUN, "char", (0.03, 0.03, 0.03, 1), 0.98, 0.0),
            finish(RIM, "rust", (0.21, 0.11, 0.06, 1), 0.9, 0.1),
            finish(GLASS, "gone", (0.02, 0.02, 0.02, 1), 0.98, 0.0),
        ]
        export(parts, "wreck_car", COL, "wreck_car.blend", slump=(-0.03, -0.055, 0.015))
    else:
        parts = [
            finish(PAINT, "paint", (0.55, 0.52, 0.47, 1), 0.55, 0.25, tex="t_paintsand.jpg", uv=1.6),
            finish(BLACK, "black", (0.045, 0.045, 0.048, 1), 0.85, 0.08, tex="t_gunsteel.jpg", uv=0.5),
            finish(GLASS, "glass", (0.06, 0.08, 0.10, 1), 0.10, 0.55),
            finish(TYRE, "tyre", (0.052, 0.052, 0.055, 1), 0.96, 0.0, tex="t_rubber.jpg", uv=0.35),
            finish(RIM, "rim", (0.30, 0.30, 0.30, 1), 0.5, 0.5),
            finish(LAMP, "lamp", (0.75, 0.78, 0.80, 1), 0.25, 0.4),
            finish(GUN, "gun", (0.09, 0.09, 0.10, 1), 0.55, 0.6),
        ]
        export(parts, "technical", COL, "technical.blend")


build_landrover(False)
build_landrover(True)
build_technical(False)
build_technical(True)
print("FLEET DONE")
