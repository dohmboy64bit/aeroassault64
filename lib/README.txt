Engine submodule (not bundled in-repo)

Preferred upstream: https://github.com/Mr-Wiseguy/Zelda64Recomp  
After cloning, open **`BUILDING.md`** or **`README.md`** at the submodule root (exact filename varies by upstream branch) for RT64, dependencies, and the Windows CMake / Visual Studio flow.

From repo root:

  git submodule add https://github.com/Mr-Wiseguy/Zelda64Recomp.git lib/Zelda64Recomp
  cd lib/Zelda64Recomp
  git checkout <pin-revision>   # record this SHA in a commit message / Docs/Workflow.md Phase 6
  cd ../..
  git submodule update --init --recursive

Then follow **BUILDING.md** / **README.md** at the submodule root for RT64, third-party submodules, and the Windows CMake/VS flow.

## AeroAssault64 repo context

- **MIPS ELF + splat:** root **`Makefile`** / **`config/splat.yaml`** — unchanged by the submodule.
- **Static recomp:** this repo already documents **`tools/N64Recomp.exe`** (**`tools/README.txt`**, commit **81213c18…**). Align with whatever revision **Zelda64Recomp** expects for in-tree N64Recomp builds, or keep using the vendored **`tools/`** PE if the engine docs allow it.
- **Game TOML:** **`config/aerofighters_assault.n64recomp.toml`** — wire into the port template the engine provides (see Zelda64Recomp docs and **`Docs/RepoInjests/`** for TOML patterns).
- **Glue / overrides:** **`src/README.txt`**, **`patches/README.txt`**, **`Docs/Workflow.md`** § Phase 6.

Do not copy generated **`RecompiledFuncs/*.c`** into **`lib/`** — regenerate under **`RecompiledFuncs/`** only.
