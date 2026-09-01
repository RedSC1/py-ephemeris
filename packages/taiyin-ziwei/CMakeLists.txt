cmake_minimum_required(VERSION 3.18)

project(py_ephemeris_ziwei LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Keep this revision in lockstep with the base Python package.  During
# monorepo development the adjacent checkout is deliberately preferred; the
# release pin is updated only after the C++ Ziwei API is tagged.
set(TAIYIN_CORE_REVISION "v1.0.0-beta.8")
set(TAIYIN_CORE_ARCHIVE_URL
    "https://github.com/RedSC1/taiyin-ephemeris/archive/${TAIYIN_CORE_REVISION}.tar.gz")
set(TAIYIN_CORE_ARCHIVE_SHA256
    "ec5adb987536dbfbee6c3eeed3465555b58f1b6c69934191a1d4fda7a0495344")
set(TAIYIN_SOURCE_DIR "" CACHE PATH
    "Optional path to a taiyin-ephemeris C++ source checkout")
set(_TAIYIN_ADJACENT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../taiyin-ephemeris")
if(NOT TAIYIN_SOURCE_DIR AND EXISTS "${_TAIYIN_ADJACENT_SOURCE_DIR}/CMakeLists.txt")
    set(TAIYIN_SOURCE_DIR "${_TAIYIN_ADJACENT_SOURCE_DIR}")
endif()

set(TAIYIN_BUILD_MODULAR_C_API OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_CHINESE_METAPHYSICS_EXTENSIONS ON CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_BAZI_EXTENSION OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_ZIWEI_EXTENSION ON CACHE BOOL "" FORCE)

if(TAIYIN_SOURCE_DIR)
    if(NOT EXISTS "${TAIYIN_SOURCE_DIR}/CMakeLists.txt")
        message(FATAL_ERROR "TAIYIN_SOURCE_DIR must point at a Taiyin C++ checkout")
    endif()
    message(STATUS "Using Taiyin C++ source checkout: ${TAIYIN_SOURCE_DIR}")
    add_subdirectory("${TAIYIN_SOURCE_DIR}"
        "${CMAKE_CURRENT_BINARY_DIR}/taiyin-ephemeris" EXCLUDE_FROM_ALL)
    set(_TAIYIN_CORE_SOURCE_DIR "${TAIYIN_SOURCE_DIR}")
else()
    include(FetchContent)
    if(POLICY CMP0135)
        cmake_policy(SET CMP0135 NEW)
    endif()
    FetchContent_Declare(taiyin_ephemeris_core
        URL "${TAIYIN_CORE_ARCHIVE_URL}"
        URL_HASH "SHA256=${TAIYIN_CORE_ARCHIVE_SHA256}")
    FetchContent_MakeAvailable(taiyin_ephemeris_core)
    set(_TAIYIN_CORE_SOURCE_DIR "${taiyin_ephemeris_core_SOURCE_DIR}")
endif()

# This wheel deliberately compiles only Ziwei's finite rule engine.  It must
# not link Taiyin's astronomy/calendar static libraries: doing so would create
# a second process-global ephemeris runtime beside ``taiyin._native``.  The
# Python facade resolves calendar facts through the installed base module,
# then supplies those finite facts to this target.
add_library(taiyin_ziwei_python_rules STATIC
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/anchors.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/chart.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/dynamic_bitset.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/flow.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/limits.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/json_internal.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/rule_modules.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/rules.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/rules_loader.cpp"
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/src/star_registry.cpp"
)
target_compile_features(taiyin_ziwei_python_rules PRIVATE cxx_std_11)
target_include_directories(taiyin_ziwei_python_rules
    PUBLIC
        "${_TAIYIN_CORE_SOURCE_DIR}/include"
        "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/include"
)
target_include_directories(taiyin_ziwei_python_rules SYSTEM PRIVATE
    "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/third_party/toml11")
set_target_properties(taiyin_ziwei_python_rules PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES)

pybind11_add_module(_ziwei_native MODULE src/native/ziwei_module.cpp)
target_compile_features(_ziwei_native PRIVATE cxx_std_11)
set(_TAIYIN_ZIWEI_NATIVE_OUTPUT_DIRECTORY
    "${CMAKE_CURRENT_BINARY_DIR}/native-modules/taiyin_ziwei")
set_target_properties(_ziwei_native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${_TAIYIN_ZIWEI_NATIVE_OUTPUT_DIRECTORY}"
    RUNTIME_OUTPUT_DIRECTORY "${_TAIYIN_ZIWEI_NATIVE_OUTPUT_DIRECTORY}"
    ARCHIVE_OUTPUT_DIRECTORY "${_TAIYIN_ZIWEI_NATIVE_OUTPUT_DIRECTORY}"
)
target_link_libraries(_ziwei_native PRIVATE taiyin_ziwei_python_rules)

install(TARGETS _ziwei_native DESTINATION taiyin_ziwei)
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/taiyin_ziwei/"
    DESTINATION taiyin_ziwei
    FILES_MATCHING PATTERN "*.py")
install(DIRECTORY "${_TAIYIN_CORE_SOURCE_DIR}/ziwei_astrology/rules/"
    DESTINATION taiyin_ziwei/data/rules
    FILES_MATCHING PATTERN "*.toml")
