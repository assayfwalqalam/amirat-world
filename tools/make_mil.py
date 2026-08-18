# Military field structures of the region's wars: the concrete, steel and
# sandbag works of camps, outposts and checkpoints. Modelled from real
# proportions, judged against Arma-class references. Objects only.
#   blender --background --python make_mil.py -- <kind> <out.glb> [assets]
# Kinds: hesco, sandbags, watchtower_wood, watchtower_metal, twall,
#        chainlink, boom_barrier, checkpoint, jersey
import bpy, bmesh, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "hesco"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 179)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 10

COLLIDERS = []
concrete, steel, gravel, cloth, wood = [], [], [], [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


def box(sx, sy, sz, loc, into, bevel=0.0, rot=(0, 0, 0), collide=False):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    if bevel:
        m = ob.modifiers.new("bv", 'BEVEL')
        m.width = bevel
        m.segments = 2
        bpy.ops.object.modifier_apply(modifier=m.name)
    if collide:
        rec(loc, sx / 2, sy / 2, sz / 2)
    into.append(ob)
    return ob


def cyl(r, h, loc, into, rot=(0, 0, 0), verts=12, collide=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=verts)
    if collide:
        rec(loc, r, r, h / 2)
    into.append(bpy.context.active_object)
    return bpy.context.active_object


def jitter(ob, amt):
    for v in ob.data.vertices:
        v.co.x += random.uniform(-amt, amt)
        v.co.y += random.uniform(-amt, amt)
        v.co.z += random.uniform(-amt, amt)


if KIND == "hesco":
    # A Hesco bastion cell: a wire-mesh gabion filled with earth. The earth
    # fill is the body you see; the galvanized mesh is only thin wires over
    # it. Real unit ~1.0 x 1.0 x 1.0. A run is several cells side by side.
    W2, H2, D2 = 1.05, 1.0, 0.92
    cells = 3
    for c in range(cells):
        cx = (c - (cells - 1) / 2.0) * W2
        # the earth fill: dominant, tan, bulging out through the mesh
        core = box(W2 - 0.02, D2 - 0.02, H2, (cx, 0, H2 / 2), gravel)
        for v in core.data.vertices:
            s = 1.0 + 0.06 * (1 - abs(v.co.z - H2 / 2) / (H2 / 2))   # barrel out at mid
            v.co.x = cx + (v.co.x - cx) * s
            v.co.y *= s
            if v.co.z > H2 - 0.02:                                   # heaped a little on top
                v.co.z += random.uniform(0, 0.04)
        jitter(core, 0.015)
        # the mesh: 12 thin edge bars (the cube outline) + a sparse grid
        for (ax, ay) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            box(0.012, 0.012, H2, (cx + ax * W2 / 2, ay * D2 / 2, H2 / 2), steel)  # verticals
        for gz in (0.02, H2 - 0.02):
            for ay in (-1, 1):
                box(W2, 0.012, 0.012, (cx, ay * D2 / 2, gz), steel)
            for ax in (-1, 1):
                box(0.012, D2, 0.012, (cx + ax * W2 / 2, 0, gz), steel)
        # a few grid wires across each long face (front and back)
        for ay in (-1, 1):
            for gz in (0.26, 0.52, 0.78):
                box(W2, 0.008, 0.006, (cx, ay * D2 / 2, gz), steel)
            for gx in (-0.3, 0.3):
                box(0.006, 0.008, H2, (cx + gx, ay * D2 / 2, H2 / 2), steel)
    rec((0, 0, H2 / 2), cells * W2 / 2, D2 / 2, H2 / 2)

elif KIND == "sandbags":
    # A stacked sandbag wall: rows of bags, each row offset, tapering up.
    rows, per = 5, 6
    bw, bh, bd = 0.34, 0.14, 0.20
    for r in range(rows):
        n = per - r // 2
        off = (r % 2) * bw * 0.5
        for i in range(n):
            x = -n * bw / 2 + i * bw + bw / 2 + off * 0.3
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, 0, bh / 2 + r * bh * 0.92),
                                                 segments=10, ring_count=7)
            b = bpy.context.active_object
            b.scale = (bw / 2, bd / 2, bh / 2)
            b.rotation_euler[2] = random.uniform(-0.12, 0.12)
            bpy.ops.object.transform_apply(scale=True, rotation=True)
            for v in b.data.vertices:            # sag the bag flat-ish on top
                if v.co.z > 0:
                    v.co.z *= 0.7
            jitter(b, 0.006)
            cloth.append(b)
    rec((0, 0, rows * bh * 0.46), per * bw / 2, bd / 2, rows * bh * 0.46)

