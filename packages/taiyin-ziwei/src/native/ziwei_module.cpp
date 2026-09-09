#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/status.h"
#include "calendar_api.h"
#include "calendar_adapter_internal.h"
#include <functional>
#include "taiyin/ziwei/ziweicore.h"

#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace {

const char* kCatalogCapsuleName =
    "taiyin_ziwei._native.NativeZiweiDataCatalog.v1";

void require_ok(taiyin::Status status, const char* operation) {
    if (status != taiyin::TAIYIN_STATUS_OK) {
        py::module_::import("taiyin.errors")
            .attr("_raise_for_status")(
                operation,
                static_cast<int>(status),
                taiyin::status_name(status),
                taiyin::status_message(status),
                static_cast<int>(taiyin::status_category(status)));
        throw std::runtime_error("native status raiser returned without throwing");
    }
}

template <typename Call>
taiyin::Status call_native_without_gil(Call&& call) {
    py::gil_scoped_release release;
    return call();
}


using namespace taiyin;
using namespace taiyin::ziwei;
using Calendar = taiyin_python_calendar::Calendar;

// The owning Python calendar is a strong argument reference for the entire
// call. The base module snapshots it before releasing the GIL.
uint32_t with_calendar(const py::object& owner, const char* operation,
    std::function<Status(const Calendar*)> call) {
    py::capsule capsule = owner.attr("_core_context_capsule")();
    const auto* calendar = static_cast<const Calendar*>(
        PyCapsule_GetPointer(capsule.ptr(), "taiyin._native.ChineseCalendarContext.v1"));
    if (!calendar) throw py::error_already_set();
    uint32_t flags = 0;
    const Status status = taiyin_python_calendar::api->invoke(calendar,
        [](const Calendar* c, void* p) -> Status {
            return (*static_cast<std::function<Status(const Calendar*)>*>(p))(c);
        }, &call, &flags);
    require_ok(status, operation);
    return flags;
}

ChartClock read_clock(int mode, double longitude) {
    if (mode < -1 || mode > 2) throw py::value_error("invalid Ziwei clock mode");
    ChartClock clock;
    clock.mode = static_cast<ChartClockMode>(mode);
    clock.longitude_rad = longitude;
    return clock;
}

BirthResolutionOptions birth_options(const std::vector<int>& values) {
    if (values.size() != 6) throw py::value_error("six birth options required");
    for (size_t i = 0; i < values.size(); ++i)
        if (values[i] < 0 || values[i] > (i < 3 ? 2 : 1))
            throw py::value_error("invalid Ziwei birth option");
    auto result = default_birth_resolution_options();
    result.rat_hour_mode = values[0];
    result.leap_month_strategy = static_cast<LeapMonthStrategy>(values[1]);
    result.anchor_options.chart_mode = static_cast<ZiweiChartMode>(values[2]);
    result.anchor_options.rules.wu_hu_dun_year_boundary = static_cast<PillarBoundary>(values[3]);
    result.anchor_options.rules.sihua_year_boundary = static_cast<PillarBoundary>(values[4]);
    result.anchor_options.rules.body_master_year_boundary = static_cast<PillarBoundary>(values[5]);
    return result;
}

py::tuple clock_time(const py::object& calendar, bool inverse,
    const py::object& input, int mode, double longitude) {
    const auto clock = read_clock(mode, longitude);
    if (mode == -1) throw py::value_error("explicit clock required");
    SplitJulianDate jd;
    CalendarDateTime time;
    if (inverse) time = input.cast<CalendarDateTime>();
    else jd = input.cast<SplitJulianDate>();
    const auto flags = with_calendar(calendar, "Ziwei chart time", [&](const Calendar* c) {
        return inverse ? chart_time_to_ut1(c, clock, time, &jd)
            : chart_time_from_ut1(c, clock, jd, &time);
    });
    return py::make_tuple(inverse ? py::cast(jd) : py::cast(time), flags);
}

py::tuple step_clock(const py::object& calendar, const SplitJulianDate& jd,
    const CalendarDateTime& time, int mode, double longitude, bool hourly,
    int rat, int direction) {
    const auto clock = read_clock(mode, longitude);
    SplitJulianDate out;
    CalendarDateTime wall;
    RatHourSegment segment = RatHourSegment::None;
    const auto flags = with_calendar(calendar, "Ziwei clock navigation", [&](const Calendar* c) {
        if (mode == -1) return hourly
            ? step_flow_hour_target(jd, time, rat, direction, &out, &wall, &segment)
            : step_flow_day_target(jd, time, direction, &out, &wall);
        return hourly ? step_flow_hour_at_ut1(c, jd, clock, rat, direction, &out, &wall, &segment)
            : step_flow_day_at_ut1(c, jd, clock, direction, &out, &wall);
    });
    return py::make_tuple(out, wall, static_cast<int>(segment), flags);
}

