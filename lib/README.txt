Engine submodule (not bundled in-repo)

Preferred upstream: https://github.com/Mr-Wiseguy/Zelda64Recomp  
Upstream build guide: https://github.com/Mr-Wiseguy/Zelda64Recomp/blob/main/BUILDING.md (path may differ slightly by branch — open **BUILDING.md** in the tree you pin).

## Add the engine (pick a commit first)

From repo root:

  git submodule add https://github.com/Mr-Wiseguy/Zelda64Recomp.git lib/Zelda64Recomp
  cd lib/Zelda64Recomp
  git checkout <pin-revision>   # record this SHA in a commit message / Docs/Workflow.md Phase 6
  cd ../..
  git submodule update --init --recursive

Then follow **BUILDING.md** for RT64, third-party submodules, and the Windows CMake/VS flow.

## AeroAssault64 repo context

- **MIPS ELF + splat:** root **`Makefile`** / **`config/splat.yaml`** — unchanged by the submodule.
- **Static recomp:** this repo already documents **`tools/N64Recomp.exe`** (**`tools/README.txt`**, commit **81213c18…**). Align with whatever revision **Zelda64Recomp** expects for in-tree N64Recomp builds, or keep using the vendored **`tools/`** PE if the engine docs allow it.
- **Game TOML:** **`config/aerofighters_assault.n64recomp.toml`** — wire into the port template the engine provides (see Zelda64Recomp docs and **`Docs/RepoInjests/`** for TOML patterns).
- **Glue / overrides:** **`src/README.txt`**, **`patches/README.txt`**, **`Docs/Workflow.md`** § Phase 6.

Do not copy generated **`RecompiledFuncs/*.c`** into **`lib/`** — regenerate under **`RecompiledFuncs/`** only.
