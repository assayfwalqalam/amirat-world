# Weapons of the region's wars, modelled to real measured proportions and
# judged against Arma-class references from every side. Objects only, never
# crew. The AK first, and its family.
#   blender --background --python make_weapons.py -- <kind> <out.glb> [assets]
# Kinds: ak, rpg, mortar, dshk
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "ak"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 313)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

steel, wood, mag, black = [], [], [], []


def box(sx, sy, sz, loc, into, bevel=0.0, rot=(0, 0, 0)):
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
    into.append(ob)
    return ob


def cyl(r, h, loc, into, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=verts)
    into.append(bpy.context.active_object)
    return bpy.context.active_object


def taper(ob, axis, t0, t1):
    """Squeeze one end of a mesh: t at min-axis = t0, at max = t1."""
    vs = [v.co[axis] for v in ob.data.vertices]
    lo, hi = min(vs), max(vs)
    span = (hi - lo) or 1
    for v in ob.data.vertices:
        f = (v.co[axis] - lo) / span
        k = t0 + (t1 - t0) * f
        other = [0, 1, 2]
        other.remove(axis)
        for o in other:
            v.co[o] *= k


# The rifle lies along +x (muzzle forward), sights up +z. Real AK proportions:
# overall ~0.88 m, barrel to muzzle ~0.42 from receiver front.
if KIND == "ak":
    # receiver: the steel body (front at x=+0.15, rear at x=-0.15)
    box(0.30, 0.052, 0.066, (0.0, 0, 0.0), steel, bevel=0.004)
    # the dust cover ridge on top
    box(0.20, 0.05, 0.016, (-0.02, 0, 0.038), steel, bevel=0.003)
    # barrel forward from the receiver front
    cyl(0.010, 0.42, (0.36, 0, 0.010), steel, rot=(0, math.pi / 2, 0))
    # gas tube above the barrel
    cyl(0.0085, 0.20, (0.27, 0, 0.030), steel, rot=(0, math.pi / 2, 0))
    # gas block and front sight block on the barrel
    box(0.026, 0.03, 0.042, (0.40, 0, 0.026), steel, bevel=0.003)   # gas block
    box(0.022, 0.028, 0.05, (0.53, 0, 0.024), steel, bevel=0.003)   # front sight base
    cyl(0.0035, 0.04, (0.53, 0, 0.052), steel, verts=8)            # front sight post
    box(0.02, 0.03, 0.05, (0.545, 0, 0.024), steel, bevel=0.002)   # front sight ears (fwd)
    # rear sight leaf on the receiver
    box(0.026, 0.03, 0.016, (0.135, 0, 0.043), steel, bevel=0.002)
    # slant muzzle
    cyl(0.013, 0.035, (0.575, 0, 0.010), steel, rot=(0, math.pi / 2, 0.28))
    # THE BANANA MAGAZINE: a smooth arc curving FORWARD as it descends,
    # hung just ahead of the trigger. Flat wide segments aligned to the
    # tangent so the curve reads clean, tapering to the floorplate.
    R = 0.30
    a0 = -0.18
    top_x, top_z = 0.05, -0.03
    cxc = top_x - R * math.sin(a0)          # arc centre
    czc = top_z + R * math.cos(a0)
    N = 9
    span = 0.92
    for i in range(N):
        a = a0 + (i + 0.5) * (span / N)
        px = cxc + R * math.sin(a)
        pz = czc - R * math.cos(a)
        w = 0.052 * (1.0 - 0.18 * i / N)     # slim taper down the mag
        seg = box(0.05, 0.043, R * span / N * 1.35, (px, 0, pz), mag, rot=(0, a, 0))
        taper(seg, 0, w / 0.05, w / 0.05)
    # the mag well lip on the receiver
    box(0.07, 0.05, 0.03, (0.045, 0, -0.043), steel, rot=(0, a0, 0), bevel=0.003)
    # wooden lower handguard, tight against the receiver front
    hg = box(0.20, 0.052, 0.052, (0.28, 0, -0.008), wood, bevel=0.008)
    taper(hg, 0, 1.0, 0.84)
    # the handguard has the characteristic palm-swell dip cut on top
    box(0.075, 0.05, 0.05, (0.235, 0, 0.026), wood, bevel=0.006)   # upper handguard
    # pistol grip: prominent, raked back the AK way
    grip = box(0.036, 0.038, 0.13, (-0.075, 0, -0.075), wood, bevel=0.01, rot=(0, 0.38, 0))
    taper(grip, 2, 1.0, 0.78)                # flares slightly to the base
    # the thin raked buttstock: a slab that drops toward the toe
    st = box(0.26, 0.04, 0.052, (-0.28, 0, -0.006), wood, bevel=0.01)
    taper(st, 0, 0.9, 1.05)
    for v in st.data.vertices:               # rake the comb down toward the butt
        f = (v.co.x + 0.41) / 0.26
        if v.co.z > 0:
            v.co.z -= (1 - max(0, min(1, f))) * 0.006
    box(0.03, 0.044, 0.08, (-0.405, 0, -0.012), wood, bevel=0.008)   # butt pad end
    # trigger guard and trigger
    box(0.075, 0.028, 0.007, (-0.02, 0, -0.052), steel)   # guard bottom bar
    box(0.008, 0.02, 0.025, (0.02, 0, -0.04), steel)      # front strap
    cyl(0.006, 0.02, (-0.035, 0, -0.036), black, rot=(math.pi / 2, 0, 0), verts=8)  # trigger

