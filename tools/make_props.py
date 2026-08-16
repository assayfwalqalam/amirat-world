# The clutter that makes a town look lived in: barrels, crates, jars, sacks,
# awnings, benches, a handcart, a well. All made here so they match the walls.
#   blender --background --python make_props.py -- <kind> <out.glb> [assets_dir]
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "barrel"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
parts = []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def box(sx, sy, sz, loc, rot=0.0, collide=False):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    parts.append(ob)
    return ob


def cyl(r1, r2, h, loc, rot=(0, 0, 0), verts=14, collide=False):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    if collide:
        rec(loc, max(r1, r2), max(r1, r2), h / 2)
    parts.append(ob)
    return ob


def sphere(r, loc, seg=14):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    ob = bpy.context.active_object
    parts.append(ob)
    return ob


def torus(rmaj, rmin, loc, seg=16):
    bpy.ops.mesh.primitive_torus_add(major_radius=rmaj, minor_radius=rmin, location=loc,
                                     major_segments=seg, minor_segments=6)
    ob = bpy.context.active_object
    parts.append(ob)
    return ob


def jitter(ob, amt=0.02):
    """A little irregularity, so nothing looks machine made."""
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("sub", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = 1
    bpy.ops.object.modifier_apply(modifier=m.name)
    t = bpy.data.textures.new("n", 'CLOUDS')
    t.noise_scale = 0.6
    d = ob.modifiers.new("d", 'DISPLACE')
    d.texture = t
    d.strength = amt
    d.mid_level = 0.5
    bpy.ops.object.modifier_apply(modifier=d.name)


# --------------------------------------------------------------- shapes
if KIND == "barrel":
    b = cyl(0.34, 0.34, 0.92, (0, 0, 0.46), verts=16, collide=True)
    jitter(b, 0.012)
    for z in (0.16, 0.46, 0.76):
        torus(0.355, 0.028, (0, 0, z))
    cyl(0.30, 0.30, 0.04, (0, 0, 0.93), verts=16)

elif KIND == "barrels":
    spots = [(0, 0, 0), (0.78, 0.12, 0), (0.36, 0.72, 0), (0.42, 0.3, 0.94)]
    for i, sp in enumerate(spots):
        b = cyl(0.33, 0.33, 0.9, (sp[0], sp[1], sp[2] + 0.45), verts=14,
                collide=True)
        jitter(b, 0.012)
        for z in (0.16, 0.72):
            torus(0.345, 0.026, (sp[0], sp[1], sp[2] + z))

elif KIND == "crates":
    for i, sp in enumerate([(0, 0, 0, 0.0), (0.92, 0.1, 0, 0.4), (0.3, 0.84, 0, -0.3), (0.5, 0.35, 0.72, 0.2)]):
        s = random.uniform(0.62, 0.78)
        c = box(s, s, s * 0.92, (sp[0], sp[1], sp[2] + s * 0.46), sp[3], collide=True)
        jitter(c, 0.01)
        for e in (-1, 1):
            box(s + 0.03, 0.05, 0.07, (sp[0], sp[1] + e * s / 2, sp[2] + s * 0.46), sp[3])

elif KIND == "jars":
    for i, sp in enumerate([(0, 0), (0.44, 0.14), (0.2, 0.46), (-0.36, 0.3)]):
        h = random.uniform(0.5, 0.82)
        r = h * 0.34
        body = sphere(r, (sp[0], sp[1], r * 0.92))
        body.scale = (1, 1, 1.25)
        bpy.ops.object.transform_apply(scale=True)
        cyl(r * 0.42, r * 0.5, h * 0.34, (sp[0], sp[1], r * 1.7), verts=12)
        torus(r * 0.5, 0.022, (sp[0], sp[1], r * 1.85), seg=12)
        rec((sp[0], sp[1], h * 0.4), r, r, h * 0.4)

elif KIND == "sacks":
    for i, sp in enumerate([(0, 0, 0), (0.5, 0.16, 0), (0.24, 0.5, 0), (0.3, 0.24, 0.44)]):
        s = random.uniform(0.34, 0.46)
        b = sphere(s, (sp[0], sp[1], sp[2] + s * 0.86))
        b.scale = (1.0, 0.78, 1.15)
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.03)
        cyl(s * 0.3, s * 0.16, s * 0.4, (sp[0], sp[1], sp[2] + s * 1.7), verts=10)
        rec((sp[0], sp[1], sp[2] + s * 0.8), s, s * 0.8, s * 0.9)

