# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): find RSP SP physical window usage (0x04000000..0x04001FFF) and optional
# call-site windows for a DMA/SP helper (e.g. FUN_80246fd0 in AFA USA decompilation).
#
# Use when decompiler shows patterns like:
#   FUN_80246fd0(1, 0x4001000, *(ctx+8), *(ctx+0xc));  // IMEM + plausible src/size
# Static analysis cannot prove register values at jal sites — this script gives *where* those
# constants appear and *where* calls to your helper happen so you can read a0-a3 in Listing.
# For callee **entry** hex values, run tools/ghidra/RSP_List_Jal_Callees_From_Function.py
# (set SOURCE_FUNCTION_ENTRY_VRAM to this function, e.g. 0x8023D92C). For all `jal` arg-setup
# windows from that caller in one pass, run tools/ghidra/RSP_Jal_Call_Sites_Disasm_From_Caller.py.
#
# Hardware map: N64brew Memory map — SP DMEM/IMEM physical `0x04000000` region.
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; tools/ghidra/Find_RSP_Microcode_ROM_Hints.py
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_IMEM_Load_And_Helper_Call_Trace
#@description Scan .ram for 0x0400… SP addresses + optional jal xref windows to a helper
#@author AeroAssault64

from __future__ import print_function

# --- Tunables -----------------------------------------------------------------
# Inclusive low / exclusive high of the 32-bit physical addresses used in MIPS immediates
# for SP DMEM/IMEM (see N64brew memory map).
SP_PHYS_LO = 0x04000000
SP_PHYS_HI = 0x04002000

# Extra immediates seen next to IMEM setup in your snippet (optional noise — comment out).
EXTRA_IMMEDIATES = (
    0x00002B00,
)

# If set (KSEG0 int), print incoming *call* xrefs and a short disassembly window before each.
# Example AFA USA: 0x80246FD0 for FUN_80246fd0 once you confirm the entry in your database.
HELPER_ENTRY_VRAM = None  # e.g. 0x80246FD0

MAX_SCALAR_HITS = 120
MAX_LUI_PAIR_HITS = 120
MAX_EXTRA_IMM_HITS = 40
MAX_HELPER_CALL_SITES = 25
INSN_WINDOW_BEFORE = 10


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def memory_block_as_address_set(block):
    from ghidra.program.model.address import AddressRangeImpl
    from ghidra.program.model.address import AddressSet

    aset = AddressSet()
    aset.add(AddressRangeImpl(block.getStart(), block.getEnd()))
    return aset


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


def _iter_references_to(ref_mgr, addr):
    refs = ref_mgr.getReferencesTo(addr)
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


def _scalar_unsigned(obj):
    try:
        from ghidra.program.model.scalar import Scalar

        if isinstance(obj, Scalar):
            return int(obj.getUnsignedValue()) & 0xFFFFFFFF
    except Exception:
        pass
    return None


def _first_register_name(ins, op_index):
    try:
        from ghidra.program.model.lang import Register

        for ob in ins.getOpObjects(op_index):
            if isinstance(ob, Register):
                return ob.getName()
    except Exception:
        pass
    return None


def _lui_upper(ins):
    if ins is None or ins.getMnemonicString().lower() != "lui" or ins.getNumOperands() < 2:
        return None
    dest = _first_register_name(ins, 0)
    imm = None
    for ob in ins.getOpObjects(1):
        v = _scalar_unsigned(ob)
        if v is not None:
            imm = v & 0xFFFF
            break
    if dest is None or imm is None:
        return None
    return (dest, imm << 16)


def _addiu_or_ori_imm(ins):
    _nil = (None, None, None, None)
    if ins is None:
        return _nil
    mn = ins.getMnemonicString().lower()
    if mn not in ("addiu", "addi", "ori", "daddiu", "daddi"):
        return _nil
    if ins.getNumOperands() < 3:
        return _nil
    rt = _first_register_name(ins, 0)
    rs = _first_register_name(ins, 1)
    imm = None
    for ob in ins.getOpObjects(2):
        v = _scalar_unsigned(ob)
        if v is not None:
            imm = v & 0xFFFF
            break
    if rt is None or rs is None or imm is None:
        return _nil
    return mn, rt, rs, imm


