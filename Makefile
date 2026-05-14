# Phase 4 — assemble splat .s and link build/aerofighters_assault.elf (WSL / Linux + mips-linux-gnu-*).
# Prerequisite: from repo root run `python3 -m splat split config/splat.yaml` so asm/, assets/ipl3.bin, and build/*.ld exist.
# See Docs/Workflow.md and https://github.com/ethteck/splat/wiki/General-Workflow

.PHONY: all split clean check-split verify dedupe-bss strict-verify n64recomp elf-sanity verify-rodata-sync verify-splat-makefile-sync verify-entrypoint-sync verify-phase6-layout phase6-mm-prereq phase6-rsprecomp check help

.DEFAULT_GOAL := all

help:
	@echo "AeroAssault64 — common Makefile targets (WSL/Linux unless noted):"
	@echo "  make split          - python3 -m splat split $(SPLIT_CFG)"
	@echo "  make all            - link $(ELF) (needs asm/ + split output)"
	@echo "  make verify         - readelf -h on $(ELF)"
	@echo "  make elf-sanity     - assert entry 80200050 + MIPS in ELF header"
	@echo "  make dedupe-bss     - strip duplicate BSS lines (needs post_data.o)"
	@echo "  make strict-verify  - dedupe-bss + LINK_STRICT=1 verify + elf-sanity"
	@echo "  make n64recomp      - run tools/N64Recomp.exe with N64RECOMP_CFG (needs $(ELF), often from WSL)"
	@echo "  make check          - ROM-free: splat/Makefile + rodata + entrypoint + N64Recomp TOML + phase6 layout + py_compile tools"
	@echo "  make verify-phase6-layout - python3 tools/verify_phase6_layout.py (RecompiledFuncs bridge vs engine)"
	@echo "  make phase6-mm-prereq  - python3 tools/phase6_mm_engine_prereq_check.py (MM engine / BUILDING.md checklist)"
	@echo "  make phase6-rsprecomp - Windows: pwsh tools/phase6_rsprecomp_engine.ps1 (MM RSP outputs; needs ROM in engine root)"
	@echo "  make clean          - remove $(ELF), objects, extern ld"
	@echo "See Docs/Workflow.md and tools/README.txt."

SPLAT        ?= python3 -m splat
SPLIT_CFG    := config/splat.yaml
LDSCRIPT     := build/aerofighters_assault.ld
EXTERN_LD    := build/splat_extern.ld
ELF          := build/aerofighters_assault.elf

MIPS_PREFIX  ?= mips-linux-gnu-
AS           := $(MIPS_PREFIX)as
LD           := $(MIPS_PREFIX)ld
READELF      := $(MIPS_PREFIX)readelf

# Match splat / N64 o32: VR4300 + 32-bit ABI (see splat General Workflow — mips-linux-gnu-as).
# `post_data.s` is special: spimdisasm emits `pref`; GNU as rejects `pref` with -march=vr4300 (MIPS III).
ASFLAGS      := -march=vr4300 -mabi=32 -G0 -I include
# post_data vs 800000.bss: duplicate `func_*` / `D_*` `.comm` in splat `*.bss.s` vs definitions in `post_data.o`.
# After `splat split` + `make build/asm/post_data.o`, run `make dedupe-bss` (see tools/dedupe_post_data_bss.py),
# then link with `make LINK_STRICT=1 ...` to omit `--allow-multiple-definition`.
LINK_STRICT  ?= 0
ifeq ($(LINK_STRICT),1)
LDFLAGS      :=
else
LDFLAGS      := --allow-multiple-definition
endif

