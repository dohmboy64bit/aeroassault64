# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): scan **`.ram`** code for **`lw` / `sw` / …** whose **effective address** matches
# **`BASE_VRAM + offset`** when the memory **base register** is known from a **local constant** model
# (**`lui`**, **`addiu`/`addi`**, **`ori`**, **`or reg,reg,zero`**, **`li`**, plus optional **`jal`** → **`v0`**
# from **`JAL_KNOWN_V0_BY_CALLEE_ENTRY`** when return value is built in the callee, not the caller).
#
# Automates “find **`sw`** writers / **`lw`** readers of **`0x802839B8`**” when **`getReferencesTo`**
# only shows **FLOW** edges (**`RSP_RAM_Context_Field_Xrefs.py`**). **Branches / calls** make the
# model wrong — verify hits in Listing / decompiler.
#
# Same **`.ram`** block as **`Phase2_Closeout_Report.py`**. **`text_offset`/`text_size`**: see
# **`config/afa_rsp/*.template.toml`**, **`lib/Zelda64Recomp/AFA_PORT.md`** §1.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_RAM_Constant_Base_Memops
#@description Scan lw/sw for effective addr == tunable BASE+offsets (constant reg model)
#@author AeroAssault64

from __future__ import print_function

import re

# --- Tunables -----------------------------------------------------------------
# AFA USA: struct head from **`RSP_Function_Return_Reg_Slice`** on **`FUN_8023d820`** (`lui`/`addiu`).
BASE_VRAM = 0x802839B0

# Effective addresses **BASE_VRAM + byte** to flag (must match **`lw`/`sw` displacement**).
MEM_OFFSETS = (0, 0x8, 0xC)

# **`"all"`** — any **`lw`/`sw`/…** in **`_MEM_RE`** matching EA. **`"stores"`** — only **`sw`/`sh`/`sb`**
# (who writes **`BASE+off`** — set this to hunt **`text_offset`/`text_size`** fills). **`"loads"`** —
# only **`lw`/`lhu`/`lbu`/`lb`** (who reads those slots).
MEMOP_RUN = "all"

# Stop after this many hits (raise if truncated).
MAX_HITS = 400

# If True, reset the constant map at each function entry (linear pass per function).
RESET_KNOWN_PER_FUNCTION = True

# If non-empty: when **`jal`** resolves to callee **entry** key (VRAM int), set **`v0`** to the
# value after the call (synthesized return). Use when writers do **`or s2,v0,zero`** after
# **`jal FUN_8023d820`** — static **`lui`/`addiu`** for **`v0`** is inside the callee, not the caller.
# AFA USA: **`RSP_Function_Return_Reg_Slice`** on **`0x8023D820`** → **`v0 = 0x802839B0`**.
JAL_KNOWN_V0_BY_CALLEE_ENTRY = {
    0x8023D820: 0x802839B0,
}


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


def _norm_dis(ins):
    s = re.sub(r"\s+", " ", ins.toString().lower().replace("_", " ")).strip()
    return s.replace("$", "")


def _parse_imm16(tok):
    """MIPS 16-bit signed immediate (addiu/lw offset)."""
    v = int(tok.strip(), 0) & 0xFFFF
    if v & 0x8000:
        return v - 0x10000
    return v


def _parse_u32(tok):
    v = int(tok.strip(), 0)
    return v & 0xFFFFFFFF


def _defined_regs_clear(ins):
    """Registers written by insn (lowercase) — for invalidation."""
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
    m = re.match(
        r"^(lw|sw|lhu|lb|lbu|sh|sb)\s+(\w+)\s*,\s*", s
    )
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


_JAL_CLOBBERS = frozenset(
    "v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 at".split()
)

