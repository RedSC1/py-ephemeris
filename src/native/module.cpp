#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/astrology/houses.h"
#include "taiyin/astrology/lunar_points.h"
#include "taiyin/astrology/sidereal.h"
#include "taiyin/chinese_calendar/ganzhi.h"
#include "taiyin/runtime/native_position.h"
#include "taiyin/runtime/moon_visibility.h"
#include "taiyin/runtime/planet_visibility.h"
#include "taiyin/runtime/solar_visibility.h"
#include "taiyin/runtime/star_visibility.h"
#include "taiyin/runtime/phenomena.h"
#include "taiyin/runtime/event_search.h"
#include "taiyin/runtime/runtime.h"
#include "taiyin/runtime/solar_time.h"
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

py::dict precise_time_scales_to_dict(const taiyin::PreciseTimeScales& value) {
    py::dict result;
    result["utc"] = value.jd_utc;
    result["tai"] = value.jd_tai;
    result["tt"] = value.jd_tt;
    result["ut1"] = value.jd_ut1;
    result["tdb"] = value.jd_tdb;
    result["tai_minus_utc_seconds"] = value.tai_minus_utc_seconds;
    result["dut1_seconds"] = value.dut1_seconds;
    result["delta_t_seconds"] = value.delta_t_seconds;
    return result;
}

py::dict estimated_time_scales_to_dict(const taiyin::EstimatedTimeScales& value) {
    py::dict result;
    result["ut1"] = value.jd_ut1;
    result["tt"] = value.jd_tt;
    result["tdb"] = value.jd_tdb;
    result["delta_t_seconds"] = value.delta_t_seconds;
    return result;
}

py::dict diagnostic_to_dict(const EphemerisEvalDiagnostic& value) {
    py::dict result;
    result["status"] = static_cast<int>(value.status);
    result["target_id"] = value.target_id;
    result["center_id"] = value.center_id;
    result["frame"] = static_cast<int>(value.frame);
    result["jd_tdb"] = value.jd_tdb;
    result["candidate_count"] = value.candidate_count;
    result["attempted_method_id"] = value.attempted_method_id;
    result["nearest_coverage_start"] = value.nearest_coverage_start;
    result["nearest_coverage_end"] = value.nearest_coverage_end;
    result["component_target_id"] = value.component_target_id;
    result["component_center_id"] = value.component_center_id;
    result["component_method_id"] = value.component_method_id;
    result["time_scale_route"] = value.time_scale_route;
    result["time_scale_fallback_reason"] = value.time_scale_fallback_reason;
    result["time_scale_flags"] = value.time_scale_flags;
    result["tai_minus_utc_seconds"] = value.tai_minus_utc_seconds;
    result["dut1_seconds"] = value.dut1_seconds;
    result["delta_t_seconds"] = value.delta_t_seconds;
    return result;
}

