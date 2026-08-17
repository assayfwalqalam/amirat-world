# Batch J: the variant set. Every kind gets five HABITS (upright, spreading,
# leaning, multistem, forked) so five variants are five different trees, not
# five draws of the same one. The flowering giants get ten, across the
# photographed blossom sheets.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"

New-Item -ItemType Directory -Force -Path "$M\tree" | Out-Null

foreach ($k in @("olive", "plane", "cypress", "tamarisk", "fig", "pine")) {
  foreach ($i in 1..5) {
    & $B --background --python "$R\tools\make_tree.py" -- $k $i "$M\tree\${k}_$i.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
foreach ($i in 1..5) {
  & $B --background --python "$R\tools\make_tree.py" -- giant $i "$M\tree\giant_$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($i in 1..10) {
  & $B --background --python "$R\tools\make_tree.py" -- blossom $i "$M\tree\blossom_$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
Write-Output "BATCH J DONE"
