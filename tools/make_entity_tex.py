# -*- coding: utf-8 -*-
# THE ENTITY - a being of space dust at the edge of the sky.
#
#   blender --background --python tools/make_entity_tex.py -- assets/entity_raw.png
#
# His brief, kept exactly: an upper body only, hunched over, facing the
# tiny person on the ground the way the reference does; made of dust-like
# structures that only FAINTLY resemble a being - no face to be made out,
# just two points of light where eyes would be; misty, far, eerily big.
#
# It is rendered as a real VOLUME - Cycles, a metaball mass (smooth unions,
# nothing blocky) voxelised and eaten away by two scales of noise, lit from
# below-front the way the reference is lit by its horizon glow. The tint and
# the edge feather happen in a post pass (make_entity_post.py).
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "assets/entity_raw.png")

sc = bpy.context.scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ---------------------------------------------------------------- the mass
# The being faces +X (frame right, where the small person stands). The head
# is lowered and pushed forward off a high hunched back; a long ragged
# trail streams away to -X like a wind-carried cloak. Only the upper body.
bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))
mb = bpy.context.active_object
mb.data.resolution = 0.09
E = mb.data.elements
# the radii OVERLAP HARD - the first pass left them barely touching and the
# render was a string of separate puffs, not a body
# the HEAD must read against the hunch: pushed forward and clear of the
# cowl, with the hunched back rising ABOVE it - the looming line of the
# reference. The second pass fused everything into featureless pudding.
E[0].co = (0.66, 0, 1.36)          # the head, forward, lowered
E[0].radius = 0.50

def ball(x, y, z, r):
    e = E.new()
    e.co = (x, y, z)
    e.radius = r

ball(0.14, 0, 1.66, 0.58)          # the cowl behind the head
ball(-0.48, 0, 1.78, 0.78)         # the hunched back, HIGHER than the head
ball(-1.10, 0, 1.42, 0.84)         # the back mass, streaming away
ball(-1.72, 0.1, 1.12, 0.72)       # the trail
ball(-2.28, -0.1, 0.86, 0.58)      # the trail, thinning
ball(0.36, 0, 0.66, 0.68)          # the chest under the head
ball(0.84, 0, 0.42, 0.50)          # the near shoulder, toward the person
ball(-0.35, 0, 0.62, 0.88)        # the body core
ball(-1.10, 0, 0.40, 0.80)        # the lower drift
ball(-0.30, 0, -0.08, 0.92)       # the fade-out below

bpy.ops.object.convert(target='MESH')
mesh = bpy.context.active_object

# ---------------------------------------------------------------- volume
bpy.ops.object.volume_add(location=(0, 0, 0))
vol = bpy.context.active_object
m2v = vol.modifiers.new("m2v", 'MESH_TO_VOLUME')
m2v.object = mesh
m2v.density = 1.0
m2v.voxel_amount = 220
m2v.interior_band_width = 0.85
mesh.hide_render = True

mat = bpy.data.materials.new("dust")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
outp = nt.nodes.new('ShaderNodeOutputMaterial')
pv = nt.nodes.new('ShaderNodeVolumePrincipled')
pv.inputs['Color'].default_value = (0.72, 0.78, 0.92, 1)
pv.inputs['Anisotropy'].default_value = 0.25
pv.inputs['Emission Color'].default_value = (0.35, 0.42, 0.62, 1)

tex1 = nt.nodes.new('ShaderNodeTexNoise')
tex1.inputs['Scale'].default_value = 2.2
tex1.inputs['Detail'].default_value = 7.0
tex1.inputs['Roughness'].default_value = 0.62
tex1.inputs['Distortion'].default_value = 1.5   # filaments, not fog
tex2 = nt.nodes.new('ShaderNodeTexNoise')
tex2.inputs['Scale'].default_value = 5.5
tex2.inputs['Detail'].default_value = 8.0

# density = grid * billow^1.6 * (0.4 + 0.6 fine) * strength
attr = nt.nodes.new('ShaderNodeAttribute')
attr.attribute_name = "density"
p1 = nt.nodes.new('ShaderNodeMath'); p1.operation = 'POWER'
p1.inputs[1].default_value = 1.7
m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'
mm = nt.nodes.new('ShaderNodeMapRange')
mm.inputs['From Min'].default_value = 0.0
mm.inputs['From Max'].default_value = 1.0
mm.inputs['To Min'].default_value = 0.35
mm.inputs['To Max'].default_value = 1.0
m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'
m3.inputs[1].default_value = 32.0
nt.links.new(tex1.outputs['Fac'], p1.inputs[0])
nt.links.new(attr.outputs['Fac'], m1.inputs[0])
nt.links.new(p1.outputs['Value'], m1.inputs[1])
nt.links.new(tex2.outputs['Fac'], mm.inputs['Value'])
nt.links.new(m1.outputs['Value'], m2.inputs[0])
nt.links.new(mm.outputs['Result'], m2.inputs[1])
nt.links.new(m2.outputs['Value'], m3.inputs[0])
nt.links.new(m3.outputs['Value'], pv.inputs['Density'])
es = nt.nodes.new('ShaderNodeMath'); es.operation = 'MULTIPLY'
es.inputs[1].default_value = 0.055
nt.links.new(m3.outputs['Value'], es.inputs[0])
nt.links.new(es.outputs['Value'], pv.inputs['Emission Strength'])
nt.links.new(pv.outputs['Volume'], outp.inputs['Volume'])
vol.data.materials.append(mat)

# ------------------------------------------------- the two points of light
for (ex, ez) in ((0.52, 1.38), (0.78, 1.33)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.042, location=(ex, -0.30, ez),
                                         segments=12, ring_count=8)
    eye = bpy.context.active_object
    em = bpy.data.materials.new("star")
    em.use_nodes = True
    bs = em.node_tree.nodes["Principled BSDF"]
    try:
        bs.inputs["Emission Color"].default_value = (1.0, 0.98, 0.92, 1)
    except KeyError:
        bs.inputs["Emission"].default_value = (1.0, 0.98, 0.92, 1)
    bs.inputs["Emission Strength"].default_value = 60.0
    eye.data.materials.append(em)

# ---------------------------------------------------------------- light
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
sun.data.energy = 6.0
sun.data.color = (1.0, 0.92, 0.80)
sun.rotation_euler = (math.radians(112), 0, math.radians(-18))
sc.collection.objects.link(sun)
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA'))
fill.data.energy = 550.0
fill.data.color = (0.55, 0.65, 1.0)
fill.data.size = 9.0
fill.location = (2.5, -4.5, 2.2)
fill.rotation_euler = (math.radians(75), 0, math.radians(28))
sc.collection.objects.link(fill)

# ---------------------------------------------------------------- camera
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 5.4
cam.location = (-0.55, -8.0, 0.95)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam

sc.render.engine = 'CYCLES'
sc.cycles.samples = 72
sc.cycles.use_denoising = True
sc.cycles.volume_step_rate = 1.0
sc.render.film_transparent = True
sc.render.resolution_x = 1280
sc.render.resolution_y = 1280
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = OUT
sc.world = bpy.data.worlds.new("w")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)

bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