taiyin::ziwei::ZiweiOptionSelection selection_from_dict(const py::dict& source) {
    taiyin::ziwei::ZiweiOptionSelection result;
    const py::object none = py::none();
    const char* scalar_names[] = {
        "placement_default", "brightness_default", "sihua_default", "masters",
        "longevity",
    };
    std::string* scalar_values[] = {
        &result.placement_default, &result.brightness_default,
        &result.sihua_default, &result.masters, &result.longevity,
    };
    for (std::size_t index = 0; index < 5u; ++index) {
        const py::object value = source.attr("get")(scalar_names[index], none);
        if (!value.is_none()) *scalar_values[index] = value.cast<std::string>();
    }
    const char* map_names[] = {"placement", "brightness", "sihua"};
    std::unordered_map<std::string, std::string>* maps[] = {
        &result.placement, &result.brightness, &result.sihua,
    };
    for (std::size_t index = 0; index < 3u; ++index) {
        const py::object value = source.attr("get")(map_names[index], none);
        if (value.is_none()) continue;
        const py::dict mapping = value.cast<py::dict>();
        for (auto iterator = mapping.begin();
             iterator != mapping.end(); ++iterator) {
            (*maps[index])[iterator->first.cast<std::string>()] =
                iterator->second.cast<std::string>();
        }
    }
    return result;
}

taiyin::ziwei::ZiweiRuleset ruleset_from_list(const py::list& source) {
    taiyin::ziwei::ZiweiRuleset result;
    for (py::handle item : source) {
        const py::dict value = py::reinterpret_borrow<py::dict>(item);
        taiyin::ziwei::ZiweiJsonRuleModuleInput input;
        input.label = value["label"].cast<std::string>();
        input.stars_json = value["stars_json"].cast<std::string>();
        input.brightness_json = value["brightness_json"].cast<std::string>();
        input.sihua_json = value["sihua_json"].cast<std::string>();
        input.flow_json = value["flow_json"].cast<std::string>();
        input.masters_json = value["masters_json"].cast<std::string>();
        result = result.add_module(
            taiyin::ziwei::ZiweiConfigLoader::compile_json(input));
    }
    return result;
}

py::dict transform_to_dict(const taiyin::ziwei::TransformSet& value) {
    py::dict result;
    result["lu"] = value.lu;
    result["quan"] = value.quan;
    result["ke"] = value.ke;
    result["ji"] = value.ji;
    return result;
}

// Raw facts are accepted only by the private oracle entry point. No
// calendar rules or missing pillar inference are implemented in this binding.
CalendarFacts facts_from_dict(const py::dict& source, const SplitJulianDate& jd,
    const CalendarDateTime& time, int gender, int /* leap_strategy */) {
    CalendarFacts result = {};
    result.birth.instant_utc=jd; result.birth.virtual_time=time;
    result.birth.gender=static_cast<Gender>(gender);
    result.lunar_date.year=source["lunar_year"].cast<int32_t>();
    result.lunar_date.historical_year=result.lunar_date.year;
    result.lunar_date.month=source["lunar_month"].cast<uint8_t>();
    result.lunar_date.day=source["lunar_day"].cast<uint8_t>();
    result.lunar_date.is_leap=source["lunar_is_leap"].cast<bool>();
    result.lunar_date.month_name=source["lunar_month_name"].cast<uint8_t>();
    result.effective_lunar_year=source["effective_lunar_year"].cast<int32_t>();
    result.effective_lunar_month=source["effective_lunar_month"].cast<uint8_t>();
    result.solar_day_from_previous_jie=source["solar_day_from_previous_jie"].cast<uint16_t>();
    auto decode=[](const py::handle& value, Pillars* out) {
        const auto packed=py::cast<std::vector<uint8_t>>(value);
        if(packed.size()!=4) throw py::value_error("four pillars required");
        Ganzhi* fields[]={&out->year,&out->month,&out->day,&out->hour};
        for(size_t i=0;i<4;++i) {
            *fields[i]=Ganzhi{static_cast<Stem>(packed[i]>>4),static_cast<Branch>(packed[i]&15)};
            if(!is_valid(*fields[i])) throw py::value_error("invalid pillar");
        }
    };
    decode(source["solar_pillars"],&result.solar_term_pillars);
    decode(source["lunar_pillars"],&result.lunar_pillars);
    return result;
}

