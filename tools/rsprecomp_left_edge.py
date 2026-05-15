# -*- coding: utf-8 -*-
"""Fine-step scan for aspMain `text_offset` where RSPRecomp stops crashing (AFA USA).

Requires **`lib/Zelda64Recomp/RSPRecomp.exe`**, **`afa.n64.us.z64`**, writes temporary **`_m.toml`**
and **`rsp/_m.cpp`**. Pair with **`rsprecomp_scan_offsets.py`** (coarse INVALID ramp).

Docs: **`lib/Zelda64Recomp/AFA_PORT.md`** §1.
"""
import os
import re
import subprocess

E = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "lib", "Zelda64Recomp"))
R = os.path.join(E, "RSPRecomp.exe")
SIZE = 0x1000


def go(off):
    path = os.path.join(E, "_m.toml")
    with open(path, "w", encoding="ascii") as f:
        f.write(
            "text_offset = 0x%X\n"
            "text_size = 0x%X\n"
            "text_address = 0x04001000\n"
            'rom_file_path = "afa.n64.us.z64"\n'
            'output_file_path = "rsp/_m.cpp"\n'
            "output_function_name = \"aspMain\"\n"
            "extra_indirect_branch_targets = []\n" % (off, SIZE)
        )
    r = subprocess.run([R, "_m.toml"], cwd=E, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    inv = len(re.findall(r"Unhandled instruction:\s*INVALID", r.stderr or ""))
    cpp = open(os.path.join(E, "rsp", "_m.cpp"), encoding="utf-8", errors="replace").read()
    return inv, cpp.count("case ")


def main():
    for off in range(0x4D800, 0x4E600, 0x10):
        g = go(off)
        if g is None:
            print("0x%X crash" % off)
            continue
        inv, cases = g
        if inv <= 2:
            print("0x%X inv=%d cases=%d" % (off, inv, cases))


if __name__ == "__main__":
    main()