elif KIND == "awning":
    # four poles and a sagging cloth, the shade over a stall
    W, D, H = 3.4, 2.4, 2.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.055, 0.05, H, (sx * W / 2, sy * D / 2, H / 2), verts=8, collide=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=6, size=1,
                                    location=(0, 0, H))
    cloth = bpy.context.active_object
    cloth.scale = (W / 2 + 0.2, D / 2 + 0.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    me = cloth.data
    for v in me.vertices:
        u = abs(v.co.x) / (W / 2 + 0.2)
        w = abs(v.co.y) / (D / 2 + 0.2)
        v.co.z -= (1 - u * u) * (1 - w * w) * 0.34
    sol = cloth.modifiers.new("sol", 'SOLIDIFY')
    sol.thickness = 0.03
    bpy.context.view_layer.objects.active = cloth
    bpy.ops.object.modifier_apply(modifier=sol.name)
    parts.append(cloth)
    box(W + 0.3, 0.07, 0.07, (0, -D / 2, H))
    box(W + 0.3, 0.07, 0.07, (0, D / 2, H))

elif KIND == "bench":
    box(1.9, 0.44, 0.1, (0, 0, 0.46), collide=True)
    for sx in (-1, 1):
        box(0.13, 0.4, 0.44, (sx * 0.78, 0, 0.22), collide=True)
    box(1.9, 0.1, 0.36, (0, 0.2, 0.74))

elif KIND == "cart":
    box(1.7, 0.95, 0.14, (0, 0, 0.62), collide=True)
    for sy in (-1, 1):
        box(1.7, 0.08, 0.3, (0, sy * 0.46, 0.8), collide=True)
    box(0.08, 0.95, 0.3, (-0.84, 0, 0.8))
    for sy in (-1, 1):
        w = cyl(0.44, 0.44, 0.1, (0.2, sy * 0.56, 0.44), rot=(math.pi / 2, 0, 0), verts=16)
        for k in range(6):
            a = k * math.pi / 3
            box(0.06, 0.06, 0.82, (0.2 + math.cos(a) * 0, sy * 0.56, 0.44), 0)
    for sx in (-1, 1):
        cyl(0.05, 0.04, 1.5, (-1.5, sx * 0.3, 0.72), rot=(0, math.pi / 2, 0), verts=8)

elif KIND == "well":
    R = 1.15
    for i in range(16):
        a = i * math.pi * 2 / 16
        b = box(0.42, 0.3, 1.0, (math.cos(a) * R, math.sin(a) * R, 0.5), -a, collide=True)
        jitter(b, 0.015)
    torus(R, 0.13, (0, 0, 1.02), seg=20)
    for sx in (-1, 1):
        cyl(0.08, 0.07, 2.4, (sx * (R + 0.1), 0, 1.2), verts=8, collide=True)
    cyl(0.06, 0.06, 2.6, (0, 0, 2.4), rot=(0, math.pi / 2, 0), verts=8)
    cyl(0.09, 0.09, 1.9, (0, 0, 2.4), rot=(0, math.pi / 2, 0), verts=10)
    box(0.05, 0.05, 0.9, (0, 0, 1.95))
    bk = cyl(0.2, 0.17, 0.28, (0, 0, 1.36), verts=12)
    torus(0.2, 0.02, (0, 0, 1.48), seg=12)

elif KIND == "stall":
    # a market stall: bench, awning, and goods stacked on it
    box(2.2, 1.0, 0.12, (0, 0, 0.86), collide=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.06, 0.055, 0.86, (sx * 1.0, sy * 0.42, 0.43), verts=8, collide=True)
            cyl(0.055, 0.05, 2.3, (sx * 1.1, sy * 0.5, 1.15), verts=8, collide=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=5, size=1, location=(0, 0, 2.3))
    cloth = bpy.context.active_object
    cloth.scale = (1.3, 0.72, 1)
    bpy.ops.object.transform_apply(scale=True)
    for v in cloth.data.vertices:
        u = abs(v.co.x) / 1.3
        v.co.z -= (1 - u * u) * 0.26
    sol = cloth.modifiers.new("sol", 'SOLIDIFY')
    sol.thickness = 0.03
    bpy.context.view_layer.objects.active = cloth
    bpy.ops.object.modifier_apply(modifier=sol.name)
    parts.append(cloth)
    for i in range(5):
        s = random.uniform(0.16, 0.26)
        sphere(s, (random.uniform(-0.85, 0.85), random.uniform(-0.3, 0.3), 0.92 + s))

elif KIND == "carpet":
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=7, size=1, location=(0, 0, 0.02))
    c = bpy.context.active_object
    c.scale = (1.1, 0.75, 1)
    bpy.ops.object.transform_apply(scale=True)
    for v in c.data.vertices:
        v.co.z += math.sin(v.co.x * 3.1) * 0.012 + math.cos(v.co.y * 4.0) * 0.01
    sol = c.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.03
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.modifier_apply(modifier=sol.name)
    parts.append(c)

