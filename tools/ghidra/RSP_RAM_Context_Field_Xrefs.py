# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): **incoming xrefs** to a tunable **`.ram`** base + word offsets, optional
# **big-endian word** dump at each offset, whether the stored word looks like a pointer into **`.rom`**,
# optional **constant-base `lw`/`sw` scan** and **`sw` xref** pass (same models as **`RSP_RAM_Constant_Base_Memops.py`**).
#
# Use after **`RSP_Function_Return_Reg_Slice.py`** prints a global return like **`v0 = 0x802839B0`**
# (AFA USA **`FUN_8023d820`**): set **`BASE_VRAM`** to that address and **`FIELD_OFFSETS`** to
# **`(0x8, 0xC)`** (or include **`0`** to see the block head) to find **who reads/writes** the
# words passed as **`lw a2,0x8(s2)`** / **`lw a3,0xc(s2)`** toward **`text_offset` / `text_size`**
# (**`config/afa_rsp/*.template.toml`**, **`lib/Zelda64Recomp/AFA_PORT.md`** §1).
#
# Same **`.ram` / `.rom`** blocks as **`Phase2_Closeout_Report.py`**. Heuristic only — verify in Listing.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; pairs with RSP_Function_Return_Reg_Slice.py and
# RSP_RAM_Constant_Base_Memops.py (tunables **`JAL_KNOWN_V0_BY_CALLEE_ENTRY`** / **`BASE_VRAM`** should agree).
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_RAM_Context_Field_Xrefs
#@description Incoming xrefs + BE words; optional constant-base lw/sw + sw-xref (Memops-aligned)
#@author AeroAssault64

from __future__ import print_function

import re

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

# --- Pair scan: same effective-address logic as **`tools/ghidra/RSP_RAM_Constant_Base_Memops.py`**
# (keep **`JAL_KNOWN_*`** and **`BASE_VRAM`** consistent). Runs once after per-field xref listing.
RUN_CONSTANT_BASE_MEMOPS = True
# **`"all"`** | **`"stores"`** | **`"loads"`** — same meaning as **`MEMOP_RUN`** in Memops (no stores_xref here;
# use **`RUN_STORE_XREF_SCAN`** below for xref-attached **`sw`**).
MEMOP_SCAN_MODE = "all"
MEMOP_SCAN_MAX_HITS = 200
RESET_KNOWN_PER_FUNCTION_MEMOPS = True
# When **`jal`** targets callee entry (VRAM int), synthesize **`v0`** after the call (AFA USA example).
JAL_KNOWN_V0_BY_CALLEE_ENTRY = {
    0x8023D820: 0x802839B0,
}

# **`getReferencesTo(EA)`** then list **`sw`/`sh`/`sb`** at ref source (Ghidra may have no DATA xref for some **`lw`**).
RUN_STORE_XREF_SCAN = True
STORE_XREF_MAX_HITS = 100


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


# --- Constant-base memop scan (keep aligned with **`RSP_RAM_Constant_Base_Memops.py`**) ----------


def memory_block_as_address_set(block):
    from ghidra.program.model.address import AddressRangeImpl
    from ghidra.program.model.address import AddressSet

    aset = AddressSet()
    aset.add(AddressRangeImpl(block.getStart(), block.getEnd()))
    return aset


def _norm_dis(ins):
    s = re.sub(r"\s+", " ", ins.toString().lower().replace("_", " ")).strip()
    return s.replace("$", "")


def _parse_imm16(tok):
    v = int(tok.strip(), 0) & 0xFFFF
    if v & 0x8000:
        return v - 0x10000
    return v


def _parse_u32(tok):
    v = int(tok.strip(), 0)
    return v & 0xFFFFFFFF


def _defined_regs_clear(ins):
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
    s = _norm_dis(ins)
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
    m = re.match(r"^(or|xor|and|nor)\s+(\w+)\s*,", s)
    if m:
        return [m.group(2)]
    return []


_JAL_CLOBBERS = frozenset("v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 at".split())

