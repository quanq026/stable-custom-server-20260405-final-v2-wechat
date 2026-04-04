param()

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildDir = Join-Path $projectRoot "build-host-tests"
if (!(Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

$exe = Join-Path $buildDir "volume_gesture_test.exe"
$src = Join-Path $projectRoot "host_tests\\volume_gesture_test.cpp"
$helper = Join-Path $projectRoot "main\\boards\\es3n28p-lcd28\\volume_gesture.cc"

& "C:\msys64\ucrt64\bin\g++.exe" "-std=c++17" "-Wall" "-Wextra" "-pedantic" $src $helper "-o" $exe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $exe
exit $LASTEXITCODE
