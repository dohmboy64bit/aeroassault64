AFA runtime assets (RmlUi / launcher / RT64)

Upstream expects the game EXE to be run from the Zelda64Recomp project root or to have the
assets/ tree available (lib/Zelda64Recomp/BUILDING.md section 6).

For AFA:
  - Fork launcher.rml and related textures under lib/Zelda64Recomp/assets/ (or your asset pack layout).
  - Keep paths consistent with zelda64::get_asset_path(...) usage in src/ui/*.cpp.

The stock MM assets are not duplicated in this AeroAssault64 repo; clone/build the engine and diff
against upstream assets/ when forking UI strings and branding.

See lib/Zelda64Recomp/AFA_PORT.md.
