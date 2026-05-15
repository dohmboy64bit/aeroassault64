Phase 4 (MIPS ELF, WSL): from repo root run `make` then `make verify` (see root `Makefile`, `tools/gen_splat_extern_ld.py`, `Docs/Workflow.md`). Requires `splat split` output (`build/aerofighters_assault.ld`, `asm/`) and `binutils-mips-linux-gnu`.

**ELF header spot-check:** `make elf-sanity` (requires `$(ELF)`) greps `mips-linux-gnu-readelf -h` for entry **0x80200050** and a **MIPS** machine line — same entry as `config/symbol_addrs.txt` / `Makefile -e entrypoint`. **`make strict-verify`** runs **`elf-sanity`** after **`verify`**.

**BSS vs `post_data` duplicates:** after `splat split`, build `build/asm/post_data.o` once (`make build/asm/post_data.o`), run `make dedupe-bss` (`tools/dedupe_post_data_bss.py --apply`), then `make LINK_STRICT=1 verify` to link **without** `--allow-multiple-definition`. Shorthand: **`make strict-verify`**. See script docstring and `Makefile` comments.

**Entry VRAM triple:** **`python3 tools/verify_entrypoint_sync.py`** (**`make verify-entrypoint-sync`**) — **`config/splat.yaml`** **`entry`** segment **`vram`**, **`config/symbol_addrs.txt`** **`entrypoint`**, and **`config/aerofighters_assault.n64recomp.toml`** **`[input].entrypoint`** must match (see **`Makefile`** **`-e entrypoint`**).

**Phase 6 layout:** **`python3 tools/verify_phase6_layout.py`** (**`make verify-phase6-layout`**) — when **`lib/Zelda64Recomp/`** is checked out, **`lib/Zelda64Recomp/RecompiledFuncs`** must be the same directory as repo-root **`RecompiledFuncs/`** (junction or symlink; see **`lib/README.txt`**). Skips if the engine submodule is absent.

**Ghidra / splat rodata sync:** `python3 tools/verify_rodata_splits_sync.py` or **`make verify-rodata-sync`** — **`tools/ghidra/Phase3_Closeout_Report.py`** **`RODATA_ROM_SPLITS`** must match **`config/splat.yaml`** **`main`** **`rodata`** ROM starts (see `tools/ghidra/README.txt`).

**Splat vs Makefile names:** **`python3 tools/verify_splat_makefile_sync.py`** (**`make verify-splat-makefile-sync`**) — **`options.basename`** / **`elf_path`** in **`config/splat.yaml`** must match **`Makefile`** **`ELF`** / **`LDSCRIPT`** stems.

**N64Recomp TOML:** **`python3 tools/verify_n64recomp_toml.py`** — parse **`config/aerofighters_assault.n64recomp.toml`**, **`[input]`** keys, mutual exclusion of **`elf_path`** / **`symbols_file_path`** (N64Recomp **`src/main.cpp`**), **`entrypoint`** vs **`config/symbol_addrs.txt`**.

**`make check`** runs **`verify-splat-makefile-sync`**, **`verify-rodata-sync`**, **`verify-entrypoint-sync`**, **`python3 tools/verify_n64recomp_toml.py`**, **`python3 tools/verify_phase6_layout.py`**, and **`py_compile`** **`tools/*.py`** (no ROM; CI — `.github/workflows/repo-check.yml`). MSVC engine partial build (stub **`RecompiledFuncs`** when no generated **`.c`**) — `.github/workflows/engine-windows.yml`; **`tools/phase6_ci_ensure_recompiledfuncs_stub.ps1`**. Requires **Python 3.11+** (**`tomllib`**).

N64Recomp and RSPRecomp (Windows PE, built from upstream)

Binaries in this folder (tracked in git):

- N64Recomp.exe — main static recompiler (CMake target N64RecompCLI, OUTPUT_NAME N64Recomp per upstream CMakeLists.txt).
- RSPRecomp.exe — RSP microcode recompiler.

Upstream source: https://github.com/Mr-Wiseguy/N64Recomp  
Built commit (shallow clone): 81213c1831fab2521a6a5459c67b63437d67e253  
Toolchain: Visual Studio 2022 MSVC, CMake “Visual Studio 17 2022” -A x64, Release.

