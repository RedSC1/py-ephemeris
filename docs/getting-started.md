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

result = ctx.position.state_at_ut1(taiyin.Body.mars, jd)
print(result.position_au)
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

observed = ctx.observed.at_ut1(
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
```

Topocentric, horizontal, and atmospheric calculations in this prerelease are
restricted to observers on Earth.

## Fixed stars

The lite fixed-star catalog is loaded automatically by `Ephemeris()` when
packaged data are enabled:

```python
star = ctx.stars.at_ut1("antares", jd)
print(star.coordinates)
```

The default lite catalog includes the 28 Chinese mansion determinative stars,
western-zodiac representative stars, and common bright-star aliases. Extra
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
import taiyin

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

eph = taiyin.Ephemeris()
ctx = eph.create_context()
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

print("year/month/day/hour:", pillars)
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

bazi = eph.create_bazi()
chart = bazi.calc_chart(pillars)
print("hidden stems:", chart.hiddenStems)
print("NaYin IDs:", chart.nayinIds)
print("relations:", bazi.collect_chart_relations(chart))

# Qi-Yun depends on gender; the chart itself is gender-neutral.
qiyun = bazi.calc_qiyun(
    instant_utc,
    local_time,
    chart,
    taiyin_bazi.BaziGender.male,  # demonstration choice only
)
print("Qi-Yun:", qiyun)
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

sun = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    instant_utc,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
moon = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.moon,
    instant_utc,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
houses = ctx.astrology.houses_at_ut1(
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
lunar = calendar.from_solar(taiyin.SolarDate(2024, 4, 8))
print(lunar)

named = taiyin.LunarDate.from_string(2003, "九月", 1)
print(calendar.from_lunar(named))
print(ctx.ganzhi.make(0, 0))
```

## Search events

Search APIs take an interval and return typed result objects:

```python
start = taiyin.JulianDate.from_double(2460400.5)
end = taiyin.JulianDate.from_double(2460420.5)

phases = ctx.events.lunar_phase_crossings_at_ut1(
    0.0, start, end, max_step_days=1.0
)
print(phases)
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

sunrise = ctx.visibility.solar_rise_set_at_ut1(
    start, end, event=taiyin.VisibilityEventKind.rise
)
print("Next sunrise:", sunrise.coordinate)

eclipse = ctx.eclipses.next_local_solar_at_ut1(start)
print("Local eclipse kinds:", eclipse.kinds)
print("Local maximum:", eclipse.maximum)
```

The standalone version is
[`examples/eclipse_and_visibility.py`](../examples/eclipse_and_visibility.py).
See its [matching example note](examples/eclipse_and_visibility.md) for the
time conversion and result fields.

For a short interactive calculation, lifecycle cleanup can be left to Python.
For a long-running application, explicitly call `close()` when a context is no
longer needed, or use the supported `with` context-manager form; neither is
needed in the quick-start snippets above.
