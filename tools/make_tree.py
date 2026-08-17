# Big trees, grown branch by branch so every one has a real silhouette.
#   blender --background --python make_tree.py -- <kind> <seed> <out.glb> [assets]
# Kinds: olive, plane, cypress, tamarisk, fig
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "olive"
SEED = int(argv[1]) if len(argv) > 1 else 1
OUT = argv[2] if len(argv) > 2 else (KIND + ".glb")
ASSETS = argv[3] if len(argv) > 3 else "assets"
random.seed(SEED * 4967 + sum(ord(c) for c in KIND) * 61)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

COLLIDERS = []
wood, leaf = [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def limb(p0, direction, length, r0, r1, segs=None, crook=0.3, min_dz=None):
    """One crooked limb; returns its tip and tip direction. A ball at every
    joint hides the elbows; min_dz keeps a trunk from wandering off upright."""
    segs = segs or max(3, int(length / 0.7))
    dx, dy, dz = direction
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    dx, dy, dz = dx / n, dy / n, dz / n
    x, y, z = p0
    seglen = length / segs
    for i in range(segs):
        t = i / float(segs)
        r = r0 + (r1 - r0) * t
        w = crook * seglen
        dx += random.uniform(-w, w) * 0.18
        dy += random.uniform(-w, w) * 0.18
        dz += random.uniform(-w * 0.5, w) * 0.18
        if min_dz is not None and dz < min_dz:
            dz = min_dz
        m = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / m, dy / m, dz / m
        nx, ny, nz = x + dx * seglen, y + dy * seglen, z + dz * seglen
        mid = ((x + nx) / 2, (y + ny) / 2, (z + nz) / 2)
        pitch = math.acos(max(-1.0, min(1.0, dz)))
        yaw = math.atan2(dy, dx)
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r0 + (r1 - r0) * (t + 1.0 / segs),
                                        depth=seglen * 1.15, location=mid, vertices=8)
        ob = bpy.context.active_object
        ob.rotation_euler = (0.0, pitch, yaw)
        bpy.ops.object.transform_apply(rotation=True)
        wood.append(ob)
        if i < segs - 1:
            r2 = r0 + (r1 - r0) * (t + 1.0 / segs)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r2 * 1.05, location=(nx, ny, nz),
                                                 segments=8, ring_count=5)
            wood.append(bpy.context.active_object)
        x, y, z = nx, ny, nz
    return (x, y, z), (dx, dy, dz)


def crown(at, r, squash=0.72, n=None):
    """A cloud of leaf masses round a point."""
    n = n or max(7, int(r * 9))
    for _ in range(n):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.4, 1.2)
        rr = random.uniform(0, r * 0.62)
        cx = at[0] + math.cos(a) * math.cos(el) * rr
        cy = at[1] + math.sin(a) * math.cos(el) * rr
        cz = at[2] + math.sin(el) * rr * squash
        cr = random.uniform(r * 0.3, r * 0.48)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=cr, location=(cx, cy, cz),
                                             segments=8, ring_count=5)
        ob = bpy.context.active_object
        for v in ob.data.vertices:
            v.co.z *= squash
            v.co.x += random.uniform(-cr * 0.22, cr * 0.22)
            v.co.y += random.uniform(-cr * 0.22, cr * 0.22)
            v.co.z += random.uniform(-cr * 0.18, cr * 0.18)
        leaf.append(ob)


GREEN = {
    "olive": (0.20, 0.26, 0.15), "plane": (0.14, 0.26, 0.10),
    "cypress": (0.08, 0.155, 0.085), "tamarisk": (0.20, 0.27, 0.155),
    "fig": (0.115, 0.23, 0.09), "giant": (0.13, 0.245, 0.10),
}[KIND]

if KIND == "olive":
    H = random.uniform(4.5, 6.0)
    tip, d = limb((0, 0, 0), (random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), 1),
                  H * 0.45, 0.34, 0.2, crook=0.5, min_dz=0.62)
    for _ in range(random.randint(3, 5)):
        a = random.uniform(0, 6.283)
        t2, _d2 = limb(tip, (math.cos(a), math.sin(a), random.uniform(0.5, 1.1)),
                       H * 0.5, 0.14, 0.045, crook=0.6)
        crown(t2, H * 0.34, 0.6)
    rec((0, 0, H * 0.3), 0.4, 0.4, H * 0.3)

