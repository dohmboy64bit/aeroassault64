Phase 4 (MIPS ELF, WSL): from repo root run `make` then `make verify` (see root `Makefile`, `tools/gen_splat_extern_ld.py`, `Docs/Workflow.md`). Requires `splat split` output (`build/aerofighters_assault.ld`, `asm/`) and `binutils-mips-linux-gnu`.

**ELF header spot-check:** `make elf-sanity` (requires `$(ELF)`) greps `mips-linux-gnu-readelf -h` for entry **0x80200050** and a **MIPS** machine line — same entry as `config/symbol_addrs.txt` / `Makefile -e entrypoint`. **`make strict-verify`** runs **`elf-sanity`** after **`verify`**.

**BSS vs `post_data` duplicates:** after `splat split`, build `build/asm/post_data.o` once (`make build/asm/post_data.o`), run `make dedupe-bss` (`tools/dedupe_post_data_bss.py --apply`), then `make LINK_STRICT=1 verify` to link **without** `--allow-multiple-definition`. Shorthand: **`make strict-verify`**. See script docstring and `Makefile` comments.

**Ghidra / splat rodata sync:** `python3 tools/verify_rodata_splits_sync.py` or **`make verify-rodata-sync`** — **`tools/ghidra/Phase3_Closeout_Report.py`** **`RODATA_ROM_SPLITS`** must match **`config/splat.yaml`** **`main`** **`rodata`** ROM starts (see `tools/ghidra/README.txt`). **`python3 tools/verify_splat_makefile_sync.py`** (**`make verify-splat-makefile-sync`**) — **`options.basename`** / **`elf_path`** in **`config/splat.yaml`** must match **`Makefile`** **`ELF`** / **`LDSCRIPT`** stems. **N64Recomp TOML:** **`python3 tools/verify_n64recomp_toml.py`** — parse **`config/aerofighters_assault.n64recomp.toml`**, **`[input]`** keys, mutual exclusion of **`elf_path`** / **`symbols_file_path`** (N64Recomp **`src/main.cpp`**), **`entrypoint`** vs **`config/symbol_addrs.txt`**. **`make check`** runs rodata sync + TOML check + **`py_compile`** **`tools/*.py`** (no ROM; CI — `.github/workflows/repo-check.yml`). Requires **Python 3.11+** (**`tomllib`**).

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

Phase 5 (N64Recomp, Windows)

Prerequisite: WSL (or Linux) **`make strict-verify`** (or at least **`make`**) so **`build/aerofighters_assault.elf`** exists — same artifact as **`config/splat.yaml`** **`elf_path`**.

From repo root in **PowerShell** (first argument is the TOML path; there is no `--help` mode):

  .\tools\N64Recomp.exe .\config\aerofighters_assault.n64recomp.toml

Optional context dump (supported in **`src/main.cpp`** for this tree): append **`--dump-context`** to emit **`dump.toml`** / **`data_dump.toml`** under the current working directory.

**Patches in `config/aerofighters_assault.n64recomp.toml`:** **`[[patches.instruction]]`** turns **`func_8024AE70`**’s **`j func_84001064`** into **`jr $ra` / `nop`** (see **`asm/4BE20.s`** — N64Recomp **`recompilation.cpp`** cannot follow that **`0x8400…`** branch). **`[patches]` `stubs`** skip bodies for handwritten COP0 / **`cache`** routines (**`asm/4BE20.s`**, **`asm/3E750.s`**, **`asm/3FFD0.s`**, **`asm/3DDC0.s`**, **`asm/49090.s`**) and for functions where **`src/analysis.cpp`** fails jump-table sizing (`Failed to determine size of jump table`).

**Regenerate stub list after big `splat split` / ELF changes:** `python tools/n64recomp_stub_until_green.py` (appends **`func_*`** names to **`stubs`** until **`N64Recomp.exe`** exits **0**).

Generated C/C++ must land only under **`RecompiledFuncs/`** (see **`RecompiledFuncs/README.txt`**; large **`funcs_*.c`** / headers are **gitignored** — regenerate locally). Schema reference: N64Recomp **`src/config.cpp`** `[input]` keys; game-style examples live under **`Docs/RepoInjests/`** (e.g. Kirby **`NK4E.toml`** `[input]` block in **`kirby64ret-kirby64recomp-8a5edab282632443.txt`**).
