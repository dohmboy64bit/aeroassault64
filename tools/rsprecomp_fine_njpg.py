# -*- coding: utf-8 -*-
"""Pick **`njpgdspMain`** offset among **`rsprecomp_find_njpg2.py`** inv=0 hits (maximize **`case`** count).

Writes **`_njf.toml`** / **`rsp/_njf.cpp`**.

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
    path = os.path.join(E, "_njf.toml")
    with open(path, "w", encoding="ascii") as f:
        f.write(
            "text_offset = 0x%X\n"
            "text_size = 0x%X\n"
            "text_address = 0x%X\n"
            'rom_file_path = "afa.n64.us.z64"\n'
            'output_file_path = "rsp/_njf.cpp"\n'
            "output_function_name = \"njpgdspMain\"\n"
            % (off, SIZE, ADDR)
        )
    r = subprocess.run([R, "_njf.toml"], cwd=E, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    inv = len(re.findall(r"Unhandled instruction:\s*INVALID", r.stderr or ""))
    cpp = open(os.path.join(E, "rsp", "_njf.cpp"), encoding="utf-8", errors="replace").read()
    return inv, cpp.count("case ")


def main():
    best = (10**9, -1, -1)
    for off in range(0x4C400, 0x4CA00, 0x10):
        g = score(off)
        if g is None:
            print("0x%X skip/overlap" % off)
            continue
        inv, cases = g
        print("0x%X inv=%d cases=%d" % (off, inv, cases))
        if inv < best[0] or (inv == best[0] and cases > best[2]):
            best = (inv, off, cases)
    print("BEST", best)


if __name__ == "__main__":
    main()
