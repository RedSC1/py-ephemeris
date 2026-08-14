# Chinese calendar and Ganzhi

Chinese calendar and Ganzhi are part of the base `taiyin` package. They do not
require `py-ephemeris-bazi`.

The default is the historical China-standard calendar. Three explicit modes
separate the calendar structure from the caller's local civil clock:

```python
historical = taiyin.ChineseCalendarConfig.historical_china(9 * 60)
china_astronomical = (
    taiyin.ChineseCalendarConfig.china_standard_astronomical(9 * 60)
)
local_astronomical = (
    taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(9 * 60)
)
```

The first two modes build a China-standard date table (historical profile or
astronomical rules at UTC+08) and apply its Gregorian date labels to the
caller's local civil date. They do not convert the local wall-clock fields to
Beijing time. `local_astronomical_utc_offset()` instead assigns new moons and
solar terms to the selected local boundary and rebuilds the month/leap-month
structure. `local_astronomical_meridian()` does the same with a local mean-solar
meridian. Latitude never changes the geocentric new-moon or solar-term instant.

## Solar and lunar dates

```python
import taiyin

ctx = taiyin.Ephemeris().create_context()
lunar = ctx.chinese_calendar.from_solar(taiyin.SolarDate(2003, 3, 13))
print(lunar.year, lunar.month, lunar.day, lunar.isLeap, lunar.monthName)

named = taiyin.LunarDate.from_string(2003, "九月", 1)
solar = ctx.chinese_calendar.from_lunar(named)
print(solar)
```

For one UTC/UT-like Julian instant, use `from_instant_ut()`. It first determines
the configured local civil date, then applies the selected calendar mode.
The runnable [three-mode new-moon example](../examples/chinese_calendar_modes.md)
shows a single instant producing different China-standard and locally rebuilt
lunar dates in India.

`LunarDate.from_string()` accepts common traditional spellings, including
`正月`, `冬月`, `腊月`, `闰五月`, `后九月`, `拾贰`, and `十三`. Parsing only
creates the structured request; the native calendar verifies whether a month
exists and whether the requested day is valid.

Historical exceptional month names and dates are represented by the existing
`monthName` / `isLeap` result fields. Do not infer leap status merely from the
Chinese month string.

## Four pillars and Ganzhi rules

Four pillars require both the astronomical UTC instant and the civil time used
for calendar/hour conventions:

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

print(pillars.year, pillars.month, pillars.day, pillars.hour)
print(ctx.ganzhi.nayin_element(pillars.day))
```

`context.ganzhi` also provides pure cycle operations: create/advance a Ganzhi,
derive month and hour pillars, calculate a civil day pillar, and query NaYin
IDs/elements. These rules are useful independently of BaZi.
