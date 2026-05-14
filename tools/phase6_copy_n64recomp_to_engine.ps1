# Phase 6 — copy vendored N64Recomp / RSPRecomp into lib/Zelda64Recomp/ (upstream BUILDING.md § 4).
#
# Upstream lib/Zelda64Recomp/BUILDING.md: build N64Recomp + RSPRecomp, then "copy to the root
# of the Zelda64Recomp repository" before ./N64Recomp us.rev1.toml and ./RSPRecomp *.toml.
# This repo already tracks tools/N64Recomp.exe and tools/RSPRecomp.exe (see tools/README.txt).
#
# Does not run the recompilers or satisfy MM ROM / TOML steps — only places the PEs where
# BUILDING.md expects them for manual or CMake-driven runs from the engine root.
param(
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$SrcN64 = Join-Path $RepoRoot 'tools\N64Recomp.exe'
$SrcRsp = Join-Path $RepoRoot 'tools\RSPRecomp.exe'
$DstN64 = Join-Path $EngineRoot 'N64Recomp.exe'
$DstRsp = Join-Path $EngineRoot 'RSPRecomp.exe'

if (-not (Test-Path (Join-Path $EngineRoot 'CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp. From repo root run: git submodule update --init --recursive'
}
if (-not (Test-Path -LiteralPath $SrcN64)) {
    Write-Error "Missing $SrcN64"
}
if (-not (Test-Path -LiteralPath $SrcRsp)) {
    Write-Error "Missing $SrcRsp"
}

if ($WhatIf) {
    Write-Host "WhatIf: would copy to $DstN64 and $DstRsp"
    exit 0
}

Copy-Item -LiteralPath $SrcN64 -Destination $DstN64 -Force
Copy-Item -LiteralPath $SrcRsp -Destination $DstRsp -Force
Write-Host "Copied N64Recomp.exe and RSPRecomp.exe to $EngineRoot"
