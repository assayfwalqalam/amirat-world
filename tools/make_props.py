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
scene.cycles.samples = 10

COLLIDERS = []


def lathe(profile, segments=26, thickness=0.015):
    """Spin a silhouette round the axis: how every vessel is actually made."""
    import bmesh
    me = bpy.data.meshes.new("v")
    ob = bpy.data.objects.new("v", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    for i in range(len(vs) - 1):
        bm.edges.new((vs[i], vs[i + 1]))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], axis=(0, 0, 1),
                   cent=(0, 0, 0), dvec=(0, 0, 0), angle=math.pi * 2,
                   steps=segments, use_merge=True)
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = thickness
    sol.offset = 1.0
    bpy.ops.object.modifier_apply(modifier=sol.name)
    for v in ob.data.vertices:                      # wheel rings and lean
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.002:
            ring = math.sin(v.co.z * 55.0) * 0.003
            k = (r + ring) / r
            v.co.x *= k
            v.co.y *= k
        v.co.x += 0.008 * v.co.z
    bpy.ops.object.shade_smooth()
    es = ob.modifiers.new("es", 'EDGE_SPLIT')
    es.use_edge_angle = True
    es.split_angle = math.radians(50)
    bpy.ops.object.modifier_apply(modifier=es.name)
    parts.append(ob)
    return ob

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
    for k, (jx, jy, js) in enumerate([(-0.22, 0.05, 1.0), (0.16, -0.08, 0.85), (0.05, 0.22, 0.7)]):
        ob2 = lathe([(0.08 * js, 0.0), (0.14 * js, 0.03), (0.19 * js, 0.14),
                     (0.21 * js, 0.3), (0.17 * js, 0.44), (0.11 * js, 0.52),
                     (0.13 * js, 0.58), (0.12 * js, 0.60)])
        ob2.location = (jx, jy, 0)
        ob2.rotation_euler = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0)
        bpy.ops.object.transform_apply(location=True, rotation=True)
    rec((0, 0, 0.3), 0.4, 0.4, 0.3)

