# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): list every `jal` callee from a named function body (entry VRAM + symbol).
#
# Automates "follow each jal from FUN_8023d92c to get helper entry addresses" for
# RSP_IMEM_Load_And_Helper_Call_Trace.py HELPER_ENTRY_VRAM tuning.
#
# Same `.ram` layout as Phase2_Closeout_Report.py. Does not resolve `jalr` / indirect calls.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_List_Jal_Callees_From_Function
#@description Print jal targets (callee entry + name) from a tunable function VRAM
#@author AeroAssault64

from __future__ import print_function

# --- Tunables -----------------------------------------------------------------
# KSEG0 VRAM of the *caller* function entry (must lie in `.ram`).
# AFA USA example: FUN_8023d92c (your IMEM / 0x2b00 setup path).
SOURCE_FUNCTION_ENTRY_VRAM = 0x8023D92C

# If True, only print rows where callee name matches this substring (case-insensitive).
# Example: "80246f" to narrow to FUN_80246f80 / FUN_80246f90 / FUN_80246fd0 style names.
CALLEE_NAME_FILTER = ""  # "" = show all


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def _iter_listing_cursor(cursor):
    if cursor is None:
        return
    if hasattr(cursor, "hasNext") and callable(getattr(cursor, "hasNext", None)):
        while cursor.hasNext():
            yield cursor.next()
        return
    try:
        for item in cursor:
            yield item
    except TypeError:
        pass


def _iter_references_from(ref_mgr, addr):
    refs = ref_mgr.getReferencesFrom(addr)
    if refs is None:
        return
    if hasattr(refs, "hasNext") and callable(getattr(refs, "hasNext", None)):
        while refs.hasNext():
            yield refs.next()
        return
    try:
        for ref in refs:
            yield ref
    except TypeError:
        pass


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    ref_mgr = prog.getReferenceManager()
    fm = prog.getFunctionManager()

    ram = get_block_exact(mem, ".ram")
    if ram is None:
        print("ERROR: need MemoryBlock `.ram`.")
        return

    space = ram.getStart().getAddressSpace()
    try:
        entry = space.getAddress(int(SOURCE_FUNCTION_ENTRY_VRAM))
    except Exception:
        print("ERROR: bad SOURCE_FUNCTION_ENTRY_VRAM.")
        return

    if not ram.contains(entry):
        print("ERROR: SOURCE_FUNCTION_ENTRY_VRAM not inside `.ram`.")
        return

    fn = fm.getFunctionContaining(entry)
    if fn is None:
        print("ERROR: no Function at 0x%X — create function first." % int(SOURCE_FUNCTION_ENTRY_VRAM))
        return

    # Warn if user address is not the canonical entry (still scan containing fn).
    if int(fn.getEntryPoint().getOffset()) != int(entry.getOffset()):
        print(
            "NOTE: 0x%X is inside %s @ %s (scanning whole caller)."
            % (int(SOURCE_FUNCTION_ENTRY_VRAM), fn.getName(), fn.getEntryPoint())
        )

    filt = (CALLEE_NAME_FILTER or "").strip().lower()

    print("=== RSP_List_Jal_Callees_From_Function (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print(
        "Caller: %s  entry=%s  body=%s .. %s"
        % (
            fn.getName(),
            fn.getEntryPoint(),
            fn.getBody().getMinAddress(),
            fn.getBody().getMaxAddress(),
        )
    )
    if filt:
        print("Filter: callee name contains %r" % CALLEE_NAME_FILTER)
    print("")
    print("  %-14s  %-14s  %s" % ("jal @", "callee entry", "callee name"))
    print("  " + "-" * 60)

    n = 0
    distinct = set()
    for ins in _iter_listing_cursor(listing.getInstructions(fn.getBody(), True)):
        if ins.getMnemonicString().lower() != "jal":
            continue
        for ref in _iter_references_from(ref_mgr, ins.getAddress()):
            if not ref.getReferenceType().isCall():
                continue
            to_a = ref.getToAddress()
            if to_a is None:
                continue
            callee = fm.getFunctionAt(to_a)
            if callee is None:
                print(
                    "  %-14s  %-14s  (no Function — target %s)"
                    % (ins.getAddress(), to_a, to_a)
                )
                n += 1
                continue
            cname = callee.getName()
            cent = callee.getEntryPoint()
            if filt and filt not in cname.lower():
                continue
            distinct.add(int(cent.getOffset()))
            print("  %-14s  %-14s  %s" % (ins.getAddress(), cent, cname))
            n += 1

    print("")
    print("`jal` sites printed: %d   distinct callee entries: %d" % (n, len(distinct)))
    print(
        "Copy callee **entry** hex into RSP_IMEM_Load_And_Helper_Call_Trace.py -> HELPER_ENTRY_VRAM."
    )
    print(
        "Or run tools/ghidra/RSP_Jal_Call_Sites_Disasm_From_Caller.py to dump all `jal` windows from this caller in one pass."
    )
    print("`jalr` / indirect calls are not scanned — use Listing xrefs for those.")


main()
