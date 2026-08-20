# Rebuilds the twenty market stalls. They are named <shape>_<trade>.glb and
# the pair is the argument, so the list is read straight off the models folder
# and nothing can drift out of step with what the town actually loads.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models\stall"
Get-ChildItem "$M\*.glb" | Where-Object { $_.Name -notlike "*.hi.glb" } | ForEach-Object {
    $n = $_.BaseName
    $i = $n.IndexOf("_")
    if ($i -lt 1) { return }
    $shape = $n.Substring(0, $i)
    $trade = $n.Substring($i + 1)
    & $B --background --python "$R\tools\make_stall.py" -- $shape $trade "$M\$n.glb" $A 2>&1 |
        Select-String -Pattern "^RESULT|Error:|Traceback|NameError" | ForEach-Object { $_.Line }
}
Write-Output "STALLS DONE"
