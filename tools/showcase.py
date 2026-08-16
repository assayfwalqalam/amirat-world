# Renders the proof scene: one house dressed with the new props, lit and
# framed the way the reference panorama is, for a side-by-side.
#   blender --background --python showcase.py -- <out.png>
import bpy, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "showcase.png"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets", "models")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 800


def load(path, loc=(0, 0, 0), rot=0.0, scale=1.0):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location = loc
            o.rotation_euler[2] = rot
            o.scale = (scale, scale, scale)
    return new


load(os.path.join(M, "kit", "house_5.glb"), (0, 0, 0))
load(os.path.join(M, "p_pergola.glb"), (-1.2, -7.6, 0), 0.12)
load(os.path.join(M, "p_ladder.glb"), (4.6, -5.35, 0), 0.06)
load(os.path.join(M, "p_basket.glb"), (2.6, -6.1, 0), 0.6)
load(os.path.join(M, "p_basket.glb"), (3.15, -6.35, 0), 2.1, 0.85)
load(os.path.join(M, "p_jars.glb"), (-4.3, -6.0, 0), 1.2, 0.9)
load(os.path.join(M, "pot", "storage.glb"), (5.3, -6.2, 0), 0.4)

# the ground: warm sand, big enough to fill the frame
bpy.ops.mesh.primitive_plane_add(size=90, location=(0, 0, 0.0))
gr = bpy.context.active_object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gb = gm.node_tree.nodes["Principled BSDF"]
tex = os.path.join(ROOT, "assets", "g_sand_d.jpg")
if os.path.exists(tex):
    img = bpy.data.images.load(tex)
    tn = gm.node_tree.nodes.new('ShaderNodeTexImage')
    tn.image = img
    mp = gm.node_tree.nodes.new('ShaderNodeMapping')
    co = gm.node_tree.nodes.new('ShaderNodeTexCoord')
    mp.inputs['Scale'].default_value = (26, 26, 26)
    gm.node_tree.links.new(co.outputs['UV'], mp.inputs['Vector'])
    gm.node_tree.links.new(mp.outputs['Vector'], tn.inputs['Vector'])
    gm.node_tree.links.new(tn.outputs['Color'], gb.inputs['Base Color'])
else:
    gb.inputs['Base Color'].default_value = (0.62, 0.52, 0.38, 1)
gb.inputs['Roughness'].default_value = 1.0
gr.data.materials.append(gm)

# the reference light: high sun, slightly warm, from the left
bpy.ops.object.light_add(type='SUN', location=(0, 0, 40))
sun = bpy.context.active_object
sun.data.energy = 4.8
sun.data.color = (1.0, 0.95, 0.86)
sun.data.angle = 0.06
sun.rotation_euler = (math.radians(40), 0, math.radians(-58))

w = bpy.data.worlds.new("w")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.74, 0.70, 0.62, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.42

# the panorama's viewpoint: elevated three-quarter, looking down a little
bpy.ops.object.camera_add(location=(10.5, -26.5, 9.8))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(72), 0, math.radians(21))
cam.data.lens = 36
scene.camera = cam

scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("Saved:", OUT)
