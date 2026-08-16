# Rocks and pebbles, each one a different stone.
#   blender --background --python make_rock.py -- <kind> <seed> <out.glb> [assets]
#
# Kinds: boulder, slab, shard, round, stack, pebbles, scree, outcrop, cliff, kerb
#
# A rock is not a sphere with noise on it. Real stone breaks along planes, so
# these are cut by a handful of random flats first and only then weathered --
# that is what gives the flat faces and sharp arrises that read as rock.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "boulder"
SEED = int(argv[1]) if len(argv) > 1 else 1
OUT = argv[2] if len(argv) > 2 else (KIND + ".glb")
ASSETS = argv[3] if len(argv) > 3 else "assets"
random.seed(SEED * 5443 + sum(ord(c) for c in KIND) * 97)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

COLLIDERS = []
parts = []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def lump(r, loc, seg=12, squash=1.0, wobble=0.22):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg,
                                         ring_count=max(4, seg // 2))
    ob = bpy.context.active_object
    for v in ob.data.vertices:
        v.co.z *= squash
        n = 1.0 + random.uniform(-wobble, wobble)
        v.co.x *= n
        v.co.y *= n * (1.0 + random.uniform(-wobble * 0.5, wobble * 0.5))
    parts.append(ob)
    return ob


def cleave(ob, n=4, keep_bottom=True):
    """Cut the lump with random flat planes, the way stone actually breaks."""
    bpy.context.view_layer.objects.active = ob
    for _ in range(n):
        a = random.uniform(0, math.pi * 2)
        el = random.uniform(-0.5, 1.1)
        big = 12.0
        bpy.ops.mesh.primitive_cube_add(size=big, location=(0, 0, 0))
        cut = bpy.context.active_object
        cut.rotation_euler = (el, random.uniform(-0.4, 0.4), a)
        bpy.ops.object.transform_apply(rotation=True)
        # push the cutter out so only a slice of the lump is taken
        d = ob.dimensions.length * random.uniform(0.28, 0.46) + big / 2
        cut.location = (math.cos(a) * d * math.cos(el),
                        math.sin(a) * d * math.cos(el),
                        d * math.sin(el) * 0.7 + (0.2 if not keep_bottom else 0.5))
        bpy.ops.object.transform_apply(location=True)
        before = len(ob.data.vertices)
        m = ob.modifiers.new("b", 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = cut
        m.solver = 'EXACT'
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(cut, do_unlink=True)
        # A plane that happens to fall the wrong side takes the whole stone
        # away and the export then has nothing to write. Stop cutting if the
        # lump is nearly gone.
        if len(ob.data.vertices) < 8:
            print("cleave swallowed the lump, stopping")
            return


def weather(ob, fine=0.02, broad=0.05, levels=1):
    bpy.context.view_layer.objects.active = ob
    if levels:
        m = ob.modifiers.new("sub", 'SUBSURF')
        m.subdivision_type = 'SIMPLE'
        m.levels = m.render_levels = levels
        bpy.ops.object.modifier_apply(modifier=m.name)
    for sc, st in ((2.2, fine), (7.0, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = sc
        t.noise_depth = 2
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = st
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.004)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def sink(ob):
    """Drop the lowest point to zero, so it sits on the ground not through it."""
    if not len(ob.data.vertices):
        return
    lo = min(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:
        v.co.z -= lo


def hewn(r, loc, seg, squash, wobble, cuts):
    """A lump broken by flat planes -- retried plainly if the cuts eat it.

    A cutting plane that happens to fall the wrong side can take the whole
    stone, and the export then has nothing to write. Rather than ship a hole
    in the world, keep the uncut lump.
    """
    b = lump(r, loc, seg, squash, wobble)
    cleave(b, cuts)
    if len(b.data.vertices) < 8:
        parts.remove(b)
        bpy.data.objects.remove(b, do_unlink=True)
        b = lump(r, loc, seg, squash, wobble)
    return b


# ------------------------------------------------------------------ kinds
if KIND == "boulder":
    R = random.uniform(1.1, 2.2)
    b = hewn(R, (0, 0, 0), 14, random.uniform(0.62, 0.9), 0.22, random.randint(3, 5))
    weather(b, 0.03, 0.08)
    sink(b)
    rec((0, 0, R * 0.4), R * 0.8, R * 0.8, R * 0.4)

elif KIND == "slab":
    W = random.uniform(1.6, 3.0)
    b = hewn(W, (0, 0, 0), 12, random.uniform(0.14, 0.24), 0.3, random.randint(4, 6))
    weather(b, 0.02, 0.05)
    sink(b)
    rec((0, 0, W * 0.1), W * 0.8, W * 0.7, W * 0.1)

elif KIND == "shard":
    H = random.uniform(1.2, 2.6)
    b = hewn(H * 0.5, (0, 0, 0), 10, random.uniform(1.5, 2.4), 0.34, random.randint(5, 7))
    weather(b, 0.02, 0.05)
    sink(b)
    b.rotation_euler = (random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), 0)
    bpy.ops.object.transform_apply(rotation=True)
    rec((0, 0, H * 0.4), H * 0.34, H * 0.34, H * 0.4)

elif KIND == "round":
    R = random.uniform(0.7, 1.4)
    b = lump(R, (0, 0, 0), 16, random.uniform(0.7, 0.95), 0.12)
    weather(b, 0.02, 0.04, levels=1)
    sink(b)
    rec((0, 0, R * 0.45), R * 0.85, R * 0.85, R * 0.45)

elif KIND == "stack":
    z = 0.0
    for i in range(random.randint(3, 5)):
        r = random.uniform(0.45, 0.95) * (1.0 - i * 0.11)
        b = hewn(r, (random.uniform(-0.14, 0.14), random.uniform(-0.14, 0.14), z + r * 0.4),
                 12, random.uniform(0.4, 0.62), 0.22, 3)
        weather(b, 0.02, 0.04)
        z += r * 0.62
    rec((0, 0, z / 2), 0.9, 0.9, z / 2)

elif KIND == "pebbles":
    for _ in range(random.randint(16, 26)):
        r = random.uniform(0.05, 0.16)
        b = lump(r, (random.uniform(-0.9, 0.9), random.uniform(-0.9, 0.9), r * 0.3),
                 8, random.uniform(0.4, 0.75), 0.3)
        b.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
        bpy.ops.object.transform_apply(rotation=True)

elif KIND == "scree":
    for _ in range(random.randint(22, 34)):
        r = random.uniform(0.09, 0.32)
        b = lump(r, (random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5), r * 0.25),
                 8, random.uniform(0.3, 0.6), 0.35)
        cleave(b, 2)
        b.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
        bpy.ops.object.transform_apply(rotation=True)

elif KIND == "outcrop":
    base = hewn(random.uniform(2.4, 3.4), (0, 0, 0), 14, random.uniform(0.5, 0.8), 0.22, 5)
    weather(base, 0.04, 0.1)
    sink(base)
    for _ in range(random.randint(2, 4)):
        r = random.uniform(0.6, 1.4)
        s = lump(r, (random.uniform(-2, 2), random.uniform(-2, 2), r * 0.5), 10,
                 random.uniform(0.5, 0.9))
        cleave(s, 3)
        weather(s, 0.02, 0.06)
    rec((0, 0, 1.2), 2.6, 2.6, 1.2)

elif KIND == "cliff":
    W = random.uniform(6.0, 9.0)
    H = random.uniform(5.0, 8.0)
    b = hewn(W * 0.5, (0, 0, 0), 16, H / (W * 0.5) * 0.5, 0.24, 6)
    weather(b, 0.06, 0.16, levels=1)
    sink(b)
    for _ in range(random.randint(3, 6)):
        r = random.uniform(0.5, 1.6)
        s = lump(r, (random.uniform(-W / 2, W / 2), random.uniform(-W / 2, W / 2), r * 0.4),
                 10, 0.6)
        cleave(s, 3)
        weather(s, 0.02, 0.05)
    rec((0, 0, H / 2), W * 0.42, W * 0.42, H / 2)

else:                       # kerb: a low line of set stones
    x = -1.6
    while x < 1.6:
        r = random.uniform(0.16, 0.3)
        b = lump(r, (x, random.uniform(-0.08, 0.08), r * 0.35), 9,
                 random.uniform(0.5, 0.8), 0.22)
        cleave(b, 2)
        x += r * 1.7
    rec((0, 0, 0.16), 1.7, 0.3, 0.16)


# -------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.004)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=1.4)
bpy.ops.object.mode_set(mode='OBJECT')

# stone colour varies by kind and by seed: sandstone, grey limestone, dark basalt
BASE = {
    "boulder": (0.30, 0.27, 0.23), "slab": (0.34, 0.31, 0.27),
    "shard":   (0.26, 0.24, 0.22), "round": (0.36, 0.32, 0.27),
    "stack":   (0.32, 0.29, 0.25), "pebbles": (0.38, 0.34, 0.29),
    "scree":   (0.31, 0.28, 0.24), "outcrop": (0.33, 0.28, 0.22),
    "cliff":   (0.35, 0.30, 0.24), "kerb": (0.33, 0.30, 0.26),
}.get(KIND, (0.32, 0.29, 0.25))
warm = random.uniform(-0.05, 0.09)
TINT = (min(1, BASE[0] + warm), min(1, BASE[1] + warm * 0.6), min(1, BASE[2] + warm * 0.25))

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (TINT[0], TINT[1], TINT[2], 1)
bsdf.inputs["Roughness"].default_value = 0.96
ob.data.materials.clear()
ob.data.materials.append(mat)

tex_path = os.path.abspath(os.path.join(ASSETS, "g_rock_d.jpg"))
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
    data = ob.data.color_attributes["ao"].data
    for i in range(len(data)):
        ao = 0.32 + 0.64 * data[i].color[0]
        data[i].color = (ao * TINT[0] * 2.6, ao * TINT[1] * 2.6, ao * TINT[2] * 2.6, 1.0)
except Exception as e:
    print("bake failed:", e)

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

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%d verts=%d tris=%d colliders=%d"
      % (KIND, SEED, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
