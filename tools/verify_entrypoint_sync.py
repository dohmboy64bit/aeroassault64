#!/usr/bin/env python3
"""Ensure entry VRAM is consistent: splat `entry` segment, symbol_addrs, N64Recomp TOML.

Game entry is 0x80200050 per config/symbol_addrs.txt (`entrypoint`), config/splat.yaml
(`segments` / `entry` / `vram`), and config/aerofighters_assault.n64recomp.toml (`entrypoint`).

Run from repo root: python3 tools/verify_entrypoint_sync.py
Requires Python 3.11+ (tomllib) for the TOML read.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLAT = ROOT / "config" / "splat.yaml"
SYMS = ROOT / "config" / "symbol_addrs.txt"
TOML = ROOT / "config" / "aerofighters_assault.n64recomp.toml"


def entry_vram_from_splat(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if re.match(r"^\s*-\s*name:\s*entry\s*$", line):
            for j in range(i + 1, min(i + 20, len(lines))):
                m = re.match(r"^\s*vram:\s*(0x[0-9A-Fa-f]+)\s*$", lines[j])
                if m:
                    return int(m.group(1), 16)
            return None
    return None


def main() -> int:
    try:
        import tomllib
    except ImportError:
        print("Python 3.11+ required (tomllib)", file=sys.stderr)
        return 1

    if not all(p.is_file() for p in (SPLAT, SYMS, TOML)):
        print("missing config/splat.yaml, symbol_addrs.txt, or aerofighters_assault.n64recomp.toml", file=sys.stderr)
        return 1

    splat_lines = SPLAT.read_text(encoding="utf-8").splitlines()
    v_splat = entry_vram_from_splat(splat_lines)
    if v_splat is None:
        print("could not find entry segment vram in config/splat.yaml", file=sys.stderr)
        return 1

    m = re.search(r"^entrypoint\s*=\s*(0x[0-9A-Fa-f]+)\s*;", SYMS.read_text(encoding="utf-8"), re.M)
    if not m:
        print("could not parse entrypoint in config/symbol_addrs.txt", file=sys.stderr)
        return 1
    v_sym = int(m.group(1), 16)

    data = tomllib.loads(TOML.read_text(encoding="utf-8"))
    inp = data.get("input") or {}
    ep = inp.get("entrypoint")
    if ep is None:
        print("missing [input] entrypoint in N64Recomp TOML", file=sys.stderr)
        return 1
    v_toml = int(ep)

    if v_splat != v_sym or v_sym != v_toml:
        print(
            f"entrypoint mismatch: splat entry vram 0x{v_splat:08X}, "
            f"symbol_addrs 0x{v_sym:08X}, n64recomp TOML 0x{v_toml:08X}",
            file=sys.stderr,
        )
        return 1

    print(f"OK: entry VRAM 0x{v_splat:08X} (splat entry / symbol_addrs / N64Recomp TOML)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
