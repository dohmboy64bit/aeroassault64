# Workflow

This file tracks **phase order** from `Docs/SystemPrompt.md`. Do not skip phases.

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Environment setup | **In progress** |
| 2 | ROM + Ghidra | Not started |
| 3 | `splat.yaml` / split | Draft in `config/splat.yaml` |
| 4 | ELF (WSL / splat) | Not started |
| 5 | N64Recomp | Not started |
| 6 | Engine + patches | Not started |
| 7 | CMake → Windows PE | Not started |
| 8 | Test / stabilize | Not started |

---

## Phase 1 — Environment setup (checklist)

Complete these on your machine; check boxes as you go. **Do not invent tool versions** — use the versions required by the splat and Zelda64Recomp repos when you add them.

### Host verification log (recorded when scaffolding landed)

- **Windows:** `cmake` reported **4.2.1** on the machine used for setup (Kitware build). Re-run `cmake --version` after upgrades.
- **WSL:** `wsl --version` reported **2.6.3**; default distro `python3` was **3.14.4**. Pin splat/MIPS versions separately per upstream docs.

### Shared reference docs (read early)

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)

### Windows (host)

- [ ] Install **Visual Studio** (Desktop development with C++) for MSVC and the debugger used on the final PE.
- [ ] Install **CMake** (3.20+ unless engine docs say otherwise).
- [ ] Optional: **LLVM/Clang** for Windows if you plan to match a Clang-based engine workflow.
- [ ] Obtain **N64Recomp** for this project (release or build); place the binary under `tools/` or add it to `PATH`, and record the exact path and version in this file when known.
- [ ] Clone or submodule **Zelda64Recomp** (or chosen engine) into `lib/` when you are ready — not blocked on ROM, but blocked on picking upstream revision.

### WSL (splat / MIPS / ELF)

- [ ] Install a current **WSL2** distro (Ubuntu is common).
- [ ] In WSL: Python 3.x + **splat** per [splat upstream](https://github.com/ethteck/splat) (pin a version once the first successful split is recorded here).
- [ ] In WSL: **MIPS GNU toolchain** (or the exact toolchain your splat/README prescribes) for any asm compile steps the decomp uses.
- [ ] Confirm you can run `wsl` from PowerShell and share the repo path (`/mnt/e/AeroAssault64` or your drive letter).

### ROM (Phase 1 prep only; analysis is Phase 2)

- [ ] Legally obtain the **Aero Fighters Assault (USA)** ROM.
- [ ] Copy it to `roms/afa.n64.us.z64` (see `roms/README.txt`).
- [ ] Compute **SHA1** and write it into `config/splat.yaml` (`sha1:` field). Paste the same value here for audit:

  `SHA1 (USA, from local Get-FileHash): 6742f67d7d2639072e186d240237be1c662cb25a` — also stored in `config/splat.yaml`; verify against No-Intro / your dump source.

### Repo hygiene

- [ ] `git` initialized at repo root; first commit after Phase 1 checklist is satisfied enough to share the tree.

### Phase 1 exit criteria

- Windows can build **nothing game-specific yet** — success means: VS + CMake ready, WSL + Python ready, ROM path + SHA1 recorded, and you know where N64Recomp will live.
- Update **Phase status** above to mark Phase 1 complete when exit criteria are met.

---

## Later phases (placeholders)

- **Phase 2:** Ghidra session with project owner; confirm boot/main VRAM and entry before locking `config/splat.yaml`.
- **Phase 3–4:** Run splat from repo root (or documented cwd); fix segment bounds; generate ELF.
- **Phase 5:** Add N64Recomp TOML; emit only under `RecompiledFuncs/`.
- **Phase 6–8:** Integrate `lib/`, wire `src/` and `patches/`, CMake PE, VS debugger — see `Docs/Debugging.md`.
