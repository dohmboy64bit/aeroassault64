# -*- coding: utf-8 -*-
"""Scan ROM for **`njpgdspMain`** `text_offset` disjoint from aspMain span **[0x4DAB0, 0x4EAB0)**.

Uses **`text_size` = 0xAF0** (same as upstream **`njpgdspMain.us.rev1.toml`** on Zelda64Recomp).
Writes **`_nj3.toml`** / **`rsp/_nj3.cpp`** under **`lib/Zelda64Recomp/`**.

Docs: **`lib/Zelda64Recomp/AFA_PORT.md`** §1.
"""
import os
import re
import subprocess

E = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "lib", "Zelda64Recomp"))
R = os.path.join(E, "RSPRecomp.exe")
SIZE = 0xAF0
ADDR = 0x04001080
ASP0, ASP1 = 0x4DAB0, 0x4DAB0 + 0x1000


def disjoint(off):
    a0, a1 = off, off + SIZE
    return a1 <= ASP0 or a0 >= ASP1


def score(off):
    if not disjoint(off):
        return None
    path = os.path.join(E, "_nj3.toml")
    with open(path, "w", encoding="ascii") as f:
        f.write(
            "text_offset = 0x%X\n"
            "text_size = 0x%X\n"
            "text_address = 0x%X\n"
            'rom_file_path = "afa.n64.us.z64"\n'
            'output_file_path = "rsp/_nj3.cpp"\n'
            "output_function_name = \"njpgdspMain\"\n"
            % (off, SIZE, ADDR)
        )
    r = subprocess.run([R, "_nj3.toml"], cwd=E, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    return len(re.findall(r"Unhandled instruction:\s*INVALID", r.stderr or ""))


def main():
    best = (10**9, -1)
    for off in range(0x4C050, 0x57A60 - SIZE, 0x40):
        s = score(off)
        if s is None:
            continue
        if s < best[0]:
            best = (s, off)
        if s == 0:
            print("inv=0 off=0x%X" % off)
    print("BEST inv=%d off=0x%X" % (best[0], best[1]))


if __name__ == "__main__":
    main()