py::dict resolved_flow_to_dict(const taiyin::ziwei::ResolvedFlow& value) {
    py::dict result;
    result["effective_birth_year"] = value.effective_birth_year;
    result["effective_target_year"] = value.effective_target_year;
    result["target_month"] = value.target_month;
    result["target_effective_month"] = value.month.effective_month;
    result["target_month_sequence"] = value.target_month_sequence;
    result["target_month_name"] = value.target_month_name;
    result["target_palace_month_index"] = value.month.palace_month_index;
    result["target_month_building_branch"] =
        static_cast<int>(value.target_month_building_branch);
    result["target_day"] = value.target_day;
    result["target_hour_index"] = value.target_hour_index;
    result["target_rat_hour_segment"] = static_cast<int>(value.target_rat_hour_segment);
    result["target_month_is_leap"] = value.target_month_is_leap;
    py::dict decade;
    decade["index"] = value.decade.index;
    decade["start_age"] = value.decade.start_age;
    decade["end_age"] = value.decade.end_age;
    decade["start_year"] = value.decade.start_year;
    decade["end_year"] = value.decade.end_year;
    decade["is_childhood"] = value.decade.is_childhood;
    decade["life_palace"] = static_cast<int>(value.decade.limit.coordinate.branch);
    result["decade"] = decade;
    py::dict small;
    small["virtual_age"] = value.small_limit.virtual_age;
    small["stem"] = static_cast<int>(value.small_limit.coordinate.stem);
    small["branch"] = static_cast<int>(value.small_limit.coordinate.branch);
    result["small_limit"] = small;
    return result;
}

#include "placement_bindings.h"

class NativeZiweiChart {
public:
    NativeZiweiChart(
        taiyin::ziwei::ZiweiContext context,
        taiyin::ziwei::NatalChart natal,
        taiyin::ziwei::LeapMonthStrategy leap_month_strategy,
        taiyin::ziwei::AnchorOptions anchor_options,
        int32_t update_bureau_override = -1
    ) : context_(std::move(context)), leap_month_strategy_(leap_month_strategy),
        anchor_options_(anchor_options), update_bureau_override_(update_bureau_override) {
        chart_.natal = std::move(natal);
    }

    std::unique_ptr<NativeZiweiChart> modify(const py::dict& source) const {
        const auto patch = placement_patch(source);
        taiyin::ziwei::NatalChart out;
        require_ok(taiyin::ziwei::modify_natal_chart(chart_.natal, patch,
            anchor_options_, context_.compiled_tables(), &out), "ZiweiChart.modify");
        return std::unique_ptr<NativeZiweiChart>(new NativeZiweiChart(context_, std::move(out),
            leap_month_strategy_, anchor_options_,
            patch.update_bureau == -1 ? update_bureau_override_ : patch.update_bureau));
    }
    std::unique_ptr<NativeZiweiChart> shift(int32_t steps) const {
        taiyin::ziwei::NatalChart out;
        require_ok(taiyin::ziwei::shift_natal_life_palace(chart_.natal, steps, &out), "ZiweiChart.shift_life_palace");
        return std::unique_ptr<NativeZiweiChart>(new NativeZiweiChart(context_, std::move(out),
            leap_month_strategy_, anchor_options_, update_bureau_override_));
    }
    std::unique_ptr<NativeZiweiChart> reset() const {
        taiyin::ziwei::NatalChart out;
        require_ok(taiyin::ziwei::reset_natal_chart(chart_.natal, &out), "ZiweiChart.reset");
        return std::unique_ptr<NativeZiweiChart>(new NativeZiweiChart(context_, std::move(out), leap_month_strategy_, anchor_options_));
    }
    py::dict placement() const {
        py::dict d;
        d["input"] = input_dict(taiyin::ziwei::natal_placement_input(chart_.natal));
        d["overrides"] = patch_dict(chart_.natal.modification.overrides, update_bureau_override_);
        d["life_palace_shift"] = chart_.natal.modification.life_palace_shift;
        return d;
    }
    py::list omitted_placements() const { return omitted_list(chart_.natal.omitted_placements); }

    std::vector<uint8_t> anchors() const {
        const std::array<uint8_t, taiyin::ziwei::kAnchorCount> values =
            taiyin::ziwei::flatten_anchors(chart_.natal.anchors);
        return std::vector<uint8_t>(values.begin(), values.end());
    }

    py::dict summary() const {
        py::dict result;
        result["gender"] = static_cast<int>(chart_.natal.gender);
        result["bureau"] = static_cast<int>(chart_.natal.anchors.bureau);
        result["body_palace"] = static_cast<int>(chart_.natal.body_palace);
        result["life_master"] = chart_.natal.life_master;
        result["body_master"] = chart_.natal.body_master;
        result["transforms"] = transform_to_dict(chart_.natal.transformations.birth_year);
        std::vector<uint8_t> palace_stems;
        for (std::size_t i = 0; i < chart_.natal.palace_stems.size(); ++i) {
            palace_stems.push_back(static_cast<uint8_t>(chart_.natal.palace_stems[i]));
        }
        result["palace_stems"] = palace_stems;
        return result;
    }

