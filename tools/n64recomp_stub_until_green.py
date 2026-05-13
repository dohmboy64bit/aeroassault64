#!/usr/bin/env python3
"""Run tools/N64Recomp.exe repeatedly; append failing func_* to stubs= in the TOML.

Run from repo root: python tools/n64recomp_stub_until_green.py

N64Recomp (commit in tools/README.txt):
- stubs: src/main.cpp sets func.stubbed; recompilation.cpp skips recompiling the body.
- jump tables: src/analysis.cpp prints "Failed to determine size of jump table" then
  analyze_function returns false -> "Failed to analyze func_...".
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "aerofighters_assault.n64recomp.toml"
EXE = ROOT / "tools" / "N64Recomp.exe"
MAX_ITERS = 200

FUNC_RE = re.compile(r"(?:Error recompiling|Failed to analyze) (func_[0-9A-Fa-f]+)")

ANCHOR = "\n]\n\n[[patches.instruction]]"


def add_stub(text: str, fn: str) -> str:
    if ANCHOR not in text:
        raise SystemExit(f"missing anchor {ANCHOR!r} in {CFG}")
    if f'"{fn}"' in text:
        raise SystemExit(f"stub {fn} already present but N64Recomp still fails")
    return text.replace(ANCHOR, f'\n    "{fn}",' + ANCHOR, 1)


def main() -> int:
    if not EXE.is_file():
        print(f"missing {EXE}", file=sys.stderr)
        return 1
    if not CFG.is_file():
        print(f"missing {CFG}", file=sys.stderr)
        return 1

    for iteration in range(MAX_ITERS):
        r = subprocess.run(
            [str(EXE), str(CFG)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            print(out)
            print(f"OK: N64Recomp exit 0 after {iteration} auto-stub iteration(s).")
            return 0

        m = FUNC_RE.search(out)
        if not m:
            print(out, file=sys.stderr)
            return r.returncode or 1

        fn = m.group(1)
        text = CFG.read_text(encoding="utf-8")
        try:
            text = add_stub(text, fn)
        except SystemExit as e:
            print(out, file=sys.stderr)
            print(str(e), file=sys.stderr)
            return 1
        CFG.write_text(text, encoding="utf-8", newline="\n")
        print(f"iter {iteration + 1}: stubbed {fn}")

    print("abort: MAX_ITERS", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
