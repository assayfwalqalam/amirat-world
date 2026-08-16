# Plants, as their own pack.
#   blender --background --python make_plant.py -- <kind> <seed> <out.glb> [assets]
#
# Kinds: tuft, reed, fern, shrub, blossom, aloe, agave, creeper, thistle,
#        sapling, lavender, poppy, papyrus, succulent
#
# Leaves are built as narrow tapering strips that curve and droop under their
# own weight, not as flat cards -- a card only reads from one side, and the
# moment you walk round it the plant disappears. Colour is carried in the
# vertex layer, so one material covers leaf, stem and flower.
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "tuft"
SEED = int(argv[1]) if len(argv) > 1 else 1
OUT = argv[2] if len(argv) > 2 else (KIND + ".glb")
ASSETS = argv[3] if len(argv) > 3 else "assets"
random.seed(SEED * 3313 + sum(ord(c) for c in KIND) * 71)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 6

parts = []          # (object, tint) so colour survives the join
LEAF = (0.10, 0.26, 0.075)
LEAF_DRY = (0.30, 0.30, 0.13)
STEM = (0.16, 0.22, 0.09)
WOOD = (0.20, 0.14, 0.09)


def add(ob, tint):
    parts.append((ob, tint))
    return ob


def blade(x, y, z, length, width, lean, twist, droop, tint=LEAF, segs=6):
    """A tapering strip that curves over as it rises."""
    me = bpy.data.meshes.new("b")
    ob = bpy.data.objects.new("b", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    prev = None
    ang = lean
    px, pz = 0.0, 0.0
    for i in range(segs + 1):
        t = i / float(segs)
        w = width * (1.0 - t) ** 0.7
        ang += droop / segs
        px += math.sin(ang) * (length / segs)
        pz += math.cos(ang) * (length / segs)
        a = bm.verts.new((px - w * math.cos(twist), -w * math.sin(twist), pz))
        b = bm.verts.new((px + w * math.cos(twist), w * math.sin(twist), pz))
        if prev:
            bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)
    bm.to_mesh(me)
    bm.free()
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, random.uniform(0, 6.283))
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True)
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.006
    bpy.ops.object.modifier_apply(modifier=sol.name)
    return add(ob, tint)


def stem(x, y, z, h, r=0.012, lean=0.0, tint=STEM, verts=5):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r * 0.4, depth=h,
                                    location=(x, y, z + h / 2), vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = (lean * random.uniform(-1, 1), lean * random.uniform(-1, 1), 0)
    bpy.ops.object.transform_apply(rotation=True)
    return add(ob, tint)


def puff(x, y, z, r, tint, seg=7, squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, z), segments=seg,
                                         ring_count=max(4, seg // 2))
    ob = bpy.context.active_object
    for v in ob.data.vertices:
        v.co.z *= squash
        v.co.x += random.uniform(-r * 0.22, r * 0.22)
        v.co.y += random.uniform(-r * 0.22, r * 0.22)
    return add(ob, tint)


def petals(x, y, z, r, tint, n=5):
    for i in range(n):
        a = i * 6.283 / n + random.uniform(-0.2, 0.2)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(
            x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, z), segments=6, ring_count=4)
        ob = bpy.context.active_object
        for v in ob.data.vertices:
            v.co.z *= 0.34
        add(ob, tint)


FLOWERS = [(0.55, 0.13, 0.14), (0.62, 0.42, 0.10), (0.34, 0.16, 0.44),
           (0.72, 0.66, 0.62), (0.60, 0.30, 0.40), (0.52, 0.48, 0.12)]
FL = FLOWERS[SEED % len(FLOWERS)]

# ------------------------------------------------------------------ kinds
if KIND == "tuft":
    for _ in range(random.randint(22, 34)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.11)
        blade(math.cos(a) * r, math.sin(a) * r, 0.0,
              random.uniform(0.24, 0.46), random.uniform(0.012, 0.022),
              random.uniform(0.1, 0.5), random.uniform(0, 3.1), random.uniform(0.3, 0.9),
              LEAF if random.random() < 0.72 else LEAF_DRY)

elif KIND == "reed":
    for _ in range(random.randint(12, 20)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.13)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = random.uniform(0.9, 1.7)
        stem(x, y, 0, h, 0.011, 0.06)
        blade(x, y, h * random.uniform(0.4, 0.8), random.uniform(0.3, 0.5), 0.016,
              random.uniform(0.4, 0.9), random.uniform(0, 3.1), 0.7)
        if random.random() < 0.5:
            puff(x, y, h + 0.05, 0.035, (0.34, 0.26, 0.14), 6, 3.0)

elif KIND == "fern":
    for _ in range(random.randint(7, 12)):
        a = random.uniform(0, 6.283)
        ln = random.uniform(0.36, 0.6)
        blade(0, 0, 0.02, ln, 0.05, random.uniform(0.5, 0.9), a, 0.55)
        for k in range(9):
            t = (k + 1) / 10.0
            blade(math.sin(a) * ln * t * 0.7, math.cos(a) * 0.0, 0.02 + ln * t * 0.55,
                  0.11 * (1 - t * 0.6), 0.012, 1.2, a + 1.57, 0.3)

elif KIND == "shrub":
    stem(0, 0, 0, 0.22, 0.03, 0.0, WOOD)
    for _ in range(random.randint(16, 26)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0.04, 0.3)
        puff(math.cos(a) * r, math.sin(a) * r, 0.2 + random.uniform(0, 0.34),
             random.uniform(0.07, 0.15), LEAF, 7, random.uniform(0.6, 0.95))

