# Trees v3, to the Bannerlord bar (shots/ref/bannerlord_1..4): thick proper
# trunks, real radiating bough structure, and canopies built from dense
# CLUSTERS of leaf cards so they read as volumes with depth, never one flat
# sheet. Every tree at least two storeys. Many variants per kind.
#   blender --background --python make_tree.py -- <kind> <seed> <out.glb> [assets]
# Kinds: olive, plane, cypress, tamarisk, fig, giant, pine
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
    """One tapering limb of stacked cone segments with joint balls. Returns
    (tip, dir). Radii are REAL: a trunk is a log, not a twig."""
    segs = segs or max(3, int(length / 0.9))
    dx, dy, dz = direction
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    dx, dy, dz = dx / n, dy / n, dz / n
    x, y, z = p0
    seglen = length / segs
    # The bark has to FLOW up the limb. Projected per segment it gives every
    # joint its own unaligned mapping and the trunk reads as a stack of drums,
    # so the vertical coordinate carries on from where the last segment ended.
    voff = random.uniform(0, 4.0)
    for i in range(segs):
        t = i / float(segs)
        r = r0 + (r1 - r0) * t
        w = crook * seglen
        dx += random.uniform(-w, w) * 0.15
        dy += random.uniform(-w, w) * 0.15
        dz += random.uniform(-w * 0.5, w) * 0.15
        if min_dz is not None and dz < min_dz:
            dz = min_dz
        m = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / m, dy / m, dz / m
        nx, ny, nz = x + dx * seglen, y + dy * seglen, z + dz * seglen
        mid = ((x + nx) / 2, (y + ny) / 2, (z + nz) / 2)
        pitch = math.acos(max(-1.0, min(1.0, dz)))
        yaw = math.atan2(dy, dx)
        r_next = r0 + (r1 - r0) * (t + 1.0 / segs)
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r_next,
                                        depth=seglen * 1.26, location=mid, vertices=12)
        ob = bpy.context.active_object
        ob.rotation_euler = (0.0, pitch, yaw)
        bpy.ops.object.transform_apply(rotation=True)
        uvl = ob.data.uv_layers.active
        if uvl:
            us = (6.283 * max(r, r_next, 0.02)) / BARKSCALE
            vs = seglen / BARKSCALE
            for lp in uvl.data:
                lp.uv = (lp.uv[0] * us, lp.uv[1] * vs + voff)
            voff += vs
        wood.append(ob)
        # No joint balls. They were meant to hide the elbow where one segment
        # turns into the next, and every setting of them failed: at equal
        # radius their corners crenellate the trunk, smaller and the segment's
        # end teeth show through, larger and they read as bandage collars with
        # the bark running the wrong way round them. The segments overlap by a
        # quarter of their length instead, so there is no gap to hide, and a
        # bend just reads as a knuckle in the wood, which is what it is.
        x, y, z = nx, ny, nz
    return (x, y, z), (dx, dy, dz)


