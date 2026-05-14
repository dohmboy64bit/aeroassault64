# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): **incoming xrefs** to a tunable **`.ram`** base + word offsets, optional
# **big-endian word** dump at each offset, and whether the stored word looks like a pointer into
# **`.rom`** (cart file offset per **`rom_file_offset`** in **`Find_RSP_Microcode_ROM_Hints.py`**).
#
# Use after **`RSP_Function_Return_Reg_Slice.py`** prints a global return like **`v0 = 0x802839B0`**
# (AFA USA **`FUN_8023d820`**): set **`BASE_VRAM`** to that address and **`FIELD_OFFSETS`** to
# **`(0x8, 0xC)`** (or include **`0`** to see the block head) to find **who reads/writes** the
# words passed as **`lw a2,0x8(s2)`** / **`lw a3,0xc(s2)`** toward **`text_offset` / `text_size`**
# (**`config/afa_rsp/*.template.toml`**, **`lib/Zelda64Recomp/AFA_PORT.md`** §1).
#
# Same **`.ram` / `.rom`** blocks as **`Phase2_Closeout_Report.py`**. Heuristic only — verify in Listing.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; pairs with RSP_Function_Return_Reg_Slice.py
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_RAM_Context_Field_Xrefs
#@description Incoming xrefs + BE words at RAM base+offsets (RSP ctx / ROM pointer trail)
#@author AeroAssault64

from __future__ import print_function

# --- Tunables -----------------------------------------------------------------
# AFA USA: **`v0`** from **`FUN_8023d820`** (`lui`/`addiu` chain in **`RSP_Function_Return_Reg_Slice`**).
BASE_VRAM = 0x802839B0

# Word offsets (bytes) from **`BASE_VRAM`** to report (**MIPS `lw` off struct** style).
FIELD_OFFSETS = (
    0,
    0x8,
    0xC,
)

# Cap listing length per field (raise if truncated).
MAX_REFS_TO_PRINT = 50

# If True, try **`Memory.getBytes`** for 4 bytes at each field (undefined memory prints a note).
READ_BE_WORD_AT_EACH_FIELD = True

# If True, list **branch/jump** xrefs (FLOW) as well as **DATA** xrefs. FLOW hits mean “this
# address is a label / jump table slot”, not “someone loaded the word here” — see printed `kind=`.
SHOW_FLOW_INCOMING = True

# If True, list outgoing **FLOW** refs (code at this VA). Often code/data overlap in `.bss` —
# treat as Listing hint, not a stored pointer.
SHOW_FLOW_OUTGOING = True


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


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


def rom_file_offset(rom, addr):
    """Byte offset into cart image if addr lies in .rom; else None (same idea as Find_RSP_*)."""
    if rom is None or addr is None:
        return None
    if not rom.contains(addr):
        return None
    return int(addr.getOffset() - rom.getStart().getOffset())


def read_u32_be(mem, addr):
    buf = bytearray(4)
    try:
        if mem.getBytes(addr, buf) != 4:
            return None
    except Exception:
        return None
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3]


def _fn_label(fm, addr):
    if addr is None:
        return "(unknown)"
    fn = fm.getFunctionContaining(addr)
    if fn is None:
        return "(no function)"
    return "%s" % fn.getName()


