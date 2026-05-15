# -*- coding: utf-8 -*-
# Ghidra (PyGhidra): **one Script Manager run** that executes the Phase-6 RSPRecomp discovery
# scripts from **`Docs/Workflow.md`** / **`lib/Zelda64Recomp/AFA_PORT.md`** §1 in a fixed order.
#
# This file does **not** replace per-script tunables: each partner `.py` still owns **`BASE_VRAM`**,
# **`HELPER_ENTRY_VRAM`**, **`TARGET_FUNCTION_ENTRY_VRAM`**, etc. Keep them aligned when you
# change addresses (AFA USA examples are already the defaults in those files).
#
# Output is still **heuristic** — confirm **`text_offset` / `text_size` / `text_address`** in Listing
# (DMA, **`OSTask`**, IMEM setup) before writing **`config/afa_rsp/*.template.toml`**.
# When **`RUN_CONFIRM_FINDINGS`** is True, partner **`RSPRecomp_Confirm_Findings.py`** can print
# **Capstone** MIPS32 BE lines at **`.rom`** hits if **`pip install capstone`** is applied to the PyGhidra env (**`requirements.txt`**).
#
# Hardware / layout: N64brew memory map (SP **`0x04000000`–`0x04001FFF`**); ROM pointers via
# **`.rom`** block same as **`Phase2_Closeout_Report.py`**.
#
#@runtime PyGhidra
#@category AeroAssault64
#@name RSPRecomp_AFA_AllInOne
#@description Run ROM-hint + IMEM + jal + RAM-field Ghidra scripts in one pass (RSPRecomp hunt)
#@author AeroAssault64

from __future__ import print_function

import os
import time
import traceback

# --- Bundle tunables ----------------------------------------------------------
# If True, stop the bundle on the first uncaught exception from a partner script.
STOP_ON_ERROR = False

# **`RSP_Scheduler_String_Xref_Trace.py`** can be long on large binaries — disable for a faster pass.
RUN_SCHEDULER_STRING_XREF_TRACE = True

# **`RSP_RAM_Constant_Base_Memops.py`** overlaps **`RSP_RAM_Context_Field_Xrefs.py`** when the latter
# has **`RUN_CONSTANT_BASE_MEMOPS`** True (default). Set True only if you want a second memop dump
# with **`MEMOP_RUN`** tunables from Memops only.
RUN_STANDALONE_MEMOPS_DUPLICATE = False

# If True, run **`RSPRecomp_Confirm_Findings.py`** last — set tunables there from your P64 snapshot first.
RUN_CONFIRM_FINDINGS = False

# -----------------------------------------------------------------------------


def _bundle_script_dir():
    """Directory containing this repo’s **`tools/ghidra/*.py`** partners."""
    try:
        import inspect

        fr = inspect.currentframe()
        if fr is not None:
            p = inspect.getfile(fr.f_back or fr)
            return os.path.dirname(os.path.abspath(p))
    except Exception:
        pass
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def _partner_path(script_dir, basename):
    return os.path.normpath(os.path.join(script_dir, basename))