_MEM_RE = re.compile(
    r"^(lw|sw|lhu|lbu|lb|sh|sb)\s+(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\((\w+)\)\s*$"
)
_LUI_RE = re.compile(r"^lui\s+(\w+)\s*,\s*(0x[0-9a-f]+|\d+)\s*$")
_ADDIU_RE = re.compile(
    r"^addiu\s+(\w+)\s*,\s*(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$"
)
_ADDI_RE = re.compile(
    r"^addi\s+(\w+)\s*,\s*(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$"
)
_ORI_RE = re.compile(r"^ori\s+(\w+)\s*,\s*(\w+)\s*,\s*(0x[0-9a-f]+|\d+)\s*$")
_OR_COPY_RE = re.compile(r"^(?:or|addu)\s+(\w+)\s*,\s*(\w+)\s*,\s*(zero|r0)\s*$")
_LI_RE = re.compile(r"^li\s+(\w+)\s*,\s*(-?0x[0-9a-f]+|-?\d+)\s*$")


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
    """Update `known` from this insn if pattern matches; else invalidate written GPRs."""
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
        mn, rdst = m.group(1), m.group(2)
        if mn in ("lw", "lhu", "lbu", "lb"):
            known.pop(rdst, None)
        return

    for r in _defined_regs_clear(ins):
        known.pop(r, None)


def _memop_filter_tuple():
    r = str(MEMOP_RUN).lower().strip()
    if r == "stores":
        return frozenset(("sw", "sh", "sb"))
    if r == "loads":
        return frozenset(("lw", "lhu", "lbu", "lb"))
    if r != "all":
        print("WARNING: MEMOP_RUN should be all|stores|loads — using all.")
    return None


def _check_memop(ins, known, want_addrs, hits, fn, max_hits, mnem_filter):
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


def main():
    prog = currentProgram  # noqa: F821
    _g = globals()
    if "RESET_KNOWN_PER_FUNCTION" not in _g:
        _g["RESET_KNOWN_PER_FUNCTION"] = True
    if "JAL_KNOWN_V0_BY_CALLEE_ENTRY" not in _g:
        _g["JAL_KNOWN_V0_BY_CALLEE_ENTRY"] = {0x8023D820: 0x802839B0}
    if "MEMOP_RUN" not in _g:
        _g["MEMOP_RUN"] = "all"

    mem = prog.getMemory()
    listing = prog.getListing()
    ref_mgr = prog.getReferenceManager()
    fm = prog.getFunctionManager()

    ram = get_block_exact(mem, ".ram")
    if ram is None:
        print("ERROR: need MemoryBlock `.ram`.")
        return

    base = int(BASE_VRAM) & 0xFFFFFFFF
    want = set((base + (int(o) & 0xFFFFFFFF)) & 0xFFFFFFFF for o in MEM_OFFSETS)

    print("=== RSP_RAM_Constant_Base_Memops (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("Want effective addresses: %s" % ", ".join("0x%08X" % a for a in sorted(want)))
    print(
        "MEMOP_RUN=%s (use \"stores\" for sw/sh/sb writers to BASE+off; \"loads\" for lw/… readers)."
        % repr(MEMOP_RUN)
    )
    print("(lui/addiu/ori/or-copy/li; jal clears volatiles; optional JAL_KNOWN_V0_BY_CALLEE_ENTRY.)")
    print("")

    mnem_filter = _memop_filter_tuple()
    ram_set = memory_block_as_address_set(ram)
    hits = []
    cur_fn = None
    known = {}

    for ins in listing.getInstructions(ram_set, True):
        if ins is None:
            continue
        fn = fm.getFunctionContaining(ins.getAddress())
        if fn is None:
            continue
        if RESET_KNOWN_PER_FUNCTION and fn != cur_fn:
            cur_fn = fn
            known = {}

        _check_memop(ins, known, want, hits, fn, MAX_HITS, mnem_filter)
        if len(hits) >= MAX_HITS:
            break
        _apply_constant_semantics(ins, known, ref_mgr, fm)

    hits.sort(key=lambda t: t[1])
    print("Hits: %d%s" % (len(hits), (" (MAX_HITS — raise tunable)" if len(hits) >= MAX_HITS else "")))
    for kind, addr, name, ent, ea, dis in hits:
        print("  [%s] @ 0x%X  %s @ %s  EA=0x%08X" % (kind, addr, name, ent, ea))
        print("      %s" % dis)

    if not hits:
        print("(none — widen patterns, add callee entries to JAL_KNOWN_V0_BY_CALLEE_ENTRY,")
        print("      Listing search, or emulator RAM.)")

    print("")
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md §1; pair: tools/ghidra/RSP_RAM_Context_Field_Xrefs.py")


main()
