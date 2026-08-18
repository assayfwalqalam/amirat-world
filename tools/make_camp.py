# The camp pack: goat-hair tents, a fire ring, a rock shelter. Cloth sags
# between poles the way real tents do; nothing lives inside. Aniconic.
#   blender --background --python make_camp.py -- <kind> <out.glb> [assets]
# Kinds: tent_long, tent_round, firering, shelter
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "tent_long"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 911)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
cloth, wood, stone = [], [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def pole(x, y, h, r=0.05, lean=(0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(x + lean[0] * h / 2, y + lean[1] * h / 2, h / 2), vertices=8)
    ob = bpy.context.active_object
    ob.rotation_euler = (math.atan2(lean[1], 1) * 0.9, math.atan2(-lean[0], 1) * 0.9, 0)
    bpy.ops.object.transform_apply(rotation=True)
    wood.append(ob)
    return ob


if KIND == "tent_long":
    # the black-tent: a wide rectangle of cloth over a ridgeline, sides guyed out
    LX, LY = 5.2, 3.6
    RH, EH = 2.1, 0.9                        # ridge height, eave height
    me = bpy.data.meshes.new("cloth")
    ob = bpy.data.objects.new("cloth", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    NX, NY = 22, 16
    grid = {}
    for ix in range(NX + 1):
        for iy in range(NY + 1):
            u, v = ix / NX, iy / NY
            x = (u - 0.5) * LX
            y = (v - 0.5) * LY
            # a ridge along x=0? no: ridge runs along the LONG axis at y=0
            t = abs(v - 0.5) * 2               # 0 at ridge, 1 at eaves
            z = RH - (RH - EH) * (t ** 0.85)
            # cloth sags between the pole stations
            sag = 0.16 * math.sin(u * math.pi * 4) ** 2 * (0.35 + 0.65 * t)
            z -= sag
            # the back long side drops as a wall almost to the ground
            if v > 0.90:
                k = (v - 0.90) / 0.10
                z = z * (1 - k) + 0.18 * k
            z += random.uniform(-0.015, 0.015)
            grid[(ix, iy)] = bm.verts.new((x, y, z))
    for ix in range(NX):
        for iy in range(NY):
            bm.faces.new((grid[(ix, iy)], grid[(ix + 1, iy)],
                          grid[(ix + 1, iy + 1)], grid[(ix, iy + 1)]))
    bm.to_mesh(me)
    bm.free()
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.03
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=sol.name)
    cloth.append(ob)
    # ridge poles inside, eave poles at the corners leaning out
    for u in (-0.33, 0.0, 0.33):
        pole(u * LX, 0, RH - 0.03, 0.06)
    for sx in (-1, 1):
        for sy in (-1, 1):
            pole(sx * (LX / 2 - 0.25), sy * (LY / 2 - 0.1), EH + 0.12, 0.045,
                 (sx * 0.12, sy * 0.16))
    # you can walk in: only the poles and the back wall block
    for u in (-0.33, 0.0, 0.33):
        rec((u * LX, 0, 1.0), 0.1, 0.1, 1.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rec((sx * (LX / 2 - 0.2), sy * (LY / 2 - 0.08), 0.5), 0.1, 0.1, 0.5)
    rec((0, LY / 2 - 0.02, 0.8), LX / 2, 0.06, 0.8)

elif KIND == "tent_round":
    # a conical tent: cloth cone with a wavering hem, one centre pole
    R, H = 2.3, 2.5
    me = bpy.data.meshes.new("cloth")
    ob = bpy.data.objects.new("cloth", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    N, RINGS = 26, 7
    top = bm.verts.new((0, 0, H))
    rings = []
    for ir in range(1, RINGS + 1):
        t = ir / RINGS
        ring = []
        for i in range(N):
            a = i / N * 2 * math.pi
            rr = R * (t ** 1.08)
            hem = 0.12 * math.sin(a * 5 + t * 2) * t ** 2
            sag = 0.10 * math.sin(a * 9) ** 2 * t
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr,
                                      H * (1 - t) + hem - sag)))
        rings.append(ring)
    for i in range(N):
        bm.faces.new((top, rings[0][i], rings[0][(i + 1) % N]))
    for ir in range(RINGS - 1):
        for i in range(N):
            bm.faces.new((rings[ir][i], rings[ir + 1][i],
                          rings[ir + 1][(i + 1) % N], rings[ir][(i + 1) % N]))
    bm.to_mesh(me)
    bm.free()
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.03
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=sol.name)
    # a door slit: carve a wedge out of one side at the hem
    cutter = bpy.ops.mesh.primitive_cube_add(size=2, location=(R * 0.92, 0, 0.55))
    c = bpy.context.active_object
    c.scale = (0.5, 0.42, 0.55)
    bpy.ops.object.transform_apply(scale=True)
    m = ob.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)
    cloth.append(ob)
    pole(0, 0, H - 0.02, 0.06)
    # a C of wall round the door (door faces +x): centre pole and three sides
    rec((0, 0, 1.1), 0.1, 0.1, 1.1)
    rec((-R * 0.72, 0, 0.8), 0.14, R * 0.62, 0.8)
    for sy in (-1, 1):
        rec((0.1, sy * R * 0.72, 0.8), R * 0.55, 0.14, 0.8)

