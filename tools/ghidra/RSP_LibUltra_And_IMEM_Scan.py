# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): scan for libultra-style RSP / PI / task clues (symbol names, IMEM constants, ASCII).
#
# Complements tools/ghidra/Find_RSP_Microcode_ROM_Hints.py: that script scores .ram→.rom xrefs;
# this one searches for common *names* and *immediate values* (0x04001000 / 0x04001080) and short
# ASCII substrings so you can jump to likely `osSpTask*` / `OSTask` / DMA setup in the Listing.
# Paradigm-era titles (AFA, Pilotwings) may ship *without* embedded `osSpTask` strings; AFA USA
# Ghidra runs still show `uvGfx` / `uvSc` / `uvDMA` scheduler rodata — see PARADIGM_ASCII_PATTERNS.
#
# Same project layout as Phase2_Closeout_Report.py: MemoryBlock `.rom` (cart) and `.ram` (MIPS).
# Run: support/pyghidraRun.bat — Script Manager — this file.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; N64brew memory map / libultra RSP task layout.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_LibUltra_And_IMEM_Scan
#@description Scan symbols, immediates, and RAM bytes for RSP/task/DMA clues
#@author AeroAssault64

from __future__ import print_function

# --- Tunables -----------------------------------------------------------------
# Print at most this many rows per section (raise if needed).
MAX_SYMBOL_HITS = 60
MAX_INSN_IMM_HITS = 80
MAX_STRING_HITS_PER_PATTERN = 15
MAX_PARADIGM_STRING_HITS = 12
# IMEM bases often seen in N64 ucode TOMLs (RSPRecomp `text_address` examples).
IMEM_IMMEDIATES = (
    0x04001000,
    0x04001080,
    0x04000800,
    0x04001800,
    0x04002000,
)
# MIPS immediates sometimes appear as sign-extended negative forms in disassembly — rare for IMEM.
# PI / RDRAM register window (DMA setup) — helps find `osPiStartDma`-style code (N64brew).
PI_REGS_HINT = (0xA4600000, 0xA4040010)

# Symbol name substrings (lowercase match).
SYMBOL_KEYWORDS = (
    "sptask",
    "ossp",
    "ostask",
    "rsp",
    "pistart",
    "pimgr",
    "pidma",
    "dma",
    "cart",
    "leo",
    "jpeg",
    "jpg",
    "njpg",
    "asp",
    "f3d",
    "gbi",
    "gfx",
    "rdp",
)

# ASCII substrings to search in `.ram` only (libultra / SDK names; keep patterns long to cut noise).
ASCII_PATTERNS = (
    b"osSpTask",
    b"osPiStartDma",
    b"osPiDma",
    b"osPi",
    b"OSTask",
)

# Substrings observed in AFA USA rodata / error strings (Ghidra labels like s_uvGfxBegin…, s__uvDMA:…).
# Pilotwings 64 is a Paradigm-era cross-check title (Docs/SystemPrompt.md); patterns may or may not match.
# Ghidra default string labels often use '_' between words while the cart uses ASCII spaces (IDO-era
# format strings): e.g. symbol `s_RSP_timeout_on_%c…` @ 802544ac vs bytes `RSP timeout on %c…`.
PARADIGM_ASCII_PATTERNS = (
    b"uvGfxBegin",
    b"uvScDoneGfx",
    b"uvDMA:",
    b"RSP timeout on",
    b"RDP timeout on",
)


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


