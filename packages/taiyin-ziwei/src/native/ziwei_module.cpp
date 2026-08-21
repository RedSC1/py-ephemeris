#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/status.h"
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

py::dict transform_to_dict(const taiyin::ziwei::TransformSet& value) {
    py::dict result;
    result["lu"] = value.lu;
    result["quan"] = value.quan;
    result["ke"] = value.ke;
    result["ji"] = value.ji;
    return result;
}

int normalized(int64_t value, int modulus) {
    const int64_t remainder = value % modulus;
    return static_cast<int>(remainder < 0 ? remainder + modulus : remainder);
}

bool decode_ganzhi(uint8_t value, taiyin::ziwei::Ganzhi* out) {
    if (out == 0 || value == 0xffu) return false;
    const taiyin::ziwei::Ganzhi result = {
        static_cast<taiyin::ziwei::Stem>((value >> 4) & 0x0fu),
        static_cast<taiyin::ziwei::Branch>(value & 0x0fu),
    };
    if (!taiyin::ziwei::is_valid(result)) return false;
    *out = result;
    return true;
}

taiyin::ziwei::CalendarFacts facts_from_dict(
    const py::dict& source,
    const taiyin::SplitJulianDate& instant_utc,
    const taiyin::CalendarDateTime& virtual_time,
    int gender,
    int leap_month_strategy
) {
    const std::vector<uint8_t> solar =
        source["solar_pillars"].cast<std::vector<uint8_t> >();
    if (solar.size() != 4u) throw py::value_error("solar_pillars must have four values");
    taiyin::ziwei::Pillars solar_pillars;
    if (!decode_ganzhi(solar[0], &solar_pillars.year)
        || !decode_ganzhi(solar[1], &solar_pillars.month)
        || !decode_ganzhi(solar[2], &solar_pillars.day)
        || !decode_ganzhi(solar[3], &solar_pillars.hour)) {
        throw py::value_error("solar_pillars contains invalid Ganzhi values");
    }
    taiyin::ziwei::CalendarFacts result = {};
    result.birth.instant_utc = instant_utc;
    result.birth.virtual_time = virtual_time;
    result.birth.gender = static_cast<taiyin::ziwei::Gender>(gender);
    result.lunar_date.year = source["lunar_year"].cast<int32_t>();
    result.lunar_date.month = source["lunar_month"].cast<uint8_t>();
    result.lunar_date.day = source["lunar_day"].cast<uint8_t>();
    result.lunar_date.is_leap = source["lunar_is_leap"].cast<bool>() ? 1u : 0u;
    result.lunar_date.month_name = source["lunar_month_name"].cast<uint8_t>();
    result.solar_term_pillars = solar_pillars;
    result.solar_day_from_previous_jie =
        source["solar_day_from_previous_jie"].cast<uint16_t>();
    // The public Python facade always supplies ordinary calendar facts and
    // lets this module derive these fields.  The optional explicit form is
    // intentionally retained only for the bundled raw C++ oracle corpus,
    // whose historical records are already resolved calendar facts.
    const py::object none = py::none();
    const py::object explicit_effective_year = source.attr("get")(
        "effective_lunar_year", none);
    const py::object explicit_effective_month = source.attr("get")(
        "effective_lunar_month", none);
    if (explicit_effective_year.is_none() != explicit_effective_month.is_none()) {
        throw py::value_error(
            "effective_lunar_year and effective_lunar_month must be supplied together");
    }
    if (explicit_effective_year.is_none()) {
        require_ok(taiyin::ziwei::resolve_effective_lunar_month(
            result.lunar_date,
            static_cast<taiyin::ziwei::LeapMonthStrategy>(leap_month_strategy),
            &result.effective_lunar_year, &result.effective_lunar_month),
            "Ziwei resolve effective lunar month");
    } else {
        result.effective_lunar_year = explicit_effective_year.cast<int32_t>();
        result.effective_lunar_month = explicit_effective_month.cast<uint8_t>();
        if (result.effective_lunar_month == 0u || result.effective_lunar_month > 12u) {
            throw py::value_error("effective_lunar_month must be from 1 through 12");
        }
    }
    const py::object explicit_lunar = source.attr("get")("lunar_pillars", none);
    if (!explicit_lunar.is_none()) {
        const std::vector<uint8_t> lunar = explicit_lunar.cast<std::vector<uint8_t> >();
        if (lunar.size() != 4u
            || !decode_ganzhi(lunar[0], &result.lunar_pillars.year)
            || !decode_ganzhi(lunar[1], &result.lunar_pillars.month)
            || !decode_ganzhi(lunar[2], &result.lunar_pillars.day)
            || !decode_ganzhi(lunar[3], &result.lunar_pillars.hour)) {
            throw py::value_error("lunar_pillars must contain four valid Ganzhi values");
        }
    } else {
        const int year_stem = normalized(
            static_cast<int64_t>(result.effective_lunar_year) + 6, 10);
        const int year_branch = normalized(
            static_cast<int64_t>(result.effective_lunar_year) + 8, 12);
        const int month_stem = ((year_stem % 5) * 2 + 2
            + result.effective_lunar_month - 1u) % 10;
        const int month_branch = (result.effective_lunar_month + 1u) % 12u;
        result.lunar_pillars.year = taiyin::ziwei::Ganzhi{
            static_cast<taiyin::ziwei::Stem>(year_stem),
            static_cast<taiyin::ziwei::Branch>(year_branch)};
        result.lunar_pillars.month = taiyin::ziwei::Ganzhi{
            static_cast<taiyin::ziwei::Stem>(month_stem),
            static_cast<taiyin::ziwei::Branch>(month_branch)};
        result.lunar_pillars.day = solar_pillars.day;
        result.lunar_pillars.hour = solar_pillars.hour;
    }
    if (!taiyin::ziwei::is_valid(result.lunar_pillars)) {
        throw std::runtime_error("Ziwei produced invalid lunar pillars");
    }
    return result;
}