elif KIND == "firering":
    # a ring of stones round scorched ground and charred sticks
    for i in range(11):
        a = i / 11 * 2 * math.pi + random.uniform(-0.1, 0.1)
        r = 0.62 + random.uniform(-0.05, 0.05)
        bpy.ops.mesh.primitive_ico_sphere_add(
            radius=random.uniform(0.10, 0.16),
            location=(math.cos(a) * r, math.sin(a) * r, 0.07), subdivisions=1)
        ob = bpy.context.active_object
        ob.scale = (1, random.uniform(0.7, 1.0), random.uniform(0.55, 0.75))
        ob.rotation_euler[2] = random.uniform(0, 3)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        stone.append(ob)
    for i in range(5):                          # charred wood
        a = random.uniform(0, 6.3)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.045, depth=random.uniform(0.5, 0.7),
            location=(random.uniform(-0.14, 0.14), random.uniform(-0.14, 0.14), 0.10),
            rotation=(math.pi / 2 + random.uniform(-0.2, 0.35), 0, a), vertices=7)
        wood.append(bpy.context.active_object)
    rec((0, 0, 0.12), 0.8, 0.8, 0.12)

else:                       # shelter: a leaning slab of rock over a hollow
    bpy.ops.mesh.primitive_ico_sphere_add(radius=2.4, location=(0, 0, 0.9), subdivisions=3)
    ob = bpy.context.active_object
    for v in ob.data.vertices:
        v.co.z *= 0.62
        v.co.x *= 1.25
        v.co.x += random.uniform(-0.06, 0.06)
        v.co.y += random.uniform(-0.06, 0.06)
        v.co.z += random.uniform(-0.05, 0.05)
    # hollow the front out
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.8, location=(2.0, 0, 0.7),
                                         segments=14, ring_count=9)
    c = bpy.context.active_object
    c.scale = (1.3, 0.95, 0.75)
    bpy.ops.object.transform_apply(scale=True)
    m = ob.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)
    stone.append(ob)
    rec((-0.9, 0, 0.9), 1.4, 1.9, 0.9)


# ------------------------------------------------------------- materials
def join_group(objs, name, csize=1.4):
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
    bpy.ops.uv.cube_project(cube_size=csize)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def tex_mat(ob, name, texfile, tint, rough=0.95, lift=2.2):
    """Texture times a painted vertex tint -- the one graph the exporter keeps."""
    me = ob.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for i in range(len(col.data)):
        col.data[i].color = (min(1.0, tint[0] * lift), min(1.0, tint[1] * lift),
                             min(1.0, tint[2] * lift), 1.0)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    path = os.path.abspath(os.path.join(ASSETS, texfile))
    if os.path.exists(path):
        img = bpy.data.images.load(path)
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = img
        vcn = nt.nodes.new('ShaderNodeVertexColor')
        vcn.layer_name = "ao"
        mix = nt.nodes.new('ShaderNodeMixRGB')
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Fac'].default_value = 1.0
        nt.links.new(tn.outputs['Color'], mix.inputs['Color1'])
        nt.links.new(vcn.outputs['Color'], mix.inputs['Color2'])
        nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
        img.pack()
    else:
        b.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1)
    return m


parts = []
cl = join_group(cloth, "cloth", 1.2)
if cl:
    cl.data.materials.clear()
    # goat-hair cloth: the cloth texture darkened towards near-black-brown
    cl.data.materials.append(tex_mat(cl, "hair", "t_cloth_d.jpg", (0.17, 0.135, 0.11)))
    parts.append(cl)
wd = join_group(wood, "wood", 0.9)
if wd:
    wd.data.materials.clear()
    tintw = (0.10, 0.085, 0.07) if KIND == "firering" else (0.42, 0.35, 0.27)
    wd.data.materials.append(tex_mat(wd, "wood", "t_woodp_d.jpg", tintw))
    parts.append(wd)
st = join_group(stone, "stone", 1.8)
if st:
    bpy.ops.object.shade_smooth()
    es = st.modifiers.new("es", 'EDGE_SPLIT')
    es.use_edge_angle = True
    es.split_angle = math.radians(34)
    bpy.context.view_layer.objects.active = st
    bpy.ops.object.modifier_apply(modifier=es.name)
    st.data.materials.clear()
    st.data.materials.append(tex_mat(st, "rock", "g_rock_d.jpg", (0.42, 0.41, 0.40)))
    parts.append(st)

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
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
