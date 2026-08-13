cmake_minimum_required(VERSION 3.18)

project(py_ephemeris LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Bind the C++ API directly.  The temporary port uses a source checkout;
# release packaging will pin that source instead of exposing a taiyin DLL.
set(
    TAIYIN_SOURCE_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/../taiyin-ephemeris"
    CACHE PATH
    "Path to the Taiyin Ephemeris C++ source checkout"
)
if(NOT EXISTS "${TAIYIN_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR
        "TAIYIN_SOURCE_DIR must point at a taiyin-ephemeris source checkout; "
        "got: ${TAIYIN_SOURCE_DIR}")
endif()

set(TAIYIN_BUILD_MODULAR_C_API OFF CACHE BOOL "" FORCE)
set(TAIYIN_BUILD_CHINESE_METAPHYSICS_EXTENSIONS ON CACHE BOOL "" FORCE)
# BaZi is compiled by the separately distributed py-ephemeris-bazi wheel.
set(TAIYIN_BUILD_BAZI_EXTENSION OFF CACHE BOOL "" FORCE)
add_subdirectory(
    "${TAIYIN_SOURCE_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}/taiyin-ephemeris"
    EXCLUDE_FROM_ALL
)

pybind11_add_module(_native MODULE src/native/module.cpp)
target_compile_features(_native PRIVATE cxx_std_11)
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
