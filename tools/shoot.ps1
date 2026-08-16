# Renders one fixed viewpoint headlessly.
#   powershell -File tools\shoot.ps1 <shot> <out.png> [width] [height]
#
# The page stops its own render loop once the models are in and the terrain
# queue has drained (see W.SHOT_MODE in js/world.js). Without that the virtual
# clock hands out frames forever and the screenshot never lands.
param(
    [string]$Shot = "2",
    [string]$Out  = "C:\Users\sandk\amirat-world\shots\shot.png",
    [int]$Width   = 1280,
    [int]$Height  = 760
)
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$prof = "C:\Users\sandk\AppData\Local\Temp\claude\C--Users-sandk\6d2fb409-b700-4fab-aef9-b77f7e8a911b\scratchpad\edgeshot"

if (Test-Path $Out) { Remove-Item $Out -Force }
& $edge --headless --disable-gpu --enable-unsafe-swiftshader --no-sandbox `
        --hide-scrollbars --user-data-dir="$prof" `
        --screenshot="$Out" --window-size="$Width,$Height" `
        --virtual-time-budget=90000 "http://localhost:8747/?shot=$Shot" 2>$null | Out-Null

if (Test-Path $Out) { "OK $Out " + (Get-Item $Out).Length + " bytes" } else { "FAILED: no file for shot $Shot" }
