# Debugging

## Windows PE (target)

- Build the CMake-generated **Windows** configuration you use day to day (Debug or RelWithDebInfo as appropriate).
- Open the built `.exe` in **Visual Studio** and set the startup project if the solution has multiple targets.
- Prefer **break on first chance** only when chasing heap/init bugs; otherwise keep exceptions quiet to reduce noise.

## N64 / recomp context

- Use **Ghidra** for ROM truth; coordinate with the project owner before large automated Ghidra changes (`Docs/SystemPrompt.md`).
- Use **Capstone** (or similar) when you need instruction-accurate disassembly beyond what static asm listing gives you.

## Reference material

- [Hack64 Wiki — Nintendo 64 Hacking](https://hack64.net/wiki/doku.php?id=nintendo_64)
- [N64brew Wiki — Main page](https://n64brew.dev/wiki/Main_Page)

Add game-specific breakpoints, known crash sites, and RT64/N64Recomp logging notes here as the port comes online.
