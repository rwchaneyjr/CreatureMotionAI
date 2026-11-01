param(
    [Parameter(Mandatory=$true)]
    [string]$InputVideo,
    [string]$OutputDir = "data\generated\dual_camera_reference",
    [int]$SampleCount = 5
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $InputVideo)) {
    throw "Input video not found: $InputVideo"
}

python tools\prepare_dual_camera_reference.py $InputVideo --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw "Dual-camera validation failed. Review the preparation report before continuing."
}

python tools\extract_dual_camera_samples.py $InputVideo --output-dir (Join-Path $OutputDir "samples") --count $SampleCount
if ($LASTEXITCODE -ne 0) {
    throw "Sample extraction failed."
}

Write-Host "Two-view preparation passed." -ForegroundColor Green
Write-Host "Review: $OutputDir\dual_camera_preparation_report.json"
Write-Host "Samples: $(Join-Path $OutputDir 'samples')"
Write-Host "Pose fitting remains a separate gated stage."