_MEM_RE = re.compile(
    r"^(lw|sw|lhu|lbu|lb|sh|sb)\s+(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\((\w+)\)\s*$"
)
_LUI_RE = re.compile(r"^lui\s+(\w+)\s*,\s*(0x[0-9a-f]+|\d+)\s*$")
_ADDIU_RE = re.compile(
    r"^addiu\s+(\w+)\s*,\s*(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$"
)
_ADDI_RE = re.compile(r"^addi\s+(\w+)\s*,\s*(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$")
_ORI_RE = re.compile(r"^ori\s+(\w+)\s*,\s*(\w+)\s*,\s*(0x[0-9a-f]+|\d+)\s*$")
_OR_COPY_RE = re.compile(r"^(?:or|addu)\s+(\w+)\s*,\s*(\w+)\s*,\s*(zero|r0)\s*$")
_LI_RE = re.compile(r"^li\s+(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$")


def _jal_callee_entry_vram(ins, ref_mgr, fm):
    for ref in _iter_references_from(ref_mgr, ins.getAddress()):
        if not ref.getReferenceType().isCall():
            continue
        to_a = ref.getToAddress()
        if to_a is None:
            continue
        fn = fm.getFunctionAt(to_a)
        if fn is not None:
            return int(fn.getEntryPoint().getOffset())
    return None


def _apply_constant_semantics(ins, known, ref_mgr, fm):
    s = _norm_dis(ins)
    mn = ins.getMnemonicString().lower()

    if mn == "jal":
        for r in list(known.keys()):
            if r in _JAL_CLOBBERS:
                known.pop(r, None)
        if ref_mgr is not None and fm is not None and JAL_KNOWN_V0_BY_CALLEE_ENTRY:
            ent = _jal_callee_entry_vram(ins, ref_mgr, fm)
            if ent is not None:
                v0v = JAL_KNOWN_V0_BY_CALLEE_ENTRY.get(ent)
                if v0v is not None:
                    known["v0"] = int(v0v) & 0xFFFFFFFF
        return

    m = _LUI_RE.match(s)
    if m:
        rt, imm = m.group(1), m.group(2)
        v = int(imm, 16) if imm.startswith("0x") else int(imm)
        known[rt] = (v & 0xFFFF) << 16
        return

    m = _ADDIU_RE.match(s) or _ADDI_RE.match(s)
    if m:
        rt, rs, im = m.group(1), m.group(2), m.group(3)
        if rs in known:
            known[rt] = (known[rs] + _parse_imm16(im)) & 0xFFFFFFFF
        else:
            known.pop(rt, None)
        return

    m = _ORI_RE.match(s)
    if m:
        rt, rs, im = m.group(1), m.group(2), m.group(3)
        iv = int(im, 16) if im.startswith("0x") else int(im)
        if rs in known:
            known[rt] = (known[rs] | (iv & 0xFFFF)) & 0xFFFFFFFF
        else:
            known.pop(rt, None)
        return

    m = _OR_COPY_RE.match(s)
    if m:
        rd, rs = m.group(1), m.group(2)
        if rs in known:
            known[rd] = known[rs]
        else:
            known.pop(rd, None)
        return

    m = _LI_RE.match(s)
    if m:
        rt, im = m.group(1), m.group(2)
        known[rt] = _parse_u32(im)
        return

    m = _MEM_RE.match(s)
    if m:
        mnm, rdst = m.group(1), m.group(2)
        if mnm in ("lw", "lhu", "lbu", "lb"):
            known.pop(rdst, None)
        return

    for r in _defined_regs_clear(ins):
        known.pop(r, None)


def _memop_filter_for_mode():
    r = str(MEMOP_SCAN_MODE).lower().strip()
    if r == "stores":
        return frozenset(("sw", "sh", "sb"))
    if r == "loads":
        return frozenset(("lw", "lhu", "lbu", "lb"))
    if r != "all":
        print("WARNING: MEMOP_SCAN_MODE should be all|stores|loads — using all.")
    return None


def _check_memop_field_scan(ins, known, want_addrs, hits, fn, max_hits, mnem_filter):
    if len(hits) >= max_hits:
        return
    s = _norm_dis(ins)
    m = _MEM_RE.match(s)
    if not m:
        return
    _mn, _rt, im_tok, base_r = m.groups()
    mn = _mn.lower()
    if mnem_filter is not None and mn not in mnem_filter:
        return
    base_r = base_r.lower()
    if base_r not in known:
        return
    try:
        imm = _parse_imm16(im_tok)
    except Exception:
        return
    ea = (known[base_r] + imm) & 0xFFFFFFFF
    if ea not in want_addrs:
        return
    kind = "STORE" if mn in ("sw", "sh", "sb") else "LOAD"
    hits.append(
        (
            kind,
            int(ins.getAddress().getOffset()),
            fn.getName() if fn else "?",
            fn.getEntryPoint() if fn else None,
            ea,
            ins.toString().replace("\n", " ")[:88],
        )
    )


