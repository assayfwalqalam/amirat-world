# Pottery: many vessel forms, each turned from its own profile.
#   blender --background --python make_pottery.py -- <form> <out.glb> [assets]
#
# Forms: amphora, jar, squat, jug, storage, bowl, deepbowl, plate, oiljar,
#        flask, krater, cookpot, pitcher, urn, basin, cup
#
# Each is a real silhouette spun round the axis, not a sphere with a neck stuck
# on it. That is what makes a shelf of pots read as a potter's work rather than
# as the same object at different sizes. Wheel rings, a little lean and an
# uneven rim are added afterwards, because nothing thrown by hand is true.
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FORM = argv[0] if argv else "jar"
OUT = argv[1] if len(argv) > 1 else (FORM + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in FORM) * 6151)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
parts = []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


# (radius, height) up the side. The last point closes the rim.
PROFILES = {
    # tall, shouldered, narrow foot: for oil and wine
    "amphora":  [(0.05, 0.0), (0.10, 0.05), (0.17, 0.18), (0.22, 0.40), (0.21, 0.58),
                 (0.15, 0.74), (0.09, 0.84), (0.08, 0.92), (0.11, 0.98), (0.10, 1.02)],
    # the everyday storage jar
    "jar":      [(0.09, 0.0), (0.15, 0.04), (0.21, 0.16), (0.24, 0.34), (0.22, 0.50),
                 (0.16, 0.62), (0.13, 0.70), (0.15, 0.75), (0.14, 0.78)],
    # low and wide
    "squat":    [(0.11, 0.0), (0.18, 0.03), (0.25, 0.12), (0.27, 0.24), (0.24, 0.34),
                 (0.18, 0.41), (0.16, 0.45), (0.18, 0.49), (0.17, 0.52)],
    # water jug, long neck
    "jug":      [(0.07, 0.0), (0.12, 0.03), (0.18, 0.14), (0.20, 0.28), (0.17, 0.40),
                 (0.10, 0.50), (0.07, 0.62), (0.07, 0.76), (0.10, 0.82), (0.09, 0.85)],
    # big-bellied store, waist high
    "storage":  [(0.14, 0.0), (0.24, 0.05), (0.34, 0.22), (0.38, 0.46), (0.35, 0.68),
                 (0.27, 0.84), (0.22, 0.92), (0.25, 0.97), (0.24, 1.0)],
    "bowl":     [(0.06, 0.0), (0.11, 0.02), (0.18, 0.07), (0.23, 0.14), (0.25, 0.20),
                 (0.25, 0.22)],
    "deepbowl": [(0.07, 0.0), (0.13, 0.03), (0.20, 0.12), (0.24, 0.24), (0.25, 0.34),
                 (0.24, 0.38)],
    "plate":    [(0.07, 0.0), (0.13, 0.015), (0.22, 0.03), (0.30, 0.06), (0.33, 0.10),
                 (0.33, 0.11)],
    # squat, wide mouth, for oil
    "oiljar":   [(0.10, 0.0), (0.17, 0.04), (0.23, 0.14), (0.24, 0.26), (0.20, 0.36),
                 (0.17, 0.42), (0.19, 0.46), (0.18, 0.48)],
    # round body, very narrow neck
    "flask":    [(0.06, 0.0), (0.11, 0.03), (0.17, 0.12), (0.19, 0.24), (0.16, 0.34),
                 (0.08, 0.40), (0.05, 0.50), (0.07, 0.54), (0.06, 0.56)],
    # wide open mixing vessel on a foot
    "krater":   [(0.09, 0.0), (0.12, 0.04), (0.09, 0.10), (0.14, 0.16), (0.22, 0.26),
                 (0.28, 0.40), (0.30, 0.50), (0.29, 0.54)],
    "cookpot":  [(0.10, 0.0), (0.16, 0.03), (0.21, 0.10), (0.22, 0.20), (0.19, 0.28),
                 (0.18, 0.32), (0.20, 0.34), (0.19, 0.36)],
    "pitcher":  [(0.08, 0.0), (0.13, 0.03), (0.17, 0.12), (0.18, 0.26), (0.15, 0.38),
                 (0.12, 0.48), (0.11, 0.58), (0.14, 0.63), (0.13, 0.66)],
    "urn":      [(0.12, 0.0), (0.16, 0.06), (0.13, 0.13), (0.20, 0.22), (0.28, 0.38),
                 (0.30, 0.54), (0.26, 0.68), (0.21, 0.76), (0.24, 0.81), (0.23, 0.84)],
    "basin":    [(0.14, 0.0), (0.24, 0.03), (0.34, 0.09), (0.40, 0.17), (0.42, 0.24),
                 (0.42, 0.26)],
    "cup":      [(0.04, 0.0), (0.06, 0.02), (0.08, 0.06), (0.09, 0.12), (0.09, 0.15)],
}

