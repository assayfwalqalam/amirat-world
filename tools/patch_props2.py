"""The prop overhaul he ordered.

1. Vessels were circles stacked until they resembled a pot. Every vessel kind
   is now turned on a lathe from a real silhouette (the same approach as the
   pottery pack), with wheel rings and an uneven rim.
2. Every prop kind gets a photographed material: weathered timber for the
   wooden things, fired clay for the vessels, woven cloth for the soft things,
   iron stays iron.
"""
import pathlib

LATHE = '''

def lathe(profile, segments=18, thickness=0.015):
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

'''

VESSELS = {
    "pot": '''elif KIND == "pot":
    lathe([(0.10, 0.0), (0.17, 0.04), (0.24, 0.16), (0.26, 0.32), (0.22, 0.46),
           (0.15, 0.55), (0.13, 0.62), (0.16, 0.67), (0.15, 0.70)])
    rec((0, 0, 0.35), 0.24, 0.24, 0.35)
''',
    "waterjug": '''elif KIND == "waterjug":
    lathe([(0.07, 0.0), (0.13, 0.03), (0.19, 0.14), (0.21, 0.30), (0.17, 0.44),
           (0.09, 0.54), (0.065, 0.66), (0.09, 0.73), (0.085, 0.76)])
    for i in range(8):
        t = i / 7.0
        z = 0.30 + t * 0.36
        rr = 0.14 + math.sin(t * math.pi) * 0.07
        cyl(0.016, 0.016, 0.05, (rr, 0, z), rot=(0.5, 0, 0), verts=6)
    rec((0, 0, 0.38), 0.2, 0.2, 0.38)
''',
    "bowl": '''elif KIND == "bowl":
    lathe([(0.05, 0.0), (0.10, 0.015), (0.17, 0.06), (0.22, 0.13), (0.24, 0.19),
           (0.24, 0.21)], thickness=0.012)
    for i in range(5):
        a = i * 1.3
        b2 = sphere(0.05, (math.cos(a) * 0.06, math.sin(a) * 0.06, 0.20))
        jitter(b2, 0.008)
''',
    "oillamp": '''elif KIND == "oillamp":
    lathe([(0.035, 0.0), (0.075, 0.012), (0.10, 0.04), (0.085, 0.075),
           (0.045, 0.095), (0.055, 0.11)], thickness=0.008, segments=14)
    cyl(0.02, 0.014, 0.1, (0.1, 0, 0.055), rot=(0, 1.25, 0), verts=8)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.009,
                                     location=(-0.1, 0, 0.06),
                                     major_segments=10, minor_segments=5,
                                     rotation=(0, 0.5, 0))
    parts.append(bpy.context.active_object)
''',
    "plantpot": '''elif KIND == "plantpot":
    lathe([(0.11, 0.0), (0.14, 0.02), (0.17, 0.14), (0.20, 0.30), (0.21, 0.34)],
          thickness=0.014)
    rec((0, 0, 0.17), 0.19, 0.19, 0.17)
    for i in range(9):
        a = random.uniform(0, 6.28)
        lean = random.uniform(0.2, 0.5)
        cyl(0.012, 0.004, random.uniform(0.3, 0.55),
            (math.cos(a) * 0.06, math.sin(a) * 0.06, 0.5),
            rot=(lean * math.sin(a), lean * math.cos(a), 0), verts=5)
''',
}

MATERIAL = '''
# ------------------------------------------------- photographed materials
WOODY = {"barrel", "barrels", "crates", "cart", "bench", "stall", "table",
         "stool", "chest", "broom", "swordrack", "spears", "bowarrows",
         "firewood", "ladder", "pergola", "torchpost"}
CLAYY = {"pot", "jars", "waterjug", "oillamp", "bowl", "plantpot", "bread"}
CLOTHY = {"awning", "carpet", "cushions", "sacks"}

tex_file = None
gain = 2.4
if KIND in WOODY:
    tex_file = "t_wood_d.jpg"
elif KIND in CLAYY:
    tex_file = "t_clay_d.jpg"
elif KIND in CLOTHY:
    tex_file = "t_cloth_d.jpg"

if tex_file is not None:
    path = os.path.abspath(os.path.join(ASSETS, tex_file))
    if os.path.exists(path):
        img = bpy.data.images.load(path)
        tn2 = nt.nodes.new('ShaderNodeTexImage')
        tn2.image = img
        mix2 = nt.nodes.new('ShaderNodeMixRGB')
        mix2.blend_type = 'MULTIPLY'
        mix2.inputs['Fac'].default_value = 1.0
        mix2.inputs['Color2'].default_value = (TINT[0] * gain, TINT[1] * gain, TINT[2] * gain, 1)
        nt.links.new(tn2.outputs['Color'], mix2.inputs['Color1'])
        nt.links.new(mix2.outputs['Color'], bsdf.inputs['Base Color'])
        img.pack()
'''


def main():
    p = pathlib.Path("tools/make_props.py")
    s = p.read_text(encoding="utf-8")

    # the lathe helper, once
    if "def lathe(" not in s:
        anchor = "COLLIDERS = []"
        i = s.index(anchor)
        j = s.index("\n", i) + 1
        s = s[:j] + LATHE + s[j:]

    # replace each stacked-circle vessel with its turned silhouette
    import re
    for kind, block in VESSELS.items():
        m = re.search(r'elif KIND == "%s":\n(?:.*?\n)*?(?=\nelif KIND == |\n# ---)' % kind, s)
        assert m, kind
        s = s[:m.start()] + block + s[m.end():]

    # jars: three turned jars leaning together
    m = re.search(r'elif KIND == "jars":\n(?:.*?\n)*?(?=\nelif KIND == |\n# ---)', s)
    if m:
        s = s[:m.start()] + '''elif KIND == "jars":
    for k, (jx, jy, js) in enumerate([(-0.22, 0.05, 1.0), (0.16, -0.08, 0.85), (0.05, 0.22, 0.7)]):
        ob2 = lathe([(0.08 * js, 0.0), (0.14 * js, 0.03), (0.19 * js, 0.14),
                     (0.21 * js, 0.3), (0.17 * js, 0.44), (0.11 * js, 0.52),
                     (0.13 * js, 0.58), (0.12 * js, 0.60)])
        ob2.location = (jx, jy, 0)
        ob2.rotation_euler = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0)
        bpy.ops.object.transform_apply(location=True, rotation=True)
    rec((0, 0, 0.3), 0.4, 0.4, 0.3)
''' + s[m.end():]

    # the material pass goes right before the bake block
    if "photographed materials" not in s:
        anchor2 = "while len(ob.data.color_attributes):"
        i2 = s.index(anchor2)
        s = s[:i2] + MATERIAL + "\n" + s[i2:]

    p.write_text(s, encoding="utf-8")
    print("vessels turned, materials photographed")


if __name__ == "__main__":
    main()
