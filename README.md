# py-ephemeris ("Taiyin")

Python bindings for [Taiyin Ephemeris](https://github.com/RedSC1/taiyin-ephemeris),
the C++ core library.

This repository is a monorepo. It publishes the base `py-ephemeris`
distribution from the root and the optional `py-ephemeris-bazi` distribution
from [`packages/taiyin-bazi`](packages/taiyin-bazi/). The two install as
separate Python packages while sharing one source-control history.

[中文 README](README.zh-CN.md) · [Chinese guides](docs_cn/index.md) ·
[Accuracy and performance](docs/accuracy-and-performance.md)

- GitHub repository: `py-ephemeris`
- PyPI distribution: `py-ephemeris`
- Python import package: `taiyin`

```bash
python -m pip install py-ephemeris
```

This is a preview release. The direct Python API is usable now, but may still
gain compatible additions before 1.0.

The package is being rebuilt as a direct pybind11 binding over the Taiyin C++
API. Python users will import native extension modules normally; they will not
locate or load Taiyin DLLs manually.

The direct binding covers the current Taiyin runtime surface, including custom
calculation targets, ayanamsha models, and house systems backed by Python
callables.

## Quick start

### Planetary positions

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
instant_ut1 = taiyin.JulianDate.from_double(2460409.25)

mars = ctx.position.at_ut1(
    taiyin.Body.mars,
    instant_ut1,
    flags=(taiyin.PositionFlag.radians,),
)
state = ctx.position.state_at_ut1(taiyin.Body.mars, instant_ut1)

print("Mars longitude/latitude/distance:", mars)
print("Mars Cartesian position (AU):", state.position_au)
```

`Ephemeris()` finds the DE442-derived data bundled with the wheel automatically.
The same position service also provides TT, TDB, UTC, batch, velocity, and
acceleration forms.

### Solar and lunar eclipses

```python
search_start = taiyin.AstroDateTime(2024, 1, 1).to_julian_date()

solar_eclipse = ctx.eclipses.next_solar_at_ut1(search_start)
lunar_eclipse = ctx.eclipses.next_lunar_at_ut1(search_start)

print("Next solar eclipse:", solar_eclipse.kinds, solar_eclipse.maximum)
print("Next lunar eclipse:", lunar_eclipse.kinds, lunar_eclipse.maximum)
```

The eclipse service also supports contact times, local circumstances, global
routes and map products, and observer-specific visibility.

### Chinese calendar and Ganzhi

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)  # UTC+08:00
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

# Gregorian date → Chinese lunar date.
lunar = ctx.chinese_calendar.from_solar(taiyin.SolarDate(2003, 3, 13))
print("Lunar date:", lunar)

# The same civil time and astronomical instant → year/month/day/hour pillars.
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)
print("Four pillars:", pillars)
print("Day NaYin:", ctx.ganzhi.nayin_element(pillars.day))
```

`taiyin` includes the Chinese calendar and Ganzhi APIs directly; this part
does not need another import or extension module.

## Astrology

Sidereal positions, ayanamsha, house systems, precession, and nutation are
built into the base `taiyin` package:

```python
import math

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 0.0)
)
degrees = lambda radians: math.degrees(radians) % 360.0

sun = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    instant_utc,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
houses = ctx.astrology.houses_at_ut1(
    instant_utc, system=taiyin.HouseSystem.porphyry
)
print("Sidereal Sun:", degrees(sun.siderealLongitudeRadians))
print("Ascendant:", degrees(houses.ascendantRadians))
print("House cusps:", [degrees(value) for value in houses.cuspLongitudesRadians])
```

## BaZi extension

Install the separate BaZi distribution before importing `taiyin_bazi`:

```bash
python -m pip install py-ephemeris-bazi
```

```python
import taiyin_bazi

# BaZi is created from the same Ephemeris runtime and inherits its data setup.
bazi = eph.create_bazi()
chart = bazi.calc_chart(pillars)
qiyun = bazi.calc_qiyun(
    instant_utc,
    local_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
year_ten_god = bazi.get_ten_god(
    pillars.day.stem_id,
    pillars.year.stem_id,
)

print("Qi-Yun start:", qiyun.startCivilTime)
print("Qi-Yun start age:", qiyun.startAgeYears)
print("Year-stem Ten God:", year_ten_god)
print("Visible Ten Gods:", chart.visibleTenGods)
```

Gender is needed for the Qi-Yun direction convention, but not for the four
pillars or the BaZi chart itself. Other house systems and BaZi options are
listed in the [API reference](docs/api.md).

## Bundled data

`Ephemeris()` uses the package's own `taiyin/data/index.opc` automatically.
The default data bundle includes a DE442-derived major-body OPM2 product over
approximately 1550–2650, selected precise asteroid OPM2 files, compact
Saturn/Uranus center-of-body corrections, and approximate Kepler fallback
elements. DE441 data are not bundled in the Python wheel; provide them through
an explicit `data_root` or `source_paths` when needed. A separate optional
approximately 30,000-year DE441 data package may be published later; it is not
released yet. Users may also add NASA/JPL's original BSP/SPK files directly,
including DE441, planetary-satellite, and small-body kernels.

The bundled lite fixed-star table is loaded automatically by `Ephemeris()`
when packaged data are enabled. It contains 2,114 bright stars, the 28
traditional Chinese mansion determinative stars, and representative stars for
the western zodiac. It remains available for explicit reload after
`eph.star_catalog.clear()`:

```python
from pathlib import Path
import taiyin

eph = taiyin.Ephemeris()
eph.star_catalog.clear()  # optional: reset the process-wide catalog
lite_stars = Path(taiyin.__file__).resolve().parent / "data" / "stars" / "catalogs" / "lite" / "stars-bright-v5.tsc1"
eph.star_catalog.add_tsc1(str(lite_stars))

ctx = eph.create_context()
antares = ctx.stars.at_ut1("antares", taiyin.JulianDate.from_double(2460310.5))
assert ctx.last_status == 0
```

See [bundled data](docs/bundled-data.md), the
[default-data example](docs/examples/default_data.md), and the
[eclipse/visibility example](docs/examples/eclipse_and_visibility.md).
Task-oriented documentation is in the [feature guides](docs/guides/index.md).
The public API is documented in
[`docs/api.md`](docs/api.md).

Start with the [getting started guide](docs/getting-started.md) for runnable
planet, star, calendar, and eclipse examples. The separate BaZi walkthrough
is the [BaZi extension example](docs/examples/bazi_extension.md).

## Development

Source builds prefer a Taiyin C++ checkout next to this repository. If that
checkout is absent—as it normally is when building from an sdist—CMake fetches
the public `v1.0.0-preview.1` source archive and verifies its pinned SHA-256
before compiling it into the extension. Set `TAIYIN_SOURCE_DIR` explicitly to
develop against another local C++ checkout.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[test]" \
  --config-settings=cmake.define.TAIYIN_SOURCE_DIR=../taiyin-ephemeris
TAIYIN_SOURCE_DIR=../taiyin-ephemeris python -m pytest
```

The wheel includes the same default `taiyin/data` directory. `Ephemeris()`
uses its valid `index.opc` automatically and falls back to discovering OPM2,
SPK, TKE1, and TKC1 sources below that directory when the index is missing or
stale:

```python
import taiyin

eph = taiyin.Ephemeris()
context = eph.create_context()
```

Pass `data_root="/path/to/other/data"` to select a separate or extended data
set instead.

Optional or user-provided solar-system shards can additionally be supplied as
files or directories through `source_paths=[...]`. The source-tree test suite
may deliberately select a DE441 fixture to keep fixed numeric oracles
independent of the default package's route priority; those test data are not
part of the Python wheel.

## Chinese lunar month strings

Traditional month names are normalized in Python and then validated by the
configured native calendar during conversion:

```python
import taiyin

context = taiyin.Ephemeris().create_context()
lunar = taiyin.LunarDate.from_string(2003, "九月", 1)
solar = context.chinese_calendar.from_lunar(lunar)

leap_month = taiyin.LunarDate.from_string(2023, "闰二月", 15)
historical = taiyin.LunarDate.from_string(-209, "后九月", 15)
```

The parser accepts `正`/`正月`, `一` through `十二`, `冬`, `腊`, `闰五`,
`后九`, `拾贰`, and `十三`; a trailing `月` is optional. The Python parser
only creates a structured `LunarDate`. Month existence and the actual 29/30-day
limit remain native Chinese-calendar responsibilities. Invalid names, absent
leap months, and days outside the selected month's length raise `ValueError`;
ephemeris coverage and runtime failures remain runtime errors.
