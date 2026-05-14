# Workflow

This file tracks **phase order** from `Docs/SystemPrompt.md`. Do not skip phases.

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Environment setup | **Complete** |
| 2 | ROM + Ghidra | **Complete** |
| 3 | `splat.yaml` / split | **Complete** — **`rodata`** subdivided **0x52B90…0x57A60** per **splat 0.40.0** split stdout (extra nops @ VRAM **0x80251BE0**); **`asm`** splits ROM **`< 0x4C050`**; **`post_data`** single **`asm`** from **`0x57D20`** (tail splits still rejected: VRAM order vs **`bss`**); **`splat split`** OK; **`post_data`** vs **`800000.bss`** handled via **`tools/dedupe_post_data_bss.py`** + **`LINK_STRICT`** (see **What to remember**). *Optional follow-up:* Ghidra xrefs to validate **`rodata`** boundaries (**`Docs/Workflow.md`** “Still to do”). |
| 4 | ELF (WSL / splat) | **Complete (smoke)** — **`make` / `make verify`** / **`make strict-verify`** (now runs **`make elf-sanity`**); **`build/aerofighters_assault.elf`** matches **`config/splat.yaml`** **`elf_path`**. Re-run **`make strict-verify`** after each **`splat split`**. |
| 5 | N64Recomp | **Smoke-complete** — **`config/aerofighters_assault.n64recomp.toml`** drives **`tools/N64Recomp.exe`** to exit **0** (outputs under **`RecompiledFuncs/`**, gitignored except **`README.txt`**). Hand-tuned **`[[patches.instruction]]`** + **`stubs`** (COP0 / **`cache`** / jump-table limits per N64Recomp **`src/main.cpp`**, **`recompilation.cpp`**, **`analysis.cpp`**); extend with **`python tools/n64recomp_stub_until_green.py`** after **`splat split`**. |
| 6 | Engine + patches | **In progress** — **Scaffolding complete:** Aero fork CMake (**`AEROASSAULT64_*`**, **`AFA_PRODUCT`**, presets, CI **`engine-windows`** with **`-AfaProduct`**), stub Patches/RSP (**`tools/phase6_materialize_no_mm_engine_files.py`** / **`.ps1`**), Phase 5 **`RecompiledFuncs`** path (**`config/aerofighters_assault.n64recomp.toml`**), smoke docs (**`Docs/Debugging.md`**). **Full AFA retail fork still open** — replace MM **`src/game/`**, RSP, engine **`patches/`** / real **`RecompiledPatches/`**, **`assets/`** (see Phase 6 checklist **full retail** row and fork touchpoints table). |
| 7 | CMake → Windows PE | **Smoke-complete (host)** — MSVC **Release** link of **`Zelda64Recompiled.exe`** via **`tools/phase6_engine_cmake_vs2022.ps1`** (**`build-engine-vs2022/`**); **`tools/phase6_smoke_engine.ps1`**. CI builds **`RecompiledFuncs`** + **`PatchesLib`** only (no generated CPU **`.c`** on the runner — **`tools/phase6_ci_ensure_recompiledfuncs_stub.ps1`**); see **`.github/workflows/engine-windows.yml`**. |
| 8 | Test / stabilize | **Automation baseline complete** — **`.github/workflows/repo-check.yml`** (ROM-free Python checks + **`py_compile`**) + **`engine-windows`** on push/PR. **Gameplay / ROM-load correctness / full-fork QA** still open (manual or future test matrix). |

---

## What to remember (`splat split` → dedupe → link)

- **`asm/`** is in **`.gitignore`** (splat output). **`splat split`** regenerates **`asm/data/800000.bss.s`** and the rest of **`asm/`**; **`tools/dedupe_post_data_bss.py`** changes are **not preserved** across a split until you run dedupe again.
- **Strict link (no `--allow-multiple-definition`):** after **`splat split`**, build **`build/asm/post_data.o`** (**`make build/asm/post_data.o`**), run **`make dedupe-bss`**, then **`make LINK_STRICT=1 verify`**. Shorthand: **`make strict-verify`**. Default **`LINK_STRICT=0`** in the **`Makefile`** keeps **`--allow-multiple-definition`** so **`make verify`** still works before dedupe on a clean tree.
- **References:** **`tools/dedupe_post_data_bss.py`**, **`tools/README.txt`**, **`Makefile`** (`dedupe-bss`, **`strict-verify`**, **`LINK_STRICT`**, **`check`**).
- **ROM-free validation:** **`make check`** — runs **`verify-splat-makefile-sync`**, **`verify-rodata-sync`**, **`verify-entrypoint-sync`** (splat **`entry`** **`vram`** / **`symbol_addrs.txt`** / N64Recomp **`[input].entrypoint`**), **`python3 tools/verify_n64recomp_toml.py`**, **`python3 tools/verify_phase6_layout.py`** (when **`lib/Zelda64Recomp`** exists, **`RecompiledFuncs/`** bridge must not split; see **`lib/README.txt`**), and **`py_compile`** on **`tools/*.py`**. Same Python checks run in **GitHub Actions** (`.github/workflows/repo-check.yml` on **`master`** / **`main`**). MSVC configure + **`RecompiledFuncs`** / **`PatchesLib`** compile (stub CPU output when needed) run in **`.github/workflows/engine-windows.yml`**. Requires **Python 3.11+** on the runner / host (**`tomllib`**). **`make help`** lists common targets.

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
- **splat split smoke test (2026-05-13):** from repo root in WSL, `python3 -m splat split config/splat.yaml` completed (emits `asm/`, `build/`, `assets/*.bin`, `include/` — see `.gitignore` for what stays out of git). **Update (same day):** re-run after Phase 3 `rodata` + `asm` subsegment expansion — still **exit 0** (splat **0.40.0**).
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
- [x] Clone or submodule **Zelda64Recomp** into **`lib/Zelda64Recomp`** (tracked **`dev`**; see **`.gitmodules`** and **`lib/README.txt`**). *(Submodule is present for Phase 6; pick commits per fork notes there.)*

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

## Phase 2 — Ghidra first (ROM truth)

Do this **before** changing `config/splat.yaml` for “final” layout or investing in ELF link. Per `Docs/SystemPrompt.md`, align conclusions with the project owner; do not treat guessed maps as authoritative.

