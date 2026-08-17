# Batch E: the inspection fixes. Trees regrown, vehicle cabs rebuilt,
# boundary walls onto plain moods. Sequential, one Blender at a time.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"

foreach ($k in @("olive", "plane", "cypress", "tamarisk", "fig")) {
  foreach ($i in 1..2) {
    & $B --background --python "$R\tools\make_tree.py" -- $k $i "$M\tree\${k}_$i.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
foreach ($k in @("pickup", "truck", "minibus")) {
  & $B --background --python "$R\tools\make_vehicle.py" -- $k "$M\veh\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($k in @("low", "mid", "high", "corner", "end", "gateposts", "ruin")) {
  & $B --background --python "$R\tools\make_boundary.py" -- $k "$M\bound\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
Write-Output "BATCH E DONE"
