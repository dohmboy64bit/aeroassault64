# Debugging

## Windows PE (target)

- Build the CMake-generated **Windows** configuration you use day to day (Debug or RelWithDebInfo as appropriate).
- Open the built `.exe` in **Visual Studio** and set the startup project if the solution has multiple targets.
- Prefer **break on first chance** only when chasing heap/init bugs; otherwise keep exceptions quiet to reduce noise.

## N64 / recomp context

- Use **Ghidra** for ROM truth; coordinate with the project owner before large automated Ghidra changes (`Docs/SystemPrompt.md`).
- Use **Capstone** (or similar) when you need instruction-accurate disassembly beyond what static asm listing gives you.

## Phase 6 — Windows PE (engine)

- After **`lib/Zelda64Recomp`** is present (**`git submodule update --init --recursive`**), build per **`lib/Zelda64Recomp/BUILDING.md`** (Majora's Mask **decompressed** ROM, in-tree **N64Recomp** / **RSPRecomp** runs, then CMake). Use **`tools/phase6_engine_cmake.ps1`** from the **AeroAssault64** repo root for **`cmake -S lib/Zelda64Recomp -B build-engine`** (**`tools/README.txt`** § Phase 6).
- **RecompiledFuncs path:** run **`tools/phase6_link_recompiledfuncs.ps1`** so upstream CMake globs see **repo-root** **`RecompiledFuncs/`** (see **`lib/README.txt`**). Without this, **`add_library(RecompiledFuncs STATIC)`** can fail with **no SOURCES** even after Phase 5 N64Recomp.

**Vendored recompilers:** run **`tools/phase6_copy_n64recomp_to_engine.ps1`** so **`lib/Zelda64Recomp/`** contains **`N64Recomp.exe`** and **`RSPRecomp.exe`** where **`lib/Zelda64Recomp/BUILDING.md`** § 4 expects them (after submodule init). Same binaries as **`tools/README.txt`** Phase 5; engine **`.gitignore`** ignores **`*.exe`** there.
- **Common configure failures (upstream tree):**
  - **`Cannot find source file: .../rsp/aspMain.cpp`** — **`rsp/.gitignore`** lists generated **`aspMain.cpp`** / **`njpgdspMain.cpp`**. Generate them with **RSPRecomp** per **`lib/Zelda64Recomp/BUILDING.md`** § 4 (**`./RSPRecomp aspMain.us.rev1.toml`** etc., from the **engine** root with MM artifacts).
  - **Missing `RecompiledPatches/patches.c`** — produced by the engine’s **`patches/`** + **`N64Recomp patches.toml`** pipeline (**`lib/Zelda64Recomp/CMakeLists.txt`** custom commands); not the same as AeroAssault64 **`patches/`** at repo root.
- Open the generated solution or launch **`build-engine/Zelda64Recompiled.exe`** (upstream **`add_executable(Zelda64Recompiled)`** + **`CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}`** in **`lib/Zelda64Recomp/CMakeLists.txt`**) under **Visual Studio** for **Debug** / **RelWithDebInfo** once the target links. **Visual Studio** launch working directory is set to **`lib/Zelda64Recomp/`** (**`VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"`** in the same file) so relative **`assets/`** paths match **`lib/Zelda64Recomp/BUILDING.md`** § 6.
- **AFA-specific** breakpoints and RT64 / recomp logging notes belong here as the port boots on a **forked** engine, not stock MM.

## Reference material

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)
