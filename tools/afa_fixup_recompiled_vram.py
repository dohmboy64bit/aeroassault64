#!/usr/bin/env python3
"""
Rewrite wrong 0x80A0/0x809F99xx lui+offset sequences in RecompiledFuncs/*.c.

N64Recomp emits immediates from ELF machine words; datasyms.toml fix alone does not
change those. This pass maps relocated addresses back to retail 0x8025xxxx using the
same +0x7A82E0 slab rule (game 0x80251680.. vs ELF 0x809F9960..).

See asm/ and lib/Zelda64Recomp/AFA_PORT.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECOMPILED = REPO / "RecompiledFuncs"

# Game 0x80251680.. band emitted as 0x809F9960.. in ELF (see AFA_PORT.md).
WRONG_SLAB_BASE = 0x809F9960
WRONG_SLAB_END = 0x809FA200
SLAB_DELTA = 0x7A82E0  # 0x809F9960 - 0x80251680 (asm D_80251774 %hi/%lo)

LUI_LINE = re.compile(
    r"^(\s*ctx->r(\d+) = S32\(0X([0-9A-F]+) << 16\);)\s*(?://.*)?$"
)
MEM_OFFSET_REG = re.compile(
    r"^(\s*)ctx->r(\d+) = (MEM_[WHU]+)\((-?0X[0-9A-F]+), ctx->r(\d+)\)(.*)$"
)
MEM_REG_OFFSET = re.compile(
    r"^(\s*)ctx->r(\d+) = (MEM_[WHU]+)\(ctx->r\2, (-?0X[0-9A-F]+)\)(.*)$"
)
ADDIU_AFTER_LUI = re.compile(
    r"^(\s*ctx->r(\d+) = ADD32\(ctx->r\2, (-?0X[0-9A-F]+)\);)\s*(?://.*)?$"
)


def wrong_to_correct(addr: int) -> int | None:
    if WRONG_SLAB_BASE <= addr < WRONG_SLAB_END:
        return addr - SLAB_DELTA
    # entry BSS / stack (see asm/1000.s)
    if addr == 0x809FF050:
        return 0x80256D70
    if addr == 0x80276E90:
        return 0x80282B60
    return None


def split_mips_addr(addr: int) -> tuple[int, int]:
    """Return (hi16_unsigned, lo16_signed) for MIPS o32 address formation."""
    lo = addr & 0xFFFF
    hi = (addr >> 16) & 0xFFFF
    if lo >= 0x8000:
        hi = (hi + 1) & 0xFFFF
    return hi, lo if lo < 0x8000 else lo - 0x10000


def fix_file(path: Path, dry_run: bool) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    i = 0
    while i < len(lines):
        m = LUI_LINE.match(lines[i])
        if not m:
            i += 1
            continue
        reg = m.group(2)
        hi_val = int(m.group(3), 16)
        # Look ahead for MEM_ or ADD32 that completes the address.
        for j in range(i + 1, min(i + 48, len(lines))):
            mm = MEM_REG_OFFSET.match(lines[j])
            if mm and mm.group(2) == reg:
                off = int(mm.group(4), 16)
                wrong = (hi_val << 16) + off
                correct = wrong_to_correct(wrong)
                if correct is None:
                    break
                new_hi, new_lo = split_mips_addr(correct)
                if not dry_run:
                    lines[i] = f"    ctx->r{reg} = S32(0X{new_hi:X} << 16);"
                    lo_abs = new_lo if new_lo >= 0 else (new_lo + 0x10000)
                    lines[j] = (
                        f"{mm.group(1)}ctx->r{reg} = {mm.group(3)}(ctx->r{reg}, 0X{lo_abs:X}){mm.group(5)}"
                    )
                changed += 1
                break
            mm = MEM_OFFSET_REG.match(lines[j])
            if mm and mm.group(2) == reg and mm.group(5) == reg:
                off = int(mm.group(4), 16)
                wrong = (hi_val << 16) + off
                correct = wrong_to_correct(wrong)
                if correct is None:
                    break
                new_hi, new_lo = split_mips_addr(correct)
                if not dry_run:
                    lines[i] = f"    ctx->r{reg} = S32(0X{new_hi:X} << 16);"
                    lo_abs = new_lo if new_lo >= 0 else (new_lo + 0x10000)
                    lines[j] = (
                        f"{mm.group(1)}ctx->r{reg} = {mm.group(3)}(0X{lo_abs:X}, ctx->r{reg}){mm.group(5)}"
                    )
                changed += 1
                break
            am = ADDIU_AFTER_LUI.match(lines[j])
            if am and am.group(2) == reg:
                off = int(am.group(3), 16)
                wrong = (hi_val << 16) + off
                correct = wrong_to_correct(wrong)
                if correct is None:
                    break
                new_hi, new_lo = split_mips_addr(correct)
                if not dry_run:
                    lines[i] = f"    ctx->r{reg} = S32(0X{new_hi:X} << 16);"
                    lo_disp = new_lo if new_lo >= 0 else new_lo
                    lines[j] = f"    ctx->r{reg} = ADD32(ctx->r{reg}, 0X{lo_disp & 0xFFFF:X});"
                changed += 1
                break
        i += 1

    if changed and not dry_run:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--funcs-dir",
        type=Path,
        default=RECOMPILED,
    )
    args = parser.parse_args()
    total = 0
    for path in sorted(args.funcs_dir.glob("funcs_*.c")):
        n = fix_file(path, args.dry_run)
        if n:
            verb = "would fix" if args.dry_run else "fixed"
            print(f"{verb} {n} lui/mem pairs in {path.name}")
            total += n
    print(f"total: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