    int star_position(uint16_t star_id) const {
        std::vector<uint8_t> positions;
        require_ok(taiyin::ziwei::dump_natal_star_positions(chart_.natal, &positions),
            "ZiweiChart.star_position");
        if (star_id >= positions.size() || positions[star_id] == 0xffu) return -1;
        return positions[star_id];
    }

    int star_palace(uint16_t star_id) const {
        const int position = star_position(star_id);
        if (position < 0) return -1;
        for (std::size_t index = 0; index < chart_.natal.anchors.palace_positions.size();
             ++index) {
            if (static_cast<int>(chart_.natal.anchors.palace_positions[index]) == position) {
                return static_cast<int>(index);
            }
        }
        return -1;
    }

    int brightness(uint16_t star_id) const {
        const int position = star_position(star_id);
        if (position < 0) return -1;
        taiyin::ziwei::Brightness value = taiyin::ziwei::Brightness::None;
        require_ok(taiyin::ziwei::brightness_at(
            context_.compiled_tables(), star_id,
            static_cast<taiyin::ziwei::Branch>(position), &value),
            "ZiweiChart.brightness");
        return static_cast<int>(value);
    }

    std::vector<uint16_t> palace_stars(uint8_t branch) const {
        if (branch >= taiyin::ziwei::kBranchCount) {
            throw py::value_error("branch must be from 0 through 11");
        }
        std::vector<uint16_t> result;
        const taiyin::ziwei::DynamicBitset& stars = chart_.natal.palaces[branch].stars;
        for (std::size_t id = 0; id < stars.size(); ++id) {
            if (stars.test(id)) result.push_back(static_cast<uint16_t>(id));
        }
        return result;
    }

    int transform_mask(uint16_t star_id) const {
        return taiyin::ziwei::star_transform_mask(chart_.natal, star_id);
    }

    bool has_transform(uint16_t star_id, int mark) const {
        if (mark < 0 || mark >= static_cast<int>(taiyin::ziwei::kStarTransformMarkCount)) {
            throw py::value_error("invalid Ziwei transform mark");
        }
        return taiyin::ziwei::has_star_transform_mark(chart_.natal,
            static_cast<taiyin::ziwei::StarTransformMark>(mark), star_id);
    }


    py::tuple set_flow_calendar(const py::object& calendar,
        const SplitJulianDate& jd, const CalendarDateTime& time,
        int mode, double longitude, int boundary, int rat, int childhood,
        int month_strategy, int deepest) {
        if (boundary < 0 || boundary > 1 || rat < 0 || rat > 2
            || childhood < 0 || childhood > 1 || month_strategy < 0 || month_strategy > 1
            || deepest < 0 || deepest > 4) throw py::value_error("invalid Ziwei flow options");
        const auto clock = read_clock(mode, longitude);
        auto options = default_flow_resolution_options();
        options.boundary = static_cast<PillarBoundary>(boundary);
        options.rat_hour_mode = rat;
        options.childhood_strategy = static_cast<ChildhoodStrategy>(childhood);
        options.flow_month_palace_strategy = static_cast<FlowMonthPalaceStrategy>(month_strategy);
        const NatalChart& original = chart_.natal.original_chart ? *chart_.natal.original_chart : chart_.natal;
        ResolvedBirth birth = {};
        birth.facts = original.birth_facts;
        birth.anchors = original.anchors;
        birth.body_palace = original.body_palace;
        birth.leap_month_strategy = leap_month_strategy_;
        ResolvedFlow flow;
        // Snapshot mutable chart state under the GIL, commit only on success.
        Chart candidate = chart_;
        const auto flags = with_calendar(calendar, "Ziwei set flow", [&](const Calendar* c) {
            return mode == -1 ? set_flow_stack_through_from_calendar(c, birth,
                jd, time, options, static_cast<FlowLevel>(deepest), context_.compiled_tables(),
                &candidate, &flow, NULL)
                : set_flow_stack_through_at_ut1(c, birth, jd, clock, options,
                    static_cast<FlowLevel>(deepest), context_.compiled_tables(), &candidate, &flow);
        });
        chart_.flow_stack = std::move(candidate.flow_stack);
        return py::make_tuple(resolved_flow_to_dict(flow), flags);
    }