taiyin::ziwei::Ganzhi year_ganzhi(int32_t year) {
    return taiyin::ziwei::Ganzhi{
        static_cast<taiyin::ziwei::Stem>(normalized(static_cast<int64_t>(year) + 6, 10)),
        static_cast<taiyin::ziwei::Branch>(normalized(static_cast<int64_t>(year) + 8, 12)),
    };
}

bool same_ganzhi(const taiyin::ziwei::Ganzhi& left,
                 const taiyin::ziwei::Ganzhi& right) {
    return left.stem == right.stem && left.branch == right.branch;
}

int32_t effective_solar_year(const taiyin::ziwei::CalendarFacts& facts) {
    const int32_t civil_year = facts.birth.virtual_time.year;
    if (same_ganzhi(year_ganzhi(civil_year), facts.solar_term_pillars.year)) {
        return civil_year;
    }
    if (same_ganzhi(year_ganzhi(civil_year - 1), facts.solar_term_pillars.year)) {
        return civil_year - 1;
    }
    throw std::runtime_error("Ziwei solar year does not match its year pillar");
}

uint8_t solar_month_from_branch(taiyin::ziwei::Branch branch) {
    return static_cast<uint8_t>(normalized(
        static_cast<int>(branch) - static_cast<int>(taiyin::ziwei::Branch::Yin), 12) + 1);
}

bool split_jd_less(
    const taiyin::SplitJulianDate& left,
    const taiyin::SplitJulianDate& right
) {
    return left.day_number < right.day_number
        || (left.day_number == right.day_number
            && left.day_fraction < right.day_fraction);
}