def card(at, size):
    """One leaf card, tilted freely."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=at)
    ob = bpy.context.active_object
    ob.scale = (size, size, 1)
    ob.rotation_euler = (random.uniform(0.6, 2.5),
                         random.uniform(0, 6.283),
                         random.uniform(0, 6.283))
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    leaf.append(ob)


def cluster(at, r, n=None):
    """A DENSE cluster of cards round one point: the unit of foliage. Cards
    overlap heavily so the mass reads solid from every side, never a sheet."""
    # A crown you can see the sky through is a scatter of paper sprigs on bare
    # sticks. Real foliage is a MASS: cards packed until the middle is opaque
    # and light only breaks through at the edges. Cards are two triangles, so
    # density is nearly free -- there was no reason to be sparing.
    n = n or random.randint(20, 28)
    for _ in range(n):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.6, 1.1)
        rr = random.uniform(0, r * 0.62)
        cx = at[0] + math.cos(a) * math.cos(el) * rr
        cy = at[1] + math.sin(a) * math.cos(el) * rr
        cz = at[2] + math.sin(el) * rr * 0.8
        card((cx, cy, cz), random.uniform(r * 0.95, r * 1.55))


def crown_of_clusters(at, spread, k, cr):
    """k clusters strewn through an ellipsoid: canopy WITH internal depth."""
    for _ in range(k):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.35, 1.1)
        rr = random.uniform(spread * 0.15, spread)
        cx = at[0] + math.cos(a) * math.cos(el) * rr
        cy = at[1] + math.sin(a) * math.cos(el) * rr
        cz = at[2] + math.sin(el) * rr * 0.7
        cluster((cx, cy, cz), cr)


GREEN = {
    "olive": (0.80, 0.86, 0.66), "plane": (0.82, 1.0, 0.72),
    "cypress": (0.38, 0.52, 0.40), "tamarisk": (0.84, 0.95, 0.70),
    "fig": (0.70, 0.95, 0.62), "giant": (0.78, 0.98, 0.70),
    "pine": (0.45, 0.62, 0.45),
}[KIND]
LEAFTEX = {
    "olive": "leafcard_fine.png", "tamarisk": "leafcard_fine.png",
    "cypress": "leafcard_fine.png", "plane": "leafcard_broad.png",
    "fig": "leafcard_broad2.png", "giant": "leafcard_broad.png",
    "pine": "leafcard_fine.png",
}[KIND]
# The trunks had NO texture at all: their colour came from a vertex-colour
# node, which is why they read as smooth blurred tubes. Real photographed
# bark now, CC0 from Poly Haven, with the furrow scale set per kind.
BARKTEX, BARKSCALE = {
    "olive":    ("t_bark_d.jpg", 0.75),
    "plane":    ("t_bark_d.jpg", 1.10),
    "fig":      ("t_bark_d.jpg", 0.95),
    "tamarisk": ("t_bark_d.jpg", 0.65),
    "cypress":  ("t_barkpine_d.jpg", 0.70),
    "pine":     ("t_barkpine_d.jpg", 1.00),
    "giant":    ("t_barkold_d.jpg", 1.70),
}[KIND]

# every tree is at least two storeys; trunks are logs
if KIND == "olive":
    H = random.uniform(6.5, 8.5)
    tip, d = limb((0, 0, 0), (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 1),
                  H * 0.4, 0.42, 0.24, crook=0.45, min_dz=0.66)
    for _ in range(random.randint(4, 6)):
        a = random.uniform(0, 6.283)
        t2, d2 = limb(tip, (math.cos(a), math.sin(a), random.uniform(0.6, 1.2)),
                      H * 0.42, 0.16, 0.05, crook=0.5)
        cluster(t2, H * 0.16)
        t3, _ = limb(t2, (math.cos(a + 0.7), math.sin(a + 0.7), random.uniform(0.3, 0.8)),
                     H * 0.18, 0.05, 0.02, segs=2, crook=0.5)
        cluster(t3, H * 0.13)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.16), H * 0.32, 26, H * 0.15)
    rec((0, 0, H * 0.3), 0.5, 0.5, H * 0.3)

elif KIND == "plane":
    H = random.uniform(11.0, 15.0)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.4, 0.55, 0.3, crook=0.22, min_dz=0.78)
    for _ in range(random.randint(5, 7)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.85, math.sin(a) * 0.85, 1.05),
                     H * 0.4, 0.2, 0.06, crook=0.35)
        cluster(t2, H * 0.15)
        t3, _ = limb(t2, (math.cos(a + 0.8), math.sin(a + 0.8), random.uniform(0.5, 1.0)),
                     H * 0.16, 0.06, 0.025, segs=2, crook=0.45)
        cluster(t3, H * 0.12)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.2), H * 0.34, 30, H * 0.14)
    rec((0, 0, H * 0.28), 0.6, 0.6, H * 0.28)

elif KIND == "cypress":
    H = random.uniform(8.5, 12.0)
    limb((0, 0, 0), (0, 0, 1), H * 0.24, 0.3, 0.16, crook=0.1, min_dz=0.9)
    n = int(H * 4.5)
    for i in range(n):
        t = i / float(n)
        rr = (1.0 - 0.75 * t) * (1.0 + random.uniform(-0.12, 0.12))
        z = H * 0.1 + t * H * 0.9
        a = random.uniform(0, 6.283)
        cluster((math.cos(a) * rr * 0.4, math.sin(a) * rr * 0.4, z),
                (0.6 + rr * 0.55), n=4)
    rec((0, 0, H * 0.4), 0.5, 0.5, H * 0.4)

elif KIND == "tamarisk":
    H = random.uniform(6.0, 8.0)
    for _ in range(random.randint(3, 4)):
        a = random.uniform(0, 6.283)
        tip, _ = limb((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0),
                      (math.cos(a) * 0.45, math.sin(a) * 0.45, 1.25),
                      H * 0.62, 0.2, 0.05, crook=0.4)
        cluster(tip, H * 0.17)
        t3, _ = limb(tip, (math.cos(a + 1.1), math.sin(a + 1.1), 0.7),
                     H * 0.2, 0.05, 0.02, segs=2, crook=0.5)
        cluster(t3, H * 0.13)
    crown_of_clusters((0, 0, H * 0.72), H * 0.32, 22, H * 0.15)
    rec((0, 0, H * 0.3), 0.45, 0.45, H * 0.3)

elif KIND == "fig":
    H = random.uniform(6.5, 9.0)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.3, 0.5, 0.3, crook=0.35, min_dz=0.7)
    for _ in range(random.randint(5, 7)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 1.25, math.sin(a) * 1.25, random.uniform(0.3, 0.7)),
                     H * 0.55, 0.18, 0.055, crook=0.45)
        cluster(t2, H * 0.18)
        cluster(((tip[0] + t2[0]) / 2, (tip[1] + t2[1]) / 2, (tip[2] + t2[2]) / 2 + H * 0.06),
                H * 0.14)
    rec((0, 0, H * 0.25), 0.55, 0.55, H * 0.25)

elif KIND == "pine":
    # the Bannerlord forest wall: straight trunk, whorls of boughs
    # shortening toward the top, dense dark foliage
    H = random.uniform(10.0, 15.0)
    limb((0, 0, 0), (0, 0, 1), H, 0.42, 0.06, segs=7, crook=0.06, min_dz=0.95)
    whorls = random.randint(6, 8)
    for wla in range(whorls):
        t = 0.3 + 0.68 * wla / (whorls - 1)
        z = H * t
        blen = H * 0.24 * (1.15 - t)
        for b in range(random.randint(4, 6)):
            a = random.uniform(0, 6.283)
            t2, _ = limb((0, 0, z), (math.cos(a), math.sin(a), random.uniform(0.05, 0.28)),
                         blen, 0.09 * (1.2 - t), 0.02, segs=2, crook=0.25)
            cluster(t2, blen * 0.5, n=5)
            cluster((t2[0] * 0.6, t2[1] * 0.6, z + blen * 0.1), blen * 0.42, n=4)
    cluster((0, 0, H * 1.0), H * 0.06, n=5)
    rec((0, 0, H * 0.4), 0.5, 0.5, H * 0.4)

else:                        # giant: the bustan patriarch, 5-7 storeys
    H = random.uniform(16.0, 21.0)
    tip, d = limb((0, 0, 0), (0, 0, 1), H * 0.36, 1.25, 0.66,
                  segs=6, crook=0.18, min_dz=0.82)
    for _ in range(random.randint(6, 8)):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.9, math.sin(a) * 0.9, random.uniform(0.55, 1.0)),
                     H * 0.4, 0.36, 0.1, crook=0.35)
        cluster(t2, H * 0.11)
        t3, _ = limb(t2, (math.cos(a + 0.9), math.sin(a + 0.9), random.uniform(0.4, 0.9)),
                     H * 0.16, 0.09, 0.03, segs=2, crook=0.4)
        cluster(t3, H * 0.09)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.22), H * 0.32, 34, H * 0.10)
    for _ in range(5):
        a = random.uniform(0, 6.283)
        limb((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.5),
             (math.cos(a), math.sin(a), -0.5), 1.8, 0.34, 0.07, segs=3, crook=0.3)
    rec((0, 0, H * 0.22), 1.2, 1.2, H * 0.22)


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


def join_leaf_cards(objs, tint):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = "leaf"
    me = ob.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for poly in me.polygons:
        g = 1.0 + random.uniform(-0.24, 0.24)
        for li in poly.loop_indices:
            col.data[li].color = (min(1.0, tint[0] * g), min(1.0, tint[1] * g),
                                  min(1.0, tint[2] * g), 1.0)
    m = bpy.data.materials.new("leafcards")
    m.use_nodes = True
    m.blend_method = 'CLIP'
    m.alpha_threshold = 0.32
    m.use_backface_culling = False
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.9
    path = os.path.abspath(os.path.join(ASSETS, "src", LEAFTEX))
    img = bpy.data.images.load(path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    vcn = nt.nodes.new('ShaderNodeVertexColor')
    vcn.layer_name = "ao"
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    nt.links.new(tn.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(vcn.outputs['Color'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(tn.outputs['Alpha'], b.inputs['Alpha'])
    img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


# The vertex colour used to BE the trunk colour, so it was near black. It is
# now only a per-face shade jitter riding on top of the bark photo, which
# means it must sit near white -- and never above 1.0, because glTF clamps a
# vertex-colour lift and the wood goes pastel.
w_ob = join_and_colour(wood, "wood", (0.74, 0.68, 0.61), 0.10)
l_ob = join_leaf_cards(leaf, GREEN)

# the wood keeps its own bark material; the join then carries both slots
mat = bpy.data.materials.new("bark")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.92
bpath = os.path.abspath(os.path.join(ASSETS, BARKTEX))
bimg = bpy.data.images.load(bpath)
btn = nt.nodes.new('ShaderNodeTexImage')
btn.image = bimg
vc = nt.nodes.new('ShaderNodeVertexColor')
vc.layer_name = "ao"
bmix = nt.nodes.new('ShaderNodeMixRGB')
bmix.blend_type = 'MULTIPLY'
bmix.inputs['Fac'].default_value = 1.0
nt.links.new(btn.outputs['Color'], bmix.inputs['Color1'])
nt.links.new(vc.outputs['Color'], bmix.inputs['Color2'])
nt.links.new(bmix.outputs['Color'], bsdf.inputs['Base Color'])
bimg.pack()
w_ob.data.materials.clear()
w_ob.data.materials.append(mat)

bpy.ops.object.select_all(action='DESELECT')
w_ob.select_set(True)
l_ob.select_set(True)
bpy.context.view_layer.objects.active = w_ob
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

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
