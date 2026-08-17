# Batch I: trees v3 — every kind, four variants each (giants three), and the
# palm thickened. The Bannerlord hard rule.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"

foreach ($k in @("olive", "plane", "cypress", "tamarisk", "fig", "pine")) {
  foreach ($i in 1..4) {
    & $B --background --python "$R\tools\make_tree.py" -- $k $i "$M\tree\${k}_$i.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
foreach ($i in 1..3) {
  & $B --background --python "$R\tools\make_tree.py" -- giant $i "$M\tree\giant_$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
# thicken the palm: widen its trunk and crown laterally, once
$thicken = @"
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'$M\palm.glb')
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH':
        ob.scale = (1.35, 1.35, 1.05)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(scale=True)
bpy.ops.export_scene.gltf(filepath=r'$M\palm.glb', export_format='GLB')
print('RESULT palm thickened')
"@
Set-Content -Path "$R\tools\_thicken_palm.py" -Value $thicken -Encoding utf8
& $B --background --python "$R\tools\_thicken_palm.py" 2>&1 |
  Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
Write-Output "BATCH I DONE"