elif KIND == "sacks":
    # A SACK IS NOT A SPHERE. It sits down on its own base and spreads there,
    # bellies out where the grain is, draws in at the shoulder, and is gathered
    # and tied at the neck with the loose cloth flaring above the tie. Made as
    # a squashed ball with a spout, it came out as a white egg a metre tall -
    # the loudest wrong thing in the market.
    # The old ones were also far too big: a sack of grain a man carries is
    # about knee height, not chest height.
    def one_sack(cx, cy, cz, sc, lean):
        prof = [
            (0.000, 0.000),
            (0.250, 0.000),          # the base it spreads on
            (0.292, 0.055),
            (0.318, 0.150),          # the belly
            (0.312, 0.255),
            (0.278, 0.340),          # the shoulder draws in
            (0.196, 0.410),
            (0.116, 0.452),          # the neck
            (0.086, 0.478),          # where the cord is tied
            (0.132, 0.520),          # the cloth flares above the tie
            (0.070, 0.556),
            (0.000, 0.566),
        ]
        prof = [(r * sc * (1.0 + random.uniform(-0.05, 0.05)), z * sc)
                for (r, z) in prof]
        b = lathe(prof, segments=18, thickness=0.010)
        b.location = (cx, cy, cz)
        b.rotation_euler = (lean[0], lean[1], random.uniform(0, 6.28))
        bpy.ops.object.select_all(action='DESELECT')
        b.select_set(True)
        bpy.context.view_layer.objects.active = b
        bpy.ops.object.transform_apply(location=True, rotation=True)
        jitter(b, 0.012 * sc)                       # the weave never sits true
        torus(0.098 * sc, 0.016 * sc, (cx, cy, cz + 0.478 * sc), seg=12)
        rec((cx, cy, cz + 0.24 * sc), 0.30 * sc, 0.30 * sc, 0.28 * sc)
        return b

    # three leaning against each other on the ground and one thrown on top
    for (sx, sy, sz, sc) in [(0.00, 0.00, 0.0, 1.00),
                             (0.46, 0.13, 0.0, 0.92),
                             (0.21, 0.44, 0.0, 0.86),
                             (0.26, 0.20, 0.50, 0.78)]:
        one_sack(sx, sy, sz,
                 sc * random.uniform(0.92, 1.06),
                 (random.uniform(-0.10, 0.10), random.uniform(-0.10, 0.10)))

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
    # three seat boards with a gap between them, shaped end-boards with a foot
    # cut into them, a back of slats, and the rail that ties it together
    for i, t in enumerate((-0.145, 0.0, 0.145)):
        b = box(1.9, 0.13, 0.055, (0, t, 0.465), collide=(i == 1))
        jitter(b, 0.004)
    for sx in (-1, 1):
        box(0.075, 0.42, 0.32, (sx * 0.80, 0, 0.28), collide=True)
        box(0.075, 0.42, 0.075, (sx * 0.80, 0, 0.038))     # the foot
        box(0.075, 0.12, 0.14, (sx * 0.80, 0, 0.135))      # cut away between
    box(1.78, 0.05, 0.055, (0, 0, 0.155))                  # stretcher
    for sx in (-1, 1):                                     # back posts
        box(0.07, 0.07, 0.34, (sx * 0.78, 0.185, 0.63))
    box(1.86, 0.05, 0.075, (0, 0.185, 0.775))              # top rail
    for i in range(5):                                     # the slats
        box(0.22, 0.032, 0.24, (-0.62 + i * 0.31, 0.185, 0.635))

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
    # A TABLE IS BOARDS, NOT A SLAB. One box on four sticks is the shape a
    # table has in a diagram; the real thing is five or six planks laid across
    # a frame with a shadow line between them, an apron underneath to stop it
    # racking, and legs that are turned and taper to a foot.
    NB = 5
    for i in range(NB):
        t = (i + 0.5) / NB - 0.5
        b = box(1.05 / NB - 0.012, 0.70, 0.055, (t * 1.05, 0, 0.445),
                collide=(i == 0))
        jitter(b, 0.004)
    for sy in (-1, 1):                                  # the apron
        box(0.95, 0.055, 0.085, (0, sy * 0.30, 0.375))
    for sx in (-1, 1):
        box(0.055, 0.60, 0.085, (sx * 0.47, 0, 0.375))
    for sx in (-1, 1):                                  # turned legs
        for sy in (-1, 1):
            lx, ly = sx * 0.45, sy * 0.28
            box(0.10, 0.10, 0.13, (lx, ly, 0.30))
            cyl(0.048, 0.034, 0.26, (lx, ly, 0.115), verts=14)
            cyl(0.056, 0.052, 0.035, (lx, ly, 0.017), verts=14)
            torus(0.048, 0.011, (lx, ly, 0.235), seg=12)
    box(0.88, 0.05, 0.05, (0, 0, 0.11))                 # low stretcher

elif KIND == "stool":
    # a dished seat with a moulding under its rim, three splayed turned legs,
    # and the ring of stretchers that keeps them from spreading
    cyl(0.21, 0.205, 0.045, (0, 0, 0.435), verts=20, collide=True)
    cyl(0.185, 0.15, 0.045, (0, 0, 0.392), verts=20)
    torus(0.205, 0.016, (0, 0, 0.418), seg=18)
    for k in range(3):
        a = k * math.pi * 2 / 3
        cx, cy = math.cos(a), math.sin(a)
        cyl(0.036, 0.026, 0.40, (cx * 0.145, cy * 0.145, 0.20), verts=10)
        torus(0.033, 0.009, (cx * 0.145, cy * 0.145, 0.30), seg=10)
        a2 = a + math.pi * 2 / 3
        mx = (cx + math.cos(a2)) * 0.5 * 0.15
        my = (cy + math.sin(a2)) * 0.5 * 0.15
        cyl(0.018, 0.018, 0.155, (mx, my, 0.13),
            rot=(math.pi / 2, 0, a + math.pi / 3 + math.pi / 2), verts=8)

