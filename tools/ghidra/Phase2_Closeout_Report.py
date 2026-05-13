# -*- coding: utf-8 -*-
# Ghidra script: ROM/RAM checks to finish Phase 2 (AeroAssault64).
# Run from Script Manager with the AFA USA program open.
#
#@category AeroAssault64
#@name Phase2_Closeout_Report
#@description Report ROM header, key offsets, and memory blocks for Docs/Workflow.md
#@author AeroAssault64

from __future__ import print_function

# Expected from repo / splat (sanity targets)
EXP_SHA1 = "6742f67d7d2639072e186d240237be1c662cb25a"
EXP_LOAD = 0x80200050
EXP_ENTRY_VRAM = 0x80200050
EXP_MAIN_VRAM = 0x80231150
EXP_BSS_VRAM = 0x80256D70
EXP_GSTR_VRAM = 0x802F5E58
ROM_OFF_DATA = 0x4C050
ROM_OFF_TAIL = 0x57D20


def _u8(mem, addr):
    return mem.getByte(addr) & 0xFF


def read_be32(mem, addr):
    return (
        (_u8(mem, addr) << 24)
        | (_u8(mem, addr.add(1)) << 16)
        | (_u8(mem, addr.add(2)) << 8)
        | _u8(mem, addr.add(3))
    )


def read_ascii(mem, addr, length):
    out = []
    for i in range(length):
        b = _u8(mem, addr.add(i))
        if 32 <= b <= 126:
            out.append(chr(b))
        else:
            out.append(".")
    return "".join(out)


def find_block(mem, *candidates):
    """Return first MemoryBlock whose name matches one of candidates (case-insensitive contains)."""
    c = [x.lower() for x in candidates]
    for b in mem.getBlocks():
        n = b.getName().lower()
        for want in c:
            if want in n or n == want.strip("*"):
                return b
    return None


def find_block_by_prefix(mem, prefix):
    for b in mem.getBlocks():
        if b.getName().startswith(prefix):
            return b
    return None


def addr_in_block(block, rom_off):
    """Address within block for file offset rom_off, if block starts at ROM image offset 0."""
    if block is None:
        return None
    base = block.getStart()
    # If block min address offset from "file 0" is not 0, caller must adjust — we only handle common case.
    return base.add(rom_off)


def mips_hint_be32(w):
    """Human-readable hint for common big-endian MIPS words (not full disasm)."""
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    if imm & 0x8000:
        simm = imm - 0x10000
    else:
        simm = imm
    # addiu opcode 0x09 (I-type): actually bits 31-26 = 001001 = 9
    if op == 9 and rs == 29 and rt == 29:
        return "addiu sp, sp, %d  (stack frame?)" % simm
    if op == 0x2B:  # sw
        return "sw r%d, %d(r%d)" % (rt, simm, rs)
    if op == 0:  # R-type
        return "R-type special 0x%08x" % w
    return "opcode=%d rs=%d rt=%d imm=%d  (0x%08x)" % (op, rs, rt, simm, w)


def make_addr(prog, offset):
    """Resolve a physical offset in the program's default memory space (typical for ram:8020... imports)."""
    space = prog.getAddressFactory().getDefaultAddressSpace()
    return space.getAddress(offset)


