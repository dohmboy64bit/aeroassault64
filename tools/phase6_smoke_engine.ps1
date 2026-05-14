# Phase 6 — launch built Zelda64Recompiled briefly (SDL) with engine cwd (matches VS_DEBUGGER_WORKING_DIRECTORY).
#
# Default: build-engine-vs2022/Release/Zelda64Recompiled.exe, cwd lib/Zelda64Recomp, stop after -Seconds if still running.
param(
    [string]$Configuration = 'Release',
    [string]$BuildDir = '',
    [int]$Seconds = 12
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
if (-not $BuildDir) {
    $BuildDir = Join-Path $RepoRoot 'build-engine-vs2022'
}
$Exe = Join-Path $BuildDir "$Configuration\Zelda64Recompiled.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Missing $Exe — build first (e.g. tools/phase6_engine_cmake_vs2022.ps1 -Mode All -NoMmRom)."
}
if (-not (Test-Path -LiteralPath (Join-Path $EngineRoot 'CMakeLists.txt'))) {
    Write-Error "Missing engine tree: $EngineRoot"
}

$p = Start-Process -FilePath $Exe -WorkingDirectory $EngineRoot -PassThru
$null = $p.WaitForExit([Math]::Max(0, $Seconds * 1000))
if (-not $p.HasExited) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Write-Host "SMOKE: still running after ${Seconds}s — process stopped (typical for SDL window)."
} else {
    $code = $p.ExitCode
    if ($null -eq $code) { $code = 'n/a' }
    Write-Host "SMOKE: exit code $code"
}