elif KIND == "chest":
    # a panelled body with corner posts, iron straps carried over a domed lid,
    # and a hasp and lockplate on the front
    box(0.82, 0.50, 0.42, (0, 0, 0.21), collide=True)
    for sx in (-1, 1):                                     # corner posts
        for sy in (-1, 1):
            box(0.075, 0.075, 0.44, (sx * 0.385, sy * 0.225, 0.22))
    cyl(0.25, 0.25, 0.82, (0, 0, 0.44), rot=(0, math.pi / 2, 0), verts=20)
    for sy in (-1, 1):                                     # rails
        box(0.86, 0.045, 0.055, (0, sy * 0.205, 0.075))
        box(0.86, 0.045, 0.055, (0, sy * 0.205, 0.345))
    for t in (-0.26, 0.0, 0.26):                           # iron straps
        box(0.055, 0.53, 0.44, (t, 0, 0.21))
        cyl(0.262, 0.262, 0.05, (t, 0, 0.44), rot=(0, math.pi / 2, 0), verts=20)
    box(0.13, 0.055, 0.15, (0, -0.262, 0.40))              # the hasp
    box(0.10, 0.03, 0.09, (0, -0.268, 0.30))               # lockplate
    torus(0.035, 0.010, (0, -0.272, 0.275), seg=10)

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
    lathe([(0.05, 0.0), (0.10, 0.015), (0.17, 0.06), (0.22, 0.13), (0.24, 0.19),
           (0.24, 0.21)], thickness=0.012)
    for i in range(5):
        a = i * 1.3
        b2 = sphere(0.05, (math.cos(a) * 0.06, math.sin(a) * 0.06, 0.20))
        jitter(b2, 0.008)

elif KIND == "bread":
    for i in range(3):
        b = sphere(0.13, (i * 0.22 - 0.22, random.uniform(-0.04, 0.04), 0.05))
        b.scale = (1.25, 0.8, 0.4)
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.012)

elif KIND == "pot":
    lathe([(0.10, 0.0), (0.17, 0.04), (0.24, 0.16), (0.26, 0.32), (0.22, 0.46),
           (0.15, 0.55), (0.13, 0.62), (0.16, 0.67), (0.15, 0.70)])
    rec((0, 0, 0.35), 0.24, 0.24, 0.35)

elif KIND == "plantpot":
    lathe([(0.11, 0.0), (0.14, 0.02), (0.17, 0.14), (0.20, 0.30), (0.21, 0.34)],
          thickness=0.014)
    rec((0, 0, 0.17), 0.19, 0.19, 0.17)
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
    lathe([(0.035, 0.0), (0.075, 0.012), (0.10, 0.04), (0.085, 0.075),
           (0.045, 0.095), (0.055, 0.11)], thickness=0.008, segments=14)
    cyl(0.02, 0.014, 0.1, (0.1, 0, 0.055), rot=(0, 1.25, 0), verts=8)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.009,
                                     location=(-0.1, 0, 0.06),
                                     major_segments=10, minor_segments=5,
                                     rotation=(0, 0.5, 0))
    parts.append(bpy.context.active_object)

elif KIND == "waterjug":
    lathe([(0.07, 0.0), (0.13, 0.03), (0.19, 0.14), (0.21, 0.30), (0.17, 0.44),
           (0.09, 0.54), (0.065, 0.66), (0.09, 0.73), (0.085, 0.76)])
    for i in range(8):
        t = i / 7.0
        z = 0.30 + t * 0.36
        rr = 0.14 + math.sin(t * math.pi) * 0.07
        cyl(0.016, 0.016, 0.05, (rr, 0, z), rot=(0.5, 0, 0), verts=6)
    rec((0, 0, 0.38), 0.2, 0.2, 0.38)

elif KIND == "ropecoil":
    for i in range(5):
        torus(0.2 - i * 0.012, 0.028, (0, 0, 0.03 + i * 0.045), seg=16)

elif KIND == "firewood":
    for i in range(7):
        cyl(0.05, 0.045, random.uniform(0.6, 0.9),
            (random.uniform(-0.2, 0.2), random.uniform(-0.15, 0.15), 0.06 + (i % 3) * 0.1),
            rot=(0, math.pi / 2, random.uniform(0, 3.14)), verts=6)

