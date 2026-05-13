Ghidra helper scripts for AeroAssault64 Phase 2 (ROM / RAM alignment).

Install
-------
1. Ghidra: **Window → Script Manager**.
2. **Script Directories** (manager toolbar): **Add** this folder
   `.../AeroAssault64/tools/ghidra` (or copy `.py` files into your user
   `ghidra_scripts` directory).
3. Select **Phase2_Closeout_Report.py** → **Run**.

Requires the Aero Fighters Assault USA ROM project to be **open** with the
same memory blocks you have been using (e.g. `.rom`, `.ram`, `.boot`).

Docs
----
See `Docs/Workflow.md` → Phase 2 checklist and findings log for what to paste
from the script output.
