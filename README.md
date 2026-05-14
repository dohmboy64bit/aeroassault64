# AeroAssault64

N64Recomp-oriented port workspace for **Aero Fighters Assault (USA)**.

- **Rules and phases:** [`Docs/SystemPrompt.md`](Docs/SystemPrompt.md)
- **Phase checklist:** [`Docs/Workflow.md`](Docs/Workflow.md)
- **Layout:** [`Docs/Architecture.md`](Docs/Architecture.md)

ROM path (local): `roms/afa.n64.us.z64` — see `roms/README.txt`.

**Phase 6 (engine):** **`lib/Zelda64Recomp`** is a submodule (**`dev`** branch; pin in **`lib/README.txt`**). Configure with **`tools/phase6_engine_cmake.ps1`** or **`cmake -S lib/Zelda64Recomp -B …`** — see **`lib/README.txt`**, **`tools/README.txt`** § Phase 6, and **`lib/Zelda64Recomp/BUILDING.md`** (upstream targets MM until forked for AFA).