elif KIND == "torch":
    # Forged ironwork, not stacked primitives: a strapped wall plate, one
    # hammered arm curving out and up, and an open finger-basket cradling
    # the pitch-soaked head. Every element bends and wavers a little.
    def seg_chain(pts, r0, r1, verts=7, hammer=0.004):
        """Tapered rod bent through the given points, ball at each joint."""
        n = len(pts) - 1
        for i in range(n):
            (x0, y0, z0), (x1, y1, z1) = pts[i], pts[i + 1]
            dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
            ln = math.sqrt(dx * dx + dy * dy + dz * dz)
            ra = r0 + (r1 - r0) * (i / n)
            rb = r0 + (r1 - r0) * ((i + 1) / n)
            pitch = math.acos(max(-1, min(1, dz / (ln or 1))))
            yaw = math.atan2(dy, dx)
            bpy.ops.mesh.primitive_cone_add(radius1=ra, radius2=rb, depth=ln * 1.12,
                location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), vertices=verts)
            ob = bpy.context.active_object
            ob.rotation_euler = (0.0, pitch, yaw)
            bpy.ops.object.transform_apply(rotation=True)
            jitter(ob, hammer)
            parts.append(ob)
            if i < n - 1:
                bpy.ops.mesh.primitive_uv_sphere_add(radius=rb * 1.06,
                    location=(x1, y1, z1), segments=7, ring_count=5)
                jb = bpy.context.active_object
                jitter(jb, hammer)
                parts.append(jb)

    pl = box(0.15, 0.3, 0.05, (0, 0.05, 0.16), 0, True)          # the strap plate
    jitter(pl, 0.008)
    for sy, sz in ((-0.1, 0.05), (0.1, 0.05), (-0.1, 0.27), (0.1, 0.27)):
        nl = cyl(0.014, 0.012, 0.03, (0.0, sy, sz), rot=(0, 1.5708, 0), verts=6)
        jitter(nl, 0.003)                                        # nail heads
    # the arm: one smooth smith's curve from the plate, out and up
    arm = []
    for i in range(7):
        t = i / 6.0
        arm.append((0,
                    -0.05 - 0.42 * math.sin(t * 1.35),
                    0.12 + 0.30 * t + 0.42 * t * t))
    seg_chain(arm, 0.030, 0.020)
    tipy, tipz = arm[-1][1], arm[-1][2]
    # a scrolled drip-curl under the arm's end, the smith's flourish
    seg_chain([(0, tipy + 0.02, tipz - 0.05), (0, tipy + 0.07, tipz - 0.10),
               (0, tipy + 0.10, tipz - 0.07), (0, tipy + 0.08, tipz - 0.03)],
              0.012, 0.007)
    # the basket: six bowed fingers meeting two waving hoops
    for k in range(6):
        a = k * math.pi / 3 + 0.26
        fx, fy = math.cos(a), math.sin(a)
        seg_chain([(fx * 0.035, tipy + fy * 0.035, tipz - 0.02),
                   (fx * 0.085, tipy + fy * 0.085, tipz + 0.07),
                   (fx * 0.105, tipy + fy * 0.105, tipz + 0.16),
                   (fx * 0.075, tipy + fy * 0.075, tipz + 0.24)],
                  0.011, 0.008, verts=5)
    for hz, hr in ((tipz + 0.10, 0.10), (tipz + 0.185, 0.105)):
        hp = torus(hr, 0.009, (0, tipy, hz), seg=14)
        jitter(hp, 0.006)
    # the pitch-soaked head, a ragged charred lump proud of the basket
    head = sphere(0.095, (0, tipy, tipz + 0.20), seg=12)
    head.scale = (1, 1, 1.35)
    bpy.ops.object.transform_apply(scale=True)
    jitter(head, 0.032)
    for k in range(3):                                           # sagging drips
        a = k * 2.2 + 0.5
        dr = sphere(0.022, (math.cos(a) * 0.08, tipy + math.sin(a) * 0.08,
                            tipz + 0.06 - k * 0.02), seg=7)
        dr.scale = (0.7, 0.7, 1.9)
        bpy.ops.object.transform_apply(scale=True)
        jitter(dr, 0.006)

