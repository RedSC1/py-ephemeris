#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/bazi/bazi.h"
#include "taiyin/chinese_calendar/calendar.h"
#include "taiyin/runtime/ephemeris_engine.h"
#include "taiyin/runtime/native_context.h"
#include "taiyin/runtime/runtime.h"
#include "taiyin/status.h"

#include <stdexcept>
#include <string>
#include <mutex>
#include <vector>

namespace py = pybind11;

namespace {

void require_ok(taiyin::Status status, const char* operation) {
    if (status != taiyin::TAIYIN_STATUS_OK) {
        throw std::runtime_error(
            std::string(operation) + ": " + taiyin::status_message(status));
    }
}

py::dict diagnostic_to_dict(
    const taiyin::runtime::EphemerisEvalDiagnostic& value
) {
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

std::vector<uint8_t> chart_pillars(const taiyin::bazi::BaziChart& value) {
    std::vector<uint8_t> result;
    result.push_back(value.pillars.year);
    result.push_back(value.pillars.month);
    result.push_back(value.pillars.day);
    result.push_back(value.pillars.hour);
    return result;
}

py::dict chart_to_dict(const taiyin::bazi::BaziChart& value) {
    py::dict result;
    result["pillars"] = chart_pillars(value);
    result["extra"] = std::vector<uint8_t>{
        value.extra.ming_gong, value.extra.shen_gong,
        value.extra.tai_yuan, value.extra.tai_xi};

    std::vector<uint8_t> hidden_counts(value.hidden_stem_count,
        value.hidden_stem_count + 4);
    std::vector<std::vector<uint8_t> > hidden_stems(4);
    std::vector<std::vector<uint8_t> > hidden_ten_gods(4);
    for (std::size_t pillar = 0; pillar < 4; ++pillar) {
        hidden_stems[pillar].assign(value.hidden_stems[pillar],
            value.hidden_stems[pillar] + taiyin::bazi::kHiddenStemCapacity);
        hidden_ten_gods[pillar].assign(value.hidden_ten_gods[pillar],
            value.hidden_ten_gods[pillar] + taiyin::bazi::kHiddenStemCapacity);
    }
    result["hidden_stem_count"] = hidden_counts;
    result["hidden_stems"] = hidden_stems;
    result["visible_ten_gods"] = std::vector<uint8_t>(
        value.visible_ten_gods, value.visible_ten_gods + 4);
    result["hidden_ten_gods"] = hidden_ten_gods;
    result["life_stages"] = std::vector<uint8_t>(
        value.life_stages, value.life_stages + 4);
    result["nayin_ids"] = std::vector<uint8_t>(
        value.nayin_ids, value.nayin_ids + 4);
    return result;
}

void require_size(std::size_t actual, std::size_t expected, const char* field) {
    if (actual != expected) {
        throw py::value_error(std::string(field) + " has an invalid length");
    }
}

taiyin::bazi::BaziChart chart_from_dict(const py::dict& source) {
    taiyin::bazi::BaziChart value;
    const std::vector<uint8_t> pillars =
        source["pillars"].cast<std::vector<uint8_t> >();
    const std::vector<uint8_t> extra =
        source["extra"].cast<std::vector<uint8_t> >();
    const std::vector<uint8_t> hidden_counts =
        source["hidden_stem_count"].cast<std::vector<uint8_t> >();
    const std::vector<std::vector<uint8_t> > hidden_stems =
        source["hidden_stems"].cast<std::vector<std::vector<uint8_t> > >();
    const std::vector<uint8_t> visible_ten_gods =
        source["visible_ten_gods"].cast<std::vector<uint8_t> >();
    const std::vector<std::vector<uint8_t> > hidden_ten_gods =
        source["hidden_ten_gods"].cast<std::vector<std::vector<uint8_t> > >();
    const std::vector<uint8_t> life_stages =
        source["life_stages"].cast<std::vector<uint8_t> >();
    const std::vector<uint8_t> nayin_ids =
        source["nayin_ids"].cast<std::vector<uint8_t> >();

    require_size(pillars.size(), 4, "pillars");
    require_size(extra.size(), 4, "extra");
    require_size(hidden_counts.size(), 4, "hidden_stem_count");
    require_size(hidden_stems.size(), 4, "hidden_stems");
    require_size(visible_ten_gods.size(), 4, "visible_ten_gods");
    require_size(hidden_ten_gods.size(), 4, "hidden_ten_gods");
    require_size(life_stages.size(), 4, "life_stages");
    require_size(nayin_ids.size(), 4, "nayin_ids");

    value.pillars.year = pillars[0];
    value.pillars.month = pillars[1];
    value.pillars.day = pillars[2];
    value.pillars.hour = pillars[3];
    value.extra.ming_gong = extra[0];
    value.extra.shen_gong = extra[1];
    value.extra.tai_yuan = extra[2];
    value.extra.tai_xi = extra[3];
    for (std::size_t pillar = 0; pillar < 4; ++pillar) {
        require_size(hidden_stems[pillar].size(),
            taiyin::bazi::kHiddenStemCapacity, "hidden_stems row");
        require_size(hidden_ten_gods[pillar].size(),
            taiyin::bazi::kHiddenStemCapacity, "hidden_ten_gods row");
        value.hidden_stem_count[pillar] = hidden_counts[pillar];
        value.visible_ten_gods[pillar] = visible_ten_gods[pillar];
        value.life_stages[pillar] = life_stages[pillar];
        value.nayin_ids[pillar] = nayin_ids[pillar];
        for (std::size_t slot = 0;
             slot < taiyin::bazi::kHiddenStemCapacity; ++slot) {
            value.hidden_stems[pillar][slot] = hidden_stems[pillar][slot];
            value.hidden_ten_gods[pillar][slot] =
                hidden_ten_gods[pillar][slot];
        }
    }
    return value;
}

py::dict qiyun_to_dict(const taiyin::bazi::BaziQiYunResult& value) {
    py::dict result;
    result["direction"] = value.direction;
    result["time_model"] = value.time_model;
    result["reference_jie_index"] = value.reference_jie_index;
    result["jie_interval_days"] = value.jie_interval_days;
    result["start_age_years"] = value.start_age_years;
    result["offset_years"] = value.offset_years;
    result["offset_months"] = value.offset_months;
    result["offset_days"] = value.offset_days;
    result["offset_hours"] = value.offset_hours;
    result["offset_minutes"] = value.offset_minutes;
    result["offset_seconds"] = value.offset_seconds;
    result["reference_jie_jd_ut"] = value.reference_jie_jd_ut;
    result["start_jd_ut"] = value.start_jd_ut;
    result["start_civil_time"] = value.start_civil_time;
    return result;
}

taiyin::bazi::BaziQiYunResult qiyun_from_dict(const py::dict& source) {
    taiyin::bazi::BaziQiYunResult value;
    value.direction = source["direction"].cast<int32_t>();
    value.time_model = source["time_model"].cast<int32_t>();
    value.reference_jie_index = source["reference_jie_index"].cast<uint8_t>();
    value.jie_interval_days = source["jie_interval_days"].cast<double>();
    value.start_age_years = source["start_age_years"].cast<double>();
    value.offset_years = source["offset_years"].cast<int32_t>();
    value.offset_months = source["offset_months"].cast<int32_t>();
    value.offset_days = source["offset_days"].cast<int32_t>();
    value.offset_hours = source["offset_hours"].cast<int32_t>();
    value.offset_minutes = source["offset_minutes"].cast<int32_t>();
    value.offset_seconds = source["offset_seconds"].cast<double>();
    value.reference_jie_jd_ut =
        source["reference_jie_jd_ut"].cast<taiyin::SplitJulianDate>();
    value.start_jd_ut = source["start_jd_ut"].cast<taiyin::SplitJulianDate>();
    value.start_civil_time =
        source["start_civil_time"].cast<taiyin::CalendarDateTime>();
    return value;
}

class BaziNativeContext {
public:
    BaziNativeContext(
        int earth_mode,
        int direction_mode,
        int qiyun_model,
        int dayun_model,
        const std::vector<std::string>& source_paths,
        const std::string& data_root,
        bool load_packaged_data,
        bool strict_discovery
    ) {
        initialize_runtime(source_paths, data_root, load_packaged_data,
            strict_discovery);

        taiyin::bazi::BaziContextConfig config =
            taiyin::bazi::default_context_config();
        config.earth_palace_mode = earth_mode;
        config.qiyun_direction_mode = direction_mode;
        config.qiyun_time_model = qiyun_model;
        config.dayun_boundary_model = dayun_model;
        require_ok(taiyin::bazi::initialize_context(&context_, &config),
            "BaziContext initialization");

        const taiyin::runtime::NativeCalcContext astronomy =
            taiyin::runtime::get_default_native_calc_context();
        const taiyin::chinese_calendar::ChineseCalendarConfig calendar_config =
            taiyin::chinese_calendar::fixed_utc_offset_config(480);
        require_ok(taiyin::chinese_calendar::initialize_context(
            &calendar_, &astronomy, &calendar_config),
            "Bazi ChineseCalendarContext initialization");
    }

    std::vector<uint8_t> kong_wang(uint8_t ganzhi) const {
        uint8_t values[2];
        require_ok(taiyin::bazi::get_kong_wang(ganzhi, values),
            "Bazi.get_kong_wang");
        return std::vector<uint8_t>(values, values + 2);
    }

    uint8_t ten_god(uint8_t day, uint8_t target) const {
        uint8_t out;
        require_ok(taiyin::bazi::get_ten_god(day, target, &out),
            "Bazi.get_ten_god");
        return out;
    }

    std::vector<uint8_t> hidden_stems(uint8_t branch) const {
        uint8_t values[taiyin::bazi::kHiddenStemCapacity];
        uint8_t count = 0;
        require_ok(taiyin::bazi::get_hidden_stems(branch, values, &count),
            "Bazi.get_hidden_stems");
        return std::vector<uint8_t>(values, values + count);
    }

    py::dict stem_relation(uint8_t a, uint8_t b) const {
        return relation(a, b, false);
    }

    py::dict branch_relation(uint8_t a, uint8_t b) const {
        return relation(a, b, true);
    }

    py::dict triple_relation(uint8_t a, uint8_t b, uint8_t c) const {
        uint32_t flags = 0;
        uint8_t combined = taiyin::bazi::kInvalidWuXing;
        require_ok(taiyin::bazi::calculate_branch_triple_relation(
            a, b, c, &flags, &combined),
            "Bazi.calc_branch_triple_relation");
        py::dict out;
        out["flags"] = flags;
        out["combined_element_id"] = combined;
        return out;
    }

    uint8_t life_stage(uint8_t stem, uint8_t branch, int mode) const {
        uint8_t out;
        require_ok(taiyin::bazi::get_life_stage(stem, branch, mode, &out),
            "Bazi.get_life_stage");
        return out;
    }

    uint8_t flow_year(int year) const {
        uint8_t out;
        require_ok(taiyin::bazi::calculate_flow_year(year, &out),
            "Bazi.calc_liunian");
        return out;
    }

    uint8_t flow_month(uint8_t year, uint8_t branch) const {
        uint8_t out;
        require_ok(taiyin::bazi::calculate_flow_month(year, branch, &out),
            "Bazi.calc_liuyue");
        return out;
    }

    uint8_t flow_day(const taiyin::CalendarDateTime& date) const {
        uint8_t out;
        require_ok(taiyin::bazi::calculate_flow_day(date, &out),
            "Bazi.calc_liuri");
        return out;
    }

    uint8_t flow_hour(uint8_t day, uint8_t hour) const {
        uint8_t out;
        require_ok(taiyin::bazi::calculate_flow_hour(day, hour, &out),
            "Bazi.calc_liushi");
        return out;
    }

    py::dict chart(const std::vector<uint8_t>& pillars) const {
        require_size(pillars.size(), 4, "pillars");
        taiyin::chinese_calendar::GanzhiFourPillars input;
        input.year = pillars[0];
        input.month = pillars[1];
        input.day = pillars[2];
        input.hour = pillars[3];
        taiyin::bazi::BaziChart output;
        require_ok(taiyin::bazi::calculate_chart(&context_, input, &output),
            "Bazi.calc_chart");
        return chart_to_dict(output);
    }

    uint8_t xiaoyun(const py::dict& source, int direction, int age) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(source);
        uint8_t output = taiyin::bazi::kInvalidGanzhi;
        require_ok(taiyin::bazi::calculate_xiaoyun(
            &chart_value, direction, age, &output), "Bazi.calc_xiaoyun");
        return output;
    }

    py::list xiaoyun_range(
        const py::dict& source,
        int direction,
        int start_age,
        std::size_t requested_count
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(source);
        std::vector<taiyin::bazi::BaziXiaoYun> output(requested_count);
        std::size_t count = 0;
        require_ok(taiyin::bazi::fill_xiaoyun(
            &chart_value, direction, start_age, requested_count,
            output.empty() ? 0 : &output[0], output.size(), &count),
            "Bazi.fill_xiaoyun");
        py::list result;
        for (std::size_t index = 0; index < count; ++index) {
            py::dict item;
            item["age"] = output[index].age;
            item["ganzhi"] = output[index].ganzhi;
            result.append(item);
        }
        return result;
    }

    py::dict qiyun(
        const taiyin::SplitJulianDate& birth_jd_ut,
        const taiyin::CalendarDateTime& birth_civil_time,
        const py::dict& source,
        int gender
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(source);
        taiyin::bazi::BaziQiYunResult output;
        taiyin::runtime::EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::bazi::calculate_qiyun(
            &context_, &calendar_, birth_jd_ut, birth_civil_time,
            &chart_value, gender, &output, &diagnostic), "Bazi.calc_qiyun");
        py::dict result;
        result["value"] = qiyun_to_dict(output);
        result["diagnostic"] = diagnostic_to_dict(diagnostic);
        return result;
    }

