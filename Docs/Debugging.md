# Debugging

## Windows PE (target)

- Build the CMake-generated **Windows** configuration you use day to day (Debug or RelWithDebInfo as appropriate).
- Open the built `.exe` in **Visual Studio** and set the startup project if the solution has multiple targets.
- Prefer **break on first chance** only when chasing heap/init bugs; otherwise keep exceptions quiet to reduce noise.

## N64 / recomp context

- Use **Ghidra** for ROM truth; coordinate with the project owner before large automated Ghidra changes (`Docs/SystemPrompt.md`).
- Use **Capstone** (or similar) when you need instruction-accurate disassembly beyond what static asm listing gives you.

## Phase 6 — Windows PE (engine)

- After **`lib/Zelda64Recomp`** is present (**`git submodule update --init --recursive`**), build per **`lib/Zelda64Recomp/BUILDING.md`** (Majora's Mask **decompressed** ROM, in-tree **N64Recomp** / **RSPRecomp** runs, then CMake). Use **`tools/phase6_engine_cmake.ps1`** from the **AeroAssault64** repo root for **`cmake -S lib/Zelda64Recomp -B build-engine`** (**`tools/README.txt`** § Phase 6), or **repo-root** **`cmake --preset engine-superbuild-ninja-release`** then **`cmake --build --preset engine-superbuild-ninja-release`** (**`CMakeLists.txt`** **`ExternalProject_Add`**, **`CMakePresets.json`**).
- **RecompiledFuncs path:** run **`tools/phase6_link_recompiledfuncs.ps1`** so upstream CMake globs see **repo-root** **`RecompiledFuncs/`** (see **`lib/README.txt`**). Without this, **`add_library(RecompiledFuncs STATIC)`** can fail with **no SOURCES** even after Phase 5 N64Recomp.

**Vendored recompilers:** run **`tools/phase6_copy_n64recomp_to_engine.ps1`** so **`lib/Zelda64Recomp/`** contains **`N64Recomp.exe`** and **`RSPRecomp.exe`** where **`lib/Zelda64Recomp/BUILDING.md`** § 4 expects them (after submodule init). Same binaries as **`tools/README.txt`** Phase 5; engine **`.gitignore`** ignores **`*.exe`** there.
- **Common configure failures (upstream tree):**
  - **`Cannot find source file: .../rsp/aspMain.cpp`** — **`rsp/.gitignore`** lists generated **`aspMain.cpp`** / **`njpgdspMain.cpp`**. Generate them with **RSPRecomp** per **`lib/Zelda64Recomp/BUILDING.md`** § 4 (**`./RSPRecomp aspMain.us.rev1.toml`** etc., from the **engine** root with MM artifacts).
  - **Missing `RecompiledPatches/patches.c`** — produced by the engine’s **`patches/`** + **`N64Recomp patches.toml`** pipeline (**`lib/Zelda64Recomp/CMakeLists.txt`** custom commands); not the same as AeroAssault64 **`patches/`** at repo root.
- Open the generated solution or launch **`build-engine/Zelda64Recompiled.exe`** (upstream **`add_executable(Zelda64Recompiled)`** + **`CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}`** in **`lib/Zelda64Recomp/CMakeLists.txt`**) under **Visual Studio** for **Debug** / **RelWithDebInfo** once the target links. **Visual Studio** launch working directory is set to **`lib/Zelda64Recomp/`** (**`VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"`** in the same file) so relative **`assets/`** paths match **`lib/Zelda64Recomp/BUILDING.md`** § 6.

- **MM baseline (until AFA fork):** run **`make phase6-mm-prereq`** (**`python3 tools/phase6_mm_engine_prereq_check.py`**) after **`tools/phase6_setup_windows.ps1`** — lists missing **`lib/Zelda64Recomp/BUILDING.md`** artifacts (decompressed ROM **`mm.us.rev1.rom_uncompressed.z64`**, generated **`rsp/*.cpp`**, **`RecompiledPatches/`**, etc.). Use **`--strict`** in scripts/CI when you require a complete MM tree. Then complete **BUILDING.md** sections 3–5 and debug **`build-engine/Zelda64Recompiled.exe`** (working directory = engine root per **`VS_DEBUGGER_WORKING_DIRECTORY`** in **`lib/Zelda64Recomp/CMakeLists.txt`**).

- **AFA-specific** breakpoints and RT64 / recomp logging notes belong here as the port boots on a **forked** engine, not stock MM.

### Phase 6 — No-MM + AFA `RecompiledFuncs` (MSVC smoke)

- **Build:** from repo root, **`tools/phase6_materialize_no_mm_engine_files.ps1`**, then **`tools/phase6_engine_cmake_vs2022.ps1 -Mode All -NoMmRom`** → **`build-engine-vs2022/Release/Zelda64Recompiled.exe`** (inner CMake **`VS_DEBUGGER_WORKING_DIRECTORY`** = **`lib/Zelda64Recomp/`** in **`lib/Zelda64Recomp/CMakeLists.txt`** — use the same cwd so relative **`assets/`** matches **`lib/Zelda64Recomp/BUILDING.md`** § 6).
- **CPU recomp:** **`tools/N64Recomp.exe config/aerofighters_assault.n64recomp.toml`** (Phase 5 **`tools/README.txt`**); output under repo-root **`RecompiledFuncs/`** with **`tools/phase6_link_recompiledfuncs.ps1`** junction into **`lib/Zelda64Recomp/RecompiledFuncs/`** (**`lib/README.txt`**). If the directory has **no** **`*.c`** yet, CMake’s **`RecompiledFuncs`** static library has **no sources** and configure fails (**`lib/Zelda64Recomp/CMakeLists.txt`** `add_library` / `file(GLOB …/*.c)`); use **`tools/phase6_ci_ensure_recompiledfuncs_stub.ps1`** or **`.\tools\phase6_engine_cmake_vs2022.ps1 -CiStub …`** for the same minimal stub path as **`.github/workflows/engine-windows.yml`** (stub is **not** a substitute for real N64Recomp output for linking **`Zelda64Recompiled.exe`**).
- **Smoke (2026-05):** launched **`Zelda64Recompiled.exe`** with cwd **`lib/Zelda64Recomp/`**; process **started** and remained running (SDL window) until stopped manually after a few seconds — **not** a gameplay or ROM-load correctness test. Repeatable: **`tools/phase6_smoke_engine.ps1`** (**`tools/README.txt`** § Phase 6). Stock **`src/game/`** is still MM-oriented; **`AEROASSAULT64_NO_MM_ROM`** only stubs engine **`patches/`** / **`patches.toml`** and RSP sources (**`lib/Zelda64Recomp/CMakeLists.txt`**) unless **`rsp/aspMain.cpp`** and **`rsp/njpgdspMain.cpp`** exist (then real RSP is linked).
- **LNK4098 (`LIBCMT` vs `MSVCRT`):** **`CMAKE_MSVC_RUNTIME_LIBRARY`** is set for **`/MD`** at the top of **`lib/Zelda64Recomp/CMakeLists.txt`**; **`Zelda64Recompiled`** also links **`/NODEFAULTLIB:LIBCMT`** for Release-like configs when a static dependency still advertises **`LIBCMT`** (MSVC linker note for **LNK4098**).
- **Branding + optional AFA ROM slot:** CMake generates **`build-engine-vs2022/aero_build_config.h`** (or your **`CMAKE_BINARY_DIR`**) from **`lib/Zelda64Recomp/cmake/aero_build_config.h.in`** — default **SDL** title **“Aero Assault 64 (recomp bring-up)”** and version **`1.2.2+aeroassault64`**. A second **`recomp::GameEntry`** for AFA USA is compiled in only when **`AEROASSAULT64_WITH_AFA_USA`** is **1** (from **`config/.afa_usa_rom_xxh3`** or **`-DAEROASSAULT64_AFA_ROM_XXH3_HEX`**); see **`tools/compute_aero_rom_xxh3.py`** and **`lib/Zelda64Recomp/CMakeLists.txt`**.

## Reference material

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)
