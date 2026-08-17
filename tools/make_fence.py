# Branch fences, screens and gates, as their own pack.
#   blender --background --python make_fence.py -- <style> <out.glb> [assets]
#
# Styles: rail, picket, wattle, lattice, palm, brush, thorn, post, gate, low, brace
#
# These are NOT sawn timber. Everything is a cut branch: crooked, tapering from
# base to tip, knotted where side shoots were taken off, and lashed with cord
# rather than nailed. A fence made of straight planed boards reads as a garden
# centre; a fence made of bent sticks reads as a place people actually live.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STYLE = argv[0] if argv else "rail"
OUT = argv[1] if len(argv) > 1 else (STYLE + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in STYLE) * 977)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
parts = []
RUN = 4.0                      # length of one section


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def branch(p0, direction, length, r0, r1=None, bend=0.30, segs=None, knots=True, verts=6):
    """A cut branch: tapering, crooked, knotted.

    The direction wanders a little at every segment and more toward the thin
    end, the stick narrows along its length, and stubs are left where side
    shoots were cut. Returns the tip so runs can be chained.
    """
    r1 = r0 * 0.45 if r1 is None else r1
    segs = segs or max(3, int(length / 0.3))
    dx, dy, dz = direction
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    dx, dy, dz = dx / n, dy / n, dz / n
    x, y, z = p0
    seglen = length / segs
    for i in range(segs):
        t = i / float(segs)
        r = r0 + (r1 - r0) * t
        w = bend * seglen * (0.45 + t)
        dx += random.uniform(-w, w)
        dy += random.uniform(-w, w)
        dz += random.uniform(-w, w) * 0.55
        m = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / m, dy / m, dz / m
        nx, ny, nz = x + dx * seglen, y + dy * seglen, z + dz * seglen
        mid = ((x + nx) / 2, (y + ny) / 2, (z + nz) / 2)
        pitch = math.acos(max(-1.0, min(1.0, dz)))
        yaw = math.atan2(dy, dx)
        rn = r + (r1 - r0) / segs
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=max(0.004, rn),
                                        depth=seglen * 1.14, location=mid, vertices=verts)
        ob = bpy.context.active_object
        ob.rotation_euler = (0.0, pitch, yaw + math.pi / 2)
        bpy.ops.object.transform_apply(rotation=True)
        parts.append(ob)
        if knots and i > 0 and random.random() < 0.16:
            kl = random.uniform(0.1, 0.26)
            ka = random.uniform(0, 6.283)
            bpy.ops.mesh.primitive_cone_add(radius1=r * 0.7, radius2=r * 0.18, depth=kl,
                                            location=(mid[0] + math.cos(ka) * kl * 0.4,
                                                      mid[1] + math.sin(ka) * kl * 0.4,
                                                      mid[2]), vertices=5)
            kb = bpy.context.active_object
            kb.rotation_euler = (0.0, math.pi / 2, ka)
            bpy.ops.object.transform_apply(rotation=True)
            parts.append(kb)
        x, y, z = nx, ny, nz
    return (x, y, z)


def lash(loc, r=0.075, turns=3):
    """A binding of cord where sticks cross."""
    for k in range(turns):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=r, minor_radius=0.015,
            location=(loc[0], loc[1], loc[2] + (k - turns * 0.5) * 0.032),
            major_segments=8, minor_segments=4,
            rotation=(random.uniform(-0.2, 0.2), math.pi / 2, 0))
        parts.append(bpy.context.active_object)


def stake(x, y, h, r=0.07):
    """An upright driven into the ground: crooked, thicker at the base."""
    return branch((x, y, -0.06),
                  (random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), 1.0),
                  h + 0.06, r, r * 0.6, bend=0.22)


def thorn_at(x, y, z):
    a = random.uniform(0, 6.283)
    bpy.ops.mesh.primitive_cone_add(radius1=0.013, radius2=0.0,
                                    depth=random.uniform(0.05, 0.13),
                                    location=(x, y, z), vertices=4)
    t = bpy.context.active_object
    t.rotation_euler = (random.uniform(0, 3.1), random.uniform(0, 3.1), a)
    bpy.ops.object.transform_apply(rotation=True)
    parts.append(t)


