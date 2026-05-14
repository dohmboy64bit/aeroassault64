# AeroAssault64 — repo-root CMake entry for Phase 6 (engine superbuild).
#
# Upstream lib/Zelda64Recomp/CMakeLists.txt uses ${CMAKE_SOURCE_DIR} for lib/rt64,
# RecompiledFuncs/, patches/, etc. add_subdirectory() from this repo would break those paths.
# ExternalProject runs CMake with SOURCE_DIR = lib/Zelda64Recomp, preserving CMAKE_SOURCE_DIR.
#
# Prereqs: git submodule update --init --recursive; tools/phase6_setup_windows.ps1 (or junction +
# copy PEs); full MM build still needs lib/Zelda64Recomp/BUILDING.md (ROM, RSP, patches pipeline).
# Optional: -DAEROASSAULT64_NO_MM_ROM=ON skips MM patches/RSP file generation — see lib/README.txt "No Majora's Mask ROM".
cmake_minimum_required(VERSION 3.20)
project(AeroAssault64_engine_superbuild LANGUAGES C)

if(NOT EXISTS "${CMAKE_SOURCE_DIR}/lib/Zelda64Recomp/CMakeLists.txt")
  message(FATAL_ERROR
    "Missing lib/Zelda64Recomp (Zelda64Recomp submodule). From repo root run:\n"
    "  git submodule update --init --recursive\n"
    "See lib/README.txt and Docs/Workflow.md § Phase 6.")
endif()

# CMake requires at least one target for some generators; this file is not linked to the engine.
set(_AERO_DUMMY "${CMAKE_CURRENT_BINARY_DIR}/_aero_superbuild_dummy.c")
file(WRITE "${_AERO_DUMMY}" "/* Empty translation unit — superbuild metadata only. */\n")
add_library(_aero_superbuild_placeholder STATIC "${_AERO_DUMMY}")

include(ExternalProject)

set(_AFA_ENGINE_SRC "${CMAKE_SOURCE_DIR}/lib/Zelda64Recomp")
set(_AFA_ENGINE_BIN "${CMAKE_SOURCE_DIR}/build-engine")

option(AEROASSAULT64_NO_MM_ROM "Forward to engine: stub PatchesLib/RSP, skip MM patches pipeline (see tools/phase6_no_mm_engine)" OFF)

set(AEROASSAULT64_AFA_ROM_XXH3_HEX "" CACHE STRING "Forwarded to engine: 16 hex digit XXH3 for AFA USA GameEntry (optional).")
set(AEROASSAULT64_EXE_OUTPUT_NAME "" CACHE STRING "Forwarded to engine: OUTPUT_NAME for game exe (optional).")
set(AEROASSAULT64_VERSION_TAG "" CACHE STRING "Forwarded to engine: version tag (optional).")
set(AEROASSAULT64_WINDOW_TITLE "" CACHE STRING "Forwarded to engine: SDL window title (optional).")

set(_EP_CMAKE_ARGS "")
if(CMAKE_BUILD_TYPE)
  list(APPEND _EP_CMAKE_ARGS "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()
if(AEROASSAULT64_NO_MM_ROM)
  list(APPEND _EP_CMAKE_ARGS "-DAEROASSAULT64_NO_MM_ROM=ON")
endif()
if(NOT "${AEROASSAULT64_AFA_ROM_XXH3_HEX}" STREQUAL "")
  list(APPEND _EP_CMAKE_ARGS "-DAEROASSAULT64_AFA_ROM_XXH3_HEX=${AEROASSAULT64_AFA_ROM_XXH3_HEX}")
endif()
if(NOT "${AEROASSAULT64_EXE_OUTPUT_NAME}" STREQUAL "")
  list(APPEND _EP_CMAKE_ARGS "-DAEROASSAULT64_EXE_OUTPUT_NAME=${AEROASSAULT64_EXE_OUTPUT_NAME}")
endif()
if(NOT "${AEROASSAULT64_VERSION_TAG}" STREQUAL "")
  list(APPEND _EP_CMAKE_ARGS "-DAEROASSAULT64_VERSION_TAG=${AEROASSAULT64_VERSION_TAG}")
endif()
if(NOT "${AEROASSAULT64_WINDOW_TITLE}" STREQUAL "")
  list(APPEND _EP_CMAKE_ARGS "-DAEROASSAULT64_WINDOW_TITLE=${AEROASSAULT64_WINDOW_TITLE}")
endif()

ExternalProject_Add(
  zelda64recomp_engine
  SOURCE_DIR "${_AFA_ENGINE_SRC}"
  BINARY_DIR "${_AFA_ENGINE_BIN}"
  CMAKE_ARGS ${_EP_CMAKE_ARGS}
  INSTALL_COMMAND ""
)

add_custom_target(aero_phase6_engine_default ALL DEPENDS zelda64recomp_engine)
