# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): **confirm** emulator / static-analysis seeds for **RSPRecomp** TOML work.
#
# Paste addresses you proved in **Project64** + **Ghidra** into the tunables, then run once.
# The script checks **`.ram`** containment, **incoming xref** counts, **`.rom`** **file offsets**
# for KSEG0 pointers, and searches **`.rom`** for a short **IMEM bootstrap** big-endian word
# signature (same idea as **`Find_RSP_Microcode_ROM_Hints.py`** **`rom_file_offset`**).
# Default **`IMEM_BOOTSTRAP_BE_U32`** may hit **MIPS** at ROM **0x4BE20** (**`asm/4BE20.s`**) — not aspMain text;
# use **`REPO_TOML_HINT_*`** / **`EXPECTED_*`** (defaults = **`config/afa_rsp/aspMain.afa.us.template.toml`**) to cross-check;
# **`IMEM_BOOTSTRAP_NJPG_BE_U32`** + **`EXPECTED_NJPG_*`** cover **`njpgdspMain.afa.us.template.toml`** when pasted.
# With **`pip install capstone`** in the PyGhidra interpreter, each hit prints **MIPS BE** disassembly (Capstone).
# Tunables **`CAPSTONE_MIPS_INSNS_PER_ROM_HIT`** / **`CAPSTONE_AT_REPO_HINTS`** trim output; **`HEX_DUMP_BYTES_AT_ROM_OFFSETS`**
# prints raw cart bytes for P64 / hex-editor compare.
#
# It does **not** replace **splat** PI-cart → file math — **`PI_CART_ADDR_*`** are printed for
# manual correlation only.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; pairs with Find_RSP_Microcode_ROM_Hints.py,
# RSP_RAM_Context_Field_Xrefs.py, RSPRecomp_AFA_AllInOne.py.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSPRecomp_Confirm_Findings
#@description Verify RAM seeds, xrefs, .rom pattern match for RSPRecomp TOML (AFA USA)
#@author AeroAssault64

from __future__ import print_function

import struct

# --- Tunables: paste values from your last P64 / Ghidra session ----------------
# CPU struct base (e.g. **`RSP_Function_Return_Reg_Slice`** / **`RSP_RAM_Context_Field_Xrefs`**).
STRUCT_BASE_VRAM = 0x802839B0

# Offsets (bytes) to print BE u32 + xref count (include **0x30** / **0x40** if you saw **`T1`/`T0`** there).
STRUCT_FIELD_OFFSETS = (
    0,
    8,
    0xC,
    0x30,
    0x40,
)

# RDRAM microcode buffer (**`A2`** / **`SP_DRAM_ADDR`** KSEG0 vs physical — both optional).
MICROCODE_RDDRAM_KSEG0 = 0x8024AE70
MICROCODE_RDDRAM_PHYS = 0x0024AE70

# Small SP DMA source seen in another snapshot (**`0x0029930`**).
SMALL_DMA_RDDRAM_PHYS = 0x0029930

# CPU **EPC** / **`RA`** anchor (e.g. **`0x8023DAC4`**).
ANCHOR_PC_VRAM = 0x8023DAC4

# First **N** **big-endian** IMEM words at **`IMEM+0x1000`** from your Memory dump (must match bytes in ROM if loaded verbatim).
IMEM_BOOTSTRAP_BE_U32 = (
    0x09000419,
    0x20010FC0,
    0x8C220010,
    0x20030F7F,
    0x20071080,
    0x40870000,
    0x40820800,
    0x40831000,
)

# Prefix check: **min(len(IMEM_BOOTSTRAP_BE_U32)*4, text_size)** bytes at **`rom_start+text_offset`**
# must equal the asp bootstrap prefix. Defaults match **`config/afa_rsp/aspMain.afa.us.template.toml`**
# (**`text_offset`** / **`text_size`**). Set both to **None** if your pasted IMEM is **njpgdsp**-only,
# a different cart SHA1, or you only want **`.rom`** pattern hits without a fixed asp offset.
# **njpgdsp** uses **`IMEM_BOOTSTRAP_NJPG_BE_U32`** + **`EXPECTED_NJPG_*`** (see **`njpgdspMain.afa.us.template.toml`**).
EXPECTED_TEXT_OFFSET_IN_ROM = 0x4DAB0
EXPECTED_TEXT_SIZE = 0x1000
EXPECTED_TEXT_ADDRESS = 0x04001000  # TOML default from config/afa_rsp/aspMain.afa.us.template.toml

