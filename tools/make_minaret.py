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
    # His order: no more round shafts. This kind is now a TALL SLENDER
    # square-tier minaret - four tiers, a window near each head, the
    # gallery posts square, the dome only a cap.
    zs = 0.0
    box(4.6, 4.6, 2.2, (0, 0, 1.1), collide=True)
    zs = 2.2
    for (w, h) in ((3.2, 9.5), (2.7, 6.5), (2.2, 4.8), (1.8, 3.2)):
        t = box(w, w, h, (0, 0, zs + h / 2), collide=True)
        cut(t, 0.62, w + 1, 1.25, (0, 0, zs + h - 1.05))
        box(w + 0.36, w + 0.36, 0.36, (0, 0, zs + h + 0.18))
        zs += h + 0.36
    for gx in (-1, 1):
        for gy in (-1, 1):
            box(0.18, 0.18, 1.9, (gx * 0.75, gy * 0.75, zs + 1.15))
    box(2.1, 2.1, 0.4, (0, 0, zs + 2.3))
    dome(1.0, (0, 0, zs + 2.5), 16, 1.1)
    cyl(0.1, 0.0, 1.4, (0, 0, zs + 2.5 + 1.1 + 0.7), verts=8)

else:
    # The octagon kind is square-tiered now too - broader, TWIN galleries
    # kept as two post rings between the tiers.
    zs = 0.0
    box(5.4, 5.4, 2.6, (0, 0, 1.3), collide=True)
    zs = 2.6
    for ti, (w, h) in enumerate(((4.0, 10.0), (3.2, 6.0))):
        t = box(w, w, h, (0, 0, zs + h / 2), collide=True)
        cut(t, 0.72, w + 1, 1.35, (0, 0, zs + h - 1.15))
        box(w + 0.5, w + 0.5, 0.45, (0, 0, zs + h + 0.22))
        zs += h + 0.45
        for gx in (-1, 1):
            for gy in (-1, 1):
                box(0.2, 0.2, 1.6, (gx * (w / 2 - 0.2), gy * (w / 2 - 0.2), zs + 0.95))
        box(w + 0.1, w + 0.1, 0.35, (0, 0, zs + 1.9))
        zs += 2.1
    box(2.4, 2.4, 3.6, (0, 0, zs + 1.8), collide=True)
    zs += 3.6
    dome(1.2, (0, 0, zs), 16, 1.15)
    cyl(0.1, 0.0, 1.5, (0, 0, zs + 1.15 * 1.2 + 0.75), verts=8)


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
