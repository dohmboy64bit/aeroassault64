# Phase 4 — assemble splat .s and link build/aerofighters_assault.elf (WSL / Linux + mips-linux-gnu-*).
# Prerequisite: from repo root run `python3 -m splat split config/splat.yaml` so asm/, assets/ipl3.bin, and build/*.ld exist.
# See Docs/Workflow.md and https://github.com/ethteck/splat/wiki/General-Workflow

.PHONY: all split clean check-split verify dedupe-bss strict-verify

.DEFAULT_GOAL := all

SPLAT        ?= python3 -m splat
SPLIT_CFG    := config/splat.yaml
LDSCRIPT     := build/aerofighters_assault.ld
EXTERN_LD    := build/splat_extern.ld
ELF          := build/aerofighters_assault.elf

MIPS_PREFIX  ?= mips-linux-gnu-
AS           := $(MIPS_PREFIX)as
LD           := $(MIPS_PREFIX)ld

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
	@mips-linux-gnu-readelf -h $(ELF) | grep -E 'Type:|Machine:|Entry|Flags:'
	@echo "OK: $(ELF)"

split:
	$(SPLAT) split $(SPLIT_CFG)

# Remove `.comm` / `.lcomm` lines in `asm/**/*.bss.s` that duplicate labels in `post_data.o` (needs mips nm or scans .s).
dedupe-bss: build/asm/post_data.o
	python3 tools/dedupe_post_data_bss.py --apply

# Phase 4: dedupe `800000.bss.s` then link with single-definition rules (see Docs/Workflow.md § Phase 4).
strict-verify: dedupe-bss
	$(MAKE) LINK_STRICT=1 verify

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
