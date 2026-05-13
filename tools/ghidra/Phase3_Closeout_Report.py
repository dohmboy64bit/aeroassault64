# -*- coding: utf-8 -*-
# Ghidra script: evidence for Phase 3 closeout (rodata boundaries, tail ROM, BSS, dup symbols).
# Run with the AFA USA program open (same setup as Phase2_Closeout_Report.py).
#
# Sync: RODATA_ROM_SPLITS must match `config/splat.yaml` `main` rodata subsegment ROM starts.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name Phase3_Closeout_Report
#@description Phase 3 — rodata boundary xrefs, tail ROM scan, splat BSS VRAM, duplicate-name hints
#@author AeroAssault64

from __future__ import print_function

# --- Sync with config/splat.yaml (main rodata + post_data + bss) -----------------
RODATA_ROM_SPLITS = (
    0x52B90,
    0x52BC0,
    0x53670,
    0x53940,
    0x53A80,
    0x53BA0,
    0x540E0,
    0x54430,
    0x54580,
    0x54650,
    0x54920,
    0x54CF0,
    0x54EC0,
    0x54F20,
    0x55370,
    0x55830,
    0x559F0,
    0x56110,
    0x56140,
    0x56150,
    0x56340,
    0x56360,
    0x56370,
    0x565F0,
    0x56620,
    0x568E0,
    0x568F0,
    0x569A0,
    0x57260,
    0x57A60,
)
ROM_OFF_DATA = 0x4C050
ROM_OFF_TAIL = 0x57D20
ROM_END = 0x800000  # cart image size marker in splat config
EXP_BSS_VRAM = 0x8027F050  # splat `bss` subsegment
EXP_TAIL_ENTRY_VRAM = 0x80256D70  # ROM 0x57D20 -> main post_data .text start

# Names that mips-linux-gnu-ld reported as multiply-defined (post_data vs 800000.bss) — re-verify in Ghidra.
DUP_CANDIDATES = (
    "func_809C801C",
    "func_809D2084",
    "func_809D20C0",
    "func_809DD100",
    "func_809DE028",
)


def _u8(mem, addr):
    return mem.getByte(addr) & 0xFF


def read_be32(mem, addr):
    return (
        (_u8(mem, addr) << 24)
        | (_u8(mem, addr.add(1)) << 16)
        | (_u8(mem, addr.add(2)) << 8)
        | _u8(mem, addr.add(3))
    )


def read_be32_safe(mem, addr, label):
    if addr is None or not mem.contains(addr):
        print("  (%s: unreadable %s)" % (label, addr))
        return None
    try:
        return read_be32(mem, addr)
    except Exception as e:
        print("  (%s: %s)" % (label, e))
        return None


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def addr_in_block(block, rom_off):
    if block is None:
        return None
    base = block.getStart()
    return base.add(rom_off)


def mips_hint_be32(w):
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    if imm & 0x8000:
        simm = imm - 0x10000
    else:
        simm = imm
    if op == 9 and rs == 29 and rt == 29:
        return "addiu sp, sp, %d" % simm
    if op == 0x2B:
        return "sw r%d, %d(r%d)" % (rt, simm, rs)
    if op == 0:
        return "R-type 0x%08x" % w
    return "op=%d rs=%d rt=%d simm=%d" % (op, rs, rt, simm)


def vram_to_addr_in_ram(ram_block, vram):
    if ram_block is None:
        return None
    base = ram_block.getStart()
    delta = int(vram) - int(base.getOffset())
    if delta < 0:
        return None
    return base.add(delta)


def vram_from_splat_style_name(name):
    """Parse VRAM from splat-style `func_DEADBEEF` or `D_DEADBEEF` (hex suffix)."""
    if "_" not in name:
        return None
    kind, rest = name.split("_", 1)
    if kind not in ("func", "D"):
        return None
    try:
        return int(rest, 16)
    except ValueError:
        return None


def report_ram_at_vram(mem, listing, sym_tab, ram, vram, label):
    """Print primary symbol + listing at mapped .ram address for a KSEG0-style VRAM."""
    a = vram_to_addr_in_ram(ram, vram)
    if a is None or not mem.contains(a):
        print("    %s: VRAM 0x%X not mapped into `.ram` (check .ram min address vs KSEG0 base)" % (label, vram))
        return
    blk = mem.getBlock(a)
    blk_s = "%s (x=%s w=%s)" % (blk.getName(), blk.isExecute(), blk.isWrite()) if blk else "(no block)"
    ps = sym_tab.getPrimarySymbol(a)
    fn = listing.getFunctionContaining(a)
    da = listing.getDataAt(a)
    ins = listing.getInstructionAt(a)
    off = int(a.getOffset()) & 0xFFFFFFFFFFFFFFFF
    print(
        "    %s: VRAM 0x%X -> flat 0x%X  block=%s"
        % (label, vram, off, blk_s)
    )
    print(
        "      primary=%s  fn=%s  insn=%s  data=%s"
        % (
            ps if ps else "(none)",
            fn if fn else "(none)",
            ins,
            da,
        )
    )
    if ps is None and ins is None:
        print(
            "      -> No function / primary label: typical for **BSS** or unanalyzed RAM;"
            " splat `post_data` may still emit **`func_*` in .text** at this VRAM (linker multiply-defined vs `800000.bss`)."
        )


