/* Included by src/main/register_patches.cpp — stub overlay tables when not using MM N64Recomp patches.toml.
 * One section with num_funcs == 0: load_special_overlay() in lib/N64ModernRuntime/librecomp/src/overlays.cpp
 * loops zero times over FuncEntry, so funcs may be nullptr. */
#include "librecomp/sections.h"

static SectionTableEntry section_table[] = {
    { 0xFFFFFFFFu, 0u, 0u, nullptr, (size_t)0, nullptr, (size_t)0, (size_t)0 },
};

static const FunctionExport export_table[] = {
    { nullptr, 0 },
};

static const char* const event_names[] = {
    nullptr,
};

static const ManualPatchSymbol manual_patch_symbols[] = {
    { 0u, nullptr },
};
