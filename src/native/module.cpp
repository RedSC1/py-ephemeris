#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin_python_core_api.h"

#include "taiyin/astrology/houses.h"
#include "taiyin/astrology/lunar_points.h"
#include "taiyin/astrology/sidereal.h"
#include "taiyin/astrology/targets.h"
#include "taiyin/chinese_calendar/ganzhi.h"
#include "taiyin/runtime/native_position.h"
#include "taiyin/runtime/moon_visibility.h"
#include "taiyin/runtime/planet_visibility.h"
#include "taiyin/runtime/solar_visibility.h"
#include "taiyin/runtime/star_visibility.h"
#include "taiyin/runtime/star_position.h"
#include "taiyin/runtime/heliacal_visibility.h"
#include "taiyin/runtime/phenomena.h"
#include "taiyin/runtime/observed_position.h"
#include "taiyin/runtime/orbital_events.h"
#include "taiyin/runtime/occultation_search.h"
#include "taiyin/runtime/eclipse_search.h"
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
using TaiyinNativeCalcContext = taiyin::runtime::NativeCalcContext;

struct PyLocalSolarEclipseCircumstances {
    SplitJulianDate coordinate;
    double delta_t_seconds;
    double magnitude;
    double obscuration;
    double center_separation_deg;
    double sun_angular_radius_deg;
    double moon_angular_radius_deg;
    double sun_altitude_deg;
    double sun_azimuth_deg;
};

void require_ok(Status status, const char* operation);

class NativeCalcContext : public TaiyinNativeCalcContext {
public:
    NativeCalcContext()
        : TaiyinNativeCalcContext(), deflectors_(), last_diagnostic_(),
          last_status_(taiyin::TAIYIN_STATUS_OK), last_operation_literal_(0),
          last_operation_owned_(),
          has_last_diagnostic_(false) {
        repair_pointers();
    }

    explicit NativeCalcContext(const TaiyinNativeCalcContext& source)
        : TaiyinNativeCalcContext(source), deflectors_(), last_diagnostic_(),
          last_status_(taiyin::TAIYIN_STATUS_OK), last_operation_literal_(0),
          last_operation_owned_(),
          has_last_diagnostic_(false) {
        copy_deflectors(source);
        repair_pointers();
    }

    NativeCalcContext(const NativeCalcContext& source)
        : TaiyinNativeCalcContext(source), deflectors_(), last_diagnostic_(),
          last_status_(taiyin::TAIYIN_STATUS_OK), last_operation_literal_(0),
          last_operation_owned_(),
          has_last_diagnostic_(false) {
        copy_deflectors(source);
        repair_pointers();
    }

    NativeCalcContext& operator=(const NativeCalcContext& source) {
        if (this == &source) return *this;
        TaiyinNativeCalcContext::operator=(source);
        deflectors_.clear();
        copy_deflectors(source);
        last_diagnostic_ = EphemerisEvalDiagnostic();
        last_status_ = taiyin::TAIYIN_STATUS_OK;
        last_operation_literal_ = 0;
        last_operation_owned_.clear();
        has_last_diagnostic_ = false;
        repair_pointers();
        return *this;
    }

    EphemerisEvalDiagnostic* diagnostic_buffer() const noexcept {
        return &last_diagnostic_;
    }

    void record_diagnostic(Status status, const char* operation) const noexcept {
        last_status_ = status;
        last_operation_literal_ = operation;
        last_operation_owned_.clear();
        has_last_diagnostic_ = true;
    }

    void record_diagnostic(Status status, const std::string& operation) const {
        last_status_ = status;
        last_operation_literal_ = 0;
        last_operation_owned_ = operation;
        has_last_diagnostic_ = true;
    }

    void record_diagnostic(
        Status status,
        const char* operation,
        const EphemerisEvalDiagnostic& diagnostic
    ) const noexcept {
        last_diagnostic_ = diagnostic;
        record_diagnostic(status, operation);
    }

    void record_diagnostic(
        Status status,
        const std::string& operation,
        const EphemerisEvalDiagnostic& diagnostic
    ) const {
        last_diagnostic_ = diagnostic;
        record_diagnostic(status, operation);
    }

    void record_status(Status status, const char* operation) const noexcept {
        last_status_ = status;
        last_operation_literal_ = operation;
        last_operation_owned_.clear();
        has_last_diagnostic_ = false;
    }

    void record_status(Status status, const std::string& operation) const {
        last_status_ = status;
        last_operation_literal_ = 0;
        last_operation_owned_ = operation;
        has_last_diagnostic_ = false;
    }

    void begin_operation(const std::string& operation) const {
        record_status(taiyin::TAIYIN_STATUS_OK, operation);
    }

    int last_status() const noexcept { return static_cast<int>(last_status_); }
    const char* last_operation() const noexcept {
        if (last_operation_literal_) return last_operation_literal_;
        return last_operation_owned_.empty() ? 0 : last_operation_owned_.c_str();
    }
    bool has_last_diagnostic() const noexcept { return has_last_diagnostic_; }
    const EphemerisEvalDiagnostic& last_diagnostic() const noexcept {
        return last_diagnostic_;
    }

    void replace_deflectors(
        const std::vector<taiyin::runtime::ApparentDeflector>& replacement,
        int solar_deflector_index
    ) {
        std::vector<taiyin::runtime::ApparentDeflector> candidate(replacement);
        require_ok(taiyin::runtime::native_context_set_deflectors(
            this,candidate.empty()?0:&candidate[0],candidate.size(),solar_deflector_index),
            "ContextConfiguration.set_deflectors");
        deflectors_.swap(candidate);
        apparent_options.deflectors=deflectors_.empty()?0:&deflectors_[0];
        apparent_options.deflector_count=deflectors_.size();
    }

    void clear_owned_deflectors() { deflectors_.clear(); }

private:
    void copy_deflectors(const TaiyinNativeCalcContext& source) {
        if(source.apparent_options.deflectors && source.apparent_options.deflector_count) {
            deflectors_.assign(source.apparent_options.deflectors,
                source.apparent_options.deflectors+source.apparent_options.deflector_count);
        }
    }

    void repair_pointers() {
        apparent_options.model_context=&model_context;
        if(!deflectors_.empty()) {
            apparent_options.deflectors=&deflectors_[0];
            apparent_options.deflector_count=deflectors_.size();
        } else if(apparent_options.deflector_count!=0) {
            apparent_options.deflectors=0;
            apparent_options.deflector_count=0;
            apparent_options.solar_deflector_index=-1;
        }
    }

    std::vector<taiyin::runtime::ApparentDeflector> deflectors_;
    mutable EphemerisEvalDiagnostic last_diagnostic_;
    mutable Status last_status_;
    mutable const char* last_operation_literal_;
    mutable std::string last_operation_owned_;
    mutable bool has_last_diagnostic_;
};

void require_ok(Status status, const char* operation) {
    if (status != taiyin::TAIYIN_STATUS_OK) {
        throw std::runtime_error(
            std::string(operation) + ": " + taiyin::status_message(status));
    }
}

template <typename Call>
void call_with_context_diagnostic(
    const NativeCalcContext& context,
    const char* operation,
    Call&& call
) {
    const Status status = call(context.diagnostic_buffer());
    context.record_diagnostic(status, operation);
    require_ok(status, operation);
}

