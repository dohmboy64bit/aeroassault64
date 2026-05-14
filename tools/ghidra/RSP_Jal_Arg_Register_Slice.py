# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): intra-procedural **heuristic** slice for MIPS `a0`–`a3` at selected `jal` sites.
#
# Builds a linear insn window ending at each `jal` (+ delay slot), walks forward tracking the
# last instruction that defines each GPR (via getResultObjects when available; else regex).
# For `lw a2,0x8(s2)`-style args, also reports where **base** (`s2`) was last set in that window.
# Optional: peel **or dst,src,zero** / **lw** chains from a2/a3 toward **v0** / stack (**DEPENDENCY_CHAIN_MAX**).
#
# **Limitation:** one predecessor chain only (getPrevious from `jal`); branches/loops can make
# the reported def wrong — verify in Listing / decompiler. Same `.ram` as Phase2_Closeout.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; pairs with RSP_Jal_Call_Sites_Disasm_From_Caller.py
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_Jal_Arg_Register_Slice
#@description Heuristic last-def for a0-a3 (+ lw base) at jal to tunable callees
#@author AeroAssault64

from __future__ import print_function

import re

# --- Tunables -----------------------------------------------------------------
SOURCE_FUNCTION_ENTRY_VRAM = 0x8023D92C

# Only analyze `jal` whose callee *entry* is in this set (empty = skip all).
TARGET_CALLEE_ENTRIES = (0x80246FD0,)

# Max instructions to walk backward from each `jal` when building the linear window.
BACKWARD_MAX = 100

# Registers to report at each snapshot (after delay slot of `jal`).
ARG_REGS = ("a0", "a1", "a2", "a3")

# After a2/a3 reporting: peel `or dst,src,zero` / `addu dst,src,zero` and `lw dst,off(base)`
# bases in the same linear window (stops at lui / unknown / depth).
DEPENDENCY_CHAIN_MAX = 8

# If True, also peel from a2/a3 defs that are register copies (e.g. or a2,s2,zero -> s2).
FOLLOW_ARG_COPY_SRCS = True


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


def _instructions_backward_chain(listing, jal_ins, max_n, min_addr):
    """Oldest-first list ending with jal_ins (no delay slot yet)."""
    chain = []
    cur = jal_ins
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
    chain.append(jal_ins)
    return chain


def _delay_slot_after(listing, jal_ins):
    try:
        nxt = jal_ins.getNext()
    except Exception:
        nxt = None
    if nxt is None:
        try:
            nxt = listing.getInstructionAfter(jal_ins.getAddress())
        except Exception:
            nxt = None
    if nxt is None:
        return None
    try:
        if int(nxt.getAddress().getOffset() - jal_ins.getAddress().getOffset()) == 4:
            return nxt
    except Exception:
        pass
    return None


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
    # Fallback: common MIPS patterns from disassembly text
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(
        r"^(lw|sw|lhu|lb|lbu|sh|sb)\s+(\w+)\s*,\s*", s
    )
    if m:
        return [m.group(2)]
    m = re.match(
        r"^(addiu|addi|daddiu|daddi|ori|andi|xori|slti|sltiu)\s+(\w+)\s*,", s
    )
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


def _lw_dest_and_base(ins):
    """Return (dest_reg, base_reg) or (None, None) if not a simple lw."""
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^lw\s+(\w+)\s*,\s*([^\(]+)\((\w+)\)", s)
    if m:
        return m.group(1), m.group(3)
    return None, None


def _copy_dest_src(ins):
    """If insn is `or dst,src,zero` / `addu dst,src,zero`, return (dst, src). Else (None, None)."""
    s = ins.toString().lower().replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^or\s+(\w+)\s*,\s*(\w+)\s*,\s*(zero|r0)\s*$", s)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^addu\s+(\w+)\s*,\s*(\w+)\s*,\s*(zero|r0)\s*$", s)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _dependency_seeds_from_arg_def(last_def, reg):
    """Registers to peel toward ROM/struct clues (same-window last_def only)."""
    seeds = set()
    dins = last_def.get(reg)
    if dins is None:
        return seeds
    dst, src = _copy_dest_src(dins)
    if dst == reg and src and src not in ("zero", "r0"):
        seeds.add(src)
    ld, base = _lw_dest_and_base(dins)
    if ld == reg and base and base not in ("zero", "r0"):
        seeds.add(base)
    return seeds