    py::list dayun(
        const taiyin::CalendarDateTime& birth_civil_time,
        const py::dict& chart_source,
        const py::dict& qiyun_source,
        std::size_t requested_count
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(chart_source);
        const taiyin::bazi::BaziQiYunResult qiyun_value =
            qiyun_from_dict(qiyun_source);
        std::vector<taiyin::bazi::BaziDaYun> output(requested_count);
        std::size_t count = 0;
        require_ok(taiyin::bazi::fill_dayun(
            &context_, birth_civil_time, &chart_value, &qiyun_value,
            requested_count, output.empty() ? 0 : &output[0], output.size(),
            &count), "Bazi.fill_dayun");
        py::list result;
        for (std::size_t index = 0; index < count; ++index) {
            py::dict item;
            item["index"] = output[index].index;
            item["ganzhi"] = output[index].ganzhi;
            item["start_virtual_age"] = output[index].start_virtual_age;
            item["end_virtual_age"] = output[index].end_virtual_age;
            item["start_jd_ut"] = output[index].start_jd_ut;
            item["end_jd_ut"] = output[index].end_jd_ut;
            item["start_civil_time"] = output[index].start_civil_time;
            item["end_civil_time"] = output[index].end_civil_time;
            result.append(item);
        }
        return result;
    }

