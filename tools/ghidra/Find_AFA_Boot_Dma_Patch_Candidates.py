# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): locate AFA USA boot / PI DMA functions to patch for recomp_load_overlays.
#
# Confirmed in-repo (asm/, config/symbol_addrs.txt):
#   entrypoint @ 0x80200050 -> main @ 0x80231150 (asm/1000.s, asm/31B30.s)
#   func_80248B70 @ 0x80248B70 — PI regs 0xA460 (cart DMA) — primary PatchesLib target (patches/afa/required_patches_afa.c)
#   func_8023E3A0 — early init from main; installs DMA func pointers including func_80248B70 (asm/3F660.s)
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md §2; patches/afa/README.txt
#
#@runtime PyGhidra
#@category AeroAssault64
#@name Find_AFA_Boot_Dma_Patch_Candidates
#@description List PI DMA helpers, boot chain, and recomp_load_overlays patch VRAs
#@author AeroAssault64

from __future__ import print_function

# Known anchors from splat / asm (adjust if your Ghidra names differ).
ENTRYPOINT_VRAM = 0x80200050
MAIN_VRAM = 0x80231150
PI_DMA_WRITE_VRAM = 0x80248B70
PI_DMA_READ_VRAM = 0x80248C50
BOOT_INIT_VRAM = 0x8023E3A0
DMA_TABLE_INSTALL_VRAM = 0x8023E760

# PI / SI register windows (N64brew memory map).
PI_REG_PHYS = 0xA4600000
SI_REG_PHYS = 0xA4800000
PI_STATUS_OFFSET = 0x10

MAX_PI_FUNCS = 40
MAX_CALLERS_PER_FUNC = 12
INSN_WINDOW = 8


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def vram_to_addr(prog, vram):
    from ghidra.program.model.address import GenericAddress

    ram = get_block_exact(prog.getMemory(), ".ram")
    if ram is None:
        return None
    off = vram - ram.getStart().getOffset()
    if off < 0 or off >= ram.getSize():
        return None
    return ram.getStart().add(off)


def func_at_vram(func_mgr, vram):
    addr = vram_to_addr(currentProgram, vram)
    if addr is None:
        return None
    f = func_mgr.getFunctionAt(addr)
    if f is None:
        f = func_mgr.getFunctionContaining(addr)
    return f


def _iter_scalar_immediates(listing, ram, lo, hi_excl):
    from ghidra.program.model.scalar import Scalar

    results = []
    ins_iter = listing.getInstructions(ram, True)
    while ins_iter.hasNext():
        ins = ins_iter.next()
        for i in range(ins.getNumOperands()):
            objs = ins.getOpObjects(i)
            if objs is None:
                continue
            for obj in objs:
                if isinstance(obj, Scalar):
                    val = obj.getValue()
                    if lo <= val < hi_excl:
                        results.append((ins.getAddress(), val))
    return results


def _function_callers(func):
    callers = []
    ref_mgr = currentProgram.getReferenceManager()
    entry = func.getEntryPoint()
    for ref in ref_mgr.getReferencesTo(entry):
        from_addr = ref.getFromAddress()
        caller = currentProgram.getFunctionManager().getFunctionContaining(from_addr)
        if caller is not None:
            name = caller.getName()
            if name not in callers:
                callers.append(name)
        if len(callers) >= MAX_CALLERS_PER_FUNC:
            break
    return callers


def main():
    prog = currentProgram
    if prog is None:
        print("No program open.")
        return

    listing = prog.getListing()
    func_mgr = prog.getFunctionManager()
    ram = get_block_exact(prog.getMemory(), ".ram")
    if ram is None:
        print("Missing .ram block — import splat ELF with .ram @ 0x80200050.")
        return

    print("=== AFA boot / DMA patch candidates ===")
    print("Primary patch VRAs (patches/afa/required_patches_afa.c):")
    print("  func_80248B70 @ 0x{:08X}  (osEPiStartDma-style write)".format(PI_DMA_WRITE_VRAM))
    print("  func_80248C50 @ 0x{:08X}  (osEPiStartDma-style read)".format(PI_DMA_READ_VRAM))
    print("")
    print("Boot chain (config/symbol_addrs.txt, asm/1000.s, asm/31B30.s):")
    for label, vram in (
        ("entrypoint", ENTRYPOINT_VRAM),
        ("main", MAIN_VRAM),
        ("func_8023E3A0 (init, calls DMA setup)", BOOT_INIT_VRAM),
        ("func_8023E760 (installs DMA vtable)", DMA_TABLE_INSTALL_VRAM),
    ):
        fn = func_at_vram(func_mgr, vram)
        nm = fn.getName() if fn else "(no function)"
        print("  0x{:08X}  {}".format(vram, nm))

    print("")
    print("=== Functions referencing PI window 0x{:08X}..0x{:08X} ===".format(
        PI_REG_PHYS, PI_REG_PHYS + 0x1000))
    pi_hits = _iter_scalar_immediates(listing, ram, PI_REG_PHYS, PI_REG_PHYS + 0x1000)
    pi_funcs = {}
    for addr, imm in pi_hits:
        fn = func_mgr.getFunctionContaining(addr)
        if fn is None:
            continue
        pi_funcs.setdefault(fn.getName(), fn)
    for i, (name, fn) in enumerate(sorted(pi_funcs.items())[:MAX_PI_FUNCS]):
        entry = fn.getEntryPoint().getOffset() + ram.getStart().getOffset()
        print("  [{:2d}] {} @ 0x{:08X}  callers(sample): {}".format(
            i, name, entry, ", ".join(_function_callers(fn)[:6]) or "?"))

    anchor = func_at_vram(func_mgr, PI_DMA_WRITE_VRAM)
    if anchor is not None:
        print("")
        print("=== Callers of {} (patch first for overlay loads) ===".format(anchor.getName()))
        for nm in _function_callers(anchor):
            print("  ", nm)

    print("")
    print("Done. Patch with RECOMP_PATCH + recomp_load_overlays(rom_file_off, rdram_vram, size);")
    print("see lib/Zelda64Recomp/patches/afa/required_patches_afa.c and librecomp overlays.cpp load_overlays().")


if __name__ == "__main__":
    main()