def _run_partner_py(path, prog):
    """Execute a partner script in an isolated namespace (fresh **`main`** each time)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        src = raw.decode("utf-8")
    except Exception:
        src = raw.decode("latin-1")
    g = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        "__file__": path,
        "currentProgram": prog,
    }
    code = compile(src, path, "exec")
    exec(code, g, g)


def main():
    prog = currentProgram  # noqa: F821
    if prog is None:
        print("ERROR: no currentProgram (open a program in Ghidra / PyGhidra first).")
        return

    script_dir = _bundle_script_dir()
    steps = [
        ("ROM offset histogram + lui/addiu .rom pointers", "Find_RSP_Microcode_ROM_Hints.py"),
        ("LibUltra / IMEM immediates / ASCII / uv* rodata scan", "RSP_LibUltra_And_IMEM_Scan.py"),
    ]
    if RUN_SCHEDULER_STRING_XREF_TRACE:
        steps.append(
            ("Scheduler rodata xref → functions → .rom refs", "RSP_Scheduler_String_Xref_Trace.py")
        )
    steps.extend(
        [
            ("`jal` callee list from driver function", "RSP_List_Jal_Callees_From_Function.py"),
            ("Disassembly before each `jal` from driver", "RSP_Jal_Call_Sites_Disasm_From_Caller.py"),
            ("Heuristic a0–a3 / lw-base slice at `jal` to helpers", "RSP_Jal_Arg_Register_Slice.py"),
            ("`v0`/`v1` last-def before each `jr ra` in callee", "RSP_Function_Return_Reg_Slice.py"),
            ("IMEM immediates + optional helper `jal` windows", "RSP_IMEM_Load_And_Helper_Call_Trace.py"),
            (
                "RAM field xrefs + BE words + constant-base lw/sw + store-xref",
                "RSP_RAM_Context_Field_Xrefs.py",
            ),
        ]
    )
    if RUN_STANDALONE_MEMOPS_DUPLICATE:
        steps.append(("Standalone constant-base lw/sw (MEMOP_RUN tunables)", "RSP_RAM_Constant_Base_Memops.py"))
    if RUN_CONFIRM_FINDINGS:
        steps.append(("Confirm P64 seeds vs .ram/.rom (tunables in partner file)", "RSPRecomp_Confirm_Findings.py"))

    print("=" * 72)
    print("RSPRecomp_AFA_AllInOne (AeroAssault64)")
    print("Program: %s" % prog.getName())
    print("Script dir: %s" % script_dir)
    print("Partners: %d step(s)" % len(steps))
    print("Docs: lib/Zelda64Recomp/AFA_PORT.md section 1; Docs/Workflow.md Phase 6")
    print("=" * 72)
    print("")
    print("Checklist — keep these consistent across the partner scripts you edit:")
    print("  • RSP_List_Jal_Callees / RSP_Jal_Call_Sites / RSP_Jal_Arg_Register_Slice: same driver")
    print("    SOURCE_FUNCTION_ENTRY_VRAM (e.g. 0x8023D92C).")
    print("  • RSP_Jal_Arg_Register_Slice TARGET_CALLEE_ENTRIES ↔ RSP_IMEM_Load HELPER_ENTRY_VRAM.")
    print("  • RSP_Function_Return_Reg_Slice TARGET_FUNCTION_ENTRY_VRAM ↔ jal callee feeding ctx ptr.")
    print("  • RSP_RAM_Context_Field_Xrefs BASE_VRAM / FIELD_OFFSETS ↔ JAL_KNOWN_V0_BY_CALLEE_ENTRY")
    print("    and RSP_RAM_Constant_Base_Memops (if you run it).")
    print("")

    t0 = time.time()
    failed = []
    for i, (title, fname) in enumerate(steps, 1):
        path = _partner_path(script_dir, fname)
        if not os.path.isfile(path):
            msg = "MISSING: %s" % path
            print("[%d/%d] %s" % (i, len(steps), msg))
            failed.append((fname, msg))
            if STOP_ON_ERROR:
                break
            continue
        print("")
        print("-" * 72)
        print("[%d/%d] %s" % (i, len(steps), title))
        print("    file: %s" % fname)
        print("-" * 72)
        t_step = time.time()
        try:
            _run_partner_py(path, prog)
        except Exception:
            print("ERROR in %s:" % fname)
            traceback.print_exc()
            failed.append((fname, "exception"))
            if STOP_ON_ERROR:
                break
        else:
            print("")
            print("    (step finished in %.2f s)" % (time.time() - t_step))

    dt = time.time() - t0
    print("")
    print("=" * 72)
    print("RSPRecomp_AFA_AllInOne finished in %.2f s" % dt)
    if failed:
        print("Steps with problems: %s" % ", ".join(a for a, _ in failed))
    else:
        print("All partner steps completed without fatal bundle abort.")
    print("")
    print("Next: pick **`text_offset` / `text_size`** from ROM hints + IMEM/DMA Listing proof;")
    print("      fill **`config/afa_rsp/*.template.toml`** then **`RSPRecomp`** (see AFA_PORT.md §1).")
    print("")
    print("Optional: set **`RUN_CONFIRM_FINDINGS = True`** above to run **`RSPRecomp_Confirm_Findings.py`**")
    print("  last (tune **`IMEM_BOOTSTRAP_*`**, **`EXPECTED_*`**, **`EXPECTED_NJPG_*`**, **`HEX_DUMP_*`**, **`CAPSTONE_*`** in that file).")
    print("  PyGhidra needs **`pip install capstone`** for optional MIPS lines (see **`requirements.txt`**).")
    print("=" * 72)


main()
