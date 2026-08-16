# Regenerates every Blender asset so the baked occlusion lands in COLOR_0.
# One Blender at a time, so the machine is never loaded with more than one.
# Note: the parameter must not be called $args -- that is a reserved automatic
# variable, and shadowing it silently drops every argument.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$M = "$R\assets\models"
$A = "$R\assets"

function Run($script, $argList) {
    & $B --background --python "$R\tools\$script" -- @argList 2>&1 |
        Select-String -Pattern "RESULT|Error:|NameError|SyntaxError|not be exported" |
        ForEach-Object { $_.Line }
}

$props = @("barrel","barrels","crates","jars","sacks","awning","bench","cart","well",
           "stall","carpet","cushions","table","stool","chest","books","scrolls",
           "inkset","bowl","bread","pot","plantpot","broom","spears","swordrack",
           "bowarrows","basket","brazier","oillamp","waterjug","ropecoil","firewood",
           "torch","torchpost","stones")
foreach ($p in $props) {
    Run "make_props.py" @($p, "$M\p_$p.glb", $A)
}

foreach ($w in @("seg","tower","tower_big","gate")) {
    Run "make_wall.py" @($w, "$M\w_$w.glb", $A)
}

Run "make_mosque.py" @("$M\m_mosque.glb", $A)

foreach ($i in 21..30) {
    Run "make_house.py" @("$i", "$M\bh$i.glb", $A)
}

Write-Output "ALL DONE"
