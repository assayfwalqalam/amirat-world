import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'C:\Users\sandk\amirat-world\assets\models\palm.glb')
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH':
        ob.scale = (1.35, 1.35, 1.05)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(scale=True)
bpy.ops.export_scene.gltf(filepath=r'C:\Users\sandk\amirat-world\assets\models\palm.glb', export_format='GLB')
print('RESULT palm thickened')
