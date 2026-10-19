# BaZi

BaZi is distributed separately so users who only need astronomy, calendars,
Ganzhi, houses, or eclipses do not install its native extension:

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

`EphemerisContext.bazi()` loads the installed `taiyin_bazi` extension on
demand. The BaZi context inherits that calculation context's data and calendar
policy.

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
print(result.pillars)
print(result_flags)
print(result.chart.hiddenStems, result.chart.visibleTenGods, result.chart.nayinIds)
```

## Qi-Yun and Da-Yun

Qi-Yun adds a direction convention, so it requires a gender value:

```python
dayun = bazi.fill_dayun(local_time, result.chart, result.qiyun, 10)
print(result.qiyun.startCivilTime, dayun)
```

The four pillars and `BaziChart` themselves are gender-neutral. The configured
`BaziContextConfig` selects the Qi-Yun time model, direction model, and Da-Yun
boundary convention. Calendar-dependent BaZi calculations share one
`ChineseCalendarContext` with four-pillar calculations, so the civil-time
offset is configured only once. The default is UTC+08:00; for example,
UTC-05:00 can be selected with:

```python
calendar_config = taiyin.ChineseCalendarConfig.historical_china(-5 * 60)
ctx = eph.create_context(chinese_calendar_config=calendar_config)
bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
```

Four pillars, Qi-Yun, and Renyuan-Siling all use the calendar attached to the
BaZi context. The default is `ctx.chinese_calendar`, but an alternate calendar
policy can be created within the same ephemeris context and attached
explicitly:

```python
calendar = ctx.create_chinese_calendar(
    taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(0)
)
bazi = ctx.bazi(calendar=calendar)
```

The calendar must have been created by that same `ctx`; calendars from another
calculation context are rejected.

`calculate_local()` accepts one local civil time and derives UTC from that
configuration. If the input is already a UTC Julian instant, use the equally
single-source form `bazi.calculate_instant(instant_utc, gender=...)`; it
derives local civil time internally.

For date-oriented code, the convenience factories avoid assembling an
`AstroDateTime` first:

```python
result, flags = bazi.calculate_solar_day(
    taiyin.SolarDate(2003, 3, 13),
    hour=14, minute=15,
    gender=taiyin_bazi.BaziGender.male,
)
result, flags = bazi.calculate_lunar_day(
    lunar_date, hour=14, minute=15,
    gender=taiyin_bazi.BaziGender.male,
)
```

The lunar factory converts through `bazi.chinese_calendar`, so it uses the
same historical/localized calendar policy as the chart.

## Local apparent ("true") solar time

Some BaZi conventions replace the ordinary civil clock with local mean or
apparent solar time. Select that chart clock explicitly; `calculate_local()`
still interprets its input as the original legal/display clock and derives one
physical UTC instant before applying the solar correction.

```python
import math

clock = taiyin_bazi.BaziClock(
    taiyin_bazi.BaziClockMode.apparentSolar,
    math.radians(118.582),
)
result, result_flags = bazi.calculate_local(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15),
    gender=taiyin_bazi.BaziGender.male,
    clock=clock,
)
print(result.clockTime, result.chartTime, result.pillars, result_flags)
```

The context performs UTC-to-UT1 through its configured EOP/fallback policy.
`result.instantUtc` is the physical event, `result.clockTime` is the original
civil clock, and `result.chartTime` is the clock actually used for pillars and
Qi-Yun. `result.localTime` remains a deprecated alias of `chartTime`.

`ChineseCalendarConfig.local_astronomical_meridian()` selects a local
mean-solar calendar day boundary and locally rebuilds the astronomical lunar
calendar. Pass `utc_offset_minutes` separately when the legal clock is not the
mean-solar clock at that longitude, for example `105.8` degrees with UTC+07.
It is not a true-solar-time switch and does not apply the equation of time.

## Rule and analysis APIs

`BaziContext` exposes Ten Gods, hidden stems, life stages, stem/branch
relations, flow year/month/day/hour, Xiao-Yun, Renyuan-Siling, chart relations,
and Shen Sha queries. For example:

```python
year_ten_god = bazi.get_ten_god(
    result.pillars.day.stem_id, result.pillars.year.stem_id
)
relations = bazi.collect_chart_relations(result.chart)
print(year_ten_god, relations)
```

See the runnable [BaZi extension example](../examples/bazi_extension.md) and
the [API reference](../api.md) for the full surface.
## Reverse lookup

`bazi.reverse_lookup_at_ut1(pillars, start_ut1, end_ut1, *, rat_hour_mode, clock)`
returns `(tuple_of_candidates, result_flags)`. It calls the C++ reverse
algorithm; Python does not scan dates itself. All four pillars are required.

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
bazi = ctx.bazi()
birth, _ = bazi.calculate_local(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15),
    gender=taiyin_bazi.BaziGender.male,
)
start, _ = ctx.time.julian_day(taiyin.AstroDateTime(2003, 1, 1))  # UT1
end, _ = ctx.time.julian_day(taiyin.AstroDateTime(2004, 1, 1))    # UT1
matches, flags = bazi.reverse_lookup_at_ut1(birth.pillars, start, end)
for candidate in matches:
    print(candidate.startUt1, candidate.endUt1)
    print(candidate.startVirtualTime, candidate.endVirtualTime)
```

Results are maximal matching half-open `[start,end)` intervals, not exact
reconstructed birth instants. No match returns an empty tuple. Native errors
raise the existing typed exceptions. Use the same rat-hour mode and chart
clock that produced the pillars; solar clocks invert each endpoint using the
core solver. Solar-term boundaries stay on physical time, not virtual time.

The bounds and returned coordinates are UT1. Fixed-offset mode adds the
calendar offset to UT1, not UTC (so it can differ from the civil UTC path by
DUT1). Convert UTC explicitly using `ctx.time.utc_to_ut1` and retain those
conversion flags separately. EOP estimation is never silently enabled.
There is no IANA timezone/DST interpretation. The native search snapshots
its calendar before releasing the GIL; independent contexts can search
concurrently without a global result buffer.

Available from 1.1.0 with matching base/BaZi modules. All three packages pin
Taiyin C++ `v1.1.0` and a verified public archive; isolated builds do not require
a local C++ checkout.
`bazi.reverse_lookup_supported` reports availability. Builds using the older
pinned release still support all previous APIs; calling reverse lookup there
raises `UnsupportedOperationError` instead of failing the build or importing a second
astronomy runtime.
