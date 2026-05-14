Engine submodule (**tracked**)

Upstream reference: https://github.com/Mr-Wiseguy/Zelda64Recomp  
**Submodule remote (this repo, `.gitmodules`):** https://github.com/DohmBoy64Bit/Zelda64Recomp.git — **branch tracked:** `dev` (AeroAssault64 port commits). **Gitlink:** run `git rev-parse HEAD:lib/Zelda64Recomp` after pull. To merge upstream Mr-Wiseguy `dev`, add that repo as a second remote inside **`lib/Zelda64Recomp`** and merge/rebase as needed.

After a fresh clone from repo root:

  git submodule update --init --recursive

Then open **`lib/Zelda64Recomp/BUILDING.md`** for RT64, nested submodules, dependencies, and the Windows CMake / Visual Studio flow. Upstream **BUILDING.md** describes **Majora's Mask** (decompressed ROM, `us.rev1.toml`, in-tree N64Recomp/RSPRecomp); **Aero Fighters Assault** still needs a **fork or in-tree adaptation** (TOML, assets, `RecompiledFuncs/` layout, glue under **`src/`**).

### Configure / build from this repo (Windows)

Upstream **`lib/Zelda64Recomp/CMakeLists.txt`** uses **`CMAKE_SOURCE_DIR`** for **`lib/rt64`**, **`RecompiledFuncs/`**, etc., so the engine must be configured with **that directory as the CMake source root** — not by `add_subdirectory` from the AeroAssault64 repo root unless the engine is refactored.

- **Script (repo root, PowerShell):** **`tools/phase6_engine_cmake.ps1`** — **`cmake -S lib/Zelda64Recomp -B build-engine`** (default **Ninja** + **Release**); see **`tools/README.txt`** § Phase 6.
- **Repo-root CMake (VS / presets):** **`CMakeLists.txt`** + **`CMakePresets.json`** — presets **`engine-superbuild-ninja-release`**, **`engine-superbuild-vs2022-release`**, and **`engine-superbuild-ninja-release-no-mm`** configure **`build-root/`**, **`build-root-vs2022/`**, or **`build-root-no-mm/`** and drive **`ExternalProject_Add(zelda64recomp_engine)`** into **`build-engine/`** (same inner **`CMAKE_SOURCE_DIR`** as direct **`-S lib/Zelda64Recomp`**).
- **Vendored recompilers (BUILDING.md § 4):** **`tools/phase6_copy_n64recomp_to_engine.ps1`** — copies **`tools/N64Recomp.exe`** and **`tools/RSPRecomp.exe`** into **`lib/Zelda64Recomp/`** (ignored by submodule **`*.gitignore`** **`*.exe`**).
- **One-shot prep:** **`tools/phase6_setup_windows.ps1`** — junction + copy + **`verify_phase6_layout.py`** (see **`tools/README.txt`**).
- **MM prerequisite audit:** **`make phase6-mm-prereq`** (repo root, needs **`make`** + Python) or **`python3 tools/phase6_mm_engine_prereq_check.py`** — lists gaps vs **`lib/Zelda64Recomp/BUILDING.md`**; **`--strict`** fails if required files are missing.
- **Manual (same layout):**  
  `cmake -S lib/Zelda64Recomp -B build-engine -G Ninja -DCMAKE_BUILD_TYPE=Release`  
  then **`cmake --build build-engine`** (after satisfying **BUILDING.md** prerequisites).

### No Majora's Mask ROM (stub PatchesLib + RSP)

Upstream **`lib/Zelda64Recomp/CMakeLists.txt`** defines **`option(AEROASSAULT64_NO_MM_ROM …)`** (after **`add_subdirectory(…/N64ModernRuntime)`**). When **ON**, **`PatchesLib`** is built from **`tools/phase6_no_mm_engine/*.c`** instead of **`RecompiledPatches/patches.c`** / **`patches_bin.c`**, and **`PatchesBin`** / **`N64Recomp patches.toml`** custom commands are omitted; **`rsp/aspMain.cpp`** and **`rsp/njpgdspMain.cpp`** are replaced by stub **`.cpp`** files in the same **`tools/phase6_no_mm_engine/`** directory.

**`src/main/register_patches.cpp`** still includes **`../../RecompiledPatches/patches_bin.h`** and **`recomp_overlays.inl`** — run from repo root:

  .\tools\phase6_materialize_no_mm_engine_files.ps1

