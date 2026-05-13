Phase 6 — RECOMP_PATCH and runtime overrides

Per Docs/SystemPrompt.md: overrides and hooks that are not suitable for editing
RecompiledFuncs/ belong here (or in config/ for N64Recomp TOML patches).

Reference patterns:

- Docs/RepoInjests/ — ingested recomp TOMLs with [[patches.hook]] and
  [[patches.instruction]] (e.g. Kirby NK4E.toml, Dino Planet snippets).
- N64Recomp upstream: src/main.cpp (patch application), src/config.cpp ([patches] schema).

Bootstrap / hardware paths already partially handled in
config/aerofighters_assault.n64recomp.toml (stubs + instruction patches). Move logic
here when the engine expects RECOMP_PATCH–style game files instead of TOML-only patches.
