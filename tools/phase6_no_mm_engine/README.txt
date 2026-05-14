Stub sources for Zelda64Recomp when configured with -DAEROASSAULT64_NO_MM_ROM=ON
(AeroAssault64 bring-up without Majora's Mask ROM or MM patches.elf / N64Recomp patches.toml).

Files here are compiled via paths in lib/Zelda64Recomp/CMakeLists.txt (AEROASSAULT64_STUB_DIR).
Headers/overlays expected under lib/Zelda64Recomp/RecompiledPatches/ are installed by:
  python3 tools/phase6_materialize_no_mm_engine_files.py
  (or: tools/phase6_materialize_no_mm_engine_files.ps1 — delegates to the .py when python is on PATH)
  Makefile: make phase6-materialize-stubs

See lib/README.txt and Docs/Workflow.md Phase 6.
