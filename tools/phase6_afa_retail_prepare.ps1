# Phase 6 — prepare engine tree for AEROASSAULT64_AFA_RETAIL_PIPELINES (PatchesLib / N64Recomp patches.toml).
#
# Does NOT build AFA-specific MIPS patches (still MM sources under lib/Zelda64Recomp/patches/).
# Use this to materialize RecompiledPatches headers, install patches.toml from template, and
# optionally build upstream MM patches.elf when clang + ld.lld are on PATH (bring-up only).
#
# See config/afa_engine/README.txt and lib/Zelda64Recomp/AFA_PORT.md section 2.
param(
    [switch]$GenerateAfaSyms,
    [switch]$BuildMmPatchesElf,
    [switch]$RunN64RecompPatches,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Engine = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$TemplateToml = Join-Path $RepoRoot 'config\afa_engine\patches.toml.template'
$EngineToml = Join-Path $Engine 'patches.toml'
$PatchesElf = Join-Path $Engine 'patches\patches.elf'
$PatchesC = Join-Path $Engine 'RecompiledPatches\patches.c'

if (-not (Test-Path (Join-Path $Engine 'CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp submodule.'
}

if ($WhatIf) {
    Write-Host "WhatIf: materialize RecompiledPatches stubs; copy $TemplateToml -> $EngineToml"
    if ($GenerateAfaSyms) { Write-Host 'WhatIf: phase6_afa_generate_syms.ps1' }
    if ($BuildMmPatchesElf) { Write-Host 'WhatIf: make patches.elf in engine patches/' }
    if ($RunN64RecompPatches) { Write-Host 'WhatIf: N64Recomp.exe patches.toml from engine root' }
    exit 0
}

if ($GenerateAfaSyms) {
    & (Join-Path $RepoRoot 'tools\phase6_afa_generate_syms.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& python (Join-Path $RepoRoot 'tools\phase6_materialize_no_mm_engine_files.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# UI assets (launcher.rml, fonts) are tracked in the engine submodule but may be absent on sparse checkouts.
$assetsLauncher = Join-Path $Engine 'assets\launcher.rml'
if (-not (Test-Path -LiteralPath $assetsLauncher)) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        Write-Host 'Restoring lib/Zelda64Recomp/assets/ from submodule (git checkout HEAD -- assets)...'
        Push-Location $Engine
        try {
            & git checkout HEAD -- assets
            if ($LASTEXITCODE -ne 0) { Write-Warning "git checkout assets failed (exit $LASTEXITCODE)" }
        } finally { Pop-Location }
    } else {
        Write-Warning "Missing $assetsLauncher and git not on PATH."
    }
}

if (-not (Test-Path -LiteralPath $TemplateToml)) {
    Write-Error "Missing $TemplateToml"
}
Copy-Item -LiteralPath $TemplateToml -Destination $EngineToml -Force
$afaSyms = Join-Path $Engine 'Zelda64RecompSyms\afa.n64.us.syms.toml'
if (-not (Test-Path -LiteralPath $afaSyms)) {
    Write-Warning "Missing $afaSyms — run: pwsh tools/phase6_afa_generate_syms.ps1 (needs build/aerofighters_assault.elf)"
}
Write-Host "Installed patches.toml (AFA syms paths — patches.elf must still be AFA MIPS objects, not MM)."

if ($BuildMmPatchesElf) {
    $built = $false
    $make = Get-Command make -ErrorAction SilentlyContinue
    $clang = Get-Command clang -ErrorAction SilentlyContinue
    if ($make -and $clang) {
        Push-Location (Join-Path $Engine 'patches')
        try {
            Write-Host 'Building patches/patches.elf (AFA_PATCHES=1, host clang)...'
            & make AFA_PATCHES=1
            if ($LASTEXITCODE -eq 0) { $built = $true }
        } finally { Pop-Location }
    }
    if (-not $built -and (Get-Command wsl -ErrorAction SilentlyContinue)) {
        Write-Host 'Trying WSL: CC=clang LD=ld.lld make in lib/Zelda64Recomp/patches/...'
        $wslCmd = 'export CC=clang LD=ld.lld; cd /mnt/e/AeroAssault64/lib/Zelda64Recomp/patches && make AFA_PATCHES=1'
        wsl -e bash -lc $wslCmd
        if ($LASTEXITCODE -eq 0) { $built = $true }
    }
    if (-not $built) {
        Write-Warning 'patches.elf not built. Install LLVM (clang+lld) on PATH or use WSL with clang and ld.lld.'
    }
}

if ($RunN64RecompPatches) {
    Write-Warning 'N64Recomp patches.toml overwrites RecompiledPatches/*.h with MM patch tables. For AFA bring-up (stub PatchesLib), run python tools/phase6_materialize_no_mm_engine_files.py after retail experiments.'
    if (-not (Test-Path -LiteralPath $PatchesElf)) {
        Write-Warning @"
Missing $PatchesElf — N64Recomp patches.toml skipped.
Build with MIPS clang + ld.lld (upstream lib/Zelda64Recomp/patches/Makefile), e.g. WSL:
  sudo apt install clang lld
  cd lib/Zelda64Recomp/patches && make
Then re-run: .\tools\phase6_afa_retail_prepare.ps1 -RunN64RecompPatches
"@
        return
    }
    $n64 = Join-Path $Engine 'N64Recomp.exe'
    if (-not (Test-Path -LiteralPath $n64)) {
        & (Join-Path $PSScriptRoot 'phase6_copy_n64recomp_to_engine.ps1')
    }
    Push-Location $Engine
    try {
        Write-Host 'N64Recomp patches.toml -> RecompiledPatches/'
        & .\N64Recomp.exe patches.toml
        if ($LASTEXITCODE -ne 0) { Write-Error "N64Recomp patches.toml failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}

if (Test-Path -LiteralPath (Join-Path $Engine 'patches\patches.bin')) {
    $patchesBinC = Join-Path $Engine 'RecompiledPatches\patches_bin.c'
    if (-not (Test-Path -LiteralPath $patchesBinC)) {
        $ftc = Join-Path $RepoRoot 'build-engine-vs2022\Release\file_to_c.exe'
        if (-not (Test-Path -LiteralPath $ftc)) {
            $ftc = Join-Path $RepoRoot 'build-engine-vs2022-retail\Release\file_to_c.exe'
        }
        if (Test-Path -LiteralPath $ftc) {
            Write-Host "file_to_c patches.bin -> RecompiledPatches/patches_bin.c"
            Push-Location $Engine
            try {
                & $ftc 'patches\patches.bin' 'mm_patches_bin' 'RecompiledPatches\patches_bin.c' 'RecompiledPatches\patches_bin.h'
            } finally { Pop-Location }
        } else {
            Write-Warning 'patches_bin.c missing; build file_to_c target once (phase6_engine_cmake_vs2022.ps1 -Mode Build) then re-run -RunN64RecompPatches.'
        }
    }
}

Write-Host 'Retail prepare done.'
Write-Host "  patches.toml: $EngineToml"
Write-Host "  patches.elf:  $(if (Test-Path $PatchesElf) { 'present' } else { 'MISSING (retail CMake will run make on configure)' })"
Write-Host "  patches.c:    $(if (Test-Path $PatchesC) { 'present' } else { 'missing until N64Recomp patches.toml' })"
Write-Host 'Configure: -DAEROASSAULT64_AFA_PRODUCT=ON -DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON (and AFA_RSP_FORCE_STUBS=OFF when rsp/*.cpp is patched).'
