# Architecture

High-level layout matches `Docs/SystemPrompt.md`:

- **`lib/`** — Reusable engine (Zelda64Recomp + RT64 via submodule when added). Must not depend on game code.
- **`src/`** — Thin glue and Aero Fighters Assault–specific logic.
- **`RecompiledFuncs/`** — N64Recomp output only (do not edit by hand).
- **`patches/`** — `RECOMP_PATCH` hooks and overrides.
- **`config/`** — `splat.yaml`, symbol lists, and future linker/recomp config.
- **`assets/`** — Extracted or converted game assets.
- **`tools/`** — Scripts and third-party binaries (e.g. N64Recomp).
- **`roms/`** — Local ROM copies (gitignored).

Fill this document with dependency diagrams and data flow once the engine submodule exists and the first ELF is produced.
