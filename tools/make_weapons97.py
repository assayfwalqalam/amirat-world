# The weapons to the 97 rule, one run, judged against shots/ref/r_ak_6 (the
# clean AKM profile), r_rpg_2, r_mortar_1, r_dshk_1. True metres, muzzle +y.
# Saves .blends beside the exports.
#   blender --background --python make_weapons97.py -- <models_dir> [assets]
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MDIR = argv[0] if argv else "assets/models/war"
ASSETS = argv[1] if len(argv) > 1 else "assets"
BLEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blend")
os.makedirs(BLEND_DIR, exist_ok=True)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(sx, sy, sz, loc, into, rx=0.0, ry=0.0, rz=0.0):
    # created at the ORIGIN, rotated there, then moved: applying a rotation
    # to a part standing at its place pivoted it about the world origin and
    # threw the magazine into the sky
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    o = bpy.context.active_object
    o.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if rx or ry or rz:
        o.rotation_euler = (rx, ry, rz)
        bpy.ops.object.transform_apply(rotation=True)
    o.location = loc
    bpy.ops.object.transform_apply(location=True)
    into.append(o)
    return o


def cyl(r, depth, loc, into, rot=(0, 0, 0), verts=16, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=(0, 0, 0), vertices=verts)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=(0, 0, 0), vertices=verts)
    o = bpy.context.active_object
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    o.location = loc
    bpy.ops.object.transform_apply(location=True)
    into.append(o)
    return o


def finish(objs, name, base, rough, metal):
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
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def export(parts, name, blend, colliders=None):
    parts = [p for p in parts if p]
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
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
        json.dump({"boxes": colliders or []}, f)
    print("WROTE", out)


# ================================================================== the AKM
# 880 mm; bore axis is z=0; butt at y=0, muzzle at y=0.88
def build_ak():
    fresh()
    WOOD, STEEL, DARK = [], [], []
    # buttplate and the tapering stock with its dropped heel
    box(0.032, 0.02, 0.115, (0, 0.01, -0.015), DARK)
    b = box(0.036, 0.245, 0.095, (0, 0.135, -0.012), WOOD, rx=0.085)
    # receiver: the long box, slight taper at top cover
    box(0.038, 0.275, 0.062, (0, 0.395, 0.002), STEEL)
    box(0.034, 0.27, 0.012, (0, 0.395, 0.038), STEEL)          # the top cover crown
    # pistol grip, raked back
    box(0.030, 0.032, 0.095, (0, 0.318, -0.075), WOOD, rx=0.42)
    # trigger guard and trigger
    box(0.026, 0.075, 0.006, (0, 0.362, -0.052), DARK)
    box(0.006, 0.028, 0.032, (0, 0.352, -0.038), DARK, rx=0.25)
    box(0.026, 0.006, 0.022, (0, 0.398, -0.042), DARK)
    # THE MAGAZINE: a true banana - deep cross-section, segments overlapping
    # through the bend so the body reads as one curved box
    MAG = ((0.4400, -0.058, 0.16), (0.4525, -0.106, 0.38),
           (0.4720, -0.150, 0.62), (0.4990, -0.188, 0.88))
    for (my, mz, ang) in MAG:
        box(0.026, 0.075, 0.062, (0, my, mz), STEEL, rx=ang)
        box(0.028, 0.062, 0.008, (0, my + 0.033 * math.sin(ang),
                                  mz - 0.033 * math.cos(ang) + 0.033 * 0), STEEL, rx=ang)
    # rear sight block and leaf
    box(0.030, 0.030, 0.030, (0, 0.545, 0.030), STEEL)
    box(0.020, 0.055, 0.006, (0, 0.575, 0.048), STEEL, rx=-0.12)
    # lower handguard with palm swell, upper handguard, gas tube
    box(0.040, 0.145, 0.040, (0, 0.635, -0.008), WOOD)
    box(0.046, 0.145, 0.012, (0, 0.635, -0.030), WOOD)
    box(0.034, 0.145, 0.024, (0, 0.635, 0.036), WOOD)
    cyl(0.011, 0.15, (0, 0.635, 0.052), STEEL, rot=(math.pi / 2, 0, 0), verts=10)
    # gas block (slanted), barrel, cleaning rod
    box(0.026, 0.030, 0.045, (0, 0.722, 0.022), STEEL, rx=0.5)
    cyl(0.0085, 0.175, (0, 0.795, 0.0), STEEL, rot=(math.pi / 2, 0, 0), verts=10)
    cyl(0.004, 0.16, (0, 0.70, -0.022), STEEL, rot=(math.pi / 2, 0, 0), verts=8)
    # front sight: post between protective ears
    box(0.024, 0.018, 0.052, (0, 0.845, 0.026), STEEL)
    cyl(0.0035, 0.03, (0, 0.845, 0.055), STEEL, verts=6)
    # the slant brake
    cyl(0.011, 0.035, (0, 0.872, 0.0), STEEL, rot=(math.pi / 2, 0, 0), verts=10)
    box(0.022, 0.020, 0.024, (0, 0.888, 0.004), STEEL, rx=-0.6)
    # sling loops
    box(0.004, 0.018, 0.014, (0, 0.055, -0.052), DARK)
    box(0.004, 0.018, 0.014, (0, 0.60, -0.036), DARK)
    parts = [
        finish(WOOD, "wood", (0.44, 0.20, 0.075, 1), 0.5, 0.0),
        finish(STEEL, "steel", (0.055, 0.057, 0.06, 1), 0.42, 0.85),
        finish(DARK, "dark", (0.035, 0.035, 0.037, 1), 0.7, 0.4),
    ]
    export(parts, "ak", "ak97.blend")


