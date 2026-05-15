# Phase 6 — run RSPRecomp in lib/Zelda64Recomp/ to emit rsp/aspMain.cpp and rsp/njpgdspMain.cpp for AFA USA.
#
# Same flow as tools/phase6_rsprecomp_engine.ps1 (MM), but TOMLs are aspMain.afa.us.toml /
# njpgdspMain.afa.us.toml at the engine root and ROM defaults to afa.n64.us.z64 (see
# lib/Zelda64Recomp/AFA_PORT.md section 1 and config/afa_rsp/README.txt).
#
# Upstream TOML schema (keys): same as upstream aspMain.us.rev1.toml / njpgdspMain.us.rev1.toml —
# https://raw.githubusercontent.com/Mr-Wiseguy/Zelda64Recomp/master/aspMain.us.rev1.toml
# https://raw.githubusercontent.com/Mr-Wiseguy/Zelda64Recomp/master/njpgdspMain.us.rev1.toml
#
# Prereqs: tools/RSPRecomp.exe; run tools/phase6_copy_n64recomp_to_engine.ps1 so RSPRecomp.exe exists
# in the engine root, or pass -CopyTools.
param(
    [string]$RomPath = '',
    [switch]$CopyTools,
    [switch]$SkipOffsetGuard,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$ToolsRsp = Join-Path $RepoRoot 'tools\RSPRecomp.exe'
$EngineRsp = Join-Path $EngineRoot 'RSPRecomp.exe'
$TomlAsp = Join-Path $EngineRoot 'aspMain.afa.us.toml'
$TomlNjpg = Join-Path $EngineRoot 'njpgdspMain.afa.us.toml'
$Rom = if ($RomPath) { $RomPath } else { Join-Path $EngineRoot 'afa.n64.us.z64' }

if (-not (Test-Path (Join-Path $EngineRoot 'CMakeLists.txt'))) {
    Write-Error 'Missing lib/Zelda64Recomp. From repo root run: git submodule update --init --recursive'
}
if ($WhatIf) {
    Write-Host "WhatIf: would run RSPRecomp.exe in $EngineRoot for aspMain.afa.us.toml and njpgdspMain.afa.us.toml."
    Write-Host "WhatIf: ROM path checked at $Rom (exists: $(Test-Path -LiteralPath $Rom))."
    exit 0
}
if (-not (Test-Path -LiteralPath $TomlAsp) -or -not (Test-Path -LiteralPath $TomlNjpg)) {
    Write-Error @"
Missing AFA RSP TOMLs under engine root:
  $TomlAsp
  $TomlNjpg
Copy and fill ../../config/afa_rsp/*.template.toml -> engine root (see lib/Zelda64Recomp/AFA_PORT.md section 1).
"@
}
if (-not $SkipOffsetGuard) {
    foreach ($p in @($TomlAsp, $TomlNjpg)) {
        $raw = Get-Content -LiteralPath $p -Raw
        if ($raw -match 'text_offset\s*=\s*0x0\b' -or $raw -match 'text_size\s*=\s*0x0\b') {
            Write-Error @"
TOML still has placeholder text_offset or text_size (0x0): $p
Fill values from ROM analysis (Ghidra + splat), or pass -SkipOffsetGuard if you intentionally use different placeholders.
"@
        }
    }
}
if (-not (Test-Path -LiteralPath $Rom)) {
    Write-Error @"
Missing ROM at:
  $Rom
Place the byteswapped USA z64 at that path or pass -RomPath <full-path>. rom_file_path in each TOML must match how you run RSPRecomp (paths are relative to engine root when cwd is engine root).
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
            @{ Toml = 'aspMain.afa.us.toml'; Out = 'rsp\aspMain.cpp' },
            @{ Toml = 'njpgdspMain.afa.us.toml'; Out = 'rsp\njpgdspMain.cpp' }
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
    $patchPy = Join-Path $RepoRoot 'tools\rsprecomp_patch_rsp_cpp.py'
    if (Test-Path -LiteralPath $patchPy) {
        Write-Host 'Patching rsp/*.cpp for MSVC (missing labels, addiu $zero)...'
        & python $patchPy
        if ($LASTEXITCODE -ne 0) {
            Write-Error "rsprecomp_patch_rsp_cpp.py failed (exit $LASTEXITCODE)"
        }
    }
}
finally {
    Pop-Location
}
