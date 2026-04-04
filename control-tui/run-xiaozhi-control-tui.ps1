$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path $PSScriptRoot).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (!(Test-Path $python)) {
    py -3.10 -m venv (Join-Path $projectRoot ".venv")
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $projectRoot "requirements.txt")
}

Push-Location $projectRoot
try {
    & $python -m xiaozhi_control_tui.main
}
finally {
    Pop-Location
}