def symbols_named(sym_tab, prog, name):
    """Resolve symbols by exact name (Ghidra has no getSymbol(String) overload — use collections APIs)."""
    out = []
    try:
        gl = sym_tab.getGlobalSymbols(name)
        if gl is not None:
            for s in gl:
                out.append(s)
    except Exception:
        pass
    if out:
        return out
    try:
        gns = prog.getGlobalNamespace()
        lb = sym_tab.getLabelOrFunctionSymbols(name, gns)
        if lb is not None:
            for s in lb:
                out.append(s)
    except Exception:
        pass
    return out


def _iter_refs_to(ref_mgr, to_addr):
    """Yield Reference objects to to_addr (Ghidra ReferenceIterator)."""
    refs = ref_mgr.getReferencesTo(to_addr)
    while refs.hasNext():
        yield refs.next()


def count_refs_from_executable(mem, ref_mgr, to_addr):
    """Count references whose *from* address lies in an executable memory block."""
    n = 0
    for r in _iter_refs_to(ref_mgr, to_addr):
        fa = r.getFromAddress()
        blk = mem.getBlock(fa)
        if blk is not None and blk.isExecute():
            n += 1
    return n


def count_refs_all(mem, ref_mgr, to_addr):
    n = 0
    for _ in _iter_refs_to(ref_mgr, to_addr):
        n += 1
    return n


