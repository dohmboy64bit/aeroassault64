# Copies stub RecompiledPatches headers/overlays into lib/Zelda64Recomp/RecompiledPatches/
# so src/main/register_patches.cpp can include ../../RecompiledPatches/patches_bin.h and
# recomp_overlays.inl when configuring with -DAEROASSAULT64_NO_MM_ROM=ON or -DAEROASSAULT64_AFA_PRODUCT=ON.
# Canonical implementation: tools/phase6_materialize_no_mm_engine_files.py (also used by Makefile target phase6-materialize-stubs).
# Source files live under tools/phase6_no_mm_engine/ (see that README.txt).
# Upstream: lib/Zelda64Recomp/CMakeLists.txt options AEROASSAULT64_NO_MM_ROM / AEROASSAULT64_AFA_PRODUCT.
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PyScript = Join-Path $PSScriptRoot 'phase6_materialize_no_mm_engine_files.py'
foreach ($PyExe in @('python', 'python3')) {
    $cmd = Get-Command $PyExe -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        & $cmd.Source $PyScript
        exit $LASTEXITCODE
    }
}
$Src = Join-Path $RepoRoot 'tools\phase6_no_mm_engine'
$Dst = Join-Path $RepoRoot 'lib\Zelda64Recomp\RecompiledPatches'
foreach ($name in @('patches_bin.h', 'recomp_overlays.inl', 'funcs.h')) {
    $f = Join-Path $Src $name
    if (-not (Test-Path $f)) { Write-Error "Missing source file: $f" }
}
New-Item -ItemType Directory -Force -Path $Dst | Out-Null
Copy-Item (Join-Path $Src 'patches_bin.h') (Join-Path $Dst 'patches_bin.h') -Force
Copy-Item (Join-Path $Src 'recomp_overlays.inl') (Join-Path $Dst 'recomp_overlays.inl') -Force
Copy-Item (Join-Path $Src 'funcs.h') (Join-Path $Dst 'funcs.h') -Force
Write-Host "Installed no-MM stub headers into $Dst (fallback copy; install Python to use $PyScript)"