    // Low-level finite-limit bindings used by the historical oracle corpus.
    // All coordinates are supplied by the corpus; no calendar policy lives here.
    py::dict oracle_limits(const std::vector<int>& v) {
        if (v.size() != 25) throw py::value_error("invalid limit oracle record");
        ResolvedFlow r = {};
        r.effective_birth_year=v[1]; r.effective_target_year=v[2];
        r.target_month=v[13]; r.target_month_sequence=v[14];
        r.target_month_is_leap=v[15]!=0; r.target_day=v[18]; r.target_hour_index=v[22];
        require_ok(make_decade_for_year(chart_.natal,v[1],v[2],static_cast<ChildhoodStrategy>(0),&r.decade),"oracle decade");
        require_ok(make_small_limit(chart_.natal,chart_.natal.birth_facts.solar_term_pillars.year.branch,
            v[2]-v[1]+1,&r.small_limit),"oracle small limit");
        require_ok(make_flow_year(chart_.natal,v[2],&r.year),"oracle year");
        require_ok(make_flow_month(chart_.natal,v[2],v[13],v[14],v[15]!=0,
            chart_.natal.birth_facts.effective_lunar_month,chart_.natal.birth_facts.solar_term_pillars.hour.branch,&r.month),"oracle month");
        require_ok(make_flow_day(chart_.natal,r.month,v[18],static_cast<Stem>(v[19]),&r.day),"oracle day");
        require_ok(make_flow_hour_from_pillar(chart_.natal,r.day,
            Ganzhi{static_cast<Stem>(v[23]),static_cast<Branch>(v[22])},RatHourSegment::None,&r.hour),"oracle hour");
        chart_.flow_stack.clear();
        const LimitCoordinate* limits[]={&r.decade.limit,&r.year.limit,&r.month.limit,&r.day.limit,&r.hour.limit};
        for (const auto* limit : limits) require_ok(push_limit_flow_layer(&chart_,*limit,context_.compiled_tables()),"oracle layer");
        return resolved_flow_to_dict(r);
    }

    void truncate_flow(int first_removed_level) {
        if (first_removed_level < 0
            || first_removed_level >= static_cast<int>(taiyin::ziwei::kFlowLevelCount)) {
            throw py::value_error("first_removed_level must be a ZiweiFlowLevel");
        }
        require_ok(taiyin::ziwei::truncate_flow_stack(&chart_,
            static_cast<taiyin::ziwei::FlowLevel>(first_removed_level)),
            "ZiweiChart.truncate_flow");
    }

    std::size_t flow_layer_count() const { return chart_.flow_stack.size(); }

    int flow_star_position(int level, uint16_t star_id) const {
        if (level < 0 || static_cast<std::size_t>(level) >= chart_.flow_stack.size()) {
            throw py::index_error("flow layer is not present");
        }
        std::vector<uint8_t> positions;
        require_ok(taiyin::ziwei::dump_flow_star_positions(
            chart_.flow_stack[static_cast<std::size_t>(level)], &positions),
            "ZiweiChart.flow_star_position");
        return star_id >= positions.size() || positions[star_id] == 0xffu
            ? -1 : positions[star_id];
    }

    py::dict flow_layer_summary(int level) const {
        if (level < 0 || static_cast<std::size_t>(level) >= chart_.flow_stack.size()) {
            throw py::index_error("flow layer is not present");
        }
        const taiyin::ziwei::FlowLayer& layer = chart_.flow_stack[level];
        py::dict result;
        result["level"] = static_cast<int>(layer.level);
        result["life_palace"] = static_cast<int>(layer.life_palace);
        result["coordinate_stem"] = static_cast<int>(layer.coordinate.stem);
        result["coordinate_branch"] = static_cast<int>(layer.coordinate.branch);
        result["transforms"] = transform_to_dict(layer.transforms);
        return result;
    }

    std::vector<uint16_t> flow_palace_stars(int level, uint8_t branch) const {
        if (level < 0 || static_cast<std::size_t>(level) >= chart_.flow_stack.size()) {
            throw py::index_error("flow layer is not present");
        }
        if (branch >= taiyin::ziwei::kBranchCount) {
            throw py::value_error("branch must be from 0 through 11");
        }
        const taiyin::ziwei::DynamicBitset& stars = chart_.flow_stack[level].stars[branch];
        std::vector<uint16_t> result;
        for (std::size_t id = 0; id < stars.size(); ++id) {
            if (stars.test(id)) result.push_back(static_cast<uint16_t>(id));
        }
        return result;
    }

private:
    taiyin::ziwei::ZiweiContext context_;
    taiyin::ziwei::LeapMonthStrategy leap_month_strategy_;
    taiyin::ziwei::AnchorOptions anchor_options_;
    // C++ retains only the effective bool; Python also exposes override intent.
    int32_t update_bureau_override_;
    taiyin::ziwei::Chart chart_;
};