Then configure with **`-DAEROASSAULT64_NO_MM_ROM=ON`**, for example:

  .\tools\phase6_engine_cmake.ps1 -Mode Configure -NoMmRom

Or repo-root **`cmake --preset engine-superbuild-ninja-release-no-mm`** (forwards the flag via root **`CMakeLists.txt`**). This does **not** replace MM game code under **`src/game/`**; it only satisfies CMake/link for the patch blob and RSP sources documented in **BUILDING.md**.

**Windows full link note:** upstream **`CMakeLists.txt`** fetches the **Visual C++** SDL2 development ZIP and links **MSVC-built** **`freetype.lib`** and DXC/D3D12 paths. A **Ninja + MinGW** configure (e.g. WinLibs GCC) can compile most of the tree but the final **`Zelda64Recompiled.exe`** link often fails on those MSVC artifacts. For a full PE link on Windows, prefer **Visual Studio 2022**: repo script **`tools/phase6_engine_cmake_vs2022.ps1`** (**`build-engine-vs2022/`**), or **`cmake -G "Visual Studio 17 2022" -A x64 …`**, or preset **`engine-superbuild-vs2022-release`**, per **`lib/Zelda64Recomp/BUILDING.md`**.

Upstream globs MIPS output only under **`${CMAKE_SOURCE_DIR}/RecompiledFuncs`** — see **`lib/Zelda64Recomp/CMakeLists.txt`** **`file(GLOB FUNC_C_SOURCES ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c)`** (and **`*.cpp`**). This repo’s N64Recomp TOML writes to **repo-root** **`RecompiledFuncs/`** (**`config/aerofighters_assault.n64recomp.toml`** **`output_func_path = "../RecompiledFuncs"`** relative to **`config/`**, per N64Recomp **`src/config.cpp`** path rules in **`tools/README.txt`**).

From repo root (PowerShell), once after clone (or whenever the junction is missing):

  .\tools\phase6_link_recompiledfuncs.ps1

Remove the junction: **`.\tools\phase6_link_recompiledfuncs.ps1 -Remove`**. This does **not** replace **BUILDING.md** steps (RSP **`rsp/*.cpp`**, **`RecompiledPatches/`**, MM **`patches/`** pipeline) — it only aligns **where** the engine CMake looks for **CPU** recomp C sources.

On **Linux / WSL** (no junction), from repo root:

  ln -sfn ../../RecompiledFuncs lib/Zelda64Recomp/RecompiledFuncs

(`samefile` in **`tools/verify_phase6_layout.py`** accepts a symlink to repo-root **`RecompiledFuncs/`**.)

One-time add (already done in this repo; for reference only):

  git submodule add -b dev https://github.com/Mr-Wiseguy/Zelda64Recomp.git lib/Zelda64Recomp
  git submodule update --init --recursive

## AeroAssault64 repo context

- **MIPS ELF + splat:** root **`Makefile`** / **`config/splat.yaml`** — unchanged by the submodule.
- **Static recomp:** this repo already documents **`tools/N64Recomp.exe`** (**`tools/README.txt`**, commit **81213c18…**). Align with whatever revision **Zelda64Recomp** expects for in-tree N64Recomp builds, or keep using the vendored **`tools/`** PE if the engine docs allow it.
- **Game TOML:** **`config/aerofighters_assault.n64recomp.toml`** — wire into the port template the engine provides (see Zelda64Recomp docs and **`Docs/RepoInjests/`** for TOML patterns).
- **Glue / overrides:** **`src/README.txt`**, **`patches/README.txt`**, **`Docs/Workflow.md`** § Phase 6 (including **fork touchpoints** table vs stock MM **`CMakeLists.txt`**).
- **Fork branding / AFA ROM slot:** **`lib/Zelda64Recomp/CMakeLists.txt`** generates **`aero_build_config.h`** (version string, SDL title, optional **`AEROASSAULT64_WITH_AFA_USA`** when **`config/.afa_usa_rom_xxh3`** or **`-DAEROASSAULT64_AFA_ROM_XXH3_HEX`** is set). Repo-root **`CMakeLists.txt`** forwards the same **`-D`** flags into **`ExternalProject_Add`**. See **`tools/compute_aero_rom_xxh3.py`**, **`tools/README.txt`** Phase 5 paragraph on XXH3.

Do not duplicate generated **`RecompiledFuncs/*.c`** into **`lib/`** as separate copies — regenerate under **repo-root** **`RecompiledFuncs/`** only, then use **`tools/phase6_link_recompiledfuncs.ps1`** (junction) or a fork that changes upstream globs.