# --------------------------------------------------------------- styles
if STYLE == "rail":
    H = random.uniform(1.1, 1.35)
    for i in range(4):
        stake(-RUN / 2 + i * (RUN / 3), 0, H * random.uniform(0.94, 1.08), 0.085)
    for frac in (0.42, 0.80):
        z = H * frac
        branch((-RUN / 2 - 0.15, random.uniform(-0.03, 0.03), z),
               (1, random.uniform(-0.06, 0.06), random.uniform(-0.05, 0.05)),
               RUN + 0.3, 0.062, 0.045, bend=0.16)
        for i in range(4):
            lash((-RUN / 2 + i * (RUN / 3), 0, z), 0.1)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "picket":
    H = random.uniform(1.15, 1.45)
    n = int(RUN / 0.19)
    for i in range(n):
        if random.random() < 0.07:
            continue
        x = -RUN / 2 + (i + 0.5) * (RUN / n)
        stake(x + random.uniform(-0.02, 0.02), random.uniform(-0.03, 0.03),
              H * random.uniform(0.78, 1.05), random.uniform(0.036, 0.055))
    for frac in (0.36, 0.82):
        z = H * frac
        branch((-RUN / 2 - 0.1, 0.06, z), (1, 0, random.uniform(-0.05, 0.05)),
               RUN + 0.2, 0.05, 0.038, bend=0.14)
        for k in range(4):
            lash((-RUN / 2 + k * (RUN / 3), 0.04, z), 0.085)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "wattle":
    H = random.uniform(1.0, 1.25)
    n_st = 9
    for i in range(n_st):
        stake(-RUN / 2 + i * (RUN / (n_st - 1)), 0, H, 0.045)
    rows = int(H / 0.14)
    for r_i in range(rows):
        z = 0.08 + r_i * (H - 0.12) / rows
        side = 0.05 if r_i % 2 == 0 else -0.05
        branch((-RUN / 2 - 0.1, side, z),
               (1, -side * 1.5, random.uniform(-0.03, 0.03)),
               RUN + 0.2, 0.03, 0.022, bend=0.55, knots=False)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "lattice":
    H = random.uniform(1.5, 1.85)
    for i in range(3):
        stake(-RUN / 2 + i * (RUN / 2), 0, H, 0.075)
    branch((-RUN / 2, 0.04, H - 0.08), (1, 0, 0), RUN, 0.055, 0.042, bend=0.12)
    branch((-RUN / 2, 0.04, 0.12), (1, 0, 0), RUN, 0.055, 0.042, bend=0.12)
    for d in (1, -1):
        for i in range(6):
            off = -RUN / 2 + (i + 0.4) * (RUN / 6)
            branch((off, 0.06 * d, 0.1), (d * 0.72, 0, 1.0),
                   H * 1.32, 0.035, 0.024, bend=0.22, knots=False)
    for i in range(5):
        lash((-RUN / 2 + i * (RUN / 4), 0.05, H * 0.55), 0.07)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "palm":
    H = random.uniform(1.7, 2.1)
    for i in range(3):
        stake(-RUN / 2 + i * (RUN / 2), 0, H, 0.085)
    for frac in (0.18, 0.9):
        branch((-RUN / 2 - 0.1, 0.05, H * frac), (1, 0, 0), RUN + 0.2, 0.05, 0.04, bend=0.12)
    n = int(RUN / 0.11)
    for i in range(n):
        x = -RUN / 2 + (i + 0.5) * (RUN / n)
        branch((x, 0.08, 0.0), (random.uniform(-0.06, 0.06), 0, 1.0),
               H * random.uniform(0.84, 1.02), 0.024, 0.012, bend=0.32, knots=False, verts=5)
    for k in range(4):
        lash((-RUN / 2 + k * (RUN / 3), 0.06, H * 0.9), 0.075)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "brush":
    H = random.uniform(0.9, 1.2)
    for i in range(5):
        stake(-RUN / 2 + i * (RUN / 4), 0, H * 1.1, 0.06)
    for _ in range(44):
        branch((random.uniform(-RUN / 2, RUN / 2 - 0.8),
                random.uniform(-0.16, 0.16), random.uniform(0.05, H)),
               (1, random.uniform(-0.35, 0.35), random.uniform(-0.3, 0.3)),
               random.uniform(0.7, 1.7), random.uniform(0.02, 0.038), 0.011,
               bend=0.6, knots=False, verts=4)
    rec((0, 0, H / 2), RUN / 2, 0.17, H / 2)

