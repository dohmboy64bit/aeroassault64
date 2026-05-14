# Phase 6 — bridge repo-root RecompiledFuncs/ into lib/Zelda64Recomp/RecompiledFuncs/
#
# Why: Zelda64Recomp/CMakeLists.txt globs:
#   file(GLOB FUNC_C_SOURCES ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c)
#   (same for *.cpp) — paths are under the engine tree, not the AeroAssault64 repo root.
# Our N64Recomp TOML (config/aerofighters_assault.n64recomp.toml) sets output_func_path = "../RecompiledFuncs"
# relative to config/, i.e. repo-root RecompiledFuncs/ (see tools/README.txt Phase 5).
#
# A directory junction (no admin on typical Windows setups) makes both layouts see the same files.
# Remove with: .\tools\phase6_link_recompiledfuncs.ps1 -Remove
#
# This does not satisfy upstream Majora's Mask RSP/main recomp steps — see lib/Zelda64Recomp/BUILDING.md.
param(
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRf = Join-Path $RepoRoot 'lib\Zelda64Recomp\RecompiledFuncs'
$RootRf = Join-Path $RepoRoot 'RecompiledFuncs'

if ($Remove) {
    if (-not (Test-Path -LiteralPath $EngineRf)) {
        Write-Host "Nothing to remove: $EngineRf"
        exit 0
    }
    $item = Get-Item -LiteralPath $EngineRf
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Remove-Item -LiteralPath $EngineRf
        Write-Host "Removed junction: $EngineRf"
    } else {
        Write-Error ('Refusing -Remove: {0} is not a junction/reparse point. Delete manually only if you are sure.' -f $EngineRf)
    }
    exit 0
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'lib\Zelda64Recomp\CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp. From repo root run: git submodule update --init --recursive'
}

if (-not (Test-Path -LiteralPath $RootRf)) {
    New-Item -ItemType Directory -Path $RootRf -Force | Out-Null
    Write-Host "Created directory: $RootRf"
}

if (Test-Path -LiteralPath $EngineRf) {
    $item = Get-Item -LiteralPath $EngineRf
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host ('Already a junction: {0} => {1}' -f $EngineRf, $RootRf)
        exit 0
    }
    Write-Error 'Path exists and is not a junction. Rename or remove it, or pass -Remove if it is an old junction.'
}

$parent = Split-Path -Parent $EngineRf
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

New-Item -ItemType Junction -Path $EngineRf -Target $RootRf | Out-Null
Write-Host ('Junction OK: {0} => {1}' -f $EngineRf, $RootRf)
