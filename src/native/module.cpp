#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/astrology/houses.h"
#include "taiyin/astrology/sidereal.h"
#include "taiyin/runtime/native_position.h"
#include "taiyin/runtime/runtime.h"
#include "taiyin/status.h"
#include "taiyin/time.h"

#include <cmath>
#include <map>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

namespace {

using taiyin::CartesianState;
using taiyin::SplitJulianDate;
using taiyin::Status;
using taiyin::astrology::AyanamshaDispatchData;
using taiyin::astrology::HouseSystemDispatchData;
using taiyin::runtime::EphemerisEvalDiagnostic;
using taiyin::runtime::NativeCalcContext;

void require_ok(Status status, const char* operation) {
    if (status != taiyin::TAIYIN_STATUS_OK) {
        throw std::runtime_error(
            std::string(operation) + ": " + taiyin::status_message(status));
    }
}

bool finite_values(const std::vector<double>& values, std::size_t expected_size) {
    if (values.size() != expected_size) return false;
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (!std::isfinite(values[index])) return false;
    }
    return true;
}

class CustomTargetRequest {
public:
    CustomTargetRequest(
        const NativeCalcContext* context,
        int target_id,
        const SplitJulianDate& jd_tdb,
        const SplitJulianDate& jd_tt,
        uint32_t flags
    )
        : context_(context), target_id_(target_id), jd_tdb_(jd_tdb), jd_tt_(jd_tt),
          flags_(flags), valid_(true) {}

    int target_id() const { return target_id_; }
    SplitJulianDate jd_tdb() const { return jd_tdb_; }
    SplitJulianDate jd_tt() const { return jd_tt_; }
    uint32_t flags() const { return flags_; }

    std::vector<double> position_of(int target_id, uint32_t flags) const {
        if (!valid_) throw std::runtime_error("custom target request has expired");
        double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        EphemerisEvalDiagnostic diagnostic;
        require_ok(
            taiyin::runtime::calc_position_tdb(
                context_, target_id, jd_tdb_, jd_tt_, flags, out, &diagnostic),
            "CustomTargetRequest.position_of");
        return std::vector<double>(out, out + 6);
    }

    void invalidate() { valid_ = false; }

private:
    const NativeCalcContext* context_;
    int target_id_;
    SplitJulianDate jd_tdb_;
    SplitJulianDate jd_tt_;
    uint32_t flags_;
    bool valid_;
};

class EphemerisRuntime {
public:
    EphemerisRuntime(
        const std::vector<std::string>& source_paths,
        const std::string& data_root,
        bool load_packaged_data,
        bool load_builtin_eop,
        std::size_t segment_cache_max_entries,
        bool strict_discovery
    ) {
        std::vector<const char*> native_paths;
        native_paths.reserve(source_paths.size());
        for (std::size_t index = 0; index < source_paths.size(); ++index) {
            native_paths.push_back(source_paths[index].c_str());
        }
        taiyin::runtime::EphemerisRuntimeConfig config;
        config.source_paths = native_paths.empty() ? 0 : &native_paths[0];
        config.source_path_count = native_paths.size();
        config.data_root = data_root.empty() ? 0 : data_root.c_str();
        config.load_packaged_data = load_packaged_data;
        config.load_builtin_eop = load_builtin_eop;
        config.segment_cache_max_entries = segment_cache_max_entries;
        config.strict_discovery = strict_discovery;
        if (!taiyin::runtime::initialize_global_ephemeris_runtime(config)) {
            throw std::runtime_error("Taiyin runtime initialization failed");
        }
    }

    NativeCalcContext create_context() const {
        return taiyin::runtime::get_default_native_calc_context();
    }

    void add_source_path(const std::string& path) const {
        if (path.empty() || !taiyin::runtime::add_global_ephemeris_source_path(path.c_str())) {
            throw std::runtime_error("could not add ephemeris source path");
        }
    }

    void clear_cache() const { taiyin::runtime::clear_global_ephemeris_cache(); }
    std::size_t catalog_size() const { return taiyin::runtime::global_ephemeris_catalog_size(); }
    std::size_t cache_entry_count() const {
        return taiyin::runtime::global_ephemeris_cache_entry_count();
    }
};

