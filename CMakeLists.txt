cmake_minimum_required(VERSION 3.18)

project(py_ephemeris LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_native MODULE src/native/module.cpp)
target_compile_features(_native PRIVATE cxx_std_11)

install(TARGETS _native DESTINATION taiyin)

