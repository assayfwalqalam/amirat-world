# Builds an Aserai-style mud-brick house in Blender and exports it as .glb
#   blender --background --python make_house.py -- <seed> <out.glb>
#
# Order matters: every solid is cut on its own while it is still a clean box.
# Merging first and cutting afterwards makes the booleans fail, because the
# merged mesh intersects itself.
import bpy, math, os, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SEED = int(argv[0]) if argv else 1
OUT = argv[1] if len(argv) > 1 else "house.glb"
random.seed(SEED)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16


def cube(sx, sy, sz, loc):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    return ob


def cyl(r, depth, loc, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cut(target, cutter):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def fix_normals(ob):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return bpy.context.active_object


def weld(ob, dist=0.0006):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=3, fine=0.055, broad=0.10):
    """Slump and wear a solid before any opening is cut into it, so the
    openings stay crisp while the wall around them never reads as flat."""
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    weld(ob)
    t1 = bpy.data.textures.new("er", 'CLOUDS')
    t1.noise_scale = 1.2
    t1.noise_depth = 2
    d1 = ob.modifiers.new("er", 'DISPLACE')
    d1.texture = t1
    d1.strength = fine
    d1.mid_level = 0.5
    bpy.ops.object.modifier_apply(modifier=d1.name)
    t2 = bpy.data.textures.new("sl", 'CLOUDS')
    t2.noise_scale = 3.8
    d2 = ob.modifiers.new("sl", 'DISPLACE')
    d2.texture = t2
    d2.strength = broad
    d2.mid_level = 0.5
    bpy.ops.object.modifier_apply(modifier=d2.name)
    weld(ob)


def bevel(ob, width, segs=2, angle=35):
    m = ob.modifiers.new("bv", 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


# ---------------------------------------------------------- proportions
W = random.uniform(7.0, 9.5)
D = random.uniform(6.0, 8.0)
H1 = random.uniform(3.6, 4.4)
H2 = random.uniform(2.9, 3.6)
has_upper = random.random() < 0.75
uw = W * random.uniform(0.62, 0.85)
ud = D * random.uniform(0.66, 0.9)
ox = random.uniform(-1, 1) * (W - uw) * 0.35
oy = random.uniform(-1, 1) * (D - ud) * 0.35

solids = []

# ------------------------------------------------- ground storey + openings
body = cube(W, D, H1, (0, 0, H1 / 2))
erode(body)

dw, dh = 1.3, 2.4
dx = random.uniform(-W * 0.2, W * 0.2)
cut(body, cube(dw, D + 2, dh - dw / 2, (dx, 0, (dh - dw / 2) / 2)))
cut(body, cyl(dw / 2, D + 2, (dx, 0, dh - dw / 2), rot=(math.pi / 2, 0, 0), verts=16))


def window(target, cx, cy, cz, w, h, axis, through):
    if axis == 'y':
        cut(target, cube(w, through, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2)))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2),
                        rot=(math.pi / 2, 0, 0), verts=12))
    else:
        cut(target, cube(through, w, h - w / 2, (cx, cy, cz - h / 2 + (h - w / 2) / 2)))
        cut(target, cyl(w / 2, through, (cx, cy, cz + h / 2 - w / 2),
                        rot=(0, math.pi / 2, 0), verts=12))


for i in range(random.randint(2, 3)):
    wx = random.uniform(-W * 0.36, W * 0.36)
    if abs(wx - dx) < 1.5:
        wx += 2.2 * (1 if wx >= dx else -1)
    window(body, wx, 0, H1 * random.uniform(0.56, 0.72), 0.74, 1.2, 'y', D + 2)
for i in range(random.randint(1, 2)):
    wy = random.uniform(-D * 0.3, D * 0.3)
    window(body, 0, wy, H1 * random.uniform(0.52, 0.7), 0.7, 1.1, 'x', W + 2)
weld(body)
solids.append(body)

# ------------------------------------------------------------ upper storey
if has_upper:
    upper = cube(uw, ud, H2, (ox, oy, H1 + H2 / 2))
    erode(upper)
    for i in range(random.randint(2, 3)):
        wx = ox + random.uniform(-uw * 0.34, uw * 0.34)
        window(upper, wx, oy, H1 + H2 * random.uniform(0.45, 0.65), 0.68, 1.05, 'y', ud + 2)
    if random.random() < 0.6:
        wy = oy + random.uniform(-ud * 0.3, ud * 0.3)
        window(upper, ox, wy, H1 + H2 * 0.55, 0.66, 1.0, 'x', uw + 2)
    weld(upper)
    solids.append(upper)


