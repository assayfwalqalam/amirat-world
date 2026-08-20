# Market stalls: several shapes of stall, each selling something different.
#   blender --background --python make_stall.py -- <shape> <trade> <out.glb> [assets]
#
# Shapes: canopy, leanto, trestle, barrow, mat, booth, rack
# Trades: spice, pottery, cloth, fruit, grain, basket, metal, rope, bread, wood
#
# The goods are what make a market read, and they are all things, never people
# or animals. Spice goes in conical heaps, cloth in folded bolts and hanging
# lengths, grain in open sacks with a heaped top, and so on. Awning cloth takes
# its own colour per stall so a row of them is not one colour repeated.
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHAPE = argv[0] if argv else "canopy"
TRADE = argv[1] if len(argv) > 1 else "spice"
OUT = argv[2] if len(argv) > 2 else (SHAPE + "_" + TRADE + ".glb")
ASSETS = argv[3] if len(argv) > 3 else "assets"
random.seed(sum(ord(c) for c in SHAPE + TRADE) * 3167)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

COLLIDERS = []
GROUPS = {"wood": [], "cloth": [], "goods": []}


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
                      "h": [round(hx, 3), round(hz, 3), round(hy, 3)]})


def into(g):
    GROUPS[g].append(bpy.context.active_object)
    return bpy.context.active_object


def box(sx, sy, sz, loc, rot=0.0, g="wood", collide=False):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    return into(g)


def rod(r, h, loc, rot=(0, 0, 0), g="wood", verts=7):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    return into(g)


