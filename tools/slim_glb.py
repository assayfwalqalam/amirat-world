# Cuts a downloaded model down to a sane triangle count.
#   blender --background --python slim_glb.py -- <in.glb> <out.glb> <budget> [leaf_budget]
#
# Solid parts (trunk, branch, bark, rock) collapse well and are decimated hard.
# Leaf and flower meshes are alpha-cut cards: collapsing them merges the cards
# into shreds, so they get a much gentler budget, or none at all.
import bpy, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = argv[0]
OUT = argv[1]
BUDGET = int(argv[2]) if len(argv) > 2 else 9000
LEAF_BUDGET = int(argv[3]) if len(argv) > 3 else 0      # 0 = never touch leaves

LEAFY = ("leaf", "leaves", "flower", "petal", "blossom", "foliage", "card", "grass")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

before = after = 0
for ob in list(bpy.data.objects):
    if ob.type != 'MESH':
        continue
    me = ob.data
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    before += n

    names = (ob.name + " " + me.name + " " +
             " ".join(m.name for m in me.materials if m)).lower()
    leafy = any(k in names for k in LEAFY)
    budget = LEAF_BUDGET if leafy else BUDGET
    if budget and n > budget:
        d = ob.modifiers.new("dec", 'DECIMATE')
        d.decimate_type = 'COLLAPSE'
        d.ratio = max(0.004, budget / float(n))
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=d.name)
        me = ob.data
    me.calc_loop_triangles()
    after += len(me.loop_triangles)
    print("  %-34s %7d -> %7d%s" % (ob.name[:34], n, len(me.loop_triangles),
                                    "  (leaf)" if leafy else ""))

print("RESULT %s %d -> %d tris" % (os.path.basename(SRC), before, after))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True)
print("WROTE", OUT)
