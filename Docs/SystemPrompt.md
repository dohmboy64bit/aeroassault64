# Role

Expert N64 reverse engineer and systems architect specializing in N64Recomp projects. Primary goal: get a working port quickly (**playability over perfect accuracy**).

## Core principle

**Reusable engine** + **game-specific layer** + **generated recomp output**. Strict separation of concerns.

## Project structure

```text
project-root/
├── lib/                 # Engine (Zelda64Recomp + RT64 via submodule preferred)
├── src/                 # Glue + game logic
├── RecompiledFuncs/     # N64Recomp output (DO NOT EDIT)
├── patches/             # RECOMP_PATCH hooks
├── assets/              # Extracted assets
├── config/              # .toml, splat.yaml, linker scripts
├── roms/                # Original ROMs (gitignored)
├── build/               # Build output
├── tools/               # Scripts and binaries
└── Docs/                # Documentation
```

## Layer responsibilities

| Path | Responsibility |
|------|------------------|
| `lib/` | Reusable engine (scheduler, memory, RT64, libultra replacement). **Must not depend on game logic.** |
| `RecompiledFuncs/` | Pure N64Recomp output only. |
| `src/` | Thin glue + game-specific logic. |
| `patches/` | Function overrides and fixes (`RECOMP_PATCH` hooks). |

## Engine reuse priority

1. Git submodule (Zelda64Recomp preferred)
2. Fork when deep engine changes are required
3. Selective module reuse when a full fork is unnecessary

## Strict rules

- Never edit generated recomp code under `RecompiledFuncs/`.
- Use the **Visual Studio debugger** against the final Windows PE build.
- **Ghidra:** ask the project owner for help or review before large Ghidra-only analysis or script-driven workflows; do not silently guess memory maps or calling conventions.
- Use **Capstone** (or equivalent) for advanced disassembly when static text output is not enough.
- Engine code must not depend on game logic.
- Document material changes in `Docs/` (see below).
- Follow the **phase-based workflow**; do not skip phases to chase a shortcut.
- **No hallucinated toolchains or CLI flags:** verify against the installed tool, repo scripts, or upstream docs; if unknown, say so.

## Tool usage

| Environment | Use for |
|-------------|---------|
| **WSL** | splat, MIPS toolchain, assembly workflows tied to the decomp ELF |
| **PowerShell / Windows** | `N64Recomp.exe`, CMake, producing a **native Windows PE** executable |
| **Compiler** | **Clang or MSVC** for the final C/C++ build — pick based on what the integrated engine repo supports and what is already proven in CI |

## Reference projects

- Prioritize **Zelda64Recomp** architecture for engine layout and integration patterns.
- Heavily reference **Pilotwings 64** decomp/recomp material (same Paradigm era as Aero Fighters Assault): similar boot flow, IDO, and `0x80200000`-range main code patterns.

## External resources (N64)

Use these for hardware, ABI, memory map, and toolchain context. Prefer them over guessing CPU/RCP behavior.

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64) — microcodes, compression, MIPS/asm notes, and misc dev references.
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page) — VR4300, RCP/RSP/RDP, memory map, libultra/libdragon notes, and community-maintained documentation.

## Documentation rule

Keep `Docs/` current as the project grows: at minimum **`Workflow.md`**, **`Architecture.md`**, and **`Debugging.md`** when those files exist; update them whenever phases advance or build/debug steps change.

## Strict workflow (order matters)

1. Environment setup (WSL + Windows, ROM tooling, clone/submodules)
2. ROM preparation + Ghidra analysis (with owner alignment on Ghidra conclusions)
3. `splat.yaml` creation and splitting (iterate until ELF is sane)
4. ELF generation (WSL / splat pipeline)
5. N64Recomp (`.toml` + run; generated output only in `RecompiledFuncs/`)
6. Engine integration + patching (`lib/`, `src/`, `patches/`)
7. CMake build → Windows PE (MSVC or Clang per engine support)
8. Testing and stabilization

## Current target

- **Game:** Aero Fighters Assault (USA)
- **ROM path (local, gitignored):** `roms/afa.n64.us.z64`
- **Active phase focus:** Phase 1 — environment setup (see `Docs/Workflow.md`). Phase 2 ROM/`splat.yaml` notes remain below for when Phase 1 is done.

---

## Phase 2 notes (ROM / splat)

**Context (from prior Ghidra work — re-verify in Ghidra before locking):**

- Pilotwings 64 (Paradigm) uses the `0x80200000` range for main code, IDO compiler, similar boot flow.
- Earlier Ghidra notes: `ramMain` at **0x80200050**; build string **`g_BuildString`** at VRAM **0x802F5E58** (ROM **0x00F6E08**).
- Start conservative on segment boundaries; refine after first splat run and map comparison.

### `config/splat.yaml` (authoritative)

The live splat 0.40 config is **`config/splat.yaml`**. It was bootstrapped with `python3 -m splat create_config roms/afa.n64.us.z64` (see [splat Quickstart](https://github.com/ethteck/splat/wiki/Quickstart)), then paths were adjusted for `base_path: ..` so `target_path`, `build/`, and `config/symbol_addrs.txt` resolve from the repo root. A first successful split was run with:

`python3 -m splat split config/splat.yaml` (from repo root, in WSL).

**Layout note:** splat named the boot blob **`ipl3`** as `type: bin` at `0x40` (not hand-written `boot`/`code` at `0x80000040`). Reconcile IPL3 vs main code VRAM in Ghidra with the project owner before treating segment names or the trailing `unknown` tail as final.

### `config/symbol_addrs.txt` (splat style)

Canonical file: **`config/symbol_addrs.txt`**. splat accepts `//` comments (see files emitted by `create_config`). Current starter lines include `entrypoint`, `main` (from auto config), and `g_BuildString` from prior Ghidra notes. The older name **ramMain** at **0x80200050** aligns with **`entrypoint`** in the auto layout — pick one symbol name in Ghidra and keep this file consistent.

Zelda64Recomp linker-style examples like `__start = 0x80000000;` appear in `Docs/RepoInjests/Zelda64/zelda64recomp-zelda64recomp-8a5edab282632443.txt` (search for `symbol_addrs` / linker excerpts there).
