# Builds the whole asset kit: fences first (fast), then the buildings.
# One Blender at a time, so the machine is never loaded with more than one.
param([string]$Only = "all")
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"
New-Item -ItemType Directory -Force "$R\assets\models\kit" | Out-Null
New-Item -ItemType Directory -Force "$R\assets\models\fence" | Out-Null

if ($Only -eq "all" -or $Only -eq "fence") {
  foreach ($s in @("rail","picket","wattle","lattice","palm","hurdle","post","gate","low","brace")) {
    & $B --background --python "$R\tools\make_fence.py" -- $s "$R\assets\models\fence\$s.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}

if ($Only -eq "all" -or $Only -eq "build") {
  $set = @(
    @("house",1),@("house",5),@("house",9),@("house",14),@("house",21),@("house",27),
    @("tower",2),@("tower",7),@("tower",16),@("tower",23),
    @("court",3),@("court",8),@("court",18),@("court",25),
    @("shops",4),@("shops",11),@("shops",19),
    @("riad",6),@("riad",12),@("riad",26),
    @("block",10),@("block",13),@("block",20),@("block",28)
  )
  foreach ($v in $set) {
    $fam = $v[0]; $sd = $v[1]
    & $B --background --python "$R\tools\make_building.py" -- $fam $sd "$R\assets\models\kit\${fam}_$sd.glb" $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}

Write-Output "KIT BUILD DONE"