struct TargetCallback {
    py::function position;
    py::function state;
};
struct AyanamshaCallback { py::function evaluator; };
struct HouseCallback { py::function evaluator; };

std::mutex callback_mutex;
std::map<int, std::shared_ptr<TargetCallback> > target_callbacks;
std::map<int, std::shared_ptr<AyanamshaCallback> > ayanamsha_callbacks;
std::map<int, std::shared_ptr<HouseCallback> > house_callbacks;

template <typename T>
std::shared_ptr<T> find_callback(
    const std::map<int, std::shared_ptr<T> >& callbacks,
    int id
) {
    typename std::map<int, std::shared_ptr<T> >::const_iterator it = callbacks.find(id);
    return it == callbacks.end() ? std::shared_ptr<T>() : it->second;
}

Status target_position_callback(
    const NativeCalcContext* context,
    int target_id,
    const SplitJulianDate& jd_tdb,
    const SplitJulianDate& jd_tt,
    uint32_t flags,
    double out[6],
    EphemerisEvalDiagnostic*
) {
    std::shared_ptr<TargetCallback> callback;
    {
        std::lock_guard<std::mutex> lock(callback_mutex);
        callback = find_callback(target_callbacks, target_id);
    }
    if (!callback || !out) return taiyin::TAIYIN_ERROR_INTERNAL;

    try {
        py::gil_scoped_acquire gil;
        CustomTargetRequest request(context, target_id, jd_tdb, jd_tt, flags);
        std::vector<double> values = callback->position(request).cast<std::vector<double> >();
        request.invalidate();
        if (!finite_values(values, 6)) return taiyin::TAIYIN_ERROR_INVALID_ARGUMENT;
        for (std::size_t index = 0; index < values.size(); ++index) out[index] = values[index];
        return taiyin::TAIYIN_STATUS_OK;
    } catch (...) {
        return taiyin::TAIYIN_ERROR_INTERNAL;
    }
}

Status target_state_callback(
    const NativeCalcContext* context,
    int target_id,
    const SplitJulianDate& jd_tdb,
    const SplitJulianDate& jd_tt,
    uint32_t flags,
    CartesianState* out,
    EphemerisEvalDiagnostic*
) {
    std::shared_ptr<TargetCallback> callback;
    {
        std::lock_guard<std::mutex> lock(callback_mutex);
        callback = find_callback(target_callbacks, target_id);
    }
    if (!callback || !callback->state || !out) return taiyin::TAIYIN_ERROR_INTERNAL;

    try {
        py::gil_scoped_acquire gil;
        CustomTargetRequest request(context, target_id, jd_tdb, jd_tt, flags);
        py::dict result = callback->state(request).cast<py::dict>();
        request.invalidate();
        std::vector<double> position = result["position_au"].cast<std::vector<double> >();
        std::vector<double> velocity = result["velocity_au_per_day"].cast<std::vector<double> >();
        std::vector<double> acceleration = result["acceleration_au_per_day2"].cast<std::vector<double> >();
        if (!finite_values(position, 3) || !finite_values(velocity, 3)
            || !finite_values(acceleration, 3)) {
            return taiyin::TAIYIN_ERROR_INVALID_ARGUMENT;
        }
        out->position_au.x = position[0];
        out->position_au.y = position[1];
        out->position_au.z = position[2];
        out->velocity_au_per_day.x = velocity[0];
        out->velocity_au_per_day.y = velocity[1];
        out->velocity_au_per_day.z = velocity[2];
        out->acceleration_au_per_day2.x = acceleration[0];
        out->acceleration_au_per_day2.y = acceleration[1];
        out->acceleration_au_per_day2.z = acceleration[2];
        return taiyin::TAIYIN_STATUS_OK;
    } catch (...) {
        return taiyin::TAIYIN_ERROR_INTERNAL;
    }
}

