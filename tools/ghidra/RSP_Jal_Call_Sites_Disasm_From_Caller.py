# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): for each `jal` inside a caller function, print a disassembly window before
# the branch (read a0-a3 setup for MIPS o32) + callee entry/name.
#
# Automates re-running RSP_IMEM_Load_And_Helper_Call_Trace.py with every HELPER_ENTRY_VRAM: one
# script walks the caller body only (not all xrefs in the binary). Same `.ram` as Phase2_Closeout.
# Backward disasm: use getInstructionBefore(Address) or Instruction.getPrevious — not
# getInstructionBefore(Instruction) (empty window in PyGhidra).
# For summarized a0-a3 last-def at the same `jal` sites, run tools/ghidra/RSP_Jal_Arg_Register_Slice.py.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_Jal_Call_Sites_Disasm_From_Caller
#@description Disasm window before each jal from a tunable caller (helper arg setup)
#@author AeroAssault64

from __future__ import print_function

# --- Tunables -----------------------------------------------------------------
SOURCE_FUNCTION_ENTRY_VRAM = 0x8023D92C

# Only print `jal` to callees whose *entry* is in this set. Empty tuple = all callees.
# Example: (0x80246FD0, 0x80246F90) to only dump DMA / poll helpers.
ONLY_CALLEE_ENTRIES = ()

# If non-empty string: callee *name* must contain this (case-insensitive). Ignored if
# ONLY_CALLEE_ENTRIES is non-empty.
CALLEE_NAME_FILTER = ""

# Instructions to print before each `jal` (walking backward in listing).
INSN_WINDOW_BEFORE = 12


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


def _instructions_backward(listing, ins, n_before, min_addr=None):
    """
    Return up to n_before instructions strictly before `ins`, oldest-first.
    Ghidra Listing.getInstructionBefore(Address) needs an Address, not an Instruction object.
    Prefer Instruction.getPrevious() when the listing links it.
    """
    out = []
    cur = ins
    for _ in range(n_before):
        prev = None
        if cur is not None:
            try:
                if hasattr(cur, "getPrevious"):
                    prev = cur.getPrevious()
            except Exception:
                prev = None
        if prev is None and cur is not None:
            try:
                prev = listing.getInstructionBefore(cur.getAddress())
            except Exception:
                prev = None
        if prev is None:
            break
        if min_addr is not None and prev.getAddress().compareTo(min_addr) < 0:
            break
        out.insert(0, prev)
        cur = prev
    return out


def _print_window_before_jal(listing, fm, jal_addr, n_before, min_body_addr=None):
    ins = listing.getInstructionContaining(jal_addr)
    if ins is None:
        print("      (no Instruction at %s)" % jal_addr)
        return
    chain = _instructions_backward(listing, ins, n_before, min_body_addr)
    for x in chain:
        try:
            fn = fm.getFunctionContaining(x.getAddress())
            fnn = fn.getName() if fn is not None else "?"
        except Exception:
            fnn = "?"
        print(
            "      %s  [%s]  %s"
            % (x.getAddress(), fnn, x.toString().replace("\n", " ")[:100])
        )
    try:
        fn = fm.getFunctionContaining(ins.getAddress())
        fnn = fn.getName() if fn is not None else "?"
    except Exception:
        fnn = "?"
    print(
        "      %s  [%s]  %s  << jal"
        % (ins.getAddress(), fnn, ins.toString().replace("\n", " ")[:100])
    )


def _callee_allowed(cent, cname, entry_set, name_filt):
    if entry_set:
        return int(cent.getOffset()) in entry_set
    if name_filt:
        return name_filt in cname.lower()
    return True


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

    entry_set = set(int(x) for x in ONLY_CALLEE_ENTRIES) if ONLY_CALLEE_ENTRIES else set()
    name_filt = (CALLEE_NAME_FILTER or "").strip().lower()

    print("=== RSP_Jal_Call_Sites_Disasm_From_Caller (AeroAssault64) ===")
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
    if entry_set:
        print("Filter: ONLY_CALLEE_ENTRIES = %s" % sorted(entry_set))
    elif name_filt:
        print("Filter: callee name contains %r" % CALLEE_NAME_FILTER)
    print("")
    print("MIPS o32 at `jal`: a0=arg0, a1=arg1, a2=arg2, a3=arg3 (often set in insns above).")
    print("")

    n = 0
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
                print("--- jal @ %s -> (no Function) %s ---" % (ins.getAddress(), to_a))
                _print_window_before_jal(
                    listing,
                    fm,
                    ins.getAddress(),
                    INSN_WINDOW_BEFORE,
                    fn.getBody().getMinAddress(),
                )
                print("")
                n += 1
                break
            cname = callee.getName()
            cent = callee.getEntryPoint()
            if not _callee_allowed(cent, cname, entry_set, name_filt):
                continue
            print(
                "--- jal @ %s  ->  %s @ %s ---"
                % (ins.getAddress(), cname, cent)
            )
            _print_window_before_jal(
                listing,
                fm,
                ins.getAddress(),
                INSN_WINDOW_BEFORE,
                fn.getBody().getMinAddress(),
            )
            print("")
            n += 1
            break

    print("Sections printed: %d" % n)
    print("Map DRAM src + len from a2/a3 (or whatever ABI this code uses) back to `.rom` for RSPRecomp.")
    print("See tools/ghidra/RSP_IMEM_Load_And_Helper_Call_Trace.py for SP-window + single-helper xref mode.")


main()
