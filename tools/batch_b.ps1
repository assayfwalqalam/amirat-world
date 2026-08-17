$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
foreach ($d in @("bound","veh","minaret")) { New-Item -ItemType Directory -Force "$M\$d" | Out-Null }
foreach ($k in @("low","mid","high","corner","end","gateposts","ruin")) {
  & $B --background --python "$R\tools\make_boundary.py" -- $k "$M\bound\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($k in @("plank","plankgate")) {
  & $B --background --python "$R\tools\make_fence.py" -- $k "$M\fence\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($k in @("pickup","truck","minibus")) {
  & $B --background --python "$R\tools\make_vehicle.py" -- $k "$M\veh\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($k in @("square","round","octagon")) {
  & $B --background --python "$R\tools\make_minaret.py" -- $k "$M\minaret\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
Write-Output "BATCH B DONE"
