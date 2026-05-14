# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): suggest ROM file offsets for RSPRecomp `text_offset` (AFA USA cart).
#
# RSPRecomp expects `text_offset` / `text_size` as byte offsets into the same ROM image as
# `rom_file_path` (see config/afa_rsp/*.template.toml and upstream aspMain.us.rev1.toml on
# Zelda64Recomp — same key names). Splat `config/splat.yaml` does not emit these; this script
# surfaces *candidates* by finding MIPS code and defined pointers in `.ram` that reference
# addresses inside Ghidra's `.rom` block (same layout as tools/ghidra/Phase2_Closeout_Report.py).
#
# This is heuristic output — verify in the Listing (xref, DMA / OSTask context) before committing
# values to `aspMain.afa.us.toml` / `njpgdspMain.afa.us.toml`. `text_address` is usually
# 0x04001000 (aspMain) and 0x04001080 (njpgdspMain) for libultra-style tasks; confirm against
# your game's `OSTask` setup (N64brew memory map / libultra docs).
#
# Run: Ghidra 12+ with support/pyghidraRun.bat — Script Manager — this file under tools/ghidra.
# Older Ghidra: MemoryBlock has no getBody(); this script uses AddressRangeImpl + AddressSet instead.
# PyGhidra: getReferencesFrom may return Reference[] (no hasNext) — see _iter_references_from().
# Companion: tools/ghidra/RSP_LibUltra_And_IMEM_Scan.py (symbol / IMEM immediate / ASCII scans);
# tools/ghidra/RSP_Scheduler_String_Xref_Trace.py (incoming xref from rodata -> functions -> .rom refs);
# tools/ghidra/RSP_IMEM_Load_And_Helper_Call_Trace.py (0x0400… SP immediates + optional jal windows);
# tools/ghidra/RSP_List_Jal_Callees_From_Function.py (`jal` callee entries from a function body).
#
#@runtime PyGhidra
#@category AeroAssault64
#@name Find_RSP_Microcode_ROM_Hints
#@description Heuristic ROM offsets referenced from .ram for RSPRecomp text_offset discovery
#@author AeroAssault64

from __future__ import print_function

from collections import Counter, defaultdict

# --- Tunables -----------------------------------------------------------------
# Ignore ROM header / very low offsets (BIOS string area, etc.).
MIN_ROM_OFFSET = 0x1000
# Report at least this many hits for an offset to reduce noise (lower = more output).
MIN_HITS = 2
# How many rows to print from the merged histogram.
TOP_N = 40
# If the main table (min_hits=MIN_HITS) prints fewer than this many rows, also dump hits==1.
SINGLE_HIT_APPEND_IF_PRIMARY_LT = 8
SINGLE_HIT_APPEND_MAX = 30
# Max .ram Data addresses to record per ROM offset (for "Go To" in Ghidra).
MAX_DATA_RAM_REFS_PER_OFFSET = 8
# Typical IMEM bases for Zelda64Recomp-style TOMLs (informational only).
TEXT_ADDR_ASP = 0x04001000
TEXT_ADDR_NJPG = 0x04001080


def get_block_exact(mem, name):
    for b in mem.getBlocks():
        if b.getName() == name:
            return b
    return None


def memory_block_as_address_set(block):
    """
    AddressSet covering one MemoryBlock. Older Ghidra builds do not have MemoryBlock.getBody()
    (added in newer releases); AddressRangeImpl + AddressSet works across versions.
    """
    from ghidra.program.model.address import AddressRangeImpl
    from ghidra.program.model.address import AddressSet

    aset = AddressSet()
    aset.add(AddressRangeImpl(block.getStart(), block.getEnd()))
    return aset


def _iter_listing_cursor(cursor):
    """
    Ghidra Listing iterators use hasNext()/next(). PyGhidra may instead expose a Java array
    or Python sequence — iterate both shapes.
    """
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
    """
    ReferenceManager.getReferencesFrom(Address) returns ReferenceIterator on some Ghidra builds
    and Reference[] (Java array) on others — PyGhidra exposes the latter without hasNext().
    """
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
    """Byte offset into cart image if addr lies in .rom; else None."""
    if rom is None or addr is None:
        return None
    if not rom.contains(addr):
        return None
    return int(addr.getOffset() - rom.getStart().getOffset())