elif KIND == "plane":
    H = random.uniform(9.0, 12.0)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.42, 0.5, 0.3, crook=0.25, min_dz=0.75)
    for _ in range(random.randint(4, 6)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.8, math.sin(a) * 0.8, 1.1),
                     H * 0.42, 0.2, 0.06, crook=0.4)
        crown(t2, H * 0.30, 0.7)
    crown((tip[0], tip[1], tip[2] + H * 0.28), H * 0.34, 0.72)
    rec((0, 0, H * 0.28), 0.55, 0.55, H * 0.28)

elif KIND == "cypress":
    H = random.uniform(7.0, 10.0)
    limb((0, 0, 0), (0, 0, 1), H * 0.3, 0.22, 0.12, crook=0.12)
    # the whole tree is one tall narrow flame of foliage
    n = int(H * 3)
    for i in range(n):
        t = i / float(n)
        rr = (0.9 - 0.72 * t) * (1.0 + random.uniform(-0.14, 0.14))
        z = H * 0.14 + t * H * 0.86
        a = random.uniform(0, 6.283)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=max(0.2, rr * 0.5),
            location=(math.cos(a) * rr * 0.3, math.sin(a) * rr * 0.3, z),
            segments=7, ring_count=5)
        ob = bpy.context.active_object
        for v in ob.data.vertices:
            v.co.z *= 1.5
            v.co.x += random.uniform(-0.08, 0.08)
            v.co.y += random.uniform(-0.08, 0.08)
        leaf.append(ob)
    rec((0, 0, H * 0.4), 0.35, 0.35, H * 0.4)

elif KIND == "tamarisk":
    H = random.uniform(4.0, 5.5)
    for _ in range(random.randint(3, 5)):
        a = random.uniform(0, 6.283)
        tip, _ = limb((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0),
                      (math.cos(a) * 0.5, math.sin(a) * 0.5, 1.2),
                      H * 0.7, 0.12, 0.03, crook=0.5)
        crown(tip, H * 0.3, 0.55, n=5)
    rec((0, 0, H * 0.3), 0.35, 0.35, H * 0.3)

elif KIND == "giant":
    # the bustan patriarch: five to seven storeys of tree
    H = random.uniform(16.0, 21.0)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.38, 1.15, 0.62,
                  segs=6, crook=0.22, min_dz=0.8)
    # heavy boughs fork off the crown point and each carries its own cloud
    for _ in range(random.randint(6, 8)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.9, math.sin(a) * 0.9, random.uniform(0.55, 1.0)),
                     H * 0.42, 0.34, 0.09, crook=0.4)
        crown(t2, H * 0.24, 0.66)
    crown((tip[0], tip[1], tip[2] + H * 0.26), H * 0.30, 0.7)
    # buttress roots at the foot
    for _ in range(5):
        a = random.uniform(0, 6.283)
        limb((math.cos(a) * 0.7, math.sin(a) * 0.7, 0.4),
             (math.cos(a), math.sin(a), -0.55), 1.6, 0.3, 0.06, segs=3, crook=0.3)
    rec((0, 0, H * 0.22), 1.1, 1.1, H * 0.22)

else:                        # fig: low, wide, spreading
    H = random.uniform(4.0, 5.5)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.3, 0.4, 0.26, crook=0.4, min_dz=0.6)
    for _ in range(random.randint(4, 6)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 1.3, math.sin(a) * 1.3, random.uniform(0.25, 0.6)),
                     H * 0.65, 0.16, 0.05, crook=0.5)
        crown(t2, H * 0.4, 0.55)
    rec((0, 0, H * 0.25), 0.45, 0.45, H * 0.25)


# ------------------------------------------------------------- assemble
def join_and_colour(objs, name, tint, jitter_amt):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    me = ob.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for poly in me.polygons:
        g = 1.0 + random.uniform(-jitter_amt, jitter_amt)
        for li in poly.loop_indices:
            col.data[li].color = (min(1.0, tint[0] * g), min(1.0, tint[1] * g),
                                  min(1.0, tint[2] * g), 1.0)
    bpy.ops.object.shade_smooth()
    return ob


w_ob = join_and_colour(wood, "wood", (0.155, 0.115, 0.085), 0.12)
l_ob = join_and_colour(leaf, "leaf", GREEN, 0.28)
bpy.ops.object.select_all(action='DESELECT')
w_ob.select_set(True)
l_ob.select_set(True)
bpy.context.view_layer.objects.active = w_ob
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.9
vc = nt.nodes.new('ShaderNodeVertexColor')
vc.layer_name = "ao"
nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
ob.data.materials.clear()
ob.data.materials.append(mat)

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%d verts=%d tris=%d" % (KIND, SEED, len(me.vertices), len(me.loop_triangles)))
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
