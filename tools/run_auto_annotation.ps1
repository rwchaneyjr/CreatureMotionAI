param(
    [string]$Video = "C:\Users\rober\Downloads\8leggedBalisk.mp4",
    [string]$Output = "data\generated\dlc_proposals_sample",
    [string]$Frames = "60,120,180"
)
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$python = "C:\Users\rober\AppData\Local\Programs\Python\Python312\python.exe"
& $python "$project\tools\propose_dlc_annotations.py" --video $Video --output $Output --frames $Frames
Write-Host "Proposal dataset created in $Output"
Write-Host "Review overlays in $Output\overlays before approving labels."
