"""Wires the baked textures into the fence and pottery generators."""
import pathlib

WIRE = '''
tex_path = os.path.abspath(os.path.join(ASSETS, "{tex}"))
tn = None
if os.path.exists(tex_path):
    img = bpy.data.images.load(tex_path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    mixc = nt.nodes.new('ShaderNodeMixRGB')
    mixc.blend_type = 'MULTIPLY'
    mixc.inputs['Fac'].default_value = 1.0
    mixc.inputs['Color2'].default_value = (TINT[0] * {gain}, TINT[1] * {gain}, TINT[2] * {gain}, 1)
    nt.links.new(tn.outputs['Color'], mixc.inputs['Color1'])
    nt.links.new(mixc.outputs['Color'], bsdf.inputs['Base Color'])
'''


def patch(path, tex, gain, anchor):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    if "ShaderNodeTexImage" in s:
        print(path, "already textured")
        return
    assert anchor in s, path + ": anchor missing"
    s = s.replace(anchor, anchor + WIRE.format(tex=tex, gain=gain), 1)
    # pack the image so the .glb carries it
    s = s.replace("""bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(""",
                  """if tn is not None:
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
    bpy.ops.export_scene.gltf(""", 1)
    p.write_text(s, encoding="utf-8")
    print(path, "-> textured with", tex)


# both scripts already have `nt` and `bsdf` and a TINT tuple in scope
patch("tools/make_fence.py", "t_wood_d.jpg", 2.6,
      'bsdf.inputs["Roughness"].default_value = 0.94')
patch("tools/make_pottery.py", "t_clay_d.jpg", 2.4,
      'bsdf.inputs["Roughness"].default_value = 0.42 if glazed else 0.88')
