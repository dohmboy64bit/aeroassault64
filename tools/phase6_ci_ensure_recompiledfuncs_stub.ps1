# Phase 6 — CI / fresh clone: CMake requires at least one RecompiledFuncs/*.c (see lib/Zelda64Recomp/CMakeLists.txt add_library RecompiledFuncs).
# On GitHub Actions the repo-root RecompiledFuncs/ has no generated .c (gitignored); this writes a minimal TU so configure succeeds.
# Local dev: if N64Recomp output is already present, this script is a no-op.
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Rf = Join-Path $RepoRoot 'RecompiledFuncs'
if (-not (Test-Path -LiteralPath $Rf)) {
    New-Item -ItemType Directory -Path $Rf -Force | Out-Null
}
$existing = @(Get-ChildItem -LiteralPath $Rf -Filter '*.c' -File -ErrorAction SilentlyContinue)
if ($existing.Count -gt 0) {
    Write-Host "RecompiledFuncs has $($existing.Count) .c file(s); skipping CI stub."
    exit 0
}
$stub = Join-Path $Rf 'funcs_ci_stub.c'
$body = @'
#include <stdint.h>
typedef struct { uint64_t gpr[32]; } recomp_context;
void recomp_rom_main(uint8_t* rdram, recomp_context* ctx) { (void)rdram; (void)ctx; }
'@
Set-Content -LiteralPath $stub -Value $body -Encoding ascii -NoNewline
Write-Host "Wrote CI stub: $stub"
