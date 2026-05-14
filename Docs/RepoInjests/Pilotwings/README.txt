Pilotwings 64 — reference for Paradigm-era layout (same studio era as Aero Fighters Assault per Docs/SystemPrompt.md).

This folder is a pointer, not a vendored tree. For a repomix-style ingest like Docs/RepoInjests/Zelda64/, generate one locally if you want a searchable snapshot.

Repos (public):
  https://github.com/gcsmith/Pilotwings64Decomp
  https://github.com/gcsmith/Pilotwings64Recomp

RSPRecomp shape example (Pilotwings USA cart — NOT AFA offsets): upstream Pilotwings64Recomp publishes aspMain.us.toml at
  https://raw.githubusercontent.com/gcsmith/Pilotwings64Recomp/main/aspMain.us.toml
At the time this README was added, that file contained (verify in browser or curl before trusting):
  text_offset = 0x48E10
  text_size = 0xE20
  text_address = 0x04001080
  rom_file_path = "baserom.us.z64"
  extra_indirect_branch_targets = [ ... ]

Ghidra workflow: import Pilotwings USA baserom with the same .rom / .ram block naming you use for AFA, then run the same AeroAssault64 PyGhidra scripts (Find_RSP_Microcode_ROM_Hints.py, RSP_LibUltra_And_IMEM_Scan.py, RSP_Scheduler_String_Xref_Trace.py). If PW still embeds libultra symbol names, the ASCII section may light up where AFA stayed dark; either way, compare how graphics init loads RSP text vs your AFA xrefs.
