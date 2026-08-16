# Rebuilds every building with the clean pass. One Blender at a time.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
$set = @(
  @("house",1),@("house",9),@("house",14),@("house",21),@("house",27),
  @("tower",2),@("tower",7),@("tower",16),@("tower",23),
  @("court",8),@("court",18),@("court",25),
  @("shops",4),@("shops",11),@("shops",19),
  @("riad",12),@("riad",26),
  @("block",10),@("block",13),@("block",20),@("block",28)
)
foreach ($v in $set) {
  & $B --background --python "$R\tools\make_building.py" -- $v[0] $v[1] "$M\kit\$($v[0])_$($v[1]).glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
foreach ($i in 21..30) {
  & $B --background --python "$R\tools\make_house.py" -- $i "$M\bh$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
Write-Output "CLEAN REBUILD DONE"
