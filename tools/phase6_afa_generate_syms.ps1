# Generate Zelda64RecompSyms for AFA from build/aerofighters_assault.elf (N64Recomp --dump-context).
# See config/afa_engine/README.txt and lib/Zelda64Recomp/AFA_PORT.md section 2.
param(
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Elf = Join-Path $RepoRoot 'build\aerofighters_assault.elf'
$DumpToml = Join-Path $RepoRoot 'config\afa_engine\dump_syms.toml'
$N64 = Join-Path $RepoRoot 'tools\N64Recomp.exe'
$SymsDir = Join-Path $RepoRoot 'lib\Zelda64Recomp\Zelda64RecompSyms'
$OutFunc = Join-Path $SymsDir 'afa.n64.us.syms.toml'
$OutData = Join-Path $SymsDir 'afa.n64.us.datasyms.toml'
$OutDataStatic = Join-Path $SymsDir 'afa.n64.us.datasyms_static.toml'

if (-not (Test-Path -LiteralPath $DumpToml)) {
    Write-Error "Missing $DumpToml"
}
if (-not (Test-Path -LiteralPath $Elf)) {
    Write-Error @"
Missing $Elf
Build from WSL: make strict-verify (see Makefile, Docs/Workflow.md Phase 4).
"@
}
if (-not (Test-Path -LiteralPath $N64)) {
    Write-Error "Missing $N64"
}

if ($WhatIf) {
    Write-Host "WhatIf: $N64 $DumpToml --dump-context -> dump.toml + data_dump.toml"
    Write-Host "WhatIf: install -> $OutFunc , $OutData , $OutDataStatic"
    exit 0
}

Push-Location $RepoRoot
try {
    Write-Host "N64Recomp --dump-context (AFA ELF symbols)..."
    & $N64 $DumpToml '--dump-context'
    if ($LASTEXITCODE -ne 0) {
        Write-Error "N64Recomp --dump-context failed (exit $LASTEXITCODE)"
    }
    foreach ($name in @('dump.toml', 'data_dump.toml')) {
        if (-not (Test-Path -LiteralPath $name)) {
            Write-Error "Expected $RepoRoot\$name after --dump-context"
        }
    }
    New-Item -ItemType Directory -Force -Path $SymsDir | Out-Null
    Move-Item -LiteralPath (Join-Path $RepoRoot 'dump.toml') -Destination $OutFunc -Force
  # Patches pipeline expects datasyms + datasyms_static; ELF dump is a single data file — split is optional later.
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'data_dump.toml') -Destination $OutData -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'data_dump.toml') -Destination $OutDataStatic -Force
    Remove-Item -LiteralPath (Join-Path $RepoRoot 'data_dump.toml') -Force -ErrorAction SilentlyContinue
    $funcLines = (Get-Content -LiteralPath $OutFunc | Measure-Object -Line).Lines
    Write-Host "OK: $OutFunc ($funcLines lines)"
    Write-Host "OK: $OutData (copy also at $OutDataStatic)"
}
finally {
    Pop-Location
}
