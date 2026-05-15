#!/usr/bin/env python3
"""
Correct VRAM in N64Recomp data_dump / afa.n64.us.datasyms.toml after --dump-context.

Splat's AFA ELF maps many 0x8025xxxx symbols into a relocated 0x809F99xx / 0x80A0xx band.
Symbol names still encode retail VRAM (D_802516D8, func_80231150, …). This script rewrites
vram fields from those names and config/symbol_addrs.txt.

See lib/Zelda64Recomp/AFA_PORT.md and asm/ + config/symbol_addrs.txt.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SYMBOL_LINE = re.compile(
    r"^(\s*\{\s*name\s*=\s*\"([^\"]+)\"\s*,\s*vram\s*=\s*)(0x[0-9A-Fa-f]+)(\s*\},?\s*)$"
)

# D_802516D8, func_80231150, jtbl_80341F80, .L80280640.NON_MATCHING
VRAM_SUFFIX = re.compile(
    r"^(?:D|func|jtbl)_(802[0-9A-F]{5})(?:\.NON_MATCHING)?$"
)
DOT_LABEL = re.compile(r"^\.L(802[0-9A-F]{5})(?:\.NON_MATCHING)?$")

# Game segment (not KSEG0 0x80xxxx libultra IO symbols named D_80000300).
GAME_RAM_LO = 0x80200000
GAME_RAM_HI = 0x80800000

SPECIAL_VRAM: dict[str, int] = {
    # asm/1000.s entry clears from main_BSS_START; reloc_addrs.txt HI16/LO16.
    "main_BSS_START": 0x80256D70,
    "main_BSS_START.NON_MATCHING": 0x80256D70,
    "entrypoint": 0x80200050,
    "entrypoint.NON_MATCHING": 0x80200050,
    "main": 0x80231150,
    "main.NON_MATCHING": 0x80231150,
    "recomp_entrypoint": 0x80200050,
    "recomp_rom_main": 0x80231150,
}


def load_symbol_addrs(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip()
        val = val.strip().rstrip(";")
        if val.lower().startswith("0x"):
            out[name] = int(val, 16)
    return out


def vram_from_name(name: str, symbol_addrs: dict[str, int]) -> int | None:
    base = name.removesuffix(".NON_MATCHING")
    if name in SPECIAL_VRAM:
        return SPECIAL_VRAM[name]
    if base in SPECIAL_VRAM:
        return SPECIAL_VRAM[base]
    if base in symbol_addrs:
        return symbol_addrs[base]

    m = VRAM_SUFFIX.match(name)
    if m:
        return int(m.group(1), 16)
    m = DOT_LABEL.match(name)
    if m:
        return int(m.group(1), 16)
    return None


def fix_file(path: Path, symbol_addrs: dict[str, int], dry_run: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changed = 0
    scanned = 0

    for i, line in enumerate(lines):
        m = SYMBOL_LINE.match(line.rstrip("\n\r"))
        if not m:
            continue
        scanned += 1
        name = m.group(2)
        old_vram = int(m.group(3), 16)
        new_vram = vram_from_name(name, symbol_addrs)
        if new_vram is None:
            continue
        if not (GAME_RAM_LO <= new_vram < GAME_RAM_HI):
            continue
        if old_vram == new_vram:
            continue
        changed += 1
        if not dry_run:
            lines[i] = f"{m.group(1)}0x{new_vram:08X}{m.group(4)}\n"

    if not dry_run and changed:
        path.write_text("".join(lines), encoding="utf-8", newline="\n")
    return scanned, changed


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="datasyms.toml files (default: engine Zelda64RecompSyms/afa.n64.us.datasyms*.toml)",
    )
    parser.add_argument(
        "--symbol-addrs",
        type=Path,
        default=repo / "config" / "symbol_addrs.txt",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    paths = args.paths
    if not paths:
        syms = repo / "lib" / "Zelda64Recomp" / "Zelda64RecompSyms"
        paths = [
            syms / "afa.n64.us.datasyms.toml",
            syms / "afa.n64.us.datasyms_static.toml",
        ]

    symbol_addrs = load_symbol_addrs(args.symbol_addrs)
    total_changed = 0
    for path in paths:
        if not path.is_file():
            print(f"skip missing: {path}", file=sys.stderr)
            continue
        scanned, changed = fix_file(path, symbol_addrs, args.dry_run)
        total_changed += changed
        verb = "would fix" if args.dry_run else "fixed"
        print(f"{verb} {changed}/{scanned} symbol lines in {path}")

    return 0 if total_changed or args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
