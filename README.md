# AeroAssault64

N64Recomp-oriented port workspace for **Aero Fighters Assault (USA)**.

- **Rules and phases:** [`Docs/SystemPrompt.md`](Docs/SystemPrompt.md)
- **Phase checklist:** [`Docs/Workflow.md`](Docs/Workflow.md)
- **Layout:** [`Docs/Architecture.md`](Docs/Architecture.md)

ROM path (local): `roms/afa.n64.us.z64` — see `roms/README.txt`.

**Phase 6 (engine):** **`lib/Zelda64Recomp`** submodule (**`dev`**; pin in **`lib/README.txt`**). Configure the engine with **`tools/phase6_engine_cmake.ps1`**, **`cmake -S lib/Zelda64Recomp -B build-engine`**, or **repo-root** **`CMakeLists.txt`** + **`CMakePresets.json`** (**`engine-superbuild-*`** presets — **`ExternalProject_Add`**, see **`Docs/Workflow.md`**). Prep: **`lib/README.txt`**, **`tools/README.txt`** § Phase 6, **`lib/Zelda64Recomp/BUILDING.md`** (MM until an AFA fork).