ASM_SRCS     := $(wildcard asm/*.s) $(wildcard asm/data/*.s)
# `asm/data/57D20.bss.s` reserves labels from VRAM 0x80256D70 — the same window as `post_data.o(.text)`
# (ROM 0x57D20). splat's `build/aerofighters_assault.ld` therefore does not list `57D20.bss.o`; linking it
# would orphan-discard `.bss` or fight VMA with `.main`. `tools/gen_splat_extern_ld.py` supplies absolute
# `D_*` / `.L*` where those symbols stay UND. See Docs/Workflow.md Phase 4.
ASM_OBJS     := $(filter-out build/asm/post_data.o build/asm/data/57D20.bss.o,$(patsubst asm/%.s,build/asm/%.o,$(ASM_SRCS)))
IPL3_OBJ     := build/assets/ipl3.o
ALL_OBJS     := $(ASM_OBJS) $(IPL3_OBJ) build/asm/post_data.o

all: check-split $(ELF)

verify: $(ELF)
	@$(READELF) -h $(ELF) | grep -E 'Type:|Machine:|Entry|Flags:'
	@echo "OK: $(ELF)"

# Phase 4: assert ELF header matches splat entry (0x80200050) and MIPS (binutils readelf -h).
elf-sanity: $(ELF)
	@$(READELF) -h $(ELF) | grep -q '80200050' || (echo "elf-sanity: entry must contain 80200050 (see config/symbol_addrs.txt entrypoint)"; exit 1)
	@$(READELF) -h $(ELF) | grep -qi 'mips' || (echo "elf-sanity: Machine line must mention MIPS"; exit 1)
	@echo "OK: elf-sanity $(ELF)"

split:
	$(SPLAT) split $(SPLIT_CFG)

# Remove `.comm` / `.lcomm` lines in `asm/**/*.bss.s` that duplicate labels in `post_data.o` (needs mips nm or scans .s).
dedupe-bss: build/asm/post_data.o
	python3 tools/dedupe_post_data_bss.py --apply

# Phase 4: dedupe `800000.bss.s` then link with single-definition rules (see Docs/Workflow.md § Phase 4).
strict-verify: dedupe-bss
	$(MAKE) LINK_STRICT=1 verify
	$(MAKE) elf-sanity

# Phase 5 (Windows PE): requires `tools/N64Recomp.exe` and a built `$(ELF)`.
# From WSL this often works via Windows interop; otherwise run from PowerShell (see tools/README.txt).
N64RECOMP_EXE ?= tools/N64Recomp.exe
N64RECOMP_CFG ?= config/aerofighters_assault.n64recomp.toml
n64recomp: $(ELF)
	@test -f $(N64RECOMP_EXE) || (echo "Missing $(N64RECOMP_EXE)"; exit 1)
	$(N64RECOMP_EXE) $(N64RECOMP_CFG)

# ROM-free sanity (CI / quick local): splat/Makefile, rodata Ghidra tuple, triple entrypoint, N64Recomp TOML shape, py_compile.
check: verify-splat-makefile-sync verify-rodata-sync verify-entrypoint-sync
	python3 tools/verify_n64recomp_toml.py
	python3 tools/verify_phase6_layout.py
	python3 -m py_compile tools/dedupe_post_data_bss.py tools/n64recomp_stub_until_green.py tools/verify_rodata_splits_sync.py tools/verify_splat_makefile_sync.py tools/verify_entrypoint_sync.py tools/verify_n64recomp_toml.py tools/verify_phase6_layout.py tools/phase6_mm_engine_prereq_check.py tools/gen_splat_extern_ld.py
	@echo "OK: make check"

# splat entry vram / symbol_addrs entrypoint / N64Recomp [input].entrypoint must agree.
verify-entrypoint-sync:
	python3 tools/verify_entrypoint_sync.py

# Ghidra Phase3: RODATA_ROM_SPLITS must match splat main rodata subsegments (stdlib check).
verify-rodata-sync:
	python3 tools/verify_rodata_splits_sync.py

# splat options.basename / elf_path stem must match Makefile ELF / ld script names.
verify-splat-makefile-sync:
	python3 tools/verify_splat_makefile_sync.py

# Phase 6: when lib/Zelda64Recomp exists, RecompiledFuncs bridge must not split roots.
verify-phase6-layout:
	python3 tools/verify_phase6_layout.py

# Phase 6: optional audit for stock Zelda64Recomp (MM) prerequisites (BUILDING.md). Not part of make check.
phase6-mm-prereq:
	python3 tools/phase6_mm_engine_prereq_check.py

# Windows / PowerShell 7+: requires mm.us.rev1.rom_uncompressed.z64 under lib/Zelda64Recomp/ (BUILDING.md §3).
phase6-rsprecomp:
	pwsh -NoProfile -ExecutionPolicy Bypass -File tools/phase6_rsprecomp_engine.ps1

check-split:
	@test -f $(LDSCRIPT) || (echo "Missing $(LDSCRIPT). Run: $(SPLAT) split $(SPLIT_CFG)"; exit 1)
	@test -f assets/ipl3.bin || (echo "Missing assets/ipl3.bin. Run: $(SPLAT) split $(SPLIT_CFG)"; exit 1)

# Absolute symbols for address-in-name labels (readelf UND); see tools/gen_splat_extern_ld.py + splat.yaml.
$(EXTERN_LD): $(ALL_OBJS) config/link_extern_additions.txt tools/gen_splat_extern_ld.py | build
	printf '%s\n' '/* Generated splat externs — see Makefile + tools/gen_splat_extern_ld.py + splat.yaml. */' > $@
	python3 tools/gen_splat_extern_ld.py --extras config/link_extern_additions.txt $(ALL_OBJS) >> $@

$(ELF): $(ALL_OBJS) $(LDSCRIPT) $(EXTERN_LD)
	$(LD) -nostdlib $(LDFLAGS) -T $(LDSCRIPT) -T $(EXTERN_LD) -o $@ -e entrypoint --oformat elf32-tradbigmips $(ALL_OBJS)

$(IPL3_OBJ): assets/ipl3_bin.s assets/ipl3.bin | build/assets
	$(AS) $(ASFLAGS) -I assets -o $@ $<

build/asm/%.o: asm/%.s | build/asm
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -o $@ $<

# Smoke-build only: replace cache `pref` with `nop` so -march=vr4300 gas accepts the file.
# Reconcile with ROM bytes / Ghidra if you rely on those hints at runtime.
build/asm/post_data.o: asm/post_data.s | build/asm
	sed 's/[[:blank:]]pref .*/\tnop/' $< | $(AS) $(ASFLAGS) -o $@ -

build/asm build/assets:
	mkdir -p $@

clean:
	rm -f $(ELF) $(EXTERN_LD) $(ASM_OBJS) $(IPL3_OBJ) build/asm/post_data.o
