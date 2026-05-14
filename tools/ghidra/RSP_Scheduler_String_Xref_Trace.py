# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): trace incoming xrefs from scheduler / error rodata into MIPS functions,
# then list each function's references *into* the `.rom` cart block (RSPRecomp `text_offset` trail).
#
# Use after `RSP_LibUltra_And_IMEM_Scan.py` — same `.ram` / `.rom` layout as Phase2_Closeout_Report.py.
# Heuristic only: follow xref chains (including one pointer table hop); verify DMA / ucode in Listing.
#
# Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; companion `Find_RSP_Microcode_ROM_Hints.py`.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSP_Scheduler_String_Xref_Trace
#@description Walk uv*/timeout rodata xrefs to functions; report .rom refs from those functions
#@author AeroAssault64

from __future__ import print_function

from collections import deque, defaultdict

# --- Tunables -----------------------------------------------------------------
# VRAM seeds (int, KSEG0). If non-empty, these are used *instead* of DEFAULT_BYTE_PATTERNS scan.
# Example for AFA USA: (0x802544AC, 0x80254FD9, 0x802528F4)
EXPLICIT_SEED_ADDRESSES = ()

# (bytes, label) — same rodata fragments as RSP_LibUltra_And_IMEM_Scan.py Paradigm section.
DEFAULT_BYTE_PATTERNS = (
    (b"uvDMA:", "uvDMA:"),
    (b"uvGfxBegin", "uvGfxBegin"),
    (b"uvScDoneGfx", "uvScDoneGfx"),
    (b"RSP timeout on", "RSP_timeout_msg"),
    (b"RDP timeout on", "RDP_timeout_msg"),
)

MIN_ROM_FILE_OFFSET = 0x1000
MAX_SEED_LOCATIONS = 24
MAX_DATA_CHAIN_HOPS = 6
MAX_FUNCTIONS_PER_SEED = 18
MAX_ROM_REFS_PRINT_PER_FUNC = 22
MAX_LUI_ROM_TARGETS_PER_FUNC = 16
CALLEE_DEPTH = 1
MAX_CALLEES_PER_FUNC = 30


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


def rom_file_offset(rom, addr):
    if rom is None or addr is None:
        return None
    if not rom.contains(addr):
        return None
    return int(addr.getOffset() - rom.getStart().getOffset())


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


def _find_bytes_first_n(mem, ram, pattern_bytes, max_addrs):
    out = []
    if not pattern_bytes or max_addrs <= 0:
        return out
    mon = _task_monitor()
    start = ram.getStart()
    end = ram.getEnd()
    cur = start
    plen = len(pattern_bytes)
    pat = bytes(pattern_bytes)
    try:
        end_off = int(end.getOffset())
    except Exception:
        return out
    while cur is not None and len(out) < max_addrs:
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
        out.append(nxt)
        try:
            if int(nxt.getOffset()) + plen > end_off:
                break
            cur = nxt.add(1)
        except Exception:
            break
    return out


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


def _functions_and_sites_for_seed(ref_mgr, listing, fm, seed_addr, max_hops):
    """
    Incoming xref walk: rodata/string <- pointers in Data <- ... <- instruction in a function.
    Each physical `target` address is expanded once (BFS order = shortest hop first).
    Returns list of (function, ref_from_address, hop_depth).
    """
    results = []
    seen_site = set()
    dq = deque([(seed_addr, 0)])
    expanded = set()

    while dq:
        target, hop = dq.popleft()
        tid = int(target.getOffset())
        if tid in expanded:
            continue
        expanded.add(tid)

        for ref in _iter_references_to(ref_mgr, target):
            fa = ref.getFromAddress()
            fn = fm.getFunctionContaining(fa)
            if fn is not None:
                sk = (int(fn.getEntryPoint().getOffset()), int(fa.getOffset()))
                if sk not in seen_site:
                    seen_site.add(sk)
                    results.append((fn, fa, hop))
                continue
            if hop >= max_hops:
                continue
            if listing.getDataAt(fa) is not None:
                dq.append((fa, hop + 1))
    return results


def _rom_refs_from_instruction(ref_mgr, rom, ins):
    out = []
    for ref in _iter_references_from(ref_mgr, ins.getAddress()):
        to_a = ref.getToAddress()
        off = rom_file_offset(rom, to_a)
        if off is not None and off >= MIN_ROM_FILE_OFFSET:
            out.append((ins.getAddress(), off, str(ref.getReferenceType())))
    return out


