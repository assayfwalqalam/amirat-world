# Batch D: waits for the running Blender to finish, then the two small
# mosques, then every building rebuilt on the six approved walls. Sequential.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"

while (Get-Process blender -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 15 }
Write-Output ("grand.glb " + (Get-Item "$M\grand.glb").LastWriteTime)

New-Item -ItemType Directory -Force "$M\mosque" | Out-Null
foreach ($i in 1..2) {
  & $B --background --python "$R\tools\make_mosque_small.py" -- $i "$M\mosque\small_$i.glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}
& "$R\tools\rebuild_clean.ps1"
Write-Output "BATCH D DONE"
