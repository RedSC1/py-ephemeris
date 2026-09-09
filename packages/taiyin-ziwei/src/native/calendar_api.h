#ifndef TAIYIN_PYTHON_CALENDAR_API_H
#define TAIYIN_PYTHON_CALENDAR_API_H
#include "taiyin/chinese_calendar/calendar.h"
#include "taiyin/chinese_calendar/ganzhi.h"
#include "taiyin/runtime/solar_time.h"
#include <cstddef>
#include <cstdint>

// Private bridge: all astronomy remains in taiyin._native. The optional
// extension compiles the original Ziwei adapters, not a second runtime.
namespace taiyin_python_calendar {
using namespace taiyin;
using Calendar = chinese_calendar::ChineseCalendarContext;
using Callback = Status (*)(const Calendar*, void*);
const char* const kName = "taiyin._native._CALENDAR_API.v1";
struct Api {
    uint32_t version;
    std::size_t size;
    Status (*invoke)(const Calendar*, Callback, void*, uint32_t*);
    bool (*finite)(const SplitJulianDate& a);
    bool (*julian)(const CalendarDateTime& a, SplitJulianDate* b);
    bool (*reverse)(const SplitJulianDate& a, CalendarDateTime* b);
    bool (*add_days)(const SplitJulianDate& a, double b, SplitJulianDate* c);
    bool (*add_seconds)(const SplitJulianDate& a, double b, SplitJulianDate* c);
    double (*difference)(const SplitJulianDate& a, const SplitJulianDate& b);
    SplitJulianDate (*plus)(const SplitJulianDate& a, double b);
    SplitJulianDate (*minus_days)(const SplitJulianDate& a, double b);
    double (*minus)(const SplitJulianDate& a, const SplitJulianDate& b);
    bool (*eq)(const SplitJulianDate& a, const SplitJulianDate& b);
    bool (*lt)(const SplitJulianDate& a, const SplitJulianDate& b);
    bool (*le)(const SplitJulianDate& a, const SplitJulianDate& b);
    Status (*normalize)(const CalendarDateTime& a, CalendarDateTime* b);
    Status (*from_solar)(const chinese_calendar::ChineseCalendarContext* a, const chinese_calendar::SolarDate* b, chinese_calendar::LunarDate* c, runtime::EphemerisEvalDiagnostic* d);
    Status (*from_lunar)(const chinese_calendar::ChineseCalendarContext* a, const chinese_calendar::LunarDate* b, chinese_calendar::SolarDate* c, runtime::EphemerisEvalDiagnostic* d);
    Status (*year)(const chinese_calendar::ChineseCalendarContext* a, SplitJulianDate b, chinese_calendar::ChineseCalendarYear* c, runtime::EphemerisEvalDiagnostic* d);
    Status (*previous_jie)(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, chinese_calendar::SolarTermEvent* c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e);
    Status (*next_jie)(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, chinese_calendar::SolarTermEvent* c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e);
    Status (*pillars)(const chinese_calendar::ChineseCalendarContext* a, const SplitJulianDate& b, const CalendarDateTime& c, int32_t d, chinese_calendar::GanzhiFourPillars* e, runtime::EphemerisEvalDiagnostic* f);
    Status (*to_apparent)(const runtime::NativeCalcContext* a, SplitJulianDate b, double c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e);
    Status (*to_mean)(const runtime::NativeCalcContext* a, SplitJulianDate b, double c, SplitJulianDate* d, runtime::EphemerisEvalDiagnostic* e);
    void (*init_SolarDate)(void*);
    void (*init_LunarDate)(void*);
    void (*init_SolarTermEvent)(void*);
    void (*init_GanzhiFourPillars)(void*);
    void (*init_ChineseCalendarYear)(void*);
    void (*init_NewMoonEvent)(void*);
    void (*init_ChineseCalendarMonth)(void*);
};
extern const Api* api;
}
#endif
