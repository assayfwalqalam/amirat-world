# The whole tree set, rebuilt on the organic trunk.
#
# Five variants of every kind, and every variant is a different HABIT (upright,
# spreading, leaning, multistem, forked) so five olives are five different
# olives rather than five draws of the same one.
#
# The blossom giants come in his three sizes. The scales are chosen against the
# tallest ordinary tree (pine, about 15m):
#   1.7 -> roughly twice it     2.6 -> three times     3.4 -> four times
# and the wood thickens faster than the height (RSCALE = SCALE^1.12).
$B = "C:\Users\sandk\Tools\blender-4.2.1-windows-x64\blender.exe"
$R = "C:\Users\sandk\amirat-world"
$A = "$R\assets"; $M = "$R\assets\models\tree"

New-Item -ItemType Directory -Force -Path $M | Out-Null

foreach ($k in @("olive", "plane", "cypress", "tamarisk", "fig", "pine")) {
  foreach ($i in 1..5) {
    & $B --background --python "$R\tools\make_tree.py" -- $k $i "$M\${k}_$i.glb" $A 1.0 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}

# the blossom giants: three sizes, five variants each
$tiers = @{ "2x" = 1.7; "3x" = 2.6; "4x" = 3.4 }
foreach ($t in $tiers.Keys) {
  foreach ($i in 1..5) {
    & $B --background --python "$R\tools\make_tree.py" -- blossom $i "$M\blossom_${t}_$i.glb" $A $tiers[$t] 2>&1 |
      Select-String -Pattern "^RESULT|Error:|Traceback" | ForEach-Object { $_.Line }
  }
}
Write-Output "BATCH TREES DONE"