class NativeZiweiDataCatalog {
public:
    explicit NativeZiweiDataCatalog(const std::string& profile_path)
        : catalog_(profile_path) {}

    py::capsule core_context_capsule() {
        return py::capsule(this, kCatalogCapsuleName);
    }

    void reload() { catalog_.reload(); }
    uint64_t generation() const { return catalog_.generation(); }

    taiyin::ziwei::ZiweiContext create_context(
        const py::dict& selection,
        const py::list& modules
    ) const {
        return catalog_.create_context(
            selection_from_dict(selection), ruleset_from_list(modules));
    }

private:
    taiyin::ziwei::ZiweiDataCatalog catalog_;
};

class NativeZiweiContext {
public:
    NativeZiweiContext(
        const py::capsule& catalog_capsule,
        const py::dict& selection,
        const py::list& modules
    ) {
        void* pointer = PyCapsule_GetPointer(catalog_capsule.ptr(), kCatalogCapsuleName);
        if (!pointer) throw py::error_already_set();
        const NativeZiweiDataCatalog* catalog =
            static_cast<const NativeZiweiDataCatalog*>(pointer);
        context_ = catalog->create_context(selection, modules);
    }

    uint64_t generation() const { return context_.catalog_generation(); }
    std::size_t star_count() const { return context_.star_registry().size(); }

    py::dict star_metadata(uint16_t id) const {
        const taiyin::ziwei::StarMetadata& value = context_.star_registry().at(id);
        py::dict result;
        result["id"] = id;
        result["key"] = value.key;
        result["category"] = static_cast<int>(value.category);
        result["is_natal"] = value.natal;
        return result;
    }

    int find_star(const std::string& key) const {
        taiyin::ziwei::StarId id = taiyin::ziwei::kInvalidStarId;
        return context_.star_registry().find(key, &id) ? static_cast<int>(id) : -1;
    }

    std::unique_ptr<NativeCastingChart> casting(int method, const py::object& value,
        int gender, int mode, int fixed_bureau) const {
        if (gender < 0 || gender > 1 || mode < 0 || mode > 2 || fixed_bureau < -1 || fixed_bureau > 4
            || (method != 0 && fixed_bureau != -1)) throw py::value_error("invalid casting options");
        CastingChart out;
        auto g = static_cast<Gender>(gender); auto m = static_cast<ZiweiChartMode>(mode);
        auto bureau = static_cast<Bureau>(fixed_bureau);
        taiyin::Status status;
        if (method == 0) status = make_casting_chart(placement_input(value.cast<py::dict>()), g, m, context_.compiled_tables(), &out, fixed_bureau < 0 ? nullptr : &bureau);
        else if (method == 1) status = casting_chart_from_index(value.cast<uint32_t>(), g, m, context_.compiled_tables(), &out);
        else if (method == 2) status = casting_chart_from_number(value.cast<std::string>(), g, m, context_.compiled_tables(), &out);
        else if (method == 3) status = random_casting_chart(g, m, context_.compiled_tables(), &out);
        else throw py::value_error("invalid casting method");
        require_ok(status, "ZiweiContext.casting");
        return std::unique_ptr<NativeCastingChart>(new NativeCastingChart(context_, std::move(out)));
    }


    py::tuple create_chart_calendar(const py::object& calendar,
        const SplitJulianDate& jd, const CalendarDateTime& time, int mode, double longitude,
        int gender, const std::vector<int>& option_values) const {
        const auto options = birth_options(option_values);
        const auto clock = read_clock(mode, longitude);
        if (gender < 0 || gender > 1) throw py::value_error("invalid gender");
        ResolvedBirth birth;
        NatalChart natal;
        const auto flags = with_calendar(calendar, "Ziwei create chart", [&](const Calendar* c) {
            Status s = mode == -1 ? resolve_birth_from_calendar(c,jd,time,static_cast<Gender>(gender),options,&birth,NULL)
                : resolve_birth_at_ut1(c,jd,clock,static_cast<Gender>(gender),options,&birth);
            if (s != TAIYIN_STATUS_OK) return s;
            return make_natal_chart(birth.facts,birth.anchors,birth.body_palace,
                options.anchor_options.rules,context_.compiled_tables(),&natal);
        });
        auto chart = std::unique_ptr<NativeZiweiChart>(new NativeZiweiChart(
            context_, std::move(natal), options.leap_month_strategy, options.anchor_options));
        return py::make_tuple(std::move(chart), flags);
    }

