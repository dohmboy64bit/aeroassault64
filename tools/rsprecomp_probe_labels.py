# -*- coding: utf-8 -*-
"""Probe RSPRecomp text_size vs missing goto labels (AFA USA)."""
from __future__ import print_function

import os
import re
import subprocess
import sys

E = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "lib", "Zelda64Recomp"))
R = os.path.join(E, "RSPRecomp.exe")


def probe(off, size, addr, extras, out_name="probe"):
    body = (
        "text_offset = 0x%X\n"
        "text_size = 0x%X\n"
        "text_address = 0x%X\n"
        'rom_file_path = "afa.n64.us.z64"\n'
        'output_file_path = "rsp/_probe_%s.cpp"\n'
        'output_function_name = "%s"\n'
        "extra_indirect_branch_targets = %s\n"
    ) % (off, size, addr, out_name, out_name, extras)
    toml = os.path.join(E, "_probe.toml")
    cpp = os.path.join(E, "rsp", "_probe_%s.cpp" % out_name)
    with open(toml, "w", encoding="ascii") as f:
        f.write(body)
    p = subprocess.run([R, "_probe.toml"], cwd=E, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return {"rc": p.returncode, "err": (p.stderr or "")[:300]}
    t = open(cpp, encoding="utf-8", errors="replace").read()
    gotos = set(re.findall(r"goto (L_[0-9A-Fa-f]+)", t))
    labels = set(re.findall(r"^(L_[0-9A-Fa-f]+):", t, re.M))
    missing = sorted(gotos - labels, key=lambda x: int(x[2:], 16))
    inv = len(re.findall(r"Unhandled instruction:\s*INVALID", p.stderr or ""))
    return {"rc": 0, "inv": inv, "gotos": len(gotos), "labels": len(labels), "missing": missing}


def main():
    if not os.path.isfile(R):
        print("Missing", R, file=sys.stderr)
        return 1
    print("=== aspMain @ 0x4DAB0 ===")
    for sz in (0x1000, 0x1100, 0x1200, 0x1800, 0x2000):
        r = probe(0x4DAB0, sz, 0x04001000, [0x888, 0xF68], "asp_%x" % sz)
        print("size=0x%X" % sz, r)
    print("=== njpg @ 0x4C830 ===")
    extras = [0x768, 0xE48, 0x1000, 0x1B70]
    for sz in (0xAF0, 0x1000, 0x1400, 0x1C00, 0x2000):
        r = probe(0x4C830, sz, 0x04001080, extras, "njpg_%x" % sz)
        print("size=0x%X" % sz, r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