Rebuild (from README Building section — https://github.com/Mr-Wiseguy/N64Recomp#building):

  git clone --recurse-submodules https://github.com/Mr-Wiseguy/N64Recomp.git N64Recomp-src
  cd N64Recomp-src
  cmake -S . -B build -G "Visual Studio 17 2022" -A x64
  cmake --build build --config Release --target N64RecompCLI --target RSPRecomp --parallel
  copy build\Release\N64Recomp.exe ..\N64Recomp.exe
  copy build\Release\RSPRecomp.exe ..\RSPRecomp.exe
  cd .. && rd /s /q N64Recomp-src

If `N64Recomp-src` cannot be deleted (file in use), close IDEs/indexers touching that path and remove the folder manually; `tools/N64Recomp-src/` is gitignored.

Ghidra: see `tools/ghidra/README.txt` and `Phase2_Closeout_Report.py` for a Phase 2 ROM/RAM report script.

Zelda64Recomp also documents in-tree builds in Docs/RepoInjests/Zelda64/zelda64recomp-zelda64recomp-8a5edab282632443.txt.

---

Phase 6 (Zelda64Recomp engine, Windows CMake)

Upstream **`lib/Zelda64Recomp`** must be the **CMake source directory** (see **`lib/README.txt`** — **`CMAKE_SOURCE_DIR`** paths in upstream **`CMakeLists.txt`**).

From repo root in **PowerShell** (requires **CMake** on `PATH`; default generator **Ninja**):

  .\tools\phase6_engine_cmake.ps1 -Mode Configure
  .\tools\phase6_engine_cmake.ps1 -Mode Build
  .\tools\phase6_engine_cmake.ps1 -Mode All

**No MM ROM (CMake stubs):** run **`python3 tools/phase6_materialize_no_mm_engine_files.py`** or **`make phase6-materialize-stubs`**, or **`.\tools\phase6_materialize_no_mm_engine_files.ps1`** on Windows, then **`.\tools\phase6_engine_cmake.ps1 -Mode Configure -NoMmRom`** (or **`-Mode All -NoMmRom`**); add **`-CiStub`** when **`RecompiledFuncs/`** has no **`.c`** yet (same stub as CI). Same as passing **`-DAEROASSAULT64_NO_MM_ROM=ON`** to inner **`cmake`** — see **`lib/Zelda64Recomp/CMakeLists.txt`** and **`lib/README.txt`**. **`make verify-phase6-layout`** notes missing **`RecompiledPatches/`** stub headers (informational).

**AFA product (CMake stubs, MM `NO_MM_ROM` off):** same **`phase6_materialize_no_mm_engine_files.py`** / **`make phase6-materialize-stubs`**, then **`.\tools\phase6_engine_cmake.ps1 -Mode Configure -AfaProduct`** (or **`-Mode All -AfaProduct`**). Same as **`-DAEROASSAULT64_AFA_PRODUCT=ON`** — skips MM **`patches.elf`** / **`patches.toml`** like **`NO_MM_ROM`**; see **`lib/Zelda64Recomp/CMakeLists.txt`** **`option(AEROASSAULT64_AFA_PRODUCT …)`** and **`config/afa_rsp/README.txt`**. **Retail patches with AFA hooks:** **`-AfaProduct -AfaRetailPipelines`** (forwards **`AEROASSAULT64_AFA_RETAIL_PIPELINES`**) once engine **`patches.elf`**, **`patches.toml`**, and **`RecompiledPatches/`** exist — **`lib/Zelda64Recomp/AFA_PORT.md`** §2. **MSVC bring-up when `rsp/*.cpp` fails to compile:** add **`-AfaRspForceStubs`** (forwards **`AEROASSAULT64_AFA_RSP_FORCE_STUBS`**) — **`AFA_PORT.md`** §1.

Optional: **`-Generator "Visual Studio 17 2022"`** (use **`-BuildType Release`** with **`cmake --build`** for that generator). Output directory: **`build-engine/`** (gitignored).

**Visual Studio 2022 (MSVC) — recommended for full `Zelda64Recompiled.exe` link:** **`tools/phase6_engine_cmake_vs2022.ps1`** uses **`build-engine-vs2022/`** (do not mix with Ninja’s **`build-engine/`**). Same **`Mode`** / **`-NoMmRom`** / **`-AfaProduct`** / **`-AfaRetailPipelines`** / **`-AfaRspForceStubs`** pattern; optional **`-CiStub`** matches **`tools/phase6_ci_ensure_recompiledfuncs_stub.ps1`** when **`RecompiledFuncs/`** has no generated **`.c`** (see **`.github/workflows/engine-windows.yml`**). Build uses **`--config Release`** by default (override with **`-Configuration`**). Example:

  .\tools\phase6_engine_cmake_vs2022.ps1 -Mode All -NoMmRom
  .\tools\phase6_engine_cmake_vs2022.ps1 -Mode All -AfaProduct
  .\tools\phase6_engine_cmake_vs2022.ps1 -Mode All -AfaProduct -AfaRspForceStubs

**Smoke launch (cwd = engine root, matches `VS_DEBUGGER_WORKING_DIRECTORY`):** **`.\tools\phase6_smoke_engine.ps1`** (optional **`-Seconds`**, **`-Configuration`**, **`-BuildDir`**). With **`-NoMmRom`** or **`-AfaProduct`**, CMake uses **RSP stubs** when **`rsp/aspMain.cpp`** + **`rsp/njpgdspMain.cpp`** are missing, or when **`AEROASSAULT64_AFA_RSP_FORCE_STUBS`** is **ON** (**`-AfaRspForceStubs`** on **`phase6_engine_cmake*.ps1`**) so broken generated **`rsp/*.cpp`** is not linked — see **`BUILDING.md`** §4 and **`AFA_PORT.md`** §1.

**CI / clean clone (no generated `RecompiledFuncs/*.c`):** **`.\tools\phase6_ci_ensure_recompiledfuncs_stub.ps1`** — writes a one-file stub only when the directory has no **`.c`** sources so **`lib/Zelda64Recomp/CMakeLists.txt`** `add_library(RecompiledFuncs …)` is legal. A full **`Zelda64Recompiled.exe`** link still requires real N64Recomp output locally (see **`config/aerofighters_assault.n64recomp.toml`**).

Convenience (runs junction + copy + **`python tools/verify_phase6_layout.py`**). Optional **`-N64RecompMm`** / **`-RspRecomp`**: if **`lib/Zelda64Recomp/mm.us.rev1.rom_uncompressed.z64`** exists, runs **`tools/phase6_n64recomp_mm.ps1`** and/or **`tools/phase6_rsprecomp_engine.ps1`** (N64 first when both). Otherwise skips with a message.

  .\tools\phase6_setup_windows.ps1
  .\tools\phase6_setup_windows.ps1 -N64RecompMm
  .\tools\phase6_setup_windows.ps1 -RspRecomp
  .\tools\phase6_setup_windows.ps1 -N64RecompMm -RspRecomp

**Repo-root CMake (optional):** **`CMakeLists.txt`** uses **`ExternalProject_Add(zelda64recomp_engine)`** so the inner project keeps **`lib/Zelda64Recomp`** as **`CMAKE_SOURCE_DIR`** (same reason direct **`cmake -S lib/Zelda64Recomp`** is used elsewhere). Presets (**`CMakePresets.json`** schema v3 — [cmake-presets(7)](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html)):

  cmake --preset engine-superbuild-ninja-release
  cmake --build --preset engine-superbuild-ninja-release

No-MM preset (forwards **`AEROASSAULT64_NO_MM_ROM`** to the engine; materialize **`RecompiledPatches/`** stubs first — **`python3 tools/phase6_materialize_no_mm_engine_files.py`** or **`make phase6-materialize-stubs`**):

  cmake --preset engine-superbuild-ninja-release-no-mm
  cmake --build --preset engine-superbuild-ninja-release-no-mm

AFA-product presets (forward **`AEROASSAULT64_AFA_PRODUCT`**; same materialize step as no-MM — **`phase6_materialize_no_mm_engine_files.py`**):

  cmake --preset engine-superbuild-ninja-release-afa-product
  cmake --build --preset engine-superbuild-ninja-release-afa-product

  cmake --preset engine-superbuild-vs2022-release-afa-product
  cmake --build --preset engine-superbuild-vs2022-release-afa-product

AFA-product **+ retail `PatchesLib`** (forward **`AEROASSAULT64_AFA_RETAIL_PIPELINES`** as well; requires real **`patches.elf`** / **`patches.toml`** / **`RecompiledPatches/`** — **`lib/Zelda64Recomp/AFA_PORT.md`** §2):

  cmake --preset engine-superbuild-ninja-release-afa-product-retail
  cmake --build --preset engine-superbuild-ninja-release-afa-product-retail

  cmake --preset engine-superbuild-vs2022-release-afa-product-retail
  cmake --build --preset engine-superbuild-vs2022-release-afa-product-retail

Visual Studio: open the **AeroAssault64** repo folder, pick preset **`engine-superbuild-vs2022-release`** or **`engine-superbuild-vs2022-release-afa-product`**, then build target **`zelda64recomp_engine`**. Outer dirs **`build-root/`**, **`build-root-vs2022/`**, **`build-root-afa-product/`**, **`build-root-vs2022-afa-product/`**, **`build-root-afa-product-retail/`**, **`build-root-vs2022-afa-product-retail/`**; inner **`build-engine/`** (see **`.gitignore`**).

**RecompiledFuncs path:** upstream CMake globs only under **`lib/Zelda64Recomp/RecompiledFuncs/`**; this repo’s TOML emits to **repo-root** **`RecompiledFuncs/`**. Run once after clone:

  .\tools\phase6_link_recompiledfuncs.ps1

(**`-Remove`** drops the junction.) Rationale: **`lib/Zelda64Recomp/CMakeLists.txt`** **`file(GLOB … ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c)`**; **`config/aerofighters_assault.n64recomp.toml`** **`output_func_path`** — see **`lib/README.txt`**.

**BUILDING.md § 4 (PEs in engine root):** copy **`tools/N64Recomp.exe`** and **`tools/RSPRecomp.exe`** next to upstream **`us.rev1.toml`**:

  .\tools\phase6_copy_n64recomp_to_engine.ps1

Optional: **`-WhatIf`** lists destinations only. Same binaries as Phase 5 (**`tools/README.txt`**); not a substitute for MM ROM / TOML runs.

**MM CPU recomp (Majora's Mask, BUILDING.md section 4):** **`.\tools\phase6_n64recomp_mm.ps1`** runs **`N64Recomp.exe us.rev1.toml`** in **`lib/Zelda64Recomp/`** after **`mm.us.rev1.rom_uncompressed.z64`** is there (section 3). Run **before** **`phase6_rsprecomp_engine.ps1`** when following upstream order. Optional **`-CopyTools`** / **`-WhatIf`**. Makefile: **`make phase6-n64recomp-mm`**.

**RSP C++ (Majora's Mask, BUILDING.md §4):** after **`mm.us.rev1.rom_uncompressed.z64`** is in **`lib/Zelda64Recomp/`** (§3), run **`.\tools\phase6_rsprecomp_engine.ps1`** — invokes **`RSPRecomp.exe`** on **`aspMain.us.rev1.toml`** and **`njpgdspMain.us.rev1.toml`**, producing **`lib/Zelda64Recomp/rsp/aspMain.cpp`** and **`njpgdspMain.cpp`** (gitignored upstream). Optional **`-CopyTools`** runs **`phase6_copy_n64recomp_to_engine.ps1`** first; **`-WhatIf`** prints intent only.

**RSP C++ (AFA USA, `AFA_PORT.md` §1):** engine-root **`aspMain.afa.us.toml`** / **`njpgdspMain.afa.us.toml`** mirror **`config/afa_rsp/*.template.toml`** (committed **`text_offset`/`text_size`** for SHA1 in **`config/splat.yaml`**; re-derive with **`python tools/rsprecomp_scan_offsets.py`**, **`tools/rsprecomp_left_edge.py`**, **`tools/rsprecomp_find_njpg2.py`**, **`tools/rsprecomp_fine_njpg.py`** if your ROM differs). Place ROM (**`afa.n64.us.z64`** by default next to TOMLs), then **`.\tools\phase6_rsprecomp_afa.ps1`** (optional **`-RomPath`**, **`-CopyTools`**, **`-WhatIf`**; **`-SkipOffsetGuard`** only if you are not using **`0x0`** placeholders). Makefile: **`make phase6-rsprecomp-afa`**. CMake links these outputs whenever both **`rsp/*.cpp`** exist — see **`lib/Zelda64Recomp/CMakeLists.txt`** **`_AERO_PATCH_RSP_STUBS`** branch and **`config/afa_rsp/README.txt`**. PyGhidra **`tools/ghidra/RSPRecomp_Confirm_Findings.py`** can cross-check **asp** and (when **`IMEM_BOOTSTRAP_NJPG_BE_U32`** is filled) **njpgdsp** ROM prefixes against those templates.

**AFA full static recomp (CPU + RSP, one script):** after WSL **`make strict-verify`**, from repo root **`.\tools\phase6_full_recomp_afa.ps1`** — runs **`phase6_link_recompiledfuncs.ps1`**, **`phase5_run_aero_n64recomp.ps1`**, **`phase6_rsprecomp_afa.ps1`** (see **`lib/Zelda64Recomp/AFA_PORT.md`** opening section). **`make phase6-full-recomp-afa-win`**. Does **not** build **`patches.elf`** / **`RecompiledPatches/`**; for that use **`AFA_RETAIL_PIPELINES`** presets and **`config/afa_engine/README.txt`**.

**MIPS vs RSP (Capstone, host — no Ghidra):** **`python tools/rsp_rom_capstone_mips.py --offset 0x4BE20`** — MIPS32 big-endian disasm at a cart file offset (**`pip install capstone`**, in **`requirements.txt`**). **`python tools/rsp_rom_capstone_mips.py --afa-usa-hints`** — three labeled blocks at **0x4BE20** (MIPS **`asm/4BE20.s`**), **0x4DAB0** / **0x4C830** (**`config/afa_rsp/*.template.toml`** **`text_offset`**). **`--offsets 0x4BE20,0x4DAB0`** — multiple offsets in one run. Optional **`--dump-hex N`**, **`--be-words N`**, **`--count N`**. Same **Capstone** **`CS_ARCH_MIPS`** / **`CS_MODE_MIPS32 | CS_MODE_BIG_ENDIAN`** as **`tools/ghidra/RSPRecomp_Confirm_Findings.py`** ([Capstone Python](https://www.capstone-engine.org/lang_python.html)).

Optional: **`make phase6-mm-prereq`** (**`python3 tools/phase6_mm_engine_prereq_check.py`**) — lists missing **Majora's Mask** engine files per **`lib/Zelda64Recomp/BUILDING.md`** (ROM, generated **`rsp/*.cpp`**, **`RecompiledPatches/`**). Append **`--strict`** to exit non-zero if anything required is missing. Not run by **`make check`**.

Follow **`lib/Zelda64Recomp/BUILDING.md`** for ROM extraction, nested submodules, and RT64 prerequisites before expecting configure to succeed.

---

Phase 5 (N64Recomp, Windows)

Prerequisite: WSL (or Linux) **`make strict-verify`** (or at least **`make`**) so **`build/aerofighters_assault.elf`** exists — same artifact as **`config/splat.yaml`** **`elf_path`**.

From repo root in **PowerShell** (first argument is the TOML path; there is no `--help` mode):

  .\tools\N64Recomp.exe .\config\aerofighters_assault.n64recomp.toml

Makefile (Windows): **`make phase5-aero-n64recomp-win`** runs **`tools/phase5_run_aero_n64recomp.ps1`** (same checks as that script; needs **`build/aerofighters_assault.elf`**).

Optional context dump (supported in **`src/main.cpp`** for this tree): append **`--dump-context`** to emit **`dump.toml`** / **`data_dump.toml`** under the current working directory.

**Patches in `config/aerofighters_assault.n64recomp.toml`:** **`[[patches.instruction]]`** turns **`func_8024AE70`**’s **`j func_84001064`** into **`jr $ra` / `nop`** (see **`asm/4BE20.s`** — N64Recomp **`recompilation.cpp`** cannot follow that **`0x8400…`** branch). **`[patches]` `stubs`** skip bodies for handwritten COP0 / **`cache`** routines (**`asm/4BE20.s`**, **`asm/3E750.s`**, **`asm/3FFD0.s`**, **`asm/3DDC0.s`**, **`asm/49090.s`**) and for functions where **`src/analysis.cpp`** fails jump-table sizing (`Failed to determine size of jump table`).

**Regenerate stub list after big `splat split` / ELF changes:** `python tools/n64recomp_stub_until_green.py` (appends **`func_*`** names to **`stubs`** until **`N64Recomp.exe`** exits **0**).

**AFA USA ROM hash (optional second `GameEntry` in the engine):** **`lib/Zelda64Recomp`** validates ROMs with **XXH3-64** over the full file after byteswap normalize — same as **`lib/N64ModernRuntime/librecomp/src/recomp.cpp`** (**`check_hash` / `XXH3_64bits`**). Run **`pip install xxhash`** then **`python tools/compute_aero_rom_xxh3.py path/to/rom.z64`** (writes **`config/.afa_usa_rom_xxh3`**, gitignored — see **`config/.afa_usa_rom_xxh3.example`**). Re-configure CMake, or pass **`-DAEROASSAULT64_AFA_ROM_XXH3_HEX=...`** / **`tools/phase6_engine_cmake_vs2022.ps1 -AfaRomXxh3Hex ...`**.

Generated C/C++ must land only under **`RecompiledFuncs/`** (see **`RecompiledFuncs/README.txt`**; large **`funcs_*.c`** / headers are **gitignored** — regenerate locally). Schema reference: N64Recomp **`src/config.cpp`** `[input]` keys; game-style examples live under **`Docs/RepoInjests/`** (e.g. Kirby **`NK4E.toml`** `[input]` block in **`kirby64ret-kirby64recomp-8a5edab282632443.txt`**).
