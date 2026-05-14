# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): for each **`jr ra`** in a function, print a **heuristic last-def** of return
# registers (**`v0`** / **`v1`**) on a **linear backward window** ending at that return (and the
# branch delay slot after **`jr ra`**, if present — MIPS can legally set **`v0`** there).
#
# Use after **`RSP_Jal_Arg_Register_Slice.py`** names a callee whose **`v0`** feeds **`or s2,v0,zero`**
# (AFA USA example: **`FUN_8023d820`** @ **`0x8023D820`** from **`jal @ 8023d944`**). Open the callee
# in Listing, run this script with **`TARGET_FUNCTION_ENTRY_VRAM`** set to that entry, then
# follow **`lui`+`addiu`/`ori`**, **`.rom`** xrefs, or nested **`jal`** return paths toward
# **`text_offset` / `text_size`** (see **`config/afa_rsp/*.template.toml`**, **`AFA_PORT.md`** §1).
#
# **Limitation:** one listing-predecessor chain per return; merges across branches are wrong.
# Verify with the decompiler. Same **`.ram`** block expectations as **`Phase2_Closeout_Report.py`**.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; pairs with RSP_Jal_Arg_Register_Slice.py
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_Function_Return_Reg_Slice
#@description Last-def of v0/v1 before each jr ra in a tunable function (RSP struct pointer hunt)
#@author AeroAssault64

from __future__ import print_function

import re

# --- Tunables -----------------------------------------------------------------
# AFA USA: pointer into **`lw a2,0x8(s2)`** path from **`RSP_Jal_Arg_Register_Slice`** jal hint.
TARGET_FUNCTION_ENTRY_VRAM = 0x8023D820

# Registers to summarize at each **`jr ra`** (MIPS o32 returns **`v0`**, sometimes **`v1`**).
RETURN_REGS = ("v0", "v1")

# Max instructions to walk backward along listing from each **`jr ra`** (not counting **`jr`**).
BACKWARD_MAX = 200

# If True, append the instruction at **`jr_ra + 4`** when it is the branch delay slot.
INCLUDE_BRANCH_DELAY_SLOT = True

# If **`v0`/`v1`** have no in-window def, print last **`jal`** before **`jr ra`** (nested return).
JAL_RETURN_REG_HINT = True

# Print this many oldest→newest disasm lines for context before each **`jr`** (0 = skip).
DISASM_CONTEXT_LINES = 14


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


def _is_jr_ra(ins):
    if ins.getMnemonicString().lower() != "jr":
        return False
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s == "jr ra" or s == "jr $ra":
        return True
    if re.search(r"\bra\b", s) and "jr" in s:
        return True
    return False


def _delay_slot_after(listing, br_ins):
    try:
        nxt = br_ins.getNext()
    except Exception:
        nxt = None
    if nxt is None:
        try:
            nxt = listing.getInstructionAfter(br_ins.getAddress())
        except Exception:
            nxt = None
    if nxt is None:
        return None
    try:
        if int(nxt.getAddress().getOffset() - br_ins.getAddress().getOffset()) == 4:
            return nxt
    except Exception:
        pass
    return None


def _backward_chain_ending_at(listing, end_ins, max_n, min_addr):
    """Oldest-first listing ending with `end_ins` (the `jr ra`)."""
    chain = []
    cur = end_ins
    for _ in range(max_n):
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
        chain.insert(0, prev)
        cur = prev
    chain.append(end_ins)
    return chain


def _defined_registers(ins):
    from ghidra.program.model.lang import Register

    out = []
    try:
        ro = ins.getResultObjects()
        if ro:
            for o in ro:
                if isinstance(o, Register):
                    out.append(o.getName().lower())
    except Exception:
        pass
    if out:
        return out
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(lw|sw|lhu|lb|lbu|sh|sb)\s+(\w+)\s*,\s*", s)
    if m:
        return [m.group(2)]
    m = re.match(r"^(addiu|addi|daddiu|daddi|ori|andi|xori|slti|sltiu)\s+(\w+)\s*,", s)
    if m:
        return [m.group(2)]
    m = re.match(r"^(lui)\s+(\w+)\s*,", s)
    if m:
        return [m.group(2)]
    m = re.match(r"^(li)\s+(\w+)\s*,", s)
    if m:
        return [m.group(2)]
    m = re.match(r"^(or|xor|and|nor|movn|movz)\s+(\w+)\s*,", s)
    if m:
        return [m.group(2)]
    return []


def _forward_last_defs(block):
    last_def = {}
    for ins in block:
        if ins.getMnemonicString().lower() == "jal":
            continue
        for r in _defined_registers(ins):
            last_def[r] = ins
    return last_def


