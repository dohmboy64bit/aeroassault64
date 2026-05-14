# Phase 6 — run N64Recomp in lib/Zelda64Recomp/ for Majora's Mask (us.rev1.toml -> RecompiledFuncs/*.c).
#
# Upstream lib/Zelda64Recomp/BUILDING.md section 4: from the engine root, ./N64Recomp us.rev1.toml after the
# decompressed ROM is present (us.rev1.toml has rom_file_path = "mm.us.rev1.rom_uncompressed.z64").
# Run before tools/phase6_rsprecomp_engine.ps1 when following BUILDING.md in order.
#
# Prereqs: tools/N64Recomp.exe; run tools/phase6_copy_n64recomp_to_engine.ps1 or -CopyTools.
param(
    [switch]$CopyTools,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$ToolsN64 = Join-Path $RepoRoot 'tools\N64Recomp.exe'
$EngineN64 = Join-Path $EngineRoot 'N64Recomp.exe'
$Rom = Join-Path $EngineRoot 'mm.us.rev1.rom_uncompressed.z64'
$Toml = Join-Path $EngineRoot 'us.rev1.toml'

if (-not (Test-Path (Join-Path $EngineRoot 'CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp. From repo root run: git submodule update --init --recursive'
}
if ($WhatIf) {
    Write-Host "WhatIf: would run N64Recomp.exe in $EngineRoot with us.rev1.toml."
    Write-Host "WhatIf: ROM path $Rom (exists: $(Test-Path -LiteralPath $Rom))."
    exit 0
}
if (-not (Test-Path -LiteralPath $Toml)) {
    Write-Error "Missing $Toml"
}
if (-not (Test-Path -LiteralPath $Rom)) {
    Write-Error @"
Missing decompressed MM ROM at:
  $Rom
Per lib/Zelda64Recomp/BUILDING.md section 3, place mm.us.rev1.rom_uncompressed.z64 in the engine root before N64Recomp.
"@
}

if ($CopyTools -or -not (Test-Path -LiteralPath $EngineN64)) {
    if (-not (Test-Path -LiteralPath $ToolsN64)) {
        Write-Error "Missing $ToolsN64 — build N64Recomp per tools/README.txt or copy the PE to the engine root."
    }
    & (Join-Path $PSScriptRoot 'phase6_copy_n64recomp_to_engine.ps1')
}

Push-Location $EngineRoot
try {
    Write-Host "N64Recomp us.rev1.toml (cwd=$EngineRoot)"
    & .\N64Recomp.exe us.rev1.toml
    if ($LASTEXITCODE -ne 0) {
        Write-Error "N64Recomp failed (exit $LASTEXITCODE)"
    }
    Write-Host 'OK: MM CPU recomp finished (see RecompiledFuncs/ under engine root or junction to repo root).'
}
finally {
    Pop-Location
}
