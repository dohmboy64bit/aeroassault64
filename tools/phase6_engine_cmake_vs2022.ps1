# Phase 6 — configure or build Zelda64Recomp with Visual Studio 2022 (MSVC), separate from Ninja/MinGW.
#
# Why: lib/Zelda64Recomp/CMakeLists.txt pulls MSVC-oriented SDL2 (VC zip), freetype.lib, and DXC paths;
# a full Zelda64Recompiled.exe link on Windows is expected to use this toolchain (see lib/README.txt).
#
# Binary directory: build-engine-vs2022/ (gitignored) — do not reuse build-engine/ (Ninja + different generator).
#
# Prereqs: Visual Studio 2022 with "Desktop development with C++"; CMake on PATH; from repo root run
#   .\tools\phase6_link_recompiledfuncs.ps1
# No-MM:   python3 tools/phase6_materialize_no_mm_engine_files.py  then  -NoMmRom
# AFA product: stub PatchesLib/RSP without MM patches pipeline — same materialize then -AfaProduct (see lib/Zelda64Recomp/CMakeLists.txt).
# With -AfaProduct -AfaRetailPipelines: real patches.elf + patches.toml PatchesLib (see lib/Zelda64Recomp/AFA_PORT.md).
# With -AfaProduct -AfaRspForceStubs: link RSP stubs even if rsp/*.cpp exist (MSVC when RSPRecomp output not yet clean).
# Optional fork: -AfaRomXxh3Hex <16 hex digits> and/or -ExeOutputName AeroAssault64 (see lib/Zelda64Recomp/CMakeLists.txt).
# CI parity: -CiStub runs tools/phase6_ci_ensure_recompiledfuncs_stub.ps1 when RecompiledFuncs has no .c (same as .github/workflows/engine-windows.yml).
param(
    [ValidateSet('Configure', 'Build', 'All')]
    [string]$Mode = 'Configure',
    [ValidateSet('Debug', 'Release', 'RelWithDebInfo', 'MinSizeRel')]
    [string]$Configuration = 'Release',
    [string]$Target = 'Zelda64Recompiled',
    [switch]$NoMmRom,
    [switch]$CiStub,
    [switch]$AfaProduct,
    [switch]$AfaRetailPipelines,
    [switch]$AfaRspForceStubs,
    [string]$AfaRomXxh3Hex = '',
    [string]$ExeOutputName = '',
    [string]$VersionTag = '',
    [string]$WindowTitle = ''
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineSource = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$BuildDir = Join-Path $RepoRoot 'build-engine-vs2022'

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
if ($AfaRetailPipelines) {
    if (-not $AfaProduct) {
        Write-Warning '-AfaRetailPipelines is intended with -AfaProduct; forwarding -DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON anyway (engine may warn).'
    }
    $NoMmArgs += '-DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON'
}
if ($AfaRspForceStubs) {
    $NoMmArgs += '-DAEROASSAULT64_AFA_RSP_FORCE_STUBS=ON'
}
if ($AfaRomXxh3Hex) {
    $NoMmArgs += "-DAEROASSAULT64_AFA_ROM_XXH3_HEX=$AfaRomXxh3Hex"
}
if ($ExeOutputName) {
    $NoMmArgs += "-DAEROASSAULT64_EXE_OUTPUT_NAME=$ExeOutputName"
}
if ($VersionTag) {
    $NoMmArgs += "-DAEROASSAULT64_VERSION_TAG=$VersionTag"
}
if ($WindowTitle) {
    $NoMmArgs += "-DAEROASSAULT64_WINDOW_TITLE=$WindowTitle"
}

switch ($Mode) {
    'Configure' {
        cmake -S $EngineSource -B $BuildDir -G 'Visual Studio 17 2022' -A x64 @NoMmArgs
    }
    'Build' {
        cmake --build $BuildDir --config $Configuration --target $Target
    }
    'All' {
        cmake -S $EngineSource -B $BuildDir -G 'Visual Studio 17 2022' -A x64 @NoMmArgs
        cmake --build $BuildDir --config $Configuration --target $Target
    }
}
