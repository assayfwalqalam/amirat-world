# The neighborhood mosque: a modest prayer hall, a small dome over the
# mihrab bay, a short minaret at one corner, and a low walled court.
# Adobe walls like the houses round it; the dome and minaret cap in plaster.
#   blender --background --python make_mosque_small.py -- <seed> <out.glb> [assets]
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SEED = int(argv[0]) if argv else 1
OUT = argv[1] if len(argv) > 1 else "mosque_small.glb"
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(SEED * 3391 + 17)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12

COLLIDERS = []
mud, plaster = [], []

# hall footprint; the court continues south of it
HW = random.uniform(9.0, 11.0)      # width (x)
HD = random.uniform(6.5, 7.5)       # depth (y)
HH = random.uniform(4.2, 4.8)       # wall height
T = 0.55                            # wall thickness
CW = HW                             # court same width
CD = random.uniform(5.5, 7.0)       # court depth
CH = 2.0                            # court wall height


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def solid(sx, sy, sz, loc, into=None, collide=True):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    (into if into is not None else mud).append(ob)
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


def arch_cut(target, w, h, loc, along='y'):
    """A doorway with a round head, cut straight through."""
    sx, sy = (w, T * 3) if along == 'y' else (T * 3, w)
    cut(target, sx, sy, h - w / 2, (loc[0], loc[1], loc[2] + (h - w / 2) / 2))
    bpy.ops.mesh.primitive_cylinder_add(
        radius=w / 2, depth=T * 3, location=(loc[0], loc[1], loc[2] + h - w / 2),
        rotation=(math.pi / 2, 0, 0) if along == 'y' else (0, math.pi / 2, 0),
        vertices=20)
    c = bpy.context.active_object
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = c
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)


# ------------------------------------------------------------- the hall
# hollow box: outer minus inner; qibla wall is +y (mihrab bulges out of it)
hall = solid(HW, HD, HH, (0, 0, HH / 2))
cut(hall, HW - 2 * T, HD - 2 * T, HH, (0, 0, HH / 2 + 0.12))
# the south door from the court into the hall
arch_cut(hall, 1.5, 2.5, (0, -HD / 2, 0.0), 'y')
# two window slots each side, one sill height
for sx in (-1, 1):
    for wx in (-HW * 0.28, HW * 0.28):
        cut(hall, 1.0, T * 3, 1.25, (wx, sx * (HD / 2), 1.7 + 1.25 / 2))
# the mihrab: a half-drum niche bulging from the qibla wall
bpy.ops.mesh.primitive_cylinder_add(radius=0.9, depth=2.6,
                                    location=(0, HD / 2, 1.3), vertices=16)
nich = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.object.mode_set(mode='OBJECT')
mud.append(nich)
rec((0, HD / 2 + 0.45, 1.3), 0.5, 0.5, 1.3)
# hollow the niche toward the hall
cut(nich, 1.3, 1.6, 2.2, (0, HD / 2 - 0.5, 1.1))

# roof slab with a low parapet
roof = solid(HW, HD, 0.35, (0, 0, HH + 0.175), collide=False)
rec((0, 0, HH + 0.175), HW / 2, HD / 2, 0.35)
para = solid(HW + 0.15, HD + 0.15, 0.7, (0, 0, HH + 0.35 + 0.35), collide=False)
cut(para, HW - 0.55, HD - 0.55, 1.2, (0, 0, HH + 0.7))

# the dome over the mihrab bay: a drum and a squashed hemisphere, plastered
DR = random.uniform(1.6, 1.9)
bpy.ops.mesh.primitive_cylinder_add(radius=DR + 0.15, depth=0.8,
                                    location=(0, HD / 2 - DR - T, HH + 0.75), vertices=22)
plaster.append(bpy.context.active_object)
bpy.ops.mesh.primitive_uv_sphere_add(radius=DR, segments=22, ring_count=12,
                                     location=(0, HD / 2 - DR - T, HH + 1.15))
dm = bpy.context.active_object
for v in dm.data.vertices:
    if v.co.z < 0:
        v.co.z = 0
    else:
        v.co.z *= 1.06
plaster.append(dm)
bpy.ops.mesh.primitive_cone_add(radius1=0.1, radius2=0.0, depth=1.1,
                                location=(0, HD / 2 - DR - T, HH + 1.15 + DR * 1.06 + 0.5),
                                vertices=8)
plaster.append(bpy.context.active_object)

# ------------------------------------------------------------- the court
cy = -HD / 2 - CD / 2                      # court centre y
for sxn in (-1, 1):                        # east and west court walls
    w = solid(T, CD, CH, (sxn * (CW / 2 - T / 2), cy, CH / 2))
