param(
    [Parameter(Mandatory=$true)] [string]$Blend,
    [Parameter(Mandatory=$true)] [string]$OutputDir,
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [double]$SideDistance = 3.0,
    [double]$SideHeight = 0.0,
    [double]$FrontDistance = 3.0,
    [double]$FrontHeight = 0.45
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path -LiteralPath $Blend)) { throw "Blend not found: $Blend" }
if (-not (Test-Path -LiteralPath $Blender)) { throw "Blender not found: $Blender" }

$combined = Join-Path $OutputDir "calibrated_two_camera_standing.blend"
$renders = Join-Path $OutputDir "calibration_renders"
python tools\combine_calibrated_cameras.py $Blend --output $combined --blender $Blender --side-distance $SideDistance --side-height $SideHeight --front-distance $FrontDistance --front-height $FrontHeight
if ($LASTEXITCODE -ne 0) { throw "Camera combination failed." }
python tools\render_calibrated_camera_pair.py $combined --output-dir $renders --blender $Blender
if ($LASTEXITCODE -ne 0) { throw "Camera render verification failed." }
Write-Host "Camera calibration package created:" -ForegroundColor Green
Write-Host $combined
Write-Host $renders
