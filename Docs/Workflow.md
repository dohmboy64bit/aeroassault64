# Workflow

This file tracks **phase order** from `Docs/SystemPrompt.md`. Do not skip phases.

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Environment setup | **Complete** |
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
- **LLVM/Clang (Windows):** `winget` package **LLVM.LLVM** is installed; **`C:\Program Files\LLVM\bin\clang.exe`** reports **clang version 22.1.5** (target **x86_64-pc-windows-msvc**). Add that directory to **PATH** (user or system) if a new PowerShell session does not resolve `clang`.
- **N64Recomp / RSPRecomp (Windows):** `tools/N64Recomp.exe` and `tools/RSPRecomp.exe` built from [Mr-Wiseguy/N64Recomp](https://github.com/Mr-Wiseguy/N64Recomp) @ **81213c1831fab2521a6a5459c67b63437d67e253** (MSVC Release). Run `.\tools\N64Recomp.exe` from PowerShell with a `.toml` per upstream docs.

### Shared reference docs (read early)

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)

### Windows (host)

- [x] Install **Visual Studio** (Desktop development with C++) for MSVC and the debugger used on the final PE. *(VS 2022 Community + VC tools detected.)*
- [x] Install **CMake** (3.20+ unless engine docs say otherwise). *(4.2.1 on PATH.)*
- [x] Optional: **LLVM/Clang** for Windows if you plan to match a Clang-based engine workflow. *(**LLVM.LLVM** via winget; `C:\Program Files\LLVM\bin\clang.exe` **22.1.5** — ensure that `bin` dir is on PATH if `clang` is not found.)*
- [x] Obtain **N64Recomp** for this project (release or build); place the binary under `tools/` or add it to `PATH`, and record the exact path and version in this file when known. *(**tools/N64Recomp.exe** + **tools/RSPRecomp.exe**; built from N64Recomp @ `81213c1831fab2521a6a5459c67b63437d67e253` — see host log and `tools/README.txt`.)*
- [ ] Clone or submodule **Zelda64Recomp** (or chosen engine) into `lib/` when you are ready — not blocked on ROM, but blocked on picking upstream revision. *(See `lib/README.txt` for the submodule command. Deferred to Phase 6 — not required to close Phase 1.)*

### WSL (splat / MIPS / ELF)

- [x] Install a current **WSL2** distro (Ubuntu is common).
- [x] In WSL: Python 3.x + **splat** per [splat upstream](https://github.com/ethteck/splat) (pin a version once the first successful split is recorded here). *(Pinned in `requirements.txt`; smoke split recorded above.)*
- [x] In WSL: **MIPS Binutils** (`mips-linux-gnu-as`, `mips-linux-gnu-ld`) for assembling splat `.s` output and linking to ELF. Ubuntu: **`binutils-mips-linux-gnu`**. **Note:** [splat Quickstart](https://github.com/ethteck/splat/wiki/Quickstart) treats full reassembly as out of scope; `splat split` does **not** require the assembler on PATH. The [General Workflow](https://github.com/ethteck/splat/wiki/General-Workflow) wiki discusses **`mips-linux-gnu-as`** (e.g. o32 float register aliases vs `macro.inc`).
- [ ] In WSL (**optional / skipped for now**): **`mips-linux-gnu-gcc`** via **`gcc-mips-linux-gnu`** — only needed to compile **C** to MIPS objects. **Skipped on Ubuntu 26.04** (package not in archive); **not required** for Phase 1. Use **`binutils-mips-linux-gnu`** (`mips-linux-gnu-as` / `mips-linux-gnu-ld`) for asm → ELF. Revisit with **Ubuntu 24.04** WSL or Docker if you later need MIPS GCC.

  **If you see `E: Unable to locate package gcc-mips-linux-gnu`:** your WSL image may be **Ubuntu 26.04 (resolute)** or another suite where that metapackage is **not published yet** (this repo verified **no** `gcc*mips*` package names in `apt-cache` on 26.04 while **`binutils-mips-linux-gnu`** still exists). The same metapackage **is** in **Ubuntu 24.04 LTS (noble)** [universe](https://packages.ubuntu.com/noble/gcc-mips-linux-gnu). **Workarounds:** (1) add a second WSL distro **Ubuntu 24.04** from `wsl.exe --list --online` / Store and install `gcc-mips-linux-gnu` there; or (2) use a **Docker** (or Podman) **`ubuntu:24.04`** container for MIPS GCC builds. Avoid force-installing **noble** `.deb` files on **26.04** (ABI/dependency mismatch).

- [x] Confirm you can run `wsl` from PowerShell and share the repo path (`/mnt/e/AeroAssault64` or your drive letter).

### ROM (Phase 1 prep only; analysis is Phase 2)

- [x] Legally obtain the **Aero Fighters Assault (USA)** ROM.
- [x] Copy it to `roms/afa.n64.us.z64` (see `roms/README.txt`).
- [x] Compute **SHA1** and write it into `config/splat.yaml` (`sha1:` field). Paste the same value here for audit:

  `SHA1 (USA, from local Get-FileHash): 6742f67d7d2639072e186d240237be1c662cb25a` — also stored in `config/splat.yaml`; verify against No-Intro / your dump source.

### Repo hygiene

- [x] `git` initialized at repo root; commits exist on `master` (continue committing as tooling lands).

### Phase 1 exit criteria

- **Phase 1 is closed when:** VS + CMake + Clang (optional) on Windows; WSL + Python + **splat split** verified; ROM + SHA1; **MIPS binutils** (`mips-linux-gnu-as` / `mips-linux-gnu-ld`) for future asm/ELF work; and **where N64Recomp will come from** is documented (`tools/README.txt`). **MIPS GCC** is optional and was **waived** for this host (Ubuntu 26.04 has no `gcc-mips-linux-gnu`; binutils-only is enough until you compile C for MIPS).
- **Before Phase 5:** use **`tools/N64Recomp.exe`** (and **`tools/RSPRecomp.exe`** when RSP recompilation is needed) with your game `.toml`; refresh binaries if you bump N64Recomp revision.
- **Before Phase 6:** add engine submodule under `lib/` per `lib/README.txt` when you pick a revision.

---

## Later phases (placeholders)

- **Phase 2:** Ghidra session with project owner; confirm boot/main VRAM and entry before locking `config/splat.yaml`.
- **Phase 3–4:** Run splat from repo root (or documented cwd); fix segment bounds; generate ELF.
- **Phase 5:** Add N64Recomp TOML; emit only under `RecompiledFuncs/`.
- **Phase 6–8:** Integrate `lib/`, wire `src/` and `patches/`, CMake PE, VS debugger — see `Docs/Debugging.md`.
