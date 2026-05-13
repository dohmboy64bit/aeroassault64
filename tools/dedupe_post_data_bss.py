#!/usr/bin/env python3
"""
Strip duplicate global names from splat-emitted `*.bss.s` when the same name is
already defined in `post_data.o` (ROM tail `.text`).

Context (see root Makefile + Docs/Workflow.md): `post_data.s` maps ROM 0x57D20+
into VRAM from 0x80256D70; splat can still emit `func_*` / `D_*` in `800000.bss.s`
for addresses that fall in the same VRAM window, so `mips-linux-gnu-ld` needs
`--allow-multiple-definition` unless those BSS lines are removed.

Preferred input: **`mips-linux-gnu-readelf -s build/asm/post_data.o`** (same line shape as
**`tools/gen_splat_extern_ld.py`**) — collects **GLOBAL** / **WEAK** symbols in any loaded section so
**`OBJECT`** labels in **`.text`** (e.g. **`.L806112D8`**) are included; plain **`nm`** often omits those.
Fallback: **`nm --defined-only`** for **`T`/`t`**, then scan **`asm/post_data.s`** for **`glabel`** /
**`dlabel`**.

spimdisasm **`800000.bss.s`** uses **`nonmatching` + `glabel`/`dlabel` + `.space`** blocks, not only
**`.comm`**. We remove a block when the symbol name is **already defined in `post_data.o`**.

Usage (from repo root, after `splat split` and assembling post_data):
  mips-linux-gnu-as ... -o build/asm/post_data.o asm/post_data.s   # or `make build/asm/post_data.o`
  python3 tools/dedupe_post_data_bss.py --dry-run
  python3 tools/dedupe_post_data_bss.py --apply

Requires WSL/Linux toolchain on PATH for **`readelf`** / **`nm`** when using the default **`post_data.o`** path.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

COMM_RE = re.compile(
    r"^\s*\.comm\s+([A-Za-z_.][\w.]*)\s*,",
    re.I,
)
LCOMM_RE = re.compile(
    r"^\s*\.lcomm\s+([A-Za-z_.][\w.]*)\s*,",
    re.I,
)
GLABEL_RE = re.compile(r"^\s*glabel\s+(\S+)")
DLABEL_RE = re.compile(r"^\s*dlabel\s+(\S+)")
NONMATCHING_RE = re.compile(r"^nonmatching\s+(\S+)\s*,")
GLABEL_OR_DLABEL = re.compile(r"^\s*(glabel|dlabel)\s+(\S+)")


def readelf_defined_global_symbols(obj: Path) -> set[str]:
    """GLOBAL/WEAK defined symbols (not UND). Matches gen_splat_extern_ld readelf parsing."""
    out: set[str] = set()
    try:
        raw = subprocess.check_output(
            ["mips-linux-gnu-readelf", "-W", "-s", str(obj)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"dedupe_post_data_bss: readelf failed ({e}).", file=sys.stderr)
        return out
    for line in raw.splitlines():
        s = line.strip()
        if not s or not s[0].isdigit():
            continue
        if ":" not in s:
            continue
        _num, rest = s.split(":", 1)
        parts = rest.split()
        if len(parts) < 7:
            continue
        ndx = parts[5]
        bind = parts[3]
        if ndx == "UND":
            continue
        if bind not in ("GLOBAL", "WEAK"):
            continue
        name = parts[6] if len(parts) == 7 else " ".join(parts[6:])
        if not name or name.startswith("@"):
            continue
        out.add(name)
    return out


def nm_defined_text_symbols(post_obj: Path) -> set[str]:
    out: set[str] = set()
    try:
        raw = subprocess.check_output(
            ["mips-linux-gnu-nm", "--defined-only", str(post_obj)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"dedupe_post_data_bss: nm failed ({e}); use --post-asm fallback.", file=sys.stderr)
        return out
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        sym_type = parts[-2]
        name = parts[-1]
        if sym_type in "Tt":
            out.add(name)
    return out


def strip_eligible(sym: str, defined: set[str]) -> bool:
    """True if bss should not re-declare this symbol (post_data.o already defines it)."""
    return sym in defined


def scan_post_data_asm_labels(post_asm: Path) -> set[str]:
    """Slow but works without mips nm; only catches labels at line start (splat style)."""
    out: set[str] = set()
    with post_asm.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = GLABEL_RE.match(line) or DLABEL_RE.match(line)
            if m:
                out.add(m.group(1))
    return out


def collect_post_data_defs(post_obj: Path | None, post_asm: Path) -> set[str]:
    if post_obj is not None and post_obj.is_file():
        s = readelf_defined_global_symbols(post_obj)
        if s:
            return s
        s = nm_defined_text_symbols(post_obj)
        if s:
            return s
    if not post_asm.is_file():
        print(f"dedupe_post_data_bss: missing {post_asm}", file=sys.stderr)
        return set()
    print("dedupe_post_data_bss: falling back to scanning asm/post_data.s for glabel/dlabel …")
    return scan_post_data_asm_labels(post_asm)


def should_skip_bss_file(path: Path) -> bool:
    # Makefile excludes this object: same VRAM window as post_data; do not strip blindly.
    return path.name == "57D20.bss.s"


def strip_bss_lines(lines: list[str], defined: set[str]) -> tuple[list[str], int]:
    """Remove `.comm` / spimdisasm `nonmatching`+label+`.space` blocks duplicating post_data symbols."""
    removed = 0
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        cm = COMM_RE.match(line) or LCOMM_RE.match(line)
        if cm:
            name = cm.group(1)
            if strip_eligible(name, defined):
                removed += 1
                i += 1
                continue
            out.append(line)
            i += 1
            continue

        nm = NONMATCHING_RE.match(line)
        if nm:
            sym = nm.group(1)
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and j + 1 < n:
                gl = GLABEL_OR_DLABEL.match(lines[j])
                if gl and gl.group(2) == sym and ".space" in lines[j + 1]:
                    if strip_eligible(sym, defined):
                        removed += 1
                        i = j + 2
                        continue
        out.append(line)
        i += 1
    return out, removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repo root (default: parent of tools/)",
    )
    ap.add_argument(
        "--post-obj",
        type=Path,
        default=None,
        help="Assembled post_data.o (default: <repo>/build/asm/post_data.o)",
    )
    ap.add_argument(
        "--post-asm",
        type=Path,
        default=None,
        help="post_data.s (default: <repo>/asm/post_data.s)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write bss files back (default is dry-run)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only (default if neither --apply nor --dry-run)",
    )
    args = ap.parse_args()
    repo: Path = args.repo
    post_obj = args.post_obj or (repo / "build" / "asm" / "post_data.o")
    post_asm = args.post_asm or (repo / "asm" / "post_data.s")

    if not args.apply and not args.dry_run:
        args.dry_run = True

    defined = collect_post_data_defs(post_obj if post_obj.is_file() else None, post_asm)
    if not defined:
        print("dedupe_post_data_bss: no symbols from post_data — nothing to do.", file=sys.stderr)
        return 1

    asm_root = repo / "asm"
    if not asm_root.is_dir():
        print(f"dedupe_post_data_bss: missing asm dir {asm_root}", file=sys.stderr)
        return 1

    bss_files = sorted(asm_root.rglob("*.bss.s"))
    if not bss_files:
        print(f"dedupe_post_data_bss: no *.bss.s under {asm_root}", file=sys.stderr)
        return 1

    total_removed = 0
    for bf in bss_files:
        if should_skip_bss_file(bf):
            continue
        text = bf.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        # splitlines(keepends) may lose last line without newline — rare for .s
        if not text.endswith("\n") and lines:
            pass
        new_lines, removed = strip_bss_lines(lines, defined)
        if removed:
            print(
                f"{bf.relative_to(repo)}: removed {removed} duplicate symbol construct(s) "
                "(.comm/.lcomm or nonmatching+label+.space)"
            )
            total_removed += removed
            if args.apply:
                bf.write_text("".join(new_lines), encoding="utf-8", newline="\n")

    print(f"dedupe_post_data_bss: total duplicate construct(s) removed: {total_removed}")
    if args.dry_run and total_removed and not args.apply:
        print("dedupe_post_data_bss: dry-run only — re-run with --apply to write files.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
