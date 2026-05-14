Phase 6 — game layer (thin glue)

Per Docs/SystemPrompt.md: engine lives under lib/; this directory holds Aero Fighters
Assault–specific C/C++ that must not be merged into the engine submodule.

Planned contents (after lib/Zelda64Recomp or chosen engine is added):

- Init / ROM load hooks wired to the engine’s recomp runtime.
- Declarations or small wrappers for symbols that bridge RecompiledFuncs/ and lib/.
- No copies of N64Recomp-generated sources — regenerate under RecompiledFuncs/ only.

Next step: engine submodule (**`lib/README.txt`**). Before **`tools/phase6_engine_cmake.ps1`**, run **`tools/phase6_link_recompiledfuncs.ps1`** so upstream CMake sees repo-root **`RecompiledFuncs/`**; see **`Docs/Workflow.md`** § **Phase 6 fork touchpoints** for what to replace in **`lib/Zelda64Recomp/`** (MM **`us.rev1.toml`**, **`patches/`**, **`src/game`**, RSP, etc.) when moving beyond stock **BUILDING.md**.
