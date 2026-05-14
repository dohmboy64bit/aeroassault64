# Phase 6 — configure or build upstream Zelda64Recomp from this repo's root layout.
# Upstream lib/Zelda64Recomp/CMakeLists.txt uses CMAKE_SOURCE_DIR for lib/rt64,
# RecompiledFuncs/, etc.; the engine source root must be lib/Zelda64Recomp (see lib/README.txt).
#
# Alternative: repo-root CMakeLists.txt + CMakePresets.json (ExternalProject_Add) — same inner
# SOURCE_DIR; outer build dir build-root/ (see Docs/Workflow.md § Phase 6).
#
# Before configure: run tools/phase6_link_recompiledfuncs.ps1 so engine CMake globs see
# repo-root RecompiledFuncs/ (N64Recomp TOML output_func_path is ../RecompiledFuncs from config/).
# Upstream configure still requires Majora's Mask recomp steps (N64Recomp/RSPRecomp, rsp/*.cpp) per lib/Zelda64Recomp/BUILDING.md.
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
    Write-Error 'Missing engine tree. From repo root run: git submodule update --init --recursive'
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
