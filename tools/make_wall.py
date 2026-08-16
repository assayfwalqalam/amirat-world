# Wall pieces for the citadel, made the same way as the houses so the whole
# town is one material family.
#   blender --background --python make_wall.py -- <kind> <out.glb> [assets_dir]
# kind: seg | tower | tower_big | gate
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "seg"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else os.path.join(os.path.dirname(OUT), "..", "..", "assets")
random.seed({"seg": 5, "tower": 9, "tower_big": 17, "gate": 23}.get(KIND, 1))

bpy.ops.wm.read_factory_settings(use_empty=True)

def use_vertex_colour(nt, bsdf, tex_node=None, name="ao"):
    """Wire the baked occlusion into Base Color.

    Blender only writes a vertex colour layer into the .glb if the material
    actually reads it. Baking alone is silently dropped on export, which
    leaves every surface flat -- so the layer is multiplied over the texture
    here. glTF stores it as COLOR_0 and the renderer multiplies it back.
    """
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = name
    vc.location = (-700, -140)
    if tex_node is None:
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        return
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    mix.location = (-380, 200)
    nt.links.new(tex_node.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(vc.outputs['Color'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12

COLLIDERS = []


def solid(sx, sy, sz, loc, collide=True):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if collide:
        COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                          "h": [round(sx / 2, 3), round(sz / 2, 3), round(sy / 2, 3)]})
    return ob


def cyl(r, depth, loc, rot=(0, 0, 0), verts=16):
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


def weld(ob, dist=0.0006):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def erode(ob, levels=2, fine=0.04, broad=0.07):
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    weld(ob)
    for scale, strength in ((1.3, fine), (4.0, broad)):
        t = bpy.data.textures.new("n", 'CLOUDS')
        t.noise_scale = scale
        t.noise_depth = 2
        d = ob.modifiers.new("d", 'DISPLACE')
        d.texture = t
        d.strength = strength
        d.mid_level = 0.5
        bpy.ops.object.modifier_apply(modifier=d.name)
    weld(ob)


def bevel(ob, width=0.03, segs=2, angle=35):
    m = ob.modifiers.new("bv", 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return bpy.context.active_object


WH = 13.5        # wall height
WD = 6.0         # wall thickness
SEG = 12.0       # length of one curtain piece
parts = []


def merlons(cx, cy, w, z, along_x=True, spacing=2.6, t=1.5):
    """Battlement teeth with gaps, on the outward face."""
    n = max(2, int(w / spacing))
    step = w / n
    for i in range(n):
        o = -w / 2 + (i + 0.5) * step
        if along_x:
            parts.append(solid(step * 0.62, t, 1.95, (cx + o, cy, z + 0.975)))
        else:
            parts.append(solid(t, step * 0.62, 1.95, (cx, cy + o, z + 0.975)))


if KIND == "seg":
    base = solid(SEG, WD + 1.7, 3.4, (0, 0, 1.7))
    main = solid(SEG, WD, WH - 3.4, (0, 0, 3.4 + (WH - 3.4) / 2))
    cap = solid(SEG, WD + 0.5, 0.55, (0, 0, WH + 0.28))
    for o in (base, main, cap):
        erode(o, levels=2)
    parts += [base, main, cap]
    # arrow slits, so the wall is not a blank face
    for i in (-1, 1):
        cut(main, solid(0.28, WD + 1.5, 1.5, (i * SEG * 0.24, 0, 8.2), False))
    weld(main)
    merlons(0, WD / 2 - 0.75, SEG, WH + 0.55, True)
    # the walkway on the inner side
    parts.append(solid(SEG, 3.6, 0.8, (0, -WD / 2 - 1.8, WH - 0.4)))
    parts.append(solid(SEG, 0.7, 1.4, (0, -WD / 2 - 3.4, WH + 0.7)))

elif KIND in ("tower", "tower_big"):
    big = KIND == "tower_big"
    w = 13.0 if big else 11.0
    TH = WH + (6.5 if big else 4.5)
    base = solid(w + 1.5, w + 1.5, 4.0, (0, 0, 2.0))
    main = solid(w, w, TH - 4.0, (0, 0, 4.0 + (TH - 4.0) / 2))
    cap = solid(w + 1.3, w + 1.3, 0.85, (0, 0, TH + 0.42))
    for o in (base, main, cap):
        erode(o, levels=2)
    parts += [base, main, cap]
    for i in range(3):
        z = 6.5 + i * 3.2
        cut(main, solid(0.3, w + 2, 1.6, (0, 0, z), False))
        cut(main, solid(w + 2, 0.3, 1.6, (0, 0, z), False))
    weld(main)
    merlons(0, w / 2 + 0.35, w + 1.3, TH + 0.85, True)
    merlons(0, -w / 2 - 0.35, w + 1.3, TH + 0.85, True)
    merlons(w / 2 + 0.35, 0, w + 1.3, TH + 0.85, False)
    merlons(-w / 2 - 0.35, 0, w + 1.3, TH + 0.85, False)

elif KIND == "gate":
    HALF = 6.5                   # half the width of the opening
    GH = WH + 7
    for sgn in (-1, 1):
        bx = sgn * (HALF + 7.0)
        b1 = solid(14, 14, 4.2, (bx, 0, 2.1))
        b2 = solid(12.6, 12.6, GH - 4.2, (bx, 0, 4.2 + (GH - 4.2) / 2))
        b3 = solid(13.8, 13.8, 0.85, (bx, 0, GH + 0.42))
        for o in (b1, b2, b3):
            erode(o, levels=2)
        parts += [b1, b2, b3]
        merlons(bx, 6.9, 13.8, GH + 0.85, True)
        merlons(bx, -6.9, 13.8, GH + 0.85, True)
    # the span over the gateway, with the tunnel cut through it
    span = solid(HALF * 2 + 14, 13.0, 5.4, (0, 0, WH - 1.2))
    erode(span, levels=2)
    parts.append(span)
    lintel = solid(HALF * 2 + 15, 13.4, 0.85, (0, 0, WH + 1.9))
    erode(lintel, levels=1)
    parts.append(lintel)
    merlons(0, 6.9, HALF * 2 + 15, WH + 2.3, True)
    # arched tunnel
    tunnel_r = HALF
    arch_cut = cyl(tunnel_r, 15, (0, 0, 8.0), rot=(math.pi / 2, 0, 0), verts=24)
    box_cut = solid(HALF * 2, 15, 8.0, (0, 0, 4.0), False)
    for target in (span,):
        m = target.modifiers.new("b1", 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = arch_cut
        m.solver = 'EXACT'
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(arch_cut, do_unlink=True)
    bpy.data.objects.remove(box_cut, do_unlink=True)
    weld(span)

for o in parts:
    bevel(o)
piece = join(parts)
piece.name = KIND
weld(piece, 0.0004)

bpy.context.view_layer.objects.active = piece
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=2.1)
bpy.ops.object.mode_set(mode='OBJECT')

mat = bpy.data.materials.new("citadel")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1.0
piece.data.materials.clear()
piece.data.materials.append(mat)

tex_path = os.path.abspath(os.path.join(ASSETS, "t_ashlar_d.jpg"))
img_tex = None
if os.path.exists(tex_path):
    img_tex = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img_tex
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
else:
    print("no ashlar texture at", tex_path)

while len(piece.data.color_attributes):
    piece.data.color_attributes.remove(piece.data.color_attributes[0])
piece.data.color_attributes.active_color = piece.data.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
scene.render.bake.target = 'VERTEX_COLORS'
scene.render.bake.margin = 2
bpy.ops.object.select_all(action='DESELECT')
piece.select_set(True)
bpy.context.view_layer.objects.active = piece
try:
    bpy.ops.object.bake(type='AO')
    data = piece.data.color_attributes["ao"].data
    for i in range(len(data)):
        ao = 0.38 + 0.62 * data[i].color[0]
        data[i].color = (ao, ao, ao, 1.0)
except Exception as e:
    print("bake failed:", e)

if img_tex:
    img_tex.pack()

me = piece.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d" % (KIND, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

use_vertex_colour(nt, bsdf, tn if 'tn' in dir() else None)
bpy.ops.object.select_all(action='DESELECT')
piece.select_set(True)
try:
    # 'ACTIVE' writes the baked occlusion layer regardless of the node tree.
    # The default only exports it if the exporter can trace it to Base Color,
    # which silently loses the bake and leaves everything flat.
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True,
                              export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
