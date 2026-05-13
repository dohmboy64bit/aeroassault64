# Workflow

This file tracks **phase order** from `Docs/SystemPrompt.md`. Do not skip phases.

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Environment setup | **In progress** |
| 2 | ROM + Ghidra | Not started |
| 3 | `splat.yaml` / split | First WSL `splat split` OK (see host log) |
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
- **splat:** `splat 0.40.0` (spimdisasm **1.40.3**) in WSL; pin in `requirements.txt` (from [splat README Installing](https://github.com/ethteck/splat/blob/main/README.md): `splat64[mips]>=0.40.0,<1.0.0`).
- **Visual Studio:** **2022 Community** with VC tools present at `C:\Program Files\Microsoft Visual Studio\2022\Community` (`vswhere` with `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`).
- **WSL repo path:** `/mnt/e/AeroAssault64` reachable from default distro.
- **ROM on disk:** `roms/afa.n64.us.z64` present; SHA1 **6742F67D7D2639072E186D240237BE1C662CB25A** matches `config/splat.yaml`.
- **splat split smoke test (2026-05-13):** from repo root in WSL, `python3 -m splat split config/splat.yaml` completed (emits `asm/`, `build/`, `assets/*.bin`, `include/` — see `.gitignore` for what stays out of git).

### Shared reference docs (read early)

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)

### Windows (host)

- [x] Install **Visual Studio** (Desktop development with C++) for MSVC and the debugger used on the final PE. *(VS 2022 Community + VC tools detected.)*
- [x] Install **CMake** (3.20+ unless engine docs say otherwise). *(4.2.1 on PATH.)*
- [ ] Optional: **LLVM/Clang** for Windows if you plan to match a Clang-based engine workflow. *(Not on PATH in the last check.)*
- [ ] Obtain **N64Recomp** for this project (release or build); place the binary under `tools/` or add it to `PATH`, and record the exact path and version in this file when known. *(See `tools/README.txt` — upstream [Mr-Wiseguy/N64Recomp](https://github.com/Mr-Wiseguy/N64Recomp); Zelda ingest documents in-tree CMake build of `lib/N64Recomp`.)*
- [ ] Clone or submodule **Zelda64Recomp** (or chosen engine) into `lib/` when you are ready — not blocked on ROM, but blocked on picking upstream revision. *(See `lib/README.txt` for the submodule command.)*

### WSL (splat / MIPS / ELF)

- [x] Install a current **WSL2** distro (Ubuntu is common).
- [x] In WSL: Python 3.x + **splat** per [splat upstream](https://github.com/ethteck/splat) (pin a version once the first successful split is recorded here). *(Pinned in `requirements.txt`; smoke split recorded above.)*
- [ ] In WSL: **MIPS GNU / mips64-elf toolchain** for assembling emitted `.s` / ELF rebuild. **Note:** [splat Quickstart](https://github.com/ethteck/splat/wiki/Quickstart) treats reassembly as out of scope; `splat split` does **not** require `mips64-elf-gcc` on PATH. Install the toolchain your eventual IDO/GNU pipeline expects **before** trying to compile split output.
- [x] Confirm you can run `wsl` from PowerShell and share the repo path (`/mnt/e/AeroAssault64` or your drive letter).

### ROM (Phase 1 prep only; analysis is Phase 2)

- [x] Legally obtain the **Aero Fighters Assault (USA)** ROM.
- [x] Copy it to `roms/afa.n64.us.z64` (see `roms/README.txt`).
- [x] Compute **SHA1** and write it into `config/splat.yaml` (`sha1:` field). Paste the same value here for audit:

  `SHA1 (USA, from local Get-FileHash): 6742f67d7d2639072e186d240237be1c662cb25a` — also stored in `config/splat.yaml`; verify against No-Intro / your dump source.

### Repo hygiene

- [x] `git` initialized at repo root; commits exist on `master` (continue committing as tooling lands).

### Phase 1 exit criteria

- Windows can build **nothing game-specific yet** — success means: VS + CMake ready, WSL + Python + splat split verified, ROM path + SHA1 recorded, and you know where N64Recomp will live (`tools/README.txt`).
- **Still open before declaring Phase 1 complete:** install or build **N64Recomp** (and optionally add **Zelda64Recomp** as a submodule), and install a **MIPS cross compiler** when you are ready to compile asm (not required for splat split alone).
- Update **Phase status** above to mark Phase 1 complete when exit criteria are met.

---

## Later phases (placeholders)

- **Phase 2:** Ghidra session with project owner; confirm boot/main VRAM and entry before locking `config/splat.yaml`.
- **Phase 3–4:** Run splat from repo root (or documented cwd); fix segment bounds; generate ELF.
- **Phase 5:** Add N64Recomp TOML; emit only under `RecompiledFuncs/`.
- **Phase 6–8:** Integrate `lib/`, wire `src/` and `patches/`, CMake PE, VS debugger — see `Docs/Debugging.md`.
