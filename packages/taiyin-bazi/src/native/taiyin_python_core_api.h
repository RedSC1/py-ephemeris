#ifndef TAIYIN_PYTHON_CORE_API_H
#define TAIYIN_PYTHON_CORE_API_H

#include "taiyin/chinese_calendar/calendar.h"
#include "taiyin/chinese_calendar/ganzhi.h"
#include "taiyin/runtime/ephemeris_engine.h"
#include "taiyin/runtime/native_context.h"
#include "taiyin/status.h"
#include "taiyin/time.h"

#include <cstddef>
#include <cstdint>

namespace taiyin_python_internal {

// Private, versioned ABI shared by the two CPython extension modules.  The
// table avoids relying on C++ symbol visibility across .pyd/.so boundaries.
// It is not part of the public taiyin Python API.
const uint32_t kCoreApiVersion = 1u;

inline const char* core_api_capsule_name() noexcept {
    return "taiyin._native._C_API.v1";
}

inline const char* native_context_capsule_name() noexcept {
    return "taiyin._native.NativeCalcContext.v1";
}

inline const char* calendar_context_capsule_name() noexcept {
    return "taiyin._native.ChineseCalendarContext.v1";
}

struct CoreApiV1 {
    uint32_t abi_version;
    std::size_t struct_size;

    taiyin::Status (*make_ganzhi)(uint8_t, uint8_t, uint8_t*);
    taiyin::Status (*advance_ganzhi)(uint8_t, int32_t, uint8_t*);
    taiyin::Status (*get_month_ganzhi)(uint8_t, uint8_t, uint8_t*);
    taiyin::Status (*get_hour_ganzhi)(uint8_t, uint8_t, uint8_t*);
    taiyin::Status (*calculate_day_pillar)(
        const taiyin::CalendarDateTime&, uint8_t*);
    taiyin::Status (*get_nayin_id)(uint8_t, uint8_t*);

    bool (*split_julian_date_is_finite)(const taiyin::SplitJulianDate&);
    bool (*julian_day_split)(
        const taiyin::CalendarDateTime&, taiyin::SplitJulianDate*);
    bool (*reverse_julian_day_split)(
        const taiyin::SplitJulianDate&, taiyin::CalendarDateTime*);
    bool (*add_days_to_split_jd)(
        const taiyin::SplitJulianDate&, double, taiyin::SplitJulianDate*);
    double (*days_between_split_jd)(
        const taiyin::SplitJulianDate&, const taiyin::SplitJulianDate&);

    taiyin::Status (*get_prev_jie)(
        const taiyin::chinese_calendar::ChineseCalendarContext*,
        taiyin::SplitJulianDate,
        taiyin::chinese_calendar::SolarTermEvent*,
        taiyin::runtime::EphemerisEvalDiagnostic*);
    taiyin::Status (*get_next_jie)(
        const taiyin::chinese_calendar::ChineseCalendarContext*,
        taiyin::SplitJulianDate,
        taiyin::chinese_calendar::SolarTermEvent*,
        taiyin::runtime::EphemerisEvalDiagnostic*);

};

extern const CoreApiV1* g_core_api;

inline bool valid_core_api(const CoreApiV1* api) noexcept {
    return api
        && api->abi_version == kCoreApiVersion
        && api->struct_size >= sizeof(CoreApiV1);
}

}  // namespace taiyin_python_internal

#endif