elif STYLE == "thorn":
    H = random.uniform(1.1, 1.4)
    for i in range(4):
        stake(-RUN / 2 + i * (RUN / 3), random.uniform(-0.1, 0.1), H * 1.15, 0.055)
    for _ in range(30):
        bx = random.uniform(-RUN / 2, RUN / 2)
        by = random.uniform(-0.2, 0.2)
        bz = random.uniform(0.08, H * 1.05)
        branch((bx, by, bz),
               (random.uniform(-1, 1), random.uniform(-0.5, 0.5), random.uniform(0.1, 1)),
               random.uniform(0.5, 1.2), 0.03, 0.01, bend=0.75, knots=False, verts=4)
        for _ in range(random.randint(2, 5)):
            thorn_at(bx + random.uniform(-0.3, 0.3),
                     by + random.uniform(-0.15, 0.15),
                     bz + random.uniform(-0.15, 0.15))
    rec((0, 0, H / 2), RUN / 2, 0.2, H / 2)

elif STYLE == "post":
    H = random.uniform(0.9, 1.15)
    for i in range(6):
        stake(-RUN / 2 + i * (RUN / 5), random.uniform(-0.05, 0.05),
              H * random.uniform(0.85, 1.12), 0.06)
    branch((-RUN / 2 - 0.1, 0.04, H * 0.88), (1, 0, random.uniform(-0.07, 0.07)),
           RUN + 0.2, 0.05, 0.036, bend=0.18)
    for k in range(5):
        lash((-RUN / 2 + k * (RUN / 4), 0.02, H * 0.88), 0.08)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "gate":
    H = random.uniform(1.3, 1.55)
    for sx in (-1, 1):
        stake(sx * RUN / 2, 0, H + 0.4, 0.11)
        rec((sx * RUN / 2, 0, (H + 0.4) / 2), 0.14, 0.14, (H + 0.4) / 2)
    gw = RUN - 0.5
    for frac in (0.18, 0.56, 0.94):
        branch((-gw / 2, 0.03, H * frac), (1, 0, random.uniform(-0.05, 0.05)),
               gw, 0.05, 0.04, bend=0.14)
    for sx in (-1, 1):
        branch((sx * gw / 2, 0.03, 0.04), (0, 0, 1), H * 0.98, 0.055, 0.04, bend=0.12)
    branch((-gw / 2, 0.07, H * 0.18), (gw, 0, H * 0.76),
           math.hypot(gw, H * 0.76), 0.04, 0.032, bend=0.1, knots=False)
    for sx in (-1, 1):
        for frac in (0.18, 0.94):
            lash((sx * gw / 2, 0.04, H * frac), 0.08)

elif STYLE == "plank":
    # rough sawn planks nailed across posts, gaps and slipped boards included
    H = random.uniform(1.15, 1.45)
    for i in range(3):
        stake(-RUN / 2 + i * (RUN / 2), 0, H + 0.1, 0.08)
    n = int(H / 0.24)
    for i in range(n):
        z = 0.14 + i * (H - 0.16) / n
        if random.random() < 0.08:
            continue                              # a board gone
        drop = random.uniform(-0.03, 0.03)
        lean = random.uniform(-0.02, 0.02)
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0.05, z + drop))
        b = bpy.context.active_object
        b.scale = ((RUN + 0.2) / 2, 0.016, random.uniform(0.085, 0.115))
        b.rotation_euler = (0, lean, random.uniform(-0.008, 0.008))
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        parts.append(b)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)

