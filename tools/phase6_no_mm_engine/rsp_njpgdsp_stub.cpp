// RSP recomp stub — replace with RSPRecomp output for AFA when ready.
// Must match `RspUcodeFunc` in lib/Zelda64Recomp/lib/N64ModernRuntime/librecomp/include/librecomp/rsp.hpp
// (same declaration site as `extern RspUcodeFunc njpgdspMain` in src/main/main.cpp).
#include "librecomp/rsp.hpp"

RspExitReason njpgdspMain(uint8_t* rdram, uint32_t ucode_addr) {
    (void)rdram;
    (void)ucode_addr;
    return RspExitReason::Unsupported;
}