py::dict position_result_to_dict(const double values[6], const EphemerisEvalDiagnostic& diagnostic) {
    py::dict result;
    result["values"] = std::vector<double>(values, values + 6);
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict state_result_to_dict(const CartesianState& value, const EphemerisEvalDiagnostic& diagnostic) {
    py::dict result;
    result["position_au"] = py::make_tuple(value.position_au.x, value.position_au.y, value.position_au.z);
    result["velocity_au_per_day"] = py::make_tuple(
        value.velocity_au_per_day.x, value.velocity_au_per_day.y, value.velocity_au_per_day.z);
    result["acceleration_au_per_day2"] = py::make_tuple(
        value.acceleration_au_per_day2.x,
        value.acceleration_au_per_day2.y,
        value.acceleration_au_per_day2.z);
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict equation_of_time_to_dict(
    const taiyin::runtime::EquationOfTimeResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["ut1"] = value.jd_ut;
    result["tt"] = value.jd_tt;
    result["equation_days"] = value.equation_days;
    result["equation_seconds"] = value.equation_seconds;
    result["apparent_sun_right_ascension_radians"] = value.apparent_sun_right_ascension_rad;
    result["greenwich_apparent_sidereal_time_radians"] = value.gast_rad;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

typedef Status (*EventScalarFn)(
    const NativeCalcContext*, double, SplitJulianDate, uint64_t,
    SplitJulianDate*, EphemerisEvalDiagnostic*);
typedef Status (*EventDateArrayFn)(
    const NativeCalcContext*, int, double, SplitJulianDate, SplitJulianDate,
    double, uint64_t, SplitJulianDate*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventStationArrayFn)(
    const NativeCalcContext*, int, SplitJulianDate, SplitJulianDate, double,
    uint64_t, SplitJulianDate*, double*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventAspectArrayFn)(
    const NativeCalcContext*, int, int, double, SplitJulianDate, SplitJulianDate,
    double, uint64_t, SplitJulianDate*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventExactAspectArrayFn)(
    const NativeCalcContext*, int, int, const double*, size_t, SplitJulianDate,
    SplitJulianDate, double, uint64_t, SplitJulianDate*, double*, size_t, size_t*,
    EphemerisEvalDiagnostic*);
typedef Status (*EventPhaseArrayFn)(
    const NativeCalcContext*, double, SplitJulianDate, SplitJulianDate, double,
    uint64_t, SplitJulianDate*, size_t, size_t*, EphemerisEvalDiagnostic*);

py::dict event_scalar(
    const NativeCalcContext& context, EventScalarFn function, double target,
    const SplitJulianDate& estimate, uint64_t flags, const char* operation
) {
    SplitJulianDate coordinate;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, target, estimate, flags, &coordinate, &diagnostic), operation);
    py::dict result;
    result["coordinate"] = coordinate;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict event_dates(
    const NativeCalcContext& context, EventDateArrayFn function, int body_id,
    double target, const SplitJulianDate& start, const SplitJulianDate& end,
    double max_step_days, uint64_t flags, size_t capacity, const char* operation
) {
    std::vector<SplitJulianDate> coordinates(capacity);
    size_t count = 0;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, body_id, target, start, end, max_step_days, flags,
                        coordinates.empty() ? 0 : &coordinates[0], capacity, &count, &diagnostic),
               operation);
    py::list values;
    for (size_t index = 0; index < count; ++index) values.append(coordinates[index]);
    py::dict result;
    result["values"] = values;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict event_stations(
    const NativeCalcContext& context, EventStationArrayFn function, int body_id,
    const SplitJulianDate& start, const SplitJulianDate& end, double max_step_days,
    uint64_t flags, size_t capacity, const char* operation
) {
    std::vector<SplitJulianDate> coordinates(capacity);
    std::vector<double> longitudes(capacity);
    size_t count = 0;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, body_id, start, end, max_step_days, flags,
                        coordinates.empty() ? 0 : &coordinates[0],
                        longitudes.empty() ? 0 : &longitudes[0], capacity, &count, &diagnostic),
               operation);
    py::list values;
    for (size_t index = 0; index < count; ++index) {
        py::dict value;
        value["coordinate"] = coordinates[index];
        value["longitude_radians"] = longitudes[index];
        values.append(value);
    }
    py::dict result;
    result["values"] = values;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict event_aspects(
    const NativeCalcContext& context, EventAspectArrayFn function, int body_a_id,
    int body_b_id, double aspect, const SplitJulianDate& start, const SplitJulianDate& end,
    double max_step_days, uint64_t flags, size_t capacity, const char* operation
) {
    std::vector<SplitJulianDate> coordinates(capacity);
    size_t count = 0;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, body_a_id, body_b_id, aspect, start, end, max_step_days, flags,
                        coordinates.empty() ? 0 : &coordinates[0], capacity, &count, &diagnostic),
               operation);
    py::list values;
    for (size_t index = 0; index < count; ++index) values.append(coordinates[index]);
    py::dict result;
    result["values"] = values;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict event_exact_aspects(
    const NativeCalcContext& context, EventExactAspectArrayFn function, int body_a_id,
    int body_b_id, const std::vector<double>& aspects, const SplitJulianDate& start,
    const SplitJulianDate& end, double max_step_days, uint64_t flags, size_t capacity,
    const char* operation
) {
    std::vector<SplitJulianDate> coordinates(capacity);
    std::vector<double> matched_aspects(capacity);
    size_t count = 0;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, body_a_id, body_b_id,
                        aspects.empty() ? 0 : &aspects[0], aspects.size(), start, end,
                        max_step_days, flags, coordinates.empty() ? 0 : &coordinates[0],
                        matched_aspects.empty() ? 0 : &matched_aspects[0], capacity, &count,
                        &diagnostic), operation);
    py::list values;
    for (size_t index = 0; index < count; ++index) {
        py::dict value;
        value["coordinate"] = coordinates[index];
        value["aspect_radians"] = matched_aspects[index];
        values.append(value);
    }
    py::dict result;
    result["values"] = values;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict event_phases(
    const NativeCalcContext& context, EventPhaseArrayFn function, double phase,
    const SplitJulianDate& start, const SplitJulianDate& end, double max_step_days,
    uint64_t flags, size_t capacity, const char* operation
) {
    std::vector<SplitJulianDate> coordinates(capacity);
    size_t count = 0;
    EphemerisEvalDiagnostic diagnostic;
    require_ok(function(&context, phase, start, end, max_step_days, flags,
                        coordinates.empty() ? 0 : &coordinates[0], capacity, &count, &diagnostic),
               operation);
    py::list values;
    for (size_t index = 0; index < count; ++index) values.append(coordinates[index]);
    py::dict result;
    result["values"] = values;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict solar_transit_to_dict(const taiyin::runtime::SolarTransitSearchResult& value) {
    py::dict result;
    result["body_id"] = value.body_id;
    result["kind"] = value.kind;
    result["greatest"] = value.greatest_jd_ut;
    result["minimum_separation_radians"] = value.minimum_separation_rad;
    result["sun_radius_radians"] = value.sun_radius_rad;
    result["body_radius_radians"] = value.body_radius_rad;
    result["t1"] = value.t1_jd_ut;
    result["t2"] = value.t2_jd_ut;
    result["t3"] = value.t3_jd_ut;
    result["t4"] = value.t4_jd_ut;
    result["iteration_count"] = value.iteration_count;
    result["evaluation_count"] = value.evaluation_count;
    return result;
}

taiyin::runtime::SolarTransitSearchResult solar_transit_from_dict(const py::dict& value) {
    taiyin::runtime::SolarTransitSearchResult result;
    result.body_id = value["body_id"].cast<int>();
    result.kind = value["kind"].cast<uint32_t>();
    result.greatest_jd_ut = value["greatest"].cast<SplitJulianDate>();
    result.minimum_separation_rad = value["minimum_separation_radians"].cast<double>();
    result.sun_radius_rad = value["sun_radius_radians"].cast<double>();
    result.body_radius_rad = value["body_radius_radians"].cast<double>();
    result.t1_jd_ut = value["t1"].cast<SplitJulianDate>();
    result.t2_jd_ut = value["t2"].cast<SplitJulianDate>();
    result.t3_jd_ut = value["t3"].cast<SplitJulianDate>();
    result.t4_jd_ut = value["t4"].cast<SplitJulianDate>();
    result.iteration_count = value["iteration_count"].cast<int>();
    result.evaluation_count = value["evaluation_count"].cast<int>();
    return result;
}

py::dict local_solar_transit_to_dict(
    const taiyin::runtime::LocalSolarTransitSearchResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["global"] = solar_transit_to_dict(value.global);
    result["topocentric"] = solar_transit_to_dict(value.topocentric);
    result["visibility_flags"] = value.visibility_flags;
    result["contact_sun_altitude_degrees"] = py::make_tuple(
        value.contact_sun_altitude_deg[0], value.contact_sun_altitude_deg[1],
        value.contact_sun_altitude_deg[2], value.contact_sun_altitude_deg[3],
        value.contact_sun_altitude_deg[4]);
    result["contact_sun_azimuth_degrees"] = py::make_tuple(
        value.contact_sun_azimuth_deg[0], value.contact_sun_azimuth_deg[1],
        value.contact_sun_azimuth_deg[2], value.contact_sun_azimuth_deg[3],
        value.contact_sun_azimuth_deg[4]);
    result["sunrise"] = value.sunrise_jd_ut;
    result["sunset"] = value.sunset_jd_ut;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

SplitJulianDate optional_split_julian_date(const py::object& value) {
    return value.is_none() ? SplitJulianDate(0, NAN) : value.cast<SplitJulianDate>();
}

py::dict sidereal_position_to_dict(
    const taiyin::astrology::SiderealPosition& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["coordinate_frame_id"] = value.coordinate_frame_id;
    result["tropical_longitude_radians"] = value.tropical_longitude_rad;
    result["sidereal_longitude_radians"] = value.sidereal_longitude_rad;
    result["latitude_radians"] = value.latitude_rad;
    result["distance_au"] = value.distance_au;
    result["tropical_longitude_rate_radians_per_day"] = value.tropical_longitude_rate_rad_per_day;
    result["sidereal_longitude_rate_radians_per_day"] = value.sidereal_longitude_rate_rad_per_day;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict sidereal_coordinates_to_dict(
    const taiyin::astrology::SiderealCoordinates& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["coordinate_frame_id"] = value.coordinate_frame_id;
    result["position_flags"] = value.position_flags;
    result["values"] = std::vector<double>(value.values, value.values + 6);
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict lunar_node_to_dict(
    const taiyin::astrology::LunarNodePosition& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["reference_frame_id"] = value.reference_frame_id;
    result["longitude_radians"] = value.longitude_rad;
    result["longitude_rate_radians_per_day"] = value.longitude_rate_rad_per_day;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict lunar_apsis_to_dict(
    const taiyin::astrology::LunarApsisPosition& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["reference_frame_id"] = value.reference_frame_id;
    result["definition"] = static_cast<int>(value.definition);
    result["longitude_radians"] = value.longitude_rad;
    result["latitude_radians"] = value.latitude_rad;
    result["longitude_rate_radians_per_day"] = value.longitude_rate_rad_per_day;
    result["latitude_rate_radians_per_day"] = value.latitude_rate_rad_per_day;
    result["distance_au"] = value.distance_au;
    result["distance_rate_au_per_day"] = value.distance_rate_au_per_day;
    result["extrapolated"] = value.extrapolated;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict house_result_to_dict(const taiyin::astrology::HouseResult& value) {
    py::dict result;
    result["requested_system_id"] = value.requested_system_id;
    result["resolved_system_id"] = value.resolved_system_id;
    result["flags"] = value.flags;
    result["armc_radians"] = value.armc_rad;
    result["ascendant_radians"] = value.ascendant_rad;
    result["midheaven_radians"] = value.midheaven_rad;
    result["vertex_radians"] = value.vertex_rad;
    result["east_point_radians"] = value.east_point_rad;
    result["armc_rate_radians_per_day"] = value.armc_rate_rad_per_day;
    result["ascendant_rate_radians_per_day"] = value.ascendant_rate_rad_per_day;
    result["midheaven_rate_radians_per_day"] = value.midheaven_rate_rad_per_day;
    result["vertex_rate_radians_per_day"] = value.vertex_rate_rad_per_day;
    result["east_point_rate_radians_per_day"] = value.east_point_rate_rad_per_day;
    result["cusp_longitudes_radians"] = std::vector<double>(
        value.cusp_longitude_rad, value.cusp_longitude_rad + 12);
    result["cusp_longitude_rates_radians_per_day"] = std::vector<double>(
        value.cusp_longitude_rate_rad_per_day, value.cusp_longitude_rate_rad_per_day + 12);
    return result;
}

taiyin::astrology::HouseResult house_result_from_dict(const py::dict& value) {
    const std::vector<double> cusps = value["cusp_longitudes_radians"].cast<std::vector<double> >();
    if (cusps.size() != 12u) {
        throw py::value_error("houses.cusp_longitudes_radians must contain exactly 12 values");
    }
    taiyin::astrology::HouseResult result;
    for (std::size_t index = 0; index < cusps.size(); ++index) {
        result.cusp_longitude_rad[index] = cusps[index];
    }
    return result;
}

template <typename T>
py::dict visibility_event_to_dict(const T& value, const EphemerisEvalDiagnostic& diagnostic) {
    py::dict result;
    result["altitude_state"] = value.altitude_state;
    result["crossing_direction"] = value.crossing_direction;
    result["coordinate"] = value.jd_ut;
    result["residual_radians"] = value.residual_rad;
    result["minimum_residual_radians"] = value.min_residual_rad;
    result["maximum_residual_radians"] = value.max_residual_rad;
    result["minimum_residual_coordinate"] = value.min_residual_jd_ut;
    result["maximum_residual_coordinate"] = value.max_residual_jd_ut;
    result["sample_count"] = value.sample_count;
    result["refine_count"] = value.refine_count;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
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

class NativeChineseCalendarContext {
public:
    NativeChineseCalendarContext(
        const NativeCalcContext& astronomy,
        int rule_mode,
        int day_boundary_mode,
        int utc_offset_minutes,
        double calendar_meridian_deg
    ) {
        taiyin::chinese_calendar::ChineseCalendarConfig config;
        config.rule_mode = rule_mode;
        config.day_boundary_mode = day_boundary_mode;
        config.utc_offset_minutes = utc_offset_minutes;
        config.calendar_meridian_deg = calendar_meridian_deg;
        require_ok(taiyin::chinese_calendar::initialize_context(
            &context_, &astronomy, &config), "ChineseCalendarContext initialization");
    }

    std::vector<uint8_t> four_pillars(
        const SplitJulianDate& instant_utc,
        const taiyin::CalendarDateTime& virtual_time,
        int rat_hour_mode
    ) const {
        taiyin::chinese_calendar::GanzhiFourPillars result;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::calculate_four_pillars(
            &context_, instant_utc, virtual_time, rat_hour_mode, &result, &diagnostic),
            "ChineseCalendarContext.four_pillars");
        std::vector<uint8_t> values;
        values.push_back(result.year);
        values.push_back(result.month);
        values.push_back(result.day);
        values.push_back(result.hour);
        return values;
    }

    py::dict from_solar(int year, int month, int day) const {
        taiyin::chinese_calendar::SolarDate solar;
        solar.year = year;
        solar.month = static_cast<uint8_t>(month);
        solar.day = static_cast<uint8_t>(day);
        taiyin::chinese_calendar::LunarDate lunar;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::fromSolar(
            &context_, &solar, &lunar, &diagnostic), "ChineseCalendarContext.from_solar");
        py::dict result;
        result["year"] = lunar.year;
        result["month"] = lunar.month;
        result["day"] = lunar.day;
        result["is_leap"] = lunar.is_leap != 0;
        result["month_days"] = lunar.month_days;
        result["month_name"] = lunar.month_name;
        return result;
    }

    py::dict from_lunar(int year, int month, int day, bool is_leap, int month_name) const {
        taiyin::chinese_calendar::LunarDate lunar;
        lunar.year = year;
        lunar.month = static_cast<uint8_t>(month);
        lunar.day = static_cast<uint8_t>(day);
        lunar.is_leap = is_leap ? 1u : 0u;
        lunar.month_name = static_cast<uint8_t>(month_name);
        taiyin::chinese_calendar::SolarDate solar;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::fromLunar(
            &context_, &lunar, &solar, &diagnostic), "ChineseCalendarContext.from_lunar");
        py::dict result;
        result["year"] = solar.year;
        result["month"] = solar.month;
        result["day"] = solar.day;
        return result;
    }

    int month_days(int year, int month, bool is_leap) const {
        uint8_t result = 0;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::getLunarMonthNum(
            &context_, year, static_cast<uint8_t>(month), is_leap, &result, &diagnostic),
            "ChineseCalendarContext.get_month_days");
        return result;
    }

    py::dict specific_solar_term(int civil_year, int term_index) const {
        taiyin::chinese_calendar::SolarTermEvent result;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::getSpecificJieQi(
            &context_, civil_year, static_cast<uint8_t>(term_index), &result, &diagnostic),
            "ChineseCalendarContext.get_specific_jie_qi_ut");
        return solar_term_dict(result);
    }

    py::dict previous_jie_qi(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getPrevJieQi,
                                 "ChineseCalendarContext.get_prev_jie_qi_ut");
    }
    py::dict next_jie_qi(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getNextJieQi,
                                 "ChineseCalendarContext.get_next_jie_qi_ut");
    }
    py::dict previous_jie(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getPrevJie,
                                 "ChineseCalendarContext.get_prev_jie_ut");
    }
    py::dict next_jie(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getNextJie,
                                 "ChineseCalendarContext.get_next_jie_ut");
    }
    py::dict previous_qi(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getPrevQi,
                                 "ChineseCalendarContext.get_prev_qi_ut");
    }
    py::dict next_qi(const SplitJulianDate& jd_ut) const {
        return solar_term_search(jd_ut, &taiyin::chinese_calendar::getNextQi,
                                 "ChineseCalendarContext.get_next_qi_ut");
    }

    py::dict calendar_year(const SplitJulianDate& jd_ut) const {
        taiyin::chinese_calendar::ChineseCalendarYear value;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::calcY(&context_, jd_ut, &value, &diagnostic),
                   "ChineseCalendarContext.calc_year_ut");
        py::dict result;
        py::list terms;
        for (std::size_t index = 0; index < value.solar_term_count; ++index) {
            terms.append(solar_term_dict(value.solar_terms[index]));
        }
        py::list moons;
        for (std::size_t index = 0; index < value.new_moon_count; ++index) {
            py::dict moon;
            moon["jd_ut"] = value.new_moons[index].jd_ut;
            moon["civil_day_number"] = value.new_moons[index].civil_day_number;
            moons.append(moon);
        }
        py::list months;
        for (std::size_t index = 0; index < value.month_count; ++index) {
            const taiyin::chinese_calendar::ChineseCalendarMonth& month = value.months[index];
            py::dict mapped;
            mapped["lunar_year"] = month.lunar_year;
            mapped["month"] = month.month;
            mapped["is_leap"] = month.is_leap != 0;
            mapped["day_count"] = month.day_count;
            mapped["month_name"] = month.month_name;
            mapped["first_civil_day_number"] = month.first_civil_day_number;
            mapped["astronomical_new_moon_jd_ut"] = month.astronomical_new_moon_jd_ut;
            months.append(mapped);
        }
        result["solar_terms"] = terms;
        result["new_moons"] = moons;
        result["months"] = months;
        result["solar_term_count"] = value.solar_term_count;
        result["new_moon_count"] = value.new_moon_count;
        result["month_count"] = value.month_count;
        result["leap_month_index"] = value.leap_month_index;
        result["first_winter_solstice_day_number"] = value.first_winter_solstice_day_number;
        result["second_winter_solstice_day_number"] = value.second_winter_solstice_day_number;
        return result;
    }