elif KIND == "cushions":
    for sp in [(0, 0), (0.42, 0.1), (0.16, 0.4)]:
        b = sphere(0.24, (sp[0], sp[1], 0.14))
        b.scale = (1.15, 1.0, 0.42)
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.02)

elif KIND == "table":
    box(1.05, 0.7, 0.07, (0, 0, 0.42), collide=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.045, 0.04, 0.4, (sx * 0.44, sy * 0.27, 0.2), verts=8)
    box(1.0, 0.06, 0.05, (0, 0, 0.2))

elif KIND == "stool":
    cyl(0.2, 0.22, 0.06, (0, 0, 0.42), verts=12, collide=True)
    for k in range(3):
        a = k * math.pi * 2 / 3
        cyl(0.032, 0.028, 0.4, (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.2), verts=6)

elif KIND == "chest":
    box(0.82, 0.5, 0.42, (0, 0, 0.21), collide=True)
    cyl(0.25, 0.25, 0.82, (0, 0, 0.44), rot=(0, math.pi / 2, 0), verts=12)
    for sy in (-1, 1):
        box(0.86, 0.05, 0.06, (0, sy * 0.2, 0.2))
    box(0.1, 0.06, 0.1, (0, -0.26, 0.36))

elif KIND == "books":
    z = 0.0
    for i in range(random.randint(3, 5)):
        h = random.uniform(0.05, 0.08)
        box(random.uniform(0.24, 0.32), random.uniform(0.18, 0.24), h,
            (random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02), z + h / 2),
            random.uniform(-0.2, 0.2))
        z += h
    box(0.22, 0.16, 0.03, (0.16, 0.2, 0.015), 0.6)

elif KIND == "scrolls":
    for i in range(4):
        cyl(0.035, 0.035, random.uniform(0.24, 0.34),
            (random.uniform(-0.12, 0.12), random.uniform(-0.1, 0.1), 0.035),
            rot=(math.pi / 2, 0, random.uniform(0, 3)), verts=10)
    box(0.26, 0.2, 0.008, (0.05, -0.12, 0.005), 0.3)

elif KIND == "inkset":
    cyl(0.07, 0.06, 0.09, (0, 0, 0.045), verts=12)
    torus(0.06, 0.012, (0, 0, 0.09), seg=12)
    cyl(0.012, 0.004, 0.3, (0.1, 0.03, 0.14), rot=(0.2, 0.5, 0), verts=6)
    box(0.24, 0.17, 0.01, (-0.14, 0.02, 0.005), 0.2)

elif KIND == "bowl":
    b = sphere(0.16, (0, 0, 0.1))
    b.scale = (1, 1, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    for i in range(5):
        a = i * 1.3
        sphere(0.055, (math.cos(a) * 0.06, math.sin(a) * 0.06, 0.15))

elif KIND == "bread":
    for i in range(3):
        b = sphere(0.13, (i * 0.22 - 0.22, random.uniform(-0.04, 0.04), 0.05))
        b.scale = (1.25, 0.8, 0.4)
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.012)

elif KIND == "pot":
    b = sphere(0.28, (0, 0, 0.26))
    b.scale = (1, 1, 1.1)
    bpy.ops.object.transform_apply(scale=True)
    cyl(0.13, 0.16, 0.12, (0, 0, 0.52), verts=12)
    torus(0.16, 0.02, (0, 0, 0.56), seg=12)
    rec((0, 0, 0.28), 0.28, 0.28, 0.3)

elif KIND == "plantpot":
    cyl(0.19, 0.24, 0.34, (0, 0, 0.17), verts=14, collide=True)
    torus(0.24, 0.022, (0, 0, 0.33), seg=14)
    for i in range(9):
        a = random.uniform(0, 6.28)
        lean = random.uniform(0.2, 0.5)
        cyl(0.012, 0.004, random.uniform(0.3, 0.55),
            (math.cos(a) * 0.06, math.sin(a) * 0.06, 0.5),
            rot=(lean * math.sin(a), lean * math.cos(a), 0), verts=5)