elif KIND == "rpg":
    # RPG-7: the tube, the wide blast shield midway, the warhead up front
    cyl(0.021, 0.95, (0.0, 0, 0), steel, rot=(0, math.pi / 2, 0), verts=20)
    cyl(0.045, 0.06, (0.17, 0, 0), steel, rot=(0, math.pi / 2, 0), verts=20)   # the conical grip flare
    taper(steel[-1], 0, 1.0, 0.55)
    # the warhead: bulb tapering to the nose
    cyl(0.043, 0.14, (0.60, 0, 0), black, rot=(0, math.pi / 2, 0), verts=20)
    taper(black[-1], 0, 1.4, 0.5)
    cyl(0.02, 0.12, (0.72, 0, 0), black, rot=(0, math.pi / 2, 0), verts=16)   # the stem to fins
    box(0.02, 0.09, 0.002, (0.50, 0, 0), steel)     # fins on the warhead stem (cross)
    box(0.02, 0.002, 0.09, (0.50, 0, 0), steel)
    # wooden heat-guard on the tube
    hg = box(0.26, 0.06, 0.06, (0.02, 0, 0), wood, bevel=0.01)
    taper(hg, 0, 1.0, 1.0)
    box(0.24, 0.055, 0.055, (-0.30, 0, 0), wood, bevel=0.01)    # rear wood
    # pistol grip and trigger group
    box(0.03, 0.04, 0.11, (0.02, 0, -0.075), wood, bevel=0.008, rot=(0, 0.2, 0))
    box(0.05, 0.03, 0.02, (0.02, 0, -0.03), steel)
    # the iron sight on a stalk
    box(0.006, 0.03, 0.07, (0.10, 0, 0.05), steel)
    # the rear venturi cone (exhaust bell)
    cyl(0.035, 0.09, (-0.50, 0, 0), steel, rot=(0, math.pi / 2, 0), verts=20)
    taper(steel[-1], 0, 0.6, 1.25)