elif KIND == "torchpost":
    # A cresset: a timber stake with an open iron basket on top holding the
    # burning pitch. A smooth pole with a bulb on the end reads as a Victorian
    # street lamp, which is the one thing this must not look like.
    st = cyl(0.34, 0.40, 0.26, (0, 0, 0.13), verts=10, collide=True)   # stone footing
    jitter(st, 0.02)
    for k in range(4):                                                  # wedged packing stones
        a = k * math.pi * 2 / 4 + 0.4
        b = sphere(0.1, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.06))
        b.scale = (1.3, 1.0, 0.6)
        bpy.ops.object.transform_apply(scale=True)
        jitter(b, 0.02)
    post = cyl(0.085, 0.072, 2.05, (0, 0, 1.18), verts=8, collide=True)  # the stake
    jitter(post, 0.012)
    for z in (0.62, 1.34):                                              # iron bands
        torus(0.088, 0.018, (0, 0, z), seg=10)
    for k in range(3):                                                  # braced feet
        a = k * math.pi * 2 / 3 + 0.7
        cyl(0.03, 0.024, 0.56, (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.34),
            rot=(0.62 * math.sin(a), -0.62 * math.cos(a), 0), verts=5)
    # the basket: bowed iron fingers meeting two hoops, none of them true
    col = cyl(0.11, 0.15, 0.1, (0, 0, 2.25), verts=10)                  # collar
    jitter(col, 0.008)
    for k in range(7):
        a = k * math.pi * 2 / 7 + 0.2
        fx, fy = math.cos(a), math.sin(a)
        bar = cyl(0.016, 0.012, 0.4,
                  (fx * 0.16, fy * 0.16, 2.48),
                  rot=(-0.38 * fy + random.uniform(-0.05, 0.05),
                       0.38 * fx + random.uniform(-0.05, 0.05), 0), verts=5)
        jitter(bar, 0.006)
    for hz, hr in ((2.36, 0.15), (2.63, 0.205)):
        hp = torus(hr, 0.016, (0, 0, hz), seg=14)
        jitter(hp, 0.01)
    for k in range(4):                                                  # the fuel in it
        a = k * 1.6
        c = sphere(0.075, (math.cos(a) * 0.07, math.sin(a) * 0.07, 2.5))
        c.scale = (1.15, 1.0, 0.75)
        bpy.ops.object.transform_apply(scale=True)
        jitter(c, 0.024)

elif KIND == "ladder":
    # leaning ladder, after the roofs in the reference panorama
    H = 2.7
    lean = 0.16
    for sx in (-1, 1):
        cyl(0.034, 0.028, H, (sx * 0.20, 0, H / 2), rot=(lean, 0, 0), verts=6)
    for i in range(7):
        z = 0.25 + i * (H - 0.5) / 6
        y = -(z - H / 2) * math.tan(lean)
        cyl(0.021, 0.021, 0.42, (0, y, z), rot=(0, math.pi / 2, 0), verts=6)

elif KIND == "pergola":
    # posts carrying spaced planks: the shade structure of every courtyard
    W2, D2, H2 = 3.0, 2.6, 2.35
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.085, 0.07, H2, (sx * W2 / 2, sy * D2 / 2, H2 / 2),
                rot=(random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), 0),
                verts=7, collide=True)
    for sy in (-1, 1):
        box(W2 + 0.5, 0.11, 0.13, (0, sy * D2 / 2, H2))
    n = 8
    for i in range(n):
        x = -W2 / 2 + i * (W2 / (n - 1))
        box(0.09, D2 + 0.55, 0.05, (x, 0, H2 + 0.08))

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
# Two segments, not one. A single chamfer is still a flat plane meeting two
# other flat planes; two make a rounded arris that catches a highlight, which
# is the difference between a carpentered edge and a cardboard one.
m.width = 0.010
m.segments = 2
m.limit_method = 'ANGLE'
m.angle_limit = math.radians(40)
bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=1.1)
bpy.ops.object.mode_set(mode='OBJECT')

# THE PROPS WERE ALL FLAT SHADED. Nothing in this file ever called
# shade_smooth, so a sack built out of three thousand triangles rendered as
# three thousand visible facets and a jar came out a faceted drum. That is
# what "too blocky" was: not a shortage of geometry - the sack has plenty of
# it - but every polygon lit as its own separate plane.
# Auto-smooth keeps the distinction that matters: faces meeting at less than
# the angle below are smoothed across, anything sharper stays a crisp edge.
# So a barrel is round and a crate still has corners, and it costs nothing -
# not one triangle is added.
bpy.ops.object.shade_smooth()
try:
    ob.data.use_auto_smooth = True                 # Blender 4.0 and earlier
    ob.data.auto_smooth_angle = math.radians(36)
