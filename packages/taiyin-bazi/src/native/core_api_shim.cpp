#include "taiyin_python_core_api.h"

#include <limits>

namespace taiyin_python_internal {

const CoreApiV1* g_core_api = 0;

}  // namespace taiyin_python_internal

namespace {

const taiyin_python_internal::CoreApiV1& core_api() noexcept {
    return *taiyin_python_internal::g_core_api;
}

}  // namespace

namespace taiyin {

bool split_julian_date_is_finite(const SplitJulianDate& value) noexcept {
    return core_api().split_julian_date_is_finite(value);
}

bool julian_day_split(
    const CalendarDateTime& value,
    SplitJulianDate* out
) noexcept {
    return core_api().julian_day_split(value, out);
}

bool reverse_julian_day_split(
    const SplitJulianDate& value,
    CalendarDateTime* out
) noexcept {
    return core_api().reverse_julian_day_split(value, out);
}

bool add_days_to_split_jd(
    const SplitJulianDate& value,
    double days,
    SplitJulianDate* out
) noexcept {
    return core_api().add_days_to_split_jd(value, days, out);
}

double days_between_split_jd(
    const SplitJulianDate& first,
    const SplitJulianDate& second
) noexcept {
    return core_api().days_between_split_jd(first, second);
}

SplitJulianDate operator+(
    const SplitJulianDate& value,
    double days
) noexcept {
    SplitJulianDate out;
    if (!add_days_to_split_jd(value, days, &out)) {
        out.day_number = 0;
        out.day_fraction = std::numeric_limits<double>::quiet_NaN();
    }
    return out;
}

double operator-(
    const SplitJulianDate& first,
    const SplitJulianDate& second
) noexcept {
    return days_between_split_jd(second, first);
}

namespace chinese_calendar {

GanzhiFourPillars::GanzhiFourPillars() noexcept
    : year(kInvalidGanzhi),
      month(kInvalidGanzhi),
      day(kInvalidGanzhi),
      hour(kInvalidGanzhi) {}

SolarTermEvent::SolarTermEvent() noexcept
    : index_from_winter_solstice(0),
      reserved{},
      target_longitude_rad(std::numeric_limits<double>::quiet_NaN()),
      jd_ut(0, std::numeric_limits<double>::quiet_NaN()),
      civil_day_number(0) {}

Status make_ganzhi(
    uint8_t stem_id,
    uint8_t branch_id,
    uint8_t* out
) noexcept {
    return core_api().make_ganzhi(stem_id, branch_id, out);
}

Status advance_ganzhi(uint8_t value, int32_t delta, uint8_t* out) noexcept {
    return core_api().advance_ganzhi(value, delta, out);
}

Status get_month_ganzhi(
    uint8_t year_stem_id,
    uint8_t month_index,
    uint8_t* out
) noexcept {
    return core_api().get_month_ganzhi(year_stem_id, month_index, out);
}

Status get_hour_ganzhi(
    uint8_t day_stem_id,
    uint8_t hour_index,
    uint8_t* out
) noexcept {
    return core_api().get_hour_ganzhi(day_stem_id, hour_index, out);
}

Status calculate_day_pillar(
    const CalendarDateTime& civil_date,
    uint8_t* out
) noexcept {
    return core_api().calculate_day_pillar(civil_date, out);
}

Status get_nayin_id(uint8_t ganzhi, uint8_t* out) noexcept {
    return core_api().get_nayin_id(ganzhi, out);
}

Status getPrevJie(
    const ChineseCalendarContext* context,
    SplitJulianDate jd_ut,
    SolarTermEvent* out,
    runtime::EphemerisEvalDiagnostic* diagnostic
) noexcept {
    return core_api().get_prev_jie(context, jd_ut, out, diagnostic);
}

Status getNextJie(
    const ChineseCalendarContext* context,
    SplitJulianDate jd_ut,
    SolarTermEvent* out,
    runtime::EphemerisEvalDiagnostic* diagnostic
) noexcept {
    return core_api().get_next_jie(context, jd_ut, out, diagnostic);
}

}  // namespace chinese_calendar
}  // namespace taiyin
