Phase 6 — game layer (thin glue)

Per Docs/SystemPrompt.md: engine lives under lib/; this directory holds Aero Fighters
Assault–specific C/C++ that must not be merged into the engine submodule.

Planned contents (after lib/Zelda64Recomp or chosen engine is added):

- Init / ROM load hooks wired to the engine’s recomp runtime.
- Declarations or small wrappers for symbols that bridge RecompiledFuncs/ and lib/.
- No copies of N64Recomp-generated sources — regenerate under RecompiledFuncs/ only.

Next step: add the engine submodule (see lib/README.txt), then follow that repo’s
BUILDING.md and port template for the first CMake target that links RecompiledFuncs/.