# **njpgdspMain** (**`config/afa_rsp/njpgdspMain.afa.us.template.toml`**): prefix compare runs only when
# **`IMEM_BOOTSTRAP_NJPG_BE_U32`** is non-empty. Set both **EXPECTED_NJPG_*** to **None** to omit this section.
EXPECTED_NJPG_TEXT_OFFSET_IN_ROM = 0x4C830
EXPECTED_NJPG_TEXT_SIZE = 0xAF0
EXPECTED_NJPG_TEXT_ADDRESS = 0x04001080
IMEM_BOOTSTRAP_NJPG_BE_U32 = ()  # paste BE u32 words from P64 IMEM tail for the **0x04001080** task

# Optional: ROM file offsets from **`config/afa_rsp/*.template.toml`** — printed for cross-check vs bootstrap hits.
# Set to **None** to silence.
REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM = 0x4DAB0
REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM = 0x4C830

# PI bus cart addresses from P64 (informational — **not** auto-mapped to file offset here).
PI_CART_ADDR_CANDIDATES = (
    0x103C26EE,
    0x1065DE64,
)

# Cap pattern hits in **`.rom`** (raise if truncated).
MAX_ROM_PATTERN_HITS = 25

# Capstone: optional MIPS BE disassembly at each `.rom` pattern hit (install **`capstone`** in PyGhidra env).
CAPSTONE_MIPS_INSNS_PER_ROM_HIT = 4
# If False, skip Capstone under **Repo TOML hints** only (hex there still runs when **HEX_DUMP_BYTES_AT_ROM_OFFSETS** > 0).
CAPSTONE_AT_REPO_HINTS = True

# First **N** bytes hex at bootstrap hits + under **EXPECTED** / **repo hints** (0 = disable).
HEX_DUMP_BYTES_AT_ROM_OFFSETS = 16


def _task_monitor():
    try:
        from ghidra.util.task import TaskMonitor

        return TaskMonitor.DUMMY
    except Exception:
        try:
            from ghidra.util.task import ConsoleTaskMonitor

            return ConsoleTaskMonitor()
        except Exception:
            return None


def _find_all_bytes(mem, start, end, pattern_bytes, max_hits):
    """Same pattern as **`RSP_LibUltra_And_IMEM_Scan.py`** — find all occurrences in range."""
    hits = []
    if pattern_bytes is None or len(pattern_bytes) == 0:
        return hits
    mon = _task_monitor()
    pat = bytes(pattern_bytes)
    cur = start
    plen = len(pat)
    try:
        end_off = int(end.getOffset())
    except Exception:
        return hits
    while cur is not None and len(hits) < max_hits:
        try:
            nxt = mem.findBytes(cur, end, pat, None, True, mon)
        except TypeError:
            try:
                nxt = mem.findBytes(cur, end, pat, None, True)
            except Exception:
                break
        except Exception:
            break
        if nxt is None:
            break
        hits.append(nxt)
        try:
            if int(nxt.getOffset()) + plen > end_off:
                break
            cur = nxt.add(1)
        except Exception:
            break
    return hits


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def rom_file_offset(rom, addr):
    """Byte offset into cart image if addr lies in `.rom`; else None (**Find_RSP_* ** same idea)."""
    if rom is None or addr is None:
        return None
    if not rom.contains(addr):
        return None
    return int(addr.getOffset() - rom.getStart().getOffset())


def _capstone_mips_be_disasm(mem, addr, md_mips, max_insns, buf_len=32):
    """
    First **max_insns** MIPS32 **big-endian** insns at **addr** using Capstone (N64 cart view).
    Returns **(lines, err)** where **lines** is **None** on failure.
    """
    if md_mips is None:
        return None, "no_engine"
    buf = bytearray(buf_len)
    try:
        nb = mem.getBytes(addr, buf)
    except Exception:
        return None, "read_fail"
    if nb is None or nb < 4:
        return None, "short_read"
    data = bytes(buf[: int(nb)])
    lines = []
    try:
        for i, insn in enumerate(md_mips.disasm(data, 0)):
            lines.append("%s %s" % (insn.mnemonic, insn.op_str))
            if i + 1 >= max_insns:
                break
    except Exception:
        return None, "disasm_fail"
    return (lines if lines else None), None


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


