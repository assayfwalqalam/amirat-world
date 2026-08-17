# Military and civilian-war vehicles of the region, reproduced by eye and
# measurement from real proportions (never extracted from any game). The
# silhouettes of a US light truck, a UK patrol vehicle, a technical, and
# their burnt-out wrecks. Objects only, never crew.
#   blender --background --python make_vehicle_mil.py -- <kind> <out.glb> [assets]
# Kinds: humvee, landrover, technical, wreck_car, wreck_truck
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "humvee"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 227)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
body, dark, glass, burnt = [], [], [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def box(sx, sy, sz, loc, into, bevel=0.03, rot=(0, 0, 0), collide=False):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if bevel:
        m = ob.modifiers.new("bv", 'BEVEL')
        m.width = bevel
        m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    into.append(ob)
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


def wheel(x, y, r, into, w=0.28):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=w, location=(x, y, r),
                                        rotation=(math.pi / 2, 0, 0), vertices=18)
    into.append(bpy.context.active_object)
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.45, depth=w + 0.02, location=(x, y, r),
                                        rotation=(math.pi / 2, 0, 0), vertices=10)
    body.append(bpy.context.active_object)


# vehicle axes: x = length (front +x), y = width, z = up
if KIND == "humvee":
    # A US light tactical truck: very wide, low, boxy, sloped hood, flat roof,
    # wide track, big wheels. Real ~4.6 x 2.2 x 1.9.
    L, W2 = 4.6, 2.2
    hull = box(L, W2, 0.9, (0, 0, 0.62), body, bevel=0.05, collide=True)
    # sloped hood at the front
    hood = box(1.2, W2 - 0.15, 0.4, (1.5, 0, 1.0), body, bevel=0.05)
    for v in hood.data.vertices:
        if v.co.x > 1.5 and v.co.z > 1.0:
            v.co.z -= (v.co.x - 1.5) * 0.28
    # the cab/greenhouse: short, upright, flat roof
    cab = box(2.0, W2 - 0.2, 0.85, (-0.2, 0, 1.45), body, bevel=0.05)
    cut(cab, 0.5, W2, 0.5, (0.75, 0, 1.55))         # windscreen
    for sy in (-1, 1):
        cut(cab, 1.4, 0.5, 0.42, (-0.3, sy * (W2 / 2 - 0.1), 1.55))   # side windows
    box(2.1, W2 - 0.2, 0.08, (-0.2, 0, 1.9), body, bevel=0.03)        # flat roof
    # the front grille and slat
    box(0.1, W2 - 0.4, 0.5, (2.32, 0, 0.85), dark, bevel=0.02)
    for i in range(6):
        box(0.02, 0.06, 0.4, (2.37, -W2 / 2 + 0.4 + i * (W2 - 0.8) / 5, 0.85), dark)
    # bumper
    box(0.18, W2, 0.16, (2.35, 0, 0.5), dark, bevel=0.03)
    # the four wide wheels, pushed to the corners
    for x, y in ((1.5, W2 / 2 + 0.02), (1.5, -W2 / 2 - 0.02), (-1.5, W2 / 2 + 0.02), (-1.5, -W2 / 2 - 0.02)):
        wheel(x, y, 0.62, dark, 0.40)
    rec((0, 0, 1.0), L / 2, W2 / 2, 1.0)

