AFA RSP (Phase 6 — execution order item 2)

This directory holds notes and (later) RSPRecomp TOMLs for Aero Fighters Assault.

Upstream Zelda64Recomp expects generated sources:
  lib/Zelda64Recomp/rsp/aspMain.cpp
  lib/Zelda64Recomp/rsp/njpgdspMain.cpp

Majora's Mask uses aspMain.us.rev1.toml / njpgdspMain.us.rev1.toml against the decompressed MM ROM
(see lib/Zelda64Recomp/BUILDING.md section 4). AFA needs its own microcode ROM offsets from Ghidra / ROM
analysis — do not point MM TOMLs at roms/afa.n64.us.z64 without re-deriving text_offset/text_size/text_address.

Build options that use RSP stubs when rsp/*.cpp are missing (see lib/Zelda64Recomp/CMakeLists.txt _AERO_PATCH_RSP_STUBS):
  -DAEROASSAULT64_NO_MM_ROM=ON, or -DAEROASSAULT64_AFA_PRODUCT=ON without -DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON
  (with python3 tools/phase6_materialize_no_mm_engine_files.py for RecompiledPatches headers as needed).
  RSP stubs come from tools/phase6_no_mm_engine/ when rsp/*.cpp are absent.
  With AFA_PRODUCT + AFA_RETAIL_PIPELINES, _AERO_PATCH_RSP_STUBS is OFF — you must supply both rsp/*.cpp (no RSP stub swap).

When you have valid TOMLs for AFA, place them under lib/Zelda64Recomp/ (or here + copy) and run
tools/RSPRecomp.exe from the engine root (upstream BUILDING.md section 4 when that file exists in the engine tree).

Windows helper (same idea as tools/phase6_rsprecomp_engine.ps1 for MM):
  pwsh tools/phase6_rsprecomp_afa.ps1
  pwsh tools/phase6_rsprecomp_afa.ps1 -RomPath E:\path\to\afa.n64.us.z64
  pwsh tools/phase6_rsprecomp_afa.ps1 -CopyTools
Expects engine root: aspMain.afa.us.toml, njpgdspMain.afa.us.toml (filled text_offset/text_size).

CMake (lib/Zelda64Recomp/CMakeLists.txt): when _AERO_PATCH_RSP_STUBS is ON, if BOTH rsp/aspMain.cpp and
rsp/njpgdspMain.cpp exist, they are linked; otherwise rsp_*_stub.cpp from tools/phase6_no_mm_engine/ is used.
When _AERO_PATCH_RSP_STUBS is OFF, the stub swap is skipped — both rsp/*.cpp must exist or the link will fail.

Templates (copy into engine root and fill offsets before running RSPRecomp):
  ../../config/afa_rsp/aspMain.afa.us.template.toml
  ../../config/afa_rsp/njpgdspMain.afa.us.template.toml

Full port checklist: lib/Zelda64Recomp/AFA_PORT.md