def _ref_kind_str(rt):
    try:
        if rt.isData():
            return "DATA"
        if rt.isCall() or rt.isJump() or rt.isConditional() or rt.isUnconditional():
            return "FLOW"
    except Exception:
        pass
    return "OTHER"


def _be_u32_at(mem, addr):
    buf = bytearray(4)
    try:
        if mem.getBytes(addr, buf) != 4:
            return None
    except Exception:
        return None
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3]


def _phys_to_kseg0_lo(pa):
    """Show low **KSEG0** alias **`0x80000000 | pa`** for **`pa < 0x00800000`** heuristic."""
    pa = int(pa) & 0xFFFFFFFF
    if pa < 0x00800000:
        return 0x80000000 | pa
    return None


def _rom_addr_from_file_offset(rom, file_off):
    """**`.rom`** **Address** for cart file byte offset, or **None**."""
    if rom is None:
        return None
    try:
        return rom.getStart().add(int(file_off) & 0xFFFFFFFF)
    except Exception:
        return None


def _print_capstone_mips_block(mem, rom, md_mips, file_off, label, max_insns):
    """Print **label** + Capstone lines at **file_off** in **`.rom`** (no-op if unavailable)."""
    if md_mips is None or rom is None or int(max_insns) <= 0:
        return
    addr = _rom_addr_from_file_offset(rom, file_off)
    if addr is None or not rom.contains(addr):
        print("  capstone %s: (bad file offset 0x%X)" % (label, int(file_off) & 0xFFFFFFFF))
        return
    lines, cerr = _capstone_mips_be_disasm(mem, addr, md_mips, int(max_insns))
    if lines:
        print("  capstone MIPS BE @ file 0x%X (%s):" % (int(file_off) & 0xFFFFFFFF, label))
        for k, ln in enumerate(lines, 1):
            print("    [%d] %s" % (k, ln))
    elif cerr:
        print("  capstone %s: (%s)" % (label, cerr))


def _sig_bytes(be_u32_tuple):
    return b"".join(struct.pack(">I", int(w) & 0xFFFFFFFF) for w in be_u32_tuple)


def _hex_dump_line(mem, addr, nbytes):
    """Return **'HH HH…'** for first **nbytes** at **addr**, or **None**."""
    n = int(nbytes) & 0xFFFFFFFF
    if n <= 0:
        return None
    cap = min(n, 64)
    buf = bytearray(cap)
    try:
        got = mem.getBytes(addr, buf)
    except Exception:
        return None
    if got is None or got <= 0:
        return None
    return " ".join("%02X" % b for b in bytes(buf[: int(got)]))


def _print_hex_if(mem, addr, label, nbytes, indent="  "):
    if int(nbytes) <= 0:
        return
    line = _hex_dump_line(mem, addr, nbytes)
    if line:
        print("%shex (%s): %s" % (indent, label, line))