# --------------------------------- parapets, built as four strips, not cut
def parapet(cx, cy, w, d, z, h, t):
    out = []
    out.append(cube(w + t * 2, t, h, (cx, cy + d / 2 + t / 2, z + h / 2)))
    out.append(cube(w + t * 2, t, h, (cx, cy - d / 2 - t / 2, z + h / 2)))
    out.append(cube(t, d, h, (cx + w / 2 + t / 2, cy, z + h / 2)))
    out.append(cube(t, d, h, (cx - w / 2 - t / 2, cy, z + h / 2)))
    return out


if has_upper:
    solids += parapet(0, 0, W, D, H1, 0.8, 0.34)      # around the open lower roof
    solids += parapet(ox, oy, uw, ud, H1 + H2, 0.85, 0.32)
else:
    solids += parapet(0, 0, W, D, H1, 0.9, 0.34)

# --------------------------------------------------------------- timber
def beams(cx, cy, w, d, z, n):
    out = []
    for i in range(n):
        bx = cx - w / 2 + (i + 0.5) * (w / n)
        for sy in (-1, 1):
            out.append(cyl(random.uniform(0.055, 0.078), 0.5,
                           (bx, cy + sy * (d / 2 + 0.14), z + random.uniform(-0.03, 0.03)),
                           rot=(math.pi / 2, 0, 0), verts=7))
    return out


timber = []
timber += beams(0, 0, W * 0.84, D, H1 - 0.34, max(3, int(W / 1.2)))
if has_upper:
    timber += beams(ox, oy, uw * 0.8, ud, H1 + H2 - 0.32, max(3, int(uw / 1.2)))

# lintel over the door
timber.append(cube(dw + 0.6, 0.3, 0.17, (dx, -D / 2 - 0.06, dh + 0.14)))

# balcony over the door
if random.random() < 0.7:
    by = -D / 2 - 0.44
    bz = H1 + 0.2
    timber.append(cube(2.6, 1.0, 0.15, (dx, by, bz)))
    for i in range(8):
        timber.append(cube(0.075, 0.075, 0.6, (dx - 1.15 + i * 0.33, by - 0.42, bz + 0.37)))
    timber.append(cube(2.6, 0.11, 0.1, (dx, by - 0.42, bz + 0.71)))
    for sx in (-1, 1):
        timber.append(cyl(0.055, 0.9, (dx + sx * 1.1, by + 0.12, bz - 0.38),
                          rot=(math.radians(56), 0, 0), verts=6))

# an outside stair to the roof
if random.random() < 0.6:
    sside = random.choice([-1, 1])
    for i in range(10):
        timber.append(cube(1.2, 0.44, 0.22,
                           (sside * (W / 2 + 0.6), -D / 2 + 0.8 + i * 0.44,
                            0.13 + i * (H1 / 10))))

# ------------------------------------------------------- erode the walls
for pw in solids[len(solids) - (8 if has_upper else 4):]:
    erode(pw, levels=1, fine=0.03, broad=0.04)

shell = join(solids)
weld(shell)
bevel(shell, 0.028, 2, 35)
for t in timber:
    bevel(t, 0.012, 1, 40)

house = join([shell] + timber) if timber else shell
house.name = "house"
fix_normals(house)

# ------------------------------------------------------------- unwrap
bpy.context.view_layer.objects.active = house
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.005)
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------ material + bake
mat = bpy.data.materials.new("adobe")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.80, 0.68, 0.50, 1)
bsdf.inputs["Roughness"].default_value = 1.0
house.data.materials.clear()
house.data.materials.append(mat)

img = bpy.data.images.new("ao", 1024, 1024)
tn = nt.nodes.new('ShaderNodeTexImage')
tn.image = img
tn.location = (-700, 250)
nt.nodes.active = tn

scene.cycles.bake_type = 'AO'
scene.render.bake.margin = 8
bpy.ops.object.select_all(action='DESELECT')
house.select_set(True)
bpy.context.view_layer.objects.active = house
baked = True
try:
    bpy.ops.object.bake(type='AO')
except Exception as e:
    print("bake failed:", e)
    baked = False

if baked:
    # Tint the baked occlusion with mud-brick colour and a little grain, then use
    # it directly as the surface. One texture, occlusion already in it, which is
    # how a game asset should arrive.
    import random as _r
    px = list(img.pixels)
    base = (0.82, 0.69, 0.50)
    _r.seed(SEED)
    for i in range(0, len(px), 4):
        ao = px[i]
        ao = 0.30 + 0.70 * ao          # never let a crevice go fully black
        g = 1.0 + (_r.random() - 0.5) * 0.13
        px[i] = base[0] * ao * g
        px[i + 1] = base[1] * ao * g
        px[i + 2] = base[2] * ao * g
        px[i + 3] = 1.0
    img.pixels = px
    img.pack()
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])

me = house.data
me.calc_loop_triangles()
print("RESULT verts=%d tris=%d" % (len(me.vertices), len(me.loop_triangles)))

bpy.ops.object.select_all(action='DESELECT')
house.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB',
                          use_selection=True, export_apply=True, export_yup=True)
print("WROTE", OUT)
