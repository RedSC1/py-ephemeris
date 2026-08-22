cmake_minimum_required(VERSION 3.18)

project(py_ephemeris LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Bind the C++ API directly. Local development prefers the adjacent checkout;
# isolated source builds fetch the exact public core revision used by this release.
set(TAIYIN_CORE_REVISION "v1.0.0-beta.1")
set(
    TAIYIN_CORE_ARCHIVE_URL
    "https://github.com/RedSC1/taiyin-ephemeris/archive/${TAIYIN_CORE_REVISION}.tar.gz"
)
set(
    TAIYIN_CORE_ARCHIVE_SHA256
    "6cffdcee9b4ac7f2efd341f75037fba2f4756452068a119965970585ca68a4e2"
)
set(
    TAIYIN_SOURCE_DIR
    ""
    CACHE PATH
    "Optional path to a Taiyin Ephemeris C++ source checkout"
)
set(_TAIYIN_ADJACENT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../taiyin-ephemeris")
if(NOT TAIYIN_SOURCE_DIR AND EXISTS "${_TAIYIN_ADJACENT_SOURCE_DIR}/CMakeLists.txt")
    set(TAIYIN_SOURCE_DIR "${_TAIYIN_ADJACENT_SOURCE_DIR}")
endif()

set(TAIYIN_BUILD_MODULAR_C_API OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_CHINESE_METAPHYSICS_EXTENSIONS ON CACHE BOOL "" FORCE)
# BaZi is compiled by the separately distributed py-ephemeris-bazi wheel.
set(TAIYIN_BUILD_BAZI_EXTENSION OFF CACHE BOOL "" FORCE)
# Ziwei is compiled by the separately distributed py-ephemeris-ziwei wheel.
set(TAIYIN_BUILD_ZIWEI_EXTENSION OFF CACHE BOOL "" FORCE)

if(TAIYIN_SOURCE_DIR)
    if(NOT EXISTS "${TAIYIN_SOURCE_DIR}/CMakeLists.txt")
        message(FATAL_ERROR
            "TAIYIN_SOURCE_DIR must point at a taiyin-ephemeris source checkout; "
            "got: ${TAIYIN_SOURCE_DIR}")
    endif()
    message(STATUS "Using Taiyin C++ source checkout: ${TAIYIN_SOURCE_DIR}")
    add_subdirectory(
        "${TAIYIN_SOURCE_DIR}"
        "${CMAKE_CURRENT_BINARY_DIR}/taiyin-ephemeris"
        EXCLUDE_FROM_ALL
    )
else()
    include(FetchContent)
    if(POLICY CMP0135)
        cmake_policy(SET CMP0135 NEW)
    endif()
    message(STATUS "Fetching Taiyin C++ revision ${TAIYIN_CORE_REVISION}")
    FetchContent_Declare(
        taiyin_ephemeris_core
        URL "${TAIYIN_CORE_ARCHIVE_URL}"
        URL_HASH "SHA256=${TAIYIN_CORE_ARCHIVE_SHA256}"
    )
    FetchContent_GetProperties(taiyin_ephemeris_core)
    if(NOT taiyin_ephemeris_core_POPULATED)
        FetchContent_Populate(taiyin_ephemeris_core)
    endif()
    add_subdirectory(
        "${taiyin_ephemeris_core_SOURCE_DIR}"
        "${taiyin_ephemeris_core_BINARY_DIR}"
        EXCLUDE_FROM_ALL
    )
endif()

pybind11_add_module(_native MODULE src/native/module.cpp)
target_compile_features(_native PRIVATE cxx_std_11)
set(_TAIYIN_NATIVE_OUTPUT_DIRECTORY
    "${CMAKE_CURRENT_BINARY_DIR}/native-modules/taiyin")
set_target_properties(_native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${_TAIYIN_NATIVE_OUTPUT_DIRECTORY}"
    RUNTIME_OUTPUT_DIRECTORY "${_TAIYIN_NATIVE_OUTPUT_DIRECTORY}"
    ARCHIVE_OUTPUT_DIRECTORY "${_TAIYIN_NATIVE_OUTPUT_DIRECTORY}"
)
target_include_directories(
    _native PRIVATE packages/taiyin-bazi/src/native
)
target_link_libraries(
    _native
    PRIVATE
        taiyin_astrology_extension
        taiyin_chinese_calendar_ganzhi_extension
)

install(TARGETS _native DESTINATION taiyin)
# Keep the default runtime data beside the extension in the wheel.  Python
# locates this package directory at runtime instead of asking end users for a
# DLL or data path.
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/taiyin/data" DESTINATION taiyin)