def _scalar_unsigned(obj):
    try:
        from ghidra.program.model.scalar import Scalar

        if isinstance(obj, Scalar):
            return int(obj.getUnsignedValue()) & 0xFFFFFFFF
    except Exception:
        pass
    return None


def _first_register_name(ins, op_index):
    """Return first Register operand object name at op_index, or None."""
    try:
        from ghidra.program.model.lang import Register

        for ob in ins.getOpObjects(op_index):
            if isinstance(ob, Register):
                return ob.getName()
    except Exception:
        pass
    return None


def _lui_upper(ins):
    """Return (dest_reg, upper_16_as_uint32) for a LUI, or None."""
    if ins is None:
        return None
    if ins.getMnemonicString().lower() != "lui":
        return None
    if ins.getNumOperands() < 2:
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
    """Return (mn, rt, rs, imm16) or (None, None, None, None) — always a 4-tuple."""
    _nil = (None, None, None, None)
    if ins is None:
        return _nil
    mn = ins.getMnemonicString().lower()
    if mn not in ("addiu", "addi", "ori", "daddiu", "daddi"):
        return _nil
    if ins.getNumOperands() < 3:
        return _nil
    # MIPS: ADDIU rt, rs, imm  -> operands 0=rt, 1=rs, 2=imm (typical)
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
    """Combine LUI high half with lower from ADDIU (sign-ext) or ORI (zero-ext)."""
    imm16 &= 0xFFFF
    if mn in ("ori",):
        return (hi32 & 0xFFFF0000) | imm16
    # sign-extend 16-bit
    if imm16 & 0x8000:
        simm = imm16 - 0x10000
    else:
        simm = imm16
    return (hi32 + simm) & 0xFFFFFFFF


def _dump_rom_prefix(mem, rom, rom_off, nbytes):
    rom_start = rom.getStart()
    a = rom_start.add(rom_off)
    parts = []
    for i in range(nbytes):
        if not mem.contains(a.add(i)):
            break
        parts.append("%02X" % (mem.getByte(a.add(i)) & 0xFF))
    return " ".join(parts)


def _leading_zero_run(mem, rom, rom_off, nbytes=32):
    """Count leading 0x00 bytes at ROM offset (padding / BSS image in ROM)."""
    a = rom.getStart().add(rom_off)
    z = 0
    for i in range(nbytes):
        if not mem.contains(a.add(i)):
            break
        if (mem.getByte(a.add(i)) & 0xFF) != 0:
            break
        z += 1
    return z


def _print_row_hints(mem, rom, off, data_ram_refs):
    """Continuation lines: where .ram pointer Data lives; padding heuristic."""
    bits = []
    refs = data_ram_refs.get(off)
    if refs:
        bits.append(".ram Data @ %s" % ", ".join(refs[:MAX_DATA_RAM_REFS_PER_OFFSET]))
    zrun = _leading_zero_run(mem, rom, off)
    if zrun >= 12:
        bits.append("leading 0x00 x%d (not typical ucode start — check Data type / false pointer)" % zrun)
    if bits:
        print("       # " + " | ".join(bits))


