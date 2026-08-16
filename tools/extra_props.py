"""Adds the household, market and armoury props to make_props.py."""
import pathlib

p = pathlib.Path("tools/make_props.py")
s = p.read_text(encoding="utf-8")

EXTRA = '''elif KIND == "carpet":
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

elif KIND == "stones":'''

s = s.replace('elif KIND == "stones":', EXTRA, 1)

TINTS = '''    "well": (0.62, 0.53, 0.40), "stall": (0.42, 0.32, 0.21),
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
    "firewood": (0.32, 0.22, 0.14),
}'''
s = s.replace('''    "well": (0.62, 0.53, 0.40), "stall": (0.42, 0.32, 0.21),
    "stones": (0.50, 0.45, 0.38),
}''', TINTS)

p.write_text(s, encoding="utf-8")
print("prop library expanded")
