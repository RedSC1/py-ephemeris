#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(_native, module) {
    module.doc() = "Native bindings for Taiyin Ephemeris";
    module.attr("__version__") = "0.1.0a0";
    module.def("binding_backend", []() { return "pybind11"; });
}

