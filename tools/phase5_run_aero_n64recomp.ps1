# Phase 5 — run N64Recomp on Aero Fighters Assault TOML (repo root).
#
# Prereq: WSL `make` / `make strict-verify` so build/aerofighters_assault.elf exists (same path as
# config/aerofighters_assault.n64recomp.toml [input].elf_path relative to config/).
#
# Why: stabilizes the AFA CPU recomp step (execution order item 1) without assuming WSL interop for the PE.
param(
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Elf = Join-Path $RepoRoot 'build\aerofighters_assault.elf'
$Toml = Join-Path $RepoRoot 'config\aerofighters_assault.n64recomp.toml'
$Exe = Join-Path $RepoRoot 'tools\N64Recomp.exe'

if (-not (Test-Path -LiteralPath $Exe)) {
    Write-Error "Missing $Exe"
}
if (-not (Test-Path -LiteralPath $Toml)) {
    Write-Error "Missing $Toml"
}
if (-not (Test-Path -LiteralPath $Elf)) {
    Write-Error @"
Missing ELF: $Elf
Build from WSL (see Makefile, Docs/Workflow.md Phase 4): make strict-verify or at least make until the ELF exists.
"@
}

if ($WhatIf) {
    Write-Host "WhatIf: would run $Exe $Toml"
    exit 0
}

Push-Location $RepoRoot
try {
    & $Exe $Toml
    if ($LASTEXITCODE -ne 0) {
        Write-Error "N64Recomp exited $LASTEXITCODE"
    }
    Write-Host 'OK: AFA N64Recomp finished (output under RecompiledFuncs/ per TOML).'
}
finally {
    Pop-Location
}