def ball(r, loc, g="goods", seg=8, squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg,
                                         ring_count=max(4, seg // 2))
    ob = bpy.context.active_object
    if squash != 1.0:
        for v in ob.data.vertices:
            v.co.z *= squash
    return into(g)


def cone(r, h, loc, g="goods", verts=12):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.008, depth=h, location=loc,
                                    vertices=verts)
    return into(g)


def sheet(w, d, loc, sag=0.12, rot=0.0, g="cloth"):
    """A hanging or stretched cloth, with a sag in it."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=9, y_subdivisions=7, size=1, location=loc)
    ob = bpy.context.active_object
    ob.scale = (w, d, 1)
    ob.rotation_euler[2] = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    for v in ob.data.vertices:
        u = v.co.x / max(0.01, w)
        t = v.co.y / max(0.01, d)
        v.co.z -= (1 - u * u) * (1 - t * t) * sag
        v.co.z += random.uniform(-0.012, 0.012)
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.016
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=sol.name)
    return into(g)


# ------------------------------------------------------------- the goods
def goods(cx, cy, z, w, d):
    """Whatever this stall sells, laid out on the counter."""
    if TRADE == "spice":
        for i in range(random.randint(4, 7)):
            x = cx + random.uniform(-w / 2 + 0.15, w / 2 - 0.15)
            y = cy + random.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            r = random.uniform(0.11, 0.17)
            bpy.ops.mesh.primitive_cylinder_add(radius=r * 1.15, depth=0.05,
                                                location=(x, y, z + 0.025), vertices=12)
            into("wood")
            cone(r, random.uniform(0.12, 0.22), (x, y, z + 0.11))
    elif TRADE == "pottery":
        for i in range(random.randint(5, 9)):
            x = cx + random.uniform(-w / 2 + 0.12, w / 2 - 0.12)
            y = cy + random.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            r = random.uniform(0.06, 0.13)
            b = ball(r, (x, y, z + r * 0.8), squash=random.uniform(0.9, 1.5))
            bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.4, depth=r * 0.7,
                                                location=(x, y, z + r * 1.7), vertices=8)
            into("goods")
    elif TRADE == "cloth":
        for i in range(random.randint(3, 5)):
            x = cx + random.uniform(-w / 2 + 0.2, w / 2 - 0.2)
            box(random.uniform(0.3, 0.5), random.uniform(0.2, 0.3),
                random.uniform(0.06, 0.12), (x, cy, z + 0.06), random.uniform(-0.3, 0.3), "cloth")
        for i in range(random.randint(2, 4)):      # lengths hung up to show
            x = cx + random.uniform(-w / 2, w / 2)
            sheet(0.16, 0.02, (x, cy - d / 2 - 0.08, z + 0.9), 0.0,
                  0.0, "cloth")
    elif TRADE == "fruit":
        for i in range(random.randint(3, 5)):
            x = cx + random.uniform(-w / 2 + 0.18, w / 2 - 0.18)
            y = cy + random.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=0.07,
                                                location=(x, y, z + 0.035), vertices=12)
            into("wood")
            for k in range(random.randint(5, 11)):
                a = random.uniform(0, 6.283)
                rr = random.uniform(0, 0.1)
                ball(random.uniform(0.035, 0.06),
                     (x + math.cos(a) * rr, y + math.sin(a) * rr,
                      z + 0.09 + random.uniform(0, 0.06)))
    elif TRADE == "grain":
        for i in range(random.randint(2, 4)):
            x = cx + random.uniform(-w / 2 + 0.2, w / 2 - 0.2)
            y = cy + random.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            s = ball(0.19, (x, y, z + 0.16), squash=1.15, g="cloth")
            for v in s.data.vertices:
                v.co.x += random.uniform(-0.02, 0.02)
                v.co.y += random.uniform(-0.02, 0.02)
            ball(0.15, (x, y, z + 0.33), squash=0.5)      # the heaped top
    elif TRADE == "basket":
        for i in range(random.randint(4, 7)):
            x = cx + random.uniform(-w / 2 + 0.15, w / 2 - 0.15)
            y = cy + random.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            st = random.randint(1, 3)
            for k in range(st):
                bpy.ops.mesh.primitive_cone_add(radius1=0.11, radius2=0.15, depth=0.16,
                                                location=(x, y, z + 0.08 + k * 0.15), vertices=12)
                into("goods")
    elif TRADE == "metal":
        for i in range(random.randint(4, 7)):
            x = cx + random.uniform(-w / 2 + 0.14, w / 2 - 0.14)
            y = cy + random.uniform(-d / 2 + 0.08, d / 2 - 0.08)
            if random.random() < 0.5:
                bpy.ops.mesh.primitive_cylinder_add(radius=random.uniform(0.08, 0.15),
                                                    depth=0.025, location=(x, y, z + 0.015),
                                                    vertices=14)
                into("goods")
            else:
                ball(random.uniform(0.05, 0.09), (x, y, z + 0.07), squash=0.7)
                rod(0.012, 0.16, (x + 0.1, y, z + 0.08), (0, 0.5, 0), "goods", 6)
    elif TRADE == "rope":
        for i in range(random.randint(3, 5)):
            x = cx + random.uniform(-w / 2 + 0.16, w / 2 - 0.16)
            y = cy + random.uniform(-d / 2 + 0.08, d / 2 - 0.08)
            for k in range(4):
                bpy.ops.mesh.primitive_torus_add(major_radius=0.15 - k * 0.012,
                                                 minor_radius=0.024,
                                                 location=(x, y, z + 0.03 + k * 0.045),
                                                 major_segments=14, minor_segments=5)
                into("goods")
    elif TRADE == "bread":
        for i in range(random.randint(3, 6)):
            x = cx + random.uniform(-w / 2 + 0.16, w / 2 - 0.16)
            y = cy + random.uniform(-d / 2 + 0.08, d / 2 - 0.08)
            for k in range(random.randint(2, 5)):
                b = ball(0.13, (x + random.uniform(-0.02, 0.02),
                                y + random.uniform(-0.02, 0.02), z + 0.02 + k * 0.035),
                         squash=0.22)
    else:                              # wood: bundled sticks and split billets
        for i in range(random.randint(2, 4)):
            x = cx + random.uniform(-w / 2 + 0.2, w / 2 - 0.2)
            for k in range(random.randint(5, 9)):
                rod(0.022, random.uniform(0.45, 0.7),
                    (x + random.uniform(-0.06, 0.06), cy + random.uniform(-0.08, 0.08),
                     z + 0.03 + k * 0.035),
                    (0, math.pi / 2, random.uniform(-0.2, 0.2)), "goods", 5)


# ------------------------------------------------------------- the shapes
if SHAPE == "canopy":
    W, D, H = 2.6, 1.6, 2.25
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod(0.055, H, (sx * W / 2, sy * D / 2, H / 2),
                (random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02), 0))
    for sy in (-1, 1):
        box(W + 0.2, 0.06, 0.07, (0, sy * D / 2, H))
    sheet(W / 2 + 0.2, D / 2 + 0.15, (0, 0, H + 0.05), 0.16)
    box(W - 0.2, D - 0.5, 0.06, (0, 0.1, 0.85), 0, "wood", True)
    for sx in (-1, 1):
        box(0.09, 0.09, 0.85, (sx * (W / 2 - 0.25), 0.1, 0.42))
    goods(0, 0.1, 0.88, W - 0.3, D - 0.6)
    rec((0, 0, 1.1), W / 2, D / 2, 1.1)

elif SHAPE == "leanto":
    W, D, H = 2.4, 1.3, 2.1
    for sx in (-1, 1):
        rod(0.06, H, (sx * W / 2, -D / 2, H / 2))
        rod(0.06, H * 0.72, (sx * W / 2, D / 2, H * 0.36))
    box(W + 0.2, 0.06, 0.07, (0, -D / 2, H))
    box(W + 0.2, 0.06, 0.07, (0, D / 2, H * 0.72))
    sh = sheet(W / 2 + 0.1, D / 2 + 0.1, (0, 0, H * 0.86), 0.1)
    sh.rotation_euler = (math.atan2(H - H * 0.72, D), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    box(W - 0.3, D - 0.4, 0.06, (0, 0, 0.8), 0, "wood", True)
    goods(0, 0, 0.83, W - 0.4, D - 0.5)
    rec((0, 0, 1.0), W / 2, D / 2, 1.0)

elif SHAPE == "trestle":
    W, D = 2.2, 0.8
    for sx in (-1, 1):
        for a in (-1, 1):
            rod(0.045, 0.9, (sx * (W / 2 - 0.2) + a * 0.14, a * D / 2, 0.45),
                (a * 0.16, 0, 0))
        box(0.5, D + 0.1, 0.05, (sx * (W / 2 - 0.2), 0, 0.5))
    box(W, D, 0.055, (0, 0, 0.9), 0, "wood", True)
    goods(0, 0, 0.93, W - 0.2, D - 0.15)
    rec((0, 0, 0.5), W / 2, D / 2, 0.5)

elif SHAPE == "barrow":
    W, D = 1.5, 0.85
    box(W, D, 0.07, (0, 0, 0.62), 0, "wood", True)
    for sy in (-1, 1):
        box(W, 0.06, 0.22, (0, sy * D / 2, 0.75))
    box(0.06, 0.06, W + 0.7, (0.0, -D / 2 - 0.1, 0.62), 0)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.055,
                                         location=(sx * (W / 2 + 0.06), 0.1, 0.32),
                                         major_segments=16, minor_segments=6,
                                         rotation=(0, math.pi / 2, 0))
        into("wood")
        for k in range(6):
            a = k * math.pi / 3
            rod(0.022, 0.6, (sx * (W / 2 + 0.06), 0.1 + math.sin(a) * 0.0, 0.32),
                (0, math.pi / 2, a), "wood", 5)
    goods(0, 0, 0.66, W - 0.2, D - 0.2)
    rec((0, 0, 0.5), W / 2, D / 2, 0.5)

elif SHAPE == "mat":
    W, D = 1.7, 1.2
    m = sheet(W / 2, D / 2, (0, 0, 0.03), 0.01, 0.0, "cloth")
    for i in range(3):
        box(random.uniform(0.3, 0.5), random.uniform(0.25, 0.4), 0.05,
            (random.uniform(-W / 3, W / 3), random.uniform(-D / 3, D / 3), 0.06),
            random.uniform(0, 1.2), "cloth")
    goods(0, 0, 0.08, W - 0.3, D - 0.3)
    rec((0, 0, 0.1), W / 2, D / 2, 0.1)

elif SHAPE == "booth":
    W, D, H = 2.2, 1.7, 2.5
    for sy in (-1, 1):
        box(0.22, D, H, (-W / 2, 0, H / 2), 0, "wood", True)
        box(0.22, D, H, (W / 2, 0, H / 2), 0, "wood", True)
    box(W + 0.5, 0.24, H, (0, D / 2, H / 2), 0, "wood", True)
    box(W + 0.5, D + 0.3, 0.22, (0, 0, H + 0.11), 0, "wood", True)
    for i in range(3):
        rod(0.05, W, (0, -D / 2 + 0.1, 0.9 + i * 0.5), (0, math.pi / 2, 0))
    box(W - 0.3, 0.5, 0.07, (0, -D / 2 + 0.25, 0.92), 0, "wood", True)
    sheet(W / 2 + 0.25, 0.55, (0, -D / 2 - 0.5, H * 0.82), 0.12)
    goods(0, -D / 2 + 0.25, 0.96, W - 0.5, 0.4)
    rec((0, 0, H / 2), W / 2 + 0.2, D / 2, H / 2)

else:                       # rack: goods hung from a frame
    W, D, H = 2.0, 0.6, 2.3
    for sx in (-1, 1):
        rod(0.06, H, (sx * W / 2, 0, H / 2))
        rod(0.045, 0.9, (sx * W / 2, 0, 0.1), (math.pi / 2, 0, 0), "wood", 6)
    box(W + 0.25, 0.07, 0.08, (0, 0, H))
    box(W + 0.25, 0.07, 0.08, (0, 0, H * 0.62))
    for i in range(7):
        x = -W / 2 + (i + 0.5) * (W / 7)
        sheet(0.14, 0.02, (x, 0.05, H - random.uniform(0.5, 0.9)), 0.0, 0.0, "cloth")
    box(W - 0.2, D, 0.06, (0, 0, 0.55), 0, "wood", True)
    goods(0, 0, 0.58, W - 0.3, D - 0.1)
    rec((0, 0, 0.9), W / 2, D / 2, 0.9)


# ------------------------------------------------------------- materials
CLOTH_TINTS = [(0.45, 0.16, 0.13), (0.16, 0.24, 0.34), (0.42, 0.33, 0.14),
               (0.20, 0.31, 0.20), (0.38, 0.24, 0.30), (0.48, 0.42, 0.28),
               (0.30, 0.14, 0.22), (0.14, 0.28, 0.30)]
GOODS_TINT = {
    "spice":   (0.62, 0.28, 0.06), "pottery": (0.40, 0.24, 0.16),
    "cloth":   (0.36, 0.20, 0.26), "fruit":   (0.44, 0.20, 0.14),
    "grain":   (0.52, 0.44, 0.26), "basket":  (0.50, 0.38, 0.20),
    "metal":   (0.34, 0.31, 0.26), "rope":    (0.46, 0.38, 0.24),
    "bread":   (0.56, 0.42, 0.24), "wood":    (0.30, 0.21, 0.13),
}.get(TRADE, (0.44, 0.30, 0.18))
cloth_tint = CLOTH_TINTS[sum(ord(c) for c in SHAPE + TRADE) % len(CLOTH_TINTS)]

MATS = {}


def make_mat(name, tint, rough, tex=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1)
    b.inputs["Roughness"].default_value = rough
    if TRADE == "metal" and name == "goods":
        b.inputs["Metallic"].default_value = 0.7
        b.inputs["Roughness"].default_value = 0.38
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = nt.nodes.new('ShaderNodeTexImage')
            tn.image = img
            mix = nt.nodes.new('ShaderNodeMixRGB')
            mix.blend_type = 'MULTIPLY'
            mix.inputs['Fac'].default_value = 1.0
            mix.inputs['Color2'].default_value = (tint[0] * 2.4, tint[1] * 2.4, tint[2] * 2.4, 1)
            nt.links.new(tn.outputs['Color'], mix.inputs['Color1'])
            nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
            img.pack()
    MATS[name] = m
    return m


make_mat("wood", (0.22, 0.15, 0.10), 0.92, "t_woodp_d.jpg")
make_mat("cloth", cloth_tint, 0.9, "t_cloth_d.jpg")
make_mat("goods", GOODS_TINT, 0.85, None if TRADE == "metal" else "t_clay_d.jpg")

joined = []
for gname in ("wood", "cloth", "goods"):
    objs = [o for o in GROUPS[gname] if o.name in bpy.data.objects]
    if not objs:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.data.materials.clear()
    ob.data.materials.append(MATS[gname])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cube_project(cube_size=0.7)
    bpy.ops.object.mode_set(mode='OBJECT')
    joined.append(ob)

bpy.ops.object.select_all(action='DESELECT')
for o in joined:
    o.select_set(True)
bpy.context.view_layer.objects.active = joined[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = SHAPE + "_" + TRADE

# The stalls went straight from raw boxes to the AO bake: no bevel and no
# smoothing at all, so every post was a hard-edged rectangular prism and every
# rolled bolt of cloth was a faceted drum. Same finish as the props now.
m = ob.modifiers.new("bv", 'BEVEL')
m.width = 0.010
m.segments = 2
m.limit_method = 'ANGLE'
m.angle_limit = math.radians(40)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.shade_smooth()
try:
    ob.data.use_auto_smooth = True
    ob.data.auto_smooth_angle = math.radians(36)
except AttributeError:
    try:
        bpy.ops.object.modifier_add(type='SMOOTH_BY_ANGLE')
        ob.modifiers[-1]["Input_1"] = math.radians(36)
        bpy.ops.object.modifier_apply(modifier=ob.modifiers[-1].name)
    except Exception as e:
        print("auto-smooth unavailable:", e)

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
        ao = 0.36 + 0.60 * data[i].color[0]
        data[i].color = (ao, ao, ao, 1.0)
except Exception as e:
    print("bake failed:", e)

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%s verts=%d tris=%d colliders=%d"
      % (SHAPE, TRADE, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))

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