void require_ok_with_context_diagnostic(
    const NativeCalcContext& context,
    Status status,
    const char* operation,
    const EphemerisEvalDiagnostic& diagnostic
) {
    context.record_diagnostic(status, operation, diagnostic);
    require_ok(status, operation);
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

py::dict registered_data_source_to_dict(
    const taiyin::runtime::RegisteredDataSource& value
) {
    py::dict result;
    result["kind"] = static_cast<int>(value.kind);
    result["format"] = static_cast<int>(value.format);
    result["flags"] = value.flags;
    result["source"] = value.source;
    result["item_count"] = value.item_count;
    result["jd_start"] = value.jd_start;
    result["jd_end"] = value.jd_end;
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

EphemerisEvalDiagnostic diagnostic_from_dict(const py::dict& source) {
    EphemerisEvalDiagnostic value;
    value.status=static_cast<Status>(source["status"].cast<int>());
    value.target_id=source["target_id"].cast<int>();
    value.center_id=source["center_id"].cast<int>();
    value.frame=static_cast<decltype(value.frame)>(source["frame"].cast<int>());
    value.jd_tdb=source["jd_tdb"].cast<SplitJulianDate>();
    value.candidate_count=source["candidate_count"].cast<int>();
    value.attempted_method_id=source["attempted_method_id"].cast<int>();
    value.nearest_coverage_start=source["nearest_coverage_start"].cast<double>();
    value.nearest_coverage_end=source["nearest_coverage_end"].cast<double>();
    value.component_target_id=source["component_target_id"].cast<int>();
    value.component_center_id=source["component_center_id"].cast<int>();
    value.component_method_id=source["component_method_id"].cast<int>();
    value.time_scale_route=source["time_scale_route"].cast<uint8_t>();
    value.time_scale_fallback_reason=source["time_scale_fallback_reason"].cast<uint8_t>();
    value.time_scale_flags=source["time_scale_flags"].cast<uint8_t>();
    value.tai_minus_utc_seconds=source["tai_minus_utc_seconds"].cast<double>();
    value.dut1_seconds=source["dut1_seconds"].cast<double>();
    value.delta_t_seconds=source["delta_t_seconds"].cast<double>();
    return value;
}

std::string format_diagnostic(const py::dict& source) {
    const EphemerisEvalDiagnostic value=diagnostic_from_dict(source);
    const size_t length=taiyin::runtime::format_ephemeris_eval_diagnostic(value,0,0);
    std::vector<char> buffer(length+1,0);
    taiyin::runtime::format_ephemeris_eval_diagnostic(value,&buffer[0],buffer.size());
    return std::string(&buffer[0],length);
}

py::dict position_result_to_dict(const double values[6], const EphemerisEvalDiagnostic& diagnostic) {
    py::dict result;
    result["values"] = std::vector<double>(values, values + 6);
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::tuple position_values_to_tuple(const double values[6], uint32_t flags) {
    const size_t count = (flags & taiyin::runtime::TAIYIN_NATIVE_POSITION_SPEED) != 0u
        ? 6u
        : 3u;
    py::tuple result(count);
    for (size_t index = 0; index < count; ++index) {
        result[index] = values[index];
    }
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

py::tuple vector3_to_tuple(const taiyin::Vector3& value) {
    return py::make_tuple(value.x, value.y, value.z);
}

py::dict orbit_reference_point_to_dict(
    const taiyin::runtime::BodyOrbitReferencePoint& value
) {
    py::dict result;
    result["position_au"] = vector3_to_tuple(value.position_au);
    result["longitude_radians"] = value.longitude_rad;
    result["latitude_radians"] = value.latitude_rad;
    result["distance_au"] = value.distance_au;
    return result;
}

py::dict osculating_orbit_to_dict(
    const taiyin::runtime::BodyOsculatingOrbit& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["body_id"] = value.body_id;
    result["center_id"] = value.center_id;
    result["reference_frame_id"] = value.reference_frame_id;
    result["gravitational_parameter_au3_per_day2"] =
        value.gravitational_parameter_au3_per_day2;
    result["semi_major_axis_au"] = value.semi_major_axis_au;
    result["eccentricity"] = value.eccentricity;
    result["inclination_radians"] = value.inclination_rad;
    result["longitude_of_ascending_node_radians"] =
        value.longitude_of_ascending_node_rad;
    result["argument_of_periapsis_radians"] = value.argument_of_periapsis_rad;
    result["true_anomaly_radians"] = value.true_anomaly_rad;
    result["mean_anomaly_radians"] = value.mean_anomaly_rad;
    result["periapsis_distance_au"] = value.periapsis_distance_au;
    result["apoapsis_distance_au"] = value.apoapsis_distance_au;
    result["osculating_period_days"] = value.osculating_period_days;
    result["current_distance_au"] = value.current_distance_au;
    result["radial_velocity_au_per_day"] = value.radial_velocity_au_per_day;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict orbit_reference_points_to_dict(
    const taiyin::runtime::BodyOrbitReferencePoints& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["body_id"] = value.body_id;
    result["center_id"] = value.center_id;
    result["reference_frame_id"] = value.reference_frame_id;
    result["model_id"] = static_cast<int>(value.model);
    result["ascending_node"] = orbit_reference_point_to_dict(value.ascending_node);
    result["descending_node"] = orbit_reference_point_to_dict(value.descending_node);
    result["periapsis"] = orbit_reference_point_to_dict(value.periapsis);
    result["apoapsis"] = orbit_reference_point_to_dict(value.apoapsis);
    result["second_focus"] = orbit_reference_point_to_dict(value.second_focus);
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict apsis_event_to_dict(
    const taiyin::runtime::BodyApsisSearchResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["body_id"] = value.body_id;
    result["center_id"] = value.center_id;
    result["kind"] = static_cast<int>(value.kind);
    result["coordinate"] = value.jd;
    result["distance_au"] = value.distance_au;
    result["radial_velocity_au_per_day"] = value.radial_velocity_au_per_day;
    result["iteration_count"] = value.iteration_count;
    result["evaluation_count"] = value.evaluation_count;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict plane_node_event_to_dict(
    const taiyin::runtime::BodyNodeSearchResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["body_id"] = value.body_id;
    result["center_id"] = value.center_id;
    result["reference_frame_id"] = value.reference_frame_id;
    result["kind"] = static_cast<int>(value.kind);
    result["coordinate"] = value.jd;
    result["reference_plane_angle_radians"] = value.reference_plane_angle_rad;
    result["distance_au"] = value.distance_au;
    result["iteration_count"] = value.iteration_count;
    result["evaluation_count"] = value.evaluation_count;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict occultation_phenomena_to_dict(
    const taiyin::runtime::LunarOccultationPhenomena& value
) {
    py::dict result;
    result["angular_distance_radians"] = value.angular_distance_rad;
    result["diameter_ratio"] = value.diameter_ratio;
    result["magnitude"] = value.magnitude;
    result["obscuration"] = value.obscuration;
    result["occulted_fraction"] = value.occulted_fraction;
    return result;
}

py::dict occultation_to_dict(
    const taiyin::runtime::LunarStarOccultationSearchResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["kind"] = value.kind;
    result["type_flags"] = value.type_flags;
    result["coordinate"] = value.jd_ut;
    result["begin"] = value.begin_jd_ut;
    result["end"] = value.end_jd_ut;
    result["first_contact"] = value.first_contact_jd_ut;
    result["second_contact"] = value.second_contact_jd_ut;
    result["third_contact"] = value.third_contact_jd_ut;
    result["fourth_contact"] = value.fourth_contact_jd_ut;
    result["separation_radians"] = value.separation_rad;
    result["moon_radius_radians"] = value.moon_radius_rad;
    result["target_radius_radians"] = value.target_radius_rad;
    result["margin_radians"] = value.margin_rad;
    result["phenomena"] = occultation_phenomena_to_dict(value.phenomena);
    result["candidate"] = value.candidate_jd_ut;
    result["next_search"] = value.next_search_jd_ut;
    result["candidate_count"] = value.candidate_count;
    result["iteration_count"] = value.iteration_count;
    result["evaluation_count"] = value.evaluation_count;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

taiyin::runtime::LunarStarOccultationSearchResult occultation_from_dict(
    const py::dict& source
) {
    taiyin::runtime::LunarStarOccultationSearchResult value;
    value.kind = source["kind"].cast<int>();
    value.type_flags = source["type_flags"].cast<uint32_t>();
    value.jd_ut = source["coordinate"].cast<SplitJulianDate>();
    value.begin_jd_ut = source["begin"].cast<SplitJulianDate>();
    value.end_jd_ut = source["end"].cast<SplitJulianDate>();
    value.first_contact_jd_ut = source["first_contact"].cast<SplitJulianDate>();
    value.second_contact_jd_ut = source["second_contact"].cast<SplitJulianDate>();
    value.third_contact_jd_ut = source["third_contact"].cast<SplitJulianDate>();
    value.fourth_contact_jd_ut = source["fourth_contact"].cast<SplitJulianDate>();
    value.separation_rad = source["separation_radians"].cast<double>();
    value.moon_radius_rad = source["moon_radius_radians"].cast<double>();
    value.target_radius_rad = source["target_radius_radians"].cast<double>();
    value.margin_rad = source["margin_radians"].cast<double>();
    const py::dict phenomena = source["phenomena"].cast<py::dict>();
    value.phenomena.angular_distance_rad =
        phenomena["angular_distance_radians"].cast<double>();
    value.phenomena.diameter_ratio = phenomena["diameter_ratio"].cast<double>();
    value.phenomena.magnitude = phenomena["magnitude"].cast<double>();
    value.phenomena.obscuration = phenomena["obscuration"].cast<double>();
    value.phenomena.occulted_fraction = phenomena["occulted_fraction"].cast<double>();
    value.candidate_jd_ut = source["candidate"].cast<SplitJulianDate>();
    value.next_search_jd_ut = source["next_search"].cast<SplitJulianDate>();
    value.candidate_count = source["candidate_count"].cast<int>();
    value.iteration_count = source["iteration_count"].cast<int>();
    value.evaluation_count = source["evaluation_count"].cast<int>();
    return value;
}

py::dict occultation_visibility_sample_to_dict(
    const taiyin::runtime::LunarOccultationLocalVisibilitySample& value
) {
    py::dict result;
    result["valid"] = value.valid != 0;
    result["coordinate"] = value.jd_ut;
    result["moon_altitude_radians"] = value.moon_altitude_rad;
    result["moon_azimuth_radians"] = value.moon_azimuth_rad;
    result["target_altitude_radians"] = value.target_altitude_rad;
    result["target_azimuth_radians"] = value.target_azimuth_rad;
    result["sun_altitude_radians"] = value.sun_altitude_rad;
    result["sun_azimuth_radians"] = value.sun_azimuth_rad;
    result["visibility_flags"] = value.visibility_flags;
    return result;
}

py::dict occultation_local_visibility_to_dict(
    const taiyin::runtime::LunarOccultationLocalVisibility& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    if (value.visible_interval_count < 0
        || value.visible_interval_count > taiyin::runtime::TAIYIN_OCCULTATION_MAX_VISIBILITY_INTERVALS
        || value.dark_visible_interval_count < 0
        || value.dark_visible_interval_count > taiyin::runtime::TAIYIN_OCCULTATION_MAX_VISIBILITY_INTERVALS) {
        throw std::runtime_error("native occultation visibility interval count is invalid");
    }
    py::dict result;
    result["first_contact"] = occultation_visibility_sample_to_dict(value.first_contact);
    result["second_contact"] = occultation_visibility_sample_to_dict(value.second_contact);
    result["maximum"] = occultation_visibility_sample_to_dict(value.maximum);
    result["third_contact"] = occultation_visibility_sample_to_dict(value.third_contact);
    result["fourth_contact"] = occultation_visibility_sample_to_dict(value.fourth_contact);
    result["target_rise"] = value.target_rise_jd_ut;
    result["target_set"] = value.target_set_jd_ut;
    result["visible_begin"] = value.visible_begin_jd_ut;
    result["visible_end"] = value.visible_end_jd_ut;
    result["dark_visible_begin"] = value.dark_visible_begin_jd_ut;
    result["dark_visible_end"] = value.dark_visible_end_jd_ut;
    py::list visible_intervals;
    for (int index = 0; index < value.visible_interval_count; ++index) {
        py::dict interval;
        interval["valid"] = value.visible_intervals[index].valid != 0;
        interval["begin"] = value.visible_intervals[index].begin_jd_ut;
        interval["end"] = value.visible_intervals[index].end_jd_ut;
        visible_intervals.append(interval);
    }
    result["visible_intervals"] = visible_intervals;
    py::list dark_intervals;
    for (int index = 0; index < value.dark_visible_interval_count; ++index) {
        py::dict interval;
        interval["valid"] = value.dark_visible_intervals[index].valid != 0;
        interval["begin"] = value.dark_visible_intervals[index].begin_jd_ut;
        interval["end"] = value.dark_visible_intervals[index].end_jd_ut;
        dark_intervals.append(interval);
    }
    result["dark_visible_intervals"] = dark_intervals;
    result["visibility_flags"] = value.visibility_flags;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict occultation_path_point_to_dict(
    const taiyin::runtime::LunarOccultationWherePathPoint& value
) {
    py::dict result;
    result["valid"] = value.valid != 0;
    result["coordinate"] = value.jd_ut;
    result["longitude_degrees"] = value.longitude_deg;
    result["latitude_degrees"] = value.latitude_deg;
    result["height_meters"] = value.height_m;
    return result;
}

py::dict occultation_where_to_dict(
    const taiyin::runtime::LunarOccultationWhereResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    if (value.center_line_path_count < 0
        || value.center_line_path_count > taiyin::runtime::TAIYIN_OCCULTATION_WHERE_MAX_PATH_POINTS
        || value.outer_limit_path_count < 0
        || value.outer_limit_path_count > taiyin::runtime::TAIYIN_OCCULTATION_WHERE_MAX_PATH_POINTS
        || value.visible_region_polygon_count < 0
        || value.visible_region_polygon_count > taiyin::runtime::TAIYIN_OCCULTATION_WHERE_MAX_POLYGON_POINTS) {
        throw std::runtime_error("native occultation path count is invalid");
    }
    py::dict result;
    result["center_line_hits_earth"] = value.center_line_hits_earth != 0;
    result["type_flags"] = value.type_flags;
    result["coordinate"] = value.jd_ut;
    result["center_line_begin"] = value.center_line_begin_jd_ut;
    result["center_line_end"] = value.center_line_end_jd_ut;
    py::list center_line_path;
    for (int index = 0; index < value.center_line_path_count; ++index) {
        center_line_path.append(occultation_path_point_to_dict(value.center_line_path[index]));
    }
    result["center_line_path"] = center_line_path;
    result["center_line_min_longitude_degrees"] = value.center_line_min_longitude_deg;
    result["center_line_max_longitude_degrees"] = value.center_line_max_longitude_deg;
    result["center_line_min_latitude_degrees"] = value.center_line_min_latitude_deg;
    result["center_line_max_latitude_degrees"] = value.center_line_max_latitude_deg;
    result["center_line_path_distance_kilometers"] = value.center_line_path_distance_km;
    py::list outer_north_path;
    py::list outer_south_path;
    for (int index = 0; index < value.outer_limit_path_count; ++index) {
        outer_north_path.append(occultation_path_point_to_dict(value.outer_north_path[index]));
        outer_south_path.append(occultation_path_point_to_dict(value.outer_south_path[index]));
    }
    result["outer_north_path"] = outer_north_path;
    result["outer_south_path"] = outer_south_path;
    result["outer_limit_mean_width_kilometers"] = value.outer_limit_mean_width_km;
    result["outer_limit_max_width_kilometers"] = value.outer_limit_max_width_km;
    py::list visible_region_polygon;
    for (int index = 0; index < value.visible_region_polygon_count; ++index) {
        visible_region_polygon.append(
            occultation_path_point_to_dict(value.visible_region_polygon[index]));
    }
    result["visible_region_polygon"] = visible_region_polygon;
    result["visible_region_min_longitude_degrees"] = value.visible_region_min_longitude_deg;
    result["visible_region_max_longitude_degrees"] = value.visible_region_max_longitude_deg;
    result["visible_region_min_latitude_degrees"] = value.visible_region_min_latitude_deg;
    result["visible_region_max_latitude_degrees"] = value.visible_region_max_latitude_deg;
    result["longitude_degrees"] = value.longitude_deg;
    result["latitude_degrees"] = value.latitude_deg;
    result["height_meters"] = value.height_m;
    result["separation_radians"] = value.separation_rad;
    result["moon_radius_radians"] = value.moon_radius_rad;
    result["target_radius_radians"] = value.target_radius_rad;
    result["margin_radians"] = value.margin_rad;
    result["phenomena"] = occultation_phenomena_to_dict(value.phenomena);
    result["local_sample"] = occultation_visibility_sample_to_dict(value.local_sample);
    result["visibility_flags"] = value.visibility_flags;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict lunar_eclipse_to_dict(
    const taiyin::runtime::LunarEclipseResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["kind"] = value.kind;
    result["maximum"] = value.maximum_jd_tt;
    result["delta_t_seconds"] = NAN;
    result["umbral_magnitude"] = value.umbral_magnitude;
    result["penumbral_magnitude"] = value.penumbral_magnitude;
    result["axis_distance_radians"] = value.axis_distance_rad;
    result["umbra_radius_radians"] = value.umbra_radius_rad;
    result["penumbra_radius_radians"] = value.penumbra_radius_rad;
    result["moon_radius_radians"] = value.moon_radius_rad;
    py::list contacts;
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT; ++i)
        contacts.append(value.contact_jd_tt[i]);
    result["contacts"] = contacts;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict lunar_eclipse_to_dict(
    const taiyin::runtime::LunarEclipseResultUt& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["kind"] = value.kind;
    result["maximum"] = value.maximum_jd_ut;
    result["delta_t_seconds"] = value.delta_t_seconds;
    result["umbral_magnitude"] = value.umbral_magnitude;
    result["penumbral_magnitude"] = value.penumbral_magnitude;
    result["axis_distance_radians"] = value.axis_distance_rad;
    result["umbra_radius_radians"] = value.umbra_radius_rad;
    result["penumbra_radius_radians"] = value.penumbra_radius_rad;
    result["moon_radius_radians"] = value.moon_radius_rad;
    py::list contacts;
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT; ++i)
        contacts.append(value.contact_jd_ut[i]);
    result["contacts"] = contacts;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

py::dict solar_eclipse_to_dict(
    const taiyin::runtime::SolarEclipseResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["kind"] = value.kind;
    result["maximum"] = value.maximum_jd_tt;
    result["delta_t_seconds"] = NAN;
    result["axis_distance_kilometers"] = value.axis_distance_km;
    result["penumbra_radius_kilometers"] = value.penumbra_radius_km;
    result["core_radius_kilometers"] = value.core_radius_km;
    result["penumbral_margin_kilometers"] = value.penumbral_margin_km;
    result["central_margin_kilometers"] = value.central_margin_km;
    result["maximum_latitude_degrees"] = value.maximum_latitude_deg;
    result["maximum_longitude_degrees"] = value.maximum_longitude_deg;
    py::list contacts;
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_SOLAR_ECLIPSE_CONTACT_COUNT; ++i)
        contacts.append(value.contact_jd_tt[i]);
    result["contacts"] = contacts;
    result["diagnostic"] = diagnostic_to_dict(diagnostic);
    return result;
}

taiyin::runtime::LunarEclipseResult lunar_eclipse_tt_from_dict(const py::dict& source) {
    taiyin::runtime::LunarEclipseResult value;
    value.kind = source["kind"].cast<uint32_t>();
    value.maximum_jd_tt = source["maximum"].cast<SplitJulianDate>();
    value.umbral_magnitude = source["umbral_magnitude"].cast<double>();
    value.penumbral_magnitude = source["penumbral_magnitude"].cast<double>();
    value.axis_distance_rad = source["axis_distance_radians"].cast<double>();
    value.umbra_radius_rad = source["umbra_radius_radians"].cast<double>();
    value.penumbra_radius_rad = source["penumbra_radius_radians"].cast<double>();
    value.moon_radius_rad = source["moon_radius_radians"].cast<double>();
    const py::list contacts = source["contacts"].cast<py::list>();
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT; ++i)
        value.contact_jd_tt[i] = contacts[i].cast<SplitJulianDate>();
    return value;
}

taiyin::runtime::LunarEclipseResultUt lunar_eclipse_ut_from_dict(const py::dict& source) {
    taiyin::runtime::LunarEclipseResultUt value;
    value.kind = source["kind"].cast<uint32_t>();
    value.maximum_jd_ut = source["maximum"].cast<SplitJulianDate>();
    value.delta_t_seconds = source["delta_t_seconds"].cast<double>();
    value.umbral_magnitude = source["umbral_magnitude"].cast<double>();
    value.penumbral_magnitude = source["penumbral_magnitude"].cast<double>();
    value.axis_distance_rad = source["axis_distance_radians"].cast<double>();
    value.umbra_radius_rad = source["umbra_radius_radians"].cast<double>();
    value.penumbra_radius_rad = source["penumbra_radius_radians"].cast<double>();
    value.moon_radius_rad = source["moon_radius_radians"].cast<double>();
    const py::list contacts = source["contacts"].cast<py::list>();
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT; ++i)
        value.contact_jd_ut[i] = contacts[i].cast<SplitJulianDate>();
    return value;
}

py::dict local_lunar_eclipse_to_dict(
    const taiyin::runtime::LocalLunarEclipseResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result; result["kind"] = value.eclipse_kind;
    result["visibility_flags"] = value.visibility_flags;
    result["maximum"] = value.maximum_jd_tt; result["delta_t_seconds"] = NAN;
    result["umbral_magnitude"] = value.umbral_magnitude;
    result["penumbral_magnitude"] = value.penumbral_magnitude;
    py::list contacts, altitudes, azimuths;
    for (size_t i=0;i<taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT;++i) {
        contacts.append(value.contact_jd_tt[i]); altitudes.append(value.contact_moon_altitude_deg[i]);
        azimuths.append(value.contact_moon_azimuth_deg[i]);
    }
    result["contacts"]=contacts; result["altitudes"]=altitudes; result["azimuths"]=azimuths;
    result["moonrise"]=value.moonrise_jd_tt; result["moonset"]=value.moonset_jd_tt;
    result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
}

py::dict local_lunar_eclipse_to_dict(
    const taiyin::runtime::LocalLunarEclipseResultUt& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result; result["kind"] = value.eclipse_kind;
    result["visibility_flags"] = value.visibility_flags;
    result["maximum"] = value.maximum_jd_ut; result["delta_t_seconds"] = value.delta_t_seconds;
    result["umbral_magnitude"] = value.umbral_magnitude;
    result["penumbral_magnitude"] = value.penumbral_magnitude;
    py::list contacts, altitudes, azimuths;
    for (size_t i=0;i<taiyin::runtime::TAIYIN_LUNAR_ECLIPSE_CONTACT_COUNT;++i) {
        contacts.append(value.contact_jd_ut[i]); altitudes.append(value.contact_moon_altitude_deg[i]);
        azimuths.append(value.contact_moon_azimuth_deg[i]);
    }
    result["contacts"]=contacts; result["altitudes"]=altitudes; result["azimuths"]=azimuths;
    result["moonrise"]=value.moonrise_jd_ut; result["moonset"]=value.moonset_jd_ut;
    result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
}

py::dict local_solar_eclipse_to_dict(
    const taiyin::runtime::LocalSolarEclipseResult& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result; result["kind"] = value.kind; result["maximum"] = value.maximum_jd_tt;
    result["delta_t_seconds"] = NAN; result["magnitude"] = value.magnitude;
    result["obscuration"] = value.obscuration; result["sun_altitude_degrees"] = value.sun_altitude_deg;
    result["sun_azimuth_degrees"] = value.sun_azimuth_deg; py::list contacts;
    for(size_t i=0;i<taiyin::runtime::TAIYIN_LOCAL_SOLAR_CONTACT_COUNT;++i) contacts.append(value.contact_jd_tt[i]);
    result["contacts"]=contacts; result["position_angle_c1_degrees"]=value.position_angle_c1_deg;
    result["position_angle_c4_degrees"]=value.position_angle_c4_deg;
    result["vertex_angle_c1_degrees"]=value.vertex_angle_c1_deg; result["vertex_angle_c4_degrees"]=value.vertex_angle_c4_deg;
    result["sunrise_magnitude"]=value.sunrise_magnitude; result["sunset_magnitude"]=value.sunset_magnitude;
    result["duration_seconds"]=value.duration_seconds; result["moon_sun_radius_ratio"]=value.moon_sun_radius_ratio;
    result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
}

PyLocalSolarEclipseCircumstances local_solar_circumstances_to_python(
    const taiyin::runtime::LocalSolarEclipseCircumstances& value
) {
    return PyLocalSolarEclipseCircumstances{
        value.jd_tt, NAN, value.magnitude, value.obscuration,
        value.center_separation_deg, value.sun_angular_radius_deg,
        value.moon_angular_radius_deg, value.sun_altitude_deg,
        value.sun_azimuth_deg};
}

py::dict besselian_elements_to_dict(const taiyin::runtime::SolarBesselianElements& value) {
    py::dict result; result["t_hours"]=value.t_hours; result["x"]=value.x; result["y"]=value.y;
    result["zeta"]=value.zeta; result["d_degrees"]=value.d_deg; result["mu_degrees"]=value.mu_deg;
    result["l1"]=value.l1; result["l2"]=value.l2; result["f1_degrees"]=value.f1_deg;
    result["f2_degrees"]=value.f2_deg; result["tan_f1"]=value.tan_f1;
    result["tan_f2"]=value.tan_f2; result["gamma"]=value.gamma; return result;
}

py::dict besselian_polynomial_to_dict(const taiyin::runtime::SolarBesselianPolynomial& value) {
    py::dict result; result["reference_epoch"]=value.t0_jd_tt; result["span_hours"]=value.span_hours;
    result["sample_step_hours"]=value.sample_step_hours; result["degree"]=value.degree;
    result["f1_degrees"]=value.f1_deg; result["f2_degrees"]=value.f2_deg;
    result["tan_f1"]=value.tan_f1; result["tan_f2"]=value.tan_f2;
    result["center"]=besselian_elements_to_dict(value.center);
    result["max_residual"]=besselian_elements_to_dict(value.max_residual);
    const size_t n=taiyin::runtime::TAIYIN_SOLAR_BESSELIAN_COEFF_COUNT;
    result["x_coefficients"]=std::vector<double>(value.x,value.x+n);
    result["y_coefficients"]=std::vector<double>(value.y,value.y+n);
    result["zeta_coefficients"]=std::vector<double>(value.zeta,value.zeta+n);
    result["d_degrees_coefficients"]=std::vector<double>(value.d_deg,value.d_deg+n);
    result["mu_degrees_coefficients"]=std::vector<double>(value.mu_deg,value.mu_deg+n);
    result["l1_coefficients"]=std::vector<double>(value.l1,value.l1+n);
    result["l2_coefficients"]=std::vector<double>(value.l2,value.l2+n); return result;
}

taiyin::runtime::SolarBesselianPolynomial besselian_polynomial_from_dict(const py::dict& source) {
    taiyin::runtime::SolarBesselianPolynomial value;
    value.t0_jd_tt=source["reference_epoch"].cast<SplitJulianDate>();
    value.span_hours=source["span_hours"].cast<double>(); value.sample_step_hours=source["sample_step_hours"].cast<double>();
    value.degree=source["degree"].cast<int>(); value.f1_deg=source["f1_degrees"].cast<double>();
    value.f2_deg=source["f2_degrees"].cast<double>(); value.tan_f1=source["tan_f1"].cast<double>(); value.tan_f2=source["tan_f2"].cast<double>();
    const char* keys[]={"x_coefficients","y_coefficients","zeta_coefficients","d_degrees_coefficients","mu_degrees_coefficients","l1_coefficients","l2_coefficients"};
    double* arrays[]={value.x,value.y,value.zeta,value.d_deg,value.mu_deg,value.l1,value.l2};
    for(size_t a=0;a<7;++a){ const std::vector<double> row=source[keys[a]].cast<std::vector<double>>();
        if(row.size()!=taiyin::runtime::TAIYIN_SOLAR_BESSELIAN_COEFF_COUNT) throw py::value_error("Besselian coefficient array must contain 8 values");
        for(size_t i=0;i<row.size();++i) arrays[a][i]=row[i]; }
    return value;
}

py::dict solar_route_point_to_dict(const taiyin::runtime::SolarEclipsePathPoint& value) {
    py::dict result; result["coordinate_tt"]=value.jd_tt; result["coordinate_ut1"]=value.jd_ut;
    result["latitude_degrees"]=value.latitude_deg; result["longitude_degrees"]=value.longitude_deg;
    result["elevation_meters"]=value.elevation_m; result["sun_altitude_degrees"]=value.sun_altitude_deg;
    result["sun_azimuth_degrees"]=value.sun_azimuth_deg; return result;
}

py::dict solar_route_row_to_dict(const taiyin::runtime::SolarEclipseRouteRow& value) {
    py::dict result; result["coordinate_tt"]=value.jd_tt; result["coordinate_ut1"]=value.jd_ut;
    result["center_line"]=solar_route_point_to_dict(value.center_line);
    result["penumbral_north_limit"]=solar_route_point_to_dict(value.penumbral_north_limit);
    result["penumbral_south_limit"]=solar_route_point_to_dict(value.penumbral_south_limit);
    result["north_limit"]=solar_route_point_to_dict(value.north_limit);
    result["south_limit"]=solar_route_point_to_dict(value.south_limit);
    result["half_magnitude_north_limit"]=solar_route_point_to_dict(value.half_magnitude_north_limit);
    result["half_magnitude_south_limit"]=solar_route_point_to_dict(value.half_magnitude_south_limit);
    result["path_width_kilometers"]=value.path_width_km; result["duration_seconds"]=value.duration_seconds;
    result["sun_altitude_degrees"]=value.sun_altitude_deg; result["sun_azimuth_degrees"]=value.sun_azimuth_deg;
    return result;
}

py::dict solar_route_curve_point_to_dict(const taiyin::runtime::SolarEclipseRouteCurvePoint& value) {
    py::dict result; result["coordinate_tt"]=value.jd_tt; result["coordinate_ut1"]=value.jd_ut;
    result["kind"]=value.curve_kind; result["latitude_degrees"]=value.latitude_deg;
    result["longitude_degrees"]=value.longitude_deg; return result;
}

py::dict solar_route_product_point_to_dict(
    const taiyin::runtime::SolarEclipseRouteProductPoint& value
) {
    py::dict result; result["coordinate_tt"]=value.jd_tt; result["coordinate_ut1"]=value.jd_ut;
    result["kind"]=value.point_kind; result["source_curve_kind"]=value.source_curve_kind;
    result["latitude_degrees"]=value.latitude_deg; result["longitude_degrees"]=value.longitude_deg;
    result["unwrapped_longitude_degrees"]=value.unwrapped_longitude_deg; return result;
}

py::dict solar_route_product_summary_to_dict(
    const taiyin::runtime::SolarEclipseRouteProductSummary& value
) {
    py::dict result; result["flags"]=value.flags; result["curve_point_count"]=value.curve_point_count;
    result["center_line_count"]=value.center_line_count; result["core_north_count"]=value.core_north_count;
    result["core_south_count"]=value.core_south_count;
    result["core_begin_horizon_count"]=value.core_begin_horizon_count;
    result["core_end_horizon_count"]=value.core_end_horizon_count;
    result["penumbral_north_count"]=value.penumbral_north_count;
    result["penumbral_south_count"]=value.penumbral_south_count;
    result["half_magnitude_north_count"]=value.half_magnitude_north_count;
    result["half_magnitude_south_count"]=value.half_magnitude_south_count;
    result["core_polygon_point_count"]=value.core_polygon_point_count;
    result["penumbral_polygon_point_count"]=value.penumbral_polygon_point_count;
    result["half_magnitude_polygon_point_count"]=value.half_magnitude_polygon_point_count;
    result["polygon_point_count"]=value.polygon_point_count;
    result["minimum_latitude_degrees"]=value.min_latitude_deg;
    result["maximum_latitude_degrees"]=value.max_latitude_deg;
    result["minimum_unwrapped_longitude_degrees"]=value.min_unwrapped_longitude_deg;
    result["maximum_unwrapped_longitude_degrees"]=value.max_unwrapped_longitude_deg; return result;
}

py::dict local_solar_boundary_to_dict(const taiyin::runtime::LocalSolarEclipseBoundary& value) {
    py::dict result; result["center_kind"]=value.center_kind;
    result["center_longitude_degrees"]=value.center_longitude_deg;
    result["center_latitude_degrees"]=value.center_latitude_deg;
    result["umbra_north_longitude_degrees"]=value.umbra_north_longitude_deg;
    result["umbra_north_latitude_degrees"]=value.umbra_north_latitude_deg;
    result["umbra_south_longitude_degrees"]=value.umbra_south_longitude_deg;
    result["umbra_south_latitude_degrees"]=value.umbra_south_latitude_deg;
    result["penumbra_north_longitude_degrees"]=value.penumbra_north_longitude_deg;
    result["penumbra_north_latitude_degrees"]=value.penumbra_north_latitude_deg;
    result["penumbra_south_longitude_degrees"]=value.penumbra_south_longitude_deg;
    result["penumbra_south_latitude_degrees"]=value.penumbra_south_latitude_deg;
    result["umbra_width_kilometers"]=value.umbra_width_km; return result;
}

PyLocalSolarEclipseCircumstances local_solar_circumstances_to_python(
    const taiyin::runtime::LocalSolarEclipseCircumstancesUt& value
) {
    return PyLocalSolarEclipseCircumstances{
        value.jd_ut, value.delta_t_seconds, value.magnitude, value.obscuration,
        value.center_separation_deg, value.sun_angular_radius_deg,
        value.moon_angular_radius_deg, value.sun_altitude_deg,
        value.sun_azimuth_deg};
}

py::dict local_solar_eclipse_to_dict(
    const taiyin::runtime::LocalSolarEclipseResultUt& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result; result["kind"] = value.kind; result["maximum"] = value.maximum_jd_ut;
    result["delta_t_seconds"] = value.delta_t_seconds; result["magnitude"] = value.magnitude;
    result["obscuration"] = value.obscuration; result["sun_altitude_degrees"] = value.sun_altitude_deg;
    result["sun_azimuth_degrees"] = value.sun_azimuth_deg; py::list contacts;
    for(size_t i=0;i<taiyin::runtime::TAIYIN_LOCAL_SOLAR_CONTACT_COUNT;++i) contacts.append(value.contact_jd_ut[i]);
    result["contacts"]=contacts; result["position_angle_c1_degrees"]=value.position_angle_c1_deg;
    result["position_angle_c4_degrees"]=value.position_angle_c4_deg;
    result["vertex_angle_c1_degrees"]=value.vertex_angle_c1_deg; result["vertex_angle_c4_degrees"]=value.vertex_angle_c4_deg;
    result["sunrise_magnitude"]=value.sunrise_magnitude; result["sunset_magnitude"]=value.sunset_magnitude;
    result["duration_seconds"]=value.duration_seconds; result["moon_sun_radius_ratio"]=value.moon_sun_radius_ratio;
    result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
}

py::dict solar_eclipse_to_dict(
    const taiyin::runtime::SolarEclipseResultUt& value,
    const EphemerisEvalDiagnostic& diagnostic
) {
    py::dict result;
    result["kind"] = value.kind;
    result["maximum"] = value.maximum_jd_ut;
    result["delta_t_seconds"] = value.delta_t_seconds;
    result["axis_distance_kilometers"] = value.axis_distance_km;
    result["penumbra_radius_kilometers"] = value.penumbra_radius_km;
    result["core_radius_kilometers"] = value.core_radius_km;
    result["penumbral_margin_kilometers"] = value.penumbral_margin_km;
    result["central_margin_kilometers"] = value.central_margin_km;
    result["maximum_latitude_degrees"] = value.maximum_latitude_deg;
    result["maximum_longitude_degrees"] = value.maximum_longitude_deg;
    py::list contacts;
    for (size_t i = 0; i < taiyin::runtime::TAIYIN_SOLAR_ECLIPSE_CONTACT_COUNT; ++i)
        contacts.append(value.contact_jd_ut[i]);
    result["contacts"] = contacts;
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
    const TaiyinNativeCalcContext*, double, SplitJulianDate, uint64_t,
    SplitJulianDate*, EphemerisEvalDiagnostic*);
typedef Status (*EventDateArrayFn)(
    const TaiyinNativeCalcContext*, int, double, SplitJulianDate, SplitJulianDate,
    double, uint64_t, SplitJulianDate*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventStationArrayFn)(
    const TaiyinNativeCalcContext*, int, SplitJulianDate, SplitJulianDate, double,
    uint64_t, SplitJulianDate*, double*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventAspectArrayFn)(
    const TaiyinNativeCalcContext*, int, int, double, SplitJulianDate, SplitJulianDate,
    double, uint64_t, SplitJulianDate*, size_t, size_t*, EphemerisEvalDiagnostic*);
typedef Status (*EventExactAspectArrayFn)(
    const TaiyinNativeCalcContext*, int, int, const double*, size_t, SplitJulianDate,
    SplitJulianDate, double, uint64_t, SplitJulianDate*, double*, size_t, size_t*,
    EphemerisEvalDiagnostic*);
typedef Status (*EventPhaseArrayFn)(
    const TaiyinNativeCalcContext*, double, SplitJulianDate, SplitJulianDate, double,
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

py::dict observed_to_dict(const taiyin::runtime::ObservedPosition& value) {
    py::dict out; out["body_id"] = value.body_id; out["status"] = value.status;
    out["diagnostic"] = diagnostic_to_dict(value.diagnostic); out["body_mask_bit"] = value.apparent.body_mask_bit;
    const CartesianState& geometric = value.apparent.geometric_state;
    const CartesianState& apparent = value.apparent.apparent_state;
    out["geometric_state"] = py::make_tuple(
        py::make_tuple(geometric.position_au.x, geometric.position_au.y, geometric.position_au.z),
        py::make_tuple(geometric.velocity_au_per_day.x, geometric.velocity_au_per_day.y, geometric.velocity_au_per_day.z),
        py::make_tuple(geometric.acceleration_au_per_day2.x, geometric.acceleration_au_per_day2.y, geometric.acceleration_au_per_day2.z));
    out["apparent_state"] = py::make_tuple(
        py::make_tuple(apparent.position_au.x, apparent.position_au.y, apparent.position_au.z),
        py::make_tuple(apparent.velocity_au_per_day.x, apparent.velocity_au_per_day.y, apparent.velocity_au_per_day.z),
        py::make_tuple(apparent.acceleration_au_per_day2.x, apparent.acceleration_au_per_day2.y, apparent.acceleration_au_per_day2.z));
    out["longitude_radians"] = value.apparent.longitude_rad;
    out["latitude_radians"] = value.apparent.latitude_rad; out["distance_au"] = value.apparent.distance_au;
    out["light_time_days"] = value.apparent.light_time_days; out["cache_hit"] = value.apparent.cache_hit;
    out["horizontal"] = py::make_tuple(value.horizontal.azimuth_rad, value.horizontal.altitude_rad, value.horizontal.distance_au);
    out["horizontal_rates"] = py::make_tuple(value.horizontal_rates.azimuth_rate_rad_per_day, value.horizontal_rates.altitude_rate_rad_per_day, value.horizontal_rates.distance_rate_au_per_day);
    out["refracted_horizontal"] = py::make_tuple(value.refracted_horizontal.azimuth_rad, value.refracted_horizontal.altitude_rad, value.refracted_horizontal.distance_au);
    out["refracted_horizontal_rates"] = py::make_tuple(value.refracted_horizontal_rates.azimuth_rate_rad_per_day, value.refracted_horizontal_rates.altitude_rate_rad_per_day, value.refracted_horizontal_rates.distance_rate_au_per_day);
    return out;
}

py::dict heliacal_visibility_to_dict(const taiyin::runtime::HeliacalVisibilityResult& value) {
    py::dict out; out["visible"]=value.visible!=0; out["model_id"]=value.model_id;
    out["extinction_model_id"]=value.extinction_model_id; out["twilight_model_id"]=value.twilight_model_id;
    out["moonlight_model_id"]=value.moonlight_model_id; out["visual_threshold_model_id"]=value.visual_threshold_model_id;
    out["target_magnitude"]=value.target_magnitude; out["limiting_magnitude"]=value.limiting_magnitude;
    out["target_altitude_radians"]=value.target_altitude_rad; out["target_azimuth_radians"]=value.target_azimuth_rad;
    out["sun_altitude_radians"]=value.sun_altitude_rad; out["sun_azimuth_radians"]=value.sun_azimuth_rad;
    out["target_sun_separation_radians"]=value.target_sun_separation_rad; out["airmass"]=value.airmass;
    out["extinction_magnitude_per_airmass"]=value.extinction_mag_per_airmass; out["extinction_magnitude"]=value.extinction_mag;
    out["sky_brightness_nanolambert"]=value.sky_brightness_nanolambert; out["moonlight_brightness_nanolambert"]=value.moonlight_brightness_nanolambert;
    out["threshold_illuminance_footcandles"]=value.threshold_illuminance_footcandles; out["target_illuminance_footcandles"]=value.target_illuminance_footcandles;
    out["visibility_margin_magnitude"]=value.visibility_margin_magnitude; out["required_sun_altitude_radians"]=value.required_sun_altitude_rad;
    out["solar_depression_margin_radians"]=value.solar_depression_margin_rad; return out;
}

taiyin::runtime::HeliacalVisibilityConditions heliacal_conditions(const py::dict& value) {
    taiyin::runtime::HeliacalVisibilityConditions out;
    if (!value["extinction"].is_none()) out.extinction_mag_per_airmass=value["extinction"].cast<double>();
    if (!value["sky"].is_none()) out.sky_brightness_nanolambert=value["sky"].cast<double>();
    if (!value["night"].is_none()) out.night_sky_brightness_nanolambert=value["night"].cast<double>();
    return out;
}

class CustomTargetRequest {
public:
    CustomTargetRequest(
        const TaiyinNativeCalcContext* context,
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
    const TaiyinNativeCalcContext* context_;
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
        bool strict_discovery,
        const std::string& eop_path,
        const std::string& lunar_limb_path
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
        config.eop_path = eop_path.empty() ? 0 : eop_path.c_str();
        config.lunar_limb_path = lunar_limb_path.empty() ? 0 : lunar_limb_path.c_str();
        config.load_packaged_data = load_packaged_data;
        config.load_builtin_eop = load_builtin_eop;
        config.segment_cache_max_entries = segment_cache_max_entries;
        config.strict_discovery = strict_discovery;
        if (!taiyin::runtime::initialize_global_ephemeris_runtime(config)) {
            throw std::runtime_error("Taiyin runtime initialization failed");
        }
    }

    std::unique_ptr<NativeCalcContext> create_context() const {
        std::unique_ptr<NativeCalcContext> context(
            new NativeCalcContext(taiyin::runtime::get_default_native_calc_context()));
        context->apparent_options.model_context = &context->model_context;
        return context;
    }

    void add_source_path(const std::string& path) const {
        if (path.empty() || !taiyin::runtime::add_global_ephemeris_source_path(path.c_str())) {
            throw std::runtime_error("could not add ephemeris source path");
        }
    }

    void clear_cache() const { taiyin::runtime::clear_global_ephemeris_cache(); }
    std::size_t catalog_size() const { return taiyin::runtime::global_ephemeris_catalog_size(); }
    void load_eop_table(const std::string& path) const {
        require_ok(taiyin::runtime::load_global_earth_orientation_table(path.c_str()),
                   "Ephemeris.load_eop_table");
    }
    void load_builtin_eop_table() const {
        require_ok(taiyin::runtime::load_global_builtin_earth_orientation_table(),
                   "Ephemeris.load_builtin_eop_table");
    }
    void clear_eop_table() const {
        if (!taiyin::runtime::set_global_earth_orientation_table(0)) {
            throw std::runtime_error("Ephemeris.clear_eop_table failed");
        }
    }
    bool has_eop_table() const {
        return taiyin::runtime::global_earth_orientation_table() != 0;
    }
    void load_lunar_limb_model(const std::string& path) const {
        require_ok(taiyin::runtime::load_global_lunar_limb_model(path.c_str()),
                   "Ephemeris.load_lunar_limb_model");
    }
    void clear_lunar_limb_model() const {
        require_ok(taiyin::runtime::load_global_lunar_limb_model(0),
                   "Ephemeris.clear_lunar_limb_model");
    }
    bool has_lunar_limb_model() const {
        return taiyin::runtime::global_lunar_limb_model() != 0;
    }
    std::size_t cache_entry_count() const {
        return taiyin::runtime::global_ephemeris_cache_entry_count();
    }

    void set_source_priority(const std::string& path_or_basename, int priority) const {
        if (path_or_basename.empty()
            || !taiyin::runtime::set_global_ephemeris_source_priority(
                path_or_basename.c_str(), priority)) {
            throw std::runtime_error("could not set ephemeris source priority");
        }
    }

    void clear_source_priority(const std::string& path_or_basename) const {
        if (path_or_basename.empty()
            || !taiyin::runtime::clear_global_ephemeris_source_priority(
                path_or_basename.c_str())) {
            throw std::runtime_error("could not clear ephemeris source priority");
        }
    }

    void clear_all_source_priorities() const {
        taiyin::runtime::clear_all_global_ephemeris_source_priorities();
    }

    std::vector<py::dict> registered_data_sources() const {
        std::vector<taiyin::runtime::RegisteredDataSource> sources;
        if (!taiyin::runtime::get_global_registered_data_sources(&sources)) {
            throw std::runtime_error("could not inspect registered runtime data");
        }
        std::vector<py::dict> result;
        result.reserve(sources.size());
        for (std::size_t index = 0; index < sources.size(); ++index) {
            result.push_back(registered_data_source_to_dict(sources[index]));
        }
        return result;
    }
};

class NativeChineseCalendarContext {
public:
    NativeChineseCalendarContext(
        const NativeCalcContext& astronomy,
        int mode,
        int day_boundary_mode,
        int utc_offset_minutes,
        double calendar_meridian_deg
    ) {
        taiyin::chinese_calendar::ChineseCalendarConfig config;
        config.mode = mode;
        config.day_boundary_mode = day_boundary_mode;
        config.utc_offset_minutes = utc_offset_minutes;
        config.calendar_meridian_deg = calendar_meridian_deg;
        require_ok(taiyin::chinese_calendar::initialize_context(
            &context_, &astronomy, &config), "ChineseCalendarContext initialization");
    }

    py::capsule core_context_capsule() {
        return py::capsule(
            &context_, taiyin_python_internal::calendar_context_capsule_name());
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
        const Status status = taiyin::chinese_calendar::fromSolar(
            &context_, &solar, &lunar, &diagnostic);
        if (status == taiyin::TAIYIN_ERROR_INVALID_ARGUMENT) {
            throw py::value_error("invalid proleptic-Gregorian solar date");
        }
        require_ok(status, "ChineseCalendarContext.from_solar");
        py::dict result;
        result["year"] = lunar.year;
        result["month"] = lunar.month;
        result["day"] = lunar.day;
        result["is_leap"] = lunar.is_leap != 0;
        result["month_days"] = lunar.month_days;
        result["month_name"] = lunar.month_name;
        return result;
    }

    py::dict from_instant_ut(const SplitJulianDate& jd_ut) const {
        taiyin::chinese_calendar::LunarDate lunar;
        EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::chinese_calendar::fromInstant(
            &context_, jd_ut, &lunar, &diagnostic),
            "ChineseCalendarContext.from_instant_ut");
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
        const Status status = taiyin::chinese_calendar::fromLunar(
            &context_, &lunar, &solar, &diagnostic);
        if (status == taiyin::TAIYIN_ERROR_INVALID_ARGUMENT) {
            throw py::value_error(
                "invalid lunar date or day exceeds the selected month's length");
        }
        if (status == taiyin::TAIYIN_EVENT_ERROR_NOT_FOUND) {
            throw py::value_error(
                "the requested lunar month does not exist in that lunar year");
        }
        require_ok(status, "ChineseCalendarContext.from_lunar");
        py::dict result;
        result["year"] = solar.year;
        result["month"] = solar.month;
        result["day"] = solar.day;
        return result;
    }

    int month_days(int year, int month, bool is_leap) const {
        uint8_t result = 0;
        EphemerisEvalDiagnostic diagnostic;
        const Status status = taiyin::chinese_calendar::getLunarMonthNum(
            &context_, year, static_cast<uint8_t>(month), is_leap, &result,
            &diagnostic);
        if (status == taiyin::TAIYIN_ERROR_INVALID_ARGUMENT) {
            throw py::value_error("invalid lunar year or month");
        }
        if (status == taiyin::TAIYIN_EVENT_ERROR_NOT_FOUND) {
            throw py::value_error(
                "the requested lunar month does not exist in that lunar year");
        }
        require_ok(status, "ChineseCalendarContext.get_month_days");
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

template <typename T>
bool callback_matches(
    const std::map<int,std::shared_ptr<T> >& callbacks,
    int id,
    const std::shared_ptr<T>& expected
) {
    const std::shared_ptr<T> current=find_callback(callbacks,id);
    return current && current.get()==expected.get();
}

Status target_position_callback(
    const TaiyinNativeCalcContext* context,
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
    const TaiyinNativeCalcContext* context,
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
    TargetRegistration(int target_id,const std::shared_ptr<TargetCallback>& callback)
        : target_id_(target_id), callback_(callback), closed_(false) {}
    ~TargetRegistration() { close(); }
    int target_id() const { return target_id_; }
    bool is_closed() const {
        if(closed_) return true;
        std::lock_guard<std::mutex> lock(callback_mutex);
        return !callback_matches(target_callbacks,target_id_,callback_);
    }
    void close() {
        if (closed_) return;
        std::lock_guard<std::mutex> lock(callback_mutex);
        if(callback_matches(target_callbacks,target_id_,callback_)) {
            taiyin::runtime::unregister_global_native_position_evaluator(target_id_);
            target_callbacks.erase(target_id_);
        }
        closed_ = true;
    }
private:
    int target_id_;
    std::shared_ptr<TargetCallback> callback_;
    bool closed_;
};

class AyanamshaRegistration {
public:
    AyanamshaRegistration(int model_id,const std::shared_ptr<AyanamshaCallback>& callback)
        : model_id_(model_id), callback_(callback), closed_(false) {}
    ~AyanamshaRegistration() { close(); }
    int model_id() const { return model_id_; }
    bool is_closed() const {
        if(closed_) return true;
        std::lock_guard<std::mutex> lock(callback_mutex);
        return !callback_matches(ayanamsha_callbacks,model_id_,callback_);
    }
    void close() {
        if (closed_) return;
        std::lock_guard<std::mutex> lock(callback_mutex);
        if (callback_matches(ayanamsha_callbacks,model_id_,callback_)) {
            taiyin::astrology::remove_ayanamsha_model_if_matches(
                model_id_, &ayanamsha_callback, callback_.get());
            ayanamsha_callbacks.erase(model_id_);
        }
        closed_ = true;
    }
private:
    int model_id_;
    std::shared_ptr<AyanamshaCallback> callback_;
    bool closed_;
};

class HouseRegistration {
public:
    HouseRegistration(int model_id,const std::shared_ptr<HouseCallback>& callback)
        : model_id_(model_id), callback_(callback), closed_(false) {}
    ~HouseRegistration() {
        try { close(); } catch (...) {}
    }
    int model_id() const { return model_id_; }
    bool is_closed() const {
        if(closed_) return true;
        std::lock_guard<std::mutex> lock(callback_mutex);
        return !callback_matches(house_callbacks,model_id_,callback_);
    }
    void close() {
        if (closed_) return;
        std::lock_guard<std::mutex> lock(callback_mutex);
        if (callback_matches(house_callbacks,model_id_,callback_)) {
            const taiyin::astrology::HouseSystemModelRemovalResult result =
                taiyin::astrology::remove_house_system_model_if_matches(
                    model_id_, &house_callback, callback_.get());
            if (result == taiyin::astrology::HouseSystemModelRemovalResult::still_referenced) {
                throw std::runtime_error("custom house system is still used as a fallback");
            }
            house_callbacks.erase(model_id_);
        }
        closed_ = true;
    }
private:
    int model_id_;
    std::shared_ptr<HouseCallback> callback_;
    bool closed_;
};

void clear_target_callbacks() {
    std::lock_guard<std::mutex> lock(callback_mutex);
    for(std::map<int,std::shared_ptr<TargetCallback> >::const_iterator it=target_callbacks.begin();
        it!=target_callbacks.end();++it) {
        taiyin::runtime::unregister_global_native_position_evaluator(it->first);
    }
    target_callbacks.clear();
}

void clear_ayanamsha_callbacks() {
    std::lock_guard<std::mutex> lock(callback_mutex);
    for(std::map<int,std::shared_ptr<AyanamshaCallback> >::const_iterator it=ayanamsha_callbacks.begin();
        it!=ayanamsha_callbacks.end();++it) {
        taiyin::astrology::remove_ayanamsha_model_if_matches(
            it->first,&ayanamsha_callback,it->second.get());
    }
    ayanamsha_callbacks.clear();
}

void clear_house_callbacks() {
    std::lock_guard<std::mutex> lock(callback_mutex);
    while(!house_callbacks.empty()) {
        bool removed=false;
        for(std::map<int,std::shared_ptr<HouseCallback> >::iterator it=house_callbacks.begin();
            it!=house_callbacks.end();) {
            const taiyin::astrology::HouseSystemModelRemovalResult result=
                taiyin::astrology::remove_house_system_model_if_matches(
                    it->first,&house_callback,it->second.get());
            if(result==taiyin::astrology::HouseSystemModelRemovalResult::still_referenced) {
                ++it;
            } else {
                it=house_callbacks.erase(it);
                removed=true;
            }
        }
        if(!removed) throw std::runtime_error("custom house-system fallback cycle prevents clearing");
    }
}

const taiyin_python_internal::CoreApiV1 kCoreApiV1 = {
    taiyin_python_internal::kCoreApiVersion,
    sizeof(taiyin_python_internal::CoreApiV1),
    &taiyin::chinese_calendar::make_ganzhi,
    &taiyin::chinese_calendar::advance_ganzhi,
    &taiyin::chinese_calendar::get_month_ganzhi,
    &taiyin::chinese_calendar::get_hour_ganzhi,
    &taiyin::chinese_calendar::calculate_day_pillar,
    &taiyin::chinese_calendar::get_nayin_id,
    &taiyin::split_julian_date_is_finite,
    &taiyin::julian_day_split,
    &taiyin::reverse_julian_day_split,
    &taiyin::add_days_to_split_jd,
    static_cast<double (*)(
        const SplitJulianDate&, const SplitJulianDate&)>(
            &taiyin::days_between_split_jd),
    &taiyin::chinese_calendar::getPrevJie,
    &taiyin::chinese_calendar::getNextJie,
};

}  // namespace

PYBIND11_MODULE(_native, module) {
    module.doc() = "Direct pybind11 bindings for Taiyin Ephemeris";
    module.attr("__version__") = "1.0.0a2";
    module.attr("_C_API") = py::capsule(
        const_cast<taiyin_python_internal::CoreApiV1*>(&kCoreApiV1),
        taiyin_python_internal::core_api_capsule_name());
    module.attr("POSITION_NONUT") = taiyin::runtime::TAIYIN_NATIVE_POSITION_NONUT;
    module.def("binding_backend", []() { return "pybind11"; });
    module.def("_star_catalog_add_tsc1", [](const std::string& path) {
        require_ok(taiyin::runtime::add_global_tsc1_star_catalog(path.c_str()), "StarCatalog.add_tsc1");
    });
    module.def("_star_catalog_add_tsc1_bytes", [](py::bytes data) {
        const std::string value = data;
        require_ok(taiyin::runtime::add_global_tsc1_star_catalog_from_memory(
            reinterpret_cast<const uint8_t*>(value.data()), value.size()), "StarCatalog.add_tsc1_bytes");
    });
    module.def("_star_catalog_add_tsf1", [](const std::string& path) {
        require_ok(taiyin::runtime::add_global_tsf1_star_catalog(path.c_str()), "StarCatalog.add_tsf1");
    });
    module.def("_star_catalog_clear", []() { taiyin::runtime::clear_global_star_catalogs(); });
    module.def("_star_catalog_count", []() { return taiyin::runtime::global_star_catalog_count(); });
    module.def("_star_find_magnitude", [](const std::string& key) {
        double value = NAN; require_ok(taiyin::runtime::find_global_star_magnitude(key.c_str(), &value), "StarCatalog.magnitude_of"); return value;
    });

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
    py::class_<taiyin::runtime::SolarEclipsePathPoint>(module, "_SolarEclipsePathPoint")
        .def_property_readonly("coordinateTt", [](const taiyin::runtime::SolarEclipsePathPoint& value) {
            return value.jd_tt;
        })
        .def_property_readonly("coordinateUt1", [](const taiyin::runtime::SolarEclipsePathPoint& value) {
            return value.jd_ut;
        })
        .def_readonly("latitudeDegrees", &taiyin::runtime::SolarEclipsePathPoint::latitude_deg)
        .def_readonly("longitudeDegrees", &taiyin::runtime::SolarEclipsePathPoint::longitude_deg)
        .def_readonly("elevationMeters", &taiyin::runtime::SolarEclipsePathPoint::elevation_m)
        .def_readonly("sunAltitudeDegrees", &taiyin::runtime::SolarEclipsePathPoint::sun_altitude_deg)
        .def_readonly("sunAzimuthDegrees", &taiyin::runtime::SolarEclipsePathPoint::sun_azimuth_deg)
        .def_property_readonly("intersectsEarth", [](const taiyin::runtime::SolarEclipsePathPoint& value) {
            return std::isfinite(value.latitude_deg) && std::isfinite(value.longitude_deg);
        });
    py::class_<taiyin::runtime::SolarEclipseWhere>(module, "SolarEclipseWhere")
        .def_property_readonly("coordinateTt", [](const taiyin::runtime::SolarEclipseWhere& value) {
            return value.jd_tt;
        })
        .def_property_readonly("coordinateUt1", [](const taiyin::runtime::SolarEclipseWhere& value) {
            return value.jd_ut;
        })
        .def_property_readonly("centerLine", [](const taiyin::runtime::SolarEclipseWhere& value)
            -> const taiyin::runtime::SolarEclipsePathPoint& { return value.center_line; },
            py::return_value_policy::reference_internal)
        .def_property_readonly("penumbralNorthLimit", [](const taiyin::runtime::SolarEclipseWhere& value)
            -> const taiyin::runtime::SolarEclipsePathPoint& { return value.penumbral_north_limit; },
            py::return_value_policy::reference_internal)
        .def_property_readonly("penumbralSouthLimit", [](const taiyin::runtime::SolarEclipseWhere& value)
            -> const taiyin::runtime::SolarEclipsePathPoint& { return value.penumbral_south_limit; },
            py::return_value_policy::reference_internal)
        .def_property_readonly("northLimit", [](const taiyin::runtime::SolarEclipseWhere& value)
            -> const taiyin::runtime::SolarEclipsePathPoint& { return value.north_limit; },
            py::return_value_policy::reference_internal)
        .def_property_readonly("southLimit", [](const taiyin::runtime::SolarEclipseWhere& value)
            -> const taiyin::runtime::SolarEclipsePathPoint& { return value.south_limit; },
            py::return_value_policy::reference_internal)
        .def_readonly("magnitude", &taiyin::runtime::SolarEclipseWhere::magnitude)
        .def_readonly("obscuration", &taiyin::runtime::SolarEclipseWhere::obscuration)
        .def_readonly("centerSeparationDegrees", &taiyin::runtime::SolarEclipseWhere::center_separation_deg)
        .def_readonly("sunAngularRadiusDegrees", &taiyin::runtime::SolarEclipseWhere::sun_angular_radius_deg)
        .def_readonly("moonAngularRadiusDegrees", &taiyin::runtime::SolarEclipseWhere::moon_angular_radius_deg)
        .def_property_readonly("hasRoute", [](const taiyin::runtime::SolarEclipseWhere& value) {
            const taiyin::runtime::SolarEclipsePathPoint* points[] = {
                &value.center_line, &value.penumbral_north_limit,
                &value.penumbral_south_limit, &value.north_limit, &value.south_limit};
            for (const taiyin::runtime::SolarEclipsePathPoint* point : points) {
                if (std::isfinite(point->latitude_deg) && std::isfinite(point->longitude_deg)) return true;
            }
            return false;
        });
    py::class_<PyLocalSolarEclipseCircumstances>(module, "LocalSolarEclipseCircumstances")
        .def_readonly("coordinate", &PyLocalSolarEclipseCircumstances::coordinate)
        .def_property_readonly("deltaTSeconds", [](const PyLocalSolarEclipseCircumstances& value) -> py::object {
            return std::isfinite(value.delta_t_seconds)
                ? py::cast(value.delta_t_seconds)
                : py::none();
        })
        .def_readonly("magnitude", &PyLocalSolarEclipseCircumstances::magnitude)
        .def_readonly("obscuration", &PyLocalSolarEclipseCircumstances::obscuration)
        .def_readonly("centerSeparationDegrees", &PyLocalSolarEclipseCircumstances::center_separation_deg)
        .def_readonly("sunAngularRadiusDegrees", &PyLocalSolarEclipseCircumstances::sun_angular_radius_deg)
        .def_readonly("moonAngularRadiusDegrees", &PyLocalSolarEclipseCircumstances::moon_angular_radius_deg)
        .def_readonly("sunAltitudeDegrees", &PyLocalSolarEclipseCircumstances::sun_altitude_deg)
        .def_readonly("sunAzimuthDegrees", &PyLocalSolarEclipseCircumstances::sun_azimuth_deg);
    py::class_<NativeCalcContext>(module, "NativeContext")
        .def(py::init<>())
        .def("_core_context_capsule", [](NativeCalcContext& context) {
            return py::capsule(
                static_cast<TaiyinNativeCalcContext*>(&context),
                taiyin_python_internal::native_context_capsule_name());
        })
        .def("clone", [](const NativeCalcContext& source) {
            std::unique_ptr<NativeCalcContext> context(new NativeCalcContext(source));
            context->apparent_options.model_context = &context->model_context;
            return context;
        })
        .def_property_readonly("last_status", [](const NativeCalcContext& context) {
            return context.last_status();
        })
        .def_property_readonly("last_operation", [](const NativeCalcContext& context) -> py::object {
            const char* operation = context.last_operation();
            return operation ? py::cast(operation) : py::none();
        })
        .def_property_readonly("has_last_diagnostic", [](const NativeCalcContext& context) {
            return context.has_last_diagnostic();
        })
        .def_property_readonly("last_diagnostic", [](const NativeCalcContext& context) -> py::object {
            if (!context.has_last_diagnostic()) return py::none();
            return diagnostic_to_dict(context.last_diagnostic());
        })
        .def("_begin_operation", [](const NativeCalcContext& context,
                                     const std::string& operation) {
            context.begin_operation(operation);
        })
        .def("_record_last_diagnostic", [](const NativeCalcContext& context,
                                             const py::dict& diagnostic,
                                             const std::string& operation) {
            const EphemerisEvalDiagnostic native_diagnostic = diagnostic_from_dict(diagnostic);
            context.record_diagnostic(native_diagnostic.status, operation, native_diagnostic);
        })
        .def("_record_last_status", [](const NativeCalcContext& context,
                                         int status,
                                         const std::string& operation) {
            context.record_status(static_cast<Status>(status), operation);
        })
        .def("position_at_tdb", [](const NativeCalcContext& context, int target_id,
                                    const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                    uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_at_tdb",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_tdb(
                        &context, target_id, jd_tdb, jd_tt, flags, out, diagnostic);
                });
            return position_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_tt", [](const NativeCalcContext& context, int target_id,
                                   const SplitJulianDate& jd_tt, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_at_tt",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_tt(
                        &context, target_id, jd_tt, flags, out, diagnostic);
                });
            return position_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_at_ut1", [](const NativeCalcContext& context, int target_id,
                                    const SplitJulianDate& jd_ut1, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_at_ut1",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_ut(
                        &context, target_id, jd_ut1, flags, out, diagnostic);
                });
            return position_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("position_at_ut1_with_delta_t", [](const NativeCalcContext& context, int target_id,
                                                 const SplitJulianDate& jd_ut1,
                                                 double delta_t_seconds, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context,
                "EphemerisContext.position_at_ut1_with_delta_t",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_ut_delta_t(
                        &context, target_id, jd_ut1, delta_t_seconds, flags, out, diagnostic);
                });
            return position_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("delta_t_seconds"), py::arg("flags") = 0)
        .def("position_at_utc", [](const NativeCalcContext& context, int target_id,
                                    const taiyin::CalendarDateTime& utc, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_at_utc",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_utc(
                        &context, target_id, utc, flags, out, diagnostic);
                });
            return position_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("utc"), py::arg("flags") = 0)
        .def("position_values_at_tdb", [](const NativeCalcContext& context, int target_id,
                                           const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                           uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_values_at_tdb",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_tdb(
                        &context, target_id, jd_tdb, jd_tt, flags, out, diagnostic);
                });
            return position_values_to_tuple(out, flags);
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_values_at_tt", [](const NativeCalcContext& context, int target_id,
                                          const SplitJulianDate& jd_tt, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_values_at_tt",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_tt(
                        &context, target_id, jd_tt, flags, out, diagnostic);
                });
            return position_values_to_tuple(out, flags);
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_values_at_ut1", [](const NativeCalcContext& context, int target_id,
                                           const SplitJulianDate& jd_ut1, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_values_at_ut1",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_ut(
                        &context, target_id, jd_ut1, flags, out, diagnostic);
                });
            return position_values_to_tuple(out, flags);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("position_values_at_ut1_with_delta_t", [](const NativeCalcContext& context, int target_id,
                                                        const SplitJulianDate& jd_ut1,
                                                        double delta_t_seconds, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context,
                "EphemerisContext.position_values_at_ut1_with_delta_t",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_ut_delta_t(
                        &context, target_id, jd_ut1, delta_t_seconds, flags, out, diagnostic);
                });
            return position_values_to_tuple(out, flags);
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("delta_t_seconds"), py::arg("flags") = 0)
        .def("position_values_at_utc", [](const NativeCalcContext& context, int target_id,
                                           const taiyin::CalendarDateTime& utc, uint32_t flags) {
            double out[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            call_with_context_diagnostic(context, "EphemerisContext.position_values_at_utc",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_position_utc(
                        &context, target_id, utc, flags, out, diagnostic);
                });
            return position_values_to_tuple(out, flags);
        }, py::arg("target_id"), py::arg("utc"), py::arg("flags") = 0)
        .def("positions_at_tt", [](const NativeCalcContext& context,
                                    const std::vector<int>& target_ids,
                                    const SplitJulianDate& jd_tt, uint32_t flags) {
            std::vector<double> values(target_ids.size() * 6u, 0.0);
            std::vector<EphemerisEvalDiagnostic> diagnostics(target_ids.size());
            const Status status = taiyin::runtime::calc_positions_tt(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_tt,
                flags, values.empty() ? 0 : &values[0],
                diagnostics.empty() ? 0 : &diagnostics[0]);
            if (diagnostics.empty()) context.record_status(status, "EphemerisContext.positions_at_tt");
            else context.record_diagnostic(status, "EphemerisContext.positions_at_tt", diagnostics.back());
            require_ok(status, "EphemerisContext.positions_at_tt");
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
            const Status status = taiyin::runtime::calc_positions_ut(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_ut1,
                flags, values.empty() ? 0 : &values[0],
                diagnostics.empty() ? 0 : &diagnostics[0]);
            if (diagnostics.empty()) context.record_status(status, "EphemerisContext.positions_at_ut1");
            else context.record_diagnostic(status, "EphemerisContext.positions_at_ut1", diagnostics.back());
            require_ok(status, "EphemerisContext.positions_at_ut1");
            py::list result;
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.append(position_result_to_dict(&values[index * 6u], diagnostics[index]));
            }
            return result;
        }, py::arg("target_ids"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("position_values_at_tt", [](const NativeCalcContext& context,
                                           const std::vector<int>& target_ids,
                                           const SplitJulianDate& jd_tt, uint32_t flags) {
            std::vector<double> values(target_ids.size() * 6u, 0.0);
            const Status status = taiyin::runtime::calc_positions_tt(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_tt,
                flags, values.empty() ? 0 : &values[0], 0);
            context.record_status(status, "EphemerisContext.position_values_at_tt");
            require_ok(status, "EphemerisContext.position_values_at_tt");
            py::list result;
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.append(position_values_to_tuple(&values[index * 6u], flags));
            }
            return result;
        }, py::arg("target_ids"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("position_values_at_ut1", [](const NativeCalcContext& context,
                                            const std::vector<int>& target_ids,
                                            const SplitJulianDate& jd_ut1, uint32_t flags) {
            std::vector<double> values(target_ids.size() * 6u, 0.0);
            const Status status = taiyin::runtime::calc_positions_ut(
                &context, target_ids.empty() ? 0 : &target_ids[0], target_ids.size(), jd_ut1,
                flags, values.empty() ? 0 : &values[0], 0);
            context.record_status(status, "EphemerisContext.position_values_at_ut1");
            require_ok(status, "EphemerisContext.position_values_at_ut1");
            py::list result;
            for (std::size_t index = 0; index < target_ids.size(); ++index) {
                result.append(position_values_to_tuple(&values[index * 6u], flags));
            }
            return result;
        }, py::arg("target_ids"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("state_at_tdb", [](const NativeCalcContext& context, int target_id,
                                 const SplitJulianDate& jd_tdb, const SplitJulianDate& jd_tt,
                                 uint32_t flags) {
            CartesianState out;
            call_with_context_diagnostic(context, "EphemerisContext.state_at_tdb",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_state_tdb(
                        &context, target_id, jd_tdb, jd_tt, flags, &out, diagnostic);
                });
            return state_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_tdb"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_tt", [](const NativeCalcContext& context, int target_id,
                                const SplitJulianDate& jd_tt, uint32_t flags) {
            CartesianState out;
            call_with_context_diagnostic(context, "EphemerisContext.state_at_tt",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_state_tt(
                        &context, target_id, jd_tt, flags, &out, diagnostic);
                });
            return state_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_tt"), py::arg("flags") = 0)
        .def("state_at_ut1", [](const NativeCalcContext& context, int target_id,
                                 const SplitJulianDate& jd_ut1, uint32_t flags) {
            CartesianState out;
            call_with_context_diagnostic(context, "EphemerisContext.state_at_ut1",
                [&](EphemerisEvalDiagnostic* diagnostic) {
                    return taiyin::runtime::calc_state_ut(
                        &context, target_id, jd_ut1, flags, &out, diagnostic);
                });
            return state_result_to_dict(out, context.last_diagnostic());
        }, py::arg("target_id"), py::arg("jd_ut1"), py::arg("flags") = 0)
        .def("osculating_orbit_at_tt", [](const NativeCalcContext& context, int body_id,
                                             const SplitJulianDate& jd_tt,
                                             int reference_frame_id, uint64_t flags) {
            taiyin::runtime::BodyOsculatingOrbit value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_osculating_orbit_tt(
                &context, body_id, jd_tt, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.osculating_at_tt");
            return osculating_orbit_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("jd_tt"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("osculating_orbit_at_ut1", [](const NativeCalcContext& context, int body_id,
                                              const SplitJulianDate& jd_ut1,
                                              int reference_frame_id, uint64_t flags) {
            taiyin::runtime::BodyOsculatingOrbit value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_osculating_orbit_ut(
                &context, body_id, jd_ut1, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.osculating_at_ut1");
            return osculating_orbit_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("jd_ut1"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("orbit_reference_points_at_tt", [](const NativeCalcContext& context,
                                                    int body_id,
                                                    const SplitJulianDate& jd_tt,
                                                    int reference_frame_id,
                                                    uint64_t flags) {
            taiyin::runtime::BodyOrbitReferencePoints value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_orbit_reference_points_tt(
                &context, body_id, jd_tt, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.reference_points_at_tt");
            return orbit_reference_points_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("jd_tt"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("orbit_reference_points_at_ut1", [](const NativeCalcContext& context,
                                                     int body_id,
                                                     const SplitJulianDate& jd_ut1,
                                                     int reference_frame_id,
                                                     uint64_t flags) {
            taiyin::runtime::BodyOrbitReferencePoints value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_orbit_reference_points_ut(
                &context, body_id, jd_ut1, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.reference_points_at_ut1");
            return orbit_reference_points_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("jd_ut1"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("search_body_apsis_from_tt", [](const NativeCalcContext& context,
                                                int body_id, int kind,
                                                const SplitJulianDate& start,
                                                uint64_t flags) {
            taiyin::runtime::BodyApsisSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_body_apsis_tt(
                &context, body_id,
                static_cast<taiyin::runtime::BodyApsisKind>(kind), start, flags,
                &value, &diagnostic), "Orbital.search_apsis_from_tt");
            return apsis_event_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("kind"), py::arg("start"),
           py::arg("flags") = 0)
        .def("search_body_apsis_from_ut1", [](const NativeCalcContext& context,
                                                 int body_id, int kind,
                                                 const SplitJulianDate& start,
                                                 uint64_t flags) {
            taiyin::runtime::BodyApsisSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_body_apsis_ut(
                &context, body_id,
                static_cast<taiyin::runtime::BodyApsisKind>(kind), start, flags,
                &value, &diagnostic), "Orbital.search_apsis_from_ut1");
            return apsis_event_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("kind"), py::arg("start"),
           py::arg("flags") = 0)
        .def("search_body_plane_node_from_tt", [](const NativeCalcContext& context,
                                                     int body_id, int kind,
                                                     const SplitJulianDate& start,
                                                     int reference_frame_id,
                                                     uint64_t flags) {
            taiyin::runtime::BodyNodeSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_body_plane_node_tt(
                &context, body_id, static_cast<taiyin::runtime::BodyNodeKind>(kind),
                start, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.search_plane_node_from_tt");
            return plane_node_event_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("kind"), py::arg("start"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("search_body_plane_node_from_ut1", [](const NativeCalcContext& context,
                                                      int body_id, int kind,
                                                      const SplitJulianDate& start,
                                                      int reference_frame_id,
                                                      uint64_t flags) {
            taiyin::runtime::BodyNodeSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_body_plane_node_ut(
                &context, body_id, static_cast<taiyin::runtime::BodyNodeKind>(kind),
                start, reference_frame_id, flags, &value, &diagnostic),
                "Orbital.search_plane_node_from_ut1");
            return plane_node_event_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("kind"), py::arg("start"),
           py::arg("reference_frame_id"), py::arg("flags") = 0)
        .def("next_geocentric_star_occultation_at_ut1", [](
                const NativeCalcContext& context, const std::string& star_key,
                const SplitJulianDate& start, uint64_t flags) {
            taiyin::runtime::LunarStarOccultationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_geocentric_lunar_star_occultation_ut(
                &context, star_key.c_str(), start, flags, &value, &diagnostic),
                "Occultation.next_geocentric_star_at_ut1");
            return occultation_to_dict(value, diagnostic);
        }, py::arg("star_key"), py::arg("start"), py::arg("flags") = 0)
        .def("next_local_star_occultation_at_ut1", [](
                const NativeCalcContext& context, const std::string& star_key,
                const SplitJulianDate& start, uint64_t flags) {
            taiyin::runtime::LunarStarOccultationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_local_lunar_star_occultation_ut(
                &context, star_key.c_str(), start, flags, &value, &diagnostic),
                "Occultation.next_local_star_at_ut1");
            return occultation_to_dict(value, diagnostic);
        }, py::arg("star_key"), py::arg("start"), py::arg("flags") = 0)
        .def("next_geocentric_body_occultation_at_ut1", [](
                const NativeCalcContext& context, int body_id,
                const SplitJulianDate& start, const py::object& target_radius_km,
                uint64_t flags) {
            taiyin::runtime::LunarBodyOccultationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            Status status = target_radius_km.is_none()
                ? taiyin::runtime::search_next_geocentric_lunar_body_occultation_ut(
                    &context, body_id, start, flags, &value, &diagnostic)
                : taiyin::runtime::search_next_geocentric_lunar_body_occultation_ut(
                    &context, body_id, target_radius_km.cast<double>(), start, flags,
                    &value, &diagnostic);
            require_ok(status, "Occultation.next_geocentric_body_at_ut1");
            return occultation_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("start"),
           py::arg("target_radius_kilometers") = py::none(), py::arg("flags") = 0)
        .def("next_local_body_occultation_at_ut1", [](
                const NativeCalcContext& context, int body_id,
                const SplitJulianDate& start, const py::object& target_radius_km,
                uint64_t flags) {
            taiyin::runtime::LunarBodyOccultationSearchResult value;
            EphemerisEvalDiagnostic diagnostic;
            Status status = target_radius_km.is_none()
                ? taiyin::runtime::search_next_local_lunar_body_occultation_ut(
                    &context, body_id, start, flags, &value, &diagnostic)
                : taiyin::runtime::search_next_local_lunar_body_occultation_ut(
                    &context, body_id, target_radius_km.cast<double>(), start, flags,
                    &value, &diagnostic);
            require_ok(status, "Occultation.next_local_body_at_ut1");
            return occultation_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("start"),
           py::arg("target_radius_kilometers") = py::none(), py::arg("flags") = 0)
        .def("star_occultation_local_visibility_at_ut1", [](
                const NativeCalcContext& context, const std::string& star_key,
                const py::dict& source, uint64_t flags) {
            const taiyin::runtime::LunarStarOccultationSearchResult occultation =
                occultation_from_dict(source);
            taiyin::runtime::LunarOccultationLocalVisibility value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_lunar_star_occultation_local_visibility_ut(
                &context, star_key.c_str(), &occultation, flags, &value, &diagnostic),
                "Occultation.local_star_visibility_at_ut1");
            return occultation_local_visibility_to_dict(value, diagnostic);
        }, py::arg("star_key"), py::arg("occultation"), py::arg("flags") = 0)
        .def("body_occultation_local_visibility_at_ut1", [](
                const NativeCalcContext& context, int body_id,
                const py::dict& source, uint64_t flags) {
            const taiyin::runtime::LunarBodyOccultationSearchResult occultation =
                occultation_from_dict(source);
            taiyin::runtime::LunarOccultationLocalVisibility value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_lunar_body_occultation_local_visibility_ut(
                &context, body_id, &occultation, flags, &value, &diagnostic),
                "Occultation.local_body_visibility_at_ut1");
            return occultation_local_visibility_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("occultation"), py::arg("flags") = 0)
        .def("star_occultation_where_at_ut1", [](
                const NativeCalcContext& context, const std::string& star_key,
                const py::dict& source, uint64_t flags) {
            const taiyin::runtime::LunarStarOccultationSearchResult occultation =
                occultation_from_dict(source);
            taiyin::runtime::LunarOccultationWhereResult value;
            EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::compute_lunar_star_occultation_where_ut(
                &context, star_key.c_str(), &occultation, flags, &value, &diagnostic),
                "Occultation.star_where_at_ut1");
            return occultation_where_to_dict(value, diagnostic);
        }, py::arg("star_key"), py::arg("occultation"), py::arg("flags") = 0)
        .def("body_occultation_where_at_ut1", [](
                const NativeCalcContext& context, int body_id,
                const py::dict& source, const py::object& target_radius_km,
                uint64_t flags) {
            const taiyin::runtime::LunarBodyOccultationSearchResult occultation =
                occultation_from_dict(source);
            taiyin::runtime::LunarOccultationWhereResult value;
            EphemerisEvalDiagnostic diagnostic;
            Status status = target_radius_km.is_none()
                ? taiyin::runtime::compute_lunar_body_occultation_where_ut(
                    &context, body_id, &occultation, flags, &value, &diagnostic)
                : taiyin::runtime::compute_lunar_body_occultation_where_ut(
                    &context, body_id, target_radius_km.cast<double>(), &occultation,
                    flags, &value, &diagnostic);
            require_ok(status, "Occultation.body_where_at_ut1");
            return occultation_where_to_dict(value, diagnostic);
        }, py::arg("body_id"), py::arg("occultation"),
           py::arg("target_radius_kilometers") = py::none(), py::arg("flags") = 0)
        .def("solve_lunar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& estimate,
                                                 uint64_t flags) {
            taiyin::runtime::LunarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_lunar_eclipse_at(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_lunar_at_tt", diagnostic);
            return lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("solve_lunar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                  const SplitJulianDate& estimate,
                                                  uint64_t flags) {
            taiyin::runtime::LunarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_lunar_eclipse_at_ut(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_lunar_at_ut1", diagnostic);
            return lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("next_lunar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                const SplitJulianDate& start,
                                                uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LunarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_lunar_eclipse_tt(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_lunar_at_tt", diagnostic);
            return lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("next_lunar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& start,
                                                 uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LunarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_lunar_eclipse_ut(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_lunar_at_ut1", diagnostic);
            return lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("lunar_eclipses_at_tt", [](const NativeCalcContext& context,
                                           const SplitJulianDate& start,
                                           const SplitJulianDate& end,
                                           uint32_t kinds, uint64_t flags, size_t capacity) {
            std::vector<taiyin::runtime::LunarEclipseResult> values(capacity);
            size_t count = 0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_lunar_eclipses_tt(
                &context, start, end, kinds, flags, values.empty() ? 0 : &values[0],
                capacity, &count, &diagnostic), "Eclipse.lunar_eclipses_at_tt", diagnostic);
            if (count > capacity) throw std::runtime_error("native lunar eclipse count exceeds capacity");
            py::list rows; for (size_t i = 0; i < count; ++i) rows.append(lunar_eclipse_to_dict(values[i], diagnostic));
            py::dict result; result["values"] = rows; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        }, py::arg("start"), py::arg("end"), py::arg("kinds") = 0,
           py::arg("flags") = 0, py::arg("capacity") = 16)
        .def("lunar_eclipses_at_ut1", [](const NativeCalcContext& context,
                                            const SplitJulianDate& start,
                                            const SplitJulianDate& end,
                                            uint32_t kinds, uint64_t flags, size_t capacity) {
            std::vector<taiyin::runtime::LunarEclipseResultUt> values(capacity);
            size_t count = 0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_lunar_eclipses_ut(
                &context, start, end, kinds, flags, values.empty() ? 0 : &values[0],
                capacity, &count, &diagnostic), "Eclipse.lunar_eclipses_at_ut1", diagnostic);
            if (count > capacity) throw std::runtime_error("native lunar eclipse count exceeds capacity");
            py::list rows; for (size_t i = 0; i < count; ++i) rows.append(lunar_eclipse_to_dict(values[i], diagnostic));
            py::dict result; result["values"] = rows; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        }, py::arg("start"), py::arg("end"), py::arg("kinds") = 0,
           py::arg("flags") = 0, py::arg("capacity") = 16)
        .def("solve_solar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& estimate,
                                                 uint64_t flags) {
            taiyin::runtime::SolarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_solar_eclipse_at(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_solar_at_tt", diagnostic);
            return solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("solve_solar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                  const SplitJulianDate& estimate,
                                                  uint64_t flags) {
            taiyin::runtime::SolarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_solar_eclipse_at_ut(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_solar_at_ut1", diagnostic);
            return solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("next_solar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                const SplitJulianDate& start,
                                                uint32_t kinds, uint64_t flags) {
            taiyin::runtime::SolarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_solar_eclipse_tt(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_solar_at_tt", diagnostic);
            return solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("next_solar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& start,
                                                 uint32_t kinds, uint64_t flags) {
            taiyin::runtime::SolarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_solar_eclipse_ut(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_solar_at_ut1", diagnostic);
            return solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("solar_eclipses_at_tt", [](const NativeCalcContext& context,
                                           const SplitJulianDate& start,
                                           const SplitJulianDate& end,
                                           uint32_t kinds, uint64_t flags, size_t capacity) {
            std::vector<taiyin::runtime::SolarEclipseResult> values(capacity);
            size_t count = 0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_solar_eclipses_tt(
                &context, start, end, kinds, flags, values.empty() ? 0 : &values[0],
                capacity, &count, &diagnostic), "Eclipse.solar_eclipses_at_tt", diagnostic);
            if (count > capacity) throw std::runtime_error("native solar eclipse count exceeds capacity");
            py::list rows; for (size_t i = 0; i < count; ++i) rows.append(solar_eclipse_to_dict(values[i], diagnostic));
            py::dict result; result["values"] = rows; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        }, py::arg("start"), py::arg("end"), py::arg("kinds") = 0,
           py::arg("flags") = 0, py::arg("capacity") = 16)
        .def("solar_eclipses_at_ut1", [](const NativeCalcContext& context,
                                            const SplitJulianDate& start,
                                            const SplitJulianDate& end,
                                            uint32_t kinds, uint64_t flags, size_t capacity) {
            std::vector<taiyin::runtime::SolarEclipseResultUt> values(capacity);
            size_t count = 0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_solar_eclipses_ut(
                &context, start, end, kinds, flags, values.empty() ? 0 : &values[0],
                capacity, &count, &diagnostic), "Eclipse.solar_eclipses_at_ut1", diagnostic);
            if (count > capacity) throw std::runtime_error("native solar eclipse count exceeds capacity");
            py::list rows; for (size_t i = 0; i < count; ++i) rows.append(solar_eclipse_to_dict(values[i], diagnostic));
            py::dict result; result["values"] = rows; result["diagnostic"] = diagnostic_to_dict(diagnostic); return result;
        }, py::arg("start"), py::arg("end"), py::arg("kinds") = 0,
           py::arg("flags") = 0, py::arg("capacity") = 16)
        .def("local_lunar_visibility_at_tt", [](const NativeCalcContext& context,
                                                    const py::dict& source, uint64_t flags) {
            const taiyin::runtime::LunarEclipseResult eclipse = lunar_eclipse_tt_from_dict(source);
            taiyin::runtime::LocalLunarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_lunar_eclipse_visibility_tt(
                &context, &eclipse, flags, &value, &diagnostic), "Eclipse.local_lunar_visibility_at_tt", diagnostic);
            return local_lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("eclipse"), py::arg("flags") = 0)
        .def("local_lunar_visibility_at_ut1", [](const NativeCalcContext& context,
                                                     const py::dict& source, uint64_t flags) {
            const taiyin::runtime::LunarEclipseResultUt eclipse = lunar_eclipse_ut_from_dict(source);
            taiyin::runtime::LocalLunarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_lunar_eclipse_visibility_ut(
                &context, &eclipse, flags, &value, &diagnostic), "Eclipse.local_lunar_visibility_at_ut1", diagnostic);
            return local_lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("eclipse"), py::arg("flags") = 0)
        .def("next_local_lunar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                      const SplitJulianDate& start,
                                                      uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LocalLunarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_local_lunar_eclipse_tt(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_local_lunar_at_tt", diagnostic);
            return local_lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("next_local_lunar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& start,
                                                       uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LocalLunarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_local_lunar_eclipse_ut(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_local_lunar_at_ut1", diagnostic);
            return local_lunar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("solve_local_solar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& estimate, uint64_t flags) {
            taiyin::runtime::LocalSolarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_local_solar_eclipse_at_tt(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_local_solar_at_tt", diagnostic);
            return local_solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("solve_local_solar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                        const SplitJulianDate& estimate, uint64_t flags) {
            taiyin::runtime::LocalSolarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::solve_local_solar_eclipse_at_ut(
                &context, estimate, flags, &value, &diagnostic), "Eclipse.solve_local_solar_at_ut1", diagnostic);
            return local_solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("estimate"), py::arg("flags") = 0)
        .def("next_local_solar_eclipse_at_tt", [](const NativeCalcContext& context,
                                                      const SplitJulianDate& start,
                                                      uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LocalSolarEclipseResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_local_solar_eclipse_tt(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_local_solar_at_tt", diagnostic);
            return local_solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("next_local_solar_eclipse_at_ut1", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& start,
                                                       uint32_t kinds, uint64_t flags) {
            taiyin::runtime::LocalSolarEclipseResultUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::search_next_local_solar_eclipse_ut(
                &context, start, kinds, flags, &value, &diagnostic), "Eclipse.next_local_solar_at_ut1", diagnostic);
            return local_solar_eclipse_to_dict(value, diagnostic);
        }, py::arg("start"), py::arg("kinds") = 0, py::arg("flags") = 0)
        .def("local_solar_circumstances_at_tt", [](const NativeCalcContext& context,
                                                       const SplitJulianDate& coordinate) {
            taiyin::runtime::LocalSolarEclipseCircumstances value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_solar_circumstances_tt(
                &context, coordinate, &value, &diagnostic), "Eclipse.local_solar_circumstances_at_tt", diagnostic);
            return local_solar_circumstances_to_python(value);
        }, py::arg("coordinate"))
        .def("local_solar_circumstances_at_ut1", [](const NativeCalcContext& context,
                                                        const SplitJulianDate& coordinate) {
            taiyin::runtime::LocalSolarEclipseCircumstancesUt value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_solar_circumstances_ut(
                &context, coordinate, &value, &diagnostic), "Eclipse.local_solar_circumstances_at_ut1", diagnostic);
            return local_solar_circumstances_to_python(value);
        }, py::arg("coordinate"))
        .def("solar_besselian_elements_at_tt", [](const NativeCalcContext& context,
                                                      const SplitJulianDate& coordinate,
                                                      double t_hours) {
            taiyin::runtime::SolarBesselianElements value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_besselian_elements_tt(
                &context, coordinate, t_hours, &value, &diagnostic), "Eclipse.solar_besselian_elements_at_tt", diagnostic);
            py::dict result=besselian_elements_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        }, py::arg("coordinate"), py::arg("time_offset_hours") = 0.0)
        .def("solar_besselian_polynomial_at_tt", [](const NativeCalcContext& context,
                                                        const SplitJulianDate& coordinate,
                                                        double span_hours, double sample_step_hours,
                                                        int degree) {
            taiyin::runtime::SolarBesselianPolynomial value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_besselian_polynomial_tt(
                &context, coordinate, span_hours, sample_step_hours, degree, &value, &diagnostic),
                "Eclipse.solar_besselian_polynomial_at_tt", diagnostic);
            py::dict result=besselian_polynomial_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        }, py::arg("coordinate"), py::arg("span_hours") = 3.0,
           py::arg("sample_step_hours") = 0.25, py::arg("degree") = 3)
        .def("evaluate_solar_besselian_polynomial", [](const NativeCalcContext&,
                                                           const py::dict& source,
                                                           double t_hours) {
            const taiyin::runtime::SolarBesselianPolynomial polynomial=besselian_polynomial_from_dict(source);
            taiyin::runtime::SolarBesselianElements value;
            require_ok(taiyin::runtime::evaluate_solar_besselian_polynomial(&polynomial,t_hours,&value),
                       "Eclipse.evaluate_solar_besselian_polynomial");
            return besselian_elements_to_dict(value);
        }, py::arg("polynomial"), py::arg("time_offset_hours"))
        .def("solar_eclipse_where_at_tt", [](const NativeCalcContext& context,
                                                const SplitJulianDate& coordinate,
                                                uint64_t flags) {
            taiyin::runtime::SolarEclipseWhere value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_where_tt(
                &context,coordinate,flags,&value,&diagnostic),"Eclipse.solar_eclipse_where_at_tt", diagnostic);
            return value;
        }, py::arg("coordinate"), py::arg("flags")=0)
        .def("solar_eclipse_where_at_ut1", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& coordinate,
                                                 uint64_t flags) {
            taiyin::runtime::SolarEclipseWhere value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_where_ut(
                &context,coordinate,flags,&value,&diagnostic),"Eclipse.solar_eclipse_where_at_ut1", diagnostic);
            return value;
        }, py::arg("coordinate"), py::arg("flags")=0)
        .def("solar_eclipse_route_row_at_tt", [](const NativeCalcContext& context,
                                                     const SplitJulianDate& coordinate,
                                                     uint64_t flags) {
            taiyin::runtime::SolarEclipseRouteRow value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_row_tt(
                &context,coordinate,flags,&value,&diagnostic),"Eclipse.solar_eclipse_route_row_at_tt", diagnostic);
            py::dict result=solar_route_row_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        }, py::arg("coordinate"), py::arg("flags")=0)
        .def("solar_eclipse_route_row_at_ut1", [](const NativeCalcContext& context,
                                                      const SplitJulianDate& coordinate,
                                                      uint64_t flags) {
            taiyin::runtime::SolarEclipseRouteRow value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_row_ut(
                &context,coordinate,flags,&value,&diagnostic),"Eclipse.solar_eclipse_route_row_at_ut1", diagnostic);
            py::dict result=solar_route_row_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        }, py::arg("coordinate"), py::arg("flags")=0)
        .def("solar_eclipse_route_at_tt", [](const NativeCalcContext& context,
                                                 const SplitJulianDate& start,
                                                 const SplitJulianDate& end,
                                                 double step_minutes,uint64_t flags,size_t capacity) {
            std::vector<taiyin::runtime::SolarEclipseRouteRow> values(capacity); size_t count=0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_tt(&context,start,end,step_minutes,flags,
                values.empty()?0:&values[0],capacity,&count,&diagnostic),"Eclipse.solar_eclipse_route_at_tt", diagnostic);
            if(count>capacity) throw std::runtime_error("native solar route count exceeds capacity");
            py::list rows; for(size_t i=0;i<count;++i) rows.append(solar_route_row_to_dict(values[i]));
            py::dict result; result["values"]=rows; result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("start"),py::arg("end"),py::arg("step_minutes"),py::arg("flags")=0,py::arg("capacity")=400)
        .def("solar_eclipse_route_at_ut1", [](const NativeCalcContext& context,
                                                  const SplitJulianDate& start,
                                                  const SplitJulianDate& end,
                                                  double step_minutes,uint64_t flags,size_t capacity) {
            std::vector<taiyin::runtime::SolarEclipseRouteRow> values(capacity); size_t count=0; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_ut(&context,start,end,step_minutes,flags,
                values.empty()?0:&values[0],capacity,&count,&diagnostic),"Eclipse.solar_eclipse_route_at_ut1", diagnostic);
            if(count>capacity) throw std::runtime_error("native solar route count exceeds capacity");
            py::list rows; for(size_t i=0;i<count;++i) rows.append(solar_route_row_to_dict(values[i]));
            py::dict result; result["values"]=rows; result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("start"),py::arg("end"),py::arg("step_minutes"),py::arg("flags")=0,py::arg("capacity")=400)
        .def("solar_eclipse_route_curves_at_tt", [](const NativeCalcContext& context,
                                                        const SplitJulianDate& coordinate,
                                                        uint64_t flags,size_t sample_count) {
            size_t count=0; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_curves_tt_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&diagnostic);
            if(count==0){require_ok_with_context_diagnostic(context,status,"Eclipse.solar_eclipse_route_curves_at_tt",diagnostic);}
            std::vector<taiyin::runtime::SolarEclipseRouteCurvePoint> values(count);
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_curves_tt_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&diagnostic),
                "Eclipse.solar_eclipse_route_curves_at_tt",diagnostic);
            py::list rows; for(size_t i=0;i<count;++i) rows.append(solar_route_curve_point_to_dict(values[i]));
            py::dict result; result["values"]=rows; result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("solar_eclipse_route_curves_at_ut1", [](const NativeCalcContext& context,
                                                         const SplitJulianDate& coordinate,
                                                         uint64_t flags,size_t sample_count) {
            size_t count=0; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_curves_ut_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&diagnostic);
            if(count==0){require_ok_with_context_diagnostic(context,status,"Eclipse.solar_eclipse_route_curves_at_ut1",diagnostic);}
            std::vector<taiyin::runtime::SolarEclipseRouteCurvePoint> values(count);
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_solar_eclipse_route_curves_ut_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&diagnostic),
                "Eclipse.solar_eclipse_route_curves_at_ut1",diagnostic);
            py::list rows; for(size_t i=0;i<count;++i) rows.append(solar_route_curve_point_to_dict(values[i]));
            py::dict result; result["values"]=rows; result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("solar_eclipse_route_product_at_tt", [](const NativeCalcContext& context,
                                                           const SplitJulianDate& coordinate,
                                                           uint64_t flags,size_t sample_count) {
            size_t count=0; taiyin::runtime::SolarEclipseRouteProductSummary summary={}; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_product_tt_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&summary,&diagnostic);
            if(count==0) require_ok(status,"Eclipse.solar_eclipse_route_product_at_tt");
            std::vector<taiyin::runtime::SolarEclipseRouteProductPoint> values(count);
            require_ok(taiyin::runtime::compute_solar_eclipse_route_product_tt_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&summary,&diagnostic),
                "Eclipse.solar_eclipse_route_product_at_tt");
            if(count>values.size()) throw std::runtime_error("native solar route product count exceeds capacity");
            py::list points; for(size_t i=0;i<count;++i) points.append(solar_route_product_point_to_dict(values[i]));
            py::dict result; result["points"]=points; result["summary"]=solar_route_product_summary_to_dict(summary);
            result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("solar_eclipse_route_product_at_ut1", [](const NativeCalcContext& context,
                                                            const SplitJulianDate& coordinate,
                                                            uint64_t flags,size_t sample_count) {
            size_t count=0; taiyin::runtime::SolarEclipseRouteProductSummary summary={}; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_product_ut_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&summary,&diagnostic);
            if(count==0) require_ok(status,"Eclipse.solar_eclipse_route_product_at_ut1");
            std::vector<taiyin::runtime::SolarEclipseRouteProductPoint> values(count);
            require_ok(taiyin::runtime::compute_solar_eclipse_route_product_ut_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&summary,&diagnostic),
                "Eclipse.solar_eclipse_route_product_at_ut1");
            if(count>values.size()) throw std::runtime_error("native solar route product count exceeds capacity");
            py::list points; for(size_t i=0;i<count;++i) points.append(solar_route_product_point_to_dict(values[i]));
            py::dict result; result["points"]=points; result["summary"]=solar_route_product_summary_to_dict(summary);
            result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("solar_eclipse_route_map_product_at_tt", [](const NativeCalcContext& context,
                                                               const SplitJulianDate& coordinate,
                                                               uint64_t flags,size_t sample_count) {
            size_t count=0; taiyin::runtime::SolarEclipseRouteProductSummary summary={}; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_map_product_tt_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&summary,&diagnostic);
            if(count==0) require_ok(status,"Eclipse.solar_eclipse_route_map_product_at_tt");
            std::vector<taiyin::runtime::SolarEclipseRouteProductPoint> values(count);
            require_ok(taiyin::runtime::compute_solar_eclipse_route_map_product_tt_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&summary,&diagnostic),
                "Eclipse.solar_eclipse_route_map_product_at_tt");
            if(count>values.size()) throw std::runtime_error("native solar route map product count exceeds capacity");
            py::list points; for(size_t i=0;i<count;++i) points.append(solar_route_product_point_to_dict(values[i]));
            py::dict result; result["points"]=points; result["summary"]=solar_route_product_summary_to_dict(summary);
            result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("solar_eclipse_route_map_product_at_ut1", [](const NativeCalcContext& context,
                                                                const SplitJulianDate& coordinate,
                                                                uint64_t flags,size_t sample_count) {
            size_t count=0; taiyin::runtime::SolarEclipseRouteProductSummary summary={}; EphemerisEvalDiagnostic diagnostic;
            Status status=taiyin::runtime::compute_solar_eclipse_route_map_product_ut_with_options(
                &context,coordinate,flags,sample_count,0,0,&count,&summary,&diagnostic);
            if(count==0) require_ok(status,"Eclipse.solar_eclipse_route_map_product_at_ut1");
            std::vector<taiyin::runtime::SolarEclipseRouteProductPoint> values(count);
            require_ok(taiyin::runtime::compute_solar_eclipse_route_map_product_ut_with_options(
                &context,coordinate,flags,sample_count,values.empty()?0:&values[0],values.size(),&count,&summary,&diagnostic),
                "Eclipse.solar_eclipse_route_map_product_at_ut1");
            if(count>values.size()) throw std::runtime_error("native solar route map product count exceeds capacity");
            py::list points; for(size_t i=0;i<count;++i) points.append(solar_route_product_point_to_dict(values[i]));
            py::dict result; result["points"]=points; result["summary"]=solar_route_product_summary_to_dict(summary);
            result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("flags")=0,py::arg("route_sample_count")=400)
        .def("local_solar_eclipse_boundary_at_tt", [](const NativeCalcContext& context,
                                                            const SplitJulianDate& coordinate,
                                                            double longitude_degrees,double latitude_degrees) {
            taiyin::runtime::LocalSolarEclipseBoundary value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_solar_eclipse_boundary_tt(
                &context,coordinate,longitude_degrees,latitude_degrees,&value,&diagnostic),
                "Eclipse.local_solar_eclipse_boundary_at_tt",diagnostic);
            py::dict result=local_solar_boundary_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("longitude_degrees"),py::arg("latitude_degrees"))
        .def("local_solar_eclipse_boundary_at_ut1", [](const NativeCalcContext& context,
                                                             const SplitJulianDate& coordinate,
                                                             double longitude_degrees,double latitude_degrees) {
            taiyin::runtime::LocalSolarEclipseBoundary value; EphemerisEvalDiagnostic diagnostic;
            require_ok_with_context_diagnostic(context, taiyin::runtime::compute_local_solar_eclipse_boundary_ut(
                &context,coordinate,longitude_degrees,latitude_degrees,&value,&diagnostic),
                "Eclipse.local_solar_eclipse_boundary_at_ut1",diagnostic);
            py::dict result=local_solar_boundary_to_dict(value); result["diagnostic"]=diagnostic_to_dict(diagnostic); return result;
        },py::arg("coordinate"),py::arg("longitude_degrees"),py::arg("latitude_degrees"))
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
        .def("reset_configuration", [](NativeCalcContext& context) {
            context = NativeCalcContext();
            context.apparent_options.model_context = &context.model_context;
        })
        .def("clear_observer_location", [](NativeCalcContext& context) {
            context.fields.clear(taiyin::runtime::TAIYIN_NATIVE_FIELD_OBSERVER_LOCATION);
            context.observer_location = taiyin::runtime::NativeObserverLocation();
        })
        .def("set_observer_location", [](NativeCalcContext& context,
                                           double longitude_degrees, double latitude_degrees,
                                           double height_meters) {
            require_ok(taiyin::runtime::native_context_set_observer_location(
                &context, taiyin::runtime::native_observer_location_degrees(
                    longitude_degrees, latitude_degrees, height_meters)),
                "ContextConfiguration.set_observer_location");
        })
        .def("set_simple_topocentric_observer", [](NativeCalcContext& context,
                                                       double longitude_degrees,
                                                       double latitude_degrees,
                                                       double height_meters,
                                                       const SplitJulianDate& jd_ut1,
                                                       const SplitJulianDate& jd_tt) {
            require_ok(taiyin::runtime::native_context_set_simple_topocentric_observer(
                &context,taiyin::runtime::native_observer_location_degrees(
                    longitude_degrees,latitude_degrees,height_meters),jd_ut1,jd_tt),
                "ContextConfiguration.set_simple_topocentric_observer");
        })
        .def("set_precise_topocentric_observer", [](NativeCalcContext& context,
                                                        double longitude_degrees,
                                                        double latitude_degrees,
                                                        double height_meters,
                                                        const SplitJulianDate& jd_utc,
                                                        const SplitJulianDate& jd_tt) {
            require_ok(taiyin::runtime::native_context_set_precise_topocentric_observer(
                &context,taiyin::runtime::native_observer_location_degrees(
                    longitude_degrees,latitude_degrees,height_meters),jd_utc,jd_tt),
                "ContextConfiguration.set_precise_topocentric_observer");
        })
        .def("set_topocentric_observer_offset", [](NativeCalcContext& context,
                                                       const std::vector<double>& values) {
            if(values.size()!=9) throw py::value_error("observer offset must contain 9 values");
            CartesianState state;
            state.position_au.x=values[0]; state.position_au.y=values[1]; state.position_au.z=values[2];
            state.velocity_au_per_day.x=values[3]; state.velocity_au_per_day.y=values[4]; state.velocity_au_per_day.z=values[5];
            state.acceleration_au_per_day2.x=values[6]; state.acceleration_au_per_day2.y=values[7]; state.acceleration_au_per_day2.z=values[8];
            require_ok(taiyin::runtime::native_context_set_topocentric_observer_offset(&context,state),
                "ContextConfiguration.set_topocentric_observer_offset");
        })
        .def("set_standard_atmosphere", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_set_atmosphere(
                &context, taiyin::runtime::native_standard_atmosphere()),
                "ContextConfiguration.set_standard_atmosphere");
        })
        .def("set_atmosphere", [](NativeCalcContext& context,double pressure_mbar,
                                      double temperature_celsius,double relative_humidity,
                                      double wavelength_micrometer) {
            taiyin::runtime::NativeAtmosphere atmosphere;
            atmosphere.pressure_mbar=pressure_mbar; atmosphere.temperature_celsius=temperature_celsius;
            atmosphere.relative_humidity=relative_humidity; atmosphere.wavelength_micrometer=wavelength_micrometer;
            require_ok(taiyin::runtime::native_context_set_atmosphere(&context,atmosphere),
                "ContextConfiguration.set_atmosphere");
        })
        .def("set_meteorological_range_km", [](NativeCalcContext& context,double range_km) {
            require_ok(taiyin::runtime::native_context_set_meteorological_range_km(&context,range_km),
                "ContextConfiguration.set_meteorological_range_km");
        })
        .def("set_atmosphere_policy", [](NativeCalcContext& context, uint32_t flags) {
            require_ok(taiyin::runtime::native_context_set_atmosphere_policy_flags(&context, flags),
                       "ContextConfiguration.set_atmosphere_policy");
        })
        .def("set_heliacal_visibility_model", [](NativeCalcContext& context, int model_id) {
            require_ok(taiyin::runtime::native_context_set_heliacal_visibility_model(&context, model_id),
                       "ContextConfiguration.set_heliacal_visibility_model");
        })
        .def("set_astro_models", [](NativeCalcContext& context,int tdb_model_id,
                                        int precession_model_id,int nutation_model_id,
                                        int obliquity_model_id,int frame_route_id) {
            context.model_context.tdb_model_id=tdb_model_id;
            context.model_context.precession_model_id=precession_model_id;
            context.model_context.nutation_model_id=nutation_model_id;
            context.model_context.obliquity_model_id=obliquity_model_id;
            context.model_context.frame_route_id=frame_route_id;
            context.apparent_options.model_context=&context.model_context;
        })
        .def("set_celestial_pole_offset", [](NativeCalcContext& context,double dx,double dy,
                                                double dx_rate,double dy_rate) {
            require_ok(taiyin::runtime::native_context_set_celestial_pole_offset(
                &context,dx,dy,dx_rate,dy_rate),"ContextConfiguration.set_celestial_pole_offset");
        })
        .def("set_refraction_model", [](NativeCalcContext& context,int model_id) {
            require_ok(taiyin::runtime::native_context_set_refraction_model(&context,model_id),
                "ContextConfiguration.set_refraction_model");
        })
        .def("use_solar_deflector", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_use_solar_deflector(&context),
                       "ContextConfiguration.use_solar_deflector");
            context.clear_owned_deflectors();
        })
        .def("clear_deflectors", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_clear_deflectors(&context),
                "ContextConfiguration.clear_deflectors");
            context.clear_owned_deflectors();
        })
        .def("set_deflectors", [](NativeCalcContext& context,
                                      const std::vector<int>& body_ids,
                                      const std::vector<double>& radii,
                                      const std::vector<double>& limits,
                                      int solar_deflector_index) {
            if(body_ids.size()!=radii.size() || body_ids.size()!=limits.size()) {
                throw py::value_error("deflector arrays must have equal lengths");
            }
            std::vector<taiyin::runtime::ApparentDeflector> values(body_ids.size());
            for(size_t i=0;i<values.size();++i) {
                values[i].body_id=body_ids[i];
                values[i].schwarzschild_radius_au=radii[i];
                values[i].limit=limits[i];
            }
            context.replace_deflectors(values,solar_deflector_index);
        })
        .def("set_light_time_iteration", [](NativeCalcContext& context,int max_iterations,
                                                double tolerance_days) {
            require_ok(taiyin::runtime::native_context_set_light_time_iteration(
                &context,max_iterations,tolerance_days),"ContextConfiguration.set_light_time_iteration");
        })
        .def("enable_shapiro_delay", [](NativeCalcContext& context,int model_id) {
            require_ok(taiyin::runtime::native_context_enable_shapiro_delay(&context,model_id),
                "ContextConfiguration.enable_shapiro_delay");
        })
        .def("disable_shapiro_delay", [](NativeCalcContext& context) {
            require_ok(taiyin::runtime::native_context_disable_shapiro_delay(&context),
                "ContextConfiguration.disable_shapiro_delay");
        })
        .def("set_eclipse_models", [](NativeCalcContext& context,int shadow_model_id,
                                         int moon_radius_model_id) {
            require_ok(taiyin::runtime::native_context_set_eclipse_shadow_model(&context,shadow_model_id),
                "ContextConfiguration.set_eclipse_models.shadow");
            require_ok(taiyin::runtime::native_context_set_eclipse_moon_radius_model(&context,moon_radius_model_id),
                "ContextConfiguration.set_eclipse_models.moon_radius");
        })
        .def("set_apparent_config", [](NativeCalcContext& context, uint32_t flags,
                                         int output_frame_id,int light_time_method_id,
                                         int shapiro_delay_model_id,int aberration_model_id,
                                         int deflection_model_id,int max_light_time_iterations,
                                         double light_time_tolerance_days,double matrix_derivative_step_days) {
            const uint32_t topocentric=context.apparent_options.flags & taiyin::TAIYIN_APPARENT_TOPOCENTRIC;
            context.apparent_options.flags = flags|topocentric;
            context.apparent_options.output_frame_id = output_frame_id;
            context.apparent_options.light_time_method_id=light_time_method_id;
            context.apparent_options.shapiro_delay_model_id=shapiro_delay_model_id;
            context.apparent_options.aberration_model_id=aberration_model_id;
            context.apparent_options.deflection_model_id=deflection_model_id;
            context.apparent_options.max_light_time_iterations=max_light_time_iterations;
            context.apparent_options.light_time_tolerance_days=light_time_tolerance_days;
            context.apparent_options.matrix_derivative_step_days=matrix_derivative_step_days;
            context.apparent_options.model_context=&context.model_context;
        })
        .def("set_allow_utc_out_of_range_estimate", [](NativeCalcContext& context,bool allow) {
            require_ok(
                taiyin::runtime::native_context_set_allow_utc_out_of_range_estimate(
                    &context,allow),
                "Time.set_allow_utc_out_of_range_estimate");
        })
        .def("set_tdb_model", [](NativeCalcContext& context,int model_id) {
            require_ok(taiyin::runtime::native_context_set_tdb_model(&context,model_id),"Time.set_tdb_model");
        })
        .def("set_delta_t_model", [](NativeCalcContext& context,int model_id,int family_id) {
            require_ok(taiyin::runtime::native_context_set_delta_t_model(
                &context,model_id,family_id),"Time.set_delta_t_model");
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
                                           const SplitJulianDate& end, int event, uint64_t flags) {
            taiyin::runtime::PlanetVisibilityEventResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_planet_transit_ut(&context, body, start, end, event, flags, &value, &diagnostic),
                       "Visibility.planet_transit_at_ut1");
            return visibility_event_to_dict(value, diagnostic);
        }, py::arg("body"), py::arg("start"), py::arg("end"), py::arg("event"),
           py::arg("flags") = 0)
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
        .def("observed_at_ut1", [](const NativeCalcContext& context, const std::vector<int>& bodies,
                                     const SplitJulianDate& ut1, uint64_t flags) {
            std::vector<taiyin::runtime::ObservedPosition> values(bodies.size());
            std::vector<EphemerisEvalDiagnostic> diagnostics(bodies.size());
            require_ok(taiyin::runtime::calc_observed_ut(&context, ut1, bodies.empty() ? 0 : &bodies[0], bodies.size(),
                flags, values.empty() ? 0 : &values[0], diagnostics.empty() ? 0 : &diagnostics[0]), "Observed.batch_at_ut1");
            py::list out; for (std::size_t i = 0; i < values.size(); ++i) out.append(observed_to_dict(values[i])); return out;
        })
        .def("star_at_tdb", [](const NativeCalcContext& context, const std::string& key,
                                  const SplitJulianDate& tdb, const SplitJulianDate& tt, uint64_t flags) {
            double values[6]; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_star_position_tdb(&context,key.c_str(),tdb,tt,flags,values,&diagnostic),"Star.at_tdb");
            return position_result_to_dict(values,diagnostic);
        })
        .def("star_at_tt", [](const NativeCalcContext& context, const std::string& key,
                                 const SplitJulianDate& tt, uint64_t flags) {
            double values[6]; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_star_position_tt(&context,key.c_str(),tt,flags,values,&diagnostic),"Star.at_tt");
            return position_result_to_dict(values,diagnostic);
        })
        .def("star_at_ut1", [](const NativeCalcContext& context, const std::string& key,
                                  const SplitJulianDate& ut1, uint64_t flags) {
            double values[6]; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_star_position_ut(&context,key.c_str(),ut1,flags,values,&diagnostic),"Star.at_ut1");
            return position_result_to_dict(values,diagnostic);
        })
        .def("star_at_ut1_with_delta_t", [](const NativeCalcContext& context, const std::string& key,
                                               const SplitJulianDate& ut1, double delta_t, uint64_t flags) {
            double values[6]; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_star_position_ut_delta_t(&context,key.c_str(),ut1,delta_t,flags,values,&diagnostic),"Star.at_ut1_with_delta_t");
            return position_result_to_dict(values,diagnostic);
        })
        .def("stars_at_tt", [](const NativeCalcContext& context, const std::vector<std::string>& keys,
                                  const SplitJulianDate& tt, uint64_t flags) {
            std::vector<const char*> raw; for(std::size_t i=0;i<keys.size();++i) raw.push_back(keys[i].c_str());
            std::vector<double> values(keys.size()*6); std::vector<EphemerisEvalDiagnostic> diagnostics(keys.size());
            taiyin::runtime::calc_star_positions_tt(&context,raw.empty()?0:&raw[0],raw.size(),tt,flags,values.empty()?0:&values[0],diagnostics.empty()?0:&diagnostics[0]);
            py::list out; for(std::size_t i=0;i<keys.size();++i) out.append(position_result_to_dict(&values[i*6],diagnostics[i])); return out;
        })
        .def("stars_at_ut1", [](const NativeCalcContext& context, const std::vector<std::string>& keys,
                                   const SplitJulianDate& ut1, uint64_t flags) {
            std::vector<const char*> raw; for(std::size_t i=0;i<keys.size();++i) raw.push_back(keys[i].c_str());
            std::vector<double> values(keys.size()*6); std::vector<EphemerisEvalDiagnostic> diagnostics(keys.size());
            taiyin::runtime::calc_star_positions_ut(&context,raw.empty()?0:&raw[0],raw.size(),ut1,flags,values.empty()?0:&values[0],diagnostics.empty()?0:&diagnostics[0]);
            py::list out; for(std::size_t i=0;i<keys.size();++i) out.append(position_result_to_dict(&values[i*6],diagnostics[i])); return out;
        })
        .def("stars_at_tdb", [](const NativeCalcContext& context, const std::vector<std::string>& keys,
                                   const SplitJulianDate& tdb, const SplitJulianDate& tt, uint64_t flags) {
            std::vector<const char*> raw; for(std::size_t i=0;i<keys.size();++i) raw.push_back(keys[i].c_str());
            std::vector<double> values(keys.size()*6); std::vector<EphemerisEvalDiagnostic> diagnostics(keys.size());
            taiyin::runtime::calc_star_positions_tdb(&context,raw.empty()?0:&raw[0],raw.size(),tdb,tt,flags,values.empty()?0:&values[0],diagnostics.empty()?0:&diagnostics[0]);
            py::list out; for(std::size_t i=0;i<keys.size();++i) out.append(position_result_to_dict(&values[i*6],diagnostics[i])); return out;
        })
        .def("stars_at_ut1_with_delta_t", [](const NativeCalcContext& context, const std::vector<std::string>& keys,
                                                const SplitJulianDate& ut1, double delta_t, uint64_t flags) {
            std::vector<const char*> raw; for(std::size_t i=0;i<keys.size();++i) raw.push_back(keys[i].c_str());
            std::vector<double> values(keys.size()*6); std::vector<EphemerisEvalDiagnostic> diagnostics(keys.size());
            taiyin::runtime::calc_star_positions_ut_delta_t(&context,raw.empty()?0:&raw[0],raw.size(),ut1,delta_t,flags,values.empty()?0:&values[0],diagnostics.empty()?0:&diagnostics[0]);
            py::list out; for(std::size_t i=0;i<keys.size();++i) out.append(position_result_to_dict(&values[i*6],diagnostics[i])); return out;
        })
        .def("observed_star_at_ut1", [](const NativeCalcContext& context, const std::string& key,
                                          const SplitJulianDate& ut1, uint64_t flags) {
            taiyin::runtime::ObservedPosition value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_observed_star_ut(&context,key.c_str(),ut1,flags,&value,&diagnostic),"Star.observed_at_ut1");
            return observed_to_dict(value);
        })
        .def("observed_stars_at_ut1", [](const NativeCalcContext& context, const std::vector<std::string>& keys,
                                           const SplitJulianDate& ut1, uint64_t flags) {
            std::vector<const char*> raw; for(std::size_t i=0;i<keys.size();++i) raw.push_back(keys[i].c_str());
            std::vector<taiyin::runtime::ObservedPosition> values(keys.size()); std::vector<EphemerisEvalDiagnostic> diagnostics(keys.size());
            require_ok(taiyin::runtime::calc_observed_stars_ut(&context,raw.empty()?0:&raw[0],raw.size(),ut1,flags,values.empty()?0:&values[0],diagnostics.empty()?0:&diagnostics[0]),"Star.observed_batch_at_ut1");
            py::list out; for(std::size_t i=0;i<keys.size();++i) out.append(observed_to_dict(values[i])); return out;
        })
        .def("observed_at_utc", [](const NativeCalcContext& context, const std::vector<int>& bodies,
                                     const taiyin::CalendarDateTime& utc, uint64_t flags) {
            std::vector<taiyin::runtime::ObservedPosition> values(bodies.size());
            std::vector<EphemerisEvalDiagnostic> diagnostics(bodies.size());
            require_ok(taiyin::runtime::calc_observed_utc(&context, utc, bodies.empty() ? 0 : &bodies[0], bodies.size(),
                flags, values.empty() ? 0 : &values[0], diagnostics.empty() ? 0 : &diagnostics[0]), "Observed.batch_at_utc");
            py::list out; for (std::size_t i = 0; i < values.size(); ++i) out.append(observed_to_dict(values[i])); return out;
        })
        .def("heliacal_body_at_ut1", [](const NativeCalcContext& context,int body,const SplitJulianDate& ut1,uint64_t flags,const py::dict& conditions) {
            const taiyin::runtime::HeliacalVisibilityConditions c=heliacal_conditions(conditions); taiyin::runtime::HeliacalVisibilityResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_body_heliacal_visibility_ut(&context,body,ut1,flags,&c,&value,&diagnostic),"Heliacal.body_at_ut1");
            py::dict out=heliacal_visibility_to_dict(value); out["diagnostic"]=diagnostic_to_dict(diagnostic); return out;
        })
        .def("heliacal_star_at_ut1", [](const NativeCalcContext& context,const std::string& key,const SplitJulianDate& ut1,uint64_t flags,const py::dict& conditions) {
            const taiyin::runtime::HeliacalVisibilityConditions c=heliacal_conditions(conditions); taiyin::runtime::HeliacalVisibilityResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::calc_star_heliacal_visibility_ut(&context,key.c_str(),ut1,flags,&c,&value,&diagnostic),"Heliacal.star_at_ut1");
            py::dict out=heliacal_visibility_to_dict(value); out["diagnostic"]=diagnostic_to_dict(diagnostic); return out;
        })
        .def("heliacal_next_body_at_ut1", [](const NativeCalcContext& context,int body,const SplitJulianDate& start,int event,double days,uint64_t flags,const py::dict& conditions) {
            const taiyin::runtime::HeliacalVisibilityConditions c=heliacal_conditions(conditions); taiyin::runtime::HeliacalVisibilitySearchResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_body_heliacal_visibility_ut(&context,body,start,event,days,flags,&c,&value,&diagnostic),"Heliacal.next_body_event_at_ut1");
            py::dict out; out["event_kind"]=value.event_kind; out["coordinate"]=value.jd_ut; out["window_start"]=value.window_start_jd_ut; out["window_end"]=value.window_end_jd_ut;
            out["scanned_day_count"]=value.scanned_day_count; out["sampled_window_count"]=value.sampled_window_count; out["visibility_evaluation_count"]=value.visibility_evaluation_count;
            out["visibility"]=heliacal_visibility_to_dict(value.visibility); out["diagnostic"]=diagnostic_to_dict(diagnostic); return out;
        })
        .def("heliacal_next_star_at_ut1", [](const NativeCalcContext& context,const std::string& key,const SplitJulianDate& start,int event,double days,uint64_t flags,const py::dict& conditions) {
            const taiyin::runtime::HeliacalVisibilityConditions c=heliacal_conditions(conditions); taiyin::runtime::HeliacalVisibilitySearchResult value; EphemerisEvalDiagnostic diagnostic;
            require_ok(taiyin::runtime::search_next_star_heliacal_visibility_ut(&context,key.c_str(),start,event,days,flags,&c,&value,&diagnostic),"Heliacal.next_star_event_at_ut1");
            py::dict out; out["event_kind"]=value.event_kind; out["coordinate"]=value.jd_ut; out["window_start"]=value.window_start_jd_ut; out["window_end"]=value.window_end_jd_ut;
            out["scanned_day_count"]=value.scanned_day_count; out["sampled_window_count"]=value.sampled_window_count; out["visibility_evaluation_count"]=value.visibility_evaluation_count;
            out["visibility"]=heliacal_visibility_to_dict(value.visibility); out["diagnostic"]=diagnostic_to_dict(diagnostic); return out;
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
        .def("_core_context_capsule",
             &NativeChineseCalendarContext::core_context_capsule)
        .def("four_pillars", &NativeChineseCalendarContext::four_pillars,
             py::arg("instant_utc"), py::arg("virtual_time"), py::arg("rat_hour_mode") = 0)
        .def("from_solar", &NativeChineseCalendarContext::from_solar)
        .def("from_instant_ut", &NativeChineseCalendarContext::from_instant_ut)
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
        .def(py::init<const std::vector<std::string>&, const std::string&, bool, bool,
                      std::size_t, bool, const std::string&, const std::string&>(),
             py::arg("source_paths") = std::vector<std::string>(),
             py::arg("data_root") = std::string(),
             py::arg("load_packaged_data") = true,
             py::arg("load_builtin_eop") = true,
             py::arg("segment_cache_max_entries") = 4096,
             py::arg("strict_discovery") = false,
             py::arg("eop_path") = std::string(),
             py::arg("lunar_limb_path") = std::string())
        .def("create_context", &EphemerisRuntime::create_context)
        .def("add_source_path", &EphemerisRuntime::add_source_path)
        .def("set_ephemeris_source_priority", &EphemerisRuntime::set_source_priority)
        .def("clear_ephemeris_source_priority", &EphemerisRuntime::clear_source_priority)
        .def("clear_all_ephemeris_source_priorities", &EphemerisRuntime::clear_all_source_priorities)
        .def("clear_ephemeris_cache", &EphemerisRuntime::clear_cache)
        .def("load_eop_table", &EphemerisRuntime::load_eop_table)
        .def("load_builtin_eop_table", &EphemerisRuntime::load_builtin_eop_table)
        .def("clear_eop_table", &EphemerisRuntime::clear_eop_table)
        .def_property_readonly("has_eop_table", &EphemerisRuntime::has_eop_table)
        .def("load_lunar_limb_model", &EphemerisRuntime::load_lunar_limb_model)
        .def("clear_lunar_limb_model", &EphemerisRuntime::clear_lunar_limb_model)
        .def_property_readonly("has_lunar_limb_model", &EphemerisRuntime::has_lunar_limb_model)
        .def_property_readonly("catalog_size", &EphemerisRuntime::catalog_size)
        .def_property_readonly("cache_entry_count", &EphemerisRuntime::cache_entry_count)
        .def("format_ephemeris_diagnostic", [](const EphemerisRuntime&,const py::dict& value) {
            return format_diagnostic(value);
        })
        .def_property_readonly("registered_data_sources", &EphemerisRuntime::registered_data_sources);
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
        return std::unique_ptr<TargetRegistration>(new TargetRegistration(target_id,callback));
    }, py::arg("target_id"), py::arg("position"), py::arg("state") = py::none());
    module.def("clear_custom_targets", &clear_target_callbacks);

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
        return std::unique_ptr<AyanamshaRegistration>(new AyanamshaRegistration(model_id,callback));
    }, py::arg("model_id"), py::arg("evaluator"), py::arg("reference_precession_model") = -1);
    module.def("clear_custom_ayanamsha_models", &clear_ayanamsha_callbacks);

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
        return std::unique_ptr<HouseRegistration>(new HouseRegistration(model_id,callback));
    }, py::arg("model_id"), py::arg("evaluator"), py::arg("fallback_model_id") = -1);
    module.def("clear_custom_house_system_models", &clear_house_callbacks);
    module.def("register_builtin_astrology_targets", []() {
        require_ok(taiyin::astrology::register_builtin_astrology_targets(),
            "Ephemeris.register_builtin_astrology_targets");
    });

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
                                               int mode, int day_boundary_mode,
                                               int utc_offset_minutes,
                                               double calendar_meridian_deg) {
        return NativeChineseCalendarContext(
            astronomy, mode, day_boundary_mode, utc_offset_minutes,
            calendar_meridian_deg);
    }, py::arg("astronomy"), py::arg("mode"), py::arg("day_boundary_mode"),
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