# =============================================================== the RPG-7
def build_rpg():
    fresh()
    WOOD, STEEL, DARK = [], [], []
    # tube: bore z=0, rear y=0, muzzle end y=0.95
    cyl(0.020, 0.62, (0, 0.42, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=14)
    # rear venturi: flared bell
    cyl(0.020, 0.16, (0, 0.06, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=14, r2=0.042)
    cyl(0.044, 0.02, (0, -0.02, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=14)
    # wood heat shielding round the mid-tube
    cyl(0.030, 0.20, (0, 0.36, 0), WOOD, rot=(math.pi / 2, 0, 0), verts=14)
    # two grips under: fire grip (front) and support grip
    box(0.026, 0.030, 0.085, (0, 0.50, -0.065), WOOD, rx=0.35)
    box(0.026, 0.028, 0.075, (0, 0.60, -0.060), WOOD, rx=0.2)
    box(0.024, 0.055, 0.02, (0, 0.515, -0.028), DARK)
    # PGO-7 optic on the left
    box(0.030, 0.075, 0.045, (-0.042, 0.52, 0.035), DARK)
    cyl(0.020, 0.05, (-0.042, 0.565, 0.035), DARK, rot=(math.pi / 2, 0, 0), verts=10)
    # front: tube widens, then the PG-7 round: cone nose + bulb + boom
    cyl(0.020, 0.14, (0, 0.88, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=14)
    cyl(0.032, 0.10, (0, 0.99, 0), DARK, rot=(math.pi / 2, 0, 0), verts=14, r2=0.046)
    cyl(0.046, 0.09, (0, 1.085, 0), DARK, rot=(math.pi / 2, 0, 0), verts=14, r2=0.030)
    cyl(0.030, 0.07, (0, 1.16, 0), DARK, rot=(math.pi / 2, 0, 0), verts=12, r2=0.004)
    # iron sight post
    box(0.006, 0.006, 0.04, (0, 0.70, 0.038), STEEL)
    parts = [
        finish(WOOD, "wood", (0.40, 0.19, 0.08, 1), 0.55, 0.0),
        finish(STEEL, "steel", (0.06, 0.062, 0.065, 1), 0.45, 0.8),
        finish(DARK, "dark", (0.10, 0.11, 0.10, 1), 0.6, 0.3),
    ]
    export(parts, "rpg", "rpg97.blend")


# ========================================================== the 82mm mortar
def build_mortar():
    fresh()
    STEEL, DARK = [], []
    ang = math.radians(76)
    L = 1.22
    tx = math.cos(ang)
    # tube leaning back on its baseplate
    top = (0, -L * 0.5 * tx, L * 0.5 * math.sin(ang) + 0.06)
    cyl(0.041, L, (0, -L * 0.5 * tx, L * 0.5 * math.sin(ang) + 0.08), STEEL,
        rot=(ang - math.pi / 2, 0, 0), verts=16)
    cyl(0.052, 0.05, (0, -L * tx + 0.02, L * math.sin(ang) + 0.06), STEEL,
        rot=(ang - math.pi / 2, 0, 0), verts=16)          # muzzle ring
    # round baseplate with webs
    cyl(0.24, 0.045, (0, 0.06, 0.03), DARK, verts=20)
    for i in range(6):
        a = i / 6 * 2 * math.pi
        box(0.03, 0.20, 0.02, (math.cos(a) * 0.1, 0.06 + math.sin(a) * 0.1, 0.055), DARK, rz=a)
    # bipod: two legs + elevation screw + traverse
    for sx in (-1, 1):
        cyl(0.012, 0.62, (sx * 0.20, -0.42, 0.32), STEEL, rot=(0.45, sx * 0.35, 0), verts=8)
        box(0.05, 0.05, 0.02, (sx * 0.30, -0.55, 0.02), DARK)
    cyl(0.016, 0.30, (0, -0.42, 0.52), STEEL, rot=(0.35, 0, 0), verts=8)
    box(0.10, 0.05, 0.05, (0, -0.36, 0.62), DARK)
    parts = [
        finish(STEEL, "steel", (0.10, 0.11, 0.10, 1), 0.5, 0.7),
        finish(DARK, "dark", (0.06, 0.065, 0.06, 1), 0.7, 0.4),
    ]
    export(parts, "mortar", "mortar97.blend")


# ================================================================ the DShK
def build_dshk():
    fresh()
    STEEL, DARK = [], []
    # barrel with finned jacket at the rear half, big muzzle brake
    cyl(0.014, 0.60, (0, 0.62, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=12)
    for i in range(9):
        cyl(0.026, 0.018, (0, 0.18 + i * 0.038, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=12)
    cyl(0.040, 0.075, (0, 0.945, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=12)
    cyl(0.050, 0.02, (0, 0.985, 0), STEEL, rot=(math.pi / 2, 0, 0), verts=12)
    # receiver box + top cover hump + drum feed
    box(0.075, 0.30, 0.085, (0, 0.0, 0.0), DARK)
    box(0.065, 0.16, 0.03, (0, 0.02, 0.055), DARK)
    cyl(0.055, 0.07, (0.0, 0.05, 0.075), DARK, rot=(0, math.pi / 2, 0), verts=14)
    # spade grips + trigger bar
    for sx in (-1, 1):
        cyl(0.011, 0.10, (sx * 0.045, -0.185, -0.01), STEEL, rot=(0.9, 0, 0), verts=8)
    box(0.08, 0.02, 0.02, (0, -0.16, 0.01), DARK)
    parts = [
        finish(STEEL, "steel", (0.07, 0.072, 0.075, 1), 0.45, 0.8),
        finish(DARK, "dark", (0.05, 0.052, 0.055, 1), 0.6, 0.5),
    ]
    export(parts, "dshk", "dshk97.blend")


build_ak()
build_rpg()
build_mortar()
build_dshk()
print("WEAPONS DONE")