PROF = PROFILES.get(FORM, PROFILES["jar"])
SCALE = {"storage": 1.0, "amphora": 1.0, "basin": 1.0}.get(FORM, 1.0)
SEG = 20


def lathe(profile, segments=SEG, thickness=0.016):
    """Spin a silhouette round the axis and give the wall a thickness."""
    me = bpy.data.meshes.new(FORM)
    ob = bpy.data.objects.new(FORM, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i + 1]))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], axis=(0, 0, 1),
                   cent=(0, 0, 0), dvec=(0, 0, 0), angle=math.pi * 2,
                   steps=segments, use_merge=True)
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = thickness
    sol.offset = 1.0
    bpy.ops.object.modifier_apply(modifier=sol.name)
    parts.append(ob)
    return ob


pot = lathe(PROF)

# wheel rings: a faint ridging round the body, the mark of throwing
for v in pot.data.vertices:
    r = math.hypot(v.co.x, v.co.y)
    if r > 0.002:
        ring = math.sin(v.co.z * 62.0) * 0.0035 + math.sin(v.co.z * 23.0) * 0.0022
        k = (r + ring) / r
        v.co.x *= k
        v.co.y *= k

# nothing thrown by hand is true: lean the whole thing and rough the rim
top_z = PROF[-1][1]
for v in pot.data.vertices:
    t = v.co.z / max(0.01, top_z)
    v.co.x += random.uniform(-0.004, 0.004) + 0.012 * t
    v.co.y += random.uniform(-0.004, 0.004)
    if v.co.z > top_z * 0.93:
        v.co.z += random.uniform(-0.008, 0.008)

bpy.context.view_layer.objects.active = pot
bpy.ops.object.shade_smooth()
es = pot.modifiers.new("es", 'EDGE_SPLIT')
es.use_edge_angle = True
es.split_angle = math.radians(46)
bpy.ops.object.modifier_apply(modifier=es.name)

# handles, where the form calls for them
def handle(z0, z1, r_at, thick=0.018, out=0.055):
    n = 7
    prev = None
    for i in range(n + 1):
        t = i / float(n)
        z = z0 + (z1 - z0) * t
        bulge = math.sin(t * math.pi) * out
        bpy.ops.mesh.primitive_uv_sphere_add(radius=thick, location=(r_at + bulge, 0, z),
                                             segments=7, ring_count=5)
        parts.append(bpy.context.active_object)


if FORM in ("amphora", "urn", "krater"):
    for a in (0, math.pi):
        bpy.ops.object.select_all(action='DESELECT')
        zs = (top_z * 0.55, top_z * 0.92)
        n = 7
        for i in range(n + 1):
            t = i / float(n)
            z = zs[0] + (zs[1] - zs[0]) * t
            bulge = math.sin(t * math.pi) * 0.07
            rr = 0.14 + bulge
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.019, location=(math.cos(a) * rr, math.sin(a) * rr, z),
                segments=7, ring_count=5)
            parts.append(bpy.context.active_object)