elif KIND == "blossom":
    stem(0, 0, 0, 0.24, 0.028, 0.0, WOOD)
    for _ in range(random.randint(14, 22)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0.04, 0.28)
        puff(math.cos(a) * r, math.sin(a) * r, 0.22 + random.uniform(0, 0.3),
             random.uniform(0.07, 0.14), LEAF, 7, 0.8)
    for _ in range(random.randint(10, 18)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0.06, 0.3)
        petals(math.cos(a) * r, math.sin(a) * r, 0.3 + random.uniform(0, 0.28), 0.032, FL)

elif KIND == "aloe":
    for i in range(random.randint(9, 14)):
        a = i * 6.283 / 11 + random.uniform(-0.2, 0.2)
        blade(math.cos(a) * 0.03, math.sin(a) * 0.03, 0.01,
              random.uniform(0.3, 0.5), random.uniform(0.045, 0.07),
              random.uniform(0.15, 0.45), a, random.uniform(0.35, 0.7),
              (0.16, 0.30, 0.16))

elif KIND == "agave":
    for i in range(random.randint(11, 16)):
        a = i * 6.283 / 13 + random.uniform(-0.15, 0.15)
        blade(math.cos(a) * 0.02, math.sin(a) * 0.02, 0.0,
              random.uniform(0.45, 0.75), random.uniform(0.05, 0.08),
              random.uniform(0.1, 0.3), a, random.uniform(0.2, 0.45),
              (0.20, 0.28, 0.15))

elif KIND == "creeper":
    for _ in range(random.randint(5, 9)):
        a = random.uniform(0, 6.283)
        x, y = 0.0, 0.0
        for k in range(random.randint(6, 11)):
            a += random.uniform(-0.5, 0.5)
            x += math.cos(a) * 0.11
            y += math.sin(a) * 0.11
            puff(x, y, 0.035, random.uniform(0.05, 0.09), LEAF, 6, 0.5)

elif KIND == "thistle":
    for _ in range(random.randint(5, 8)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.08)
        h = random.uniform(0.35, 0.6)
        stem(math.cos(a) * r, math.sin(a) * r, 0, h, 0.013, 0.05, LEAF_DRY)
        puff(math.cos(a) * r, math.sin(a) * r, h + 0.03, 0.045, FL, 7, 1.2)
    for _ in range(random.randint(8, 14)):
        a = random.uniform(0, 6.283)
        blade(0, 0, 0.02, random.uniform(0.14, 0.26), 0.03,
              random.uniform(0.7, 1.2), a, 0.5, LEAF_DRY)

elif KIND == "sapling":
    stem(0, 0, 0, random.uniform(0.9, 1.5), 0.035, 0.0, WOOD)
    for _ in range(random.randint(5, 9)):
        a = random.uniform(0, 6.283)
        z = random.uniform(0.45, 1.2)
        stem(0, 0, z, 0.3, 0.014, 0.5, WOOD)
        puff(math.cos(a) * 0.18, math.sin(a) * 0.18, z + 0.18,
             random.uniform(0.12, 0.2), LEAF, 7, 0.75)

elif KIND == "lavender":
    for _ in range(random.randint(14, 22)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.13)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = random.uniform(0.3, 0.5)
        stem(x, y, 0, h, 0.008, 0.08)
        for k in range(5):
            puff(x, y, h + k * 0.035, 0.022 - k * 0.002, (0.28, 0.18, 0.40), 6, 1.1)

elif KIND == "poppy":
    for _ in range(random.randint(7, 12)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.14)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = random.uniform(0.28, 0.46)
        stem(x, y, 0, h, 0.007, 0.12)
        petals(x, y, h + 0.015, 0.038, FL, 5)
        puff(x, y, h + 0.02, 0.012, (0.14, 0.12, 0.07), 5)
    for _ in range(random.randint(6, 10)):
        blade(0, 0, 0.01, random.uniform(0.1, 0.2), 0.022,
              random.uniform(0.8, 1.3), random.uniform(0, 3.1), 0.4)

elif KIND == "papyrus":
    for _ in range(random.randint(6, 10)):
        a = random.uniform(0, 6.283)
        r = random.uniform(0, 0.1)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = random.uniform(1.1, 1.8)
        stem(x, y, 0, h, 0.016, 0.04)
        for k in range(random.randint(14, 22)):
            aa = random.uniform(0, 6.283)
            blade(x, y, h, random.uniform(0.14, 0.24), 0.008,
                  random.uniform(1.1, 1.5), aa, 0.5)

else:                       # succulent
    for i in range(random.randint(10, 16)):
        a = i * 0.9
        r = 0.04 + i * 0.012
        puff(math.cos(a) * r, math.sin(a) * r, 0.03 + i * 0.008,
             random.uniform(0.05, 0.085), (0.18, 0.28, 0.17), 7, 0.6)


# --------------------------------------------------------------- assemble
# bake the tint into a vertex colour before joining, so one material serves all
for ob, tint in parts:
    me = ob.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    shade = random.uniform(0.82, 1.18)
    for i in range(len(col.data)):
        col.data[i].color = (tint[0] * shade * 2.5, tint[1] * shade * 2.5,
                             tint[2] * shade * 2.5, 1.0)

bpy.ops.object.select_all(action='DESELECT')
for ob, _t in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0][0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=0.4)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.86
bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
vc = nt.nodes.new('ShaderNodeVertexColor')
vc.layer_name = "ao"
nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
ob.data.materials.clear()
ob.data.materials.append(mat)

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%d verts=%d tris=%d" % (KIND, SEED, len(me.vertices), len(me.loop_triangles)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": []}, f)
print("WROTE", OUT)