    py::dict renyuan_siling(
        const taiyin::SplitJulianDate& instant_jd_ut,
        const py::dict& chart_source,
        int table_model,
        int time_model
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(chart_source);
        taiyin::bazi::BaziRenyuanSilingResult output;
        taiyin::runtime::EphemerisEvalDiagnostic diagnostic;
        require_ok(taiyin::bazi::calculate_renyuan_siling(
            &calendar_, instant_jd_ut, &chart_value, table_model, time_model,
            &output, &diagnostic), "Bazi.calc_renyuan_siling");
        py::dict value;
        value["table_model"] = output.table_model;
        value["time_model"] = output.time_model;
        value["month_branch_id"] = output.month_branch_id;
        value["stem_id"] = output.stem_id;
        value["origin_kind"] = output.origin_kind;
        value["segment_index"] = output.segment_index;
        value["previous_jie_index"] = output.previous_jie_index;
        value["days_since_jie"] = output.days_since_jie;
        value["segment_start_day"] = output.segment_start_day;
        value["segment_end_day"] = output.segment_end_day;
        value["previous_jie_jd_ut"] = output.previous_jie_jd_ut;
        py::dict result;
        result["value"] = value;
        result["diagnostic"] = diagnostic_to_dict(diagnostic);
        return result;
    }