elif FORM in ("jug", "pitcher"):
    zs = (top_z * 0.42, top_z * 0.9)
    n = 8
    for i in range(n + 1):
        t = i / float(n)
        z = zs[0] + (zs[1] - zs[0]) * t
        rr = 0.13 + math.sin(t * math.pi) * 0.075
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.017, location=(rr, 0, z),
                                             segments=7, ring_count=5)
        parts.append(bpy.context.active_object)
    # a pouring lip
    bpy.ops.mesh.primitive_cone_add(radius1=0.045, radius2=0.02, depth=0.07,
                                    location=(-0.09, 0, top_z + 0.005), vertices=8)
    lip = bpy.context.active_object
    lip.rotation_euler = (0, -0.7, 0)
    bpy.ops.object.transform_apply(rotation=True)
    parts.append(lip)

maxr = max(r for r, _z in PROF)
rec((0, 0, top_z / 2), maxr * 0.9, maxr * 0.9, top_z / 2)

# ------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = FORM
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0025)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=0.35)
bpy.ops.object.mode_set(mode='OBJECT')

# Clay comes out of the ground in different colours, and a glaze changes it
# again. Each form gets its own so a shelf of them is not one colour repeated.
TINT = {
    "amphora":  (0.40, 0.24, 0.15),   # red earthenware
    "jar":      (0.46, 0.30, 0.19),   # buff
    "squat":    (0.34, 0.20, 0.14),
    "jug":      (0.50, 0.36, 0.24),   # pale desert clay
    "storage":  (0.36, 0.23, 0.15),
    "bowl":     (0.44, 0.27, 0.17),
    "deepbowl": (0.30, 0.19, 0.13),
    "plate":    (0.52, 0.40, 0.27),
    "oiljar":   (0.26, 0.17, 0.12),   # near black, pitch-sealed
    "flask":    (0.13, 0.19, 0.22),   # blue-green glaze
    "krater":   (0.15, 0.21, 0.24),
    "cookpot":  (0.19, 0.14, 0.11),   # sooted
    "pitcher":  (0.42, 0.28, 0.18),
    "urn":      (0.33, 0.22, 0.16),
    "basin":    (0.47, 0.34, 0.22),
    "cup":      (0.20, 0.24, 0.25),
}.get(FORM, (0.42, 0.27, 0.17))

mat = bpy.data.materials.new(FORM)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (TINT[0], TINT[1], TINT[2], 1)
# glazed wares catch a highlight; unglazed earthenware does not
glazed = FORM in ("flask", "krater", "cup", "plate")
bsdf.inputs["Roughness"].default_value = 0.42 if glazed else 0.88
tex_path = os.path.abspath(os.path.join(ASSETS, "t_clay_d.jpg"))
tn = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    mixc = nt.nodes.new('ShaderNodeMixRGB')
    mixc.blend_type = 'MULTIPLY'
    mixc.inputs['Fac'].default_value = 1.0
    mixc.inputs['Color2'].default_value = (TINT[0] * 2.4, TINT[1] * 2.4, TINT[2] * 2.4, 1)
    nt.links.new(tn.outputs['Color'], mixc.inputs['Color1'])
    nt.links.new(mixc.outputs['Color'], bsdf.inputs['Base Color'])

ob.data.materials.clear()
ob.data.materials.append(mat)

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
        ao = 0.38 + 0.60 * data[i].color[0]
        data[i].color = (ao, ao, ao, 1.0)
except Exception as e:
    print("bake failed:", e)

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d"
      % (FORM, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

if tn is not None:
    tn.image.pack()
    vcn = nt.nodes.new('ShaderNodeVertexColor')
    vcn.layer_name = "ao"
    mixa = nt.nodes.new('ShaderNodeMixRGB')
    mixa.blend_type = 'MULTIPLY'
    mixa.inputs['Fac'].default_value = 1.0
    nt.links.new(mixc.outputs['Color'], mixa.inputs['Color1'])
    nt.links.new(vcn.outputs['Color'], mixa.inputs['Color2'])
    nt.links.new(mixa.outputs['Color'], bsdf.inputs['Base Color'])

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