elif KIND == "broom":
    cyl(0.022, 0.02, 1.3, (0, 0, 0.72), rot=(0.16, 0, 0), verts=8)
    for i in range(14):
        a = random.uniform(0, 6.28)
        cyl(0.008, 0.004, 0.28, (math.cos(a) * 0.05, math.sin(a) * 0.05 - 0.11, 0.14),
            rot=(0.16 + random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 0), verts=4)

elif KIND == "spears":
    for i in range(3):
        x = i * 0.12 - 0.12
        cyl(0.022, 0.018, 2.1, (x, 0, 1.05), rot=(0.1, random.uniform(-0.06, 0.06), 0), verts=8)
        cyl(0.035, 0.0, 0.28, (x + 0.1, 0, 2.16), rot=(0.1, 0, 0), verts=8)

elif KIND == "swordrack":
    box(0.9, 0.12, 0.06, (0, 0, 0.9), collide=True)
    for sx in (-1, 1):
        box(0.08, 0.1, 0.9, (sx * 0.42, 0, 0.45), collide=True)
    for i in (-1, 1):
        box(0.05, 0.02, 0.72, (i * 0.18, 0.02, 0.56))
        box(0.14, 0.03, 0.05, (i * 0.18, 0.02, 0.2))

elif KIND == "bowarrows":
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.018, location=(0, 0, 0.5),
                                     major_segments=18, minor_segments=5,
                                     rotation=(math.pi / 2, 0, 0))
    parts.append(bpy.context.active_object)
    cyl(0.14, 0.16, 0.42, (0.44, 0.06, 0.21), verts=12)
    for i in range(6):
        cyl(0.008, 0.008, 0.66,
            (0.44 + random.uniform(-0.05, 0.05), 0.06 + random.uniform(-0.05, 0.05), 0.5),
            rot=(random.uniform(-0.1, 0.1), random.uniform(-0.08, 0.08), 0), verts=4)

elif KIND == "basket":
    b = cyl(0.24, 0.19, 0.3, (0, 0, 0.15), verts=14, collide=True)
    jitter(b, 0.012)
    torus(0.24, 0.02, (0, 0, 0.3), seg=14)
    for i in range(4):
        sphere(0.07, (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 0.32))

elif KIND == "brazier":
    cyl(0.26, 0.2, 0.16, (0, 0, 0.62), verts=14, collide=True)
    for k in range(3):
        a = k * math.pi * 2 / 3
        cyl(0.03, 0.025, 0.56, (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.28),
            rot=(0.12 * math.sin(a), -0.12 * math.cos(a), 0), verts=6)
    torus(0.24, 0.022, (0, 0, 0.7), seg=14)

elif KIND == "oillamp":
    b = sphere(0.1, (0, 0, 0.07))
    b.scale = (1.3, 1.0, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    cyl(0.03, 0.012, 0.16, (0.13, 0, 0.09), rot=(0, 1.2, 0), verts=8)
    torus(0.05, 0.012, (-0.12, 0, 0.09), seg=10)

elif KIND == "waterjug":
    b = sphere(0.2, (0, 0, 0.2))
    b.scale = (1, 1, 1.25)
    bpy.ops.object.transform_apply(scale=True)
    cyl(0.06, 0.08, 0.22, (0, 0, 0.44), verts=12)
    torus(0.09, 0.016, (0, 0, 0.53), seg=12)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.016, location=(0.19, 0, 0.34),
                                     major_segments=10, minor_segments=5, rotation=(0, 0.4, 0))
    parts.append(bpy.context.active_object)
    rec((0, 0, 0.25), 0.2, 0.2, 0.28)

elif KIND == "ropecoil":
    for i in range(5):
        torus(0.2 - i * 0.012, 0.028, (0, 0, 0.03 + i * 0.045), seg=16)

elif KIND == "firewood":
    for i in range(7):
        cyl(0.05, 0.045, random.uniform(0.6, 0.9),
            (random.uniform(-0.2, 0.2), random.uniform(-0.15, 0.15), 0.06 + (i % 3) * 0.1),
            rot=(0, math.pi / 2, random.uniform(0, 3.14)), verts=6)

