# Ornamental gold domes for the palace, after the fantasy references
# (shots/ref/fantasy_1..6): smooth swelling onion silhouettes, finely ribbed,
# crowned with a finial. Lathed at high resolution so the curve is true, never
# a faceted ball. Aniconic: the crescent is a symbol, no living form.
#   blender --background --python make_dome.py -- <kind> <out.glb> [assets]
# Kinds: onion, ribbed, tiered, small
import bpy, bmesh, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "onion"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

gold, drum = [], []
SEG = 96          # radial resolution: high, so the curve reads smooth


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def onion_profile(n):
    """A swelling onion silhouette as (r, z) samples, base to tip. r is a
    fraction of the belly radius; z a fraction of total height."""
    pts = []
    # control points of the silhouette (t, r) -- the classic bulb
    ctrl = [(0.00, 0.72), (0.06, 0.88), (0.16, 1.00), (0.30, 1.02),
            (0.44, 0.94), (0.58, 0.78), (0.70, 0.58), (0.80, 0.40),
            (0.88, 0.25), (0.94, 0.13), (0.98, 0.05), (1.00, 0.0)]
    # z easing: rises faster low, eases into the point
    for i in range(n + 1):
        t = i / n
        # piecewise-linear interpolation of r through the control points
        r = ctrl[-1][1]
        for k in range(len(ctrl) - 1):
            t0, r0 = ctrl[k]
            t1, r1 = ctrl[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0 or 1)
                f = f * f * (3 - 2 * f)          # smooth each span
                r = r0 + (r1 - r0) * f
                break
        z = 1.06 * (t ** 0.92)
        pts.append((r, z))
    return pts


def lathe(profile, belly_r, height, ribs, rib_amp, z0=0.0):
    """Spin a profile into a dome, with `ribs` shallow flutes round it."""
    me = bpy.data.meshes.new("dome")
    ob = bpy.data.objects.new("dome", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    rings = []
    n = len(profile)
    for i in range(n):
        r_frac, z_frac = profile[i]
        ring = []
        for s in range(SEG):
            th = s / SEG * 2 * math.pi
            # ribs: a gentle cosine flute, fading out to the tip
            rib = 1.0 + rib_amp * (0.5 - 0.5 * math.cos(ribs * th)) * max(0.0, 1 - z_frac) ** 0.5
            rr = belly_r * r_frac * rib
            ring.append(bm.verts.new((math.cos(th) * rr, math.sin(th) * rr, z0 + z_frac * height)))
        rings.append(ring)
    for i in range(n - 1):
        for s in range(SEG):
            s2 = (s + 1) % SEG
            a, b, c, d = rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]
            try:
                bm.faces.new((a, b, c, d))
            except ValueError:
                pass
    # close the very tip
    tip = bm.verts.new((0, 0, z0 + profile[-1][1] * height + 0.001))
    for s in range(SEG):
        s2 = (s + 1) % SEG
        try:
            bm.faces.new((rings[-1][s], rings[-1][s2], tip))
        except ValueError:
            pass
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    return ob


def finial(z, s=1.0):
    """A stacked-ball spike with a crescent on top -- the alem."""
    zc = z
    for r in (0.10 * s, 0.07 * s, 0.045 * s):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(0, 0, zc), segments=20, ring_count=12)
        gold.append(bpy.context.active_object)
        zc += r * 1.6
    bpy.ops.mesh.primitive_cone_add(radius1=0.02 * s, radius2=0.0, depth=0.28 * s, location=(0, 0, zc + 0.1 * s), vertices=16)
    gold.append(bpy.context.active_object)
    zc += 0.3 * s
    # a crescent: a torus with a sphere cut from one side
    bpy.ops.mesh.primitive_torus_add(location=(0, 0, zc + 0.12 * s), major_radius=0.10 * s, minor_radius=0.022 * s,
                                     major_segments=24, minor_segments=10, abso_major_rad=0.10 * s)
    cres = bpy.context.active_object
    cres.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.085 * s, location=(0.06 * s, 0, zc + 0.12 * s), segments=16, ring_count=10)
    cut = bpy.context.active_object
    m = cres.modifiers.new("b", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cut; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = cres
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cut, do_unlink=True)
    gold.append(cres)


if KIND in ("onion", "ribbed", "small"):
    R = 1.0
    H = 1.9 if KIND != "small" else 1.6
    ribs = 24 if KIND == "ribbed" else 16
    amp = 0.06 if KIND == "ribbed" else 0.035
    # the drum the dome sits on
    bpy.ops.mesh.primitive_cylinder_add(radius=R * 0.72, depth=0.5, location=(0, 0, 0.25), vertices=SEG)
    drum.append(bpy.context.active_object)
    # a torus lip where drum meets dome
    bpy.ops.mesh.primitive_torus_add(location=(0, 0, 0.5), major_radius=R * 0.72, minor_radius=0.05,
                                     major_segments=SEG, minor_segments=12)
    gold.append(bpy.context.active_object)
    dome = lathe(onion_profile(48), R, H, ribs, amp, z0=0.5)
    gold.append(dome)
    finial(0.5 + H + 0.02, 1.0)

else:                          # tiered: a big dome with a ring of small ones
    R = 1.0
    H = 1.9
    bpy.ops.mesh.primitive_cylinder_add(radius=R * 0.72, depth=0.5, location=(0, 0, 0.25), vertices=SEG)
    drum.append(bpy.context.active_object)
    gold.append(lathe(onion_profile(48), R, H, 16, 0.035, z0=0.5))
    finial(0.5 + H + 0.02, 1.0)
    for i in range(6):
        a = i / 6 * 2 * math.pi
        bx, by = math.cos(a) * R * 1.5, math.sin(a) * R * 1.5
        bpy.ops.mesh.primitive_cylinder_add(radius=0.28, depth=0.4, location=(bx, by, 0.2), vertices=32)
        drum.append(bpy.context.active_object)
        small = lathe(onion_profile(36), 0.4, 0.8, 12, 0.03, z0=0.4)
        small.location = (bx, by, 0)
        gold.append(small)


# --------------------------------------------------------------- materials
def finish(objs, name, base, rough, metal):
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
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    # gold must read bright without an environment map: a warm emissive floor
    # so it glows like lit gold rather than a black mirror
    if name == "gold":
        try:
            b.inputs["Emission Color"].default_value = (0.55, 0.40, 0.12, 1)
        except KeyError:
            b.inputs["Emission"].default_value = (0.55, 0.40, 0.12, 1)
        b.inputs["Emission Strength"].default_value = 0.55
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


parts = []
parts.append(finish(gold, "gold", (0.95, 0.72, 0.26, 1), 0.34, 0.75))
parts.append(finish(drum, "drumstone", (0.80, 0.76, 0.68, 1), 0.7, 0.0))
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d" % (KIND, len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
print("WROTE", OUT)