def _ref_kind(rt):
    """FLOW = branch/jump/call edge; DATA = memory ref; OTHER."""
    try:
        if rt.isCall():
            return "FLOW"
        if rt.isJump() or rt.isConditional() or rt.isUnconditional():
            return "FLOW"
        if rt.isData() or rt.isRead() or rt.isWrite():
            return "DATA"
    except Exception:
        pass
    return "OTHER"


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    ref_mgr = prog.getReferenceManager()
    fm = prog.getFunctionManager()

    ram = get_block_exact(mem, ".ram")
    rom = get_block_exact(mem, ".rom")
    if ram is None:
        print("ERROR: need MemoryBlock `.ram`.")
        return
    if rom is None:
        print("WARNING: no `.rom` block — ROM file offsets for stored pointers will be skipped.")

    space = ram.getStart().getAddressSpace()
    try:
        base = space.getAddress(int(BASE_VRAM))
    except Exception:
        print("ERROR: bad BASE_VRAM.")
        return

    if not ram.contains(base):
        print("ERROR: BASE_VRAM not inside `.ram`.")
        return

    print("=== RSP_RAM_Context_Field_Xrefs (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("Base: %s  (offsets: %s)" % (base, ", ".join("+0x%X" % o for o in FIELD_OFFSETS)))
    print("")

    zero_reads = 0
    nonzero_reads = 0

    for off in FIELD_OFFSETS:
        try:
            faddr = base.add(off)
        except Exception:
            print("--- offset +0x%X: (bad address) ---" % off)
            continue

        print("--- field +0x%X @ %s ---" % (off, faddr))

        if READ_BE_WORD_AT_EACH_FIELD:
            w = read_u32_be(mem, faddr)
            if w is None:
                print("  stored word: (could not read 4 bytes — undefined or gap)")
            else:
                print("  stored word (BE u32): 0x%08X" % w)
                if w == 0:
                    zero_reads += 1
                else:
                    nonzero_reads += 1
                try:
                    p = space.getAddress(int(w) & 0xFFFFFFFF)
                    roff = rom_file_offset(rom, p)
                    if roff is not None:
                        print(
                            "    -> points into `.rom` at file offset 0x%X (RSPRecomp `text_offset` candidate — verify)"
                            % roff
                        )
                    elif int(w) & 0xF0000000 == 0x80000000 or int(w) & 0xF0000000 == 0xA0000000:
                        if ram.contains(p):
                            print("    -> KSEG0/KSEG1 address in `.ram` (not .rom) @ %s" % p)
                        else:
                            print("    -> KSEG-like pointer %s (not in .ram start — check map)" % p)
                except Exception as ex:
                    print("    -> (could not decode pointer: %s)" % ex)

        raw_in = list(_iter_references_to(ref_mgr, faddr))
        flow_in = sum(1 for r in raw_in if _ref_kind(r.getReferenceType()) == "FLOW")
        data_in = sum(1 for r in raw_in if _ref_kind(r.getReferenceType()) == "DATA")
        refs = raw_in if SHOW_FLOW_INCOMING else [r for r in raw_in if _ref_kind(r.getReferenceType()) != "FLOW"]
        print(
            "  incoming xrefs: %d raw (FLOW=%d DATA=%d)%s"
            % (
                len(raw_in),
                flow_in,
                data_in,
                "" if SHOW_FLOW_INCOMING else " — listing excludes FLOW",
            )
        )
        n = 0
        for ref in refs[:MAX_REFS_TO_PRINT]:
            n += 1
            fa = ref.getFromAddress()
            rt = ref.getReferenceType()
            try:
                rts = rt.toString()
            except Exception:
                rts = str(rt)
            ins = prog.getListing().getInstructionAt(fa)
            ins_s = ins.toString().replace("\n", " ")[:72] if ins is not None else "(data label?)"
            rk = _ref_kind(rt)
            print(
                "    [%d] kind=%s  from %s  type=%s  fn=%s"
                % (n, rk, fa, rts, _fn_label(fm, fa))
            )
            print("         %s" % ins_s)
        if len(refs) > MAX_REFS_TO_PRINT:
            print("    ... truncated (%d more)" % (len(refs) - MAX_REFS_TO_PRINT))

        out_raw = list(_iter_references_from(ref_mgr, faddr))
        out_refs = (
            out_raw if SHOW_FLOW_OUTGOING else [r for r in out_raw if _ref_kind(r.getReferenceType()) != "FLOW"]
        )
        if out_raw:
            oflow = sum(1 for r in out_raw if _ref_kind(r.getReferenceType()) == "FLOW")
            odata = sum(1 for r in out_raw if _ref_kind(r.getReferenceType()) == "DATA")
            print(
                "  outgoing xrefs: %d raw (FLOW=%d DATA=%d)%s"
                % (
                    len(out_raw),
                    oflow,
                    odata,
                    "" if SHOW_FLOW_OUTGOING else " — listing excludes FLOW",
                )
            )
            if out_refs:
                for i, ref in enumerate(out_refs[:15], 1):
                    ta = ref.getToAddress()
                    rt = ref.getReferenceType()
                    try:
                        rts = rt.toString()
                    except Exception:
                        rts = str(rt)
                    rk = _ref_kind(rt)
                    roff = rom_file_offset(rom, ta)
                    extra = ""
                    if rk == "DATA" and roff is not None:
                        extra = "  -> .rom file offset 0x%X" % roff
                    print("    [%d] kind=%s  to %s  type=%s%s" % (i, rk, ta, rts, extra))
                if len(out_refs) > 15:
                    print("    ... %d more" % (len(out_refs) - 15))
            elif not SHOW_FLOW_OUTGOING and oflow > 0:
                print("    (all outgoing refs are FLOW — enable SHOW_FLOW_OUTGOING to list them)")

        print("")

    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; `text_offset`/`text_size` in config/afa_rsp/*.template.toml")
    if READ_BE_WORD_AT_EACH_FIELD and zero_reads > 0 and nonzero_reads == 0:
        print("")
        print("Note: every readable field was 0x0 in the static image — common for .bss zero-init")
        print("      and runtime `sw` fills before `lw a2,0x8(s2)` sees real src/size. Trace writers")
        print("      to this base (e.g. xref from FUN_80283824) or use emulator RAM.")
        print("      Incoming kind=FLOW = control-flow to this address (e.g. `beq` label), not a load")
        print("      of the stored word. Outgoing kind=FLOW = jump from bytes at this VA (code/data mix).")


main()
