# Phase 6 — configure or build upstream Zelda64Recomp from this repo's root layout.
# Upstream lib/Zelda64Recomp/CMakeLists.txt uses CMAKE_SOURCE_DIR for lib/rt64,
# RecompiledFuncs/, etc.; the engine source root must be lib/Zelda64Recomp (see lib/README.txt).
#
# For a full MSVC link on Windows (recommended over Ninja+MinGW here), use tools/phase6_engine_cmake_vs2022.ps1
# (separate build-engine-vs2022/ tree). See lib/README.txt.
#
# Alternative: repo-root CMakeLists.txt + CMakePresets.json (ExternalProject_Add) — same inner
# SOURCE_DIR; outer build dir build-root/ (see Docs/Workflow.md § Phase 6).
#
# Before configure: run tools/phase6_link_recompiledfuncs.ps1 so engine CMake globs see
# repo-root RecompiledFuncs/ (N64Recomp TOML output_func_path is ../RecompiledFuncs from config/).
# Without -NoMmRom: upstream configure still needs Majora's Mask recomp steps (N64Recomp/RSPRecomp, rsp/*.cpp) per lib/Zelda64Recomp/BUILDING.md.
# With -NoMmRom: run python3 tools/phase6_materialize_no_mm_engine_files.py (or make phase6-materialize-stubs) first, then pass -DAEROASSAULT64_NO_MM_ROM=ON (see lib/README.txt).
# -AfaProduct: pass -DAEROASSAULT64_AFA_PRODUCT=ON (stub PatchesLib/RSP; still materialize RecompiledPatches headers first).
# -CiStub: run tools/phase6_ci_ensure_recompiledfuncs_stub.ps1 when RecompiledFuncs has no .c (matches CI / fresh clone).
param(
    [ValidateSet('Configure', 'Build', 'All')]
    [string]$Mode = 'Configure',
    [string]$Generator = 'Ninja',
    [string]$BuildType = 'Release',
    [switch]$NoMmRom,
    [switch]$CiStub,
    [switch]$AfaProduct
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineSource = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$BuildDir = Join-Path $RepoRoot 'build-engine'
if (-not (Test-Path (Join-Path $EngineSource 'CMakeLists.txt'))) {
    Write-Error 'Missing engine tree. From repo root run: git submodule update --init --recursive'
}
if ($CiStub) {
    & (Join-Path $PSScriptRoot 'phase6_ci_ensure_recompiledfuncs_stub.ps1')
}
$NoMmArgs = @()
if ($NoMmRom) {
    $NoMmArgs += '-DAEROASSAULT64_NO_MM_ROM=ON'
}
if ($AfaProduct) {
    $NoMmArgs += '-DAEROASSAULT64_AFA_PRODUCT=ON'
}

switch ($Mode) {
    'Configure' {
        cmake -S $EngineSource -B $BuildDir -G $Generator "-DCMAKE_BUILD_TYPE=$BuildType" @NoMmArgs
    }
    'Build' {
        cmake --build $BuildDir --config $BuildType
    }
    'All' {
        cmake -S $EngineSource -B $BuildDir -G $Generator "-DCMAKE_BUILD_TYPE=$BuildType" @NoMmArgs
        cmake --build $BuildDir --config $BuildType
    }
}
