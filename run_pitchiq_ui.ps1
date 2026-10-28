$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython -PathType Leaf) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command python -ErrorAction Stop
    $Python = $PythonCommand.Source
}

Set-Location $ProjectRoot
Write-Host "Launching PitchIQ Unified Mode (Basic + Advanced)..." -ForegroundColor Cyan
& $Python -m pitchiq.unified
exit $LASTEXITCODE
