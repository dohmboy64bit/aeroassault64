# -*- coding: utf-8 -*-
"""MIPS32 big-endian disassembly at ROM file offset(s) using Python **Capstone** (host — no Ghidra).

Use to tell **MIPS** (e.g. **`asm/4BE20.s`** @ ROM **0x4BE20**) from RSP microcode blobs before trusting **`text_offset`**.

Examples::

  python tools/rsp_rom_capstone_mips.py --offset 0x4BE20 --count 6
  python tools/rsp_rom_capstone_mips.py --rom roms/afa.n64.us.z64 --offset 0x4DAB0 --dump-hex 32 --be-words 8
  python tools/rsp_rom_capstone_mips.py --afa-usa-hints
  python tools/rsp_rom_capstone_mips.py --offsets 0x4BE20,0x4DAB0,0x4C830 --count 4

Docs: **`lib/Zelda64Recomp/AFA_PORT.md`** §1; **`requirements.txt`** (**`pip install capstone`**). Same **CS_ARCH_MIPS** /
**`CS_MODE_MIPS32 | CS_MODE_BIG_ENDIAN`** as **`tools/ghidra/RSPRecomp_Confirm_Findings.py`** (Capstone project docs:
https://www.capstone-engine.org/lang_python.html — **MIPS** + **CS_MODE_BIG_ENDIAN**).
"""
from __future__ import print_function

import argparse
import os
import struct
import sys


def _default_rom_path(repo):
    for cand in (
        os.path.join(repo, "lib", "Zelda64Recomp", "afa.n64.us.z64"),
        os.path.join(repo, "roms", "afa.n64.us.z64"),
    ):
        if os.path.isfile(cand):
            return cand
    return None


def _disasm_block(md, rom_path, offset, count, dump_hex, be_words):
    """Print one offset block; **md** is **Cs** instance."""
    with open(rom_path, "rb") as f:
        f.seek(offset)
        data = f.read(max(4, int(count) * 4 + 4))

    print("ROM %s  file_offset 0x%X  MIPS32 BE (Capstone)" % (rom_path, int(offset) & 0xFFFFFFFF))
    if int(dump_hex) > 0:
        nh = min(int(dump_hex), len(data))
        print("  hex: %s" % " ".join("%02X" % b for b in data[:nh]))
    if int(be_words) > 0:
        nw = min(int(be_words), max(0, (len(data) + 3) // 4))
        words = []
        for i in range(nw):
            off = i * 4
            if off + 4 <= len(data):
                words.append(struct.unpack(">I", data[off : off + 4])[0])
        if words:
            print("  be_words: %s" % ", ".join("0x%08X" % w for w in words))
    n = 0
    for insn in md.disasm(data, offset):
        print("  0x%08X: %s %s" % (insn.address, insn.mnemonic, insn.op_str))
        n += 1
        if n >= int(count):
            break
    if n == 0:
        print("  (no insns decoded — short file or invalid alignment)")
    print("")


# ROM file offsets aligned with **`config/afa_rsp/*.template.toml`** (same SHA1 as **`config/splat.yaml`**).
AFA_USA_CAPSTONE_HINTS = (
    (0x4BE20, "MIPS at 0x4BE20 (repo asm/4BE20.s func_8024AE70) - not aspMain RSP text"),
    (0x4DAB0, "aspMain.afa.us.template.toml text_offset"),
    (0x4C830, "njpgdspMain.afa.us.template.toml text_offset"),
)


def main():
    ap = argparse.ArgumentParser(
        description="Disassemble MIPS32 BE at ROM offset(s) using Capstone (host CLI; no Ghidra)."
    )
    ap.add_argument(
        "--rom",
        default=None,
        help="Cart ROM path (default: lib/Zelda64Recomp/afa.n64.us.z64 or roms/afa.n64.us.z64)",
    )
    ap.add_argument(
        "--offset",
        type=lambda x: int(x, 0),
        default=None,
        help="Single file byte offset (hex ok). Omit if using --offsets or --afa-usa-hints.",
    )
    ap.add_argument(
        "--offsets",
        default=None,
        metavar="LIST",
        help="Comma-separated file offsets (hex ok), e.g. 0x4BE20,0x4DAB0,0x4C830",
    )
    ap.add_argument(
        "--afa-usa-hints",
        action="store_true",
        help="Print Capstone at **0x4BE20**, **0x4DAB0**, **0x4C830** (labels match **config/afa_rsp/*.template.toml**)",
    )
    ap.add_argument("--count", type=int, default=8, help="Max instructions per block (default 8)")
    ap.add_argument(
        "--dump-hex",
        type=int,
        default=0,
        metavar="N",
        help="Print first N bytes as hex before disasm (0=skip; matches Ghidra HEX_DUMP idea)",
    )
    ap.add_argument(
        "--be-words",
        type=int,
        default=0,
        metavar="N",
        help="Print first N big-endian u32 words as 0x..., comma-separated (0=skip; compare IMEM bootstrap)",
    )
    args = ap.parse_args()

    try:
        from capstone import CS_ARCH_MIPS, CS_MODE_BIG_ENDIAN, CS_MODE_MIPS32, Cs
    except ImportError:
        print("Install Capstone: pip install -r requirements.txt  (or: pip install capstone)", file=sys.stderr)
        return 1

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rom_path = args.rom or _default_rom_path(repo)
    if not rom_path or not os.path.isfile(rom_path):
        print("ROM not found; pass --rom", file=sys.stderr)
        return 1

    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_BIG_ENDIAN)

    blocks = []
    if args.afa_usa_hints:
        blocks = [(off, lbl) for off, lbl in AFA_USA_CAPSTONE_HINTS]
    elif args.offsets:
        parts = [p.strip() for p in str(args.offsets).split(",") if p.strip()]
        for p in parts:
            try:
                blocks.append((int(p, 0), None))
            except ValueError:
                print("Bad offset in --offsets: %r" % p, file=sys.stderr)
                return 1
    elif args.offset is not None:
        blocks = [(args.offset, None)]
    else:
        ap.error("Specify --offset, --offsets LIST, or --afa-usa-hints")

    for off, label in blocks:
        if label:
            print("--- %s ---" % label)
        _disasm_block(md, rom_path, off, args.count, args.dump_hex, args.be_words)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
