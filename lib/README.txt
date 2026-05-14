Engine submodule (**tracked**)

Upstream: https://github.com/Mr-Wiseguy/Zelda64Recomp  
**Branch tracked:** `dev` (see **`.gitmodules`**). **Pinned commit (this repo):** `ab677e76615e5e47b3b26c822ca426485752ac77` (`ab677e7` short).

After a fresh clone from repo root:

  git submodule update --init --recursive

Then open **`lib/Zelda64Recomp/BUILDING.md`** for RT64, nested submodules, dependencies, and the Windows CMake / Visual Studio flow. Upstream **BUILDING.md** describes **Majora's Mask** (decompressed ROM, `us.rev1.toml`, in-tree N64Recomp/RSPRecomp); **Aero Fighters Assault** still needs a **fork or in-tree adaptation** (TOML, assets, `RecompiledFuncs/` layout, glue under **`src/`**).

### Configure / build from this repo (Windows)

Upstream **`lib/Zelda64Recomp/CMakeLists.txt`** uses **`CMAKE_SOURCE_DIR`** for **`lib/rt64`**, **`RecompiledFuncs/`**, etc., so the engine must be configured with **that directory as the CMake source root** — not by `add_subdirectory` from the AeroAssault64 repo root unless the engine is refactored.

- **Script (repo root, PowerShell):** **`tools/phase6_engine_cmake.ps1`** — **`cmake -S lib/Zelda64Recomp -B build-engine`** (default **Ninja** + **Release**); see **`tools/README.txt`** § Phase 6.
- **Manual (same layout):**  
  `cmake -S lib/Zelda64Recomp -B build-engine -G Ninja -DCMAKE_BUILD_TYPE=Release`  
  then **`cmake --build build-engine`** (after satisfying **BUILDING.md** prerequisites).

One-time add (already done in this repo; for reference only):

  git submodule add -b dev https://github.com/Mr-Wiseguy/Zelda64Recomp.git lib/Zelda64Recomp
  git submodule update --init --recursive

## AeroAssault64 repo context

- **MIPS ELF + splat:** root **`Makefile`** / **`config/splat.yaml`** — unchanged by the submodule.
- **Static recomp:** this repo already documents **`tools/N64Recomp.exe`** (**`tools/README.txt`**, commit **81213c18…**). Align with whatever revision **Zelda64Recomp** expects for in-tree N64Recomp builds, or keep using the vendored **`tools/`** PE if the engine docs allow it.
- **Game TOML:** **`config/aerofighters_assault.n64recomp.toml`** — wire into the port template the engine provides (see Zelda64Recomp docs and **`Docs/RepoInjests/`** for TOML patterns).
- **Glue / overrides:** **`src/README.txt`**, **`patches/README.txt`**, **`Docs/Workflow.md`** § Phase 6.

Do not copy generated **`RecompiledFuncs/*.c`** into **`lib/`** — regenerate under **`RecompiledFuncs/`** only.
