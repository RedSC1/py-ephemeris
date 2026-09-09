#include "calendar_api.h"
namespace taiyin_python_calendar { const Api* api = NULL; }
namespace taiyin {
chinese_calendar::NewMoonEvent::NewMoonEvent() noexcept { taiyin_python_calendar::api->init_NewMoonEvent(this); }
chinese_calendar::ChineseCalendarMonth::ChineseCalendarMonth() noexcept { taiyin_python_calendar::api->init_ChineseCalendarMonth(this); }
bool split_julian_date_is_finite(const SplitJulianDate& a) noexcept { return taiyin_python_calendar::api->finite(a); }
bool julian_day_split(const CalendarDateTime& a, SplitJulianDate* b) noexcept { return taiyin_python_calendar::api->julian(a,b); }
bool reverse_julian_day_split(const SplitJulianDate& a, CalendarDateTime* b) noexcept { return taiyin_python_calendar::api->reverse(a,b); }
bool add_days_to_split_jd(const SplitJulianDate& a, double b, SplitJulianDate* c) noexcept { return taiyin_python_calendar::api->add_days(a,b,c); }
bool add_seconds_to_split_jd(const SplitJulianDate& a, double b, SplitJulianDate* c) noexcept { return taiyin_python_calendar::api->add_seconds(a,b,c); }
double days_between_split_jd(const SplitJulianDate& a, const SplitJulianDate& b) noexcept { return taiyin_python_calendar::api->difference(a,b); }
SplitJulianDate operator+(const SplitJulianDate& a, double b) noexcept { return taiyin_python_calendar::api->plus(a,b); }
SplitJulianDate operator-(const SplitJulianDate& a, double b) noexcept { return taiyin_python_calendar::api->minus_days(a,b); }
double operator-(const SplitJulianDate& a, const SplitJulianDate& b) noexcept { return taiyin_python_calendar::api->minus(a,b); }
bool operator==(const SplitJulianDate& a, const SplitJulianDate& b) noexcept { return taiyin_python_calendar::api->eq(a,b); }
bool operator<(const SplitJulianDate& a, const SplitJulianDate& b) noexcept { return taiyin_python_calendar::api->lt(a,b); }
bool operator<=(const SplitJulianDate& a, const SplitJulianDate& b) noexcept { return taiyin_python_calendar::api->le(a,b); }
Status chinese_calendar::normalize_chart_virtual_time(const CalendarDateTime& a, CalendarDateTime* b) noexcept { return taiyin_python_calendar::api->normalize(a,b); }
Status chinese_calendar::fromSolar(const chinese_calendar::ChineseCalendarContext* a, const chinese_calendar::SolarDate* b, chinese_calendar::LunarDate* c, runtime::EphemerisEvalDiagnostic* d) noexcept { return taiyin_python_calendar::api->from_solar(a,b,c,d); }
Status chinese_calendar::fromLunar(const chinese_calendar::ChineseCalendarContext* a, const chinese_calendar::LunarDate* b, chinese_calendar::SolarDate* c, runtime::EphemerisEvalDiagnostic* d) noexcept { return taiyin_python_calendar::api->from_lunar(a,b,c,d); }
Status chinese_calendar::calcY(const chinese_calendar::ChineseCalendarContext* a, SplitJulianDate b, chinese_calendar::ChineseCalendarYear* c, runtime::EphemerisEvalDiagnostic* d) noexcept { return taiyin_python_calendar::api->year(a,b,c,d); }
Status chinese_calendar::previous_pillar_jie(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, chinese_calendar::SolarTermEvent* c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e) noexcept { return taiyin_python_calendar::api->previous_jie(a,b,c,d,e); }
Status chinese_calendar::next_pillar_jie(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, chinese_calendar::SolarTermEvent* c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e) noexcept { return taiyin_python_calendar::api->next_jie(a,b,c,d,e); }
Status chinese_calendar::calculate_four_pillars(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, const CalendarDateTime& c, int32_t d, chinese_calendar::GanzhiFourPillars* e, runtime::EphemerisEvalDiagnostic* f) noexcept { return taiyin_python_calendar::api->pillars(a,b,c,d,e,f); }
Status runtime::local_mean_to_apparent_solar_time(const runtime::NativeCalcContext* a, SplitJulianDate b, double c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e) noexcept { return taiyin_python_calendar::api->to_apparent(a,b,c,d,e); }
Status runtime::local_apparent_to_mean_solar_time(const runtime::NativeCalcContext* a, SplitJulianDate b, double c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e) noexcept { return taiyin_python_calendar::api->to_mean(a,b,c,d,e); }
SplitJulianDate& SplitJulianDate::operator+=(double days) noexcept {
    *this = taiyin_python_calendar::api->plus(*this, days); return *this;
}
chinese_calendar::SolarDate::SolarDate() noexcept { taiyin_python_calendar::api->init_SolarDate(this); }
chinese_calendar::LunarDate::LunarDate() noexcept { taiyin_python_calendar::api->init_LunarDate(this); }
chinese_calendar::SolarTermEvent::SolarTermEvent() noexcept { taiyin_python_calendar::api->init_SolarTermEvent(this); }
chinese_calendar::GanzhiFourPillars::GanzhiFourPillars() noexcept { taiyin_python_calendar::api->init_GanzhiFourPillars(this); }
chinese_calendar::ChineseCalendarYear::ChineseCalendarYear() noexcept { taiyin_python_calendar::api->init_ChineseCalendarYear(this); }
}
