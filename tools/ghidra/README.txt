Ghidra helper scripts for AeroAssault64 Phase 2 (ROM / RAM) and Phase 3 (`splat.yaml` evidence).

**Phase 3:** run **`Phase3_Closeout_Report.py`** after Phase 2 when closing **`config/splat.yaml`** / rodata / tail / BSS. Output is for **`Docs/Workflow.md`** (boundary xrefs, tail listing mix, BSS VRAM, linker dup candidates). Keep **`RODATA_ROM_SPLITS`** in that script aligned with **`config/splat.yaml`** whenever rodata subsegments change — from repo root run **`python3 tools/verify_rodata_splits_sync.py`** (or **`make verify-rodata-sync`**) before trusting Ghidra boundary tables.

**Phase 3 (listing fix):** run **`Phase3_Ensure_PostData_Function.py`** when section **F** shows **`DAT_80256d70`** / no instruction at **`0x80256D70`** but ROM tail is MIPS (section **D**). It clears the splat **`post_data`** tail span in **`.ram`**, disassembles, and runs **`CreateFunctionCmd`** at that entry (see Ghidra API docs linked in the script). Edit **`DRY_RUN`** / **`FORCE`** / **`EXPECTED_ENTRY_BE32`** at the top if needed; sync **`ROM_OFF_TAIL`**, **`ROM_END`**, **`EXP_TAIL_ENTRY_VRAM`**, **`EXP_BSS_VRAM`** with **`config/splat.yaml`** / **`Phase3_Closeout_Report.py`** after layout changes.

Ghidra 12.0.4 — Python / PyGhidra (read this first)
---------------------------------------------------
Ghidra 12 uses **PyGhidra** (CPython 3) for `.py` scripts in the GUI. If Script Manager says
something like **“Ghidra was not started with PyGhidra”**, you launched with the **wrong
starter**.

**Do this (official “PyGhidra Mode” — NSA Ghidra GettingStarted.md):**

1. Close Ghidra if it is open.
2. Open a folder to your Ghidra install, then **`support`**.
3. Run **`pyghidraRun.bat`** (Windows) — **not** `ghidraRun.bat`.
4. If prompted, let it install the **`pyghidra`** wheel from Ghidra’s bundled `pypkg/dist`, or run:
   `python3 -m pip install --no-index -f "<GhidraInstallDir>/Ghidra/Features/PyGhidra/pypkg/dist" pyghidra`
5. After Ghidra opens, **Window → Script Manager** → add this repo folder under script paths →
   run **Phase2_Closeout_Report.py**, then **Phase3_Closeout_Report.py**. Output appears in the **Script** console.

**If you copied the script to `~/ghidra_scripts/NewScript3.py`:** replace it from
`AeroAssault64/tools/ghidra/Phase2_Closeout_Report.py` and `Phase3_Closeout_Report.py` after updates — old copies will miss fixes.

**Optional:** If Script Manager still offers **Jython** and you prefer the classic launcher,
edit the script’s first runtime line to **`# @runtime Jython`** (see comment in the `.py` file)
and start Ghidra with **`ghidraRun.bat`** instead. Use only one `@runtime` line.

Install script path
-------------------
**Script Manager** → toolbar **“Script Directories”** (folder icon) → **Add** this directory:

`.../AeroAssault64/tools/ghidra`

Docs
----
See `Docs/Workflow.md` → Phase 2 / Phase 3 for what to paste from the reports.
