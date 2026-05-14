AFA engine patches (N64Recomp) — templates live next to this file.

Upstream Majora's Mask flow (lib/Zelda64Recomp/BUILDING.md, upstream patches/ + patches.toml):
  patches/Makefile -> patches/patches.elf
  ./N64Recomp patches.toml -> RecompiledPatches/patches.c, patches.bin, etc.

For AFA you need:
  - MIPS patch sources under lib/Zelda64Recomp/patches/ (or a parallel tree + CMake change).
  - Symbol reference TOMLs for the AFA ELF (upstream uses Zelda64RecompSyms/mm.us.rev1.*.toml — see
    patches.toml.template in this directory, copied from:
    https://raw.githubusercontent.com/Mr-Wiseguy/Zelda64Recomp/master/patches.toml

When patches.elf + syms exist, copy patches.toml.template to lib/Zelda64Recomp/patches.toml (or a
fork-specific name) and adjust paths, then re-enable the full PatchesLib CMake branch
(AEROASSAULT64_NO_MM_ROM and AEROASSAULT64_AFA_PRODUCT OFF, or extend CMake for an AFA-specific option).

See lib/Zelda64Recomp/AFA_PORT.md for the checklist.
