# Vehicles, after the ones standing about in the reference: sun-bleached,
# scratched, rusted working machines. No occupants -- objects only.
#   blender --background --python make_vehicle.py -- <kind> <out.glb> [assets]
# Kinds: pickup, truck, minibus
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "pickup"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 449)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
body_parts, glass_parts, dark_parts = [], [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def box(sx, sy, sz, loc, into=None, collide=False, bevel=0.05):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = ob.modifiers.new("bv", 'BEVEL')
        m.width = bevel
        m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    (into if into is not None else body_parts).append(ob)
    return ob


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


def wheel(x, y, r=0.42):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.3, location=(x, y, r),
                                        rotation=(math.pi / 2, 0, 0), vertices=18)
    dark_parts.append(bpy.context.active_object)
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.55, depth=0.32, location=(x, y, r),
                                        rotation=(math.pi / 2, 0, 0), vertices=12)
    hub = bpy.context.active_object
    body_parts.append(hub)



def cab_box(cx, w2, cl, ch, zb, side_wins=1):
    """A cab that keeps its roof: hollow shell, then a hole per face."""
    c = box(cl, w2, ch, (cx, 0, zb + ch / 2), collide=True)
    cut(c, cl - 0.24, w2 - 0.24, ch - 0.2, (cx, 0, zb + ch / 2 - 0.06))
    zw = zb + ch * 0.62                       # window band centre
    hw = ch * 0.42                            # window height
    cut(c, 0.5, w2 - 0.55, hw, (cx + cl / 2 - 0.1, 0, zw))       # windscreen
    cut(c, 0.5, w2 - 0.6, hw * 0.9, (cx - cl / 2 + 0.1, 0, zw))  # rear window
    for sy in (-1, 1):                        # door windows
        for k in range(side_wins):
            wx = cx + (cl * 0.22 - k * cl * 0.42)
            cut(c, cl * 0.3, 0.5, hw, (wx, sy * (w2 / 2 - 0.1), zw))
    return c

# vehicle axes: x = length, y = width, z = up
if KIND == "pickup":
    L, W2, CH = 4.6, 1.75, 1.0
    bed = box(L, W2, 0.65, (0, 0, 0.45 + 0.325), collide=True)
    cut(bed, L - 2.5, W2 - 0.3, 0.6, (-0.75, 0, 0.85))       # the open bed
    cab_box(1.05, W2, 1.6, 1.5, 0.75)
    bon = box(1.05, W2 - 0.1, 0.5, (2.3, 0, 1.0), bevel=0.07)  # the bonnet
    for v in bon.data.vertices:                                # nose drops a little
        if v.co.z > 1.0 and v.co.x > 2.3:
            v.co.z -= (v.co.x - 2.3) * 0.18
    box(0.08, W2 * 0.62, 0.2, (2.82, 0, 1.02), into=dark_parts, bevel=0.02)  # grille
    for x, y in ((2.15, W2 / 2), (2.15, -W2 / 2), (-1.4, W2 / 2), (-1.4, -W2 / 2)):
        wheel(x, y)
    box(0.25, W2 * 0.9, 0.12, (2.35, 0, 0.75), into=dark_parts)   # bumper
    rec((0, 0, 0.9), L / 2, W2 / 2, 0.9)

elif KIND == "truck":
    L, W2 = 6.6, 2.3
    box(L - 2.0, W2, 0.35, (-1.0, 0, 0.85), collide=True)          # flat bed
    for sy in (-1, 1):                                             # stake sides
        for i in range(5):
            box(0.08, 0.08, 0.9, (-3.0 + i * 1.1, sy * (W2 / 2 - 0.06), 1.45), bevel=0.02)
        box(L - 2.1, 0.06, 0.1, (-1.0, sy * (W2 / 2 - 0.06), 1.85), bevel=0.02)
    cab_box(2.3, W2, 1.8, 1.9, 0.75)
    bon = box(0.95, W2 * 0.92, 0.75, (3.65, 0, 1.15), bevel=0.08)  # the nose
    for v in bon.data.vertices:
        if v.co.z > 1.2 and v.co.x > 3.65:
            v.co.z -= (v.co.x - 3.65) * 0.22
    box(0.08, W2 * 0.6, 0.26, (4.1, 0, 1.15), into=dark_parts, bevel=0.02)   # grille
    for x, y in ((3.3, W2 / 2), (3.3, -W2 / 2), (-0.4, W2 / 2), (-0.4, -W2 / 2),
                 (-2.4, W2 / 2), (-2.4, -W2 / 2)):
        wheel(x, y, 0.52)
    rec((0, 0, 1.1), L / 2, W2 / 2, 1.1)

else:                        # minibus
    L, W2 = 5.4, 1.9
    body = box(L, W2, 1.75, (0, 0, 0.55 + 0.875), collide=True, bevel=0.09)
    cut(body, L - 0.3, W2 - 0.26, 1.45, (0, 0, 1.35))            # hollow shell
    for i in range(4):                                           # side windows
        for sy in (-1, 1):
            cut(body, 0.85, 0.5, 0.6, (-1.7 + i * 1.15, sy * (W2 / 2 - 0.1), 1.95))
    cut(body, 0.5, W2 - 0.55, 0.7, (L / 2 - 0.1, 0, 1.9))        # windscreen
    cut(body, 0.5, W2 - 0.6, 0.6, (-L / 2 + 0.1, 0, 1.95))       # rear window
    box(0.3, W2 * 0.9, 0.14, (2.75, 0, 0.7), into=dark_parts)
    for x, y in ((1.8, W2 / 2), (1.8, -W2 / 2), (-1.7, W2 / 2), (-1.7, -W2 / 2)):
        wheel(x, y, 0.44)
    # roof rack with bundles
    for sy in (-1, 1):
        box(L * 0.7, 0.05, 0.18, (0, sy * (W2 / 2 - 0.15), 2.55), bevel=0.02)
    for i in range(3):
        b = box(0.9, W2 * 0.6, 0.4, (-1.2 + i * 1.2, 0, 2.75), bevel=0.12)
    rec((0, 0, 1.2), L / 2, W2 / 2, 1.2)


# ------------------------------------------------------------- materials
def join_group(objs, name):
    if not objs:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cube_project(cube_size=1.6)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


paintN = {"pickup": 1, "truck": 2, "minibus": 3}[KIND]
body = join_group(body_parts, "body")
mat = bpy.data.materials.new("paint")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.62
bsdf.inputs["Metallic"].default_value = 0.25
tex_path = os.path.abspath(os.path.join(ASSETS, "t_metal%d_d.jpg" % paintN))
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    img.pack()
body.data.materials.clear()
body.data.materials.append(mat)

dark = join_group(dark_parts, "dark")
if dark:
    dm = bpy.data.materials.new("dark")
    dm.use_nodes = True
    db = dm.node_tree.nodes["Principled BSDF"]
    db.inputs["Base Color"].default_value = (0.045, 0.045, 0.048, 1)
    db.inputs["Roughness"].default_value = 0.9
    dark.data.materials.clear()
    dark.data.materials.append(dm)

bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
if dark:
    dark.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d" % (KIND, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