def scan_tail_rom_stats(listing, mem, rom, start_off, end_off):
    """Classify aligned words in [start_off, end_off) by Ghidra listing (instruction vs data vs empty)."""
    ins = 0
    dat = 0
    und = 0
    step = 4
    pos = start_off
    base = rom.getStart()
    while pos < end_off:
        a = base.add(pos)
        if not mem.contains(a):
            break
        if listing.getInstructionAt(a) is not None:
            ins += 1
        elif listing.getDataAt(a) is not None:
            dat += 1
        else:
            und += 1
        pos += step
    total = (end_off - start_off) // step
    return ins, dat, und, total


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    ref_mgr = prog.getReferenceManager()
    sym_tab = prog.getSymbolTable()

    print("=== AeroAssault64 Phase 3 — Ghidra closeout evidence ===")
    print("Program: %s" % prog.getName())
    print("Sync RODATA_ROM_SPLITS with config/splat.yaml before trusting boundary table.")

    rom = get_block_exact(mem, ".rom")
    ram = get_block_exact(mem, ".ram")
    if rom is None:
        print("ERROR: need MemoryBlock named exactly `.rom`")
        return
    if ram is None:
        print("WARNING: no `.ram` block — RAM checks will be skipped")

    # Section C scans **.rom** only; tail may already be code in **.ram** (Phase3_Ensure_PostData_Function.py).
    tail_ram_has_insn = False
    if ram is not None:
        ta_chk = vram_to_addr_in_ram(ram, EXP_TAIL_ENTRY_VRAM)
        if ta_chk is not None and mem.contains(ta_chk) and listing.getInstructionAt(ta_chk) is not None:
            tail_ram_has_insn = True

    rom_base = rom.getStart()

    print("\n--- A) ROM `data` start (splat 0x4C050) ---")
    a = addr_in_block(rom, ROM_OFF_DATA)
    w = read_be32_safe(mem, a, "ROM+0x%X" % ROM_OFF_DATA)
    if w is not None:
        print("  First word: 0x%08X  %s" % (w, mips_hint_be32(w)))
        print("  Code unit: %s" % listing.getInstructionAt(a))
        print("  Data unit: %s" % listing.getDataAt(a))

    print("\n--- B) Rodata split boundaries (splat yaml ROM offsets) ---")
    print("  For each start offset: BE32 @ start, xref counts (exec-from / all).")
    print("  High exec-from count on a boundary may mean jump tables / pointers land there — validate before moving yaml.")
    print(
        "  NOTE: xrefs are **to the .rom file address**. The game usually references the **.ram** KSEG0 mirror;"
        " xrefs_exec/xrefs_all often stay 0 here even when rodata is heavily used."
    )
    for off in RODATA_ROM_SPLITS:
        a = addr_in_block(rom, off)
        w = read_be32_safe(mem, a, "ROM+0x%X" % off)
        hint = mips_hint_be32(w) if w is not None else "?"
        xe = count_refs_from_executable(mem, ref_mgr, a)
        xa = count_refs_all(mem, ref_mgr, a)
        ins = listing.getInstructionAt(a)
        du = listing.getDataAt(a)
        print(
            "  ROM+0x%05X  word=0x%08X  %s  xrefs_exec=%d xrefs_all=%d  ins=%s data=%s"
            % (off, w if w is not None else -1, hint, xe, xa, ins is not None, du is not None)
        )

    print("\n--- C) Tail `post_data` ROM [0x%x, 0x%x) listing mix (4-byte steps) ---" % (ROM_OFF_TAIL, ROM_END))
    ins, dat, und, tot = scan_tail_rom_stats(listing, mem, rom, ROM_OFF_TAIL, ROM_END)
    print("  Instructions (aligned): %d" % ins)
    print("  Defined data:           %d" % dat)
    print("  Undefined / neither:    %d" % und)
    print("  Total 4-byte slots:    %d" % tot)
    if tot > 0:
        print(
            "  (Large `undefined` count is normal until you define tail as code/data in Ghidra.)"
        )
    if ins == 0 and dat > 100000:
        print(
            "  NOTE: Ghidra has ~no instructions in this ROM span — it is mostly **defined data**."
        )
        print(
            "        splat still emits `post_data` as **asm** from ROM 0x%X; compare **.rom** vs **.ram**"
            " at 0x80256D70 (Create Function / clear erroneous data if the tail is really code)." % ROM_OFF_TAIL
        )
        if tail_ram_has_insn:
            print(
                "  NOTE: **.ram** at 0x%08X already has an instruction (see section F) — this table is **.rom**-only."
                " `Phase3_Ensure_PostData_Function.py` only clears/disassembles `.ram`; mirror clear/disassemble on `.rom`"
                " if you want instruction counts here too." % EXP_TAIL_ENTRY_VRAM
            )

    print("\n--- D) First words at tail (sanity: MIPS prologue?) ---")
    a0 = addr_in_block(rom, ROM_OFF_TAIL)
    for i in range(8):
        addr = a0.add(i * 4)
        w = read_be32_safe(mem, addr, "ROM+0x%X" % (ROM_OFF_TAIL + i * 4))
        if w is not None:
            print("  ROM+0x%X  0x%08X  %s" % (ROM_OFF_TAIL + i * 4, w, mips_hint_be32(w)))

    print("\n--- E) splat BSS VRAM 0x%08X (symbol / listing at .ram)" % EXP_BSS_VRAM)
    if ram is not None:
        ba = vram_to_addr_in_ram(ram, EXP_BSS_VRAM)
        if ba is not None and mem.contains(ba):
            ps = sym_tab.getPrimarySymbol(ba)
            print("  Address: %s" % ba)
            print("  Primary symbol: %s" % (ps if ps else "(none)"))
            print("  Instruction: %s" % listing.getInstructionAt(ba))
            print("  Data: %s" % listing.getDataAt(ba))
        else:
            print("  (could not map VRAM into `.ram` — check block base vs KSEG0)")

    print("\n--- F) splat tail entry VRAM 0x%08X (post_data .text start)" % EXP_TAIL_ENTRY_VRAM)
    if ram is not None:
        ta = vram_to_addr_in_ram(ram, EXP_TAIL_ENTRY_VRAM)
        if ta is not None and mem.contains(ta):
            fn = listing.getFunctionContaining(ta)
            ps = sym_tab.getPrimarySymbol(ta)
            print("  Address: %s" % ta)
            print("  Function containing: %s" % (fn if fn else "(none)"))
            print("  Primary symbol: %s" % (ps if ps else "(none)"))
            print("  Instruction: %s" % listing.getInstructionAt(ta))
            if fn is None and listing.getInstructionAt(ta) is None:
                print(
                    "  NOTE: If ROM @ 0x%X is MIPS (see section D), create a **function** at this"
                    " RAM address (or fix auto-analysis) so Phase 3 notes match splat." % ROM_OFF_TAIL
                )

    print("\n--- G) Multiply-defined symbol candidates (linker smoke list) ---")
    print(
        "  splat/asm uses names like `func_809D20C0` (= VRAM 0x809D20C0). Ghidra rarely uses the same string;"
        " each line below parses **VRAM from the suffix** and shows what **.ram** actually has."
    )
    for name in DUP_CANDIDATES:
        print("  --- %s ---" % name)
        syms = symbols_named(sym_tab, prog, name)
        if syms:
            print("    exact-name match: %d symbol(s)" % len(syms))
            for s in syms[:4]:
                print("      %s  addr=%s  type=%s" % (s.getName(), s.getAddress(), s.getSymbolType()))
        else:
            print("    (no exact-name Ghidra symbol — expected for splat `func_*` labels)")
        vram = vram_from_splat_style_name(name)
        if vram is not None and ram is not None:
            report_ram_at_vram(mem, listing, sym_tab, ram, vram, "VRAM from name")
        elif vram is None:
            print("    (could not parse VRAM from name)")

    print("\n--- Paste block for Docs/Workflow.md (fill in after you read Ghidra) ---")
    print("| Check | Your Ghidra conclusion |")
    print("|-------|-------------------------|")
    print("| Any rodata boundary with suspicious exec xrefs | (see section B) |")
    print("| Tail ROM undefined ratio vs real code | (see section C) |")
    print("| BSS @ 0x8027F050 matches linker intent | (see section E) |")
    print("| Dup candidates: splat `func_*` vs Ghidra label at parsed VRAM (see section G) | |")

    print("\nDone.")


main()