Status ayanamsha_callback(const AyanamshaDispatchData* data, double* out) {
    if (!data || !out || !data->model_data) return taiyin::TAIYIN_ERROR_INVALID_ARGUMENT;
    const AyanamshaCallback* callback = static_cast<const AyanamshaCallback*>(data->model_data);
    try {
        py::gil_scoped_acquire gil;
        py::dict request;
        request["jd_tt"] = data->jd_tt;
        request["native_position_flags"] = data->native_position_flags;
        const double value = callback->evaluator(request).cast<double>();
        if (!std::isfinite(value)) return taiyin::TAIYIN_ERROR_INVALID_ARGUMENT;
        *out = value;
        return taiyin::TAIYIN_STATUS_OK;
    } catch (...) {
        return taiyin::TAIYIN_ERROR_INTERNAL;
    }
}

bool house_callback(const HouseSystemDispatchData* data, double out[12]) {
    if (!data || !out || !data->model_data) return false;
    const HouseCallback* callback = static_cast<const HouseCallback*>(data->model_data);
    try {
        py::gil_scoped_acquire gil;
        py::dict request;
        request["armc_radians"] = data->armc_rad;
        request["observer_latitude_radians"] = data->observer_latitude_rad;
        request["true_obliquity_radians"] = data->true_obliquity_rad;
        request["ascendant_radians"] = data->ascendant_rad;
        request["midheaven_radians"] = data->midheaven_rad;
        std::vector<double> values = callback->evaluator(request).cast<std::vector<double> >();
        if (!finite_values(values, 12)) return false;
        for (std::size_t index = 0; index < values.size(); ++index) out[index] = values[index];
        return true;
    } catch (...) {
        return false;
    }
}

class TargetRegistration {
public:
    explicit TargetRegistration(int target_id) : target_id_(target_id), closed_(false) {}
    ~TargetRegistration() { close(); }
    int target_id() const { return target_id_; }
    bool is_closed() const { return closed_; }
    void close() {
        if (closed_) return;
        taiyin::runtime::unregister_global_native_position_evaluator(target_id_);
        std::lock_guard<std::mutex> lock(callback_mutex);
        target_callbacks.erase(target_id_);
        closed_ = true;
    }
private:
    int target_id_;
    bool closed_;
};

class AyanamshaRegistration {
public:
    explicit AyanamshaRegistration(int model_id) : model_id_(model_id), closed_(false) {}
    ~AyanamshaRegistration() { close(); }
    int model_id() const { return model_id_; }
    bool is_closed() const { return closed_; }
    void close() {
        if (closed_) return;
        std::shared_ptr<AyanamshaCallback> callback;
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            callback = find_callback(ayanamsha_callbacks, model_id_);
        }
        if (callback) {
            taiyin::astrology::remove_ayanamsha_model_if_matches(
                model_id_, &ayanamsha_callback, callback.get());
        }
        std::lock_guard<std::mutex> lock(callback_mutex);
        ayanamsha_callbacks.erase(model_id_);
        closed_ = true;
    }
private:
    int model_id_;
    bool closed_;
};

class HouseRegistration {
public:
    explicit HouseRegistration(int model_id) : model_id_(model_id), closed_(false) {}
    ~HouseRegistration() {
        try { close(); } catch (...) {}
    }
    int model_id() const { return model_id_; }
    bool is_closed() const { return closed_; }
    void close() {
        if (closed_) return;
        std::shared_ptr<HouseCallback> callback;
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            callback = find_callback(house_callbacks, model_id_);
        }
        if (callback) {
            const taiyin::astrology::HouseSystemModelRemovalResult result =
                taiyin::astrology::remove_house_system_model_if_matches(
                    model_id_, &house_callback, callback.get());
            if (result == taiyin::astrology::HouseSystemModelRemovalResult::still_referenced) {
                throw std::runtime_error("custom house system is still used as a fallback");
            }
        }
        std::lock_guard<std::mutex> lock(callback_mutex);
        house_callbacks.erase(model_id_);
        closed_ = true;
    }
private:
    int model_id_;
    bool closed_;
};

}  // namespace

