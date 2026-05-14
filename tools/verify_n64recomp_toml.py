#!/usr/bin/env python3
"""Validate config/aerofighters_assault.n64recomp.toml (parse + N64Recomp rules).

Rules mirror N64Recomp src/config.cpp + src/main.cpp @ 81213c1831fab2521a6a5459c67b63437d67e253
(see tools/README.txt): [input] requires output_func_path; elf_path and symbols_file_path
are mutually exclusive; one of elf vs symbols mode must be selected.

Optional: entrypoint must match config/symbol_addrs.txt `entrypoint = 0x...`.

Run from repo root: python3 tools/verify_n64recomp_toml.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOML_PATH = ROOT / "config" / "aerofighters_assault.n64recomp.toml"
SYMS_PATH = ROOT / "config" / "symbol_addrs.txt"


def main() -> int:
    try:
        import tomllib
    except ImportError:
        print("Python 3.11+ required (stdlib tomllib)", file=sys.stderr)
        return 1

    if not TOML_PATH.is_file():
        print(f"missing {TOML_PATH}", file=sys.stderr)
        return 1

    data = tomllib.loads(TOML_PATH.read_text(encoding="utf-8"))
    inp = data.get("input")
    if not isinstance(inp, dict):
        print("missing [input] table", file=sys.stderr)
        return 1

    if not inp.get("output_func_path"):
        print("input.output_func_path is required (N64Recomp src/config.cpp)", file=sys.stderr)
        return 1

    elf = (inp.get("elf_path") or "").strip()
    syms = (inp.get("symbols_file_path") or "").strip()
    if elf and syms:
        print("elf_path and symbols_file_path both set — N64Recomp src/main.cpp rejects this", file=sys.stderr)
        return 1
    if not elf and not syms:
        print("must set either elf_path or symbols_file_path", file=sys.stderr)
        return 1

    ep = inp.get("entrypoint")
    if ep is not None and SYMS_PATH.is_file():
        m = re.search(r"^entrypoint\s*=\s*(0x[0-9A-Fa-f]+)\s*;", SYMS_PATH.read_text(encoding="utf-8"), re.M)
        if m:
            expected = int(m.group(1), 16)
            if int(ep) != expected:
                print(
                    f"entrypoint 0x{int(ep):08X} != symbol_addrs entrypoint 0x{expected:08X}",
                    file=sys.stderr,
                )
                return 1

    print(f"OK: {TOML_PATH.relative_to(ROOT)} ([input] valid for N64Recomp ELF mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
