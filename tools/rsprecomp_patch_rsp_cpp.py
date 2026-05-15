# -*- coding: utf-8 -*-
"""Post-process RSPRecomp rsp/*.cpp for MSVC: stub missing goto labels, fix addiu $zero.

RSPRecomp may emit `goto L_XXXX` and switch cases without a matching `L_XXXX:` when
extra_indirect_branch_targets or branch targets fall outside the recovered static graph
(see lib/Zelda64Recomp/AFA_PORT.md section 1).

Usage (repo root):
  python tools/rsprecomp_patch_rsp_cpp.py
  python tools/rsprecomp_patch_rsp_cpp.py lib/Zelda64Recomp/rsp/aspMain.cpp
"""
from __future__ import print_function

import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATHS = [
    os.path.join(REPO, "lib", "Zelda64Recomp", "rsp", "aspMain.cpp"),
    os.path.join(REPO, "lib", "Zelda64Recomp", "rsp", "njpgdspMain.cpp"),
]

MARKER = "// AEROASSAULT64_RSP_PATCHED_MISSING_LABELS"


def patch_file(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if MARKER in text:
        print(path, "already patched")
        return 0

    gotos = set(re.findall(r"goto (L_[0-9A-Fa-f]+)", text))
    labels = set(re.findall(r"^(L_[0-9A-Fa-f]+):", text, re.M))
    missing = sorted(gotos - labels, key=lambda x: int(x[2:], 16))
    if not missing:
        print(path, "no missing labels")
    else:
        stubs = [MARKER]
        for lab in missing:
            stubs.append(
                "%s:\n"
                "    return RspExitReason::UnhandledJumpTarget;"
                % lab
            )
        stub_block = "\n".join(stubs) + "\n"
        anchor = "do_indirect_jump:"
        if anchor in text:
            text = text.replace(anchor, stub_block + anchor, 1)
        else:
            # njpg may lack do_indirect_jump; insert before final closing brace of function
            idx = text.rfind("\n}")
            if idx < 0:
                print(path, "cannot find insertion point", file=sys.stderr)
                return 1
            text = text[:idx] + "\n" + stub_block + text[idx:]

    # addiu $zero assignments are invalid C++ lvalues
    text2, n_zero = re.subn(
        r"^(\s*)0 = (RSP_ADD32\([^)]*\));",
        r"\1(void)\2;",
        text,
        flags=re.M,
    )
    if n_zero:
        text = text2

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(path, "patched missing labels:", missing, "zero_assign_fixes:", n_zero)
    return 0


def main(argv):
    paths = argv[1:] if len(argv) > 1 else DEFAULT_PATHS
    rc = 0
    for p in paths:
        if not os.path.isfile(p):
            print("skip missing", p)
            continue
        rc |= patch_file(p)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