front = solid(CW, T, CH, (0, cy - CD / 2 + T / 2, CH / 2))
arch_cut(front, 1.4, 2.0, (random.choice((-1, 1)) * CW * 0.2, cy - CD / 2 + T / 2, 0), 'y')
# a small ablution basin in the court
b = solid(1.7, 1.2, 0.5, (CW * 0.24, cy, 0.25))
cut(b, 1.4, 0.9, 0.4, (CW * 0.24, cy, 0.42))

# ------------------------------------------------------------- the minaret
# short square shaft at the hall's SW corner, small gallery, plaster cap
MX, MY = -HW / 2 + 0.9, -HD / 2 + 0.9
MH = random.uniform(8.5, 10.5)
sh = solid(1.7, 1.7, MH, (MX, MY, MH / 2))
cut(sh, 0.6, T * 3, 1.5, (MX, MY - 0.85, 1.1))          # a slot door
solid(2.1, 2.1, 0.35, (MX, MY, MH + 0.17), collide=False)
gal = solid(1.35, 1.35, 1.7, (MX, MY, MH + 0.35 + 0.85))
for f in range(4):
    a = f * math.pi / 2
    cut(gal, 0.5 if f % 2 == 0 else 2.2, 2.2 if f % 2 == 0 else 0.5, 1.0,
        (MX, MY, MH + 1.15))
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.85, segments=16, ring_count=9,
                                     location=(MX, MY, MH + 2.1))
cap = bpy.context.active_object
for v in cap.data.vertices:
    if v.co.z < 0:
        v.co.z = 0
    else:
        v.co.z *= 1.12
plaster.append(cap)
bpy.ops.mesh.primitive_cone_add(radius1=0.08, radius2=0.0, depth=1.0,
                                location=(MX, MY, MH + 2.1 + 0.85 * 1.12 + 0.45), vertices=8)
plaster.append(bpy.context.active_object)


# ------------------------------------------------------------- materials
def join_group(objs, name, csize):
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
    bpy.ops.mesh.remove_doubles(threshold=0.0008)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cube_project(cube_size=csize)
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


mud_ob = join_group(mud, "mud", 2.6)
m = bpy.data.materials.new("adobe")
m.use_nodes = True
nt = m.node_tree
b1 = nt.nodes["Principled BSDF"]
b1.inputs["Roughness"].default_value = 1.0
variant = ["t_adobe_d.jpg", "t_adobe3_d.jpg"][SEED % 2]
path = os.path.abspath(os.path.join(ASSETS, variant))
if os.path.exists(path):
    img = bpy.data.images.load(path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], b1.inputs['Base Color'])
    img.pack()
np = os.path.abspath(os.path.join(ASSETS, "t_adobe_gn.jpg"))
if os.path.exists(np):
    nimg = bpy.data.images.load(np)
    nimg.colorspace_settings.name = 'Non-Color'
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nimg
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = 1.2
    nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], b1.inputs['Normal'])
    nimg.pack()
mud_ob.data.materials.clear()
mud_ob.data.materials.append(m)

pl_ob = join_group(plaster, "plaster", 1.8)
if pl_ob:
    bpy.ops.object.shade_smooth()
    es = pl_ob.modifiers.new("es", 'EDGE_SPLIT')
    es.use_edge_angle = True
    es.split_angle = math.radians(38)
    bpy.ops.object.modifier_apply(modifier=es.name)
    m2 = bpy.data.materials.new("plaster")
    m2.use_nodes = True
    nt2 = m2.node_tree
    b2 = nt2.nodes["Principled BSDF"]
    b2.inputs["Roughness"].default_value = 0.9
    path2 = os.path.abspath(os.path.join(ASSETS, "t_plaster_d.jpg"))
    if os.path.exists(path2):
        img2 = bpy.data.images.load(path2)
        tn2 = nt2.nodes.new('ShaderNodeTexImage')
        tn2.image = img2
        nt2.links.new(tn2.outputs['Color'], b2.inputs['Base Color'])
        img2.pack()
    else:
        b2.inputs["Base Color"].default_value = (0.72, 0.68, 0.60, 1)
    pl_ob.data.materials.clear()
    pl_ob.data.materials.append(m2)

bpy.ops.object.select_all(action='DESELECT')
for o in (mud_ob, pl_ob):
    if o:
        o.select_set(True)
bpy.context.view_layer.objects.active = mud_ob
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "mosque_small"

me = ob.data
me.calc_loop_triangles()
print("RESULT mosque_small/%d verts=%d tris=%d colliders=%d"
      % (SEED, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
