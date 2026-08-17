$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
foreach ($p in @("barrel","barrels","crates","jars","sacks","awning","bench","cart","well",
                 "stall","carpet","cushions","table","stool","chest","books","scrolls",
                 "inkset","bowl","bread","pot","plantpot","broom","spears","swordrack",
                 "bowarrows","basket","brazier","oillamp","waterjug","ropecoil","firewood",
                 "torch","torchpost","stones","ladder","pergola")) {
    & $B --background --python "$R\tools\make_props.py" -- $p "$M\p_$p.glb" $A 2>&1 |
        Select-String -Pattern "^RESULT|Error:|Traceback|NameError" | ForEach-Object { $_.Line }
}
Write-Output "PROPS V2 DONE"