def _run_constant_base_memop_scan(listing, ref_mgr, fm, ram, want_addrs, max_hits, mnem_filter):
    hits = []
    ram_set = memory_block_as_address_set(ram)
    cur_fn = None
    known = {}
    for ins in listing.getInstructions(ram_set, True):
        if ins is None:
            continue
        fn = fm.getFunctionContaining(ins.getAddress())
        if fn is None:
            continue
        if RESET_KNOWN_PER_FUNCTION_MEMOPS and fn != cur_fn:
            cur_fn = fn
            known = {}
        _check_memop_field_scan(ins, known, want_addrs, hits, fn, max_hits, mnem_filter)
        if len(hits) >= max_hits:
            break
        _apply_constant_semantics(ins, known, ref_mgr, fm)
    hits.sort(key=lambda t: t[1])
    return hits


def _run_store_xref_scan_for_want(listing, ref_mgr, fm, ram, want_addrs, max_hits):
    """sw/sh/sb at getReferencesTo(EA) — same idea as Memops **`stores_xref`**."""
    space = ram.getStart().getAddressSpace()
    hits = []
    for ea in sorted(want_addrs):
        if len(hits) >= max_hits:
            break
        try:
            to_a = space.getAddress(int(ea) & 0xFFFFFFFF)
        except Exception:
            continue
        if not ram.contains(to_a):
            continue
        for ref in _iter_references_to(ref_mgr, to_a):
            if len(hits) >= max_hits:
                break
            fa = ref.getFromAddress()
            if fa is None or not ram.contains(fa):
                continue
            ins = listing.getInstructionAt(fa)
            if ins is None:
                continue
            mn = ins.getMnemonicString().lower()
            if mn not in ("sw", "sh", "sb"):
                continue
            fn = fm.getFunctionContaining(fa)
            try:
                rts = ref.getReferenceType().toString()
            except Exception:
                rts = str(ref.getReferenceType())
            hits.append(
                (
                    "STORE_XREF",
                    int(fa.getOffset()),
                    fn.getName() if fn else "?",
                    fn.getEntryPoint() if fn else None,
                    int(ea) & 0xFFFFFFFF,
                    ins.toString().replace("\n", " ")[:88],
                    rts,
                )
            )
    return hits


