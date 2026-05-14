AFA RSP (Phase 6 — execution order item 2)

This directory holds notes and (later) RSPRecomp TOMLs for Aero Fighters Assault.

Upstream Zelda64Recomp expects generated sources:
  lib/Zelda64Recomp/rsp/aspMain.cpp
  lib/Zelda64Recomp/rsp/njpgdspMain.cpp

Majora's Mask uses aspMain.us.rev1.toml / njpgdspMain.us.rev1.toml against the decompressed MM ROM
(see lib/Zelda64Recomp/BUILDING.md section 4). AFA needs its own microcode ROM offsets from Ghidra / ROM
analysis — do not point MM TOMLs at roms/afa.n64.us.z64 without re-deriving text_offset/text_size/text_address.

Build options until real AFA RSP exists:
  -DAEROASSAULT64_NO_MM_ROM=ON or -DAEROASSAULT64_AFA_PRODUCT=ON
  with python3 tools/phase6_materialize_no_mm_engine_files.py (RecompiledPatches headers) uses rsp stubs from
  tools/phase6_no_mm_engine/ when rsp/*.cpp are absent (lib/Zelda64Recomp/CMakeLists.txt).

When you have valid TOMLs for AFA, place them under lib/Zelda64Recomp/ (or here + copy) and run
tools/RSPRecomp.exe from the engine root per BUILDING.md.
