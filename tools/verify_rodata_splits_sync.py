#!/usr/bin/env python3
"""Fail if Ghidra Phase3 RODATA_ROM_SPLITS drifts from config/splat.yaml rodata starts.

Phase3_Closeout_Report.py documents: RODATA_ROM_SPLITS must match splat `main` rodata
subsegment ROM starts. This script compares the two sources (stdlib only).

Run from repo root: python3 tools/verify_rodata_splits_sync.py
Exit 0 if lists match; exit 1 with a diff hint otherwise.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLAT = ROOT / "config" / "splat.yaml"
PHASE3 = ROOT / "tools" / "ghidra" / "Phase3_Closeout_Report.py"


def rodata_starts_from_splat(text: str) -> list[int]:
    return [int(m.group(1), 16) for m in re.finditer(r"-\s*\[(0x[0-9A-Fa-f]+),\s*rodata\]", text)]


def rodata_tuple_from_phase3(path: Path) -> tuple[int, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "RODATA_ROM_SPLITS":
                    return ast.literal_eval(node.value)
    raise SystemExit(f"RODATA_ROM_SPLITS not found in {path}")


def main() -> int:
    if not SPLAT.is_file():
        print(f"missing {SPLAT}", file=sys.stderr)
        return 1
    if not PHASE3.is_file():
        print(f"missing {PHASE3}", file=sys.stderr)
        return 1

    splat_text = SPLAT.read_text(encoding="utf-8")
    yaml_list = rodata_starts_from_splat(splat_text)
    py_tuple = rodata_tuple_from_phase3(PHASE3)
    py_list = list(py_tuple)

    if yaml_list == py_list:
        print(f"OK: {len(py_list)} rodata split ROM offsets match ({PHASE3.name} <-> {SPLAT.name})")
        return 0

    print("Mismatch: splat.yaml rodata starts vs Phase3_Closeout_Report.RODATA_ROM_SPLITS", file=sys.stderr)
    print(f"  splat ({len(yaml_list)}): {yaml_list!r}", file=sys.stderr)
    print(f"  phase3 ({len(py_list)}): {py_list!r}", file=sys.stderr)
    print("  Update RODATA_ROM_SPLITS in tools/ghidra/Phase3_Closeout_Report.py to match splat.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