def _expected_rom_prefix_vs_imem_sig(mem, rom, md_mips, expected_off, expected_size, sig, which_label):
    """
    Compare **min(len(sig), expected_size)** bytes at **`.rom`** file offset **expected_off** to **sig** prefix.
    **which_label** is a short name for log lines (e.g. **aspMain** / **njpgdspMain**).
    """
    need = min(len(sig), int(expected_size) & 0xFFFFFFFF)
    if need <= 0:
        print(
            "  %s: EXPECTED size too small (need > 0 bytes to compare with IMEM prefix)."
            % which_label
        )
        return
    try:
        start = rom.getStart().add(int(expected_off) & 0xFFFFFFFF)
    except Exception:
        start = None
    if start is None or not rom.contains(start):
        print("  %s: EXPECTED file offset invalid or outside `.rom`." % which_label)
        return
    buf = bytearray(need)
    ok = mem.getBytes(start, buf) == need
    _print_hex_if(
        mem,
        start,
        "%s EXPECTED prefix window" % which_label,
        HEX_DUMP_BYTES_AT_ROM_OFFSETS,
    )
    if ok and buf == sig[:need]:
        print(
            "  %s: MATCH — first %d bytes at file offset 0x%X equal IMEM prefix."
            % (which_label, need, int(expected_off) & 0xFFFFFFFF)
        )
        if md_mips is not None and int(CAPSTONE_MIPS_INSNS_PER_ROM_HIT) > 0:
            _print_capstone_mips_block(
                mem,
                rom,
                md_mips,
                int(expected_off) & 0xFFFFFFFF,
                "%s EXPECTED offset (MIPS decode meaningless if bytes are RSP ucode)" % which_label,
                CAPSTONE_MIPS_INSNS_PER_ROM_HIT,
            )
    else:
        print(
            "  %s: MISMATCH at file offset 0x%X (read ok=%s)."
            % (which_label, int(expected_off) & 0xFFFFFFFF, ok)
        )
        if md_mips is not None and start is not None:
            _print_capstone_mips_block(
                mem,
                rom,
                md_mips,
                int(expected_off) & 0xFFFFFFFF,
                "%s EXPECTED (why mismatch?)" % which_label,
                CAPSTONE_MIPS_INSNS_PER_ROM_HIT,
            )


