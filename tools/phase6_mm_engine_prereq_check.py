#!/usr/bin/env python3
"""Audit Majora's Mask engine build prerequisites (lib/Zelda64Recomp/BUILDING.md).

Checks paths and files referenced in BUILDING.md sections 3-4 and CMakeLists.txt expectations
(rsp/*.cpp, RecompiledPatches). Does not verify ROM SHA1 (legal/sourcing is manual).

Exit 0 always unless --strict is passed and any MM-required item is missing.

Run from repo root:
  python3 tools/phase6_mm_engine_prereq_check.py
  python3 tools/phase6_mm_engine_prereq_check.py --strict
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "lib" / "Zelda64Recomp"
ROM_NAME = "mm.us.rev1.rom_uncompressed.z64"


def _ok(p: Path) -> bool:
    return p.is_file() or p.is_dir()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any MM-required prerequisite is missing (submodule must exist)",
    )
    args = ap.parse_args()

    cmake = ENGINE / "CMakeLists.txt"
    if not cmake.is_file():
        print("SKIP: lib/Zelda64Recomp not present (git submodule update --init --recursive)")
        return 0

    rows: list[tuple[str, Path, bool, str]] = []
    # (label, path, required_for_mm, doc_ref)

    rom = ENGINE / ROM_NAME
    rows.append(
        (
            f"Decompressed MM ROM ({ROM_NAME})",
            rom,
            True,
            "lib/Zelda64Recomp/BUILDING.md section 3",
        ),
    )

    rows.append(("CPU recomp TOML", ENGINE / "us.rev1.toml", True, "BUILDING.md section 4"))
    rows.append(("Patches TOML", ENGINE / "patches.toml", True, "lib/Zelda64Recomp/CMakeLists.txt (N64Recomp patches.toml)"))
    rows.append(("RSP TOML aspMain", ENGINE / "aspMain.us.rev1.toml", True, "BUILDING.md section 4"))
    rows.append(("RSP TOML njpgdsp", ENGINE / "njpgdspMain.us.rev1.toml", True, "BUILDING.md section 4"))

    rows.append(("N64Recomp.exe in engine root", ENGINE / "N64Recomp.exe", True, "BUILDING.md section 4 + tools/phase6_copy_n64recomp_to_engine.ps1"))
    rows.append(("RSPRecomp.exe in engine root", ENGINE / "RSPRecomp.exe", True, "BUILDING.md section 4 + tools/phase6_copy_n64recomp_to_engine.ps1"))

    rows.append(("rsp/aspMain.cpp (generated)", ENGINE / "rsp" / "aspMain.cpp", True, "BUILDING.md section 4; rsp/.gitignore"))
    rows.append(("rsp/njpgdspMain.cpp (generated)", ENGINE / "rsp" / "njpgdspMain.cpp", True, "BUILDING.md section 4"))

    rows.append(("RecompiledPatches/patches.c", ENGINE / "RecompiledPatches" / "patches.c", True, "CMakeLists.txt custom commands + patches/"))
    rows.append(("RecompiledPatches/patches_bin.c", ENGINE / "RecompiledPatches" / "patches_bin.c", True, "CMakeLists.txt"))

    # RecompiledFuncs: at least one .c from MM us.rev1 run OR AFA bridge to repo root
    eng_rf = ENGINE / "RecompiledFuncs"
    root_rf = ROOT / "RecompiledFuncs"
    mm_funcs_ok = False
    if eng_rf.exists():
        mm_funcs_ok = any(eng_rf.glob("*.c")) or any(eng_rf.glob("*.cpp"))
    note_rf = "CMakeLists.txt file(GLOB RecompiledFuncs/*.c)"
    rows.append(("RecompiledFuncs/*.c (or .cpp)", eng_rf, True, note_rf))

    missing_required: list[str] = []

    print("Phase 6 - MM engine prerequisite audit (Zelda64Recomp / BUILDING.md)\n")
    for label, path, required, ref in rows:
        ok = _ok(path)
        if label.startswith("RecompiledFuncs"):
            ok = mm_funcs_ok
        status = "OK " if ok else "MISS"
        flag = "[required] " if required else ""
        print(f"  {status} {flag}{label}")
        print(f"         path: {path.relative_to(ROOT)}")
        print(f"         ref:  {ref}")
        if required and not ok:
            missing_required.append(label)

    # Bridge note (AFA smoke C may live only at repo root)
    try:
        import os

        bridged = eng_rf.exists() and root_rf.exists() and os.path.samefile(root_rf, eng_rf)
    except OSError:
        bridged = False
    print()
    if bridged:
        print("NOTE: lib/Zelda64Recomp/RecompiledFuncs is the same directory as repo-root RecompiledFuncs (junction/symlink).")
        print("      MM CPU recomp output still requires ./N64Recomp us.rev1.toml in the engine tree when doing stock MM.")
    elif eng_rf.exists() and not mm_funcs_ok:
        print("NOTE: RecompiledFuncs bridge exists but no *.c/*.cpp — run MM ./N64Recomp us.rev1.toml or AFA recomp as appropriate.")

    rsp_asp = ENGINE / "rsp" / "aspMain.cpp"
    rsp_njpg = ENGINE / "rsp" / "njpgdspMain.cpp"
    if not rsp_asp.is_file() or not rsp_njpg.is_file():
        print(
            "HINT: rsp/*.cpp missing — on Windows after BUILDING.md section 3 ROM is in lib/Zelda64Recomp/, run "
            "tools/phase6_rsprecomp_engine.ps1 (see tools/README.txt Phase 6)."
        )

    print()
    if not missing_required:
        print("Summary: all listed MM-required paths are present (or RecompiledFuncs populated).")
        return 0

    print("Summary: missing MM-required items:")
    for m in missing_required:
        print(f"  - {m}")
    if args.strict:
        return 1
    print("(exit 0; pass --strict to fail the process for CI/scripts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
