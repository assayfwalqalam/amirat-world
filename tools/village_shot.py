# Lays the ten town houses out as a cluster and shoots it from the same kind
# of viewpoint as the Afghan Ursilat panorama, so the two can be put side by
# side and judged.
#   blender --background --python village_shot.py -- <out.png> [angle]
#
# Daylight on purpose: this is a workshop sheet for judging shape, not a
# picture of the game. The game itself is night only.
import bpy, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "village.png"
ANGLE = argv[1] if len(argv) > 1 else "pan"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets", "models")
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1600
scene.render.resolution_y = 900


def load(path, loc=(0, 0, 0), rot=0.0, scale=1.0):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for o in bpy.data.objects:
        if o in before or o.parent is not None:
            continue
        o.location = loc
        o.rotation_euler[2] = rot
        o.scale = (scale, scale, scale)


# the town's own spacing: houses at 1.38, lanes left between them
SC = 1.38
spots = []
for gz in range(-2, 3):
    for gx in range(-2, 3):
        x = gx * 17.5 + random.uniform(-3.4, 3.4)
        y = gz * 16.5 + random.uniform(-3.0, 3.0)
        spots.append((x, y, random.uniform(0, 6.283)))

keys = ["bh%d" % i for i in range(21, 31)]
for i, (x, y, r) in enumerate(spots):
    p = os.path.join(M, keys[i % len(keys)] + ".glb")
    if os.path.exists(p):
        load(p, (x, y, 0.0), r, SC)

# the ground
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.02))
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
    mp.inputs['Scale'].default_value = (60, 60, 60)
    gm.node_tree.links.new(co.outputs['UV'], mp.inputs['Vector'])
    gm.node_tree.links.new(mp.outputs['Vector'], tn.inputs['Vector'])
    gm.node_tree.links.new(tn.outputs['Color'], gb.inputs['Base Color'])
gb.inputs['Roughness'].default_value = 1.0
gr.data.materials.append(gm)

bpy.ops.object.light_add(type='SUN', location=(0, 0, 60))
sun = bpy.context.active_object
sun.data.energy = 3.6
sun.data.color = (1.0, 0.96, 0.90)
sun.data.angle = 0.09
sun.rotation_euler = (math.radians(46), 0, math.radians(-52))

w = bpy.data.worlds.new("w")
scene.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.80, 0.84, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.55

if ANGLE == "eye":                      # standing in front of the row
    loc, rx, rz, lens = (3.0, -58.0, 1.75), 87, 2, 32
elif ANGLE == "close":                  # a corner, near enough to read a door
    loc, rx, rz, lens = (11.0, -54.0, 6.5), 79, 11, 45
else:                                   # the panorama, as in the reference
    loc, rx, rz, lens = (44.0, -96.0, 44.0), 68, 24, 42

bpy.ops.object.camera_add(location=loc)
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(rx), 0, math.radians(rz))
cam.data.lens = lens
scene.camera = cam

scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("Saved:", OUT)
