#!/usr/bin/env python3
"""
Compute XXH3-64 of an N64 ROM file the same way librecomp does before validation:

  lib/Zelda64Recomp/lib/N64ModernRuntime/librecomp/src/recomp.cpp
    - read full file
    - pad size to multiple of 4
    - byteswap to native .z64 order when magic at byte 0 is 0x80371240 after normalization
    - XXH3_64bits(rom_data.data(), rom_data.size())

Requires: pip install xxhash

Writes one line of 16 lowercase hex digits to the output path (default: config/.afa_usa_rom_xxh3).
CMake / lib/Zelda64Recomp/CMakeLists.txt reads that file (or use -DAEROASSAULT64_AFA_ROM_XXH3_HEX=...).
"""
from __future__ import annotations

import argparse
import sys

FIRST_ROM = bytes((0x80, 0x37, 0x12, 0x40))


def normalize_rom(data: bytearray) -> bytes:
    # Pad to multiple of 4 (recomp.cpp select_rom).
    while len(data) % 4:
        data.append(0)

    def match(idx: tuple[int, int, int, int]) -> bool:
        return (
            len(data) >= 4
            and data[0] == FIRST_ROM[idx[0]]
            and data[1] == FIRST_ROM[idx[1]]
            and data[2] == FIRST_ROM[idx[2]]
            and data[3] == FIRST_ROM[idx[3]]
        )

    if match((0, 1, 2, 3)):
        return bytes(data)
    if match((3, 2, 1, 0)):
        # Byteswapped4 — reverse each 4-byte word (see recomp.cpp byteswap_data with index_xor 3).
        for i in range(0, len(data), 4):
            data[i], data[i + 3] = data[i + 3], data[i]
            data[i + 1], data[i + 2] = data[i + 2], data[i + 1]
        return bytes(data)
    if match((1, 0, 3, 2)):
        # Byteswapped2 — swap 16-bit halves within each 32-bit word (index_xor 1).
        for i in range(0, len(data), 4):
            data[i], data[i + 1] = data[i + 1], data[i]
            data[i + 2], data[i + 3] = data[i + 3], data[i + 2]
        return bytes(data)
    print("error: ROM does not match expected N64 header byte orders (see recomp.cpp check_rom_start).", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", help="Path to .z64/.n64/.v64 USA retail image")
    ap.add_argument(
        "-o",
        "--output",
        default="config/.afa_usa_rom_xxh3",
        help="Write 16 hex digits (no 0x) here (default: config/.afa_usa_rom_xxh3)",
    )
    args = ap.parse_args()

    try:
        import xxhash
    except ImportError:
        print("error: install xxhash first:  pip install xxhash", file=sys.stderr)
        sys.exit(1)

    path = args.rom
    with open(path, "rb") as f:
        raw = bytearray(f.read())

    normalized = normalize_rom(raw)
    h = xxhash.xxh3_64(normalized)
    digest = h.intdigest()
    line = f"{digest:016x}\n"

    out = args.output
    with open(out, "w", encoding="ascii", newline="\n") as f:
        f.write(line)

    print(f"OK: wrote {digest:#018x} to {out}")


if __name__ == "__main__":
    main()