def _lui_pair_rom_targets_in_range(listing, rom, rom_start, insn_iter):
    """Like Find_RSP_Microcode_ROM_Hints: lui + addiu/ori -> full pointer into .rom."""
    pending_lui = {}
    targets = []
    for ins in _iter_listing_cursor(insn_iter):
        lui = _lui_upper(ins)
        if lui is not None:
            reg, hi = lui
            pending_lui[reg] = hi
            continue
        parsed = _addiu_or_ori_imm(ins)
        if parsed[0] is None:
            continue
        mn, rt, rs, imm16 = parsed
        if rs not in pending_lui:
            continue
        hi32 = pending_lui[rs]
        full = _combine_hi_lo(mn, hi32, imm16) & 0xFFFFFFFF
        space = rom_start.getAddressSpace()
        try:
            to_addr = space.getAddress(int(full))
        except Exception:
            continue
        if rom.contains(to_addr):
            off = rom_file_offset(rom, to_addr)
            if off is not None and off >= MIN_ROM_FILE_OFFSET:
                targets.append((ins.getAddress(), off))
        if mn.startswith("addi") and rt == rs:
            pending_lui.pop(rs, None)
    return targets


def _collect_callees(ref_mgr, listing, fn, max_callees):
    """Direct `jal` call targets from this function (best-effort)."""
    out = []
    seen = set()
    for ins in _iter_listing_cursor(listing.getInstructions(fn.getBody(), True)):
        if ins.getMnemonicString().lower() != "jal":
            continue
        for ref in _iter_references_from(ref_mgr, ins.getAddress()):
            if not ref.getReferenceType().isCall():
                continue
            ta = ref.getToAddress()
            if ta is None or int(ta.getOffset()) in seen:
                continue
            seen.add(int(ta.getOffset()))
            out.append(ta)
            if len(out) >= max_callees:
                return out
    return out


def _analyze_function(prog, listing, ref_mgr, fm, rom, rom_start, fn):
    rom_by_insn = defaultdict(list)
    for ins in _iter_listing_cursor(listing.getInstructions(fn.getBody(), True)):
        for ia, off, rtype in _rom_refs_from_instruction(ref_mgr, rom, ins):
            rom_by_insn[ia].append((off, rtype))
    lui_targets = _lui_pair_rom_targets_in_range(
        listing, rom, rom_start, listing.getInstructions(fn.getBody(), True)
    )
    return rom_by_insn, lui_targets