def _lw_dest_and_base(ins):
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^lw\s+(\w+)\s*,\s*([^\(]+)\((\w+)\)", s)
    if m:
        return m.group(1), m.group(3)
    return None, None


def _fmt_def(ins):
    if ins is None:
        return "(unknown)"
    return "%s  %s" % (ins.getAddress(), ins.toString().replace("\n", " ")[:96])


def _insn_index_in_block(block, ins):
    if ins is None or not block:
        return -1
    try:
        return block.index(ins)
    except ValueError:
        pass
    addr = ins.getAddress()
    for i, b in enumerate(block):
        if b.getAddress() == addr:
            return i
    return -1


def _last_jal_before_in_block(block, before_ins):
    idx = _insn_index_in_block(block, before_ins)
    if idx <= 0:
        return None
    for j in range(idx - 1, -1, -1):
        if block[j].getMnemonicString().lower() == "jal":
            return block[j]
    return None


def _jal_callee_label(jal_ins, ref_mgr, fm):
    for ref in _iter_references_from(ref_mgr, jal_ins.getAddress()):
        if not ref.getReferenceType().isCall():
            continue
        to_a = ref.getToAddress()
        if to_a is None:
            continue
        fn = fm.getFunctionAt(to_a)
        if fn is not None:
            return "%s @ %s" % (fn.getName(), fn.getEntryPoint())
        return str(to_a)
    return "(unresolved call target)"


def _print_return_reg_line(reg, last_def, block, ref_mgr, fm, ret_ins):
    dins = last_def.get(reg)
    if dins is not None:
        print("  %s <- %s" % (reg, _fmt_def(dins)))
        ld, base = _lw_dest_and_base(dins)
        if ld == reg and base:
            bs = last_def.get(base)
            print("      (lw base %s <- %s)" % (base, _fmt_def(bs)))
        return
    if (
        JAL_RETURN_REG_HINT
        and reg in ("v0", "v1")
        and block
        and ref_mgr is not None
        and fm is not None
    ):
        jal_i = _last_jal_before_in_block(block, ret_ins)
        if jal_i is not None:
            print(
                "  %s: (no static def in window — often nested jal return)"
                % reg
            )
            print(
                "      last jal before jr: @ %s -> %s"
                % (jal_i.getAddress(), _jal_callee_label(jal_i, ref_mgr, fm))
            )
            return
    print(
        "  %s: (no def in window — widen BACKWARD_MAX or inspect other return paths)"
        % reg
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

    space = ram.getStart().getAddressSpace()
    try:
        entry = space.getAddress(int(TARGET_FUNCTION_ENTRY_VRAM))
    except Exception:
        print("ERROR: bad TARGET_FUNCTION_ENTRY_VRAM.")
        return

    if not ram.contains(entry):
        print("ERROR: TARGET_FUNCTION_ENTRY_VRAM not inside `.ram`.")
        return

    fn = fm.getFunctionContaining(entry)
    if fn is None:
        print("ERROR: no Function at entry.")
        return

    if int(fn.getEntryPoint().getOffset()) != int(TARGET_FUNCTION_ENTRY_VRAM):
        print(
            "WARNING: function at entry is %s @ %s (requested 0x%X)"
            % (
                fn.getName(),
                fn.getEntryPoint(),
                int(TARGET_FUNCTION_ENTRY_VRAM),
            )
        )

    min_addr = fn.getBody().getMinAddress()

    print("=== RSP_Function_Return_Reg_Slice (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("Function: %s @ %s" % (fn.getName(), fn.getEntryPoint()))
    print("Return regs: %s" % ", ".join(RETURN_REGS))
    print(
        "Window: up to %d insns before each `jr ra`"
        % BACKWARD_MAX
        + (" + branch delay slot" if INCLUDE_BRANCH_DELAY_SLOT else "")
        + "."
    )
    print("")

    returns_found = 0
    for ins in _iter_listing_cursor(listing.getInstructions(fn.getBody(), True)):
        if not _is_jr_ra(ins):
            continue
        returns_found += 1

        chain = _backward_chain_ending_at(listing, ins, BACKWARD_MAX, min_addr)
        block = list(chain)
        had_delay = False
        if INCLUDE_BRANCH_DELAY_SLOT:
            ds = _delay_slot_after(listing, ins)
            if ds is not None:
                block.append(ds)
                had_delay = True

        last_def = _forward_last_defs(block)

        print("--- `jr ra` @ %s  (%s) ---" % (ins.getAddress(), fn.getName()))
        if DISASM_CONTEXT_LINES > 0 and len(block) > 0:
            tail = block[-min(len(block), DISASM_CONTEXT_LINES) :]
            print(
                "  Context (oldest -> newest, incl. jr%s):"
                % (" + delay" if had_delay else "")
            )
            for t in tail:
                mark = " <-- jr" if t.getAddress() == ins.getAddress() else ""
                print("    %s  %s%s" % (t.getAddress(), t.toString().replace("\n", " ")[:88], mark))

        for reg in RETURN_REGS:
            _print_return_reg_line(reg, last_def, block, ref_mgr, fm, ins)
        print("")

    if returns_found == 0:
        print("No `jr ra` in this function body — check boundaries / tail calls (`j` to thunk).")
    else:
        print("Return sites processed: %d" % returns_found)
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; RSPRecomp templates: config/afa_rsp/*.template.toml")


main()
