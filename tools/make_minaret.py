# Standalone minarets, three schools.
#   blender --background --python make_minaret.py -- <style> <out.glb> [assets]
# Styles: square (Kairouan tiers), round (balcony and lantern), octagon (twin galleries)
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STYLE = argv[0] if argv else "square"
OUT = argv[1] if len(argv) > 1 else (STYLE + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in STYLE) * 557)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12

COLLIDERS = []
parts = []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def box(sx, sy, sz, loc, collide=False):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    parts.append(ob)
    return ob


def cyl(r1, r2, h, loc, verts=20, collide=False):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, location=loc, vertices=verts)
    ob = bpy.context.active_object
    if collide:
        rec(loc, max(r1, r2) * 0.85, max(r1, r2) * 0.85, h / 2)
    parts.append(ob)
    return ob


def dome(r, loc, seg=18, squash=1.05):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    ob = bpy.context.active_object
    for v in ob.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
        else:
            v.co.z *= squash
    parts.append(ob)
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


if STYLE == "square":
    # three shrinking square tiers, arched openings near each top, ribbed dome
    zs = 0.0
    for i, (w, h) in enumerate(((5.2, 13.0), (3.6, 6.5), (2.4, 4.2))):
        t = box(w, w, h, (0, 0, zs + h / 2), collide=True)
        for f in range(4):
            a = f * math.pi / 2
            cut(t, 0.8 if f % 2 == 0 else w + 1, w + 1 if f % 2 == 0 else 0.8, 1.4,
                (0, 0, zs + h - 1.2))
        box(w + 0.4, w + 0.4, 0.4, (0, 0, zs + h + 0.2))
        zs += h + 0.4
    dome(1.35, (0, 0, zs), 16, 1.1)
    cyl(0.12, 0.0, 1.6, (0, 0, zs + 1.35 * 1.1 + 0.8), verts=8)

elif STYLE == "round":
    H = 22.0
    base = box(3.4, 3.4, 2.6, (0, 0, 1.3), collide=True)
    sh = cyl(1.5, 1.1, H, (0, 0, 2.6 + H / 2), verts=24, collide=True)
    z1 = 2.6 + H
    cyl(1.9, 1.9, 0.55, (0, 0, z1 + 0.27), verts=24)
    gal = cyl(1.25, 1.25, 2.3, (0, 0, z1 + 1.7), verts=18, collide=True)
    for i in range(8):
        a = i * math.pi / 4
        cut(gal, 0.5, 0.5, 1.4, (math.cos(a) * 1.25, math.sin(a) * 1.25, z1 + 1.9))
    for i in range(10):
        a = i * math.pi / 5
        cyl(0.07, 0.07, 1.5, (math.cos(a) * 1.7, math.sin(a) * 1.7, z1 + 1.3), verts=6)
    cyl(1.9, 1.9, 0.4, (0, 0, z1 + 3.0), verts=24)
    cyl(1.0, 0.8, 2.6, (0, 0, z1 + 4.6), verts=16)
    dome(1.05, (0, 0, z1 + 5.9), 16, 1.15)
    cyl(0.1, 0.0, 1.5, (0, 0, z1 + 5.9 + 1.15 + 0.75), verts=8)

else:                       # octagon with twin galleries
    H1, H2 = 14.0, 7.0
    base = box(3.8, 3.8, 3.0, (0, 0, 1.5), collide=True)
    s1 = cyl(1.7, 1.35, H1, (0, 0, 3.0 + H1 / 2), verts=8, collide=True)
    z1 = 3.0 + H1
    cyl(2.1, 2.1, 0.5, (0, 0, z1 + 0.25), verts=8)
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        cyl(0.07, 0.07, 1.3, (math.cos(a) * 1.85, math.sin(a) * 1.85, z1 + 0.95), verts=6)
    cyl(2.1, 2.1, 0.32, (0, 0, z1 + 1.7), verts=8)
    s2 = cyl(1.25, 1.0, H2, (0, 0, z1 + 1.9 + H2 / 2), verts=8, collide=True)
    z2 = z1 + 1.9 + H2
    cyl(1.6, 1.6, 0.4, (0, 0, z2 + 0.2), verts=8)
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        cyl(0.06, 0.06, 1.1, (math.cos(a) * 1.42, math.sin(a) * 1.42, z2 + 0.75), verts=6)
    cyl(1.6, 1.6, 0.3, (0, 0, z2 + 1.35), verts=8)
    dome(0.95, (0, 0, z2 + 1.6), 14, 1.2)
    cyl(0.09, 0.0, 1.4, (0, 0, z2 + 1.6 + 0.95 * 1.2 + 0.7), verts=8)


# ------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = STYLE
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=2.6)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()
es = ob.modifiers.new("es", 'EDGE_SPLIT')
es.use_edge_angle = True
es.split_angle = math.radians(33)
bpy.ops.object.modifier_apply(modifier=es.name)

mat = bpy.data.materials.new(STYLE)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.95
ob.data.materials.clear()
ob.data.materials.append(mat)
tex_path = os.path.abspath(os.path.join(ASSETS, "t_ashlar_d.jpg"))
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    img.pack()

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d" % (STYLE, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
