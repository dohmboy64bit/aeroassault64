# Phase 6 — AFA USA: **CPU N64Recomp** + **RSP RSPRecomp** in one run (static outputs for engine link).
#
# This is the repo-side **full static recomp** for game MIPS + microcode blobs. It does **not** run the
# **PatchesLib** pipeline (`patches/patches.elf` + `patches.toml` + `./N64Recomp patches.toml`) — that
# still needs AFA patch objects + `Zelda64RecompSyms` for the AFA ELF (see `lib/Zelda64Recomp/AFA_PORT.md`
# §2 and `config/afa_engine/README.txt`).
#
# Prereqs:
#   - WSL: `make strict-verify` so `build/aerofighters_assault.elf` exists (same as `config/aerofighters_assault.n64recomp.toml`).
#   - `tools/N64Recomp.exe` and `tools/RSPRecomp.exe` (or pass `-CopyTools` so RSP step can copy into engine).
#   - `lib/Zelda64Recomp/aspMain.afa.us.toml` + `njpgdspMain.afa.us.toml` + `afa.n64.us.z64` at engine root (or `-RomPath`).
#
# Upstream analog: `BUILDING.md` §3–4 (MM `N64Recomp.exe` + `RSPRecomp.exe` from engine root).
#
param(
    [switch]$WhatIf,
    [switch]$SkipJunction,
    [switch]$SkipN64Recomp,
    [switch]$SkipRSP,
    [switch]$CopyTools,
    [string]$RomPath = ''
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Link = Join-Path $PSScriptRoot 'phase6_link_recompiledfuncs.ps1'
$N64 = Join-Path $PSScriptRoot 'phase5_run_aero_n64recomp.ps1'
$Rsp = Join-Path $PSScriptRoot 'phase6_rsprecomp_afa.ps1'

function Invoke-Step {
    param([string]$Title, [scriptblock]$Block)
    Write-Host ''
    Write-Host "=== $Title ===" -ForegroundColor Cyan
    & $Block
}

if ($WhatIf) {
    Write-Host @"
WhatIf: phase6_full_recomp_afa.ps1 would:
  1. $(if ($SkipJunction) { 'SKIP' } else { 'Run' }) tools/phase6_link_recompiledfuncs.ps1
  2. $(if ($SkipN64Recomp) { 'SKIP' } else { 'Run' }) tools/phase5_run_aero_n64recomp.ps1 (N64Recomp -> repo-root RecompiledFuncs/)
  3. $(if ($SkipRSP) { 'SKIP' } else { 'Run' }) tools/phase6_rsprecomp_afa.ps1 $(if ($CopyTools) { '-CopyTools ' })$(if ($RomPath) { "-RomPath $RomPath" })
Then: see lib/Zelda64Recomp/AFA_PORT.md section 2 for PatchesLib (patches.elf + patches.toml + -DAEROASSAULT64_AFA_RETAIL_PIPELINES).
"@
    exit 0
}

if (-not $SkipJunction) {
    Invoke-Step 'RecompiledFuncs junction' { & $Link }
}

if (-not $SkipN64Recomp) {
    Invoke-Step 'AFA CPU static recomp (N64Recomp)' { & $N64 }
}

if (-not $SkipRSP) {
    $rspArgs = @()
    if ($RomPath) { $rspArgs += '-RomPath', $RomPath }
    if ($CopyTools) { $rspArgs += '-CopyTools' }
    Invoke-Step 'AFA RSP microcode (RSPRecomp)' { & $Rsp @rspArgs }
}

Write-Host ''
Write-Host 'OK: AFA full static recomp (CPU + RSP) finished.' -ForegroundColor Green
Write-Host @'

Next for a full engine link with real PatchesLib (not stubs):
  - Build lib/Zelda64Recomp/patches/patches.elf from AFA MIPS patch sources (see upstream patches/Makefile).
  - Add Zelda64RecompSyms/*.toml for the AFA ELF (replace mm.us.rev1.* placeholders in config/afa_engine/patches.toml.template).
  - Copy patches.toml.template -> lib/Zelda64Recomp/patches.toml and edit paths; from engine root run: .\N64Recomp.exe patches.toml
  - Configure with -DAEROASSAULT64_AFA_PRODUCT=ON -DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON (tools/phase6_engine_cmake*.ps1 or CMakePresets engine-superbuild-*-afa-product-retail).

See: lib/Zelda64Recomp/AFA_PORT.md sections 1-2, config/afa_engine/README.txt, Docs/Workflow.md Phase 6.
'@