def _cluster_contiguous_ram_pointer_rows(records, step=4, min_len=3):
    """
    Find runs of Data addresses spaced by `step` (e.g. four dwords at 803fa684..803fa690).
    Yields list of (ram_address, rom_file_offset) per cluster.
    """
    if len(records) < min_len:
        return
    uniq = {}
    for ram_addr, rom_off in records:
        uniq[int(ram_addr.getOffset())] = (ram_addr, rom_off)
    rows = sorted(uniq.values(), key=lambda t: int(t[0].getOffset()))
    run = [rows[0]]
    for i in range(1, len(rows)):
        po = int(rows[i - 1][0].getOffset())
        co = int(rows[i][0].getOffset())
        if co - po == step:
            run.append(rows[i])
        else:
            if len(run) >= min_len:
                yield run
            run = [rows[i]]
    if len(run) >= min_len:
        yield run


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    ref_mgr = prog.getReferenceManager()

    rom = get_block_exact(mem, ".rom")
    ram = get_block_exact(mem, ".ram")
    if rom is None:
        print("ERROR: need a MemoryBlock named exactly `.rom` (see Phase2_Closeout_Report.py).")
        return
    if ram is None:
        print("ERROR: need a MemoryBlock named exactly `.ram`.")
        return

    rom_start = rom.getStart()
    hits = Counter()
    lui_pair_hits = Counter()
    ram_addrs = memory_block_as_address_set(ram)

    # --- References from instructions in .ram into .rom ----------------------
    ins_iter = listing.getInstructions(ram_addrs, True)
    for ins in _iter_listing_cursor(ins_iter):
        for ref in _iter_references_from(ref_mgr, ins.getAddress()):
            to_addr = ref.getToAddress()
            off = rom_file_offset(rom, to_addr)
            if off is not None and off >= MIN_ROM_OFFSET:
                hits[off] += 1

    # --- LUI + ADDIU/ORI immediate full-address into .rom ---------------------
    pending_lui = {}  # reg_name -> (hi32, insn_addr_str)
    ins_iter = listing.getInstructions(ram_addrs, True)
    for ins in _iter_listing_cursor(ins_iter):
        la = ins.getAddress()
        lui = _lui_upper(ins)
        if lui is not None:
            reg, hi = lui
            pending_lui[reg] = (hi, str(la))
            continue

        parsed = _addiu_or_ori_imm(ins)
        if parsed[0] is None:
            continue
        mn, rt, rs, imm16 = parsed
        if rs not in pending_lui:
            continue
        hi32, _ = pending_lui[rs]
        full = _combine_hi_lo(mn, hi32, imm16) & 0xFFFFFFFF
        # Resolve in the same AddressSpace as the cart image (see Phase2 — `.rom` block).
        space = rom_start.getAddressSpace()
        try:
            to_addr = space.getAddress(int(full))
        except Exception:
            continue
        if rom.contains(to_addr):
            off = rom_file_offset(rom, to_addr)
            if off is not None and off >= MIN_ROM_OFFSET:
                lui_pair_hits[off] += 1
        # Clear LUI slot after classic `lui r; addiu r, r, lo` (keep slot if `addiu t1, t0, lo` may pair again).
        if mn.startswith("addi") and rt == rs:
            pending_lui.pop(rs, None)

    # --- Defined pointers (Data) in .ram to .rom ------------------------------
    data_hits = Counter()
    data_ram_refs = defaultdict(list)
    data_pointer_records = []  # (ram_addr, rom_off) for clustering contiguous tables
    dit = listing.getDefinedData(ram_addrs, True)
    for d in _iter_listing_cursor(dit):
        if not d.isPointer():
            continue
        try:
            v = d.getValue()
        except Exception:
            continue
        to_addr = None
        try:
            from ghidra.program.model.address import Address

            if isinstance(v, Address):
                to_addr = v
        except Exception:
            to_addr = None
        if to_addr is None:
            continue
        off = rom_file_offset(rom, to_addr)
        if off is not None and off >= MIN_ROM_OFFSET:
            data_hits[off] += 1
            if len(data_ram_refs[off]) < MAX_DATA_RAM_REFS_PER_OFFSET:
                data_ram_refs[off].append(str(d.getAddress()))
            data_pointer_records.append((d.getAddress(), off))

    merged = Counter()
    for c in (hits, lui_pair_hits, data_hits):
        merged.update(c)

    print("=== Find_RSP_Microcode_ROM_Hints (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print(
        "ROM block: %s .. %s (file offsets 0 .. 0x%X)"
        % (rom.getStart(), rom.getEnd(), int(rom.getEnd().getOffset() - rom_start.getOffset()))
    )
    print(
        "Counts: insn_operand_refs=%d offsets, lui+imm_pairs=%d, data_pointers=%d"
        % (len(hits), len(lui_pair_hits), len(data_hits))
    )
    if len(lui_pair_hits) == 0:
        print(
            "Note: lui+imm_pairs=0 — pair scanner expects lui + addiu/addi/ori with Scalar imms in "
            "operands 1–2; your listing may differ. RSP blobs are still often found via xref-to-ROM "
            "or OSTask / DMA tables (search RAM for pointers into .rom)."
        )
    print("")
    print(
        "Top ROM offsets (merged, min_hits=%d, min_off=0x%X). "
        "High hit counts often include jump tables / rodata — still useful xrefs." % (MIN_HITS, MIN_ROM_OFFSET)
    )
    print("  offset     hits  insn_ref  lui_pair  data_ptr  first_bytes")
    printed = 0
    printed_offs = set()
    for off, cnt in merged.most_common():
        if cnt < MIN_HITS:
            continue
        b = _dump_rom_prefix(mem, rom, off, 16)
        print(
            "  0x%06X  %4d  %4d  %4d  %4d  %s"
            % (
                off,
                cnt,
                hits.get(off, 0),
                lui_pair_hits.get(off, 0),
                data_hits.get(off, 0),
                b,
            )
        )
        _print_row_hints(mem, rom, off, data_ram_refs)
        printed_offs.add(off)
        printed += 1
        if printed >= TOP_N:
            break

    if printed == 0:
        print("  (no offsets met MIN_HITS — try lowering MIN_HITS in the script header)")

    if printed < SINGLE_HIT_APPEND_IF_PRIMARY_LT and merged:
        print("")
        print(
            "--- Exploratory: single-hit ROM refs (hits==1, max %d rows) ---"
            % SINGLE_HIT_APPEND_MAX
        )
        print("  (often noise — still worth xrefs for DMA/ucode; deduped from table above)")
        print(
            "  Isolated data_ptr rows: re-type the .ram Data in Ghidra if the value looks like a "
            "bit-mask, not a cart offset (false Pointer)."
        )
        sub = 0
        for off, cnt in merged.most_common():
            if cnt != 1 or off in printed_offs:
                continue
            b = _dump_rom_prefix(mem, rom, off, 16)
            print(
                "  0x%06X  %4d  %4d  %4d  %4d  %s"
                % (
                    off,
                    cnt,
                    hits.get(off, 0),
                    lui_pair_hits.get(off, 0),
                    data_hits.get(off, 0),
                    b,
                )
            )
            _print_row_hints(mem, rom, off, data_ram_refs)
            sub += 1
            if sub >= SINGLE_HIT_APPEND_MAX:
                break

    clusters = list(_cluster_contiguous_ram_pointer_rows(data_pointer_records))
    if clusters:
        print("")
        print("--- Contiguous .ram `Data` typed as pointer (spacing 0x4) ---")
        print(
            "  Often one dword table/struct; Ghidra auto-type may be wrong — try `dword` "
            "or a named struct instead of four separate `pointer`."
        )
        for run in clusters:
            roms = ", ".join("0x%X" % r[1] for r in run)
            print(
                "  %d words @ %s .. %s  ->  ROM file offsets: %s"
                % (
                    len(run),
                    run[0][0],
                    run[-1][0],
                    roms,
                )
            )

    print("")
    print("--- RSPRecomp TOML reminder (verify before use) ---")
    print("  aspMain:       text_address = 0x%08X   # typical; confirm in OSTask / game code" % TEXT_ADDR_ASP)
    print("  njpgdspMain:   text_address = 0x%08X" % TEXT_ADDR_NJPG)
    print("  text_size:     NOT inferred here — use ucode length from docs, adjacent blob,")
    print("                 or compare with a known-good recomp (e.g. upstream MM toml sizes).")
    print("  extra_indirect_branch_targets: only for aspMain — see upstream aspMain.us.rev1.toml")
    print("")
    print("Next: pick 1–2 candidates, Go To offset in .rom, xref from .ram, confirm RSP/DMA context,")
    print("      then run tools/phase6_rsprecomp_afa.ps1 after filling config/afa_rsp/*.template.toml.")


main()
