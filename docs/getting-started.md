# Getting started

This page is the short, human-oriented introduction to `py-ephemeris`
(`taiyin`). For the complete method index, see [API reference](api.md). For
the bundled files and external data rules, see [bundled data](bundled-data.md).
For data-route accuracy scope and the current benchmark protocol, see
[accuracy and performance](accuracy-and-performance.md).
For one guide per major feature, see the [feature-guide index](guides/index.md).
The separate BaZi script is
[`examples/bazi_extension.py`](../examples/bazi_extension.py); its inputs and
outputs are explained in the [matching example note](examples/bazi_extension.md).

## Install and calculate a planet

```bash
python -m pip install py-ephemeris
```

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
jd = taiyin.JulianDate.from_double(2460310.5)

result, result_flags = ctx.position.state_at_ut1(taiyin.Body.mars, jd)
print(result.position_au)
print(result_flags)
print(ctx.last_status)  # 0 means success
```

The wheel includes a DE442-derived OPM2 product and an OPC catalog, so this
example does not need an ephemeris path. The same `ctx.position` service also
has TT, TDB, UTC, batch, and apparent-position forms.

## Observed altitude and azimuth

Configure an Earth observer, then request horizontal output:

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
ctx.configuration.set_standard_atmosphere()

observed, observed_flags = ctx.observed.at_ut1(
    taiyin.Body.moon,
    jd,
    flags=(
        taiyin.ObservedFlag.topocentric,
        taiyin.ObservedFlag.horizontal,
        taiyin.ObservedFlag.refraction,
    ),
)
print(observed.horizontal)
print(observed.refractedHorizontal)
print(observed_flags)
```

Topocentric, horizontal, and atmospheric calculations in this prerelease are
restricted to observers on Earth.

## Fixed stars

The lite fixed-star catalog is loaded automatically by `Ephemeris()` when
packaged data are enabled:

```python
star, star_flags = ctx.stars.at_ut1("antares", jd)
print(star.coordinates)
print(star_flags)
```

The default lite catalog contains 2,057 stars and 12,242 aliases, including
every HIP member of Stellarium's Chinese and western-zodiac line figures. Extra
TSC1/TSF1 catalogs can be added with `eph.star_catalog.add_tsc1(...)` or
`add_tsf1(...)`.

## Astrology extension example

```text
Civil time: 2003-03-13 14:15 (UTC+08:00)
Location:   118.582° E, 37.449° N
```

The longitude and latitude are used for the observer/houses; the civil time is
converted to UTC for the astronomical calculation.

### Four pillars

```python
from datetime import datetime, timedelta, timezone
import taiyin

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = taiyin.JulianDate.from_datetime(
    datetime(
        2003, 3, 13, 14, 15,
        tzinfo=timezone(timedelta(hours=8)),
    )
)

eph = taiyin.Ephemeris()
ctx = eph.create_context()
pillars, pillar_flags = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

print("year/month/day/hour:", pillars)
print(pillar_flags)
```

### BaZi

BaZi requires its separate distribution:

```bash
python -m pip install py-ephemeris-bazi
```

It is still created from the base `Ephemeris` instance, so it uses the same
packaged or user-supplied ephemeris data:

```python
import taiyin_bazi

bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time,
    gender=taiyin_bazi.BaziGender.male,  # demonstration choice only
)
print("pillars:", result.pillars)
print("result flags:", result_flags)
print("hidden stems:", result.chart.hiddenStems)
print("NaYin IDs:", result.chart.nayinIds)
print("relations:", bazi.collect_chart_relations(result.chart))
print("Qi-Yun:", result.qiyun)
```

### Western/sidereal chart calculations

The same instant can be used with the base astrology service. Sidereal
positions, ayanamsha, and house systems are part of `taiyin`; they do not
require `taiyin_bazi`:

```python
import math

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 0.0)
)

sun, sun_flags = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    instant_utc,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
moon, moon_flags = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.moon,
    instant_utc,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
houses, house_flags = ctx.astrology.houses_at_ut1(
    instant_utc,
    system=taiyin.HouseSystem.porphyry,
)

degrees = lambda radians: math.degrees(radians) % 360.0
print("Sun longitude:", degrees(sun.siderealLongitudeRadians))
print("Moon longitude:", degrees(moon.siderealLongitudeRadians))
print("Ascendant:", degrees(houses.ascendantRadians))
print("House cusps:", [degrees(value) for value in houses.cuspLongitudesRadians])
```

This shows the low-level calculation pieces: planets, lunar position, and
house cusps. A chart UI or a higher-level chart object can format those values
into signs, houses, aspects, and display objects.

## Chinese calendar and Ganzhi

Chinese calendar and Ganzhi are part of the base package and do not require
`taiyin_bazi`:

```python
calendar = ctx.chinese_calendar
lunar, lunar_flags = calendar.from_solar(taiyin.SolarDate(2024, 4, 8))
print(lunar, lunar_flags)

named = taiyin.LunarDate.from_string(2003, "九月", 1)
solar, solar_flags = calendar.from_lunar(named)
print(solar, solar_flags)
print(ctx.ganzhi.make(0, 0))
```

## Search events

Search APIs take an interval and return `(result, result_flags)`:

```python
start = taiyin.JulianDate.from_double(2460400.5)
end = taiyin.JulianDate.from_double(2460420.5)

phases, phase_flags = ctx.events.lunar_phase_crossings_at_ut1(
    0.0, start, end, max_step_days=1.0
)
print(phases, phase_flags)
```

The same pattern is used by visibility, eclipse, occultation, orbital, and
heliacal searches. See the [API reference](api.md) for each service's method
names and options.

## Eclipses and visibility

Once an Earth observer is configured, visibility searches and local eclipse
searches use that same location:

```python
start = taiyin.AstroDateTime(2024, 1, 1).to_julian_date().add_seconds(-8 * 3600)
end = start.add_seconds(2 * 86400)

sunrise, sunrise_flags = ctx.visibility.solar_rise_set_at_ut1(
    start, end, event=taiyin.VisibilityEventKind.rise
)
print("Next sunrise:", sunrise.coordinate, sunrise_flags)

eclipse, eclipse_flags = ctx.eclipses.next_local_solar_at_ut1(start)
print("Local eclipse kinds:", eclipse.kinds)
print("Local maximum:", eclipse.maximum, eclipse_flags)
```

The standalone version is
[`examples/eclipse_and_visibility.py`](../examples/eclipse_and_visibility.py).
See its [matching example note](examples/eclipse_and_visibility.md) for the
time conversion and result fields.

For a short interactive calculation, lifecycle cleanup can be left to Python.
For a long-running application, explicitly call `close()` when a context is no
longer needed, or use the supported `with` context-manager form; neither is
needed in the quick-start snippets above.