elif KIND == "torch":
    # an iron bracket driven into a wall, holding a pitch-soaked head
    box(0.16, 0.34, 0.16, (0, 0.1, 0), 0, True)                  # the wall plate
    cyl(0.035, 0.03, 0.52, (0, -0.16, 0.14), rot=(1.05, 0, 0), verts=8)   # the arm
    cyl(0.055, 0.05, 0.16, (0, -0.36, 0.36), rot=(0.25, 0, 0), verts=8)   # the collar
    ring = torus(0.1, 0.018, (0, -0.38, 0.42), seg=12)
    cyl(0.045, 0.055, 0.62, (0, -0.4, 0.7), rot=(0.12, 0, 0), verts=8)    # the shaft
    head = sphere(0.11, (0, -0.44, 1.02))
    head.scale = (1, 1, 1.3)
    bpy.ops.object.transform_apply(scale=True)
    jitter(head, 0.02)

elif KIND == "torchpost":
    # a free-standing torch, for courtyards and gateways
    cyl(0.2, 0.26, 0.22, (0, 0, 0.11), verts=12, collide=True)
    cyl(0.06, 0.075, 2.3, (0, 0, 1.2), verts=10, collide=True)
    for k in range(3):
        a = k * math.pi * 2 / 3
        cyl(0.022, 0.02, 0.42, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.3),
            rot=(0.5 * math.sin(a), -0.5 * math.cos(a), 0), verts=6)
    cyl(0.16, 0.1, 0.2, (0, 0, 2.4), verts=12)
    torus(0.15, 0.02, (0, 0, 2.48), seg=12)
    hd = sphere(0.13, (0, 0, 2.6))
    hd.scale = (1, 1, 1.2)
    bpy.ops.object.transform_apply(scale=True)
    jitter(hd, 0.02)

elif KIND == "stones":
    for i in range(9):
        r = random.uniform(0.18, 0.42)
        b = sphere(r, (random.uniform(-1.3, 1.3), random.uniform(-1.0, 1.0), r * 0.55))
        b.scale = (1.0, random.uniform(0.7, 1.1), random.uniform(0.5, 0.8))
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.05)

# ------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

m = ob.modifiers.new("bv", 'BEVEL')
m.width = 0.012
m.segments = 1
m.limit_method = 'ANGLE'
m.angle_limit = math.radians(40)
bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=1.1)
bpy.ops.object.mode_set(mode='OBJECT')

TINT = {
    "barrel": (0.30, 0.19, 0.11), "barrels": (0.30, 0.19, 0.11),
    "crates": (0.38, 0.26, 0.15), "jars": (0.42, 0.24, 0.16),
    "sacks": (0.52, 0.44, 0.30), "awning": (0.55, 0.46, 0.33),
    "bench": (0.32, 0.21, 0.13), "cart": (0.31, 0.20, 0.12),
    "well": (0.62, 0.53, 0.40), "stall": (0.42, 0.32, 0.21),
    "stones": (0.50, 0.45, 0.38), "carpet": (0.42, 0.14, 0.13),
    "cushions": (0.34, 0.16, 0.20), "table": (0.33, 0.22, 0.13),
    "stool": (0.34, 0.23, 0.14), "chest": (0.30, 0.20, 0.12),
    "books": (0.32, 0.22, 0.18), "scrolls": (0.66, 0.60, 0.46),
    "inkset": (0.22, 0.18, 0.16), "bowl": (0.44, 0.26, 0.17),
    "bread": (0.62, 0.46, 0.26), "pot": (0.44, 0.26, 0.18),
    "plantpot": (0.40, 0.26, 0.18), "broom": (0.46, 0.36, 0.20),
    "spears": (0.34, 0.24, 0.15), "swordrack": (0.31, 0.21, 0.13),
    "bowarrows": (0.35, 0.25, 0.15), "basket": (0.52, 0.40, 0.22),
    "brazier": (0.24, 0.20, 0.17), "oillamp": (0.46, 0.34, 0.20),
    "waterjug": (0.45, 0.28, 0.19), "ropecoil": (0.50, 0.42, 0.28),
    "firewood": (0.32, 0.22, 0.14), "torch": (0.20, 0.17, 0.15),
    "torchpost": (0.24, 0.20, 0.16),
}.get(KIND, (0.45, 0.36, 0.26))

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (TINT[0], TINT[1], TINT[2], 1)
bsdf.inputs["Roughness"].default_value = 0.95
ob.data.materials.clear()
ob.data.materials.append(mat)

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
        ao = 0.32 + 0.68 * data[i].color[0]
        data[i].color = (ao, ao, ao, 1.0)
except Exception as e:
    print("bake failed:", e)

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
