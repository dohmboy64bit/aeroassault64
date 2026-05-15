AFA engine patches (N64Recomp) — templates live next to this file.

Upstream Majora's Mask flow (lib/Zelda64Recomp/BUILDING.md, upstream patches/ + patches.toml):
  patches/Makefile -> patches/patches.elf
  ./N64Recomp.exe patches.toml -> RecompiledPatches/patches.c, patches.bin, etc.

For AFA you still need (not automated by tools/phase6_full_recomp_afa.ps1):

  1. MIPS patch sources under lib/Zelda64Recomp/patches/ that build patches/patches.elf for the AFA
     program (same Makefile pattern as upstream MM, but symbols/VRAs from splat AFA ELF).

  2. Zelda64RecompSyms/afa.n64.us.*.toml — generate from build/aerofighters_assault.elf:
       pwsh tools/phase6_afa_generate_syms.ps1
     (runs N64Recomp config/afa_engine/dump_syms.toml --dump-context; see dump_syms.toml).

  3. Copy patches.toml.template -> lib/Zelda64Recomp/patches.toml (engine root), edit elf_path,
     func_reference_syms_file, data_reference_syms_files to your AFA artifacts.

  4. From engine root (with N64Recomp.exe per BUILDING.md section 4): ./N64Recomp.exe patches.toml

  5. CMake: -DAEROASSAULT64_AFA_PRODUCT=ON -DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON so PatchesLib uses
     RecompiledPatches/*.c from N64Recomp instead of tools/phase6_no_mm_engine stubs (see
     lib/Zelda64Recomp/CMakeLists.txt and repo CMakePresets engine-superbuild-*-afa-product-retail).

  Retail bring-up script (repo root): .\tools\phase6_afa_retail_prepare.ps1 -BuildMmPatchesElf -RunN64RecompPatches
  - WSL: CC=clang LD=ld.lld make in lib/Zelda64Recomp/patches/ (see script).
  - N64Recomp patches.toml uses MM syms — linking retail PatchesLib against AFA RecompiledFuncs will LNK2019
    until AFA patches.elf + Zelda64RecompSyms for AFA exist. After -RunN64RecompPatches on an AFA CPU tree,
    restore stub headers: python tools/phase6_materialize_no_mm_engine_files.py

One-shot CPU + RSP only (no patches): ../../tools/phase6_full_recomp_afa.ps1 from repo root (PowerShell).

See lib/Zelda64Recomp/AFA_PORT.md sections 1-2 and Docs/Workflow.md Phase 6.
