# Renders preview sheets of the new packs, then rebuilds the buildings with
# their furnished interiors. One Blender at a time throughout.
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models"
foreach ($d in @("stall","pot","rock")) { New-Item -ItemType Directory -Force "$R\shots\$d" | Out-Null }

Write-Output "== previews: stalls"
foreach ($n in @("canopy_spice","canopy_fruit","leanto_pottery","trestle_metal",
                 "barrow_grain","mat_rope","booth_cloth","rack_cloth",
                 "trestle_basket","booth_spice","leanto_bread","mat_basket")) {
  & $B --background --python "$R\tools\preview.py" -- "$M\stall\$n.glb" "$R\shots\stall\$n.png" 2>&1 |
    Select-String -Pattern "Error:" | ForEach-Object { $_.Line }
}

Write-Output "== previews: pottery"
foreach ($n in @("amphora","jar","jug","storage","krater","urn","basin","flask",
                 "bowl","plate","pitcher","cookpot")) {
  & $B --background --python "$R\tools\preview.py" -- "$M\pot\$n.glb" "$R\shots\pot\$n.png" 2>&1 |
    Select-String -Pattern "Error:" | ForEach-Object { $_.Line }
}

Write-Output "== previews: rocks"
foreach ($n in @("boulder_1","slab_1","shard_1","round_1","stack_1","pebbles_1",
                 "scree_1","outcrop_1","cliff_1","kerb_1")) {
  & $B --background --python "$R\tools\preview.py" -- "$M\rock\$n.glb" "$R\shots\rock\$n.png" 2>&1 |
    Select-String -Pattern "Error:" | ForEach-Object { $_.Line }
}

Write-Output "== buildings with interiors"
$set = @(
  @("house",1),@("house",5),@("house",9),@("house",14),@("house",21),@("house",27),
  @("tower",2),@("tower",7),@("tower",16),@("tower",23),
  @("court",3),@("court",8),@("court",18),@("court",25),
  @("shops",4),@("shops",11),@("shops",19),
  @("riad",6),@("riad",12),@("riad",26),
  @("block",10),@("block",13),@("block",20),@("block",28)
)
foreach ($v in $set) {
  & $B --background --python "$R\tools\make_building.py" -- $v[0] $v[1] "$M\kit\$($v[0])_$($v[1]).glb" $A 2>&1 |
    Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
}

Write-Output "PREVIEW AND BUILD DONE"
