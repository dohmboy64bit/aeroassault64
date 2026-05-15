# Run retail engine with boot log + console that stays open on crash/exit.
param(
    [string]$LogPath = '',
    [switch]$AutoStart,
    [switch]$NoBuild
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EngineRoot = Join-Path $RepoRoot 'lib\Zelda64Recomp'
$Exe = Join-Path $RepoRoot 'build-engine-vs2022-retail\Release\Zelda64Recompiled.exe'
if (-not $LogPath) {
    $LogPath = Join-Path $EngineRoot 'aero_boot.log'
}

if (-not $NoBuild) {
    cmake --build (Join-Path $RepoRoot 'build-engine-vs2022-retail') --config Release --target Zelda64Recompiled
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Missing $Exe"
}

$args = @('--show-console', '--boot-log', $LogPath, '--pause-on-exit')
if ($AutoStart) { $args += '--auto-start' }

Write-Host "Log: $LogPath"
Write-Host "Args: $($args -join ' ')"

& $Exe @args
$code = $LASTEXITCODE
Write-Host "Exit code: $code"
Write-Host "--- tail of log ---"
if (Test-Path -LiteralPath $LogPath) {
    Get-Content -LiteralPath $LogPath -Tail 80
}
exit $code
