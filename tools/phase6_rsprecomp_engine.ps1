# Phase 6 — run RSPRecomp in lib/Zelda64Recomp/ to emit rsp/aspMain.cpp and rsp/njpgdspMain.cpp.
#
# Upstream lib/Zelda64Recomp/BUILDING.md §4: from the engine root, ./RSPRecomp aspMain.us.rev1.toml and
# ./RSPRecomp njpgdspMain.us.rev1.toml after the decompressed MM ROM is present (aspMain.us.rev1.toml /
# njpgdspMain.us.rev1.toml reference rom_file_path = "mm.us.rev1.rom_uncompressed.z64").
#
# Prereqs: tools/RSPRecomp.exe (see tools/README.txt); run tools/phase6_copy_n64recomp_to_engine.ps1 so
# RSPRecomp.exe exists in the engine root, or pass -CopyTools to copy automatically.
param(
    [switch]$CopyTools,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$ToolsRsp = Join-Path $RepoRoot 'tools\RSPRecomp.exe'
$EngineRsp = Join-Path $EngineRoot 'RSPRecomp.exe'
$Rom = Join-Path $EngineRoot 'mm.us.rev1.rom_uncompressed.z64'
$TomlAsp = Join-Path $EngineRoot 'aspMain.us.rev1.toml'
$TomlNjpg = Join-Path $EngineRoot 'njpgdspMain.us.rev1.toml'

if (-not (Test-Path (Join-Path $EngineRoot 'CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp. From repo root run: git submodule update --init --recursive'
}
if ($WhatIf) {
    Write-Host "WhatIf: would run RSPRecomp.exe in $EngineRoot for aspMain.us.rev1.toml and njpgdspMain.us.rev1.toml."
    Write-Host "WhatIf: ROM path checked at $Rom (exists: $(Test-Path -LiteralPath $Rom))."
    exit 0
}
if (-not (Test-Path -LiteralPath $TomlAsp) -or -not (Test-Path -LiteralPath $TomlNjpg)) {
    Write-Error "Missing RSP TOMLs under $EngineRoot (expected aspMain.us.rev1.toml and njpgdspMain.us.rev1.toml)."
}
if (-not (Test-Path -LiteralPath $Rom)) {
    Write-Error @"
Missing decompressed MM ROM at:
  $Rom
Per lib/Zelda64Recomp/BUILDING.md §3, place mm.us.rev1.rom_uncompressed.z64 in the engine root before RSPRecomp.
"@
}

if ($CopyTools -or -not (Test-Path -LiteralPath $EngineRsp)) {
    if (-not (Test-Path -LiteralPath $ToolsRsp)) {
        Write-Error "Missing $ToolsRsp — build RSPRecomp per tools/README.txt or run without -CopyTools after copying the PE to the engine root."
    }
    & (Join-Path $PSScriptRoot 'phase6_copy_n64recomp_to_engine.ps1')
}

Push-Location $EngineRoot
try {
    foreach ($pair in @(
            @{ Toml = 'aspMain.us.rev1.toml'; Out = 'rsp\aspMain.cpp' },
            @{ Toml = 'njpgdspMain.us.rev1.toml'; Out = 'rsp\njpgdspMain.cpp' }
        )) {
        $argToml = $pair.Toml
        $outPath = Join-Path $EngineRoot $pair.Out
        Write-Host "RSPRecomp $argToml -> $outPath"
        & .\RSPRecomp.exe $argToml
        if ($LASTEXITCODE -ne 0) {
            Write-Error "RSPRecomp failed (exit $LASTEXITCODE) for $argToml"
        }
        if (-not (Test-Path -LiteralPath $outPath)) {
            Write-Error "RSPRecomp did not create $outPath"
        }
    }
    Write-Host 'RSP outputs OK: rsp/aspMain.cpp, rsp/njpgdspMain.cpp'
}
finally {
    Pop-Location
}