elif KIND == "watchtower_wood":
    # A four-legged timber guard tower: splayed legs, a railed platform, a
    # low pitched roof. Real ~5-6 m to the platform.
    H2 = 5.2
    top = 1.6                       # platform half-width
    footspread = 2.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx0, by0 = sx * footspread / 2, sy * footspread / 2
            bx1, by1 = sx * top, sy * top
            # a leaning leg from foot to platform corner
            mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
            leg = cyl(0.08, H2 + 0.3, (mx, my, H2 / 2), wood,
                      rot=(math.atan2(by1 - by0, H2) * 0.5, -math.atan2(bx1 - bx0, H2) * 0.5, 0),
                      verts=8, collide=True)
    # cross-bracing on the sides
    for lvl in (1.6, 3.4):
        for sy in (-1, 1):
            box(footspread, 0.05, 0.05, (0, sy * (footspread / 2 - lvl * 0.06), lvl), wood)
        for sx in (-1, 1):
            box(0.05, footspread, 0.05, (sx * (footspread / 2 - lvl * 0.06), 0, lvl), wood)
    # the platform
    box(top * 2 + 0.3, top * 2 + 0.3, 0.12, (0, 0, H2), wood, collide=True)
    # the rail
    for sx in (-1, 1):
        box(0.06, top * 2, 0.5, (sx * top, 0, H2 + 0.3), wood)
    for sy in (-1, 1):
        box(top * 2, 0.06, 0.5, (0, sy * top, H2 + 0.3), wood)
    rec((0, 0, H2 + 0.25), top, top, 0.5)
    # the roof: four posts and a low pyramid
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.05, 1.4, (sx * top * 0.9, sy * top * 0.9, H2 + 0.9), wood, verts=6)
    bpy.ops.mesh.primitive_cone_add(radius1=top * 1.5, radius2=0, depth=0.9,
                                    location=(0, 0, H2 + 2.0), vertices=4)
    r = bpy.context.active_object
    r.rotation_euler[2] = math.pi / 4
    bpy.ops.object.transform_apply(rotation=True)
    wood.append(r)

elif KIND == "watchtower_metal":
    # A steel scaffold guard tower: four uprights, X-bracing every level, a
    # deck with a hatch, a ladder you can actually climb, and a cabin that
    # SITS ON the deck.
    def link(p0, p1, r, into):
        """A strut between two points. Built at the ORIGIN, turned there, and
        only then moved - a part that is rotated after it has been placed
        swings about the world origin, which is what threw every brace out
        past the legs like spikes."""
        dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 0.001
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=ln, location=(0, 0, 0), vertices=6)
        ob = bpy.context.active_object
        ob.rotation_euler = (0, math.acos(max(-1, min(1, dz / ln))), math.atan2(dy, dx) + math.pi / 2)
        bpy.ops.object.transform_apply(rotation=True)
        ob.location = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
        bpy.ops.object.transform_apply(location=True)
        into.append(ob)
        return ob

    H2 = 6.0
    hw = 1.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(0.05, H2, (sx * hw, sy * hw, H2 / 2), steel, verts=8, collide=True)
    corners = [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)]
    levels = 4
    for lv in range(levels):
        z0 = lv * H2 / levels
        z1 = (lv + 1) * H2 / levels
        for e in range(4):
            (ax, ay) = corners[e]
            (bx, by) = corners[(e + 1) % 4]
            if e == 0:
                continue                 # the front bay is left clear for the ladder
            link((ax, ay, z0), (bx, by, z1), 0.02, steel)
            link((ax, ay, z1), (bx, by, z0), 0.02, steel)
            link((ax, ay, z1), (bx, by, z1), 0.02, steel)

    # THE DECK, with a hatch at the ladder head. Four boards round a gap, so
    # you come up through it instead of into the underside of a slab.
    DK = hw + 0.15
    HX, HZ = 0.42, 0.46                  # half the hatch
    hy = -DK + HZ + 0.10                 # the hatch sits over the front bay
    box(DK * 2, DK - (hy + HZ), 0.08, (0, (hy + HZ + DK) / 2, H2), steel, collide=True)
    box(DK * 2, (hy - HZ) + DK, 0.08, (0, (-DK + hy - HZ) / 2, H2), steel, collide=True)
    for sx in (-1, 1):
        box(DK - HX, HZ * 2, 0.08, (sx * (HX + DK) / 2, hy, H2), steel, collide=True)

    # THE LADDER: two rails and rungs, each rung a solid you can stand on, and
    # a climb volume so it is scaled the way a ladder is, not walked up.
    LY = -DK - 0.22
    for sx2 in (-1, 1):
        cyl(0.035, H2 + 0.5, (sx2 * 0.26, LY, (H2 + 0.5) / 2), steel, verts=6)
    nrung = int((H2 + 0.3) / 0.30)
    for i in range(nrung):
        z = 0.26 + i * 0.30
        box(0.56, 0.05, 0.045, (0, LY, z), steel)
        rec((0, LY, z), 0.28, 0.03, 0.03)
    # hoops round the upper half, as every real one has
    for i in range(6):
        z = H2 * 0.45 + i * 0.55
        box(0.62, 0.04, 0.04, (0, LY - 0.28, z), steel)
        for sx3 in (-1, 1):
            box(0.04, 0.56, 0.04, (sx3 * 0.31, LY - 0.14, z), steel)
    CLIMB = {"c": [0, (H2 + 0.4) / 2, -LY], "h": [0.42, (H2 + 0.4) / 2, 0.55]}

    # THE CABIN, standing ON the deck
    CZ = H2 + 0.04
    for sy in (-1, 1):
        box(hw * 2, 0.05, 0.62, (0, sy * hw, CZ + 0.31), steel)          # below the slit
        box(hw * 2, 0.05, 0.34, (0, sy * hw, CZ + 1.13), steel)          # above it
    box(0.05, hw * 2, 0.62, (-hw, 0, CZ + 0.31), steel)
    box(0.05, hw * 2, 0.34, (-hw, 0, CZ + 1.13), steel)
    box(0.05, hw * 2, 0.5, (hw, 0, CZ + 0.55), steel)                    # firing slot side
    box(hw * 2 + 0.2, hw * 2 + 0.2, 0.08, (0, 0, CZ + 1.34), steel)      # roof
    for sx4 in (-1, 1):                                                  # corner posts
        for sy4 in (-1, 1):
            cyl(0.04, 1.34, (sx4 * hw, sy4 * hw, CZ + 0.67), steel, verts=6)
    rec((0, 0, CZ + 0.7), hw, hw, 0.05)                                  # the cabin floor edge

