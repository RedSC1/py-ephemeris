cmake_minimum_required(VERSION 3.18)

project(py_ephemeris_bazi LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

set(
    TAIYIN_SOURCE_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../taiyin-ephemeris"
    CACHE PATH
    "Path to a taiyin-ephemeris C++ source checkout"
)
if(NOT EXISTS "${TAIYIN_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR
        "TAIYIN_SOURCE_DIR must point at a taiyin-ephemeris source checkout; "
        "got: ${TAIYIN_SOURCE_DIR}")
endif()

set(TAIYIN_BUILD_MODULAR_C_API OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_CHINESE_METAPHYSICS_EXTENSIONS ON CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_BAZI_EXTENSION ON CACHE BOOL "" FORCE)
add_subdirectory(
    "${TAIYIN_SOURCE_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}/taiyin-ephemeris"
    EXCLUDE_FROM_ALL
)

pybind11_add_module(_bazi_native MODULE src/native/bazi_module.cpp)
target_compile_features(_bazi_native PRIVATE cxx_std_11)
target_link_libraries(_bazi_native PRIVATE taiyin_bazi_extension)
install(TARGETS _bazi_native DESTINATION taiyin_bazi)