### Baseline (repo — use in Ghidra)

| Item | Value |
|------|--------|
| ROM file (local) | `roms/afa.n64.us.z64` |
| SHA1 | `6742f67d7d2639072e186d240237be1c662cb25a` (must match `config/splat.yaml`) |
| Prior notes (re-verify) | VRAM **0x80200050** — entry / `ramMain`; **`g_BuildString`** VRAM **0x802F5E58**, ROM **0x00F6E08** (`Docs/SystemPrompt.md`) |
| splat draft (reconcile) | `config/splat.yaml` — `ipl3` @ ROM **0x40** (`bin`); **`entry`** ROM **0x1000** VRAM **0x80200050** (`hasm`); **`main`** from ROM **0x1050**; **`data`** @ **0x4C050**; **`rodata`** @ **0x52B90**; **`post_data`** `asm` @ **0x57D20**–**0x7FFFFF**; **`bss`** linker VMA **0x8027F050**; **`[0x800000]`** end marker |

### ROM ↔ splat map (use while in Ghidra)

These offsets come from the **committed** `config/splat.yaml` (splat **0.40** layout). If your editor shows an older hand-written `boot` / `main` @ `0x001FF000` tree, **refresh from disk** — generated `build/aerofighters_assault.ld` and `asm/*.s` must agree with this file.

| Segment (splat `name`) | ROM start | VRAM (from yaml / asm) | Notes |
|------------------------|-----------|-------------------------|--------|
| `header` | **0x0** | (header blob) | 0x40-byte cart header |
| `ipl3` | **0x40** | *(bin only in split — no asm)* | IPL3 cartridge blob; decide in Ghidra how you want to map or skip it |
| `entry` | **0x1000** | **0x80200050** | `hasm` → see `asm/1000.s` (`entrypoint`) |
| `main` (`.text`, split) | **0x1050** … **0x4BEF0** (many **`asm`** files) | **0x802000A0** + linear offset from **`0x1050`** | See `asm/*.s` named by ROM start (splat file-split hints). |
| `main` (`data`) | **0x4C050** | `rom_to_ram(0x4C050)` | `asm/data/4C050.data.s` |
| `main` (`rodata`) | **0x52B90** | `rom_to_ram(0x52B90)` | `asm/data/52B90.rodata.s`; splat may warn this block is referenced from many `.text` files (expected). |
| `main` (`post_data` `.text`) | **0x57D20** … **0x7FFFFF** | **`0x80256D70`** at ROM **0x57D20** (same linear rule) | Single `post_data.s` — see Phase 3 for why tail is not split further. |
| `main` (`bss`, linker) | *(none in ROM)* | **`0x8027F050`** | **`bss_size: 0x853E0`** — linker bookkeeping vs runtime **`ramMain`** clear from **`0x80256D70`** (Phase 2 table + Phase 3 note). |
| end marker | **0x800000** | — | Full ROM size |

**Reading splat asm for cross-check:** In `asm/1000.s`, each disassembled line uses the form `/* <ROM> <VRAM> <word> */` — e.g. `/* 1000 80200050 3C088025 */` means ROM **0x1000**, VRAM **0x80200050**. Use that to sanity-check that your Ghidra image’s ROM offset ↔ address mapping matches splat before you trust auto-analysis.