taiyin::ziwei::RatHourSegment rat_hour_segment(
    const taiyin::CalendarDateTime& virtual_time,
    int rat_hour_mode,
    taiyin::ziwei::Branch hour_branch
) {
    if (hour_branch != taiyin::ziwei::Branch::Zi) {
        return taiyin::ziwei::RatHourSegment::None;
    }
    if (rat_hour_mode == 0) return taiyin::ziwei::RatHourSegment::Unified;
    return virtual_time.hour >= 23
        ? taiyin::ziwei::RatHourSegment::Late
        : taiyin::ziwei::RatHourSegment::Early;
}

py::dict resolved_flow_to_dict(const taiyin::ziwei::ResolvedFlow& value) {
    py::dict result;
    result["effective_birth_year"] = value.effective_birth_year;
    result["effective_target_year"] = value.effective_target_year;
    result["target_month"] = value.target_month;
    result["target_month_sequence"] = value.target_month_sequence;
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

class NativeZiweiChart {
public:
    NativeZiweiChart(
        taiyin::ziwei::ZiweiContext context,
        taiyin::ziwei::NatalChart natal
    ) : context_(std::move(context)) {
        chart_.natal = std::move(natal);
    }

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

    py::dict set_flow(
        const py::dict& target_source,
        const taiyin::SplitJulianDate& target_instant_utc,
        const taiyin::CalendarDateTime& target_virtual_time,
        int boundary,
        int rat_hour_mode,
        int childhood_strategy,
        int deepest_level
    ) {
        if (boundary < 0 || boundary > 1 || childhood_strategy < 0
            || childhood_strategy > 1 || deepest_level < 0
            || deepest_level >= static_cast<int>(taiyin::ziwei::kFlowLevelCount)
            || split_jd_less(target_instant_utc,
                chart_.natal.birth_facts.birth.instant_utc)) {
            throw py::value_error("invalid Ziwei flow request");
        }
        const taiyin::ziwei::CalendarFacts target = facts_from_dict(
            target_source, target_instant_utc, target_virtual_time,
            static_cast<int>(chart_.natal.gender), 2);
        taiyin::ziwei::ResolvedFlow result = {};
        if (boundary == static_cast<int>(taiyin::ziwei::PillarBoundary::Lunar)) {
            result.effective_birth_year = chart_.natal.birth_facts.lunar_date.year;
            result.effective_target_year = target.lunar_date.year;
            result.target_month = target.lunar_date.month == 13u
                ? 12u : target.lunar_date.month;
            result.target_day = target.lunar_date.day;
            result.target_month_is_leap = target.lunar_date.is_leap != 0u;
            result.target_month_sequence =
                target_source["lunar_month_sequence"].cast<uint8_t>();
            // A normal month following an early leap month legitimately has
            // sequence 13.  Only a historical fourteenth structural month
            // is collapsed to Ziwei's synthetic leap twelfth month.
            if (result.target_month_sequence > 13u) {
                result.target_month_sequence = 13u;
                result.target_month = 12u;
                result.target_month_is_leap = true;
            }
            const py::object month_branch_value = target_source.attr("get")(
                "lunar_month_building_branch", py::none());
            if (month_branch_value.is_none()) {
                // Retain the raw-oracle entry point for the bundled legacy
                // corpus.  The public Python facade always supplies the
                // calendar-resolved branch below.
                result.target_month_building_branch =
                    taiyin::ziwei::advance_branch(
                        taiyin::ziwei::Branch::Yin,
                        static_cast<int>(result.target_month_sequence) - 1);
            } else {
                const int month_branch = month_branch_value.cast<int>();
                if (month_branch < 0 || month_branch >= taiyin::ziwei::kBranchCount) {
                    throw py::value_error(
                        "lunar_month_building_branch must be from 0 through 11");
                }
                result.target_month_building_branch =
                    static_cast<taiyin::ziwei::Branch>(month_branch);
            }
        } else {
            result.effective_birth_year = effective_solar_year(chart_.natal.birth_facts);
            result.effective_target_year = effective_solar_year(target);
            result.target_month = solar_month_from_branch(target.solar_term_pillars.month.branch);
            result.target_month_sequence = result.target_month;
            result.target_day = static_cast<uint8_t>(target.solar_day_from_previous_jie);
            result.target_month_is_leap = false;
            result.target_month_building_branch =
                target.solar_term_pillars.month.branch;
            if (result.target_day > taiyin::ziwei::kMaxFlowDayIndex) {
                throw std::runtime_error("Ziwei solar flow day exceeds 32 days");
            }
        }
        result.target_hour_index = static_cast<uint8_t>(target.solar_term_pillars.hour.branch);
        result.target_rat_hour_segment = rat_hour_segment(
            target_virtual_time, rat_hour_mode, target.solar_term_pillars.hour.branch);
        const int64_t age = static_cast<int64_t>(result.effective_target_year)
            - result.effective_birth_year + 1;
        if (age < 1 || age > 2147483647) {
            throw py::value_error("flow target is before the Ziwei birth year");
        }
        require_ok(taiyin::ziwei::make_decade_for_year(
            chart_.natal, result.effective_birth_year, result.effective_target_year,
            static_cast<taiyin::ziwei::ChildhoodStrategy>(childhood_strategy),
            &result.decade), "Ziwei decade flow");
        require_ok(taiyin::ziwei::make_small_limit(
            chart_.natal, chart_.natal.birth_facts.solar_term_pillars.year.branch,
            static_cast<int32_t>(age), &result.small_limit), "Ziwei small limit");
        require_ok(taiyin::ziwei::make_flow_year(
            chart_.natal, result.effective_target_year, &result.year), "Ziwei yearly flow");
        const py::object month_branch_value = target_source.attr("get")(
            "lunar_month_building_branch", py::none());
        if (boundary == static_cast<int>(taiyin::ziwei::PillarBoundary::Lunar)
            && month_branch_value.is_none()) {
            require_ok(taiyin::ziwei::make_flow_month(
                chart_.natal, result.effective_target_year, result.target_month,
                result.target_month_sequence, result.target_month_is_leap,
                chart_.natal.birth_facts.effective_lunar_month,
                chart_.natal.birth_facts.solar_term_pillars.hour.branch,
                &result.month), "Ziwei monthly flow");
        } else {
            require_ok(taiyin::ziwei::make_flow_month_from_lunar_month_branch(
                chart_.natal, result.effective_target_year, result.target_month,
                result.target_month_sequence, result.target_month_is_leap,
                result.target_month_building_branch,
                chart_.natal.birth_facts.effective_lunar_month,
                chart_.natal.birth_facts.solar_term_pillars.hour.branch,
                &result.month), "Ziwei monthly flow");
        }
        require_ok(taiyin::ziwei::make_flow_day(
            chart_.natal, result.month, result.target_day,
            target.solar_term_pillars.day.stem, &result.day), "Ziwei daily flow");
        require_ok(taiyin::ziwei::make_flow_hour_from_pillar(
            chart_.natal, result.day, target.solar_term_pillars.hour,
            result.target_rat_hour_segment, &result.hour), "Ziwei hourly flow");
        taiyin::ziwei::Chart candidate;
        candidate.natal = chart_.natal;
        const taiyin::ziwei::LimitCoordinate* limits[] = {
            &result.decade.limit, &result.year.limit, &result.month.limit,
            &result.day.limit, &result.hour.limit,
        };
        for (int level = 0; level <= deepest_level; ++level) {
            require_ok(taiyin::ziwei::push_limit_flow_layer(
                &candidate, *limits[level], context_.compiled_tables()),
                "Ziwei flow layer");
        }
        chart_.flow_stack = std::move(candidate.flow_stack);
        return resolved_flow_to_dict(result);
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

    taiyin::ziwei::ZiweiContext create_context(const py::dict& selection) const {
        return catalog_.create_context(selection_from_dict(selection));
    }

private:
    taiyin::ziwei::ZiweiDataCatalog catalog_;
};

class NativeZiweiContext {
public:
    NativeZiweiContext(const py::capsule& catalog_capsule, const py::dict& selection) {
        void* pointer = PyCapsule_GetPointer(catalog_capsule.ptr(), kCatalogCapsuleName);
        if (!pointer) throw py::error_already_set();
        const NativeZiweiDataCatalog* catalog =
            static_cast<const NativeZiweiDataCatalog*>(pointer);
        context_ = catalog->create_context(selection);
    }

    uint64_t generation() const { return context_.catalog_generation(); }
    std::size_t star_count() const { return context_.star_registry().size(); }

    py::dict star_metadata(uint16_t id) const {
        const taiyin::ziwei::StarMetadata& value = context_.star_registry().at(id);
        py::dict result;
        result["id"] = id;
        result["key"] = value.key;
        result["category"] = static_cast<int>(value.category);
        return result;
    }

    int find_star(const std::string& key) const {
        taiyin::ziwei::StarId id = taiyin::ziwei::kInvalidStarId;
        return context_.star_registry().find(key, &id) ? static_cast<int>(id) : -1;
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
        require_ok(call_native_without_gil([&]() {
            return taiyin::ziwei::compute_anchors(
                calendar_facts, options.anchor_options, &anchors, &body_palace);
        }), "ZiweiContext.compute_anchors");
        require_ok(taiyin::ziwei::make_natal_chart(
            calendar_facts, anchors, body_palace,
            options.anchor_options.rules, context_.compiled_tables(), &natal),
            "ZiweiContext.create_chart");
        return std::unique_ptr<NativeZiweiChart>(
            new NativeZiweiChart(context_, natal));
    }

private:
    taiyin::ziwei::ZiweiContext context_;
};

}  // namespace

PYBIND11_MODULE(_ziwei_native, module) {
    module.doc() = "Direct pybind11 bindings for the optional Taiyin Ziwei extension";
    py::module_::import("taiyin._native");

    py::class_<NativeZiweiDataCatalog>(module, "NativeZiweiDataCatalog")
        .def(py::init<const std::string&>(), py::arg("profile_path"))
        .def("_core_context_capsule", &NativeZiweiDataCatalog::core_context_capsule)
        .def("reload", &NativeZiweiDataCatalog::reload)
        .def_property_readonly("generation", &NativeZiweiDataCatalog::generation);

    py::class_<NativeZiweiContext>(module, "NativeZiweiContext")
        .def(py::init<const py::capsule&, const py::dict&>(),
            py::arg("catalog"), py::arg("selection"))
        .def_property_readonly("generation", &NativeZiweiContext::generation)
        .def_property_readonly("star_count", &NativeZiweiContext::star_count)
        .def("find_star", &NativeZiweiContext::find_star)
        .def("star_metadata", &NativeZiweiContext::star_metadata)
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
        .def("anchors", &NativeZiweiChart::anchors)
        .def("summary", &NativeZiweiChart::summary)
        .def("star_position", &NativeZiweiChart::star_position)
        .def("star_palace", &NativeZiweiChart::star_palace)
        .def("brightness", &NativeZiweiChart::brightness)
        .def("palace_stars", &NativeZiweiChart::palace_stars)
        .def("transform_mask", &NativeZiweiChart::transform_mask)
        .def("has_transform", &NativeZiweiChart::has_transform)
        .def("set_flow", &NativeZiweiChart::set_flow,
            py::arg("facts"), py::arg("instant_utc"), py::arg("virtual_time"),
            py::arg("boundary") = 1, py::arg("rat_hour_mode") = 0,
            py::arg("childhood_strategy") = 0, py::arg("deepest_level") = 4)
        .def("truncate_flow", &NativeZiweiChart::truncate_flow)
        .def_property_readonly("flow_layer_count", &NativeZiweiChart::flow_layer_count)
        .def("flow_star_position", &NativeZiweiChart::flow_star_position)
        .def("flow_layer_summary", &NativeZiweiChart::flow_layer_summary)
        .def("flow_palace_stars", &NativeZiweiChart::flow_palace_stars);
}
