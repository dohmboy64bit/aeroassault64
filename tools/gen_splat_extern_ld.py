#!/usr/bin/env python3
"""
Emit GNU ld assignment lines for splat-style labels whose VRAM is encoded in the name
(func_<hex>, D_<hex>, jtbl_<hex>, .L<hex>). Feeds build/splat_extern.ld for Phase 4.

splat.yaml `undefined_*_auto_path` guides splat/spimdisasm during split; GNU ld still needs
symbols for unresolved relocs. `mips-linux-gnu-nm -u` omits some UND globals (e.g. names
starting with `.`); we parse `mips-linux-gnu-readelf -s` instead (see binutils readelf(1)).

Labels in ``asm/data/57D20.bss.s`` are intentionally not linked as a separate object in this repo
(see root ``Makefile``): that VRAM range is already occupied by ``post_data.o(.text)`` in splat's script,
so ``D_*`` / ``.L*`` relocs stay ``UND`` here and receive absolute assignments from this script.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

FUNC_RE = re.compile(r"^func_([0-9A-Fa-f]{1,16})$", re.I)
D_RE = re.compile(r"^D_([0-9A-Fa-f]{1,16})$", re.I)
JTBL_RE = re.compile(r"^jtbl_([0-9A-Fa-f]{1,16})$", re.I)
DOTL_RE = re.compile(r"^\.L([0-9A-Fa-f]{1,16})$", re.I)


def readelf_symbols(obj: str) -> tuple[set[str], set[str]]:
    """Return (undefined_names, defined_names) from .symtab.

    Lines look like ``9: 00000000   124 OBJECT  GLOBAL DEFAULT    1 name`` — see
    ``mips-linux-gnu-readelf -s`` (binutils): Value, Size, Type, Bind, Vis, Ndx, Name.
    """
    try:
        out = subprocess.check_output(
            ["mips-linux-gnu-readelf", "-W", "-s", obj],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"gen_splat_extern_ld: readelf failed for {obj}: {e}", file=sys.stderr)
        return set(), set()
    undefined: set[str] = set()
    defined: set[str] = set()
    for line in out.splitlines():
        s = line.strip()
        if not s or not s[0].isdigit():
            continue
        if ":" not in s:
            continue
        _num, rest = s.split(":", 1)
        parts = rest.split()
        if len(parts) < 7:
            continue
        ndx = parts[5]
        name = parts[6] if len(parts) == 7 else " ".join(parts[6:])
        if not name or name.startswith("@"):
            continue
        if ndx == "UND":
            undefined.add(name)
        else:
            defined.add(name)
    return undefined, defined


def assignment_for(name: str) -> str | None:
    m = FUNC_RE.match(name) or D_RE.match(name) or JTBL_RE.match(name) or DOTL_RE.match(name)
    if not m:
        return None
    addr = int(m.group(1), 16)
    return f"{name} = 0x{addr:X};"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--extras",
        type=argparse.FileType("r", encoding="utf-8"),
        help="Optional fragment of ld assignments (already in ld syntax)",
    )
    ap.add_argument("objects", nargs="+", help=".o files from mips-linux-gnu-as")
    args = ap.parse_args()

    seen: set[str] = set()
    lines: list[str] = []

    if args.extras:
        for raw in args.extras:
            line = raw.rstrip()
            if not line or line.startswith("/*") or line.startswith("//"):
                continue
            lines.append(line)
            if "=" in line:
                sym = line.split("=", 1)[0].strip()
                seen.add(sym)

    all_undef: set[str] = set()
    all_defined: set[str] = set()
    for obj in args.objects:
        u, d = readelf_symbols(obj)
        all_undef |= u
        all_defined |= d

    for name in sorted(all_undef):
        if name in all_defined:
            continue
        a = assignment_for(name)
        if a and name not in seen:
            seen.add(name)
            lines.append(a)

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
