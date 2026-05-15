# -*- coding: utf-8 -*-
"""Brute-scan AFA USA ROM for aspMain RSPRecomp-friendly text_offset (coarse).

Runs RSPRecomp.exe from lib/Zelda64Recomp for each candidate offset; scores stderr
"Unhandled instruction: INVALID" count (lower is better). Skips offsets that crash
the tool (exit != 0 and != 1 — RSPRecomp may use 0 on success).

Evidence: splat `asm/data/4C050.data.s` shows RSP-like words after zeros at ROM 0x4C068
(VRAM 8024B0B8); `asm/4BE20.s` at 0x4BE20 is MIPS (`func_8024AE70`), not RSP text.

Docs: lib/Zelda64Recomp/AFA_PORT.md section 1.
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE = os.path.join(REPO, "lib", "Zelda64Recomp")
ROM = os.path.join(ENGINE, "afa.n64.us.z64")
RSP = os.path.join(ENGINE, "RSPRecomp.exe")

# .data start per config/splat.yaml main subsegment [0x4C050, data]
ROM_DATA_START = 0x4C050
# Last rodata before post_data asm
ROM_RODATA_END = 0x57A60
STEP = 0x100
TEXT_SIZE = 0x1000
TEXT_ADDR = 0x04001000


def main():
    if not os.path.isfile(RSP):
        print("Missing", RSP, file=sys.stderr)
        return 1
    if not os.path.isfile(ROM):
        print("Missing ROM", ROM, file=sys.stderr)
        return 1

    toml_path = os.path.join(ENGINE, "_scan_asp.toml")
    best = None
    for off in range(ROM_DATA_START, ROM_RODATA_END - TEXT_SIZE, STEP):
        body = (
            "text_offset = 0x%X\n"
            "text_size = 0x%X\n"
            "text_address = 0x%X\n"
            'rom_file_path = "afa.n64.us.z64"\n'
            'output_file_path = "rsp/_scan_aspMain.cpp"\n'
            "output_function_name = \"aspMain\"\n"
            "extra_indirect_branch_targets = []\n"
        ) % (off, TEXT_SIZE, TEXT_ADDR)
        with open(toml_path, "w", encoding="ascii") as f:
            f.write(body)

        try:
            p = subprocess.run(
                [RSP, "_scan_asp.toml"],
                cwd=ENGINE,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            print("timeout off=0x%X" % off)
            continue

        err = (p.stderr or "") + (p.stdout or "")
        inv = len(re.findall(r"Unhandled instruction:\s*INVALID", err))
        ok = p.returncode == 0 and inv < 500
        line = "off=0x%X rc=%d INVALID=%d" % (off, p.returncode, inv)
        if p.returncode not in (0, 1):
            line += " (crash?)"
        print(line)
        if p.returncode == 0:
            if best is None or inv < best[1]:
                best = (off, inv)
            if inv == 0:
                print("  *** zero INVALID — strong candidate")
    if best:
        print("BEST off=0x%X INVALID=%d" % (best[0], best[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