def _incoming_ref_source_tag(ref_kind, ins):
    """Annotate xref source: DATA lw/sw vs FLOW branch/jump target (not a memory operand ref)."""
    if ins is None:
        return ""
    mn = ins.getMnemonicString().lower().replace("_", "")
    if ref_kind == "DATA":
        if mn in ("sw", "sh", "sb"):
            return "  insn=STORE"
        if mn in ("lw", "lhu", "lbu", "lb"):
            return "  insn=LOAD"
        return "  insn=DATA_OTHER"
    if ref_kind == "FLOW":
        if mn in (
            "beq",
            "bne",
            "beqz",
            "bnez",
            "blez",
            "bgtz",
            "bltz",
            "bgez",
            "bgezal",
            "bltzal",
            "bc1f",
            "bc1t",
            "bc1fl",
            "bc1tl",
        ):
            return "  ref=BRANCH_TARGET (not lw/sw operand)"
        if mn in ("j", "jal", "jr", "jalr"):
            return "  ref=JUMP_TARGET (not lw/sw operand)"
        return "  ref=FLOW (control edge)"
    return ""


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
            src_tag = _incoming_ref_source_tag(rk, ins)
            print(
                "    [%d] kind=%s  from %s  type=%s  fn=%s%s"
                % (n, rk, fa, rts, _fn_label(fm, fa), src_tag)
            )
            print("         %s" % ins_s)
        if len(refs) > MAX_REFS_TO_PRINT:
            print("    ... truncated (%d more)" % (len(refs) - MAX_REFS_TO_PRINT))

        if data_in == 0 and flow_in > 0:
            print(
                "  hint: DATA=0 but FLOW>0 — Ghidra only shows control-flow to this VA (branch/jump labels),"
            )
            print(
                "        not operand xrefs for lw/sw. Loads/stores can still exist (see constant-base block)."
            )

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

    want_eas = set()
    for off in FIELD_OFFSETS:
        try:
            want_eas.add((int(base.getOffset()) + (int(off) & 0xFFFFFFFF)) & 0xFFFFFFFF)
        except Exception:
            pass

    if RUN_CONSTANT_BASE_MEMOPS or RUN_STORE_XREF_SCAN:
        bo = int(base.getOffset()) & 0xFFFFFFFF
        vals = {int(x) & 0xFFFFFFFF for x in JAL_KNOWN_V0_BY_CALLEE_ENTRY.values()}
        if vals and bo not in vals:
            print(
                "NOTE: BASE VRAM 0x%08X is not in JAL_KNOWN_V0_BY_CALLEE_ENTRY values %s — fix if copy-paste error."
                % (bo, ", ".join("0x%08X" % v for v in sorted(vals)))
            )

    if RUN_CONSTANT_BASE_MEMOPS:
        print("=== Constant-base lw/sw (same model as RSP_RAM_Constant_Base_Memops.py) ===")
        print(
            "MEMOP_SCAN_MODE=%s  max_hits=%d  RESET_KNOWN_PER_FUNCTION_MEMOPS=%s"
            % (repr(MEMOP_SCAN_MODE), MEMOP_SCAN_MAX_HITS, RESET_KNOWN_PER_FUNCTION_MEMOPS)
        )
        print("Want EA: %s" % ", ".join("0x%08X" % a for a in sorted(want_eas)))
        mf = _memop_filter_for_mode()
        hits = _run_constant_base_memop_scan(
            prog.getListing(),
            ref_mgr,
            fm,
            ram,
            want_eas,
            MEMOP_SCAN_MAX_HITS,
            mf,
        )
        print("Hits: %d%s" % (len(hits), (" (MEMOP_SCAN_MAX_HITS)" if len(hits) >= MEMOP_SCAN_MAX_HITS else "")))
        for kind, addr, name, ent, ea, dis in hits:
            print("  [%s] @ 0x%X  %s @ %s  EA=0x%08X" % (kind, addr, name, ent, ea))
            print("      %s" % dis)
        print("")

    if RUN_STORE_XREF_SCAN:
        print("=== Store xrefs (sw/sh/sb at getReferencesTo each field EA) ===")
        sx = _run_store_xref_scan_for_want(
            prog.getListing(), ref_mgr, fm, ram, want_eas, STORE_XREF_MAX_HITS
        )
        print("Hits: %d%s" % (len(sx), (" (STORE_XREF_MAX_HITS)" if len(sx) >= STORE_XREF_MAX_HITS else "")))
        if not sx:
            print("  (none — Ghidra has no sw/sh/sb operand xref to these VAs, or cap hit.)")
        for row in sx:
            kind, addr, name, ent, ea, dis, rts = row
            print("  [%s] @ 0x%X  %s @ %s  EA=0x%08X  ref=%s" % (kind, addr, name, ent, ea, rts))
            print("      %s" % dis)
        print("")

    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; `text_offset`/`text_size` in config/afa_rsp/*.template.toml")
    print("Pair: tools/ghidra/RSP_RAM_Constant_Base_Memops.py (same constant-base / JAL_KNOWN tunables when split-run).")
    if READ_BE_WORD_AT_EACH_FIELD and zero_reads > 0 and nonzero_reads == 0:
        print("")
        print("Note: every readable field was 0x0 in the static image — common for .bss zero-init")
        print("      and runtime `sw` fills before `lw a2,0x8(s2)` sees real src/size. Inspect callers")
        print("      that initialize this struct; **FLOW** incoming (e.g. **`beq` → BASE+off**) is a branch")
        print("      target at that VA, not Ghidra’s DATA xref for the word — use Listing or the memop block.")
        print("      Emulator RAM helps when static bytes are still 0.")
        print("      Incoming kind=FLOW = control-flow to this address (e.g. `beq` label), not a load")
        print("      of the stored word. Outgoing kind=FLOW = jump from bytes at this VA (code/data mix).")
        print("")
        print("      Incoming lines tag DATA as insn=LOAD/STORE; FLOW as ref=BRANCH_TARGET / JUMP_TARGET.")
        print("      Constant-base memop + store-xref blocks ran when RUN_* tunables are True (see script top).")


main()
