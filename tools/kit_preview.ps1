# Generates a sample of the building kit and renders a preview of each.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$M = "$R\assets\models\kit"
$A = "$R\assets"
New-Item -ItemType Directory -Force $M | Out-Null
New-Item -ItemType Directory -Force "$R\shots\kit" | Out-Null

$set = @(
  @("house", 1), @("house", 5), @("house", 9),
  @("tower", 2), @("tower", 7),
  @("court", 3), @("court", 8),
  @("shops", 4), @("shops", 11),
  @("riad", 6), @("block", 10), @("block", 13)
)
foreach ($v in $set) {
  $fam = $v[0]; $sd = $v[1]
  $glb = "$M\${fam}_$sd.glb"
  if (-not (Test-Path $glb)) {
    & $B --background --python "$R\tools\make_building.py" -- $fam $sd $glb $A 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
  & $B --background --python "$R\tools\preview.py" -- $glb "$R\shots\kit\${fam}_$sd.png" 2>&1 |
    Select-String -Pattern "Saved|Error:" | ForEach-Object { $_.Line }
}
Write-Output "KIT PREVIEW DONE"
