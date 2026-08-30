cmake_minimum_required(VERSION 3.18)

project(py_ephemeris_bazi LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

set(TAIYIN_CORE_REVISION "v1.0.0-beta.5")
set(
    TAIYIN_CORE_ARCHIVE_URL
    "https://github.com/RedSC1/taiyin-ephemeris/archive/${TAIYIN_CORE_REVISION}.tar.gz"
)
set(
    TAIYIN_CORE_ARCHIVE_SHA256
    "e3c92cc388c13ca76eeaeae2773ec43b569353042ddf43a6c67607fa8769aa2b"
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
    set(_TAIYIN_CORE_SOURCE_DIR "${TAIYIN_SOURCE_DIR}")
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
    set(_TAIYIN_CORE_SOURCE_DIR "${taiyin_ephemeris_core_SOURCE_DIR}")
endif()

add_library(taiyin_bazi_python_rules STATIC
    "${_TAIYIN_CORE_SOURCE_DIR}/bazi_astrology/src/bazi.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/bazi_astrology/src/bazi_rules.cpp"
)
target_compile_features(taiyin_bazi_python_rules PRIVATE cxx_std_11)
target_include_directories(taiyin_bazi_python_rules
    PUBLIC
        "${_TAIYIN_CORE_SOURCE_DIR}/include"
        "${_TAIYIN_CORE_SOURCE_DIR}/bazi_astrology/include"
    PRIVATE
        "${_TAIYIN_CORE_SOURCE_DIR}/src"
        "${_TAIYIN_CORE_SOURCE_DIR}/bazi_astrology/internal"
)
set_target_properties(taiyin_bazi_python_rules PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES
)

pybind11_add_module(_bazi_native MODULE
    src/native/bazi_module.cpp
    src/native/core_api_shim.cpp
)
target_compile_features(_bazi_native PRIVATE cxx_std_11)
set(_TAIYIN_BAZI_NATIVE_OUTPUT_DIRECTORY
    "${CMAKE_CURRENT_BINARY_DIR}/native-modules/taiyin_bazi")
set_target_properties(_bazi_native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${_TAIYIN_BAZI_NATIVE_OUTPUT_DIRECTORY}"
    RUNTIME_OUTPUT_DIRECTORY "${_TAIYIN_BAZI_NATIVE_OUTPUT_DIRECTORY}"
    ARCHIVE_OUTPUT_DIRECTORY "${_TAIYIN_BAZI_NATIVE_OUTPUT_DIRECTORY}"
)
target_link_libraries(_bazi_native PRIVATE taiyin_bazi_python_rules)
install(TARGETS _bazi_native DESTINATION taiyin_bazi)
