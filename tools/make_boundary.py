# The small mud walls that divide land, after the ones threading through the
# reference village: low, uneven, eroded along the top, endlessly combinable.
#   blender --background --python make_boundary.py -- <kind> <out.glb> [assets]
# Kinds: low, mid, high, corner, end, gateposts, ruin
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "mid"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 733)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12

COLLIDERS = []
parts = []
RUN = 4.0
T = 0.38


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def solid(sx, sy, sz, loc, collide=True):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    parts.append(ob)
    return ob


def weld(ob):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0006)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def mud_wall(length, height, loc, along='x'):
    """A wall whose top line sags and dips the way old mud does."""
    sx, sy = (length, T) if along == 'x' else (T, length)
    ob = solid(sx, sy, height, (loc[0], loc[1], loc[2] + height / 2))
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = 3
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    ph = random.uniform(0, 6.3)
    for v in ob.data.vertices:
        a = v.co.x if along == 'x' else v.co.y
        # the top dips and rounds; the faces wander a little
        if v.co.z > loc[2] + height * 0.72:
            drop = (0.10 + 0.16 * (0.5 + 0.5 * math.sin(a * 1.7 + ph))) * height
            k = (v.co.z - (loc[2] + height * 0.72)) / (height * 0.28)
            v.co.z -= drop * k * k
            # the top rounds over
            side = v.co.y - loc[1] if along == 'x' else v.co.x - loc[0]
            v.co.y -= side * 0.5 * k if along == 'x' else 0
            if along != 'x':
                v.co.x -= side * 0.5 * k
        v.co.x += random.uniform(-0.012, 0.012)
        v.co.y += random.uniform(-0.012, 0.012)
    for sc, st in ((1.1, 0.02), (3.2, 0.045)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = sc
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = st
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)
    return ob


H = {"low": 0.85, "mid": 1.35, "high": 1.9}.get(KIND, 1.35)

if KIND in ("low", "mid", "high"):
    mud_wall(RUN, H, (0, 0, 0))

elif KIND == "corner":
    mud_wall(RUN / 2 + T / 2, 1.35, (-RUN / 4 + T / 4, 0, 0), 'x')
    mud_wall(RUN / 2 + T / 2, 1.35, (0, RUN / 4 - T / 4 + T / 2, 0), 'y')
    p = solid(0.62, 0.62, 1.62, (0, 0, 0.81))
    for v in p.data.vertices:
        v.co.x += random.uniform(-0.02, 0.02)
        v.co.y += random.uniform(-0.02, 0.02)

elif KIND == "end":
    mud_wall(RUN * 0.7, 1.35, (-RUN * 0.15, 0, 0), 'x')
    p = solid(0.6, 0.6, 1.58, (RUN * 0.25, 0, 0.79))
    for v in p.data.vertices:
        v.co.x += random.uniform(-0.02, 0.02)
        v.co.y += random.uniform(-0.02, 0.02)

elif KIND == "gateposts":
    for sx in (-1, 1):
        p = solid(0.62, 0.62, 1.9, (sx * 1.35, 0, 0.95))
        for v in p.data.vertices:
            v.co.x += random.uniform(-0.02, 0.02)
            v.co.y += random.uniform(-0.02, 0.02)
        cap = solid(0.8, 0.8, 0.16, (sx * 1.35, 0, 1.98), collide=False)

else:                       # ruin: a broken run, fallen in the middle
    mud_wall(RUN * 0.4, 1.3, (-RUN * 0.28, 0, 0), 'x')
    mud_wall(RUN * 0.3, 0.55, (RUN * 0.3, 0, 0), 'x')
    for _ in range(7):      # tumbled lumps
        b = solid(random.uniform(0.15, 0.34), random.uniform(0.15, 0.3),
                  random.uniform(0.1, 0.24),
                  (random.uniform(-0.4, 1.2), random.uniform(-0.4, 0.4),
                   random.uniform(0.05, 0.14)), collide=False)
        for v in b.data.vertices:
            v.co.x += random.uniform(-0.03, 0.03)
            v.co.z += random.uniform(-0.02, 0.02)


# ------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND
weld(ob)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=2.6)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1.0
ob.data.materials.clear()
ob.data.materials.append(mat)
# boundary walls wear the same mud as the houses, variant by kind
# small walls read banded textures as one giant stripe -- plain moods only
variant = {"low": "t_adobe_d.jpg", "mid": "t_adobe3_d.jpg", "high": "t_adobe_d.jpg",
           "corner": "t_adobe3_d.jpg", "end": "t_adobe_d.jpg",
           "gateposts": "t_adobe5_d.jpg", "ruin": "t_adobe4_d.jpg"}[KIND]
tex_path = os.path.abspath(os.path.join(ASSETS, variant))
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    img.pack()
nor_path = os.path.abspath(os.path.join(ASSETS, "t_adobe_gn.jpg"))
if os.path.exists(nor_path):
    nimg = bpy.data.images.load(nor_path)
    nimg.colorspace_settings.name = 'Non-Color'
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nimg
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = 1.2
    nt.links.new(ntex.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    nimg.pack()

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