def _gather_seed_addresses(prog, mem, ram, space):
    seeds = []
    if EXPLICIT_SEED_ADDRESSES:
        for v in EXPLICIT_SEED_ADDRESSES:
            try:
                a = space.getAddress(int(v))
                if ram.contains(a):
                    seeds.append((a, "explicit_0x%X" % int(v)))
            except Exception:
                pass
        return seeds

    per_pat = max(1, MAX_SEED_LOCATIONS // max(1, len(DEFAULT_BYTE_PATTERNS)))
    for pat, label in DEFAULT_BYTE_PATTERNS:
        for a in _find_bytes_first_n(mem, ram, pat, per_pat):
            seeds.append((a, label))
    merged = {}
    for a, lab in seeds:
        k = int(a.getOffset())
        if k not in merged:
            merged[k] = lab
        elif lab not in merged[k]:
            merged[k] = merged[k] + "|" + lab
    deduped = []
    for off in sorted(merged.keys()):
        deduped.append((space.getAddress(off), merged[off]))
    return deduped


def main():
    prog = currentProgram  # noqa: F821
    mem = prog.getMemory()
    listing = prog.getListing()
    ref_mgr = prog.getReferenceManager()
    fm = prog.getFunctionManager()

    rom = get_block_exact(mem, ".rom")
    ram = get_block_exact(mem, ".ram")
    if rom is None or ram is None:
        print("ERROR: need MemoryBlocks `.rom` and `.ram`.")
        return

    rom_start = rom.getStart()
    space = ram.getStart().getAddressSpace()

    print("=== RSP_Scheduler_String_Xref_Trace (AeroAssault64) ===")
    print("Program: %s" % prog.getName())
    if EXPLICIT_SEED_ADDRESSES:
        print("Seeds: EXPLICIT_SEED_ADDRESSES (%d)" % len(EXPLICIT_SEED_ADDRESSES))
    else:
        print(
            "Seeds: DEFAULT_BYTE_PATTERNS (max ~%d total hits across patterns)"
            % MAX_SEED_LOCATIONS
        )
    print(
        "Chain: incoming xrefs up to %d data-pointer hops -> functions; "
        "then .rom operand refs + lui+lo pairs inside each function." % MAX_DATA_CHAIN_HOPS
    )
    if CALLEE_DEPTH > 0:
        print(
            "Callees: depth=%d (direct `jal` only), max %d per function."
            % (CALLEE_DEPTH, MAX_CALLEES_PER_FUNC)
        )
    print("")

    seeds = _gather_seed_addresses(prog, mem, ram, space)
    if not seeds:
        print("No seed addresses — set EXPLICIT_SEED_ADDRESSES or widen patterns.")
        return

    global_rom_hits = defaultdict(int)

    for seed_addr, seed_label in seeds:
        print("--- Seed %s @ %s ---" % (seed_label, seed_addr))
        rows = _functions_and_sites_for_seed(
            ref_mgr, listing, fm, seed_addr, MAX_DATA_CHAIN_HOPS
        )
        if not rows:
            print("  (no incoming xrefs into this address — try xref window manually in Ghidra)")
            print("")
            continue

        uniq_fn = []
        seen_e = set()
        example_site = {}
        for fn, fa, hop in rows:
            e = int(fn.getEntryPoint().getOffset())
            if e in seen_e:
                continue
            seen_e.add(e)
            uniq_fn.append(fn)
            example_site[e] = (fa, hop)
        uniq_fn = uniq_fn[:MAX_FUNCTIONS_PER_SEED]

        for fn in uniq_fn:
            rom_by_insn, lui_targets = _analyze_function(
                prog, listing, ref_mgr, fm, rom, rom_start, fn
            )
            entry = fn.getEntryPoint()
            name = fn.getName()
            es = example_site.get(int(entry.getOffset()))
            if es:
                print(
                    "  Function %s @ %s  (example xref site %s  hop=%d)"
                    % (name, entry, es[0], es[1])
                )
            else:
                print("  Function %s @ %s" % (name, entry))

            n_insn = 0
            for ia in sorted(rom_by_insn.keys(), key=lambda x: int(x.getOffset())):
                for off, rtype in rom_by_insn[ia][:4]:
                    print(
                        "    insn %s  ->  ROM file offset 0x%X  (%s)"
                        % (ia, off, rtype)
                    )
                    global_rom_hits[off] += 1
                    n_insn += 1
                    if n_insn >= MAX_ROM_REFS_PRINT_PER_FUNC:
                        break
                if n_insn >= MAX_ROM_REFS_PRINT_PER_FUNC:
                    break
            if n_insn == 0:
                print("    (no direct instruction->.rom references in this function)")

            lt = lui_targets[:MAX_LUI_ROM_TARGETS_PER_FUNC]
            if lt:
                print("    lui+addiu/ori -> .rom:")
                for ia, off in lt:
                    print("      @ %s  ->  ROM file offset 0x%X" % (ia, off))
                    global_rom_hits[off] += 1

            if CALLEE_DEPTH > 0:
                for call_tgt in _collect_callees(ref_mgr, listing, fn, MAX_CALLEES_PER_FUNC):
                    cfn = fm.getFunctionAt(call_tgt)
                    if cfn is None:
                        continue
                    cr, cl = _analyze_function(
                        prog, listing, ref_mgr, fm, rom, rom_start, cfn
                    )
                    if not cr and not cl:
                        continue
                    print("    callee %s @ %s" % (cfn.getName(), cfn.getEntryPoint()))
                    n2 = 0
                    for ia in sorted(cr.keys(), key=lambda x: int(x.getOffset())):
                        for off, rtype in cr[ia][:3]:
                            print(
                                "      insn %s  ->  0x%X  (%s)"
                                % (ia, off, rtype)
                            )
                            global_rom_hits[off] += 1
                            n2 += 1
                            if n2 >= 12:
                                break
                        if n2 >= 12:
                            break
                    for ia, off in cl[:8]:
                        print("      lui+lo @ %s  ->  0x%X" % (ia, off))
                        global_rom_hits[off] += 1

        print("")

    if global_rom_hits:
        print("--- Merged ROM file offsets (vote count across printed functions) ---")
        print("  Higher counts may be jump tables / shared rodata — still worth opening in .rom.")
        for off, cnt in sorted(global_rom_hits.items(), key=lambda t: (-t[1], t[0]))[:35]:
            print("  0x%06X  hits=%d" % (off, cnt))
    print("")
    print("Next: open top offsets in `.rom`, confirm RSP microcode / DMA; cross-check")
    print("      `Find_RSP_Microcode_ROM_Hints.py` histogram + AFA_PORT.md section 1.")


main()
