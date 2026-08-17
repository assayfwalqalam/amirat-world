$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
foreach ($d in @("tree","book")) { New-Item -ItemType Directory -Force "$M\$d" | Out-Null }
foreach ($k in @("olive","plane","cypress","tamarisk","fig")) {
  foreach ($s in @(1,2)) {
    & $B --background --python "$R\tools\make_tree.py" -- $k $s "$M\tree\${k}_$s.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
foreach ($k in @("laid","pair","stack","row","shelfrow","case","open")) {
  & $B --background --python "$R\tools\make_books.py" -- $k "$M\book\$k.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
# the stone buildings pick up the photographed ashlar
foreach ($w in @("seg","tower","tower_big","gate")) {
  & $B --background --python "$R\tools\make_wall.py" -- $w "$M\w_$w.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
& $B --background --python "$R\tools\make_mosque.py" -- "$M\m_mosque.glb" $A 2>&1 |
  Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
& $B --background --python "$R\tools\make_grand.py" -- "$M\grand.glb" $A 2>&1 |
  Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
Write-Output "BATCH C DONE"
