#!/usr/bin/env python3
"""When lib/Zelda64Recomp exists, ensure RecompiledFuncs/ is one tree (engine vs repo root).

Upstream Zelda64Recomp/CMakeLists.txt globs:
  ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c
  ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.cpp
This repo's N64Recomp TOML uses output_func_path = "../RecompiledFuncs" from config/, i.e.
repo-root RecompiledFuncs/ (see tools/README.txt, lib/README.txt).

If both paths exist, they must be the same directory (junction on Windows, symlink on Unix).
If lib/Zelda64Recomp is absent (e.g. CI without submodules), exit 0.

Run from repo root: python3 tools/verify_phase6_layout.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_CMAKE = ROOT / "lib" / "Zelda64Recomp" / "CMakeLists.txt"
ROOT_RF = ROOT / "RecompiledFuncs"
ENG_RF = ROOT / "lib" / "Zelda64Recomp" / "RecompiledFuncs"


def main() -> int:
    if not ENGINE_CMAKE.is_file():
        print("OK: phase6 layout (no lib/Zelda64Recomp — submodule not checked out)")
        return 0

    if not ENG_RF.exists():
        print(
            "OK: phase6 layout (engine checkout present; RecompiledFuncs bridge not created — optional)",
        )
        return 0

    if not ROOT_RF.exists():
        print(f"error: {ENG_RF} exists but repo-root {ROOT_RF} does not", file=sys.stderr)
        return 1

    try:
        if os.path.samefile(ROOT_RF, ENG_RF):
            print("OK: phase6 layout (RecompiledFuncs bridge points at repo root)")
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