elif STYLE == "plankgate":
    H = random.uniform(1.2, 1.45)
    for sx in (-1, 1):
        stake(sx * RUN / 2, 0, H + 0.35, 0.1)
        rec((sx * RUN / 2, 0, (H + 0.35) / 2), 0.13, 0.13, (H + 0.35) / 2)
    gw = RUN - 0.5
    for i in range(4):
        z = 0.16 + i * (H - 0.2) / 4
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0.04, z))
        b = bpy.context.active_object
        b.scale = (gw / 2, 0.015, 0.1)
        b.rotation_euler = (0, random.uniform(-0.015, 0.015), 0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        parts.append(b)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0.07, H * 0.55))
    d2 = bpy.context.active_object
    d2.scale = (0.05, 0.014, H * 0.44)
    d2.rotation_euler = (0, math.atan2(gw, H * 0.8), 0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    parts.append(d2)

elif STYLE == "low":
    H = random.uniform(0.4, 0.55)
    n = int(RUN / 0.16)
    for i in range(n):
        stake(-RUN / 2 + (i + 0.5) * (RUN / n), random.uniform(-0.03, 0.03),
              H * random.uniform(0.8, 1.12), 0.04)
    branch((-RUN / 2, 0.05, H * 0.82), (1, 0, 0), RUN, 0.036, 0.028, bend=0.18)
    rec((0, 0, H / 2), RUN / 2, 0.08, H / 2)

else:                     # brace
    H = random.uniform(1.15, 1.4)
    for i in range(3):
        stake(-RUN / 2 + i * (RUN / 2), 0, H, 0.095)
    for frac in (0.3, 0.68, 0.97):
        branch((-RUN / 2 - 0.1, 0.04, H * frac), (1, 0, random.uniform(-0.06, 0.06)),
               RUN + 0.2, 0.055, 0.042, bend=0.15)
    half = RUN / 2
    for sx in (-1, 1):
        branch((sx * half * 0.95, 0.07, 0.06), (-sx * 0.8, 0, 1.0),
               math.hypot(half, H) * 0.9, 0.045, 0.03, bend=0.12)
    for k in range(3):
        lash((-RUN / 2 + k * (RUN / 2), 0.05, H * 0.68), 0.085)
    rec((0, 0, H / 2), RUN / 2, 0.1, H / 2)


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
bpy.ops.mesh.remove_doubles(threshold=0.0006)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=0.9)
bpy.ops.object.mode_set(mode='OBJECT')

# Cut wood, mostly dark, each style its own tone.
TINT = {
    "rail":    (0.19, 0.13, 0.085),
    "picket":  (0.24, 0.17, 0.115),
    "wattle":  (0.30, 0.22, 0.14),
    "lattice": (0.16, 0.11, 0.08),
    "palm":    (0.34, 0.26, 0.15),
    "brush":   (0.22, 0.16, 0.10),
    "thorn":   (0.18, 0.14, 0.10),
    "post":    (0.21, 0.15, 0.10),
    "gate":    (0.14, 0.10, 0.075),
    "low":     (0.28, 0.20, 0.13),
    "plank":   (0.42, 0.38, 0.33), "plankgate": (0.40, 0.36, 0.31),
    "brace":   (0.17, 0.12, 0.085),
}.get(STYLE, (0.22, 0.16, 0.11))

mat = bpy.data.materials.new(STYLE)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (TINT[0], TINT[1], TINT[2], 1)
bsdf.inputs["Roughness"].default_value = 0.94
tex_choice = "t_plank_d.jpg" if STYLE in ("plank", "plankgate") else "t_wood_d.jpg"
tex_path = os.path.abspath(os.path.join(ASSETS, tex_choice))
tn = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    mixc = nt.nodes.new('ShaderNodeMixRGB')
    mixc.blend_type = 'MULTIPLY'
    mixc.inputs['Fac'].default_value = 1.0
    mixc.inputs['Color2'].default_value = (TINT[0] * 2.6, TINT[1] * 2.6, TINT[2] * 2.6, 1)
    nt.links.new(tn.outputs['Color'], mixc.inputs['Color1'])
    nt.links.new(mixc.outputs['Color'], bsdf.inputs['Base Color'])

ob.data.materials.clear()
ob.data.materials.append(mat)

while len(ob.data.color_attributes):
    ob.data.color_attributes.remove(ob.data.color_attributes[0])
ob.data.color_attributes.active_color = ob.data.color_attributes.new(
    name="ao", type='FLOAT_COLOR', domain='CORNER')
scene.render.bake.target = 'VERTEX_COLORS'
scene.render.bake.margin = 2
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
try:
    bpy.ops.object.bake(type='AO')
    data = ob.data.color_attributes["ao"].data
    for i in range(len(data)):
        ao = 0.34 + 0.62 * data[i].color[0]
        g = 0.90 + 0.18 * random.random()      # a little tone from stick to stick
        data[i].color = (ao * g, ao * g, ao * g, 1.0)
except Exception as e:
    print("bake failed:", e)

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d colliders=%d"
      % (STYLE, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

if tn is not None:
    tn.image.pack()
    vcn = nt.nodes.new('ShaderNodeVertexColor')
    vcn.layer_name = "ao"
    mixa = nt.nodes.new('ShaderNodeMixRGB')
    mixa.blend_type = 'MULTIPLY'
    mixa.inputs['Fac'].default_value = 1.0
    nt.links.new(mixc.outputs['Color'], mixa.inputs['Color1'])
    nt.links.new(vcn.outputs['Color'], mixa.inputs['Color2'])
    nt.links.new(mixa.outputs['Color'], bsdf.inputs['Base Color'])

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