elif KIND == "twall":
    # A concrete T-wall (blast wall): a tall slab on a wide foot, the grey
    # panels that line every base. Real ~3.7 m tall.
    H2 = 3.7
    box(0.28, 1.5, H2, (0, 0, H2 / 2), concrete, bevel=0.02, collide=True)   # the slab
    box(0.9, 1.5, 0.3, (0, 0, 0.15), concrete, bevel=0.02, collide=True)     # the foot
    # the lifting lug at the top
    cyl(0.06, 0.14, (0, 0, H2 + 0.02), steel, rot=(math.pi / 2, 0, 0), verts=10)
    rec((0, 0, H2 / 2), 0.14, 0.75, H2 / 2)

elif KIND == "jersey":
    # A Jersey barrier: the short sloped-side concrete divider.
    me = bpy.data.meshes.new("jersey")
    ob = bpy.data.objects.new("jersey", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    L = 1.5
    prof = [(-0.30, 0), (0.30, 0), (0.20, 0.15), (0.08, 0.35), (0.08, 0.81),
            (-0.08, 0.81), (-0.08, 0.35), (-0.20, 0.15)]
    for sx in (-1, 1):
        ring = [bm.verts.new((p[0], sx * L, p[1])) for p in prof]
        if sx == 1:
            bm.faces.new(ring)
        else:
            first = ring
    verts_a = [v for v in bm.verts if v.co.y < 0]
    verts_b = [v for v in bm.verts if v.co.y > 0]
    for i in range(len(prof)):
        bm.faces.new((verts_a[i], verts_a[(i + 1) % len(prof)],
                      verts_b[(i + 1) % len(prof)], verts_b[i]))
    bm.to_mesh(me)
    bm.free()
    concrete.append(ob)
    rec((0, 0, 0.4), 0.3, L, 0.4)

elif KIND == "chainlink":
    # A chain-link fence panel with barbed strands leaning out on top.
    W2, H2 = 2.5, 2.0
    for sx in (-1, 1):
        cyl(0.03, H2 + 0.2, (sx * W2 / 2, 0, H2 / 2), steel, verts=8, collide=True)
    box(W2, 0.02, 0.03, (0, 0, H2), steel)          # top rail
    box(W2, 0.02, 0.03, (0, 0, 0.05), steel)        # bottom rail
    # the mesh: a thin translucent-ish grid, drawn as fine wires
    for i in range(1, 12):
        cyl(0.006, H2, (-W2 / 2 + i * W2 / 12, 0, H2 / 2), steel, verts=4)
    for j in range(1, 9):
        box(W2, 0.005, 0.008, (0, 0, j * H2 / 9), steel)
    # the barbed arm leaning outward and three strands
    for sx in (-1, 1):
        cyl(0.02, 0.4, (sx * W2 / 2, -0.12, H2 + 0.15), steel, rot=(0.7, 0, 0), verts=6)
    for k in range(3):
        box(W2, 0.005, 0.005, (0, -0.1 - k * 0.08, H2 + 0.1 + k * 0.1), steel)
    rec((0, 0, H2 / 2), W2 / 2, 0.08, H2 / 2)

elif KIND == "boom_barrier":
    # A counterweighted boom barrier: a post, a long pole that lifts, a
    # red-and-white striped arm, and the counterweight box.
    box(0.18, 0.18, 1.2, (0, 0, 0.6), steel, bevel=0.01, collide=True)     # the post
    box(0.28, 0.28, 0.25, (0, 0, 1.25), steel, bevel=0.01)                 # the head housing
    # the arm, down (closed) across the road
    L = 3.6
    arm = box(L, 0.09, 0.12, (L / 2 + 0.15, 0, 1.2), steel, bevel=0.01)
    # a support foot at the far end
    box(0.1, 0.1, 1.15, (L + 0.1, 0, 0.575), steel)
    rec((L / 2 + 0.15, 0, 1.2), L / 2, 0.1, 0.12)
    # the counterweight on the short end
    box(0.35, 0.35, 0.35, (-0.5, 0, 1.2), steel, bevel=0.02)
    rec((0, 0, 0.6), 0.12, 0.12, 0.6)

elif KIND == "checkpoint":
    # A guard booth: a small hut with a window and a low sandbag skirt.
    W2, D2, H2 = 1.6, 1.6, 2.4
    for sy in (-1, 1):
        box(W2, 0.08, H2, (0, sy * D2 / 2, H2 / 2), concrete, bevel=0.01, collide=True)
    box(0.08, D2, H2, (-W2 / 2, 0, H2 / 2), concrete, bevel=0.01, collide=True)   # back
    box(0.08, D2, 0.9, (W2 / 2, 0, H2 - 0.45), concrete, bevel=0.01)              # front lintel
    box(0.08, D2, 0.9, (W2 / 2, 0, 0.45), concrete, bevel=0.01)                   # front sill
    box(W2 + 0.3, D2 + 0.3, 0.12, (0, 0, H2 + 0.06), concrete, bevel=0.01)        # roof
    rec((0, 0, H2 / 2), W2 / 2, D2 / 2, H2 / 2)

else:                          # jersey handled above; fallback plain block
    box(1, 1, 1, (0, 0, 0.5), concrete, collide=True)


# --------------------------------------------------------------- materials
def finish(objs, name, base, rough, metal, tex=None, tint=None, csize=1.2):
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
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cube_project(cube_size=csize)
    bpy.ops.object.mode_set(mode='OBJECT')
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = m.node_tree.nodes.new('ShaderNodeTexImage')
            tn.image = img
            if tint:
                mix = m.node_tree.nodes.new('ShaderNodeMixRGB')
                mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0
                mix.inputs['Color2'].default_value = tint
                m.node_tree.links.new(tn.outputs['Color'], mix.inputs['Color1'])
                m.node_tree.links.new(mix.outputs['Color'], b.inputs['Base Color'])
            else:
                m.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


parts = []
parts.append(finish(concrete, "concrete", (0.42, 0.42, 0.40, 1), 0.9, 0.0,
                    tex="t_concrete.jpg", csize=1.6))
parts.append(finish(steel, "steel", (0.46, 0.48, 0.49, 1), 0.55, 0.6,
                    tex="t_gunsteel.jpg", csize=0.6))
parts.append(finish(gravel, "gravel", (0.5, 0.45, 0.36, 1), 1.0, 0.0,
                    tex="g_gravel_d.jpg", csize=0.6))
parts.append(finish(cloth, "cloth", (0.55, 0.5, 0.36, 1), 1.0, 0.0,
                    tex="t_cloth_d.jpg", tint=(0.62, 0.58, 0.42, 1), csize=0.5))
parts.append(finish(wood, "wood", (0.4, 0.28, 0.16, 1), 0.75, 0.0,
                    tex="t_wood_d.jpg", tint=(0.72, 0.5, 0.3, 1)))
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
print("RESULT %s verts=%d tris=%d colliders=%d" % (KIND, len(me.vertices), len(me.loop_triangles), len(COLLIDERS)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
SPOTS = []
try:
    SPOTS.append(dict(CLIMB, k="climb"))
except NameError:
    pass
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS, "spots": SPOTS}, f)
print("WROTE", OUT)
