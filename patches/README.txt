Phase 6 — RECOMP_PATCH and runtime overrides

Per Docs/SystemPrompt.md: overrides and hooks that are not suitable for editing
RecompiledFuncs/ belong here (or in config/ for N64Recomp TOML patches).

## Not the same folder as the engine’s `patches/`

This directory is at the **AeroAssault64 repo root** (`patches/` next to `config/`, `src/`).

Upstream **Zelda64Recomp** uses a different tree: **`lib/Zelda64Recomp/patches/`** — there the
**`Makefile`** builds **`patches.elf`**, and **`lib/Zelda64Recomp/CMakeLists.txt`** runs
**`./N64Recomp patches.toml`** from the **engine** root to emit **`RecompiledPatches/patches.c`**
and related outputs (see **`Docs/Workflow.md`** § Phase 6 fork touchpoints).

Do not confuse the two when copying patch workflows from MM.

Reference patterns:

- Docs/RepoInjests/ — ingested recomp TOMLs with [[patches.hook]] and
  [[patches.instruction]] (e.g. Kirby NK4E.toml, Dino Planet snippets).
- N64Recomp upstream: src/main.cpp (patch application), src/config.cpp ([patches] schema).

Bootstrap / hardware paths already partially handled in
config/aerofighters_assault.n64recomp.toml (stubs + instruction patches). Move logic
here when the engine expects RECOMP_PATCH–style game files instead of TOML-only patches.