def _expand_reg_deps(last_def, reg, indent, max_depth, depth, seen):
    """Print copy/lw-base chain for one GPR within forward last_def map."""
    if depth >= max_depth:
        print("%s%s: (max depth)" % (indent, reg))
        return
    if reg in seen:
        print("%s%s: (cycle)" % (indent, reg))
        return
    seen.add(reg)
    dins = last_def.get(reg)
    if dins is None:
        print("%s%s: (no def in window — widen BACKWARD_MAX or read decompiler)" % (indent, reg))
        return
    print("%s%s <- %s" % (indent, reg, _fmt_def(dins)))
    dst, src = _copy_dest_src(dins)
    if dst == reg and src and src not in ("zero", "r0"):
        _expand_reg_deps(last_def, src, indent + "  ", max_depth, depth + 1, seen)
        return
    ld, base = _lw_dest_and_base(dins)
    if ld == reg and base and base not in ("zero", "r0"):
        _expand_reg_deps(last_def, base, indent + "  ", max_depth, depth + 1, seen)


def _forward_last_defs(block):
    """block: chronological insns ending with jal then optional delay. Return last_def dict."""
    last_def = {}
    for ins in block:
        mn = ins.getMnemonicString().lower()
        if mn == "jal":
            continue
        for r in _defined_registers(ins):
            last_def[r] = ins
    return last_def


def _fmt_def(ins):
    if ins is None:
        return "(unknown)"
    return "%s  %s" % (ins.getAddress(), ins.toString().replace("\n", " ")[:90])


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
        print("ERROR: no Function at caller entry.")
        return

    targets = set(int(x) for x in TARGET_CALLEE_ENTRIES)
    if not targets:
        print("ERROR: set TARGET_CALLEE_ENTRIES non-empty (e.g. (0x80246FD0,)).")
        return

    min_addr = fn.getBody().getMinAddress()

    print("=== RSP_Jal_Arg_Register_Slice (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("Caller: %s @ %s" % (fn.getName(), fn.getEntryPoint()))
    print("Targets: %s" % ", ".join("0x%X" % t for t in sorted(targets)))
    print(
        "Heuristic: linear window of up to %d insns before each matching `jal` + delay slot."
        % BACKWARD_MAX
    )
    print("")

    n = 0
    for ins in _iter_listing_cursor(listing.getInstructions(fn.getBody(), True)):
        if ins.getMnemonicString().lower() != "jal":
            continue
        to_ent = None
        for ref in _iter_references_from(ref_mgr, ins.getAddress()):
            if not ref.getReferenceType().isCall():
                continue
            to_a = ref.getToAddress()
            if to_a is None:
                continue
            c = fm.getFunctionAt(to_a)
            if c is None:
                continue
            to_ent = int(c.getEntryPoint().getOffset())
            break
        if to_ent is None or to_ent not in targets:
            continue

        chain = _instructions_backward_chain(listing, ins, BACKWARD_MAX, min_addr)
        delay = _delay_slot_after(listing, ins)
        block = list(chain)
        if delay is not None:
            block.append(delay)

        last_def = _forward_last_defs(block)

        print("--- jal @ %s  ->  callee @ 0x%X (after delay slot) ---" % (ins.getAddress(), to_ent))
        for reg in ARG_REGS:
            dins = last_def.get(reg)
            print("  %s <- %s" % (reg, _fmt_def(dins)))

        a2i = last_def.get("a2")
        if a2i is not None:
            d, b = _lw_dest_and_base(a2i)
            if d == "a2" and b:
                bs = last_def.get(b)
                print("  (a2 loaded by lw @ %s uses base %s <- %s)" % (a2i.getAddress(), b, _fmt_def(bs)))

        a3i = last_def.get("a3")
        if a3i is not None:
            d, b = _lw_dest_and_base(a3i)
            if d == "a3" and b:
                bs = last_def.get(b)
                print("  (a3 loaded by lw @ %s uses base %s <- %s)" % (a3i.getAddress(), b, _fmt_def(bs)))

        seeds = set()
        if FOLLOW_ARG_COPY_SRCS:
            seeds |= _dependency_seeds_from_arg_def(last_def, "a2")
            seeds |= _dependency_seeds_from_arg_def(last_def, "a3")
        if seeds:
            print("  --- same-window copy/lw peel (s2/v0/… toward ROM or struct) ---")
            for r in sorted(seeds):
                _expand_reg_deps(last_def, r, "  ", DEPENDENCY_CHAIN_MAX, 0, set())

        print("")
        n += 1

    print("Slices printed: %d" % n)
    print("If defs look wrong past a branch, widen BACKWARD_MAX or read the decompiler.")
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1.")
    print("")
    print("RSPRecomp TOML (see config/afa_rsp/*.template.toml + upstream *.us.rev1.toml URLs there):")
    print("  text_offset / text_size — byte offset and length of ucode TEXT inside the same ROM as rom_file_path.")
    print("  text_address — IMEM VA the game uses for that task (templates suggest 0x04001000 / 0x04001080; verify).")
    print("  extra_indirect_branch_targets — aspMain often needs word offsets; njpgdsp may use [].")
    print("Next: xref .rom from lw-immediate / lui+lo on v0/tables; confirm DMA path in Listing.")


main()
