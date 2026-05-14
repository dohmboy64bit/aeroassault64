# Phase 6 — one-shot Windows prep after submodule init (optional convenience).
# Runs: RecompiledFuncs junction -> copy N64Recomp/RSPRecomp into engine -> verify_phase6_layout.py
# Optional -RspRecomp: if lib/Zelda64Recomp/mm.us.rev1.rom_uncompressed.z64 exists, runs tools/phase6_rsprecomp_engine.ps1
# (BUILDING.md §4). Does not run CMake or ./N64Recomp us.rev1.toml — see lib/Zelda64Recomp/BUILDING.md.
param(
    [switch]$RspRecomp
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

& (Join-Path $PSScriptRoot 'phase6_link_recompiledfuncs.ps1')
& (Join-Path $PSScriptRoot 'phase6_copy_n64recomp_to_engine.ps1')

$engineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$mmRom = Join-Path $engineRoot 'mm.us.rev1.rom_uncompressed.z64'
if ($RspRecomp) {
    if (Test-Path -LiteralPath $mmRom) {
        & (Join-Path $PSScriptRoot 'phase6_rsprecomp_engine.ps1')
    } else {
        Write-Host "Skip -RspRecomp: missing $mmRom (BUILDING.md §3)."
    }
}

$python = $null
foreach ($name in @('python', 'python3')) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { $python = $c.Path; break }
}
if (-not $python) {
    Write-Error 'python or python3 not on PATH (needed for verify_phase6_layout.py)'
}
& $python (Join-Path $RepoRoot 'tools\verify_phase6_layout.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'OK: phase6_setup_windows (link + copy + layout verify)'
