cmake_minimum_required(VERSION 3.18)

project(py_ephemeris_bazi LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

set(TAIYIN_CORE_VERSION "1.0.0-preview.1")
set(
    TAIYIN_CORE_ARCHIVE_URL
    "https://github.com/RedSC1/taiyin-ephemeris/archive/refs/tags/v${TAIYIN_CORE_VERSION}.tar.gz"
)
set(
    TAIYIN_CORE_ARCHIVE_SHA256
    "9c7ddd525c87508bfdb7d6bdcd02ea2e9091e7376eafb4529f9f9bc144804b16"
)
set(
    TAIYIN_SOURCE_DIR
    ""
    CACHE PATH
    "Optional path to a taiyin-ephemeris C++ source checkout"
)
set(_TAIYIN_ADJACENT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../taiyin-ephemeris")
if(NOT TAIYIN_SOURCE_DIR AND EXISTS "${_TAIYIN_ADJACENT_SOURCE_DIR}/CMakeLists.txt")
    set(TAIYIN_SOURCE_DIR "${_TAIYIN_ADJACENT_SOURCE_DIR}")
endif()

set(TAIYIN_BUILD_MODULAR_C_API OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_CHINESE_METAPHYSICS_EXTENSIONS ON CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_BAZI_EXTENSION ON CACHE BOOL "" FORCE)

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
    message(STATUS "Fetching Taiyin C++ v${TAIYIN_CORE_VERSION}")
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

pybind11_add_module(_bazi_native MODULE src/native/bazi_module.cpp)
target_compile_features(_bazi_native PRIVATE cxx_std_11)
target_link_libraries(_bazi_native PRIVATE taiyin_bazi_extension)
install(TARGETS _bazi_native DESTINATION taiyin_bazi)