private:
    typedef Status (*SolarTermSearchFn)(
        const taiyin::chinese_calendar::ChineseCalendarContext*,
        SplitJulianDate,
        taiyin::chinese_calendar::SolarTermEvent*,
        EphemerisEvalDiagnostic*
    );

    static py::dict solar_term_dict(const taiyin::chinese_calendar::SolarTermEvent& value) {
        py::dict result;
        result["index"] = value.index_from_winter_solstice;
        result["longitude"] = value.target_longitude_rad;
        result["jd_ut"] = value.jd_ut;
        result["civil_day_number"] = value.civil_day_number;
        return result;
    }

    py::dict solar_term_search(
        const SplitJulianDate& jd_ut,
        SolarTermSearchFn search,
        const char* operation
    ) const {
        taiyin::chinese_calendar::SolarTermEvent result;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(search(&context_, jd_ut, &result, &diagnostic), operation);
        return solar_term_dict(result);
    }

    taiyin::chinese_calendar::ChineseCalendarContext context_;
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
            return taiyin::seconds_between_split_jd(other, value);
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
        .def_readwrite("second", &taiyin::CalendarDateTime::second)
        .def("to_julian_date", [](const taiyin::CalendarDateTime& value) {
            SplitJulianDate result;
            if (!taiyin::julian_day_split(value, &result)) {
                throw py::value_error("invalid calendar date/time");
            }
            return result;
        });
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
            return position_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_tt", [](const NativeCalcContext& context, int target_id,
                                   const SplitJulianDate& jd_tt, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_tt(
                &context, target_id, jd_tt, flags, out, &diagnostic),
                "EphemerisContext.position_at_tt");
            return position_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_ut1", [](const NativeCalcContext& context, int target_id,
                                    const SplitJulianDate& jd_ut1, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_ut(
                &context, target_id, jd_ut1, flags, out, &diagnostic),
                "EphemerisContext.position_at_ut1");
            return position_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("position_at_ut1_with_delta_t", [](const NativeCalcContext& context, int target_id,
                                                 const SplitJulianDate& jd_ut1,
                                                 double delta_t_seconds, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_ut_delta_t(
                &context, target_id, jd_ut1, delta_t_seconds, flags, out, &diagnostic),
                "EphemerisContext.position_at_ut1_with_delta_t");
            return position_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("delta_t_seconds"), py::arg("flags") = 0)
        .def("position_at_utc", [](const NativeCalcContext& context, int target_id,
                                    const taiyin::CalendarDateTime& utc, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_position_utc(
                &context, target_id, utc, flags, out, &diagnostic),
                "EphemerisContext.position_at_utc");
            return position_result_to_dict(out, diagnostic);
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
            py::list result;
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.append(position_result_to_dict(&values[index * 6u], diagnostics[index]));
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
            py::list result;
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.append(position_result_to_dict(&values[index * 6u], diagnostics[index]));
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
            return state_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_tt", [](const NativeCalcContext& context, int target_id,
                                const SplitJulianDate& jd_tt, uint32_t flags) {
            CartesianState out;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_state_tt(
                &context, target_id, jd_tt, flags, &out, &diagnostic),
                "EphemerisContext.state_at_tt");
            return state_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_ut1", [](const NativeCalcContext& context, int target_id,
                                 const SplitJulianDate& jd_ut1, uint32_t flags) {
            CartesianState out;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_state_ut(
                &context, target_id, jd_ut1, flags, &out, &diagnostic),
                "EphemerisContext.state_at_ut1");
            return state_result_to_dict(out, diagnostic);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("equation_of_time_at_ut1", [](const NativeCalcContext& context,
                                             const SplitJulianDate& jd_ut1) {
            taiyin::runtime::EquationOfTimeResult result;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_equation_of_time_ut(
                &context, jd_ut1, &result, &diagnostic),
                "EphemerisContext.equation_of_time_at_ut1");
            return equation_of_time_to_dict(result, diagnostic);
        }, py::arg("jd_ut1"))
        .def("equation_of_time_at_tt", [](const NativeCalcContext& context,
                                            const SplitJulianDate& jd_tt) {
            taiyin::runtime::EquationOfTimeResult result;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_equation_of_time_tt(
                &context, jd_tt, &result, &diagnostic),
                "EphemerisContext.equation_of_time_at_tt");
            return equation_of_time_to_dict(result, diagnostic);
        }, py::arg("jd_tt"))
        .def("local_mean_to_apparent_solar_time", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& local_mean,
                                                       double longitude_radians) {
            SplitJulianDate result;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::local_mean_to_apparent_solar_time(
                &context, local_mean, longitude_radians, &result, &diagnostic),
                "EphemerisContext.local_mean_to_apparent_solar_time");
            py::dict mapped;
            mapped["coordinate"] = result;
            mapped["diagnostic"] = diagnostic_to_dict(diagnostic);
            return mapped;
        }, py::arg("local_mean"), py::arg("longitude_radians"))
        .def("local_apparent_to_mean_solar_time", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& local_apparent,
                                                       double longitude_radians) {
            SplitJulianDate result;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::local_apparent_to_mean_solar_time(
                &context, local_apparent, longitude_radians, &result, &diagnostic),
                "EphemerisContext.local_apparent_to_mean_solar_time");
            py::dict mapped;
            mapped["coordinate"] = result;
            mapped["diagnostic"] = diagnostic_to_dict(diagnostic);
            return mapped;
        }, py::arg("local_apparent"), py::arg("longitude_radians"))
        .def("recommended_longitude_search_step_days", [](const NativeCalcContext&, int body_id) {
            return taiyin::runtime::recommended_longitude_search_step_days(body_id);
        })
        .def("recommended_aspect_search_step_days", [](const NativeCalcContext&, int body_a_id, int body_b_id) {
            return taiyin::runtime::recommended_aspect_search_step_days(body_a_id, body_b_id);
        })
        .def("solar_longitude_at_ut1", [](const NativeCalcContext& context, double target,
                                            const SplitJulianDate& estimate, uint64_t flags) {
            return event_scalar(context, &taiyin::runtime::search_solar_longitude_ut,
                                target, estimate, flags, "Events.solar_longitude_at_ut1");
        })
        .def("solar_longitude_at_tt", [](const NativeCalcContext& context, double target,
                                           const SplitJulianDate& estimate, uint64_t flags) {
            return event_scalar(context, &taiyin::runtime::search_solar_longitude_tt,
                                target, estimate, flags, "Events.solar_longitude_at_tt");
        })
        .def("moon_longitude_at_ut1", [](const NativeCalcContext& context, double target,
                                           const SplitJulianDate& estimate, uint64_t flags) {
            return event_scalar(context, &taiyin::runtime::search_moon_longitude_ut,
                                target, estimate, flags, "Events.moon_longitude_at_ut1");
        })
        .def("moon_longitude_at_tt", [](const NativeCalcContext& context, double target,
                                          const SplitJulianDate& estimate, uint64_t flags) {
            return event_scalar(context, &taiyin::runtime::search_moon_longitude_tt,
                                target, estimate, flags, "Events.moon_longitude_at_tt");
        })
        .def("longitude_crossings_at_ut1", [](const NativeCalcContext& context, int body_id,
                                                double target, const SplitJulianDate& start,
                                                const SplitJulianDate& end, double max_step_days,
                                                uint64_t flags, size_t capacity) {
            return event_dates(context, &taiyin::runtime::search_body_longitude_crossings_ut,
                               body_id, target, start, end, max_step_days, flags, capacity,
                               "Events.longitude_crossings_at_ut1");
        })
        .def("longitude_crossings_at_tt", [](const NativeCalcContext& context, int body_id,
                                               double target, const SplitJulianDate& start,
                                               const SplitJulianDate& end, double max_step_days,
                                               uint64_t flags, size_t capacity) {
            return event_dates(context, &taiyin::runtime::search_body_longitude_crossings_tt,
                               body_id, target, start, end, max_step_days, flags, capacity,
                               "Events.longitude_crossings_at_tt");
        })
        .def("longitude_stations_at_ut1", [](const NativeCalcContext& context, int body_id,
                                               const SplitJulianDate& start, const SplitJulianDate& end,
                                               double max_step_days, uint64_t flags, size_t capacity) {
            return event_stations(context, &taiyin::runtime::search_body_longitude_stations_ut,
                                  body_id, start, end, max_step_days, flags, capacity,
                                  "Events.longitude_stations_at_ut1");
        })
        .def("longitude_stations_at_tt", [](const NativeCalcContext& context, int body_id,
                                              const SplitJulianDate& start, const SplitJulianDate& end,
                                              double max_step_days, uint64_t flags, size_t capacity) {
            return event_stations(context, &taiyin::runtime::search_body_longitude_stations_tt,
                                  body_id, start, end, max_step_days, flags, capacity,
                                  "Events.longitude_stations_at_tt");
        })
        .def("aspect_crossings_at_ut1", [](const NativeCalcContext& context, int body_a_id,
                                             int body_b_id, double aspect, const SplitJulianDate& start,
                                             const SplitJulianDate& end, double max_step_days,
                                             uint64_t flags, size_t capacity) {
            return event_aspects(context, &taiyin::runtime::search_body_aspect_crossings_ut,
                                 body_a_id, body_b_id, aspect, start, end, max_step_days, flags,
                                 capacity, "Events.aspect_crossings_at_ut1");
        })
        .def("aspect_crossings_at_tt", [](const NativeCalcContext& context, int body_a_id,
                                            int body_b_id, double aspect, const SplitJulianDate& start,
                                            const SplitJulianDate& end, double max_step_days,
                                            uint64_t flags, size_t capacity) {
            return event_aspects(context, &taiyin::runtime::search_body_aspect_crossings_tt,
                                 body_a_id, body_b_id, aspect, start, end, max_step_days, flags,
                                 capacity, "Events.aspect_crossings_at_tt");
        })
        .def("exact_aspects_at_ut1", [](const NativeCalcContext& context, int body_a_id,
                                         int body_b_id, const std::vector<double>& aspects,
                                         const SplitJulianDate& start, const SplitJulianDate& end,
                                         double max_step_days, uint64_t flags, size_t capacity) {
            return event_exact_aspects(context, &taiyin::runtime::search_body_exact_aspects_ut,
                                       body_a_id, body_b_id, aspects, start, end, max_step_days, flags,
                                       capacity, "Events.exact_aspects_at_ut1");
        })
        .def("exact_aspects_at_tt", [](const NativeCalcContext& context, int body_a_id,
                                        int body_b_id, const std::vector<double>& aspects,
                                        const SplitJulianDate& start, const SplitJulianDate& end,
                                        double max_step_days, uint64_t flags, size_t capacity) {
            return event_exact_aspects(context, &taiyin::runtime::search_body_exact_aspects_tt,
                                       body_a_id, body_b_id, aspects, start, end, max_step_days, flags,
                                       capacity, "Events.exact_aspects_at_tt");
        })
        .def("lunar_phase_crossings_at_ut1", [](const NativeCalcContext& context, double phase,
                                                  const SplitJulianDate& start, const SplitJulianDate& end,
                                                  double max_step_days, uint64_t flags, size_t capacity) {
            return event_phases(context, &taiyin::runtime::search_lunar_phase_crossings_ut,
                                phase, start, end, max_step_days, flags, capacity,
                                "Events.lunar_phase_crossings_at_ut1");
        })
        .def("lunar_phase_crossings_at_tt", [](const NativeCalcContext& context, double phase,
                                                 const SplitJulianDate& start, const SplitJulianDate& end,
                                                 double max_step_days, uint64_t flags, size_t capacity) {
            return event_phases(context, &taiyin::runtime::search_lunar_phase_crossings_tt,
                                phase, start, end, max_step_days, flags, capacity,
                                "Events.lunar_phase_crossings_at_tt");
        })
        .def("set_geocentric_observer", [](NativeCalcContext& context,
                                             int observer_id, int center_id) {
            require_ok(taiyin::runtime::native_context_set_geocentric_observer(
                &context, observer_id, center_id), "ContextConfiguration.set_geocentric_observer");
        })
        .def("set_observer_location", [](NativeCalcContext& context,
                                           double longitude_degrees, double latitude_degrees,
                                           double height_meters) {
            require_ok(taiyin::runtime::native_context_set_observer_location(
                &context, taiyin::runtime::native_observer_location_degrees(
                    longitude_degrees, latitude_degrees, height_meters)),
                "ContextConfiguration.set_observer_location");
        })
        .def("set_standard_atmosphere", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_set_atmosphere(
                &context, taiyin::runtime::native_standard_atmosphere()),
                "ContextConfiguration.set_standard_atmosphere");
        })
        .def("use_solar_deflector", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_use_solar_deflector(&context),
                       "ContextConfiguration.use_solar_deflector");
        })
        .def("set_apparent_config", [](NativeCalcContext& context, uint32_t flags,
                                         int output_frame_id) {
            context.apparent_options.flags = flags;
            context.apparent_options.output_frame_id = output_frame_id;
        })
        .def("set_route_rule", [](NativeCalcContext& context, uint64_t route_rule_id) {
            require_ok(taiyin::runtime::native_context_set_route_rule(&context, route_rule_id),
                       "ContextConfiguration.set_route_rule");
        })
        .def("greatest_elongation_at_ut1", [](const NativeCalcContext& context, int body_id,
                                               const SplitJulianDate& start, const SplitJulianDate& end,
                                               uint64_t flags) {
            taiyin::runtime::GreatestElongationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_greatest_elongation_ut(
                &context, body_id, start, end, flags, &value, &diagnostic),
                "Events.greatest_elongation_at_ut1");
            py::dict result;
            result["body_id"] = value.body_id;
            result["coordinate"] = value.jd_ut;
            result["elongation_radians"] = value.elongation_rad;
            result["relative_longitude_radians"] = value.relative_longitude_rad;
            result["kind"] = value.kind;
            result["iteration_count"] = value.iteration_count;
            result["evaluation_count"] = value.evaluation_count;
            py::dict phenomena;
            phenomena["phase_angle_radians"] = value.phenomena.phase_angle_rad;
            phenomena["illuminated_fraction"] = value.phenomena.illuminated_fraction;
            phenomena["solar_elongation_radians"] = value.phenomena.solar_elongation_rad;
            phenomena["apparent_diameter_radians"] = value.phenomena.apparent_diameter_rad;
            phenomena["apparent_magnitude"] = value.phenomena.apparent_magnitude;
            phenomena["horizontal_parallax_radians"] = value.phenomena.horizontal_parallax_rad;
            result["phenomena"] = phenomena;
            result["diagnostic"] = diagnostic_to_dict(diagnostic);
            return result;
        })
        .def("minimum_angular_separation_at_ut1", [](const NativeCalcContext& context,
                                                       int body_a_id, int body_b_id,
                                                       const SplitJulianDate& start,
                                                       const SplitJulianDate& end,
                                                       double max_step_days, uint64_t flags) {
            taiyin::runtime::AngularSeparationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_minimum_angular_separation_ut(
                &context, body_a_id, body_b_id, start, end, max_step_days, flags,
                &value, &diagnostic), "Events.minimum_angular_separation_at_ut1");
            py::dict result;
            result["body_a_id"] = value.body_a_id;
            result["body_b_id"] = value.body_b_id;
            result["coordinate"] = value.jd;
            result["separation_radians"] = value.separation_rad;
            result["separation_rate_radians_per_day"] = value.separation_rate_rad_per_day;
            result["iteration_count"] = value.iteration_count;
            result["evaluation_count"] = value.evaluation_count;
            result["diagnostic"] = diagnostic_to_dict(diagnostic);
            return result;
        })
        .def("minimum_angular_separation_at_tt", [](const NativeCalcContext& context,
                                                      int body_a_id, int body_b_id,
                                                      const SplitJulianDate& start,
                                                      const SplitJulianDate& end,
                                                      double max_step_days, uint64_t flags) {
            taiyin::runtime::AngularSeparationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_minimum_angular_separation_tt(
                &context, body_a_id, body_b_id, start, end, max_step_days, flags,
                &value, &diagnostic), "Events.minimum_angular_separation_at_tt");
            py::dict result;
            result["body_a_id"] = value.body_a_id;
            result["body_b_id"] = value.body_b_id;
            result["coordinate"] = value.jd;
            result["separation_radians"] = value.separation_rad;
            result["separation_rate_radians_per_day"] = value.separation_rate_rad_per_day;
            result["iteration_count"] = value.iteration_count;
            result["evaluation_count"] = value.evaluation_count;
            result["diagnostic"] = diagnostic_to_dict(diagnostic);
            return result;
        })
        .def("next_solar_transit_at_ut1", [](const NativeCalcContext& context, int body_id,
                                               const SplitJulianDate& start, uint64_t flags) {
            taiyin::runtime::SolarTransitSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_solar_transit_ut(
                &context, body_id, start, flags, &value, &diagnostic),
                "Events.next_solar_transit_at_ut1");
            py::dict result = solar_transit_to_dict(value);
            result["diagnostic"] = diagnostic_to_dict(diagnostic);
            return result;
        })
        .def("local_solar_transit_at_ut1", [](const NativeCalcContext& context,
                                                const py::dict& global_transit,
                                                double longitude_degrees, double latitude_degrees,
                                                double height_meters, uint64_t flags) {
            taiyin::runtime::SolarTransitSearchResult source = solar_transit_from_dict(global_transit);
            taiyin::runtime::LocalSolarTransitSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_local_solar_transit_ut(
                &context, &source, longitude_degrees, latitude_degrees, height_meters, flags,
                &value, &diagnostic), "Events.local_solar_transit_at_ut1");
            return local_solar_transit_to_dict(value, diagnostic);
        })
        .def("next_local_solar_transit_at_ut1", [](const NativeCalcContext& context, int body_id,
                                                     const SplitJulianDate& start,
                                                     double longitude_degrees, double latitude_degrees,
                                                     double height_meters, uint64_t flags) {
            taiyin::runtime::LocalSolarTransitSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_local_solar_transit_ut(
                &context, body_id, start, longitude_degrees, latitude_degrees, height_meters,
                flags, &value, &diagnostic), "Events.next_local_solar_transit_at_ut1");
            return local_solar_transit_to_dict(value, diagnostic);
        })
        .def("moon_rise_set_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& start,
                                          const SplitJulianDate& end, int event, int limb,
                                          py::object horizon, uint64_t flags) {
            taiyin::runtime::MoonVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            const Status status = horizon.is_none()
                ? taiyin::runtime::search_moon_rise_set_ut(&context, start, end, event, limb, flags, &value, &diagnostic)
                : taiyin::runtime::search_moon_rise_set_at_horizon_ut(&context, start, end, event, limb,
                    horizon.cast<double>(), flags, &value, &diagnostic);
            require_ok(status, "Visibility.moon_rise_set_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("moon_transit_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& start,
                                         const SplitJulianDate& end, int event) {
            taiyin::runtime::MoonVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_moon_transit_ut(&context, start, end, event, &value, &diagnostic),
                       "Visibility.moon_transit_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("planet_rise_set_at_ut1", [](const NativeCalcContext& context, int body, const SplitJulianDate& start,
                                            const SplitJulianDate& end, int event, int limb,
                                            py::object horizon, uint64_t flags) {
            taiyin::runtime::PlanetVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            const Status status = horizon.is_none()
                ? taiyin::runtime::search_planet_rise_set_ut(&context, body, start, end, event, limb, flags, &value, &diagnostic)
                : taiyin::runtime::search_planet_rise_set_at_horizon_ut(&context, body, start, end, event, limb,
                    horizon.cast<double>(), flags, &value, &diagnostic);
            require_ok(status, "Visibility.planet_rise_set_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("planet_transit_at_ut1", [](const NativeCalcContext& context, int body, const SplitJulianDate& start,
                                           const SplitJulianDate& end, int event) {
            taiyin::runtime::PlanetVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_planet_transit_ut(&context, body, start, end, event, &value, &diagnostic),
                       "Visibility.planet_transit_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("solar_rise_set_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& start,
                                           const SplitJulianDate& end, int event, int limb,
                                           py::object horizon, uint64_t flags) {
            taiyin::runtime::SolarVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            const Status status = horizon.is_none()
                ? taiyin::runtime::search_solar_rise_set_ut(&context, start, end, event, limb, flags, &value, &diagnostic)
                : taiyin::runtime::search_solar_rise_set_at_horizon_ut(&context, start, end, event, limb,
                    horizon.cast<double>(), flags, &value, &diagnostic);
            require_ok(status, "Visibility.solar_rise_set_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("solar_twilight_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& start,
                                           const SplitJulianDate& end, int event, int twilight) {
            taiyin::runtime::SolarVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_solar_twilight_ut(&context, start, end, event, twilight, &value, &diagnostic),
                       "Visibility.solar_twilight_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("solar_transit_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& start,
                                          const SplitJulianDate& end, int event) {
            taiyin::runtime::SolarVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_solar_transit_ut(&context, start, end, event, &value, &diagnostic),
                       "Visibility.solar_transit_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("solar_rise_set_fast_at_tt", [](const NativeCalcContext& context, const SplitJulianDate& center,
                                               double longitude, double latitude, double height, int limb,
                                               double horizon, uint64_t flags) {
            taiyin::runtime::SolarRiseSetFastResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_solar_rise_set_fast_tt(&context, center, longitude, latitude,
                height, limb, horizon, flags, &value, &diagnostic), "Visibility.solar_rise_set_fast_at_tt");
            py::dict result; result["altitude_state"] = value.altitude_state; result["rise"] = value.rise_jd_tt;
            result["set"] = value.set_jd_tt; result["sample_count"] = value.sample_count;
            result["refine_count"] = value.refine_count; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        })
        .def("solar_transit_fast_at_tt", [](const NativeCalcContext& context, const SplitJulianDate& center,
                                              double longitude, double latitude, double height) {
            taiyin::runtime::SolarTransitFastResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_solar_transit_fast_tt(&context, center, longitude, latitude,
                height, &value, &diagnostic), "Visibility.solar_transit_fast_at_tt");
            py::dict result; result["coordinate"] = value.transit_jd_tt; result["altitude_radians"] = value.altitude_rad;
            result["azimuth_radians"] = value.azimuth_rad; result["sample_count"] = value.sample_count;
            result["refine_count"] = value.refine_count; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        })
        .def("star_rise_set_at_ut1", [](const NativeCalcContext& context, const std::string& star, const SplitJulianDate& start,
                                          const SplitJulianDate& end, int event, py::object horizon, uint64_t flags) {
            taiyin::runtime::StarVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            const Status status = horizon.is_none()
                ? taiyin::runtime::search_star_rise_set_ut(&context, star.c_str(), start, end, event, flags, &value, &diagnostic)
                : taiyin::runtime::search_star_rise_set_at_horizon_ut(&context, star.c_str(), start, end, event,
                    horizon.cast<double>(), flags, &value, &diagnostic);
            require_ok(status, "Visibility.star_rise_set_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("star_transit_at_ut1", [](const NativeCalcContext& context, const std::string& star, const SplitJulianDate& start,
                                         const SplitJulianDate& end, int event) {
            taiyin::runtime::StarVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_star_transit_ut(&context, star.c_str(), start, end, event, &value, &diagnostic),
                       "Visibility.star_transit_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        })
        .def("phenomena_at_tt", [](const NativeCalcContext& context, int body, const SplitJulianDate& tt, uint64_t flags) {
            taiyin::runtime::BodyPhenomena value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_phenomena_tt(&context, body, tt, flags, &value, &diagnostic), "Phenomena.at_tt");
            py::dict out; out["phase_angle_radians"] = value.phase_angle_rad; out["illuminated_fraction"] = value.illuminated_fraction;
            out["solar_elongation_radians"] = value.solar_elongation_rad; out["apparent_diameter_radians"] = value.apparent_diameter_rad;
            out["apparent_magnitude"] = value.apparent_magnitude; out["horizontal_parallax_radians"] = value.horizontal_parallax_rad;
            out["diagnostic"] = diagnostic_to_dict(diagnostic); return out;
        })
        .def("phenomena_at_ut1", [](const NativeCalcContext& context, int body, const SplitJulianDate& ut1, uint64_t flags) {
            taiyin::runtime::BodyPhenomena value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_phenomena_ut(&context, body, ut1, flags, &value, &diagnostic), "Phenomena.at_ut1");
            py::dict out; out["phase_angle_radians"] = value.phase_angle_rad; out["illuminated_fraction"] = value.illuminated_fraction;
            out["solar_elongation_radians"] = value.solar_elongation_rad; out["apparent_diameter_radians"] = value.apparent_diameter_rad;
            out["apparent_magnitude"] = value.apparent_magnitude; out["horizontal_parallax_radians"] = value.horizontal_parallax_rad;
            out["diagnostic"] = diagnostic_to_dict(diagnostic); return out;
        })
        .def("has_ayanamsha_model", [](const NativeCalcContext&, int model_id) {
            return taiyin::astrology::has_ayanamsha_model(model_id);
        })
        .def("has_house_system_model", [](const NativeCalcContext&, int model_id) {
            return taiyin::astrology::has_house_system_model(model_id);
        })
        .def("ayanamsha_at_tt", [](const NativeCalcContext& context, int model_id,
                                    const SplitJulianDate& jd_tt, uint64_t flags) {
            double value = NAN;
            require_ok(taiyin::astrology::calc_ayanamsha_tt(
                &context, model_id, jd_tt, flags, &value), "Astrology.ayanamsha_at_tt");
            return value;
        })
        .def("sidereal_position_at_tt", [](const NativeCalcContext& context, int model_id,
                                             int body_id, const SplitJulianDate& jd_tt,
                                             uint64_t flags, py::object reference_epoch) {
            taiyin::astrology::SiderealPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_sidereal_position_tt(
                &context, model_id, body_id, jd_tt, flags, &value, &diagnostic,
                optional_split_julian_date(reference_epoch)), "Astrology.sidereal_position_at_tt");
            return sidereal_position_to_dict(value, diagnostic);
        }, py::arg("model_id"), py::arg("body_id"), py::arg("jd_tt"),
           py::arg("flags") = 0, py::arg("reference_epoch") = py::none())
        .def("sidereal_position_at_ut1", [](const NativeCalcContext& context, int model_id,
                                              int body_id, const SplitJulianDate& jd_ut1,
                                              uint64_t flags, py::object reference_epoch) {
            taiyin::astrology::SiderealPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_sidereal_position_ut(
                &context, model_id, body_id, jd_ut1, flags, &value, &diagnostic,
                optional_split_julian_date(reference_epoch)), "Astrology.sidereal_position_at_ut1");
            return sidereal_position_to_dict(value, diagnostic);
        }, py::arg("model_id"), py::arg("body_id"), py::arg("jd_ut1"),
           py::arg("flags") = 0, py::arg("reference_epoch") = py::none())
        .def("sidereal_coordinates_at_tt", [](const NativeCalcContext& context, int model_id,
                                                int body_id, const SplitJulianDate& jd_tt,
                                                uint64_t flags, py::object reference_epoch) {
            taiyin::astrology::SiderealCoordinates value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_sidereal_coordinates_tt(
                &context, model_id, body_id, jd_tt, flags, &value, &diagnostic,
                optional_split_julian_date(reference_epoch)), "Astrology.sidereal_coordinates_at_tt");
            return sidereal_coordinates_to_dict(value, diagnostic);
        }, py::arg("model_id"), py::arg("body_id"), py::arg("jd_tt"),
           py::arg("flags") = 0, py::arg("reference_epoch") = py::none())
        .def("sidereal_coordinates_at_ut1", [](const NativeCalcContext& context, int model_id,
                                                 int body_id, const SplitJulianDate& jd_ut1,
                                                 uint64_t flags, py::object reference_epoch) {
            taiyin::astrology::SiderealCoordinates value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_sidereal_coordinates_ut(
                &context, model_id, body_id, jd_ut1, flags, &value, &diagnostic,
                optional_split_julian_date(reference_epoch)), "Astrology.sidereal_coordinates_at_ut1");
            return sidereal_coordinates_to_dict(value, diagnostic);
        }, py::arg("model_id"), py::arg("body_id"), py::arg("jd_ut1"),
           py::arg("flags") = 0, py::arg("reference_epoch") = py::none())
        .def("houses_from_armc", [](const NativeCalcContext&, double armc, double latitude,
                                     double obliquity, int model_id) {
            taiyin::astrology::HouseResult value;
            require_ok(taiyin::astrology::calc_houses_from_armc(
                armc, latitude, obliquity, model_id, &value), "Astrology.houses_from_armc");
            return house_result_to_dict(value);
        })
        .def("houses_at_ut1", [](const NativeCalcContext& context, const SplitJulianDate& jd_ut1,
                                   int model_id) {
            taiyin::astrology::HouseResult value;
            require_ok(taiyin::astrology::calc_houses_ut(
                &context, jd_ut1, model_id, &value), "Astrology.houses_at_ut1");
            return house_result_to_dict(value);
        })
        .def("houses_at_tt", [](const NativeCalcContext& context, const SplitJulianDate& jd_tt,
                                  int model_id) {
            taiyin::astrology::HouseResult value;
            require_ok(taiyin::astrology::calc_houses_tt(
                &context, jd_tt, model_id, &value), "Astrology.houses_at_tt");
            return house_result_to_dict(value);
        })
        .def("house_position_of", [](const NativeCalcContext&, const py::dict& houses,
                                       double longitude_radians) {
            const taiyin::astrology::HouseResult native_houses = house_result_from_dict(houses);
            taiyin::astrology::HousePositionResult value;
            require_ok(taiyin::astrology::calc_house_position_from_longitude(
                &native_houses, longitude_radians, &value), "Astrology.house_position_of");
            py::dict result;
            result["house_number"] = value.house_number;
            result["fraction"] = value.fraction;
            result["continuous_house_position"] = value.continuous_house_position;
            return result;
        })
        .def("lunar_true_node_at_tt", [](const NativeCalcContext& context,
                                           const SplitJulianDate& jd_tt, int kind, uint32_t flags) {
            taiyin::astrology::LunarNodePosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_true_node_tt(
                &context, jd_tt, static_cast<taiyin::astrology::LunarNodeKind>(kind), flags,
                &value, &diagnostic), "Astrology.lunar_true_node_at_tt");
            return lunar_node_to_dict(value, diagnostic);
        })
        .def("lunar_true_node_at_ut1", [](const NativeCalcContext& context,
                                            const SplitJulianDate& jd_ut1, int kind, uint32_t flags) {
            taiyin::astrology::LunarNodePosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_true_node_ut(
                &context, jd_ut1, static_cast<taiyin::astrology::LunarNodeKind>(kind), flags,
                &value, &diagnostic), "Astrology.lunar_true_node_at_ut1");
            return lunar_node_to_dict(value, diagnostic);
        })
        .def("lunar_mean_node_at_tt", [](const NativeCalcContext& context,
                                           const SplitJulianDate& jd_tt, int kind, uint32_t flags) {
            taiyin::astrology::LunarNodePosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_mean_node_tt(
                &context, jd_tt, static_cast<taiyin::astrology::LunarNodeKind>(kind), flags,
                &value, &diagnostic), "Astrology.lunar_mean_node_at_tt");
            return lunar_node_to_dict(value, diagnostic);
        })
        .def("lunar_mean_node_at_ut1", [](const NativeCalcContext& context,
                                            const SplitJulianDate& jd_ut1, int kind, uint32_t flags) {
            taiyin::astrology::LunarNodePosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_mean_node_ut(
                &context, jd_ut1, static_cast<taiyin::astrology::LunarNodeKind>(kind), flags,
                &value, &diagnostic), "Astrology.lunar_mean_node_at_ut1");
            return lunar_node_to_dict(value, diagnostic);
        })
        .def("lunar_mean_apogee_at_tt", [](const NativeCalcContext& context,
                                             const SplitJulianDate& jd_tt, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_mean_apogee_tt(
                &context, jd_tt, flags, &value, &diagnostic), "Astrology.lunar_mean_apogee_at_tt");
            return lunar_apsis_to_dict(value, diagnostic);
        })
        .def("lunar_mean_apogee_at_ut1", [](const NativeCalcContext& context,
                                              const SplitJulianDate& jd_ut1, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_mean_apogee_ut(
                &context, jd_ut1, flags, &value, &diagnostic), "Astrology.lunar_mean_apogee_at_ut1");
            return lunar_apsis_to_dict(value, diagnostic);
        })
        .def("lunar_osculating_apogee_at_tt", [](const NativeCalcContext& context,
                                                   const SplitJulianDate& jd_tt, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_osculating_apogee_tt(
                &context, jd_tt, flags, &value, &diagnostic),
                "Astrology.lunar_osculating_apogee_at_tt");
            return lunar_apsis_to_dict(value, diagnostic);
        })
        .def("lunar_osculating_apogee_at_ut1", [](const NativeCalcContext& context,
                                                    const SplitJulianDate& jd_ut1, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_osculating_apogee_ut(
                &context, jd_ut1, flags, &value, &diagnostic),
                "Astrology.lunar_osculating_apogee_at_ut1");
            return lunar_apsis_to_dict(value, diagnostic);
        })
        .def("lunar_fitted_apogee_at_tt", [](const NativeCalcContext& context,
                                               const SplitJulianDate& jd_tt, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_fitted_apogee_tt(
                &context, jd_tt, flags, &value, &diagnostic), "Astrology.lunar_fitted_apogee_at_tt");
            return lunar_apsis_to_dict(value, diagnostic);
        })
        .def("lunar_fitted_apogee_at_ut1", [](const NativeCalcContext& context,
                                                const SplitJulianDate& jd_ut1, uint32_t flags) {
            taiyin::astrology::LunarApsisPosition value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::astrology::calc_lunar_fitted_apogee_ut(
                &context, jd_ut1, flags, &value, &diagnostic), "Astrology.lunar_fitted_apogee_at_ut1");
            return lunar_apsis_to_dict(value, diagnostic);
        });
    py::class_<NativeChineseCalendarContext>(module, "_ChineseCalendarContext")
        .def("four_pillars", &NativeChineseCalendarContext::four_pillars,
             py::arg("instant_utc"), py::arg("virtual_time"), py::arg("rat_hour_mode") = 0)
        .def("from_solar", &NativeChineseCalendarContext::from_solar)
        .def("from_lunar", &NativeChineseCalendarContext::from_lunar,
             py::arg("year"), py::arg("month"), py::arg("day"),
             py::arg("is_leap"), py::arg("month_name") = 0)
        .def("get_month_days", &NativeChineseCalendarContext::month_days)
        .def("get_specific_jie_qi_ut", &NativeChineseCalendarContext::specific_solar_term)
        .def("get_prev_jie_qi_ut", &NativeChineseCalendarContext::previous_jie_qi)
        .def("get_next_jie_qi_ut", &NativeChineseCalendarContext::next_jie_qi)
        .def("get_prev_jie_ut", &NativeChineseCalendarContext::previous_jie)
        .def("get_next_jie_ut", &NativeChineseCalendarContext::next_jie)
        .def("get_prev_qi_ut", &NativeChineseCalendarContext::previous_qi)
        .def("get_next_qi_ut", &NativeChineseCalendarContext::next_qi)
        .def("calc_year_ut", &NativeChineseCalendarContext::calendar_year);
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
    module.def("_estimated_delta_t_for_decimal_year", [](double value) {
        if (!std::isfinite(value)) throw py::value_error("decimal year must be finite");
        return taiyin::estimated_delta_t_seconds_for_decimal_year(value);
    });
    module.def("_tai_minus_utc", [](const taiyin::CalendarDateTime& value) {
        double result = 0.0;
        if (!taiyin::tai_minus_utc_seconds_from_utc(value, &result)) {
            throw py::value_error("UTC date is outside the leap-second table");
        }
        return result;
    });
    module.def("_delta_t", [](double tai_minus_utc_seconds, double dut1_seconds) {
        if (!std::isfinite(tai_minus_utc_seconds) || !std::isfinite(dut1_seconds)) {
            throw py::value_error("time offsets must be finite");
        }
        return taiyin::delta_t_from_tai_minus_utc_and_dut1(
            tai_minus_utc_seconds, dut1_seconds);
    });
    module.def("_julian_day", [](const taiyin::CalendarDateTime& value) {
        SplitJulianDate result;
        if (!taiyin::julian_day_split(value, &result)) {
            throw py::value_error("invalid calendar date/time");
        }
        return result;
    });
    module.def("_reverse_julian_day", [](const SplitJulianDate& value) {
        taiyin::CalendarDateTime result;
        if (!taiyin::reverse_julian_day_split(value, &result)) {
            throw py::value_error("invalid Julian date");
        }
        return result;
    });
    module.def("_decimal_year", [](const SplitJulianDate& value) {
        return taiyin::decimal_year_from_jd(value);
    });
    module.def("_julian_centuries_since_j2000", [](const SplitJulianDate& value) {
        return taiyin::julian_centuries_from_j2000(value);
    });
    module.def("_julian_millennia_since_j2000", [](const SplitJulianDate& value) {
        return taiyin::julian_millennia_from_j2000(value);
    });
    module.def("_utc_to_tai", [](const SplitJulianDate& value, double offset_seconds) {
        SplitJulianDate result;
        if (!taiyin::utc_to_tai_split_jd(value, offset_seconds, &result)) {
            throw py::value_error("invalid UTC Julian date or offset");
        }
        return result;
    });
    module.def("_tai_to_tt", [](const SplitJulianDate& value) {
        SplitJulianDate result;
        if (!taiyin::tai_to_tt_split_jd(value, &result)) throw py::value_error("invalid TAI Julian date");
        return result;
    });
    module.def("_utc_to_tt", [](const SplitJulianDate& value, double offset_seconds) {
        SplitJulianDate result;
        if (!taiyin::utc_to_tt_split_jd(value, offset_seconds, &result)) {
            throw py::value_error("invalid UTC Julian date or offset");
        }
        return result;
    });
    module.def("_utc_to_ut1", [](const SplitJulianDate& value, double dut1_seconds) {
        SplitJulianDate result;
        if (!taiyin::utc_to_ut1_split_jd(value, dut1_seconds, &result)) {
            throw py::value_error("invalid UTC Julian date or DUT1");
        }
        return result;
    });
    module.def("_tt_to_ut1", [](const SplitJulianDate& value, double delta_t_seconds) {
        SplitJulianDate result;
        if (!taiyin::tt_to_ut1_split_jd(value, delta_t_seconds, &result)) {
            throw py::value_error("invalid TT Julian date or Delta-T");
        }
        return result;
    });
    module.def("_ut1_to_tt", [](const SplitJulianDate& value, double delta_t_seconds) {
        SplitJulianDate result;
        if (!taiyin::ut1_to_tt_split_jd(value, delta_t_seconds, &result)) {
            throw py::value_error("invalid UT1 Julian date or Delta-T");
        }
        return result;
    });
    module.def("_precise_scales_from_utc", [](const taiyin::CalendarDateTime& value,
                                                double tai_minus_utc_seconds,
                                                double dut1_seconds, int model_id) {
        if (!std::isfinite(tai_minus_utc_seconds) || !std::isfinite(dut1_seconds)
            || model_id < static_cast<int>(taiyin::FastPeriodic)
            || model_id > static_cast<int>(taiyin::SofaFull)) {
            throw py::value_error("invalid time-scale arguments");
        }
        return precise_time_scales_to_dict(taiyin::make_precise_time_scales_from_utc(
            value, tai_minus_utc_seconds, dut1_seconds,
            static_cast<taiyin::TdbModel>(model_id)));
    });
    module.def("_scales_from_ut_delta_t", [](const taiyin::CalendarDateTime& value,
                                               double delta_t_seconds, int model_id) {
        if (!std::isfinite(delta_t_seconds) || model_id < static_cast<int>(taiyin::FastPeriodic)
            || model_id > static_cast<int>(taiyin::SofaFull)) {
            throw py::value_error("invalid time-scale arguments");
        }
        return estimated_time_scales_to_dict(taiyin::make_time_scales_from_ut_delta_t(
            value, delta_t_seconds, static_cast<taiyin::TdbModel>(model_id)));
    });
    module.def("_estimated_scales_from_ut", [](const taiyin::CalendarDateTime& value,
                                                 int model_id) {
        if (model_id < static_cast<int>(taiyin::FastPeriodic)
            || model_id > static_cast<int>(taiyin::SofaFull)) {
            throw py::value_error("invalid TDB model");
        }
        return estimated_time_scales_to_dict(taiyin::make_estimated_time_scales_from_ut(
            value, static_cast<taiyin::TdbModel>(model_id)));
    });
    module.def("_create_chinese_calendar", [](const NativeCalcContext& astronomy,
                                               int rule_mode, int day_boundary_mode,
                                               int utc_offset_minutes,
                                               double calendar_meridian_deg) {
        return NativeChineseCalendarContext(
            astronomy, rule_mode, day_boundary_mode, utc_offset_minutes,
            calendar_meridian_deg);
    }, py::arg("astronomy"), py::arg("rule_mode"), py::arg("day_boundary_mode"),
       py::arg("utc_offset_minutes"), py::arg("calendar_meridian_deg"));
    module.def("_ganzhi_make", [](int stem_id, int branch_id) {
        uint8_t value = taiyin::chinese_calendar::kInvalidGanzhi;
        require_ok(taiyin::chinese_calendar::make_ganzhi(
            static_cast<uint8_t>(stem_id), static_cast<uint8_t>(branch_id), &value),
            "GanzhiApi.make");
        return value;
    });
    module.def("_ganzhi_advance", [](int value, int delta) {
        uint8_t result = taiyin::chinese_calendar::kInvalidGanzhi;
        require_ok(taiyin::chinese_calendar::advance_ganzhi(
            static_cast<uint8_t>(value), delta, &result), "GanzhiApi.advance");
        return result;
    });
    module.def("_ganzhi_month_pillar", [](int year_stem_id, int month_index) {
        uint8_t result = taiyin::chinese_calendar::kInvalidGanzhi;
        require_ok(taiyin::chinese_calendar::get_month_ganzhi(
            static_cast<uint8_t>(year_stem_id), static_cast<uint8_t>(month_index), &result),
            "GanzhiApi.month_pillar");
        return result;
    });
    module.def("_ganzhi_hour_pillar", [](int day_stem_id, int hour_index) {
        uint8_t result = taiyin::chinese_calendar::kInvalidGanzhi;
        require_ok(taiyin::chinese_calendar::get_hour_ganzhi(
            static_cast<uint8_t>(day_stem_id), static_cast<uint8_t>(hour_index), &result),
            "GanzhiApi.hour_pillar");
        return result;
    });
    module.def("_ganzhi_day_pillar", [](const taiyin::CalendarDateTime& civil_date) {
        uint8_t result = taiyin::chinese_calendar::kInvalidGanzhi;
        require_ok(taiyin::chinese_calendar::calculate_day_pillar(civil_date, &result),
                   "GanzhiApi.day_pillar");
        return result;
    });
    module.def("_ganzhi_nayin_element", [](int value) {
        uint8_t result = taiyin::chinese_calendar::kInvalidNaYin;
        require_ok(taiyin::chinese_calendar::get_nayin_element(
            static_cast<uint8_t>(value), &result), "GanzhiApi.nayin_element");
        return result;
    });
    module.def("_ganzhi_nayin_id", [](int value) {
        uint8_t result = taiyin::chinese_calendar::kInvalidNaYin;
        require_ok(taiyin::chinese_calendar::get_nayin_id(
            static_cast<uint8_t>(value), &result), "GanzhiApi.nayin_id");
        return result;
    });
}