elif KIND == "landrover":
    # A UK patrol vehicle: tall, narrow, flat vertical panels, roof rack,
    # spare wheel on the bonnet. Real ~4.5 x 1.8 x 2.0.
    L, W2 = 4.5, 1.8
    hull = box(L, W2, 1.1, (0, 0, 0.75), body, bevel=0.03, collide=True)
    # flat vertical bonnet
    box(1.3, W2 - 0.1, 0.5, (1.5, 0, 1.05), body, bevel=0.03)
    # the upright boxy cab with big flat windscreen
    cab = box(2.2, W2 - 0.05, 1.0, (-0.3, 0, 1.7), body, bevel=0.03)
    cut(cab, 0.4, W2, 0.6, (0.85, 0, 1.8))          # windscreen (near-vertical)
    for sy in (-1, 1):
        cut(cab, 1.6, 0.4, 0.5, (-0.4, sy * (W2 / 2 - 0.05), 1.8))
    # roof rack
    box(2.4, W2 - 0.1, 0.06, (-0.3, 0, 2.25), body, bevel=0.02)
    for sy in (-1, 1):
        box(2.4, 0.05, 0.14, (-0.3, sy * (W2 / 2 - 0.1), 2.32), dark)
    # spare wheel on the bonnet
    bpy.ops.mesh.primitive_cylinder_add(radius=0.38, depth=0.22, location=(1.5, 0, 1.5),
                                        rotation=(0, 0, 0), vertices=16)
    dark.append(bpy.context.active_object)
    # grille + round headlamps
    box(0.1, W2 - 0.3, 0.45, (2.18, 0, 1.05), dark, bevel=0.02)
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.08, location=(2.2, sy * (W2 / 2 - 0.3), 1.1),
                                            rotation=(0, math.pi / 2, 0), vertices=12)
        glass.append(bpy.context.active_object)
    box(0.16, W2, 0.14, (2.2, 0, 0.55), dark, bevel=0.03)     # bumper
    for x, y in ((1.45, W2 / 2 + 0.02), (1.45, -W2 / 2 - 0.02), (-1.5, W2 / 2 + 0.02), (-1.5, -W2 / 2 - 0.02)):
        wheel(x, y, 0.42, dark, 0.26)
    rec((0, 0, 1.1), L / 2, W2 / 2, 1.1)

elif KIND == "technical":
    # A technical: a civilian pickup with a heavy gun on the bed. The truck
    # is our existing pickup silhouette; the gun mount is a pintle + DShK-like
    # barrel (built here so the piece stands alone at the test site).
    L, W2 = 4.6, 1.75
    bed = box(L, W2, 0.6, (0, 0, 0.75), body, bevel=0.04, collide=True)
    cut(bed, L - 2.6, W2 - 0.3, 0.55, (-0.8, 0, 1.02))       # open bed
    cab = box(1.7, W2, 0.95, (1.2, 0, 1.35), body, bevel=0.05)
    cut(cab, 0.45, W2, 0.5, (0.55, 0, 1.5))
    for sy in (-1, 1):
        cut(cab, 1.2, 0.45, 0.4, (1.25, sy * (W2 / 2 - 0.08), 1.5))
    box(0.95, W2 - 0.12, 0.35, (2.15, 0, 0.95), body, bevel=0.05)   # bonnet
    box(0.1, W2 - 0.3, 0.35, (2.6, 0, 0.85), dark, bevel=0.02)      # grille
    box(0.2, W2, 0.14, (2.62, 0, 0.55), dark, bevel=0.03)          # bumper
    for x, y in ((1.6, W2 / 2), (1.6, -W2 / 2), (-1.5, W2 / 2), (-1.5, -W2 / 2)):
        wheel(x, y, 0.44, dark, 0.28)
    # the pintle mount and gun on the bed
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.7, location=(-0.9, 0, 1.4), vertices=12)
    dark.append(bpy.context.active_object)
    box(0.7, 0.12, 0.14, (-0.55, 0, 1.75), dark, bevel=0.02)       # receiver
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=1.1, location=(-0.05, 0, 1.78),
                                        rotation=(0, math.pi / 2, 0), vertices=12)
    dark.append(bpy.context.active_object)                         # barrel
    for sy in (-1, 1):                                             # spade grips
        box(0.02, 0.03, 0.14, (-0.95, sy * 0.06, 1.72), dark, bevel=0.004)
    rec((0, 0, 1.0), L / 2, W2 / 2, 1.0)

