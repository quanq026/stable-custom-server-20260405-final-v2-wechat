param()

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildDir = Join-Path $projectRoot "build-host-tests"
if (!(Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

$exe = Join-Path $buildDir "bridge_discovery_test.exe"
$src = Join-Path $projectRoot "host_tests\\bridge_discovery_test.cpp"
$helper = Join-Path $projectRoot "main\\protocols\\bridge_discovery_logic.cc"

& "C:\msys64\ucrt64\bin\g++.exe" "-std=c++17" "-Wall" "-Wextra" "-pedantic" $src $helper "-o" $exe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $exe
exit $LASTEXITCODE
