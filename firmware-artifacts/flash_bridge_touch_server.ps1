param(
    [string]$Port = "",
    [switch]$EraseFlash
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$idfPath = "C:\Espressif\frameworks\esp-idf-v5.5.3"
$idfPython = "C:\Espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe"
$sdkconfigDefaults = "sdkconfig.defaults;sdkconfig.defaults.esp32s3;sdkconfig.defaults.bridge;sdkconfig.defaults.bridge.touch"

$env:IDF_PATH = $idfPath
$env:IDF_PYTHON_ENV_PATH = "C:\Espressif\python_env\idf5.5_py3.11_env"

$toolPaths = @(
    "C:\Espressif\frameworks\esp-idf-v5.5.3\components\espcoredump",
    "C:\Espressif\frameworks\esp-idf-v5.5.3\components\partition_table",
    "C:\Espressif\frameworks\esp-idf-v5.5.3\components\app_update",
    "C:\Espressif\tools\xtensa-esp-elf-gdb\16.3_20250913\xtensa-esp-elf-gdb\bin",
    "C:\Espressif\tools\riscv32-esp-elf-gdb\16.3_20250913\riscv32-esp-elf-gdb\bin",
    "C:\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20251107\xtensa-esp-elf\bin",
    "C:\Espressif\tools\esp-clang\esp-19.1.2_20250312\esp-clang\bin",
    "C:\Espressif\tools\riscv32-esp-elf\esp-14.2.0_20251107\riscv32-esp-elf\bin",
    "C:\Espressif\tools\esp32ulp-elf\2.38_20240113\esp32ulp-elf\bin",
    "C:\Espressif\tools\cmake\3.30.2\bin",
    "C:\Espressif\tools\openocd-esp32\v0.12.0-esp32-20251215\openocd-esp32\bin",
    "C:\Espressif\tools\ninja\1.12.1",
    "C:\Espressif\tools\idf-exe\1.0.3",
    "C:\Espressif\tools\ccache\4.12.1\ccache-4.12.1-windows-x86_64",
    "C:\Espressif\tools\dfu-util\0.11\dfu-util-0.11-win64",
    "C:\Espressif\python_env\idf5.5_py3.11_env\Scripts",
    "C:\Espressif\frameworks\esp-idf-v5.5.3\tools",
    "C:\Espressif\tools\idf-python\3.11.2",
    "C:\Espressif\tools\idf-git\2.44.0\cmd",
    "C:\Espressif"
)
$env:PATH = (($toolPaths + @($env:PATH)) -join ";")

Push-Location $projectRoot
try {
    $buildDir = Join-Path $projectRoot "build"
    $normalizedProject = [System.IO.Path]::GetFullPath($projectRoot)
    if (Test-Path $buildDir) {
        $cacheFiles = @(
            Join-Path $buildDir "CMakeCache.txt"
            Join-Path $buildDir "bootloader\\CMakeCache.txt"
        )

        foreach ($cmakeCache in $cacheFiles) {
            if (-not (Test-Path $cmakeCache)) {
                continue
            }

            $cacheSourceLine = Select-String -Path $cmakeCache -Pattern '^CMAKE_HOME_DIRECTORY:INTERNAL=' -ErrorAction SilentlyContinue | Select-Object -First 1
            if (-not $cacheSourceLine) {
                continue
            }

            $cachedSource = ($cacheSourceLine.Line -replace '^CMAKE_HOME_DIRECTORY:INTERNAL=', '').Trim()
            $normalizedCached = [System.IO.Path]::GetFullPath($cachedSource)
            if (-not [string]::Equals($normalizedCached, $normalizedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
                Write-Host "Detected stale build cache from another source tree. Removing build directory..." -ForegroundColor Yellow
                Remove-Item $buildDir -Recurse -Force
                break
            }
        }
    }

    $sdkconfigFile = Join-Path $projectRoot "sdkconfig.bridge.touch"
    if (Test-Path $sdkconfigFile) {
        Remove-Item $sdkconfigFile -Force
    }

    $baseArgs = @(
        "$env:IDF_PATH\tools\idf.py",
        "-DSDKCONFIG=sdkconfig.bridge.touch",
        "-DSDKCONFIG_DEFAULTS=$sdkconfigDefaults"
    )

    & $idfPython @baseArgs reconfigure build
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if ($Port) {
        if ($EraseFlash) {
            & $idfPython @baseArgs -p $Port erase-flash
            if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
            }
        }

        & $idfPython @baseArgs -p $Port flash
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}
finally {
    Pop-Location
}
