# Renders a .glb from a few angles so the asset can be judged before it goes in the game.
#   blender --background --python preview.py -- <in.glb> <out.png>
import bpy, math, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = argv[0]
OUT = argv[1] if len(argv) > 1 else "preview.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 760
scene.render.film_transparent = False

bpy.ops.import_scene.gltf(filepath=SRC)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']

# frame everything
mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector((min(mn[i], w[i]) for i in range(3)))
        mx = Vector((max(mx[i], w[i]) for i in range(3)))
ctr = (mn + mx) / 2
size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)

# ground so the house has something to stand on
bpy.ops.mesh.primitive_plane_add(size=size * 8, location=(ctr.x, ctr.y, mn.z))
gmat = bpy.data.materials.new("ground")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.47, 0.35, 1)
gmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1
bpy.context.active_object.data.materials.append(gmat)

# a low warm key, like late sun, and a cool sky fill
bpy.ops.object.light_add(type='SUN', location=(ctr.x + size, ctr.y - size, ctr.z + size * 1.2))
sun = bpy.context.active_object
sun.data.energy = 2.6
sun.data.angle = math.radians(2)
sun.data.color = (1.0, 0.86, 0.68)
sun.rotation_euler = (math.radians(58), 0, math.radians(38))

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.56, 0.75, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.55

bpy.ops.object.camera_add(location=(ctr.x + size * 1.5, ctr.y - size * 1.9, ctr.z + size * 0.8))
cam = bpy.context.active_object
scene.camera = cam
d = (ctr - cam.location)
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 38

scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("PREVIEW", OUT)