    py::list renyuan_segments(uint8_t branch, int table_model) const {
        std::size_t count = 0;
        require_ok(taiyin::bazi::get_renyuan_siling_segments(
            branch, table_model, 0, 0, &count),
            "Bazi.get_renyuan_siling_segments count");
        std::vector<taiyin::bazi::BaziRenyuanSilingSegment> output(count);
        require_ok(taiyin::bazi::get_renyuan_siling_segments(
            branch, table_model, output.empty() ? 0 : &output[0],
            output.size(), &count), "Bazi.get_renyuan_siling_segments");
        py::list result;
        for (std::size_t index = 0; index < count; ++index) {
            py::dict item;
            item["stem_id"] = output[index].stem_id;
            item["origin_kind"] = output[index].origin_kind;
            item["segment_index"] = output[index].segment_index;
            item["start_day"] = output[index].start_day;
            item["end_day"] = output[index].end_day;
            result.append(item);
        }
        return result;
    }

    py::list relations(
        const py::dict& source,
        uint32_t pillar_mask,
        uint32_t relation_mask
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(source);
        std::size_t count = 0;
        require_ok(taiyin::bazi::collect_chart_relations(
            &chart_value, pillar_mask, relation_mask, 0, 0, &count),
            "Bazi.collect_chart_relations count");
        std::vector<taiyin::bazi::BaziRelation> output(count);
        require_ok(taiyin::bazi::collect_chart_relations(
            &chart_value, pillar_mask, relation_mask,
            output.empty() ? 0 : &output[0], output.size(), &count),
            "Bazi.collect_chart_relations");
        py::list result;
        for (std::size_t index = 0; index < count; ++index) {
            py::dict item;
            item["kind"] = output[index].kind;
            item["pillar_mask"] = output[index].pillar_mask;
            item["combined_element_id"] = output[index].combined_element_id;
            result.append(item);
        }
        return result;
    }