def _print_ram_vram(label, mem, ram, rom, ref_mgr, fm, listing, space, vram):
    a = int(vram) & 0xFFFFFFFF
    try:
        addr = space.getAddress(a)
    except Exception:
        print("  %s: 0x%08X — (bad address)" % (label, a))
        return
    if not ram.contains(addr):
        print(
            "  %s: 0x%08X — NOT in `.ram` (wrong VA, overlay, or import map)"
            % (label, a)
        )
        ro = rom_file_offset(rom, addr)
        if ro is not None:
            print("    (same VA maps to `.rom` file offset 0x%X — unexpected for RDRAM pointer)"
                  % ro)
        return
    w = _be_u32_at(mem, addr)
    if w is None:
        wstr = "(read failed)"
    else:
        wstr = "0x%08X" % w
    ro = rom_file_offset(rom, addr)
    rom_note = ""
    if ro is not None:
        rom_note = "  also in `.rom` file offset 0x%X (!)" % ro
    print("  %s: 0x%08X  in `.ram`  BE u32=%s%s" % (label, a, wstr, rom_note))
    refs = list(_iter_references_to(ref_mgr, addr))
    print("    incoming xrefs: %d" % len(refs))
    for i, ref in enumerate(refs[:MAX_XREFS_LIST], 1):
        fa = ref.getFromAddress()
        rt = ref.getReferenceType()
        rk = _ref_kind_str(rt)
        try:
            rts = rt.toString()
        except Exception:
            rts = str(rt)
        ins = listing.getInstructionAt(fa) if listing is not None else None
        dis = ins.toString().replace("\n", " ")[:76] if ins is not None else "(no insn)"
        fn = fm.getFunctionContaining(fa)
        fnn = fn.getName() if fn is not None else "?"
        print("      [%d] kind=%s  from=%s  fn=%s  type=%s" % (i, rk, fa, fnn, rts))
        print("          %s" % dis)
    if len(refs) > MAX_XREFS_LIST:
        print("      ... %d more" % (len(refs) - MAX_XREFS_LIST))


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    ref_mgr = prog.getReferenceManager()
    fm = prog.getFunctionManager()
    listing = prog.getListing()

    ram = get_block_exact(mem, ".ram")
    rom = get_block_exact(mem, ".rom")
    if ram is None:
        print("ERROR: need `.ram` block.")
        return
    if rom is None:
        print("WARNING: no `.rom` — ROM pattern search and pointer→file offset skipped.")

    space = ram.getStart().getAddressSpace()

    print("=== RSPRecomp_Confirm_Findings (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("Edit tunables at top of this script to match your P64/Ghidra session.")
    print("")
    print("--- Struct fields (BASE + offset) ---")
    base = int(STRUCT_BASE_VRAM) & 0xFFFFFFFF
    for off in STRUCT_FIELD_OFFSETS:
        ea = (base + (int(off) & 0xFFFFFFFF)) & 0xFFFFFFFF
        _print_ram_vram(
            "BASE+0x%X" % off, mem, ram, rom, ref_mgr, fm, listing, space, ea
        )

    print("")
    print("--- Microcode / DMA RDRAM pointers ---")
    if MICROCODE_RDDRAM_KSEG0:
        _print_ram_vram(
            "MICROCODE_KSEG0",
            mem,
            ram,
            rom,
            ref_mgr,
            fm,
            listing,
            space,
            MICROCODE_RDDRAM_KSEG0,
        )
    if MICROCODE_RDDRAM_PHYS is not None:
        k0 = _phys_to_kseg0_lo(MICROCODE_RDDRAM_PHYS)
        print(
            "  MICROCODE_PHYS 0x%08X  heuristic KSEG0 alias 0x%08X"
            % (int(MICROCODE_RDDRAM_PHYS) & 0xFFFFFFFF, k0 if k0 else 0)
        )
        if k0:
            _print_ram_vram(
                "MICROCODE_PHYS→KSEG0 xrefs",
                mem,
                ram,
                rom,
                ref_mgr,
                fm,
                listing,
                space,
                k0,
            )
    if SMALL_DMA_RDDRAM_PHYS is not None:
        k0 = _phys_to_kseg0_lo(SMALL_DMA_RDDRAM_PHYS)
        print(
            "  SMALL_DMA_PHYS 0x%08X  heuristic KSEG0 alias 0x%08X"
            % (int(SMALL_DMA_RDDRAM_PHYS) & 0xFFFFFFFF, k0 if k0 else 0)
        )
        if k0:
            _print_ram_vram(
                "SMALL_DMA_PHYS→KSEG0 xrefs",
                mem,
                ram,
                rom,
                ref_mgr,
                fm,
                listing,
                space,
                k0,
            )

    print("")
    print("--- Anchor PC (function + disasm) ---")
    try:
        ap = space.getAddress(int(ANCHOR_PC_VRAM) & 0xFFFFFFFF)
    except Exception:
        ap = None
    if ap is None or not ram.contains(ap):
        print("  ANCHOR 0x%08X not in `.ram`." % (int(ANCHOR_PC_VRAM) & 0xFFFFFFFF))
    else:
        fn = fm.getFunctionContaining(ap)
        if fn:
            print(
                "  0x%08X in %s @ entry %s"
                % (
                    int(ANCHOR_PC_VRAM) & 0xFFFFFFFF,
                    fn.getName(),
                    fn.getEntryPoint(),
                )
            )
        else:
            print("  0x%08X — (no function)" % (int(ANCHOR_PC_VRAM) & 0xFFFFFFFF))
        ins = listing.getInstructionAt(ap)
        if ins:
            print("  insn @ anchor: %s" % ins.toString().replace("\n", " ")[:88])
        for delta in (-4, 0, 4, 8):
            try:
                ap2 = ap.add(delta)
                ins2 = listing.getInstructionAt(ap2)
                if ins2:
                    print("    @ %s: %s" % (ap2, ins2.toString().replace("\n", " ")[:88]))
            except Exception:
                pass

    print("")
    print("--- IMEM bootstrap BE words → search `.rom` ---")
    sig = _sig_bytes(IMEM_BOOTSTRAP_BE_U32)
    print("  signature length: %d bytes (%d words)" % (len(sig), len(IMEM_BOOTSTRAP_BE_U32)))
    nw = len(sig) // 4
    if nw > 0:
        words = struct.unpack(">" + "I" * nw, sig[: nw * 4])
        print(
            "  IMEM_BOOTSTRAP_BE_U32 (%d words): %s"
            % (nw, ", ".join("0x%08X" % (int(w) & 0xFFFFFFFF) for w in words))
        )
    print("  same prefix as raw bytes: %s" % " ".join("%02X" % b for b in sig))
    md_mips = None
    try:
        from capstone import CS_ARCH_MIPS, CS_MODE_BIG_ENDIAN, CS_MODE_MIPS32, Cs

        md_mips = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_BIG_ENDIAN)
    except ImportError:
        print(
            "  Capstone: not installed — `pip install capstone` in this Python env for MIPS BE lines at hits."
        )
    if rom is None:
        print("  (skip — no `.rom`)")
    else:
        hits = _find_all_bytes(mem, rom.getStart(), rom.getEnd(), sig, MAX_ROM_PATTERN_HITS)
        print("  hits in `.rom` (capped at %d): %d" % (MAX_ROM_PATTERN_HITS, len(hits)))
        for ha in hits:
            rfo = rom_file_offset(rom, ha)
            print(
                "    file offset 0x%X  program VA %s  TOML text_offset candidate (verify unique + DMA chain)"
                % (rfo if rfo is not None else -1, ha)
            )
            _print_hex_if(mem, ha, "bootstrap hit", HEX_DUMP_BYTES_AT_ROM_OFFSETS, indent="    ")
            if md_mips is not None and int(CAPSTONE_MIPS_INSNS_PER_ROM_HIT) > 0 and rfo is not None:
                _print_capstone_mips_block(
                    mem,
                    rom,
                    md_mips,
                    int(rfo) & 0xFFFFFFFF,
                    "bootstrap pattern hit",
                    CAPSTONE_MIPS_INSNS_PER_ROM_HIT,
                )
            if rfo == 0x4BE20:
                print(
                    "      NOTE: on AFA USA this often matches **MIPS** at ROM 0x4BE20 (see repo **asm/4BE20.s**"
                    " **`func_8024AE70`**), not RSP IMEM text — compare with **config/afa_rsp/aspMain.afa.us.template.toml**."
                )
        if not hits:
            print("    (none — wrong signature, byteswapped ROM view, or ucode not stored verbatim in .rom)")

    print("")
    print("--- Optional EXPECTED_TEXT_OFFSET prefix check ---")
    if (
        EXPECTED_TEXT_OFFSET_IN_ROM is not None
        and EXPECTED_TEXT_SIZE is not None
        and rom is not None
    ):
        _expected_rom_prefix_vs_imem_sig(
            mem,
            rom,
            md_mips,
            EXPECTED_TEXT_OFFSET_IN_ROM,
            EXPECTED_TEXT_SIZE,
            sig,
            "aspMain",
        )
    elif EXPECTED_TEXT_OFFSET_IN_ROM is not None or EXPECTED_TEXT_SIZE is not None:
        if rom is None:
            print(
                "  EXPECTED_* set but no `.rom` block — cannot verify prefix in cart image."
            )
        else:
            print(
                "  Set **both** EXPECTED_TEXT_OFFSET_IN_ROM and EXPECTED_TEXT_SIZE (or clear both)."
            )
    else:
        print("  (set EXPECTED_TEXT_OFFSET_IN_ROM + EXPECTED_TEXT_SIZE to enable)")

    print("")
    print("--- Optional njpgdsp EXPECTED_NJPG_* prefix check ---")
    sig_njpg = _sig_bytes(IMEM_BOOTSTRAP_NJPG_BE_U32)
    if EXPECTED_NJPG_TEXT_OFFSET_IN_ROM is None and EXPECTED_NJPG_TEXT_SIZE is None:
        print("  (disabled — set **EXPECTED_NJPG_TEXT_OFFSET_IN_ROM** + **EXPECTED_NJPG_TEXT_SIZE** from **njpgdspMain.afa.us.template.toml**)")
    elif len(sig_njpg) == 0:
        print("  Skipped: **IMEM_BOOTSTRAP_NJPG_BE_U32** is empty.")
        print(
            "  Paste BE u32 words from P64 for the **njpgdsp** task IMEM tail (**text_address** 0x%08X per template)."
            % (int(EXPECTED_NJPG_TEXT_ADDRESS) & 0xFFFFFFFF)
        )
    elif EXPECTED_NJPG_TEXT_OFFSET_IN_ROM is None or EXPECTED_NJPG_TEXT_SIZE is None:
        if rom is None:
            print("  EXPECTED_NJPG_* incomplete and no `.rom` — cannot verify.")
        else:
            print(
                "  Set **both** EXPECTED_NJPG_TEXT_OFFSET_IN_ROM and EXPECTED_NJPG_TEXT_SIZE (or clear **IMEM_BOOTSTRAP_NJPG_BE_U32**)."
            )
    elif rom is None:
        print("  EXPECTED_NJPG_* set but no `.rom` — cannot verify prefix in cart image.")
    else:
        _expected_rom_prefix_vs_imem_sig(
            mem,
            rom,
            md_mips,
            EXPECTED_NJPG_TEXT_OFFSET_IN_ROM,
            EXPECTED_NJPG_TEXT_SIZE,
            sig_njpg,
            "njpgdspMain",
        )

    print("")
    print("--- TOML text_address note ---")
    print(
        "  aspMain template: text_address = 0x%08X (**config/afa_rsp/aspMain.afa.us.template.toml**)"
        % (int(EXPECTED_TEXT_ADDRESS) & 0xFFFFFFFF)
    )
    print(
        "  njpgdspMain template: text_address = 0x%08X (**config/afa_rsp/njpgdspMain.afa.us.template.toml**)"
        % (int(EXPECTED_NJPG_TEXT_ADDRESS) & 0xFFFFFFFF)
    )
    print("  Confirm each matches the **OSTask** / IMEM snapshot you are validating.")

    print("")
    print("--- Repo TOML `text_offset` hints (cross-check vs bootstrap hits) ---")
    if REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM is not None:
        print(
            "  aspMain committed ROM offset (see **config/afa_rsp/aspMain.afa.us.template.toml**): 0x%X"
            % (int(REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM) & 0xFFFFFFFF)
        )
    if REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM is not None:
        print(
            "  njpgdspMain committed ROM offset (see **config/afa_rsp/njpgdspMain.afa.us.template.toml**): 0x%X"
            % (int(REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM) & 0xFFFFFFFF)
        )
    if REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM is None and REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM is None:
        print("  (set **REPO_TOML_HINT_*_TEXT_OFFSET_ROM** to print committed offsets)")
    else:
        print(
            "  If IMEM bootstrap hit **0x4BE20** but asp hint is **0x4DAB0**, the hit is **MIPS** (**`asm/4BE20.s`**), not RSP text."
        )
        if rom is not None and int(HEX_DUMP_BYTES_AT_ROM_OFFSETS) > 0:
            if REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM is not None:
                a = _rom_addr_from_file_offset(rom, int(REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM) & 0xFFFFFFFF)
                if a is not None and rom.contains(a):
                    _print_hex_if(mem, a, "repo aspMain text_offset", HEX_DUMP_BYTES_AT_ROM_OFFSETS)
            if REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM is not None:
                a = _rom_addr_from_file_offset(rom, int(REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM) & 0xFFFFFFFF)
                if a is not None and rom.contains(a):
                    _print_hex_if(mem, a, "repo njpgdspMain text_offset", HEX_DUMP_BYTES_AT_ROM_OFFSETS)
        if (
            CAPSTONE_AT_REPO_HINTS
            and rom is not None
            and md_mips is not None
            and int(CAPSTONE_MIPS_INSNS_PER_ROM_HIT) > 0
        ):
            if REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM is not None:
                _print_capstone_mips_block(
                    mem,
                    rom,
                    md_mips,
                    int(REPO_TOML_HINT_ASP_TEXT_OFFSET_ROM) & 0xFFFFFFFF,
                    "repo aspMain text_offset",
                    CAPSTONE_MIPS_INSNS_PER_ROM_HIT,
                )
            if REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM is not None:
                _print_capstone_mips_block(
                    mem,
                    rom,
                    md_mips,
                    int(REPO_TOML_HINT_NJPG_TEXT_OFFSET_ROM) & 0xFFFFFFFF,
                    "repo njpgdspMain text_offset",
                    CAPSTONE_MIPS_INSNS_PER_ROM_HIT,
                )

    print("")
    print("--- PI cart seeds (manual splat / PI map) ---")
    for pi in PI_CART_ADDR_CANDIDATES:
        print(
            "  PI_CART 0x%08X — subtract cart base per your map (often 0x10000000 domain) for ROM byte."
            % (int(pi) & 0xFFFFFFFF)
        )

    print("")
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1")


main()
