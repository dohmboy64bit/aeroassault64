#!/usr/bin/env python3
"""Copy stub RecompiledPatches headers into lib/Zelda64Recomp/RecompiledPatches/.

Same files as tools/phase6_materialize_no_mm_engine_files.ps1 — required before
engine configure with -DAEROASSAULT64_NO_MM_ROM=ON or -DAEROASSAULT64_AFA_PRODUCT=ON
because lib/Zelda64Recomp/src/main/register_patches.cpp includes:
  ../../RecompiledPatches/patches_bin.h
  ../../RecompiledPatches/recomp_overlays.inl
(funcs.h is part of the stub set used by the engine tree.)

Upstream: lib/Zelda64Recomp/CMakeLists.txt (AEROASSAULT64_NO_MM_ROM / AFA_PRODUCT).

Run from repo root:
  python3 tools/phase6_materialize_no_mm_engine_files.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "phase6_no_mm_engine"
DST = ROOT / "lib" / "Zelda64Recomp" / "RecompiledPatches"
NAMES = ("patches_bin.h", "recomp_overlays.inl", "funcs.h")


def main() -> int:
    for name in NAMES:
        src = SRC / name
        if not src.is_file():
            print(f"error: missing source file: {src}", file=sys.stderr)
            return 1
    DST.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        shutil.copy2(SRC / name, DST / name)
    print(f"Installed no-MM stub headers into {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