except AttributeError:
    # 4.1 and later dropped the mesh flags in favour of a modifier
    try:
        bpy.ops.object.modifier_add(type='SMOOTH_BY_ANGLE')
        ob.modifiers[-1]["Input_1"] = math.radians(36)
        bpy.ops.object.modifier_apply(modifier=ob.modifiers[-1].name)
    except Exception as e:
        print("auto-smooth unavailable:", e)

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
    "firewood": (0.32, 0.22, 0.14),
    # iron stands right under a flame -- too dark a tint and it reads as a
    # black modern lamp post rather than a lit bracket
    "torch": (0.34, 0.28, 0.23), "torchpost": (0.38, 0.32, 0.26),
    "ladder": (0.30, 0.21, 0.12), "pergola": (0.27, 0.19, 0.11),
}.get(KIND, (0.45, 0.36, 0.26))

mat = bpy.data.materials.new(KIND)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (TINT[0], TINT[1], TINT[2], 1)
bsdf.inputs["Roughness"].default_value = 0.95
ob.data.materials.clear()
ob.data.materials.append(mat)


# ------------------------------------------------- photographed materials
WOODY = {"barrel", "barrels", "crates", "cart", "bench", "stall", "table",
         "stool", "chest", "broom", "swordrack", "spears", "bowarrows",
         "firewood", "ladder", "pergola", "torchpost"}
CLAYY = {"pot", "jars", "waterjug", "oillamp", "bowl", "plantpot", "bread"}
CLOTHY = {"awning", "carpet", "cushions", "sacks"}
# every surface wears something: a flat colour is what made these read as toys
# A WELL IS DRESSED MASONRY AND A BRAZIER IS IRON. Both were wearing
# g_rock_d.jpg, which is a photograph of rocky GROUND - loose stones lying in
# dirt, shot from above. On a heap of rocks that is exactly right; wrapped
# round a built cylinder at one repeat for the whole object it reads as gravel
# smeared on a drum, which is why the well came out a black-and-white block.
STONEY = {"stones"}
ASHLAR = {"well"}
FIBRE = {"basket", "ropecoil"}
PAPERY = {"scrolls", "books", "inkset"}
IRONY = {"torch", "brazier"}

tex_file = None
gain = 2.4
if KIND in WOODY:
    tex_file = "t_woodp_d.jpg"
elif KIND in CLAYY:
    tex_file = "t_clay_d.jpg"
elif KIND in CLOTHY:
    tex_file = "t_cloth_d.jpg"
elif KIND in STONEY:
    tex_file = "g_rock_d.jpg"
elif KIND in ASHLAR:
    tex_file = "t_ashlar_d.jpg"
elif KIND in FIBRE:
    tex_file = "t_canvas.jpg"
elif KIND in PAPERY:
    tex_file = "t_parch.jpg"
elif KIND in IRONY:
    tex_file = "t_gunsteel.jpg"

if tex_file is not None:
    path = os.path.abspath(os.path.join(ASSETS, tex_file))
    if os.path.exists(path):
        img = bpy.data.images.load(path)
        tn2 = nt.nodes.new('ShaderNodeTexImage')
        tn2.image = img
        # The texture goes straight into Base Color. The multiply that used
        # to sit here was dropped by the glTF exporter every time (checked by
        # parsing p_cart.glb: baseColorFactor absent), so the props have
        # always shipped as the bare photograph. The tone is baked into the
        # texture instead, light enough to read by moonlight.
        nt.links.new(tn2.outputs['Color'], bsdf.inputs['Base Color'])
        img.pack()

while len(ob.data.color_attributes):
    ob.data.color_attributes.remove(ob.data.color_attributes[0])
ob.data.color_attributes.active_color = ob.data.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
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

# Props carry a flat tint rather than a texture, so Base Color must stay a
# constant: linking anything into it makes the exporter drop baseColorFactor
# and every prop turns grey. The occlusion still ships, because the export
# call below asks for the active colour layer explicitly.
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
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