elif KIND == "wreck_car":
    # A burnt-out car: a slumped hull, no wheels (on its rims/blocks),
    # blackened, window holes empty, a caved roof.
    L, W2 = 4.0, 1.75
    hull = box(L, W2, 0.7, (0, 0, 0.5), burnt, bevel=0.04, collide=True)
    cab = box(2.0, W2 - 0.1, 0.7, (-0.1, 0, 1.0), burnt, bevel=0.04)
    # cave the roof in
    for v in cab.data.vertices:
        if v.co.z > 1.1:
            v.co.z -= 0.25 + random.uniform(0, 0.12)
            v.co.x += random.uniform(-0.06, 0.06)
    cut(cab, 0.5, W2, 0.6, (0.7, 0, 1.15))          # gaping windscreen
    for sy in (-1, 1):
        cut(cab, 1.3, 0.5, 0.5, (-0.2, sy * (W2 / 2 - 0.05), 1.15))
    box(1.0, W2 - 0.15, 0.3, (1.4, 0, 0.85), burnt, bevel=0.04)   # hood, buckled
    for v in burnt[-1].data.vertices:
        v.co.z += random.uniform(-0.05, 0.08)
    # sat on brake rims / blocks, not wheels
    for x, y in ((1.3, W2 / 2 - 0.1), (1.3, -W2 / 2 + 0.1), (-1.3, W2 / 2 - 0.1), (-1.3, -W2 / 2 + 0.1)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.12, location=(x, y, 0.12),
                                            rotation=(math.pi / 2, 0, 0), vertices=12)
        burnt.append(bpy.context.active_object)
    rec((0, 0, 0.8), L / 2, W2 / 2, 0.8)

else:                          # wreck_truck: a gutted truck cab + bare chassis
    L, W2 = 5.5, 2.1
    box(2.6, W2 - 0.2, 0.25, (-1.2, 0, 0.7), burnt, bevel=0.03, collide=True)   # bare flatbed chassis
    for i in range(5):                                                          # chassis cross members
        box(0.1, W2 - 0.2, 0.1, (-2.4 + i * 0.6, 0, 0.6), burnt)
    cab = box(1.6, W2 - 0.1, 1.3, (2.0, 0, 1.2), burnt, bevel=0.04)
    for v in cab.data.vertices:                                                 # crumpled cab
        if v.co.z > 1.5:
            v.co.z -= 0.2 + random.uniform(0, 0.15)
        v.co.x += random.uniform(-0.04, 0.04)
    cut(cab, 0.45, W2, 0.7, (2.7, 0, 1.5))
    for sy in (-1, 1):
        cut(cab, 1.0, 0.45, 0.55, (2.0, sy * (W2 / 2 - 0.05), 1.5))
    box(0.8, W2 - 0.2, 0.5, (3.0, 0, 0.85), burnt, bevel=0.03)                  # gutted engine bay
    # two wheels left, two gone
    for x, y in ((2.1, W2 / 2), (-1.6, -W2 / 2 - 0.02)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=0.3, location=(x, y, 0.5),
                                            rotation=(math.pi / 2, 0, 0), vertices=16)
        burnt.append(bpy.context.active_object)
    for x, y in ((2.1, -W2 / 2), (-1.6, W2 / 2 + 0.02)):                        # bare hubs
        bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.14, location=(x, y, 0.5),
                                            rotation=(math.pi / 2, 0, 0), vertices=10)
        burnt.append(bpy.context.active_object)
    rec((0, 0, 1.0), L / 2, W2 / 2, 1.0)


# --------------------------------------------------------------- materials
def finish(objs, name, base, rough, metal, tex=None):
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
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cube_project(cube_size=1.4)
    bpy.ops.object.mode_set(mode='OBJECT')
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = m.node_tree.nodes.new('ShaderNodeTexImage')
            tn.image = img
            m.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


# desert-tan for US, dark-sand for UK, civilian white-ish for technical
PAINT = {"humvee": (0.52, 0.46, 0.32, 1), "landrover": (0.40, 0.42, 0.34, 1),
         "technical": (0.55, 0.52, 0.46, 1)}.get(KIND, (0.5, 0.47, 0.4, 1))

parts = []
parts.append(finish(body, "paint", PAINT, 0.62, 0.25, tex="t_metal1_d.jpg"))
parts.append(finish(dark, "dark", (0.05, 0.05, 0.05, 1), 0.8, 0.2))
parts.append(finish(glass, "glass", (0.1, 0.12, 0.14, 1), 0.25, 0.5))
parts.append(finish(burnt, "burnt", (0.06, 0.055, 0.05, 1), 0.9, 0.1))
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
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