**Symbols:** `config/symbol_addrs.txt` lists `entrypoint`, `main`, and `g_BuildString` (see [splat wiki — Adding symbols](https://github.com/ethteck/splat/wiki/Adding-Symbols)). Rename in Ghidra to match whatever you keep in that file.

### Ghidra session checklist

Work in a **non-shared** Ghidra project so imports and memory blocks stay under your control.

1. **Import** the same bytes as splat: `roms/afa.n64.us.z64` (verify size/SHA1 if Ghidra offers it).
2. **Loader / image base:** use whatever N64/ND loader or workflow you already trust for Paradigm-era games; if unsure, stop and pick a loader with the project owner (`Docs/SystemPrompt.md` Ghidra rule) — do not assume a default Ghidra import is correct for this ROM.
3. **Sanity — entry:** At VRAM **0x80200050**, confirm code looks like a real entry (not obvious garbage). Label **`entrypoint`** (or your chosen name) and note ROM offset Ghidra shows for that address.
4. **Sanity — build string:** Confirm **`g_BuildString`** (or equivalent) at VRAM **0x802F5E58** / ROM **0x00F6E08** reads as a plausible build/version string; if it does not, record what *is* there — the old note may be wrong.
5. **IPL3 / boot (ROM 0x40):** Decide what lives in **0x40–0xFFF** (before `entry` at **0x1000** in current splat): raw IPL3 only vs mixed code; whether splat’s **`ipl3` `bin`** segment is correct or should become **`code`/`asm`** with a chosen VRAM (owner decision). **Update (user Ghidra):** cart IPL disassembles as **`bootMain`** in **`ram:a4000040`–`ram:a4000fff`** — that range is **RSP DMEM** on real hardware (**0xA4000000**–**0xA4000FFF**; see [N64brew — memory map](https://n64brew.dev/wiki/Memory_map)). It is **not** the same address space as main game (**0x80000000** / **0x8020…**). Keeping splat’s **`ipl3` `type: bin`** for ROM **0x40** is still appropriate for a **game-only** ELF/recomp pipeline unless you explicitly want IPL3 emitted as asm in another memory model.
6. **Main code region:** Bound the bulk of **.text** (start/end VRAM and ROM). Compare to splat’s **`main`** subsegments (asm / data / bss split at **0x4C050** etc.); note where **.rodata** and **.bss** really begin if different from splat’s first-pass hints.
7. **Tail of ROM:** From the last defined segment to **0x800000** — what is it (more code, overlays, assets, padding)? This drives the final **`bin`** / named segments vs one big unknown.
8. **Write-down:** Fill the table below in this file (or paste into chat / issue) so Phase 3 edits to `config/splat.yaml` are traceable.
9. **RSPRecomp `text_offset` hints (Phase 6 engine):** If memory blocks match Phase 2 (**`.rom`**, **`.ram`**), run **`tools/ghidra/Find_RSP_Microcode_ROM_Hints.py`** in Ghidra (PyGhidra — same **`support/pyghidraRun.bat`** as **`Phase2_Closeout_Report.py`**). It prints a **histogram of ROM file offsets** referenced from RAM (operand xrefs + **`lui`/`addiu`** ROM pointers). Also run **`tools/ghidra/RSP_LibUltra_And_IMEM_Scan.py`** for symbol-name matches, **`0x04001000`**-style immediates, ASCII **`osSpTask`** / **`OSTask`**, and Paradigm **`uv*`** rodata hints when SDK strings are stripped. Use both scripts to **short-list** microcode blob locations; **confirm** in the Listing (DMA / **`OSTask`** / graphics init) before copying values into **`config/afa_rsp/*.template.toml`** — see **`lib/Zelda64Recomp/AFA_PORT.md`** §1. Optional cross-title sanity check: import **Pilotwings 64 USA** the same way and re-run both scripts — links and a **non-AFA** RSPRecomp example TOML are in **`Docs/RepoInjests/Pilotwings/README.txt`**.

### Ghidra findings log (fill in after session)

*Evidence snapshot (user): Search Memory → String **"Aero Fighters Assault"** in `afa.n64.us.z64`.*

| Question | Your answer (VRAM / ROM / notes) |
|----------|----------------------------------|
| Confirmed entry / init address | **Ghidra `.ram`:** **`ramMain()`** @ **`80200050`**, marked **Entry Point**. Prologue: **`lui t0, 0x8025`** + **`addiu t0, 0x6d70`** → **`t0 = 0x80256D70`**; loop clears words from that address (BSS zero); then **`jr t2 => FUN_80231150`**. So **entry = `0x80200050`**, **first real game routine = `0x80231150`**, **BSS clear base = `0x80256D70`** — matches **`config/symbol_addrs.txt`** (`entrypoint`, `main`) and **`config/splat.yaml`** (`entry` VRAM **`0x80200050`**, `main` follows). **Phase 3 linker note:** splat **`main`** **`bss`** subsegment is **`vram: 0x8027F050`** (see Phase 3 section) so **`post_data`** `.text` at **`0x80256D70`** does not overlap **`.bss`** in the generated script; **`bss_size: 0x853E0`** keeps the same nominal **`.bss`** span end as the old **`0x306C0`** layout. Ghidra block span **`80200050`–`809ff04f`** is the analyzer’s RAM window (not necessarily full hardware RAM). |
| `g_BuildString` (or correction) | **VRAM `802f5e58`:** `ds "Aero Fighters Assault v0.93 built on %s..."` — confirms prior **`g_BuildString`** @ **0x802F5E58** in `config/symbol_addrs.txt` / `Docs/SystemPrompt.md`. **Also listed @ `b00f6e08`** in Ghidra (same string); treat as ROM/file-backed view of the same data — cross-check against documented ROM **0x00F6E08** and your loader’s block naming. |
| ROM header / `.rom` cart image | **Confirmed by `tools/ghidra/Phase2_Closeout_Report.py` (Ghidra 12 / PyGhidra):** **`Magic`** `80371240`, **`Load_Address`** `0x80200050`, **`Release_Offset`** `0x00001447`, **`CRC1/CRC2`** `1B598BF1` / `ECA29B45`, title **`AERO FIGHTERS ASSAUL…`** @ **`0x20`**. **`Release_Offset`** is **not** the same numeric value as splat’s **`entry` @ ROM `0x1000`** — interpret **`0x0C`** using [N64brew — ROM](https://n64brew.dev/wiki/ROM) (or your loader’s field names); do not rename the field without that doc. |
| IPL3 region ROM **0x40**–**0xFFF** description | **Ghidra `.boot`:** `bootMain()` at **`a4000040`**–**`a4000fff`** (block comment *ROM bootloader*). Opcodes are real MIPS: **COP0** (`mtc0`), **RI/MI/RDRAM** MMIO (`0xA3F0…`, `0xA3F8…`), stack in DMEM, **`jal`** to helpers, loops with **`cache`**, ends **`jr t4 => TLB_REFILL`**. That matches **IPL3 / PIF bootstrap** running in **SP DMEM** (**`0xA4000000`** region), not KSEG0 game RAM. **Cart ROM `0x40`–`0xFFF`** is this blob; splat **`ipl3` `bin`** is still the right shape for splitting **game** code at **`0x1000`**. |
| Main `.text` ROM/VRAM range | *(still refine bounds / rodata — Ghidra confirms entry handoff only)* **VRAM:** entry stub **`0x80200050`**, transfer to **`main` @ `0x80231150`** per `jr` above. **ROM:** splat still has **`entry`** @ **`0x1000`**, **`main` .text** from **`0x1050`** (`config/splat.yaml`). |
| `.data` / `.rodata` / `.bss` boundaries (best effort) | **Script @ ROM `0x4C050`:** first word **`0x00000000`** (no code unit in `.rom` — consistent with **BSS / padding / template** in cart image, not proof that splat’s **`data`** split is wrong). **RAM:** **`g_BuildString`** is **`ds`** at **`0x802F5E58`**; **`0x80256D70`** shows **`undefined4`** matching first stack pattern from **`ramMain`** (BSS region). **Rodata vs `.data`:** still refine in Ghidra by following **xrefs from code** into **`.rom`** if you need a sharper split than **`0x4C050`**. |
| ROM **0x57D20**+ until **0x800000** | **At `b0057d20` (= ROM `0x57D20`):** bytes **`27 bd ff 98`** decode to MIPS **`addiu sp, sp, -0x68`** (I-type `addiu` / stack frame). Following **`af bf 00 1c`**, **`af a4 00 68`**, **`af a5 00 6c`** are consistent with **`sw`** prologue stores. So this is **live MIPS `.text`**, not padding — Ghidra shows **`??`** only because **`.rom`** has not created a **code** unit there yet. **Bytes just above (`b0057d14`–`b0057d1f`):** still ambiguous (could be tail **data**, **padding**, or **mixed**). **Repo status:** `config/splat.yaml` has **`[0x57D20, asm, post_data]`** under **`main`** (see [splat General Workflow](https://github.com/ethteck/splat/wiki/General-Workflow)). |
| Disagreements vs current `config/splat.yaml` | **IPL3 / entry / main / header CRCs:** aligned with Ghidra + script. **`Release_Offset` `0x1447`:** document meaning from ROM wiki — **do not equate to `0x1000`** without that doc. **`bss`** linker VMA vs **`ramMain`** clear base: documented in Phase 3 (not a hardware disagreement — a splat linker choice). |

### Phase 2 exit

- [x] Findings log completed; **Phase2_Closeout_Report.py** run in Ghidra 12 (PyGhidra) matches header, RAM symbols, and ROM **`0x57D20`** / **`0x4C050`** checks above.
- [x] **Phase status:** ROM + Ghidra → **Complete**; next is **Phase 3–4** (`config/splat.yaml` + ELF).

---

## Phase 3 — `splat.yaml` and `splat split`

**Goal:** match the ROM layout to Ghidra-backed facts while keeping splat’s linker model self-consistent ([splat General Workflow](https://github.com/ethteck/splat/wiki/General-Workflow), [Quickstart](https://github.com/ethteck/splat/wiki/Quickstart)).

### Done in repo (2026-05-13)

- **`config/splat.yaml`:** tail ROM **`0x57D20+`** is **`[0x57D20, asm, post_data]`** under **`main`** (MIPS at **`b0057d20`**, Ghidra Phase 2).
- **`rodata`:** single **`[0x52B90, rodata]`** → **29** additional **`rodata`** subsegments (**`0x52BC0`** … **`0x57A60`**) from **`python3 -m splat split`** stdout (“Segment 52B90…” / file split suggestions). **`0x58080+`** `asm` hints in that block were **not** applied (would duplicate existing **`main`** `asm` list). Re-run split + **`make`** after yaml change: **exit 0**.
- **`asm` file splits:** all addresses splat printed for segment **`1050`** with ROM **`< 0x4C050`** are listed as separate **`asm`** subsegments (same heuristic as splat stdout). **Not** applied to ROM **`≥ 0x57D20`:** each subsegment’s **`vram_start`** is **`rom_to_ram(start)`** on the parent segment (see splat **`segtypes/common/code.py`**, splat **0.40.0** — `vram = self.get_most_parent().rom_to_ram(start)` when building subsegments). Splitting **`post_data`** at e.g. **`0x7DE0B0`** gives a **text** **`vram_start`** around **`0x809DD100`**, which is **greater** than explicit **`bss`** at **`0x8027F050`**, so splat errors with **ascending vram order** (`code.py` check at **`segment.vram_start < prev_vram`**). Keeping **one** **`post_data`** `asm` keeps **`bss`** after **`0x80256D70`** text as intended for this linker hack.
- **BSS / VRAM:** unchanged from prior Phase 3 write-up — **`bss`** @ **`0x8027F050`**, **`bss_size: 0x853E0`**, vs Ghidra runtime clear from **`0x80256D70`**.
- **Verification:** `python -m splat split config/splat.yaml` and `python3 -m splat split config/splat.yaml` from repo root completed with exit code **0** on **Windows (PowerShell)** and **WSL** respectively (**2026-05-13**); splat **0.40.0** / spimdisasm **1.40.3**. **Ghidra:** run **`tools/ghidra/Phase3_Closeout_Report.py`** (PyGhidra; see **`tools/ghidra/README.txt`**) and paste conclusions into the Phase 3 findings / Workflow table — keep **`RODATA_ROM_SPLITS`** in that script aligned with **`config/splat.yaml`**.
- **`Phase3_Closeout_Report.py` (user run, PyGhidra):** **B** — xrefs to **`.rom`** rodata starts are **0** (expected: consumers use **`.ram`** KSEG0). **C** — tail **`.rom`** listing mix (use extra NOTE when **`.ram`** at **`0x80256D70`** is already code). **D** — **ROM 0x57D20** MIPS prologue. **E** — **`0x8027F050`**: often unlabeled **`??`**. **F** — **`0x80256D70`**: use **`Phase3_Ensure_PostData_Function.py`** until **`FUN_80256d70`** / real instruction appears in **`.ram`**. **G** — high VRAM **`func_*`** candidates vs **`??`** in Ghidra vs splat **`post_data`** / **`800000.bss`** (see **`tools/dedupe_post_data_bss.py`** + **`LINK_STRICT`**).

### Phase 3 closeout checklist

- [x] Reconcile **`post_data`** vs **`800000.bss`**: **`tools/dedupe_post_data_bss.py`** (uses **`mips-linux-gnu-readelf -s`** on **`post_data.o`** per binutils **readelf(1)**, same line shape as **`tools/gen_splat_extern_ld.py`**) strips **`nonmatching`+`glabel`/`dlabel`+`.space`** / **`.comm`** in **`asm/data/800000.bss.s`** when the symbol is already GLOBAL in **`post_data.o`**. **`make dedupe-bss`** then **`make LINK_STRICT=1 verify`** completes without **`--allow-multiple-definition`** (verified **2026-05-13** WSL). Re-run dedupe after each **`splat split`** (regenerated **`800000.bss.s`**). **`asm/data/57D20.bss.s`** stays excluded from the link per **`Makefile`**.
- [ ] *(Optional — does not block calling Phase 3 complete.)* Validate **`rodata`** split boundaries in Ghidra (xrefs from **`.text`** into **`.rom`** **0x52B90–0x57D20**); adjust **`config/splat.yaml`** if a boundary cuts a table. **CI-style drift check:** **`python3 tools/verify_rodata_splits_sync.py`** or **`make verify-rodata-sync`** — ensures **`tools/ghidra/Phase3_Closeout_Report.py`** **`RODATA_ROM_SPLITS`** matches splat **`main`** **`rodata`** lines.

**Completed from this backlog (2026-05-13):** subdivided **`rodata`** per splat stdout (**`0x52BC0`** … **`0x57A60`**); smoke **`make`** / **`make verify`** still green after re-split.

---

## Phase 4 — ELF (WSL / splat)

**Goal:** a reproducible **MIPS o32** ELF at **`build/aerofighters_assault.elf`** that matches splat’s **`build/aerofighters_assault.ld`**, with a **strict** link path (no **`--allow-multiple-definition`**) ready for **N64Recomp** (Phase 5). See [splat General Workflow](https://github.com/ethteck/splat/wiki/General-Workflow).

### Prerequisites

- **WSL** (or Linux) with **`binutils-mips-linux-gnu`** on **`PATH`** (`mips-linux-gnu-as`, **`mips-linux-gnu-ld`**, **`mips-linux-gnu-readelf`**).
- **ROM** at **`roms/afa.n64.us.z64`** (gitignored) and **`python3 -m splat split config/splat.yaml`** so **`asm/`**, **`build/*.ld`**, **`assets/ipl3.bin`**, and **`include/`** exist.

### Commands (repo root, WSL)

| Step | Command |
|------|---------|
| Regenerate asm / ld | **`make split`** or **`python3 -m splat split config/splat.yaml`** |
| Default smoke ELF | **`make`** then **`make verify`** (**`LINK_STRICT=0`** — permissive **`ld`**) |
| Strict link + verify + entry check | **`make strict-verify`** ( **`dedupe-bss`**, **`LINK_STRICT=1` `verify`**, then **`elf-sanity`**) — same as **What to remember** |
| Entry / MIPS header only | **`make elf-sanity`** (requires existing **`$(ELF)`**) |

### Phase 4 checklist

- [x] Root **`Makefile`**: assemble **`asm/**/*.s`**, **`post_data`** **`pref`→`nop`**, **`build/splat_extern.ld`** from **`tools/gen_splat_extern_ld.py`**, link **`-e entrypoint`** **`--oformat elf32-tradbigmips`**.
- [x] **`make verify`** reads **`mips-linux-gnu-readelf -h`** (Type / Machine / Entry / Flags).
- [x] **`tools/dedupe_post_data_bss.py`** + **`make dedupe-bss`**; **`LINK_STRICT=1`** link verified (**2026-05-13**).
- [x] Run **`make strict-verify`** after each **`splat split`** before trusting multiply-defined cleanliness (regenerates **`800000.bss.s`** — see **What to remember**). *Discipline verified on repo tree (**2026-05-13**, WSL): **`make strict-verify`** exit **0** on **`build/aerofighters_assault.elf`**. Re-run after every future **`splat split`**. (**`strict-verify`** ends with **`make elf-sanity`** — entry **80200050** + MIPS **readelf** line.)*
- [x] **ELF sanity:** **`make elf-sanity`** (after **`$(ELF)`** exists) checks **`mips-linux-gnu-readelf -h`** for entry **0x80200050** and a **MIPS** machine string — same entry as **`config/symbol_addrs.txt`** / **`Makefile`** **`-e entrypoint`**. Optional **`readelf -S`** / **`nm`** spot-checks vs Ghidra remain manual.
- [x] **Handoff to Phase 5:** **`config/splat.yaml`** **`elf_path: build/aerofighters_assault.elf`** — game TOML is **`config/aerofighters_assault.n64recomp.toml`** for **`tools/N64Recomp.exe`** (see **`tools/README.txt`** Phase 5 and N64Recomp **`src/config.cpp`** @ commit pinned in **`tools/README.txt`**); output only under **`RecompiledFuncs/`**.

### Phase 4 exit criteria

Phase **4** is **closed at smoke level** when: **`make strict-verify`** is documented and repeatable (includes **`elf-sanity`**), and Phase **5** can consume **`build/aerofighters_assault.elf`**.

---

## Phase 5 — N64Recomp (Windows `tools/N64Recomp.exe`)

**Goal:** drive the vendored CLI with a checked-in TOML so recompiled sources are emitted only under **`RecompiledFuncs/`** ([N64Recomp](https://github.com/Mr-Wiseguy/N64Recomp) README; this repo pins the binary’s source commit in **`tools/README.txt`**).

### Prerequisites

- **`build/aerofighters_assault.elf`** from Phase 4 (**`make strict-verify`** recommended after **`splat split`** + **`make dedupe-bss`**).
- **`tools/N64Recomp.exe`** present (tracked).

### Commands

| Step | Where | Command |
|------|--------|---------|
| Run recompiler | Repo root, **PowerShell** | **`.\tools\N64Recomp.exe .\config\aerofighters_assault.n64recomp.toml`** |
| Same (optional) | WSL after **`$(ELF)`** exists | **`make n64recomp`** — invokes **`tools/N64Recomp.exe`** with **`config/aerofighters_assault.n64recomp.toml`** (Windows interop; skip if your WSL cannot run PE) |
| Optional context dump | Same | Append **`--dump-context`** (writes **`dump.toml`** / **`data_dump.toml`** in the cwd per **`src/main.cpp`**) |

**Config:** **`config/aerofighters_assault.n64recomp.toml`** — **`[input]`** keys match N64Recomp **`src/config.cpp`** (paths relative to the TOML file). **`entrypoint = 0x80200050`** matches **`config/symbol_addrs.txt`** and **`Makefile`** **`-e entrypoint`**.

### Phase 5 checklist

- [x] Committed TOML with **`elf_path`** + **`output_func_path`** + **`entrypoint`** (ELF-only mode; no **`symbols_file_path`** — mutually exclusive per **`src/main.cpp`**).
- [x] First successful static recomp (**`N64Recomp.exe`** exit **0**, **2026-05-13**). **`[[patches.instruction]]`** on **`func_8024AE70`** replaces **`j func_84001064`** (**`asm/4BE20.s`**) with **`jr $ra` / `nop`** — same bytes as Kirby-style patches in **`Docs/RepoInjests/`**. **`stubs`** cover **`func_8024AE78`** (COP0 bootstrap per **`asm/4BE20.s`**), every splat **`cache`** helper in **`asm/3E750.s`**, **`asm/3FFD0.s`**, **`asm/3DDC0.s`**, **`asm/49090.s`**, plus functions where **`src/analysis.cpp`** could not size a jump table; re-run **`python tools/n64recomp_stub_until_green.py`** after large **`asm/`** or ELF changes to extend the list.

---

## Phase 6 — Engine integration (`lib/`, `src/`, `patches/`)

**Goal:** submodule or vendor the reusable runtime (**[Zelda64Recomp](https://github.com/Mr-Wiseguy/Zelda64Recomp)** preferred per **`lib/README.txt`**), add thin game glue under **`src/`**, and keep overrides under **`patches/`** — see **`Docs/SystemPrompt.md`** layers table.

### Prerequisites

- Phase **4** ELF + Phase **5** smoke recomp path understood (**`Docs/Workflow.md`** § 4–5).
- Engine revision is recorded in **`lib/README.txt`** and **`.gitmodules`** (**`branch = dev`**; full SHA in **`lib/README.txt`**).

### Commands / files

| Step | Notes |
|------|--------|
| Init engine | From repo root: **`git submodule update --init --recursive`** — pulls **`lib/Zelda64Recomp`** and nested deps (see **`.gitmodules`**, **`lib/README.txt`**). |
| Bridge **RecompiledFuncs** | **`tools/phase6_link_recompiledfuncs.ps1`** — junction **`lib/Zelda64Recomp/RecompiledFuncs`** → repo-root **`RecompiledFuncs/`** so upstream **`CMakeLists.txt`** **`file(GLOB …/RecompiledFuncs/*.c)`** matches Phase 5 output paths (**`config/aerofighters_assault.n64recomp.toml`** **`output_func_path`**; N64Recomp **`src/config.cpp`**). **`-Remove`** to delete the junction. On Unix/WSL: **`ln -sfn ../../RecompiledFuncs lib/Zelda64Recomp/RecompiledFuncs`** (see **`lib/README.txt`**). |
| Vendored **N64Recomp** in engine | **`tools/phase6_copy_n64recomp_to_engine.ps1`** — copies **`tools/N64Recomp.exe`** and **`tools/RSPRecomp.exe`** into **`lib/Zelda64Recomp/`** per **`lib/Zelda64Recomp/BUILDING.md`** § 4 (same step as upstream “copy … to the root of the Zelda64Recomp repository”). **`-WhatIf`** previews paths. Binaries are **gitignored** inside the submodule (**`lib/Zelda64Recomp/.gitignore`** **`*.exe`**). |
| **Windows prep (all of the above)** | **`tools/phase6_setup_windows.ps1`** — runs **`phase6_link_recompiledfuncs.ps1`**, **`phase6_copy_n64recomp_to_engine.ps1`**, then **`python`/`python3 tools/verify_phase6_layout.py`**. Optional **`-N64RecompMm`** / **`-RspRecomp`**: if **`lib/Zelda64Recomp/mm.us.rev1.rom_uncompressed.z64`** exists, runs **`tools/phase6_n64recomp_mm.ps1`** and/or **`tools/phase6_rsprecomp_engine.ps1`** (N64 first when both; **`lib/Zelda64Recomp/BUILDING.md`** sections 3–4). |
| **MM engine prereq audit** | **`make phase6-mm-prereq`** — **`python3 tools/phase6_mm_engine_prereq_check.py`** ( **`--strict`** fails if ROM / RSP / **`RecompiledPatches`** etc. are missing per **`lib/Zelda64Recomp/BUILDING.md`**). Not part of **`make check`**. |
| **MM CPU recomp (Windows)** | **`make phase6-n64recomp-mm`** — **`pwsh`** runs **`tools/phase6_n64recomp_mm.ps1`** (**`N64Recomp.exe us.rev1.toml`**). Run before **`make phase6-rsprecomp`** when following **`BUILDING.md`**. |
| **MM RSP C++ (Windows)** | **`make phase6-rsprecomp`** — **`pwsh`** runs **`tools/phase6_rsprecomp_engine.ps1`** (same as **`.\tools\phase6_rsprecomp_engine.ps1`** from repo root in PowerShell). Requires **`mm.us.rev1.rom_uncompressed.z64`** in **`lib/Zelda64Recomp/`** and **`tools/RSPRecomp.exe`**. |
| **AFA RSP C++ (Windows)** | **`make phase6-rsprecomp-afa`** — **`pwsh`** runs **`tools/phase6_rsprecomp_afa.ps1`**. Requires filled **`aspMain.afa.us.toml`** / **`njpgdspMain.afa.us.toml`** in **`lib/Zelda64Recomp/`**, ROM (**`afa.n64.us.z64`** default), **`tools/RSPRecomp.exe`**. See **`lib/Zelda64Recomp/AFA_PORT.md`** §1. |
| **No MM ROM (stub patches + RSP)** | **`tools/phase6_materialize_no_mm_engine_files.py`** (or **`.ps1`**) copies stub **`patches_bin.h`**, **`recomp_overlays.inl`**, **`funcs.h`** into **`lib/Zelda64Recomp/RecompiledPatches/`** (paths **`register_patches.cpp`** includes). Then configure the engine with **`-DAEROASSAULT64_NO_MM_ROM=ON`** — see **`lib/Zelda64Recomp/CMakeLists.txt`** **`option(AEROASSAULT64_NO_MM_ROM …)`** and **`tools/phase6_engine_cmake.ps1 -NoMmRom`**. Repo-root preset **`engine-superbuild-ninja-release-no-mm`** forwards the same flag via **`CMakeLists.txt`**. Stock **`src/game/`** is still MM-oriented; this only bypasses **`patches/`** / **`N64Recomp patches.toml`** and missing **`rsp/*.cpp`**. **Makefile:** **`make phase6-materialize-stubs`** (**`python3`**). **`make verify-phase6-layout`** prints a note if stub headers are missing. |
| **AFA product (stub patches + RSP)** | Same **`phase6_materialize_no_mm_engine_files.py`** as no-MM (stub **`RecompiledPatches/`** headers). Configure with **`-DAEROASSAULT64_AFA_PRODUCT=ON`** — **`tools/phase6_engine_cmake.ps1 -AfaProduct`** or **`tools/phase6_engine_cmake_vs2022.ps1 -Mode Configure -AfaProduct`**; repo-root presets **`engine-superbuild-ninja-release-afa-product`**, **`engine-superbuild-vs2022-release-afa-product`**. Skips MM **`patches.elf`** / **`patches.toml`** like **`NO_MM_ROM`** but leaves **`AEROASSAULT64_NO_MM_ROM` off** for AFA-only bring-up; see **`config/afa_rsp/README.txt`**. **Makefile:** **`make phase6-materialize-stubs`**. |
| **AFA product + retail patches pipeline** | After **`patches.elf`**, **`patches.toml`**, and **`N64Recomp`** **`RecompiledPatches/`** exist for AFA, add **`-DAEROASSAULT64_AFA_RETAIL_PIPELINES=ON`** with **`AFA_PRODUCT`** — **`tools/phase6_engine_cmake.ps1 -AfaProduct -AfaRetailPipelines`** (same **`-AfaRetailPipelines`** on **`phase6_engine_cmake_vs2022.ps1`**); presets **`engine-superbuild-ninja-release-afa-product-retail`**, **`engine-superbuild-vs2022-release-afa-product-retail`**. See **`lib/Zelda64Recomp/AFA_PORT.md`** §2 and **`CMakeLists.txt`** **`_AERO_PATCH_RSP_STUBS`**. |
| Verify bridge | **`make verify-phase6-layout`** — **`python3 tools/verify_phase6_layout.py`** (fails if both **`RecompiledFuncs`** paths exist but are not the same directory; skips if submodule missing). Part of **`make check`**. |
| Configure / build | Root **`tools/phase6_engine_cmake.ps1`** — runs **`cmake -S lib/Zelda64Recomp -B build-engine …`** (default Ninja; upstream **`CMakeLists.txt`** expects that tree as **`CMAKE_SOURCE_DIR`**; see **`lib/README.txt`**). For a **full MSVC link** on Windows use **`tools/phase6_engine_cmake_vs2022.ps1`** (**`build-engine-vs2022/`**, Visual Studio 17 2022 generator). Or run the same **`cmake`** lines manually. Follow **`lib/Zelda64Recomp/BUILDING.md`** for MM ROM / toolchain prerequisites until an AFA fork exists. |
| **Repo-root CMake (alternative)** | **`CMakeLists.txt`** at repo root uses **`ExternalProject_Add`** (**`zelda64recomp_engine`**) so the **inner** configure uses **`SOURCE_DIR = lib/Zelda64Recomp`** (same **`CMAKE_SOURCE_DIR`** invariant as direct **`-S lib/Zelda64Recomp`**). Outer binary dirs: **`build-root/`** (Ninja), **`build-root-vs2022/`** (VS), **`build-root-afa-product/`**, **`build-root-vs2022-afa-product/`**, **`build-root-afa-product-retail/`**, **`build-root-vs2022-afa-product-retail/`**. **`CMakePresets.json`**: **`engine-superbuild-ninja-release`**, **`engine-superbuild-vs2022-release`**, **`engine-superbuild-ninja-release-no-mm`**, **`engine-superbuild-ninja-release-afa-product`**, **`engine-superbuild-vs2022-release-afa-product`**, **`engine-superbuild-ninja-release-afa-product-retail`**, **`engine-superbuild-vs2022-release-afa-product-retail`**. Example: **`cmake --preset engine-superbuild-ninja-release`** then **`cmake --build --preset engine-superbuild-ninja-release`**. Default **`ALL`** also builds **`zelda64recomp_engine`** via **`aero_phase6_engine_default`**. |
| Game layer | Thin glue under repo-root **`src/`** — see **`src/README.txt`**; overrides under **`patches/README.txt`** (not engine **`lib/Zelda64Recomp/patches/`**). |
| Debug | **`Docs/Debugging.md`** — Visual Studio against the engine-generated **Windows PE** once CMake exists |

### Phase 6 checklist

- [x] **`lib/Zelda64Recomp`** present as submodule (**`dev`**); **`git submodule update --init --recursive`** documented in **`lib/README.txt`**. **Gitlink:** use **`git rev-parse HEAD:lib/Zelda64Recomp`** after pull (see **`lib/README.txt`** fork / upstream notes).
- [x] **Windows one-shot prep** — **`tools/phase6_setup_windows.ps1`** chains junction + PE copy + **`verify_phase6_layout.py`**; optional **`-N64RecompMm`** / **`-RspRecomp`** (documented in **`Docs/Workflow.md`** Phase 6 table).
- [x] **Repo-root CMake superbuild** — **`CMakeLists.txt`** + **`CMakePresets.json`**: **`ExternalProject_Add(zelda64recomp_engine)`** with inner **`SOURCE_DIR`** **`lib/Zelda64Recomp`** and **`BINARY_DIR`** **`build-engine/`** (preserves upstream **`CMAKE_SOURCE_DIR`**; see **`lib/README.txt`**).
- [x] **MM engine prereq audit** — **`tools/phase6_mm_engine_prereq_check.py`** + **`make phase6-mm-prereq`** ( **`--strict`** optional); **`Docs/Debugging.md`** MM baseline bullet.
- [x] **AFA fork — scaffolding (repo + engine build path)** — CMake **`AEROASSAULT64_AFA_PRODUCT`** / **`NO_MM_ROM`**, repo-root **`CMakeLists.txt`** + **`CMakePresets.json`**, **`tools/phase6_engine_cmake*.ps1`**, **`tools/phase5_run_aero_n64recomp.ps1`**, materialized stub **`RecompiledPatches/`** headers, **`config/afa_rsp/README.txt`**, **`engine-windows`** configure with **`-AfaProduct`**, smoke notes (**`Docs/Debugging.md`**). **`make_supported_games()`** / **`zelda64::primary_supported_game_id()`** (**`src/main/main.cpp`**, **`src/ui/ui_launcher.cpp`**, **`include/zelda_game.h`**) put **AFA USA** first when **`AFA_PRODUCT`** and **`WITH_AFA_USA`** so the launcher ROM flow targets AFA. Stock **`lib/Zelda64Recomp/src/game/`** / **`src/ui/`** remain MM-oriented until replaced.
- [ ] **AFA fork — full retail runtime** — replace MM **`us.rev1.toml`** usage for **CPU** where applicable, MM **`src/game/`** / **`src/ui/`**, RSP **`rsp/*.cpp`** (real AFA TOMLs), engine **`patches/`** + AFA **`patches.toml`** → real **`RecompiledPatches/`**, AFA **`assets/`**, and related glue so the shipped binary is **Aero Fighters Assault**, not stock **`Zelda64Recompiled`** (**fork touchpoints** table). *(Large port — requires ongoing reverse engineering and runtime work beyond this repo’s automation baseline.)* **Start here:** **`lib/Zelda64Recomp/AFA_PORT.md`**, **`config/afa_rsp/*.template.toml`**, **`config/afa_engine/`**, **`config/afa_assets/README.txt`**.
- [x] First **PowerShell** / **VS** run of the built engine binary with **AFA** **`RecompiledFuncs`** + stub Patches/RSP (**`-NoMmRom`** or **`-AfaProduct`**) — smoke notes under **`Docs/Debugging.md`** § *Phase 6 — No-MM + AFA `RecompiledFuncs` (MSVC smoke)*. A true **AFA**-branded runtime still depends on the **AFA fork** row above.

### Phase 6 fork touchpoints (upstream `lib/Zelda64Recomp`)

Use this as a checklist when forking or replacing **Majora's Mask** assumptions. Paths are under **`lib/Zelda64Recomp/`** unless noted; primary build logic is **`lib/Zelda64Recomp/CMakeLists.txt`**.

| Area | Upstream files / CMake | AFA direction |
|------|-------------------------|---------------|
| CPU static recomp | **`us.rev1.toml`**, **`./N64Recomp us.rev1.toml`** (**`lib/Zelda64Recomp/BUILDING.md`** § 4) | Repo uses **`tools/N64Recomp.exe`** + **`config/aerofighters_assault.n64recomp.toml`** → **`RecompiledFuncs/`** (junction). Optional second **`GameEntry`** for AFA USA when **`config/.afa_usa_rom_xxh3`** or **`-DAEROASSAULT64_AFA_ROM_XXH3_HEX`** is set (**`lib/Zelda64Recomp/CMakeLists.txt`**, **`tools/compute_aero_rom_xxh3.py`**). |
| **`RecompiledFuncs/`** | **`file(GLOB … ${CMAKE_SOURCE_DIR}/RecompiledFuncs/*.c)`** / **`*.cpp`** (same **`CMakeLists.txt`**) | Keep output under one tree; interim: **`tools/phase6_link_recompiledfuncs.ps1`** / symlink (**`lib/README.txt`**). |
| RSP microcode | **`rsp/aspMain.cpp`**, **`rsp/njpgdspMain.cpp`** (repo-root **`.gitignore`** **`lib/Zelda64Recomp/rsp/*.cpp`**); **`./RSPRecomp *.toml`** or **`tools/phase6_rsprecomp_afa.ps1`** for AFA TOMLs | Regenerate from AFA RSP TOMLs (**`AFA_PORT.md`** §1) or use CMake RSP stubs until ported. |
| Patch ELF + **`RecompiledPatches/`** | Engine **`patches/`** **`Makefile`** → **`patches.elf`**; **`./N64Recomp patches.toml`** → **`RecompiledPatches/patches.c`** etc. (**`CMakeLists.txt`** custom commands) | Not the same as repo-root **`patches/`** — see **`patches/README.txt`**. Full AFA pipeline needs engine **`patches/`** + AFA **`patches.toml`**. Interim: **`AEROASSAULT64_NO_MM_ROM`** or **`AEROASSAULT64_AFA_PRODUCT`** (without **`AEROASSAULT64_AFA_RETAIL_PIPELINES`**) + **`tools/phase6_no_mm_engine/`** stubs (**`lib/Zelda64Recomp/CMakeLists.txt`**); with **`AFA_PRODUCT`** + **`AFA_RETAIL_PIPELINES`**, use the real **`PatchesLib`** path (**`lib/Zelda64Recomp/AFA_PORT.md`** §2). |
| Game + UI C++ | **`src/game/*`**, **`src/main/*`**, **`src/ui/*`**, **`rsp/*.cpp`** in **`SOURCES`** | Replace MM-specific ROM load, scenes, assets with AFA logic; keep **`RT64Context`** / **`ultramodern`** boundaries where possible. **Launcher:** **`src/ui/ui_launcher.cpp`** uses **`zelda64::primary_supported_game_id()`** (**`include/zelda_game.h`**, implemented in **`src/main/main.cpp`**) so ROM pick / start match **`supported_games[0]`** — **AFA first** when **`AEROASSAULT64_AFA_PRODUCT`** and **`AEROASSAULT64_WITH_AFA_USA`** (**`make_supported_games()`**, **`librecomp`** **`select_rom`** / **`recomp.cpp`** XXH3 check). |
| Project / binary name | **`project(Zelda64Recompiled …)`**, executable **`Zelda64Recompiled`** | CMake **`AEROASSAULT64_EXE_OUTPUT_NAME`** → **`OUTPUT_NAME`** (target name unchanged). **`tools/phase6_engine_cmake_vs2022.ps1 -ExeOutputName`** or superbuild **`-D`**. |
| Assets / runtime | **`BUILDING.md`** § 6 (run EXE from project root or copy **`assets/`**) | AFA **`assets/`** / RT64 paths after de-MM the tree. |

---

## Later phases (Phase 7+)

### Phase 7 — CMake → Windows PE (host smoke)

- [x] Documented MSVC path — **`tools/phase6_engine_cmake_vs2022.ps1`**, **`build-engine-vs2022/`**, **`lib/Zelda64Recomp/BUILDING.md`** § toolchain.
- [x] Smoke launch script — **`tools/phase6_smoke_engine.ps1`** (**`tools/README.txt`**, **`Docs/Debugging.md`**).
- [x] CI compiles engine libs with stubs — **`.github/workflows/engine-windows.yml`** (**`RecompiledFuncs`** + **`PatchesLib`**, **`phase6_ci_ensure_recompiledfuncs_stub.ps1`** when no generated **`.c`**).

### Phase 8 — Test / stabilize (automation vs. product QA)

- [x] ROM-free **`repo-check`** workflow — splat/Makefile sync, rodata tuple, entrypoint triple, N64Recomp TOML, phase6 layout, MM prereq audit (informational), **`py_compile`** on **`tools/*.py`** (see **`.github/workflows/repo-check.yml`**).
- [x] Windows **`engine-windows`** workflow — submodule recursive checkout, materialize **`RecompiledPatches/`** stubs, junction **`RecompiledFuncs`**, MSVC configure **`-AfaProduct`**, build **`RecompiledFuncs`** + **`PatchesLib`**.
- [ ] **Product QA** — gameplay loops, ROM-load correctness, perf/regression matrix, release signing/packaging (add here as the port matures).

**Policy:** Phases **1–5** and **7–8 automation baseline** are **closed at the repo/CI level** as documented above. Phase **6** stays **in progress** until the **full retail runtime** checklist row is satisfied; optional Phase **1–3** items (MIPS GCC, Ghidra rodata spot-check) remain **optional** and do not block that closure.
