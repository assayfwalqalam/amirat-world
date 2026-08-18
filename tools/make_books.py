# Books in every posture, and the furniture that holds them. Covers are
# embossed leather; pages are plain -- never imitation script.
#   blender --background --python make_books.py -- <form> <out.glb> [assets]
# Forms: laid, pair, stack, row, shelfrow, case, open
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FORM = argv[0] if argv else "stack"
OUT = argv[1] if len(argv) > 1 else (FORM + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in FORM) * 271)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
covers, pages, woodp = [], [], []

COVER_TONES = [(0.30, 0.16, 0.10), (0.13, 0.20, 0.16), (0.24, 0.10, 0.10),
               (0.10, 0.12, 0.22), (0.28, 0.22, 0.10), (0.16, 0.10, 0.18)]


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def book_flat(x, y, z, w=None, d=None, t=None, rot=0.0):
    """One closed book lying flat: cover slightly proud of the page block."""
    w = w or random.uniform(0.20, 0.30)
    d = d or random.uniform(0.15, 0.22)
    t = t or random.uniform(0.035, 0.07)
    for dz, sx, sy, into in ((0, w, d, covers), (t / 2, w * 0.96, d * 0.94, pages),
                             (t, w, d, covers)):
        bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z + dz + (0.006 if into is covers else t / 2 - 0.006)))
        ob = bpy.context.active_object
        ob.scale = (sx / 2, sy / 2, (0.006 if into is covers else t / 2 - 0.006))
        ob.rotation_euler[2] = rot
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        into.append(ob)
    # the spine
    bpy.ops.mesh.primitive_cube_add(size=2, location=(x - math.cos(rot) * w / 2, y - math.sin(rot) * w / 2, z + t / 2))
    sp = bpy.context.active_object
    sp.scale = (0.008, d / 2, t / 2 + 0.004)
    sp.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    covers.append(sp)
    return t


def book_upright(x, y, z, h=None, d=None, t=None, lean=0.0):
    """One book standing, optionally leaning."""
    h = h or random.uniform(0.22, 0.30)
    d = d or random.uniform(0.16, 0.2)
    t = t or random.uniform(0.03, 0.06)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z + h / 2))
    ob = bpy.context.active_object
    ob.scale = (t / 2, d / 2, h / 2)
    ob.rotation_euler[1] = lean
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    covers.append(ob)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y + 0.004, z + h / 2))
    pg = bpy.context.active_object
    pg.scale = (t / 2 - 0.005, d / 2 - 0.004, h / 2 - 0.008)
    pg.rotation_euler[1] = lean
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    pages.append(pg)
    return t


def shelf_plank(x, y, z, w, d=0.26, t=0.035):
    bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z))
    ob = bpy.context.active_object
    ob.scale = (w / 2, d / 2, t / 2)
    bpy.ops.object.transform_apply(scale=True)
    woodp.append(ob)
    return ob


if FORM == "laid":
    book_flat(0, 0, 0)

elif FORM == "pair":
    t1 = book_flat(0, 0, 0)
    book_flat(0.05, 0.03, t1 + 0.002, rot=random.uniform(-0.3, 0.3))

elif FORM == "stack":
    z = 0.0
    for i in range(random.randint(4, 7)):
        t = book_flat(random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02), z,
                      rot=random.uniform(-0.25, 0.25))
        z += t + 0.004
    rec((0, 0, z / 2), 0.16, 0.13, z / 2)

elif FORM == "row":
    x = -0.5
    while x < 0.5:
        t = book_upright(x, 0, 0, lean=random.uniform(-0.06, 0.02))
        x += t + 0.006
    # the last few lean over against nothing
    book_upright(x + 0.02, 0, 0, lean=-0.35)
    rec((0, 0, 0.14), 0.56, 0.12, 0.14)

elif FORM == "shelfrow":
    shelf_plank(0, 0, -0.02, 1.3)
    x = -0.6
    while x < 0.55:
        t = book_upright(x, 0, 0, lean=random.uniform(-0.05, 0.02))
        x += t + random.uniform(0.004, 0.05)
    rec((0, 0, 0.16), 0.66, 0.14, 0.18)