def _combine_hi_lo(mn, hi32, imm16):
    imm16 &= 0xFFFF
    if mn in ("ori",):
        return (hi32 & 0xFFFF0000) | imm16
    if imm16 & 0x8000:
        simm = imm16 - 0x10000
    else:
        simm = imm16
    return (hi32 + simm) & 0xFFFFFFFF


def _in_sp_window(u32):
    return SP_PHYS_LO <= u32 < SP_PHYS_HI


def _instructions_backward(listing, ins, n_before, min_addr=None):
    """Instructions strictly before `ins`, oldest-first. See RSP_Jal_Call_Sites_Disasm_From_Caller."""
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


def _print_insn_window(listing, fm, from_addr, n_before):
    ins = listing.getInstructionContaining(from_addr)
    if ins is None:
        print("      (no Instruction at xref %s)" % from_addr)
        return
    min_addr = None
    try:
        f = fm.getFunctionContaining(from_addr)
        if f is not None:
            min_addr = f.getBody().getMinAddress()
    except Exception:
        pass
    chain = _instructions_backward(listing, ins, n_before, min_addr)
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
        "      %s  [%s]  %s  << call xref"
        % (ins.getAddress(), fnn, ins.toString().replace("\n", " ")[:100])
    )


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

    ram_set = memory_block_as_address_set(ram)
    space = ram.getStart().getAddressSpace()

    print("=== RSP_IMEM_Load_And_Helper_Call_Trace (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print(
        "SP physical window for immediates: 0x%08X .. 0x%08X (see N64brew memory map)"
        % (SP_PHYS_LO, SP_PHYS_HI - 1)
    )
    print("")

    # --- Scalar operands in SP window -----------------------------------------
    print("--- .ram instructions: operand Scalar in SP DMEM/IMEM window ---")
    n = 0
    ins_it = listing.getInstructions(ram_set, True)
    for ins in _iter_listing_cursor(ins_it):
        if n >= MAX_SCALAR_HITS:
            break
        try:
            nops = ins.getNumOperands()
        except Exception:
            continue
        for opi in range(nops):
            for ob in ins.getOpObjects(opi):
                v = _scalar_unsigned(ob)
                if v is None or not _in_sp_window(v):
                    continue
                try:
                    fn = fm.getFunctionContaining(ins.getAddress())
                    fnn = fn.getName() if fn is not None else "?"
                except Exception:
                    fnn = "?"
                print(
                    "  0x%08X  @ %s  [%s]  %s"
                    % (
                        v,
                        ins.getAddress(),
                        fnn,
                        ins.toString().replace("\n", " ")[:110],
                    )
                )
                n += 1
                if n >= MAX_SCALAR_HITS:
                    break
            if n >= MAX_SCALAR_HITS:
                break
        if n >= MAX_SCALAR_HITS:
            break
    if n == 0:
        print(
            "  (no Scalar hits — constants may be lui+addiu only; see next section.)"
        )
    print("")

    # --- LUI + ADDIU/ORI -> full address in window -----------------------------
    print("--- .ram: lui + addiu/ori -> address in SP window ---")
    pending_lui = {}
    n2 = 0
    ins_it = listing.getInstructions(ram_set, True)
    for ins in _iter_listing_cursor(ins_it):
        if n2 >= MAX_LUI_PAIR_HITS:
            break
        lui = _lui_upper(ins)
        if lui is not None:
            reg, hi = lui
            pending_lui[reg] = (hi, ins.getAddress())
            continue
        parsed = _addiu_or_ori_imm(ins)
        if parsed[0] is None:
            continue
        mn, rt, rs, imm16 = parsed
        if rs not in pending_lui:
            continue
        hi32, lui_addr = pending_lui[rs]
        full = _combine_hi_lo(mn, hi32, imm16) & 0xFFFFFFFF
        if not _in_sp_window(full):
            if mn.startswith("addi") and rt == rs:
                pending_lui.pop(rs, None)
            continue
        try:
            fn = fm.getFunctionContaining(ins.getAddress())
            fnn = fn.getName() if fn is not None else "?"
        except Exception:
            fnn = "?"
        print(
            "  -> 0x%08X  @ %s  [%s]  (lui @ %s)  %s"
            % (
                full,
                ins.getAddress(),
                fnn,
                lui_addr,
                ins.toString().replace("\n", " ")[:90],
            )
        )
        n2 += 1
        if mn.startswith("addi") and rt == rs:
            pending_lui.pop(rs, None)
    if n2 == 0:
        print("  (no lui+lo pairs into SP window in linear scan.)")
    print("")

    # --- Extra immediates (snippet: 0x2b00) ------------------------------------
    if EXTRA_IMMEDIATES:
        print("--- .ram: EXTRA_IMMEDIATES (Scalar match only) ---")
        n3 = 0
        want = set(EXTRA_IMMEDIATES)
        ins_it = listing.getInstructions(ram_set, True)
        for ins in _iter_listing_cursor(ins_it):
            if n3 >= MAX_EXTRA_IMM_HITS:
                break
            try:
                nops = ins.getNumOperands()
            except Exception:
                continue
            for opi in range(nops):
                for ob in ins.getOpObjects(opi):
                    v = _scalar_unsigned(ob)
                    if v is None or v not in want:
                        continue
                    try:
                        fn = fm.getFunctionContaining(ins.getAddress())
                        fnn = fn.getName() if fn is not None else "?"
                    except Exception:
                        fnn = "?"
                    print(
                        "  0x%08X  @ %s  [%s]  %s"
                        % (
                            v,
                            ins.getAddress(),
                            fnn,
                            ins.toString().replace("\n", " ")[:110],
                        )
                    )
                    n3 += 1
                    if n3 >= MAX_EXTRA_IMM_HITS:
                        break
                if n3 >= MAX_EXTRA_IMM_HITS:
                    break
            if n3 >= MAX_EXTRA_IMM_HITS:
                break
        if n3 == 0:
            print("  (no hits)")
        print("")

    # --- Optional: call sites to HELPER_ENTRY_VRAM ----------------------------
    if HELPER_ENTRY_VRAM is not None:
        try:
            haddr = space.getAddress(int(HELPER_ENTRY_VRAM))
        except Exception:
            haddr = None
        print(
            "--- Incoming calls to helper @ 0x%X (VRAM) ---" % int(HELPER_ENTRY_VRAM)
        )
        if haddr is None or not ram.contains(haddr):
            print("  ERROR: bad HELPER_ENTRY_VRAM for this address space.")
        else:
            sites = 0
            for ref in _iter_references_to(ref_mgr, haddr):
                if not ref.getReferenceType().isCall():
                    continue
                fa = ref.getFromAddress()
                if not ram.contains(fa):
                    continue
                try:
                    fn = fm.getFunctionContaining(fa)
                    fnn = fn.getName() if fn is not None else "?"
                except Exception:
                    fnn = "?"
                print("  Call site %s  in  %s" % (fa, fnn))
                _print_insn_window(listing, fm, fa, INSN_WINDOW_BEFORE)
                print("")
                sites += 1
                if sites >= MAX_HELPER_CALL_SITES:
                    print("  (... truncated; raise MAX_HELPER_CALL_SITES)")
                    break
            if sites == 0:
                print(
                    "  (no incoming *call* xrefs — confirm entry address or run auto-analysis)"
                )
        print("")

    print("Manual: at each call site, identify a0-a3 in MIPS o32 ABI (arg0..arg3).")
    print("  Third/fourth args often map to DRAM source + length for ucode DMA; map DRAM")
    print("  pointer back to `.rom` file offset (Ghidra .rom block) for RSPRecomp text_offset.")
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1.")


main()
