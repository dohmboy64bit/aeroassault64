# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): clear mistaken data listing on splat `post_data` tail in `.ram`,
# disassemble that span, then create a function at VRAM 0x80256D70 (ROM 0x57D20).
#
# Matches `config/splat.yaml` main segment: `[0x57D20, asm, post_data]` and
# `Phase3_Closeout_Report.py` (EXP_TAIL_ENTRY_VRAM / ROM_OFF_TAIL / ROM_END).
#
# Docs: Ghidra `Listing.clearCodeUnits`, `CreateFunctionCmd`
#   — https://ghidra.re/ghidra_docs/api/ghidra/app/cmd/function/CreateFunctionCmd.html
#   `Disassembler` lives in `ghidra.program.disassemble` (not `ghidra.app.util.disassembler`):
#   https://ghidra.re/ghidra_docs/api/ghidra/program/disassemble/Disassembler.html
#
# Run: same as Phase2/Phase3 — `support/pyghidraRun.bat`, Script Manager, repo `tools/ghidra`.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name Phase3_Ensure_PostData_Function
#@description Phase 3 — clear .ram post_data tail, disassemble, create function at 0x80256D70
#@author AeroAssault64

from __future__ import print_function

# --- Sync with config/splat.yaml + Phase3_Closeout_Report.py --------------------
ROM_OFF_TAIL = 0x57D20
ROM_END = 0x800000
EXP_TAIL_ENTRY_VRAM = 0x80256D70
EXP_BSS_VRAM = 0x8027F050  # splat bss VMA — do not clear at or past this address

# If True, only print the computed `.ram` range and exit (no DB changes).
DRY_RUN = False

# If False, refuse to run when the first big-endian word at the entry is not this value
# (observed on USA ROM at RAM mirror of ROM+0x57D20 — see Docs/Workflow.md / Phase3 report).
# Set to None to skip the check.
EXPECTED_ENTRY_BE32 = 0x27BDFF98

# If True, allow EXPECTED_ENTRY_BE32 mismatch (still clears/disassembles — use with care).
FORCE = False

# Disassembler: follow flows within the cleared span (Ghidra Disassembler.disassemble).
FOLLOW_FLOWS = True


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def vram_to_addr_in_ram(ram_block, vram):
    if ram_block is None:
        return None
    base = ram_block.getStart()
    delta = int(vram) - int(base.getOffset())
    if delta < 0:
        return None
    return base.add(delta)


def _u8(mem, addr):
    return mem.getByte(addr) & 0xFF


def read_be32(mem, addr):
    return (
        (_u8(mem, addr) << 24)
        | (_u8(mem, addr.add(1)) << 16)
        | (_u8(mem, addr.add(2)) << 8)
        | _u8(mem, addr.add(3))
    )


def _addr_min(a, b):
    return a if a.compareTo(b) <= 0 else b


def main():
    from ghidra.app.cmd.function import CreateFunctionCmd
    from ghidra.program.disassemble import Disassembler
    from ghidra.program.model.address import AddressRangeImpl
    from ghidra.program.model.address import AddressSet
    from ghidra.util.task import ConsoleTaskMonitor

    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    monitor = ConsoleTaskMonitor()
    ram = get_block_exact(mem, ".ram")

    tail_len = ROM_END - ROM_OFF_TAIL
    print("=== Phase3_Ensure_PostData_Function ===")
    print("Program: %s" % prog.getName())
    print(
        "Target: splat `post_data` entry VRAM 0x%08X (ROM 0x%X .. 0x%X, len 0x%X)"
        % (EXP_TAIL_ENTRY_VRAM, ROM_OFF_TAIL, ROM_END - 1, tail_len)
    )

    if ram is None:
        print("ERROR: need MemoryBlock named exactly `.ram`")
        return

    start_addr = vram_to_addr_in_ram(ram, EXP_TAIL_ENTRY_VRAM)
    if start_addr is None or not mem.contains(start_addr):
        print("ERROR: could not map VRAM 0x%X into `.ram`" % EXP_TAIL_ENTRY_VRAM)
        return

    bss_addr = vram_to_addr_in_ram(ram, EXP_BSS_VRAM)
    if bss_addr is not None:
        # Never clear into splat linker BSS VMA or beyond
        last_allowed = bss_addr.subtract(1)
    else:
        last_allowed = ram.getEnd()

    desired_last = start_addr.add(tail_len - 1)
    end_inclusive = _addr_min(desired_last, _addr_min(last_allowed, ram.getEnd()))

    if end_inclusive.compareTo(start_addr) < 0:
        print("ERROR: empty or invalid span after clipping")
        return

    if end_inclusive.compareTo(desired_last) < 0:
        print(
            "WARNING: clipped end from %s to %s (BSS at 0x%X or `.ram` end)"
            % (desired_last, end_inclusive, EXP_BSS_VRAM)
        )

    span = AddressSet()
    span.add(AddressRangeImpl(start_addr, end_inclusive))
    print("`.ram` span (inclusive): %s .. %s" % (start_addr, end_inclusive))

    w0 = read_be32(mem, start_addr)
    print("First word @ entry (bytes): 0x%08X" % w0)

    if EXPECTED_ENTRY_BE32 is not None and (w0 & 0xFFFFFFFF) != (EXPECTED_ENTRY_BE32 & 0xFFFFFFFF):
        print(
            "Expected first word 0x%08X per repo / Phase3 report; got 0x%08X."
            % (EXPECTED_ENTRY_BE32, w0)
        )
        if not FORCE:
            print("Aborting (set FORCE = True or EXPECTED_ENTRY_BE32 = None to override).")
            return

    fn_existing = listing.getFunctionContaining(start_addr)
    ins0 = listing.getInstructionAt(start_addr)
    if (
        fn_existing is not None
        and fn_existing.getEntryPoint().equals(start_addr)
        and ins0 is not None
    ):
        print("OK: function already at entry with instruction: %s" % fn_existing.getName())
        print("    (No changes — remove the function first if you want a full redo.)")
        return

    if DRY_RUN:
        print("DRY_RUN: no listing changes.")
        return

    print("Starting transaction: clear + disassemble + CreateFunctionCmd ...")
    tx = prog.startTransaction("Phase3 post_data tail")
    ok = False
    try:
        # Ghidra 12+ ListingDB: clearCodeUnits(Address, Address, boolean, TaskMonitor)
        # (AddressSet overload not present on all builds — see Ghidra Listing / CodeManager API.)
        listing.clearCodeUnits(start_addr, end_inclusive, False, monitor)
        dis = Disassembler.getDisassembler(prog, monitor, None)
        dis_ok = dis.disassemble(start_addr, span, FOLLOW_FLOWS)
        if dis_ok is False:
            print("WARNING: disassemble() returned false (partial disasm is still possible).")

        cmd = CreateFunctionCmd(start_addr)
        if not cmd.applyTo(prog, monitor):
            msg = cmd.getStatusMsg() if hasattr(cmd, "getStatusMsg") else "(no status)"
            print("ERROR: CreateFunctionCmd failed: %s" % msg)
            return

        new_fn = cmd.getFunction() if hasattr(cmd, "getFunction") else listing.getFunctionAt(start_addr)
        print("OK: created function: %s" % (new_fn if new_fn else listing.getFunctionContaining(start_addr)))
        ok = True
    finally:
        prog.endTransaction(tx, ok)

    if ok:
        ins0 = listing.getInstructionAt(start_addr)
        print("Instruction at entry: %s" % ins0)


main()