elif KIND == "mortar":
    # 82mm mortar: the tube leaning back over a bipod, on a baseplate
    lean = 1.16                       # radians from horizontal-ish, near-vertical
    tube = cyl(0.05, 0.9, (0, 0, 0.46), steel, rot=(0.34, 0, 0), verts=20)
    cyl(0.055, 0.06, (0.0, 0.16, 0.05), steel, rot=(0.34, 0, 0), verts=20)   # breech ball at the foot
    # baseplate: a dished steel disc
    plate = cyl(0.18, 0.03, (0, 0.16, 0.02), steel, verts=22)
    for v in plate.data.vertices:
        if v.co.z > 0:
            v.co.z += (0.18 - math.hypot(v.co.x, v.co.y - 0.16)) * 0.1
    # the bipod: two splayed legs to a clamp on the tube
    for sy in (-1, 1):
        cyl(0.012, 0.62, (sy * 0.16, -0.14, 0.30), steel,
            rot=(0.5, 0, sy * 0.32), verts=8)
    box(0.09, 0.05, 0.04, (0, -0.05, 0.44), steel, bevel=0.004)    # bipod clamp
    cyl(0.014, 0.14, (0.10, -0.05, 0.44), steel, rot=(0, math.pi / 2, 0), verts=8)  # traverse screw
    # the sight
    box(0.02, 0.03, 0.08, (-0.10, -0.05, 0.46), steel, bevel=0.003)

else:                          # dshk: heavy MG on a mount (the vehicle turret gun)
    # the barrel with its perforated jacket
    cyl(0.028, 0.9, (0.30, 0, 0.0), steel, rot=(0, math.pi / 2, 0), verts=18)
    cyl(0.045, 0.5, (0.15, 0, 0.0), steel, rot=(0, math.pi / 2, 0), verts=18)   # jacket
    # muzzle brake
    cyl(0.05, 0.05, (0.76, 0, 0), steel, rot=(0, math.pi / 2, 0), verts=14)
    # receiver body
    box(0.34, 0.09, 0.11, (-0.12, 0, 0), steel, bevel=0.005)
    # the round ammo drum on the side
    cyl(0.11, 0.07, (-0.16, 0.09, -0.02), mag, rot=(0, math.pi / 2, 0), verts=20)
    # spade grips at the back
    for sy in (-1, 1):
        box(0.02, 0.03, 0.13, (-0.30, sy * 0.06, -0.02), black, bevel=0.005, rot=(0, -0.2, 0))
    box(0.03, 0.16, 0.03, (-0.30, 0, 0.02), steel)      # grip crossbar
    # the pintle mount stalk below
    cyl(0.03, 0.34, (-0.10, 0, -0.22), steel, verts=14)
    box(0.14, 0.14, 0.04, (-0.10, 0, -0.40), steel, bevel=0.006)   # mount base


# --------------------------------------------------------------- materials
def finish(objs, name, base, rough, metal, tex=None, tint=None):
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
    bpy.ops.object.shade_smooth()
    es = ob.modifiers.new("es", 'EDGE_SPLIT')
    es.use_edge_angle = True
    es.split_angle = math.radians(40)
    bpy.ops.object.modifier_apply(modifier=es.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=0.3)
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
            if tint:
                mix = m.node_tree.nodes.new('ShaderNodeMixRGB')
                mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0
                mix.inputs['Color2'].default_value = tint
                m.node_tree.links.new(tn.outputs['Color'], mix.inputs['Color1'])
                m.node_tree.links.new(mix.outputs['Color'], b.inputs['Base Color'])
            else:
                m.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


parts = []
parts.append(finish(steel, "steel", (0.05, 0.05, 0.055, 1), 0.42, 0.85))
parts.append(finish(wood, "wood", (0.28, 0.16, 0.08, 1), 0.6, 0.0,
                    tex="t_wood_d.jpg", tint=(0.7, 0.42, 0.2, 1)))
parts.append(finish(mag, "mag", (0.30, 0.20, 0.09, 1), 0.5, 0.1))    # bakelite/steel mag
parts.append(finish(black, "black", (0.03, 0.03, 0.03, 1), 0.55, 0.2))
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
print("RESULT %s verts=%d tris=%d" % (KIND, len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
print("WROTE", OUT)