    py::tuple reverse_calendar(const py::object& calendar,
        const SplitJulianDate& start, const SplitJulianDate& end, const CalendarDateTime& time,
        int mode, double longitude, int gender, const std::vector<int>& options,
        const std::vector<int>& query) const {
        if (gender < 0 || gender > 1 || query.size()!=9) throw py::value_error("invalid reverse request");
        const auto clock = read_clock(mode, longitude);
        ReverseLookupRequest request;
        request.start_instant_utc=start; request.end_instant_utc=end;
        request.start_virtual_time=time; request.gender=static_cast<Gender>(gender);
        request.birth_options=birth_options(options);
        int32_t* fields[]={&request.query.lucun_branch,&request.query.hongluan_branch,
            &request.query.zuofu_branch,&request.query.youbi_branch,&request.query.wenchang_branch,
            &request.query.wenqu_branch,&request.query.santai_branch,&request.query.bazuo_branch,&request.query.ziwei_branch};
        for(size_t i=0;i<query.size();++i) *fields[i]=query[i];
        std::vector<ReverseLookupCandidate> result;
        std::vector<uint8_t> month_days;
        const auto flags=with_calendar(calendar,"Ziwei reverse lookup",[&](const Calendar* c) -> Status {
            Status status = mode==-1 ? reverse_lookup_tier1_from_calendar(c,request,context_.compiled_tables(),
                context_.star_registry(),&result,NULL) : reverse_lookup_tier1_at_ut1(c,request,clock,
                context_.compiled_tables(),context_.star_registry(),&result);
            if (status != TAIYIN_STATUS_OK) return status;
            for (const auto& v : result) {
                chinese_calendar::LunarDate lunar;
                status = detail::resolve_logical_lunar_date(c, v.virtual_time,
                    request.birth_options.rat_hour_mode, &lunar, NULL);
                if (status != TAIYIN_STATUS_OK) return status;
                month_days.push_back(lunar.month_days);
            }
            return TAIYIN_STATUS_OK;
        });
        py::list values;
        size_t index = 0;
        for(const auto& v:result) {
            py::dict lunar;
            lunar["year"]=v.lunar_date.year; lunar["month"]=v.lunar_date.month;
            lunar["day"]=v.lunar_date.day; lunar["is_leap"]=v.lunar_date.is_leap!=0;
            lunar["month_name"]=v.lunar_date.month_name;
            lunar["month_days"]=month_days[index++];
            values.append(py::make_tuple(v.instant_utc,v.virtual_time,lunar,
                v.hour_branch,static_cast<int>(v.rat_hour_segment)));
        }
        return py::make_tuple(values,flags);
    }

    std::unique_ptr<NativeZiweiChart> create_chart(
        const py::dict& facts,
        const taiyin::SplitJulianDate& instant_utc,
        const taiyin::CalendarDateTime& virtual_time,
        int gender,
        int rat_hour_mode,
        int leap_month_strategy,
        int chart_mode,
        int wu_hu_dun_boundary,
        int sihua_boundary,
        int body_master_boundary
    ) const {
        taiyin::ziwei::BirthResolutionOptions options = {};
        options.rat_hour_mode = rat_hour_mode;
        options.leap_month_strategy =
            static_cast<taiyin::ziwei::LeapMonthStrategy>(leap_month_strategy);
        options.anchor_options.rules = taiyin::ziwei::default_natal_rule_options();
        options.anchor_options.chart_mode =
            static_cast<taiyin::ziwei::ZiweiChartMode>(chart_mode);
        options.anchor_options.rules.wu_hu_dun_year_boundary =
            static_cast<taiyin::ziwei::PillarBoundary>(wu_hu_dun_boundary);
        options.anchor_options.rules.sihua_year_boundary =
            static_cast<taiyin::ziwei::PillarBoundary>(sihua_boundary);
        options.anchor_options.rules.body_master_year_boundary =
            static_cast<taiyin::ziwei::PillarBoundary>(body_master_boundary);
        taiyin::ziwei::CalendarFacts calendar_facts = facts_from_dict(
            facts, instant_utc, virtual_time, gender, leap_month_strategy);
        taiyin::ziwei::Anchors anchors;
        taiyin::ziwei::Branch body_palace;
        taiyin::ziwei::NatalChart natal;
        const char* failed_operation = "ZiweiContext.compute_anchors";
        const taiyin::Status status = call_native_without_gil([&]() {
            taiyin::Status current = taiyin::ziwei::compute_anchors(
                calendar_facts, options.anchor_options, &anchors, &body_palace);
            if (current != taiyin::TAIYIN_STATUS_OK) return current;
            failed_operation = "ZiweiContext.create_chart";
            return taiyin::ziwei::make_natal_chart(
                calendar_facts, anchors, body_palace,
                options.anchor_options.rules, context_.compiled_tables(), &natal);
        });
        require_ok(status, failed_operation);
        return std::unique_ptr<NativeZiweiChart>(
            new NativeZiweiChart(context_, natal, options.leap_month_strategy, options.anchor_options));
    }

private:
    taiyin::ziwei::ZiweiContext context_;
};

}  // namespace