elif FORM == "case":
    W, H, D = 1.5, 2.1, 0.34
    for sx in (-1, 1):                                # sides
        shelf_plank(sx * W / 2, 0, H / 2, 0.05, D, H)
    shelf_plank(0, 0, H - 0.02, W, D, 0.05)           # top
    shelf_plank(0, 0.02, H / 2, W, 0.03, H)           # back
    woodp[-1].location.y = D / 2 - 0.015
    bpy.ops.object.transform_apply(location=True)
    nshelf = 4
    for i in range(nshelf + 1):
        z = 0.05 + i * (H - 0.2) / nshelf
        shelf_plank(0, 0, z, W - 0.06, D - 0.04)
        if i < nshelf:
            x = -W / 2 + 0.09
            while x < W / 2 - 0.12:
                if random.random() < 0.12:            # a gap on the shelf
                    x += random.uniform(0.05, 0.14)
                    continue
                t = book_upright(x, 0, z + 0.02,
                                 h=random.uniform(0.2, 0.32),
                                 lean=random.uniform(-0.05, 0.02))
                x += t + 0.006
            if random.random() < 0.5:                 # some lie flat on top
                book_flat(random.uniform(-W / 3, W / 3), 0, z + 0.02,
                          rot=random.uniform(-0.2, 0.2))
    rec((0, 0, H / 2), W / 2, D / 2, H / 2)

else:                       # open: a book lying open, pages fanned
    W, D = 0.34, 0.24
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=2, location=(sx * W / 4, 0, 0.012))
        c = bpy.context.active_object
        c.scale = (W / 4, D / 2, 0.01)
        c.rotation_euler[1] = -sx * 0.09
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        covers.append(c)
    for i in range(7):                               # the fan of leaves
        k = i / 6.0
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_cube_add(
                size=2, location=(sx * (W / 4 - 0.004), 0, 0.022 + i * 0.004))
            pgl = bpy.context.active_object
            pgl.scale = (W / 4 - 0.01, D / 2 - 0.012, 0.0016)
            pgl.rotation_euler[1] = -sx * (0.09 - k * 0.07)
            bpy.ops.object.transform_apply(scale=True, rotation=True)
            pages.append(pgl)


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
    bpy.ops.uv.cube_project(cube_size=0.3)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


cov = join_group(covers, "covers")
if cov:
    # per-face cover tones over the embossed leather
    me = cov.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    import collections
    tone_by_island = {}
    for poly in me.polygons:
        key = poly.index // 7
        if key not in tone_by_island:
            tone_by_island[key] = random.choice(COVER_TONES)
        t = tone_by_island[key]
        for li in poly.loop_indices:
            col.data[li].color = (t[0] * 3.2, t[1] * 3.2, t[2] * 3.2, 1.0)
    m = bpy.data.materials.new("cover")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.7
    path = os.path.abspath(os.path.join(ASSETS, "t_leather_d.jpg"))
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
    cov.data.materials.clear()
    cov.data.materials.append(m)

pg = join_group(pages, "pages")
if pg:
    m2 = bpy.data.materials.new("pages")
    m2.use_nodes = True
    b2 = m2.node_tree.nodes["Principled BSDF"]
    b2.inputs["Base Color"].default_value = (0.78, 0.72, 0.58, 1)
    b2.inputs["Roughness"].default_value = 0.95
    pg.data.materials.clear()
    pg.data.materials.append(m2)

wd = join_group(woodp, "wood")
if wd:
    m3 = bpy.data.materials.new("wood")
    m3.use_nodes = True
    nt3 = m3.node_tree
    b3 = nt3.nodes["Principled BSDF"]
    b3.inputs["Roughness"].default_value = 0.92
    path = os.path.abspath(os.path.join(ASSETS, "t_woodp_d.jpg"))
    if os.path.exists(path):
        img = bpy.data.images.load(path)
        tn3 = nt3.nodes.new('ShaderNodeTexImage')
        tn3.image = img
        nt3.links.new(tn3.outputs['Color'], b3.inputs['Base Color'])
        img.pack()
    wd.data.materials.clear()
    wd.data.materials.append(m3)

bpy.ops.object.select_all(action='DESELECT')
for o in (cov, pg, wd):
    if o:
        o.select_set(True)
bpy.context.view_layer.objects.active = cov or pg or wd
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = FORM

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d" % (FORM, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))
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