PYBIND11_MODULE(_native, module) {
    module.doc() = "Direct pybind11 bindings for Taiyin Ephemeris";
    module.attr("__version__") = "0.1.0a0";
    module.attr("POSITION_NONUT") = taiyin::runtime::TAIYIN_NATIVE_POSITION_NONUT;
    module.def("binding_backend", []() { return "pybind11"; });

    py::class_<SplitJulianDate>(module, "JulianDate")
        .def(py::init<int64_t, double>(), py::arg("day_number"), py::arg("day_fraction"))
        .def_static("from_double", [](double value) {
            SplitJulianDate result;
            if (!taiyin::split_julian_date_from_double(value, &result)) {
                throw py::value_error("Julian date must be finite");
            }
            return result;
        })
        .def_readwrite("day_number", &SplitJulianDate::day_number)
        .def_readwrite("day_fraction", &SplitJulianDate::day_fraction)
        .def("to_double", &taiyin::split_julian_date_to_double)
        .def("add_seconds", [](const SplitJulianDate& value, double seconds) {
            SplitJulianDate result;
            if (!taiyin::add_seconds_to_split_jd(value, seconds, &result)) {
                throw py::value_error("Julian date and seconds must be finite");
            }
            return result;
        })
        .def("seconds_difference", [](const SplitJulianDate& value, const SplitJulianDate& other) {
            return taiyin::seconds_between_split_jd(value, other);
        });
    py::class_<taiyin::CalendarDateTime>(module, "AstroDateTime")
        .def(py::init([](int year, int month, int day, int hour, int minute, double second) {
            taiyin::CalendarDateTime result = {year, month, day, hour, minute, second};
            return result;
        }), py::arg("year"), py::arg("month"), py::arg("day"),
           py::arg("hour") = 0, py::arg("minute") = 0, py::arg("second") = 0.0)
        .def_readwrite("year", &taiyin::CalendarDateTime::year)
        .def_readwrite("month", &taiyin::CalendarDateTime::month)
        .def_readwrite("day", &taiyin::CalendarDateTime::day)
        .def_readwrite("hour", &taiyin::CalendarDateTime::hour)
        .def_readwrite("minute", &taiyin::CalendarDateTime::minute)
        .def_readwrite("second", &taiyin::CalendarDateTime::second);
    py::class_<NativeCalcContext>(module, "NativeContext")
        .def(py::init<>())
        .def("clone", [](const NativeCalcContext& context) { return context; })
        .def("position_at_tdb", [](const NativeCalcContext& context, int target_id,
                                    const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                    uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_tdb(
                &context, target_id, jd_tdb, jd_tt, flags, out, &diagnostic),
                "EphemerisContext.position_at_tdb");
            return std::vector<double>(out, out + 6);
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_tt", [](const NativeCalcContext& context, int target_id,
                                   const SplitJulianDate& jd_tt, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_tt(
                &context, target_id, jd_tt, flags, out, &diagnostic),
                "EphemerisContext.position_at_tt");
            return std::vector<double>(out, out + 6);
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_ut1", [](const NativeCalcContext& context, int target_id,
                                    const SplitJulianDate& jd_ut1, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_ut(
                &context, target_id, jd_ut1, flags, out, &diagnostic),
                "EphemerisContext.position_at_ut1");
            return std::vector<double>(out, out + 6);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("position_at_ut1_with_delta_t", [](const NativeCalcContext& context, int target_id,
                                                 const SplitJulianDate& jd_ut1,
                                                 double delta_t_seconds, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_ut_delta_t(
                &context, target_id, jd_ut1, delta_t_seconds, flags, out, &diagnostic),
                "EphemerisContext.position_at_ut1_with_delta_t");
            return std::vector<double>(out, out + 6);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("delta_t_seconds"), py::arg("flags") = 0)
        .def("position_at_utc", [](const NativeCalcContext& context, int target_id,
                                    const taiyin::CalendarDateTime& utc, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_utc(
                &context, target_id, utc, flags, out, &diagnostic),
                "EphemerisContext.position_at_utc");
            return std::vector<double>(out, out + 6);
        }, py::arg("target_id"), py::arg("utc"), py::arg("flags") = 0)
        .def("positions_at_tt", [](const NativeCalcContext& context,
                                    const std::vector<int>& target_ids,
                                    const SplitJulianDate& jd_tt, uint32_t flags) {
            std::vector<double> values(target_ids.size() * 6u, 0.0);
            std::vector<EphemerisEvalDiagnostic> diagnostics(target_ids.size());
            require_ok(taiyin::runtime::calc_positions_tt(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_tt,
                flags, values.empty() ? 0 : &values[0],
                diagnostics.empty() ? 0 : &diagnostics[0]), "EphemerisContext.positions_at_tt");
            std::vector<std::vector<double> > result;
            result.reserve(target_ids.size());
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.push_back(std::vector<double>(
                    values.begin() + index * 6u, values.begin() + (index + 1u) * 6u));
            }
            return result;
        }, py::arg("target_ids"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("positions_at_ut1", [](const NativeCalcContext& context,
                                     const std::vector<int>& target_ids,
                                     const SplitJulianDate& jd_ut1, uint32_t flags) {
            std::vector<double> values(target_ids.size() * 6u, 0.0);
            std::vector<EphemerisEvalDiagnostic> diagnostics(target_ids.size());
            require_ok(taiyin::runtime::calc_positions_ut(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_ut1,
                flags, values.empty() ? 0 : &values[0],
                diagnostics.empty() ? 0 : &diagnostics[0]), "EphemerisContext.positions_at_ut1");
            std::vector<std::vector<double> > result;
            result.reserve(target_ids.size());
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.push_back(std::vector<double>(
                    values.begin() + index * 6u, values.begin() + (index + 1u) * 6u));
            }
            return result;
        }, py::arg("target_ids"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("state_at_tdb", [](const NativeCalcContext& context, int target_id,
                                 const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                 uint32_t flags) {
            CartesianState out;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_state_tdb(
                &context, target_id, jd_tdb, jd_tt, flags, &out, &diagnostic),
                "EphemerisContext.state_at_tdb");
            py::dict result;
            result["position_au"] = py::make_tuple(out.position_au.x, out.position_au.y, out.position_au.z);
            result["velocity_au_per_day"] = py::make_tuple(
                out.velocity_au_per_day.x, out.velocity_au_per_day.y, out.velocity_au_per_day.z);
            result["acceleration_au_per_day2"] = py::make_tuple(
                out.acceleration_au_per_day2.x,
                out.acceleration_au_per_day2.y,
                out.acceleration_au_per_day2.z);
            return result;
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_tt", [](const NativeCalcContext& context, int target_id,
                                const SplitJulianDate& jd_tt, uint32_t flags) {
            CartesianState out;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_state_tt(
                &context, target_id, jd_tt, flags, &out, &diagnostic),
                "EphemerisContext.state_at_tt");
            py::dict result;
            result["position_au"] = py::make_tuple(out.position_au.x, out.position_au.y, out.position_au.z);
            result["velocity_au_per_day"] = py::make_tuple(
                out.velocity_au_per_day.x, out.velocity_au_per_day.y, out.velocity_au_per_day.z);
            result["acceleration_au_per_day2"] = py::make_tuple(
                out.acceleration_au_per_day2.x,
                out.acceleration_au_per_day2.y,
                out.acceleration_au_per_day2.z);
            return result;
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_ut1", [](const NativeCalcContext& context, int target_id,
                                 const SplitJulianDate& jd_ut1, uint32_t flags) {
            CartesianState out;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_state_ut(
                &context, target_id, jd_ut1, flags, &out, &diagnostic),
                "EphemerisContext.state_at_ut1");
            py::dict result;
            result["position_au"] = py::make_tuple(out.position_au.x, out.position_au.y, out.position_au.z);
            result["velocity_au_per_day"] = py::make_tuple(
                out.velocity_au_per_day.x, out.velocity_au_per_day.y, out.velocity_au_per_day.z);
            result["acceleration_au_per_day2"] = py::make_tuple(
                out.acceleration_au_per_day2.x,
                out.acceleration_au_per_day2.y,
                out.acceleration_au_per_day2.z);
            return result;
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0);
    py::class_<EphemerisRuntime>(module, "_EphemerisRuntime")
        .def(py::init<const std::vector<std::string>&, const std::string&, bool, bool, std::size_t, bool>(),
             py::arg("source_paths") = std::vector<std::string>(),
             py::arg("data_root") = std::string(),
             py::arg("load_packaged_data") = true,
             py::arg("load_builtin_eop") = true,
             py::arg("segment_cache_max_entries") = 4096,
             py::arg("strict_discovery") = false)
        .def("create_context", &EphemerisRuntime::create_context)
        .def("add_source_path", &EphemerisRuntime::add_source_path)
        .def("clear_ephemeris_cache", &EphemerisRuntime::clear_cache)
        .def_property_readonly("catalog_size", &EphemerisRuntime::catalog_size)
        .def_property_readonly("cache_entry_count", &EphemerisRuntime::cache_entry_count);
    py::class_<CustomTargetRequest>(module, "CustomTargetRequest")
        .def_property_readonly("target_id", &CustomTargetRequest::target_id)
        .def_property_readonly("jd_tdb", &CustomTargetRequest::jd_tdb)
        .def_property_readonly("jd_tt", &CustomTargetRequest::jd_tt)
        .def_property_readonly("flags", &CustomTargetRequest::flags)
        .def("position_of", &CustomTargetRequest::position_of,
             py::arg("target_id"), py::arg("flags") = 0);

    py::class_<TargetRegistration>(module, "CustomTargetRegistration")
        .def_property_readonly("target_id", &TargetRegistration::target_id)
        .def_property_readonly("is_closed", &TargetRegistration::is_closed)
        .def("close", &TargetRegistration::close);
    py::class_<AyanamshaRegistration>(module, "CustomAyanamshaRegistration")
        .def_property_readonly("model_id", &AyanamshaRegistration::model_id)
        .def_property_readonly("is_closed", &AyanamshaRegistration::is_closed)
        .def("close", &AyanamshaRegistration::close);
    py::class_<HouseRegistration>(module, "CustomHouseSystemRegistration")
        .def_property_readonly("model_id", &HouseRegistration::model_id)
        .def_property_readonly("is_closed", &HouseRegistration::is_closed)
        .def("close", &HouseRegistration::close);

    module.def("register_custom_target", [](int target_id, py::function position, py::object state) {
        if (target_id >= 0) throw py::value_error("custom target_id must be negative");
        std::shared_ptr<TargetCallback> callback(new TargetCallback());
        callback->position = position;
        if (!state.is_none()) callback->state = state.cast<py::function>();
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            if (target_callbacks.count(target_id)) throw py::value_error("custom target_id is already registered");
            target_callbacks[target_id] = callback;
        }
        if (!taiyin::runtime::register_global_native_position_evaluator(
                target_id, &target_position_callback,
                callback->state ? &target_state_callback : 0)) {
            std::lock_guard<std::mutex> lock(callback_mutex);
            target_callbacks.erase(target_id);
            throw std::runtime_error("Taiyin rejected custom target registration");
        }
        return std::unique_ptr<TargetRegistration>(new TargetRegistration(target_id));
    }, py::arg("target_id"), py::arg("position"), py::arg("state") = py::none());

    module.def("position_at_tdb", [](const NativeCalcContext& context, int target_id,
                                      const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                      uint32_t flags) {
        double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::runtime::calc_position_tdb(
            &context, target_id, jd_tdb, jd_tt, flags, out, &diagnostic), "position_at_tdb");
        return std::vector<double>(out, out + 6);
    }, py::arg("context"), py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0);

    module.def("state_at_tdb", [](const NativeCalcContext& context, int target_id,
                                   const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                   uint32_t flags) {
        CartesianState out;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::runtime::calc_state_tdb(
            &context, target_id, jd_tdb, jd_tt, flags, &out, &diagnostic), "state_at_tdb");
        py::dict result;
        result["position_au"] = py::make_tuple(out.position_au.x, out.position_au.y, out.position_au.z);
        result["velocity_au_per_day"] = py::make_tuple(
            out.velocity_au_per_day.x, out.velocity_au_per_day.y, out.velocity_au_per_day.z);
        result["acceleration_au_per_day2"] = py::make_tuple(
            out.acceleration_au_per_day2.x,
            out.acceleration_au_per_day2.y,
            out.acceleration_au_per_day2.z);
        return result;
    }, py::arg("context"), py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0);

    module.def("register_custom_ayanamsha", [](int model_id, py::function evaluator,
                                                 int reference_precession_model) {
        std::shared_ptr<AyanamshaCallback> callback(new AyanamshaCallback());
        callback->evaluator = evaluator;
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            if (ayanamsha_callbacks.count(model_id)) throw py::value_error("custom ayanamsha model_id is already registered");
            ayanamsha_callbacks[model_id] = callback;
        }
        if (!taiyin::astrology::add_ayanamsha_model(taiyin::astrology::AyanamshaModelEntry(
                model_id, &ayanamsha_callback, reference_precession_model, callback.get()))) {
            std::lock_guard<std::mutex> lock(callback_mutex);
            ayanamsha_callbacks.erase(model_id);
            throw std::runtime_error("Taiyin rejected custom ayanamsha registration");
        }
        return std::unique_ptr<AyanamshaRegistration>(new AyanamshaRegistration(model_id));
    }, py::arg("model_id"), py::arg("evaluator"), py::arg("reference_precession_model") = -1);

    module.def("ayanamsha_at_tt", [](const NativeCalcContext& context, int model_id,
                                      const SplitJulianDate& jd_tt, uint64_t flags) {
        double value = NAN;
        require_ok(taiyin::astrology::calc_ayanamsha_tt(
            &context, model_id, jd_tt, flags, &value), "ayanamsha_at_tt");
        return value;
    }, py::arg("context"), py::arg("model_id"), py::arg("jd_tt"), py::arg("flags") = 0);

    module.def("register_custom_house_system", [](int model_id, py::function evaluator,
                                                   int fallback_model_id) {
        std::shared_ptr<HouseCallback> callback(new HouseCallback());
        callback->evaluator = evaluator;
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            if (house_callbacks.count(model_id)) throw py::value_error("custom house-system model_id is already registered");
            house_callbacks[model_id] = callback;
        }
        if (!taiyin::astrology::add_house_system_model(taiyin::astrology::HouseSystemModelEntry(
                model_id, &house_callback, fallback_model_id, callback.get()))) {
            std::lock_guard<std::mutex> lock(callback_mutex);
            house_callbacks.erase(model_id);
            throw std::runtime_error("Taiyin rejected custom house-system registration");
        }
        return std::unique_ptr<HouseRegistration>(new HouseRegistration(model_id));
    }, py::arg("model_id"), py::arg("evaluator"), py::arg("fallback_model_id") = -1);

    module.def("houses_from_armc", [](double armc_radians, double latitude_radians,
                                       double true_obliquity_radians, int model_id) {
        taiyin::astrology::HouseResult result;
        require_ok(taiyin::astrology::calc_houses_from_armc(
            armc_radians, latitude_radians, true_obliquity_radians, model_id, &result),
            "houses_from_armc");
        return std::vector<double>(result.cusp_longitude_rad, result.cusp_longitude_rad + 12);
    }, py::arg("armc_radians"), py::arg("latitude_radians"),
       py::arg("true_obliquity_radians"), py::arg("model_id"));

    module.def("_tt_to_tdb", [](const SplitJulianDate& value, int model_id) {
        SplitJulianDate result;
        if (!taiyin::tt_to_tdb_split_jd(
                value, static_cast<taiyin::TdbModel>(model_id), &result)) {
            throw py::value_error("invalid TT Julian date or TDB model");
        }
        return result;
    }, py::arg("value"), py::arg("model_id") = static_cast<int>(taiyin::FastPeriodic));
    module.def("_tdb_to_tt", [](const SplitJulianDate& value, int model_id) {
        SplitJulianDate result;
        if (!taiyin::tdb_to_tt_split_jd(
                value, static_cast<taiyin::TdbModel>(model_id), &result)) {
            throw py::value_error("invalid TDB Julian date or TDB model");
        }
        return result;
    }, py::arg("value"), py::arg("model_id") = static_cast<int>(taiyin::FastPeriodic));
    module.def("_estimated_delta_t_from_ut1", [](const SplitJulianDate& value) {
        return taiyin::estimated_delta_t_seconds_from_ut1_jd(value);
    });
    module.def("_estimated_delta_t_from_tt", [](const SplitJulianDate& value) {
        return taiyin::estimated_delta_t_seconds_from_tt_jd(value);
    });
}
