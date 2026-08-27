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

## Local apparent ("true") solar time

Some BaZi conventions replace the ordinary civil clock with local apparent
solar time. Keep the physical UTC instant authoritative: derive the solar
clock from that instant and the birthplace longitude, then use the derived
clock as `virtual_time`. Do **not** pass it to `calculate_local()`, because that
method would treat it as civil time and apply the calendar offset again.

```python
import math

longitude_degrees = 118.582

# Solar-time conversion formally uses UT1. For chart boundaries, treating this
# UTC Julian coordinate as UT1 introduces only the sub-second UTC−UT1 offset.
solar_ut1 = instant_utc
local_mean = taiyin.LocalMeanSolarTime.from_ut1(
    solar_ut1,
    longitudeRadians=math.radians(longitude_degrees),
)
local_apparent, solar_flags = ctx.solar_time.mean_to_apparent(local_mean)
true_solar_time, clock_flags = ctx.time.reverse_julian_day(
    local_apparent.coordinate
)

pillars, pillar_flags = ctx.chinese_calendar.four_pillars(
    instant_utc,
    true_solar_time,
)
chart = bazi.calc_chart(pillars)
qiyun, qiyun_flags = bazi.calc_qiyun(
    instant_utc,
    true_solar_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
result = taiyin_bazi.BaziResult(
    instantUtc=instant_utc,
    localTime=true_solar_time,
    pillars=pillars,
    chart=chart,
    qiyun=qiyun,
)

result_flags = solar_flags | clock_flags | pillar_flags | qiyun_flags
dayun = bazi.fill_dayun(true_solar_time, chart, qiyun, 10)
print(true_solar_time, result.pillars, dayun, result_flags)
```

If an exact DUT1 value is available, replace `solar_ut1 = instant_utc` with
`solar_ut1, dut1_flags = ctx.time.utc_to_ut1(instant_utc, dut1_seconds)` and
include `dut1_flags` in the combined flags. The real `instant_utc` passed to
the chart and Qi-Yun APIs does not change.

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
