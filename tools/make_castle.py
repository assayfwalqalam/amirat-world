# The palace massing: a mountain of domes after fantasy_3, at genuinely huge
# scale, in whiter ashlar. This is the MASSING blockout, shown for approval
# before the detailed build. Terraced base, a great central dome, flanking
# and scattered domes, corner towers, a grand iwan portal. Aniconic.
#   blender --background --python make_castle.py -- <out.glb> [assets]
import bpy, bmesh, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "castle.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

stone, gold = [], []
SEG = 64


def box(sx, sy, sz, loc, into, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = ob.modifiers.new("bv", 'BEVEL'); m.width = bevel; m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
    into.append(ob)
    return ob


def cyl(r, h, loc, into, verts=SEG):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=verts)
    into.append(bpy.context.active_object)
    return bpy.context.active_object


def onion_profile(n):
    ctrl = [(0.00, 0.72), (0.06, 0.88), (0.16, 1.00), (0.30, 1.02),
            (0.44, 0.94), (0.58, 0.78), (0.70, 0.58), (0.80, 0.40),
            (0.88, 0.25), (0.94, 0.13), (0.98, 0.05), (1.00, 0.0)]
    pts = []
    for i in range(n + 1):
        t = i / n
        r = ctrl[-1][1]
        for k in range(len(ctrl) - 1):
            t0, r0 = ctrl[k]; t1, r1 = ctrl[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0 or 1); f = f * f * (3 - 2 * f)
                r = r0 + (r1 - r0) * f
                break
        pts.append((r, 1.06 * (t ** 0.92)))
    return pts


def dome(cx, cy, base_z, belly_r, height, ribs=16):
    """A gold onion dome on a short stone drum at (cx,cy)."""
    cyl(belly_r * 0.74, belly_r * 0.7, (cx, cy, base_z + belly_r * 0.35), stone, verts=40)
    prof = onion_profile(40)
    me = bpy.data.meshes.new("d"); ob = bpy.data.objects.new("d", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new(); rings = []
    z0 = base_z + belly_r * 0.7
    for (rf, zf) in prof:
        ring = []
        for s in range(SEG):
            th = s / SEG * 2 * math.pi
            rib = 1.0 + 0.03 * (0.5 - 0.5 * math.cos(ribs * th)) * max(0.0, 1 - zf) ** 0.5
            rr = belly_r * rf * rib
            ring.append(bm.verts.new((cx + math.cos(th) * rr, cy + math.sin(th) * rr, z0 + zf * height)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(SEG):
            s2 = (s + 1) % SEG
            try:
                bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))
            except ValueError:
                pass
    tip = bm.verts.new((cx, cy, z0 + prof[-1][1] * height + 0.01))
    for s in range(SEG):
        s2 = (s + 1) % SEG
        try:
            bm.faces.new((rings[-1][s], rings[-1][s2], tip))
        except ValueError:
            pass
    bm.normal_update(); bm.to_mesh(me); bm.free()
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    gold.append(ob)
    # a spike finial
    cyl(belly_r * 0.03, height * 0.28, (cx, cy, z0 + prof[-1][1] * height + height * 0.14), gold, verts=10)


def tower(cx, cy, base_z, r, h):
    """An octagonal ashlar tower capped by a small dome."""
    cyl(r, h, (cx, cy, base_z + h / 2), stone, verts=8)
    cyl(r * 1.12, h * 0.06, (cx, cy, base_z + h), stone, verts=8)   # a cornice ring
    dome(cx, cy, base_z + h, r * 0.9, r * 1.6, ribs=10)


def arcade(x0, y, x1, z, n, h, into):
    """A row of arched piers (blockout: piers + a lintel band)."""
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        box(1.4, 1.4, h, (x, y, z + h / 2), into, bevel=0.1)
    box(abs(x1 - x0) + 1.4, 1.4, 1.6, ((x0 + x1) / 2, y, z + h + 0.8), into, bevel=0.1)


# ------------------------------------------------------------ the massing
# HUGE. The base is ~58 m across; the great dome tops out near ~46 m.
# Three retreating terraces, arcaded, the mountain of domes above.
T = [(29, 26, 0, 10), (22, 20, 10, 9), (15.5, 14, 19, 8)]   # (hx, hy, z0, h)
for (hx, hy, z0, h) in T:
    b = box(hx * 2, hy * 2, h, (0, 0, z0 + h / 2), stone, bevel=0.2)
    # a parapet lip
    box(hx * 2 + 0.6, hy * 2 + 0.6, 1.4, (0, 0, z0 + h + 0.4), stone, bevel=0.1)

# arcades along the front of each terrace
for (hx, hy, z0, h) in T:
    arcade(-hx + 3, -hy - 0.2, hx - 3, z0 + 1.0, max(4, int(hx / 3.2)), h * 0.62, stone)

top_z = T[-1][2] + T[-1][3]        # 27

# the grand iwan portal on the front of the base: a tall recessed pointed arch
box(10, 3, 20, (0, -26.2, 10), stone, bevel=0.2)
# (blockout recess: a darker inset — kept simple for the massing)
box(6.5, 3.2, 14, (0, -26.6, 8), gold, bevel=0.1)   # gold-lit portal face, reads as the entrance

# the great central dome
dome(0, 0, top_z, 9.5, 18, ribs=20)
# four flanking medium domes at the corners of the top terrace
for sx in (-1, 1):
    for sy in (-1, 1):
        dome(sx * 9, sy * 8, top_z, 4.2, 8, ribs=14)
# a scatter of small domes on the middle terrace to build the "mountain"
mid_z = T[1][2] + T[1][3]
for (dx, dy) in ((-16, -12), (16, -12), (-16, 12), (16, 12), (0, -15), (0, 15)):
    dome(dx, dy, mid_z, 3.0, 5.5, ribs=12)
# corner towers on the base, tall
for sx in (-1, 1):
    for sy in (-1, 1):
        tower(sx * 26, sy * 23, 0, 3.2, 34)
# two front minaret-towers flanking the portal, taller
for sx in (-1, 1):
    tower(sx * 13, -25, 0, 2.4, 40)


# ------------------------------------------------------------ materials
def finish(objs, name, base, rough, metal, tex=None, tint=None, emis=None):
    if not objs:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    if name == "stone":
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=3.0)
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emis:
        try:
            b.inputs["Emission Color"].default_value = emis
        except KeyError:
            b.inputs["Emission"].default_value = emis
        b.inputs["Emission Strength"].default_value = 0.5
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = m.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
            if tint:
                mix = m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0; mix.inputs['Color2'].default_value = tint
                m.node_tree.links.new(tn.outputs['Color'], mix.inputs['Color1'])
                m.node_tree.links.new(mix.outputs['Color'], b.inputs['Base Color'])
            else:
                m.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


parts = []
# whiter ashlar: the beloved stone tinted lighter
parts.append(finish(stone, "stone", (0.86, 0.82, 0.74, 1), 0.72, 0.0,
                    tex="t_ashlar_d.jpg", tint=(1.18, 1.15, 1.08, 1)))
parts.append(finish(gold, "gold", (0.95, 0.72, 0.26, 1), 0.34, 0.75, emis=(0.55, 0.40, 0.12, 1)))
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "castle"

me = ob.data
me.calc_loop_triangles()
print("RESULT castle verts=%d tris=%d" % (len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
print("WROTE", OUT)
