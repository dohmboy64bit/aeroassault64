Ghidra helper scripts for AeroAssault64 Phase 2 (ROM / RAM alignment).

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
   run **Phase2_Closeout_Report.py**. Output appears in the **Script** console.

**If you copied the script to `~/ghidra_scripts/NewScript3.py`:** replace it from
`AeroAssault64/tools/ghidra/Phase2_Closeout_Report.py` after updates — old copies will miss fixes.

**Optional:** If Script Manager still offers **Jython** and you prefer the classic launcher,
edit the script’s first runtime line to **`# @runtime Jython`** (see comment in the `.py` file)
and start Ghidra with **`ghidraRun.bat`** instead. Use only one `@runtime` line.

Install script path
-------------------
**Script Manager** → toolbar **“Script Directories”** (folder icon) → **Add** this directory:

`.../AeroAssault64/tools/ghidra`

Docs
----
See `Docs/Workflow.md` → Phase 2 checklist and findings log for what to paste from the report.
