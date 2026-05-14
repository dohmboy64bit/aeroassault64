# Phase 6 — configure or build upstream Zelda64Recomp from this repo's root layout.
# Upstream lib/Zelda64Recomp/CMakeLists.txt uses CMAKE_SOURCE_DIR for lib/rt64,
# RecompiledFuncs/, etc.; the engine source root must be lib/Zelda64Recomp (see lib/README.txt).
param(
    [ValidateSet('Configure', 'Build', 'All')]
    [string]$Mode = 'Configure',
    [string]$Generator = 'Ninja',
    [string]$BuildType = 'Release'
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineSource = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$BuildDir = Join-Path $RepoRoot 'build-engine'
if (-not (Test-Path (Join-Path $EngineSource 'CMakeLists.txt'))) {
    Write-Error "Missing engine tree at $EngineSource. From repo root run: git submodule update --init --recursive"
}
switch ($Mode) {
    'Configure' {
        cmake -S $EngineSource -B $BuildDir -G $Generator "-DCMAKE_BUILD_TYPE=$BuildType"
    }
    'Build' {
        cmake --build $BuildDir --config $BuildType
    }
    'All' {
        cmake -S $EngineSource -B $BuildDir -G $Generator "-DCMAKE_BUILD_TYPE=$BuildType"
        cmake --build $BuildDir --config $BuildType
    }
}