PYBIND11_MODULE(_ziwei_native, module) {
    module.doc() = "Direct pybind11 bindings for the optional Taiyin Ziwei extension";
    py::module_ base = py::module_::import("taiyin._native");
    py::capsule api = base.attr("_CALENDAR_API");
    auto* table = static_cast<taiyin_python_calendar::Api*>(PyCapsule_GetPointer(api.ptr(),taiyin_python_calendar::kName));
    if (!table) throw py::error_already_set();
    if (table->version!=1 || table->size!=sizeof(taiyin_python_calendar::Api))
        throw py::import_error("incompatible Taiyin calendar bridge; upgrade the base package");
    taiyin_python_calendar::api=table;
    module.def("clock_time",&clock_time);
    module.def("step_clock",&step_clock);

    py::class_<NativeZiweiDataCatalog>(module, "NativeZiweiDataCatalog")
        .def(py::init<const std::string&>(), py::arg("profile_path"))
        .def("_core_context_capsule", &NativeZiweiDataCatalog::core_context_capsule)
        .def("reload", &NativeZiweiDataCatalog::reload)
        .def_property_readonly("generation", &NativeZiweiDataCatalog::generation);

    py::class_<NativeZiweiContext>(module, "NativeZiweiContext")
        .def(py::init<const py::capsule&, const py::dict&, const py::list&>(),
            py::arg("catalog"), py::arg("selection"),
            py::arg("modules") = py::list())
        .def_property_readonly("generation", &NativeZiweiContext::generation)
        .def_property_readonly("star_count", &NativeZiweiContext::star_count)
        .def("find_star", &NativeZiweiContext::find_star)
        .def("star_metadata", &NativeZiweiContext::star_metadata)
        .def("casting", &NativeZiweiContext::casting)
        .def("create_chart_calendar", &NativeZiweiContext::create_chart_calendar)
        .def("reverse_calendar", &NativeZiweiContext::reverse_calendar)
        .def("create_chart", &NativeZiweiContext::create_chart,
            py::arg("facts"), py::arg("instant_utc"),
            py::arg("virtual_time"), py::arg("gender"),
            py::arg("rat_hour_mode") = 0,
            py::arg("leap_month_strategy") = 2,
            py::arg("chart_mode") = 0,
            py::arg("wu_hu_dun_boundary") = 1,
            py::arg("sihua_boundary") = 1,
            py::arg("body_master_boundary") = 1);

    py::class_<NativeZiweiChart>(module, "NativeZiweiChart")
        .def("modify", &NativeZiweiChart::modify)
        .def("shift_life_palace", &NativeZiweiChart::shift)
        .def("reset", &NativeZiweiChart::reset)
        .def("placement", &NativeZiweiChart::placement)
        .def("omitted_placements", &NativeZiweiChart::omitted_placements)
        .def("anchors", &NativeZiweiChart::anchors)
        .def("summary", &NativeZiweiChart::summary)
        .def("star_position", &NativeZiweiChart::star_position)
        .def("star_palace", &NativeZiweiChart::star_palace)
        .def("brightness", &NativeZiweiChart::brightness)
        .def("palace_stars", &NativeZiweiChart::palace_stars)
        .def("transform_mask", &NativeZiweiChart::transform_mask)
        .def("has_transform", &NativeZiweiChart::has_transform)
        .def("set_flow_calendar", &NativeZiweiChart::set_flow_calendar)
        .def("_oracle_limits", &NativeZiweiChart::oracle_limits)
        .def("truncate_flow", &NativeZiweiChart::truncate_flow)
        .def_property_readonly("flow_layer_count", &NativeZiweiChart::flow_layer_count)
        .def("flow_star_position", &NativeZiweiChart::flow_star_position)
        .def("flow_layer_summary", &NativeZiweiChart::flow_layer_summary)
        .def("flow_palace_stars", &NativeZiweiChart::flow_palace_stars);

    py::class_<NativeCastingChart>(module, "NativeCastingChart")
        .def("summary", &NativeCastingChart::summary)
        .def("omitted_placements", &NativeCastingChart::omitted_placements)
        .def("star_position", &NativeCastingChart::star_position)
        .def("star_palace", &NativeCastingChart::star_palace)
        .def("brightness", &NativeCastingChart::brightness)
        .def("palace_stars", &NativeCastingChart::palace_stars)
        .def("transform_mask", &NativeCastingChart::transform_mask)
        .def("modify", &NativeCastingChart::modify)
        .def("shift_life_palace", &NativeCastingChart::shift)
        .def("reset", &NativeCastingChart::reset);
}
