# Rebuilds the whole asset library against the current textures.
# One Blender at a time. Order is by how much each matters on screen.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"
$M = "$R\assets\models"
foreach ($d in @("kit","fence","pot","rock")) { New-Item -ItemType Directory -Force "$M\$d" | Out-Null }

function Run($script, $argList, $label) {
    & $B --background --python "$R\tools\$script" -- @argList 2>&1 |
        Select-String -Pattern "^RESULT|Error:|Traceback|NameError|SyntaxError" |
        ForEach-Object { $_.Line }
}

Write-Output "== pottery"
foreach ($f in @("amphora","jar","squat","jug","storage","bowl","deepbowl","plate",
                 "oiljar","flask","krater","cookpot","pitcher","urn","basin","cup")) {
    Run "make_pottery.py" @($f, "$M\pot\$f.glb", $A)
}

Write-Output "== rocks"
foreach ($k in @("boulder","slab","shard","round","stack","pebbles","scree","outcrop","cliff","kerb")) {
    foreach ($s in @(1,2)) {
        Run "make_rock.py" @($k, $s, "$M\rock\${k}_$s.glb", $A)
    }
}

Write-Output "== fences"
foreach ($s in @("rail","picket","wattle","lattice","palm","brush","thorn","post","gate","low","brace")) {
    Run "make_fence.py" @($s, "$M\fence\$s.glb", $A)
}

Write-Output "== buildings"
$set = @(
  @("house",1),@("house",5),@("house",9),@("house",14),@("house",21),@("house",27),
  @("tower",2),@("tower",7),@("tower",16),@("tower",23),
  @("court",3),@("court",8),@("court",18),@("court",25),
  @("shops",4),@("shops",11),@("shops",19),
  @("riad",6),@("riad",12),@("riad",26),
  @("block",10),@("block",13),@("block",20),@("block",28)
)
foreach ($v in $set) {
    Run "make_building.py" @($v[0], $v[1], "$M\kit\$($v[0])_$($v[1]).glb", $A)
}

Write-Output "== city walls and the old town pieces"
foreach ($w in @("seg","tower","tower_big","gate")) {
    Run "make_wall.py" @($w, "$M\w_$w.glb", $A)
}
Run "make_mosque.py" @("$M\m_mosque.glb", $A)
foreach ($i in 21..30) { Run "make_house.py" @($i, "$M\bh$i.glb", $A) }

Write-Output "== props"
foreach ($p in @("barrel","barrels","crates","jars","sacks","awning","bench","cart","well",
                 "stall","carpet","cushions","table","stool","chest","books","scrolls",
                 "inkset","bowl","bread","pot","plantpot","broom","spears","swordrack",
                 "bowarrows","basket","brazier","oillamp","waterjug","ropecoil","firewood",
                 "torch","torchpost","stones")) {
    Run "make_props.py" @($p, "$M\p_$p.glb", $A)
}

Write-Output "== the great house"
Run "make_grand.py" @("$M\grand.glb", $A)

Write-Output "ALL ASSETS REBUILT"