    std::vector<uint64_t> shen_sha(
        const py::dict& source,
        uint8_t target,
        int target_kind,
        const py::object& gender
    ) const {
        const taiyin::bazi::BaziChart chart_value = chart_from_dict(source);
        std::size_t count = 0;
        const bool with_gender = !gender.is_none();
        taiyin::Status status = with_gender
            ? taiyin::bazi::collect_target_shen_sha_with_gender(
                &chart_value, target, target_kind, gender.cast<int>(),
                0, 0, &count)
            : taiyin::bazi::collect_target_shen_sha(
                &chart_value, target, target_kind, 0, 0, &count);
        require_ok(status, "Bazi.collect_target_shen_sha count");
        std::vector<uint64_t> output(count);
        status = with_gender
            ? taiyin::bazi::collect_target_shen_sha_with_gender(
                &chart_value, target, target_kind, gender.cast<int>(),
                output.empty() ? 0 : &output[0], output.size(), &count)
            : taiyin::bazi::collect_target_shen_sha(
                &chart_value, target, target_kind,
                output.empty() ? 0 : &output[0], output.size(), &count);
        require_ok(status, "Bazi.collect_target_shen_sha");
        output.resize(count);
        return output;
    }

private:
    static void initialize_runtime(
        const std::vector<std::string>& source_paths,
        const std::string& data_root,
        bool load_packaged_data,
        bool strict_discovery
    ) {
        static std::mutex mutex;
        static bool initialized = false;
        static std::vector<std::string> active_source_paths;
        static std::string active_data_root;
        static bool active_load_packaged_data = true;
        static bool active_strict_discovery = false;
        std::lock_guard<std::mutex> lock(mutex);
        if (initialized
            && source_paths == active_source_paths
            && data_root == active_data_root
            && load_packaged_data == active_load_packaged_data
            && strict_discovery == active_strict_discovery) {
            return;
        }
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
        config.load_builtin_eop = false;
        config.segment_cache_max_entries = 4096;
        config.strict_discovery = strict_discovery;
        if (!taiyin::runtime::initialize_global_ephemeris_runtime(config)) {
            throw std::runtime_error("BaZi ephemeris runtime initialization failed");
        }
        active_source_paths = source_paths;
        active_data_root = data_root;
        active_load_packaged_data = load_packaged_data;
        active_strict_discovery = strict_discovery;
        initialized = true;
    }

