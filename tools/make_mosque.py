# The friday mosque: a domed prayer hall behind an arcaded courtyard, with a
# minaret. Built the same way as the houses, so the town is one hand.
#   blender --background --python make_mosque.py -- <out.glb> [assets_dir]
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "mosque.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"
random.seed(77)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
SPOTS = []
parts = []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def box(sx, sy, sz, loc, rot=0.0, collide=True):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    parts.append(ob)
    return ob


def cyl(r1, r2, h, loc, rot=(0, 0, 0), verts=20, collide=False):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    if collide:
        rec(loc, max(r1, r2) * 0.86, max(r1, r2) * 0.86, h / 2)
    parts.append(ob)
    return ob


def dome(r, loc, seg=26):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    ob = bpy.context.active_object
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for v in ob.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
        else:
            v.co.z *= 1.12
    parts.append(ob)
    return ob


def box_rot(sx, sy, sz, loc, euler, collide=False):
    """A box that is pitched and yawed in one go. Applying a yaw first and a
       pitch afterwards puts the stone in the wrong place on the side runs."""
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler = euler
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    parts.append(ob)
    return ob


def cut(target, cutter):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    if cutter in parts:
        parts.remove(cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)


def weld(ob):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0006)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=2, fine=0.035, broad=0.055):
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    weld(ob)
    for sc, st in ((1.3, fine), (4.0, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = sc
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = st
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)


def arch_opening(target, cx, cy, cz, w, h, through, axis='y'):
    """A round-headed opening cut clean through."""
    if axis == 'y':
        c1 = box(w, through, h - w / 2, (cx, cy, cz + (h - w / 2) / 2), 0, False)
        cut(target, c1)
        c2 = cyl(w / 2, w / 2, through, (cx, cy, cz + h - w / 2), rot=(math.pi / 2, 0, 0), verts=18)
        cut(target, c2)
    else:
        c1 = box(through, w, h - w / 2, (cx, cy, cz + (h - w / 2) / 2), 0, False)
        cut(target, c1)
        c2 = cyl(w / 2, w / 2, through, (cx, cy, cz + h - w / 2), rot=(0, math.pi / 2, 0), verts=18)
        cut(target, c2)


# ------------------------------------------------------------ the hall
HW, HD, HH, T = 26.0, 24.0, 11.5, 1.1
back = box(HW, T, HH, (0, HD / 2 - T / 2, HH / 2))
left = box(T, HD - T * 2, HH, (-HW / 2 + T / 2, 0, HH / 2))
right = box(T, HD - T * 2, HH, (HW / 2 - T / 2, 0, HH / 2))
front = box(HW, T, HH, (0, -HD / 2 + T / 2, HH / 2))
for w in (back, left, right, front):
    erode(w)

# the great door, and windows down both flanks
arch_opening(front, 0, -HD / 2 + T / 2, 0, 4.2, 6.4, T + 2.2, 'y')
for i in (-1, 1):
    arch_opening(front, i * 8.4, -HD / 2 + T / 2, 4.2, 1.5, 3.0, T + 2.2, 'y')
for i in (-1, 0, 1):
    arch_opening(left, -HW / 2 + T / 2, i * 6.4, 4.6, 1.5, 3.2, T + 2.2, 'x')
    arch_opening(right, HW / 2 - T / 2, i * 6.4, 4.6, 1.5, 3.2, T + 2.2, 'x')
# the mihrab niche in the qibla wall, and a window either side
arch_opening(back, 0, HD / 2 - T / 2, 5.6, 1.6, 3.4, T + 2.2, 'y')
for w in (back, left, right, front):
    weld(w)

floor = box(HW - T * 2, HD - T * 2, 0.3, (0, 0, 0.15))
roof = box(HW, HD, 0.6, (0, 0, HH + 0.3))
erode(floor, 1, 0.02, 0.03)
erode(roof, 1, 0.02, 0.03)
SPOTS.append({"c": [0, 0.3, 0], "r": [HW / 2 - 3, HD / 2 - 3], "k": "room"})

# roof parapet
for sy in (-1, 1):
    box(HW + 0.7, 0.55, 1.1, (0, sy * (HD / 2 + 0.27), HH + 1.15))
for sx in (-1, 1):
    box(0.55, HD, 1.1, (sx * (HW / 2 + 0.27), 0, HH + 1.15))

# ------------------------------------------------------------- the dome
drum = cyl(8.6, 9.0, 3.4, (0, 0, HH + 2.3), verts=28, collide=True)
erode(drum, 1, 0.02, 0.03)
for i in range(10):
    a = i * math.pi * 2 / 10
    arch_opening(drum, math.cos(a) * 8.8, math.sin(a) * 8.8, HH + 1.5, 0.8, 1.7, 3.0,
                 'y' if abs(math.sin(a)) < 0.5 else 'x')
weld(drum)
d1 = dome(8.7, (0, 0, HH + 4.0))
erode(d1, 1, 0.02, 0.03)
cyl(0.5, 0.35, 1.2, (0, 0, HH + 14.4), verts=12)
cyl(0.28, 0.0, 1.6, (0, 0, HH + 15.6), verts=10)

# four small corner domes
for q in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
    qx, qy = q[0] * (HW / 2 - 4.2), q[1] * (HD / 2 - 4.2)
    cyl(2.5, 2.7, 1.2, (qx, qy, HH + 1.2), verts=18)
    dd = dome(2.5, (qx, qy, HH + 1.8))
    cyl(0.16, 0.0, 0.8, (qx, qy, HH + 5.1), verts=8)

# ---------------------------------------------------------- the minaret
mx, my = -HW / 2 - 4.6, -HD / 2 - 4.6
shaft = cyl(2.2, 2.6, 26, (mx, my, 13), verts=20, collide=True)
erode(shaft, 1, 0.02, 0.04)
box(6.4, 6.4, 3.0, (mx, my, 1.5))
cyl(3.4, 3.4, 0.7, (mx, my, 26.4), verts=20)
gal = cyl(2.6, 2.6, 2.4, (mx, my, 27.8), verts=18, collide=True)
for i in range(12):
    a = i * math.pi * 2 / 12
    cyl(0.14, 0.14, 2.2, (mx + math.cos(a) * 3.0, my + math.sin(a) * 3.0, 27.6), verts=6)
cyl(3.4, 3.4, 0.5, (mx, my, 28.9), verts=20)
cyl(1.9, 2.1, 4.2, (mx, my, 31.2), verts=16)
dome(2.0, (mx, my, 33.3))
cyl(0.22, 0.0, 1.5, (mx, my, 35.4), verts=10)

# ------------------------------------------------- the courtyard arcade
CY = -HD / 2 - 17.0
CW = HW
box(CW + 2.4, 0.9, 1.1, (0, CY - 8.5, 0.55))              # the low court wall
for sx in (-1, 1):
    box(0.9, 17.5, 1.1, (sx * (CW / 2 + 1.2), CY, 0.55))
# a run of piers carrying arches on three sides
def arcade(x0, y0, x1, y1, n):
    """A run of piers carrying round arches, the shaded walk of a courtyard."""
    L = math.hypot(x1 - x0, y1 - y0)
    yaw = math.atan2(y1 - y0, x1 - x0)
    ux, uy = math.cos(yaw), math.sin(yaw)
    PIER_H = 5.2
    for i in range(n + 1):
        t = i / n
        px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        cyl(0.7, 0.78, PIER_H, (px, py, PIER_H / 2), verts=12, collide=True)
        cyl(0.95, 0.8, 0.5, (px, py, PIER_H + 0.25), verts=12)
    span = L / n
    rise = span * 0.5
    for i in range(n):
        cx = x0 + (x1 - x0) * ((i + 0.5) / n)
        cy2 = y0 + (y1 - y0) * ((i + 0.5) / n)
        k = 9
        for j in range(k):
            aa = math.pi * (j + 0.5) / k
            along = -math.cos(aa) * span / 2
            up = math.sin(aa) * rise
            bx = cx + ux * along
            by = cy2 + uy * along
            bz = PIER_H + 0.5 + up
            box_rot(span / k * 1.5, 1.5, 0.62, (bx, by, bz), (0, aa - math.pi / 2, yaw))
    box(L + 1.6, 1.7, 0.9, ((x0 + x1) / 2, (y0 + y1) / 2, PIER_H + rise + 1.2), yaw)


arcade(-CW / 2, CY - 8.0, CW / 2, CY - 8.0, 6)
arcade(-CW / 2, CY - 8.0, -CW / 2, CY + 8.0, 5)
arcade(CW / 2, CY - 8.0, CW / 2, CY + 8.0, 5)
SPOTS.append({"c": [0, 0.05, round(-CY, 2)], "r": [CW / 2 - 4, 6], "k": "court"})

# a fountain in the middle of the court
cyl(2.6, 2.8, 0.8, (0, CY, 0.4), verts=20, collide=True)
cyl(2.2, 2.2, 0.1, (0, CY, 0.75), verts=20)
cyl(0.4, 0.5, 1.4, (0, CY, 1.2), verts=12)
dome(0.55, (0, CY, 1.85))

# ------------------------------------------------------------- assemble
for o in parts:
    m = o.modifiers.new("bv", 'BEVEL')
    m.width = 0.022
    m.segments = 2
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(35)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "mosque"
weld(ob)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=3.0)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new("mosque")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.95
ob.data.materials.clear()
ob.data.materials.append(mat)
tex_path = os.path.abspath(os.path.join(ASSETS, "t_ashlar_d.jpg"))
img = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])

while len(ob.data.color_attributes):
    ob.data.color_attributes.remove(ob.data.color_attributes[0])
ob.data.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
scene.render.bake.target = 'VERTEX_COLORS'
scene.render.bake.margin = 2
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
try:
    bpy.ops.object.bake(type='AO')
    data = ob.data.color_attributes["ao"].data
    for i in range(len(data)):
        ao = 0.36 + 0.64 * data[i].color[0]
        data[i].color = (ao, ao, ao, 1.0)
except Exception as e:
    print("bake failed:", e)

if img:
    img.pack()

me = ob.data
me.calc_loop_triangles()
print("RESULT mosque verts=%d tris=%d colliders=%d" % (len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
