# Batch G: every tree regrown with leaf-card crowns.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
foreach ($k in @("olive", "plane", "cypress", "tamarisk", "fig")) {
  foreach ($i in 1..2) {
    if (($k -eq "olive") -and ($i -eq 1)) { continue }   # already built
    & $B --background --python "$R\tools\make_tree.py" -- $k $i "$M\tree\${k}_$i.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
foreach ($i in 1..3) {
  & $B --background --python "$R\tools\make_tree.py" -- giant $i "$M\tree\giant_$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
Write-Output "BATCH G DONE"