    py::dict relation(uint8_t a, uint8_t b, bool branch) const {
        uint32_t flags = 0;
        uint8_t combined = taiyin::bazi::kInvalidWuXing;
        require_ok(branch
                ? taiyin::bazi::calculate_branch_relation(
                    a, b, &flags, &combined)
                : taiyin::bazi::calculate_stem_relation(
                    a, b, &flags, &combined),
            branch ? "Bazi.calc_branch_relation" : "Bazi.calc_stem_relation");
        py::dict out;
        out["flags"] = flags;
        out["combined_element_id"] = combined;
        return out;
    }

    taiyin::bazi::BaziContext context_;
    taiyin::chinese_calendar::ChineseCalendarContext calendar_;
};

}  // namespace

PYBIND11_MODULE(_bazi_native, module) {
    module.doc() = "Direct pybind11 bindings for the optional Taiyin BaZi extension";
    py::class_<BaziNativeContext>(module, "NativeBaziContext")
        .def(py::init<int, int, int, int, const std::vector<std::string>&,
                      const std::string&, bool, bool>(),
             py::arg("earth_palace_mode") = 0,
             py::arg("qiyun_direction_mode") = 0,
             py::arg("qiyun_time_model") = 0,
             py::arg("dayun_boundary_model") = 0,
             py::arg("source_paths") = std::vector<std::string>(),
             py::arg("data_root") = std::string(),
             py::arg("load_packaged_data") = true,
             py::arg("strict_discovery") = false)
        .def("get_kong_wang", &BaziNativeContext::kong_wang)
        .def("get_ten_god", &BaziNativeContext::ten_god)
        .def("get_hidden_stems", &BaziNativeContext::hidden_stems)
        .def("calc_stem_relation", &BaziNativeContext::stem_relation)
        .def("calc_branch_relation", &BaziNativeContext::branch_relation)
        .def("calc_branch_triple_relation", &BaziNativeContext::triple_relation)
        .def("get_life_stage", &BaziNativeContext::life_stage)
        .def("calc_liunian", &BaziNativeContext::flow_year)
        .def("calc_liuyue", &BaziNativeContext::flow_month)
        .def("calc_liuri", &BaziNativeContext::flow_day)
        .def("calc_liushi", &BaziNativeContext::flow_hour)
        .def("calc_chart", &BaziNativeContext::chart)
        .def("calc_xiaoyun", &BaziNativeContext::xiaoyun)
        .def("fill_xiaoyun", &BaziNativeContext::xiaoyun_range)
        .def("calc_qiyun", &BaziNativeContext::qiyun)
        .def("fill_dayun", &BaziNativeContext::dayun)
        .def("calc_renyuan_siling", &BaziNativeContext::renyuan_siling)
        .def("get_renyuan_siling_segments", &BaziNativeContext::renyuan_segments)
        .def("collect_chart_relations", &BaziNativeContext::relations,
             py::arg("chart"), py::arg("pillar_mask") = 0xff,
             py::arg("relation_mask") = taiyin::bazi::kBaziRelationKindMaskAll)
        .def("collect_target_shen_sha", &BaziNativeContext::shen_sha,
             py::arg("chart"), py::arg("target"), py::arg("target_kind"),
             py::arg("gender") = py::none());
}
