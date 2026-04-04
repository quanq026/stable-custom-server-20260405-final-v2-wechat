param(
    [string]$WorktreeRoot = "",
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $WorktreeRoot) {
    $WorktreeRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Import-EnvFile {
    param([string]$Path)

    if (!(Test-Path $Path)) {
        return
    }

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Length -ne 2) {
            return
        }

        $key = $parts[0].Trim()
        $value = $parts[1]
        if (-not $key) {
            return
        }

        [System.Environment]::SetEnvironmentVariable($key, $value)
    }
}

Import-EnvFile -Path (Join-Path $WorktreeRoot ".env.local")

$python = $null
if ($PythonPath) {
    $python = $PythonPath
} elseif ($env:XIAOZHI_BRIDGE_PYTHON) {
    $python = $env:XIAOZHI_BRIDGE_PYTHON
} else {
    $python = Join-Path $WorktreeRoot ".venv\Scripts\python.exe"
}

if (!(Test-Path $python)) {
    throw "Python runtime not found at $python"
}

$logDir = Join-Path $WorktreeRoot "tmp"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdoutLog = Join-Path $logDir "bridge-clean.out.log"
$stderrLog = Join-Path $logDir "bridge-clean.err.log"

$bridgeCmdPattern = [regex]::Escape((Join-Path $WorktreeRoot "xiaozhi_bridge\\server.py"))
Get-CimInstance Win32_Process |
    Where-Object {
        ($_.CommandLine -like "*xiaozhi_bridge.server*") -or
        ($_.CommandLine -match $bridgeCmdPattern)
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

$existing8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing8000) {
    $existing8000 | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
}

$process = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "xiaozhi_bridge.server") `
    -WorkingDirectory $WorktreeRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

$listening = $null
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 2
    if ($process.HasExited) {
        throw "Bridge server exited early with code $($process.ExitCode). Check $stderrLog"
    }

    $listening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
        Where-Object {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.OwningProcess)"
            $proc.CommandLine -like "*xiaozhi_bridge.server*"
        }
    if ($listening) {
        break
    }
}

if (-not $listening) {
    throw "Bridge server failed to start on port 8000 within timeout. Check $stderrLog"
}

Write-Output "Bridge server running on port 8000"
Write-Output "stdout: $stdoutLog"
Write-Output "stderr: $stderrLog"
