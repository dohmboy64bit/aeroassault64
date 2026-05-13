Phase 4 (MIPS ELF, WSL): from repo root run `make` then `make verify` (see root `Makefile`, `tools/gen_splat_extern_ld.py`, `Docs/Workflow.md`). Requires `splat split` output (`build/aerofighters_assault.ld`, `asm/`) and `binutils-mips-linux-gnu`.

**BSS vs `post_data` duplicates:** after `splat split`, build `build/asm/post_data.o` once (`make build/asm/post_data.o`), run `make dedupe-bss` (`tools/dedupe_post_data_bss.py --apply`), then `make LINK_STRICT=1` to link **without** `--allow-multiple-definition`. See script docstring and `Makefile` comments.

---

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
