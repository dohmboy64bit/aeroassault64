# Phase 6 — one-shot Windows prep after submodule init (optional convenience).
# Runs: RecompiledFuncs junction -> copy N64Recomp/RSPRecomp into engine -> verify_phase6_layout.py
# Does not run CMake, N64Recomp on MM TOMLs, or RSPRecomp — see lib/Zelda64Recomp/BUILDING.md.
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

& (Join-Path $PSScriptRoot 'phase6_link_recompiledfuncs.ps1')
& (Join-Path $PSScriptRoot 'phase6_copy_n64recomp_to_engine.ps1')

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
