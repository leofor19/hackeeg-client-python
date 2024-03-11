// acquire_data_cpp
// pybind_wrapper.cpp

// Usage:
// import acquire_data_module
// data = acquire_data_module.acquire_data_cpp()
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "acquire_data.cpp"

namespace py = pybind11;

std::vector<int> acquire_data_cpp_wrapper(int max_samples, float duration, int speed, bool display_output = false) {
    return acquire_data_cpp(max_samples, duration, speed, display_output);
}

PYBIND11_MODULE(acquire_data_module, m) {
    m.def("acquire_data_cpp", &acquire_data_cpp, "A function that acquires data");
}