#!/usr/bin/env python3
"""Ensure config/splat.yaml basename / elf_path agree with root Makefile ELF name.

Avoid drift where splat emits aerofighters_assault.ld but Makefile still points at
another basename after a rename.

Run from repo root: python3 tools/verify_splat_makefile_sync.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLAT = ROOT / "config" / "splat.yaml"
MAKEFILE = ROOT / "Makefile"


def main() -> int:
    if not SPLAT.is_file() or not MAKEFILE.is_file():
        print("missing config/splat.yaml or Makefile", file=sys.stderr)
        return 1

    st = SPLAT.read_text(encoding="utf-8")
    m_base = re.search(r"^\s*basename:\s*(\S+)\s*$", st, re.M)
    m_elf = re.search(r"^\s*elf_path:\s*build/(\S+)\.elf\s*$", st, re.M)
    if not m_base or not m_elf:
        print("could not parse basename / elf_path from splat.yaml", file=sys.stderr)
        return 1
    base = m_base.group(1)
    yaml_stem = m_elf.group(1)
    if base != yaml_stem:
        print(f"splat.yaml basename {base!r} != elf_path stem {yaml_stem!r}", file=sys.stderr)
        return 1

    mk = MAKEFILE.read_text(encoding="utf-8")
    m_mk = re.search(r"^ELF[ \t]*:=[ \t]*build/(\S+)\.elf\s*$", mk, re.M)
    if not m_mk:
        print("could not parse ELF := from Makefile", file=sys.stderr)
        return 1
    mk_stem = m_mk.group(1)
    if mk_stem != base:
        print(f"Makefile ELF stem {mk_stem!r} != splat basename {base!r}", file=sys.stderr)
        return 1

    if f"build/{base}.ld" not in mk:
        print(f"Makefile should reference build/{base}.ld", file=sys.stderr)
        return 1

    print(f"OK: splat basename / elf_path / Makefile ELF agree ({base})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
