#!/usr/bin/env python3
"""When lib/Zelda64Recomp exists, ensure RecompiledFuncs/ is one tree (engine vs repo root).

Upstream Zelda64Recomp/CMakeLists.txt globs:
  ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c
  ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.cpp
This repo's N64Recomp TOML uses output_func_path = "../RecompiledFuncs" from config/, i.e.
repo-root RecompiledFuncs/ (see tools/README.txt, lib/README.txt).

If both paths exist, they must be the same directory (junction on Windows, symlink on Unix).
If lib/Zelda64Recomp is absent (e.g. CI without submodules), exit 0.

When the engine checkout exists, also notes (stdout, still exit 0) if **N64Recomp.exe** is
missing under **lib/Zelda64Recomp/** — optional **tools/phase6_copy_n64recomp_to_engine.ps1**
per **lib/Zelda64Recomp/BUILDING.md** § 4.

If **lib/Zelda64Recomp/RecompiledPatches/patches_bin.h** (and sibling stub headers from
**tools/phase6_materialize_no_mm_engine_files.ps1**) are missing, prints an informational
note — engine configure with **-NoMmRom** or **-AfaProduct** needs those files for
**src/main/register_patches.cpp** includes; still exit 0.

Run from repo root: python3 tools/verify_phase6_layout.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_CMAKE = ROOT / "lib" / "Zelda64Recomp" / "CMakeLists.txt"
ENGINE_ROOT = ROOT / "lib" / "Zelda64Recomp"
ROOT_RF = ROOT / "RecompiledFuncs"
ENG_RF = ENGINE_ROOT / "RecompiledFuncs"
ENG_RP = ENGINE_ROOT / "RecompiledPatches"
ENG_N64 = ENGINE_ROOT / "N64Recomp.exe"
ENG_RSP = ENGINE_ROOT / "RSPRecomp.exe"
STUB_HEADERS = ("patches_bin.h", "recomp_overlays.inl", "funcs.h")


def _stub_headers_note() -> str:
    """register_patches.cpp includes RecompiledPatches/*.h — materialize before stub CMake."""
    missing = [n for n in STUB_HEADERS if not (ENG_RP / n).is_file()]
    if not missing:
        return ""
    return (
        "; RecompiledPatches stub headers missing ("
        + ", ".join(missing)
        + ") — run tools/phase6_materialize_no_mm_engine_files.ps1 or `make phase6-materialize-stubs` "
        "before engine configure with -NoMmRom/-AfaProduct (lib/Zelda64Recomp/src/main/register_patches.cpp)"
    )


def _engine_pe_note() -> str:
    if not ENGINE_CMAKE.is_file():
        return ""
    n64 = ENG_N64.is_file()
    rsp = ENG_RSP.is_file()
    if n64 and rsp:
        return ""
    if not n64 and not rsp:
        return "; N64Recomp.exe and RSPRecomp.exe missing in engine root (optional: tools/phase6_copy_n64recomp_to_engine.ps1)"
    if not n64:
        return "; N64Recomp.exe missing in engine root (optional: tools/phase6_copy_n64recomp_to_engine.ps1)"
    return "; RSPRecomp.exe missing in engine root (optional: tools/phase6_copy_n64recomp_to_engine.ps1)"


def main() -> int:
    if not ENGINE_CMAKE.is_file():
        print("OK: phase6 layout (no lib/Zelda64Recomp — submodule not checked out)")
        return 0

    if not ENG_RF.exists():
        print(
            "OK: phase6 layout (engine checkout present; RecompiledFuncs bridge not created — optional)"
            + _engine_pe_note()
            + _stub_headers_note(),
        )
        return 0

    if not ROOT_RF.exists():
        print(f"error: {ENG_RF} exists but repo-root {ROOT_RF} does not", file=sys.stderr)
        return 1

    try:
        if os.path.samefile(ROOT_RF, ENG_RF):
            print(
                "OK: phase6 layout (RecompiledFuncs bridge points at repo root)"
                + _engine_pe_note()
                + _stub_headers_note(),
            )
            return 0
    except OSError as e:
        print(f"error: could not compare paths: {e}", file=sys.stderr)
        return 1

    print(
        f"error: {ROOT_RF} and {ENG_RF} are different directories. "
        "Remove the stray tree and use tools/phase6_link_recompiledfuncs.ps1 (Windows) "
        "or: ln -s ../../RecompiledFuncs lib/Zelda64Recomp/RecompiledFuncs",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