def _scalar_unsigned(obj):
    try:
        from ghidra.program.model.scalar import Scalar

        if isinstance(obj, Scalar):
            return int(obj.getUnsignedValue()) & 0xFFFFFFFF
    except Exception:
        pass
    return None


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
    """Return up to max_hits Addresses in [start,end] where pattern_bytes occurs."""
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
            # Older Ghidra: no TaskMonitor arg
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


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    ram = get_block_exact(mem, ".ram")
    rom = get_block_exact(mem, ".rom")
    if ram is None:
        print("ERROR: need MemoryBlock named exactly `.ram`.")
        return
    if rom is None:
        print("WARNING: no `.rom` block — byte scans still run on `.ram` only.")

    ram_set = memory_block_as_address_set(ram)
    imms = set(IMEM_IMMEDIATES) | set(PI_REGS_HINT)

    print("=== RSP_LibUltra_And_IMEM_Scan (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    print("")

    # --- Symbols --------------------------------------------------------------
    print("--- Symbols (name contains keyword) ---")
    sym_n = 0
    try:
        st = prog.getSymbolTable()
        it = st.getAllSymbols(True)
        for sym in _iter_listing_cursor(it):
            if sym_n >= MAX_SYMBOL_HITS:
                break
            n = sym.getName().lower()
            if not any(k in n for k in SYMBOL_KEYWORDS):
                continue
            print("  %s  @ %s  (%s)" % (sym.getName(), sym.getAddress(), sym.getSymbolType()))
            sym_n += 1
    except Exception as e:
        print("  (symbol scan failed: %s)" % e)
    if sym_n == 0:
        print("  (no symbol names matched — names may be FUN_/DAT_ only; use insn + ASCII sections)")
    print("")

    # --- Instruction immediates in .ram ---------------------------------------
    print("--- .ram instructions: operand Scalar in IMEM/PI hint set ---")
    imm_hits = 0
    ins_it = listing.getInstructions(ram_set, True)
    for ins in _iter_listing_cursor(ins_it):
        if imm_hits >= MAX_INSN_IMM_HITS:
            break
        try:
            nops = ins.getNumOperands()
        except Exception:
            continue
        for opi in range(nops):
            for ob in ins.getOpObjects(opi):
                v = _scalar_unsigned(ob)
                if v is None:
                    continue
                if v not in imms:
                    continue
                print(
                    "  0x%08X  insn @ %s  %s"
                    % (v, ins.getAddress(), ins.toString().replace("\n", " ")[:120])
                )
                imm_hits += 1
                if imm_hits >= MAX_INSN_IMM_HITS:
                    break
            if imm_hits >= MAX_INSN_IMM_HITS:
                break
    if imm_hits == 0:
        print(
            "  (no matching immediates — operands may use relocations / reg-only math; "
            "try ASCII search or decompiler view on graphics init.)"
        )
    print("")

    # --- ASCII patterns in .ram (raw bytes) -----------------------------------
    print("--- .ram raw-byte search (ASCII substrings) ---")
    for pat in ASCII_PATTERNS:
        found = _find_all_bytes(mem, ram.getStart(), ram.getEnd(), pat, MAX_STRING_HITS_PER_PATTERN)
        if not found:
            print("  %r: (no hits)" % pat.decode("ascii", errors="replace"))
            continue
        print("  %r: %d hit(s)" % (pat.decode("ascii", errors="replace"), len(found)))
        for a in found[:MAX_STRING_HITS_PER_PATTERN]:
            print("    @ %s" % a)
    print("")

    print("--- .ram raw-byte search (Paradigm / AFA-style scheduler rodata) ---")
    print("  (see Docs/RepoInjests/Pilotwings/README.txt for Pilotwings 64 RSPRecomp *example* TOML)")
    for pat in PARADIGM_ASCII_PATTERNS:
        found = _find_all_bytes(
            mem, ram.getStart(), ram.getEnd(), pat, MAX_PARADIGM_STRING_HITS
        )
        if not found:
            print("  %r: (no hits)" % pat.decode("ascii", errors="replace"))
            continue
        print("  %r: %d hit(s)" % (pat.decode("ascii", errors="replace"), len(found)))
        for a in found[:MAX_PARADIGM_STRING_HITS]:
            print("    @ %s" % a)
    print("")

    print("Done. Follow hits in the Listing / decompiler; cross-check RSPRecomp `text_address` in")
    print("      lib/Zelda64Recomp/AFA_PORT.md section 1 + config/afa_rsp/*.template.toml.")


main()