def main():
    prog = currentProgram  # noqa: F821 — Ghidra injects this
    mem = prog.getMemory()
    listing = prog.getListing()

    print("=== AeroAssault64 Phase 2 — Ghidra closeout report ===")
    print("Program: %s" % prog.getName())
    print("Executable path: %s" % prog.getExecutablePath())

    print("\n--- Memory blocks (name, start, end, execute, write) ---")
    for b in mem.getBlocks():
        print(
            "  %-20s  %s  %s  x=%s w=%s"
            % (b.getName(), b.getStart(), b.getEnd(), b.isExecute(), b.isWrite())
        )

    rom = find_block(mem, ".rom", "rom")
    ram = find_block(mem, ".ram", "ram")
    boot = find_block(mem, ".boot", "boot", "ipl")

    print("\n--- Resolved blocks ---")
    print("  .rom-like: %s" % (rom.getName() if rom else "(none)"))
    print("  .ram-like: %s" % (ram.getName() if ram else "(none)"))
    print("  .boot-like: %s" % (boot.getName() if boot else "(none)"))

    if rom is None:
        print("\nERROR: No ROM block found (tried names containing .rom / rom).")
        print("Rename or extend this script to match your memory block names.")
        return

    rom_base = rom.getStart()
    print("\n--- ROM header (big-endian dwords at file offset 0x0) ---")
    magic = read_be32(mem, rom_base)
    clock = read_be32(mem, rom_base.add(4))
    load_addr = read_be32(mem, rom_base.add(8))
    release = read_be32(mem, rom_base.add(0x0C))
    crc1 = read_be32(mem, rom_base.add(0x10))
    crc2 = read_be32(mem, rom_base.add(0x14))
    print("  Magic:          0x%08X  (expect 0x80371240 for .z64)" % magic)
    print("  Clock rate:     0x%08X" % clock)
    print("  Load_Address:   0x%08X  (repo expect 0x%08X)" % (load_addr, EXP_LOAD))
    print("  Release_Offset: 0x%08X  (reconcile with ROM docs / splat entry ROM 0x1000)" % release)
    print("  CRC1 / CRC2:    0x%08X / 0x%08X" % (crc1, crc2))
    title = read_ascii(mem, rom_base.add(0x20), 20)
    print('  Title@0x20:     "%s"' % title)

    if load_addr != EXP_LOAD:
        print("  WARNING: Load_Address does not match expected entry VRAM.")

    print("\n--- ROM offset 0x%x (splat first `data` subsegment) ---" % ROM_OFF_DATA)
    a = addr_in_block(rom, ROM_OFF_DATA)
    if a is not None:
        w0 = read_be32(mem, a)
        print("  First word: 0x%08X  %s" % (w0, mips_hint_be32(w0)))
        ins = listing.getInstructionAt(a)
        print("  Ghidra code unit at start: %s" % (ins if ins else "(undefined — not disassembled as code)"))

    print("\n--- ROM offset 0x%x (splat tail `bin`; should verify MIPS vs padding) ---" % ROM_OFF_TAIL)
    a = addr_in_block(rom, ROM_OFF_TAIL)
    if a is not None:
        for i in range(4):
            addr = a.add(i * 4)
            w = read_be32(mem, addr)
            off = ROM_OFF_TAIL + i * 4
            print("  ROM+0x%X  BE32=0x%08X  %s" % (off, w, mips_hint_be32(w)))
        ins = listing.getInstructionAt(a)
        print("  Ghidra code unit at ROM+0x%X: %s" % (ROM_OFF_TAIL, ins if ins else "(undefined)"))

    print("\n--- RAM symbols (fixed VRAM offsets in default memory space) ---")

    def check_ram_vram(offset, label_hint):
        addr = make_addr(prog, offset)
        if addr is None or not mem.contains(addr):
            print("  %s @ 0x%X: address not in memory" % (label_hint, offset))
            return
        fn = listing.getFunctionContaining(addr)
        data = listing.getDataAt(addr)
        ins = listing.getInstructionAt(addr)
        print("  %s @ %s" % (label_hint, addr))
        if fn:
            print("    Function: %s  entry=%s" % (fn.getName(), fn.getEntryPoint()))
        if data:
            print("    Data: %s" % data)
        if ins:
            print("    Instruction: %s" % ins)
        if not fn and not data and not ins:
            print("    (no function/data/instruction — try Go To this offset in your .ram block)")

    check_ram_vram(EXP_ENTRY_VRAM, "Entry / ramMain")
    check_ram_vram(EXP_MAIN_VRAM, "main")
    check_ram_vram(EXP_BSS_VRAM, "BSS base")
    check_ram_vram(EXP_GSTR_VRAM, "g_BuildString")

    print("\n--- Paste targets for Docs/Workflow.md ---")
    print("  ROM Load_Address: 0x%08X" % load_addr)
    print("  Release_Offset:   0x%08X  (note meaning after checking ROM wiki)")
    tail_addr = addr_in_block(rom, ROM_OFF_TAIL)
    if tail_addr is not None:
        tw = read_be32(mem, tail_addr)
        print(
            "  ROM+0x%X first word: 0x%08X — %s"
            % (ROM_OFF_TAIL, tw, mips_hint_be32(tw))
        )

    print("\nDone. SHA1 is not computed here — use host: `Get-FileHash -Algorithm SHA1 roms\\afa.n64.us.z64` (expect %s)." % EXP_SHA1)


main()
