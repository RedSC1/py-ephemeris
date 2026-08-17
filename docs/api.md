# Python API reference

This is the public Python-facing shape of `py-ephemeris`. The package name on
PyPI is `py-ephemeris`; the import name is `taiyin`.

The binding is currently a prerelease. The API below describes the direct
pybind11 surface and may receive compatible additions before the stable 1.0
release.

## Creating a runtime

```python
import taiyin

eph = taiyin.Ephemeris()
context = eph.create_context()
```

`Ephemeris` owns process-wide runtime services and creates independent native
calculation contexts. It accepts one primary `data_root` and any number of
additional `source_paths`:

```python
eph = taiyin.Ephemeris(
    data_root="/path/to/data",
    source_paths=["/path/to/satellites", "/path/to/custom.opm2"],
)
```

With no `data_root`, the wheel's `taiyin/data` directory and its `index.opc`
are used. See [bundled data](bundled-data.md) for routing, OPC, and external
SPK/BSP rules.

Useful runtime methods and properties:

| API | Purpose |
| --- | --- |
| `create_context(chinese_calendar_config=...)` | Create a calculation context with one calendar policy. |
| `clone_context(context)` | Clone context configuration and native state. |
| `registered_data_sources` | Inspect successfully registered data sources. |
| `catalog_size` | Number of discovered ephemeris descriptors. |
| `set_ephemeris_source_priority(name, priority)` | Override provider-local source priority. |
| `clear_ephemeris_source_priority(name)` | Remove one priority override. |
| `clear_all_ephemeris_source_priorities()` | Remove all overrides. |
| `add_source_path(path)` | Add a file or directory after initialization. |
| `clear_ephemeris_cache()` | Clear loaded ephemeris segment state. |
| `load_eop_table(path)` / `load_builtin_eop_table()` | Load Earth-orientation data. |
| `load_lunar_limb_model(path)` | Load an optional TLL1 lunar-limb model. |
| `register_custom_target(...)` | Register a Python-backed native target callback. |
| `register_custom_ayanamsha_model(...)` | Register a Python ayanamsha callback. |
| `register_custom_house_system_model(...)` | Register a Python house-system callback. |

Call `close()` on a context when deterministic cleanup is needed. Contexts also
support `with` blocks.

### Threads

Core position, event-search, and Chinese-calendar calculations release
Python's GIL while the C++ core is running. Create one `EphemerisContext` per
worker to evaluate independent charts, event searches, or position batches
concurrently:

```python
from concurrent.futures import ThreadPoolExecutor
import taiyin

eph = taiyin.Ephemeris()
contexts = [eph.create_context() for _ in range(4)]
instant = taiyin.JulianDate.from_double(2460310.5)

with ThreadPoolExecutor(max_workers=4) as pool:
    positions = list(pool.map(
        lambda ctx: ctx.position.at_ut1(taiyin.Body.mars, instant), contexts
    ))
```

An individual `EphemerisContext` is not reentrant: do not calculate, mutate
its configuration, read `last_diagnostic`, or close it concurrently from
multiple threads. Python-backed custom targets, house systems, and ayanamsha
models still execute their callbacks under the GIL.

## Common value types

`JulianDate` stores a split Julian date. Use `JulianDate.from_double(value)`
and `value.to_double()` at API boundaries. `AstroDateTime` represents a civil
calendar date/time.

Every calculation returns its domain value directly. Diagnostic information
includes status, target/center, selected route, coverage, and time-scale
fallback; it is retained in the owning context's native snapshot and is only
materialized when read:

```python
coordinates = context.position.at_ut1(taiyin.Body.mars, jd)
assert context.last_status == 0
diagnostic = context.last_diagnostic  # materialized only when read
```

`last_diagnostic` is replaced by the next calculation on that same context.
It is intentionally `None` after a compact batch position call: a batch has
multiple targets, and the API does not invent one arbitrary diagnostic for the
whole batch.

For higher-level operations such as eclipse searches, event searches,
visibility searches, occultations, and heliacal calculations, the snapshot is
owned by the outer public operation. Internal Sun/Moon or planetary evaluations
performed during a search never replace it.

`Body` contains standard Solar-System IDs, planetary barycenters, major
satellite IDs, Pluto-system IDs, and user-addressable numbered small bodies.
`PositionFlag` controls coordinate/rate output and options such as `xyz`,
`speed`, `truepos`, `nonut`, `topocentric`, and
`allow_barycenter_approx`.

## Context services

Every service below is accessed from an `EphemerisContext`.

### Position and state

```python
jd = taiyin.JulianDate.from_double(2460310.5)
position = context.position.at_ut1(taiyin.Body.mars, jd)
state = context.position.state_at_ut1(taiyin.Body.mars, jd)
batch = context.position.batch_at_ut1(
    [taiyin.Body.sun, taiyin.Body.moon, taiyin.Body.mars], jd
)
```

`context.position` provides `at_tdb`, `at_tt`, `at_ut1`,
`at_ut1_with_delta_t`, `at_utc`, `batch_at_tt`, `batch_at_ut1`,
`state_at_tdb`, `state_at_tt`, and `state_at_ut1`. Position `at_*` methods
return compact coordinate tuples and raise on native failure. Inspect the
context snapshot after a scalar call when route detail is needed.

### Observed positions and configuration

`context.observed` provides `at_ut1`, `at_utc`, `batch_at_ut1`, and
`batch_at_utc`. Combine `ObservedFlag` values for horizontal coordinates,
topocentric output, rates, and refraction:

```python
context.configuration.set_observer_location(
    taiyin.ObserverLocation(116.391, 39.907, 50.0)
)
observed = context.observed.at_ut1(
    taiyin.Body.moon, jd,
    flags=(taiyin.ObservedFlag.topocentric, taiyin.ObservedFlag.horizontal),
)
```

Topocentric and atmospheric observer calculations in this prerelease support
Earth observers only.

`context.configuration` controls observer, route, apparent-model, and
atmosphere behavior. Its main methods are `reset`, `set_geocentric_observer`,
`set_observer_location`, `clear_observer_location`,
`set_simple_topocentric_observer`, `set_precise_topocentric_observer`,
`set_topocentric_observer_offset`, `set_standard_atmosphere`,
`set_atmosphere`, `set_atmosphere_policy`, `set_astro_models`,
`set_celestial_pole_offset`, `set_refraction_model`, `use_solar_deflector`,
`clear_deflectors`, `set_deflectors`, `set_light_time_iteration`,
`enable_shapiro_delay`, `disable_shapiro_delay`, `set_eclipse_models`, and
`set_apparent_config`.

`ApparentConfig()` defaults to light-time, annual aberration, and
gravitational deflection. A new context also contains one built-in solar
deflector, so no setup call is needed for ordinary apparent positions.
`set_deflectors(iterable, solar_deflector_index=...)` replaces that list and
accepts multiple `ApparentDeflector` values; the index identifies the Sun.
Per-call `PositionFlag.no_aberr` and `PositionFlag.no_gdefl` disable the
corresponding corrections. `PositionFlag.speed` remains valid with either the
built-in or a custom deflector list.

### Time and solar time

`context.time` provides `julian_day`, `reverse_julian_day`, `decimal_year`,
`julian_centuries_since_j2000`, `julian_millennia_since_j2000`,
`utc_to_tai`, `tai_to_tt`, `utc_to_tt`, `utc_to_ut1`, `tt_to_ut1`,
`ut1_to_tt`, `tai_minus_utc`, `delta_t`, `precise_scales_from_utc`, and
`estimated_scales_from_ut1`.

UTC position and observed APIs require leap-second and EOP coverage by
default. Applications that explicitly accept an approximation outside those
tables may opt in with
`context.time.set_allow_utc_out_of_range_estimate(True)`. The fallback treats
the supplied civil value as approximate UT1 and applies the configured Delta-T
model. It never changes the meaning of an `*_at_ut1` call.

`context.solar_time` provides `equation_of_time_at_ut1`,
`equation_of_time_at_tt`, `mean_to_apparent`, and `apparent_to_mean`.

### Events and phenomena

`context.events` searches solar/moon longitude, longitude crossings and
stations, aspects, lunar phases, greatest elongations, minimum separations,
and global/local solar transits:

```python
context.events.solar_longitude_at_ut1(0.0, jd)
context.events.longitude_stations_at_ut1(
    taiyin.Body.mercury, start, end, max_step_days=0.25
)
context.events.minimum_angular_separation_at_ut1(
    taiyin.Body.moon, taiyin.Body.sun, start, end, max_step_days=0.05
)
context.events.next_solar_transit_at_ut1(taiyin.Body.mercury, start)
```

`context.phenomena.at_tt` and `at_ut1` return phase angle, illumination,
elongation, apparent diameter, magnitude, and horizontal parallax.

### Visibility and heliacal events

`context.visibility` provides Moon, planet, Sun, and fixed-star rise/set and
transit searches, solar twilight, and fast solar rise/transit routes. Its main
methods include `moon_rise_set_at_ut1`, `moon_transit_at_ut1`,
`planet_rise_set_at_ut1`, `planet_transit_at_ut1`, `solar_rise_set_at_ut1`,
`solar_twilight_at_ut1`, `solar_transit_at_ut1`,
`solar_rise_set_fast_at_tt`, `solar_transit_fast_at_tt`,
`star_rise_set_at_ut1`, and `star_transit_at_ut1`.

`context.heliacal` provides `body_at_ut1`, `star_at_ut1`,
`next_body_event_at_ut1`, and `next_star_event_at_ut1` with configurable
visibility conditions.

### Eclipses, occultations, and orbital calculations

`context.eclipses` includes global/local lunar and solar solve, next-event and
interval searches, local circumstances, Besselian elements/polynomials, solar
lightweight one-epoch geometry, route rows/curves/products/map products, and
local solar boundaries:

```python
lunar = context.eclipses.next_lunar_at_ut1(start)
solar = context.eclipses.solve_solar_at_ut1(estimate)
where = context.eclipses.solar_eclipse_where_at_ut1(solar.maximum)
route = context.eclipses.solar_eclipse_route_product_at_ut1(
    estimate, route_sample_count=256
)
```

`context.occultation` provides geocentric/local star and body occultation
searches, local visibility, and path/visible-region products.

`context.orbits` provides `osculating_at_tt`, `osculating_at_ut1`,
`reference_points_at_tt`, `reference_points_at_ut1`,
`search_apsis_from_tt`, `search_apsis_from_ut1`,
`search_plane_node_from_tt`, and `search_plane_node_from_ut1`.

### Fixed stars

The wheel loads its lite catalog automatically when packaged data are enabled.
The catalog is process-wide:

```python
eph.star_catalog.count
eph.star_catalog.magnitude_of("antares")
eph.star_catalog.add_tsc1("/path/to/extra.tsc1")
eph.star_catalog.add_tsf1("/path/to/custom.tsf1")
eph.star_catalog.clear()

star = context.stars.at_ut1("antares", jd)
observed_star = context.stars.observed_at_ut1("antares", jd)
```

`context.stars` also provides TDB/TT/UT1 single and batch routes, including
`at_tdb`, `at_tt`, `at_ut1`, `at_ut1_with_delta_t`,
`batch_at_tdb`, `batch_at_tt`, `batch_at_ut1`,
`batch_at_ut1_with_delta_t`, and `observed_batch_at_ut1`.

### Sidereal astrology and houses

`context.astrology` provides ayanamsha, sidereal position/coordinates, lunar
nodes and apsides, houses, and house positions:

```python
sidereal = context.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun, jd, ayanamsha=taiyin.Ayanamsha.lahiri
)
houses = context.astrology.houses_at_ut1(
    jd, system=taiyin.HouseSystem.porphyry
)
```

Custom ayanamsha and house-system callbacks are registered on `Ephemeris` and
return registration handles that can be closed after setup.

## Chinese calendar and Ganzhi

The base `taiyin` package contains Chinese calendar and Ganzhi APIs; they do
not require the optional BaZi package.

```python
calendar = context.chinese_calendar
lunar = calendar.from_solar(taiyin.SolarDate(2024, 4, 8))
solar = calendar.from_lunar(taiyin.LunarDate.from_string(2024, "二月", 30))
civil_time = taiyin.AstroDateTime(2024, 4, 8, 18, 17)
instant_utc = civil_time.to_julian_date().add_seconds(-8 * 3600)
pillars = calendar.four_pillars(instant_utc, civil_time)
```

`ChineseCalendarConfig.mode` is one of `chinaStandardHistorical` (the
default), `chinaStandardAstronomical`, or `localAstronomical`. Prefer the
matching `historical_china()`, `china_standard_astronomical()`,
`local_astronomical_utc_offset()`, and `local_astronomical_meridian()` factory
methods instead of assembling a configuration by hand.

Calendar methods include `from_solar`, `from_instant_ut`, `from_lunar`, `get_month_days`,
`calc_year_ut`, `get_specific_jie_qi_ut`, previous/next Jie-Qi queries, and
`four_pillars`. `LunarDate.from_string` accepts traditional names such as
`正月`, `九月`, `冬月`, `腊月`, `闰五月`, `后九月`, `拾贰`, and `十三`.

`context.ganzhi` provides `make`, `advance`, `month_pillar`, `hour_pillar`,
`day_pillar`, `nayin_element`, and `nayin_id`.

## BaZi module

BaZi is provided by the separate `py-ephemeris-bazi` distribution and is
imported as `taiyin_bazi`. `EphemerisContext.bazi()` loads that installed
extension on demand:

```python
 # python -m pip install py-ephemeris-bazi
import taiyin_bazi

bazi = context.bazi()
result = bazi.calculate_local(
    civil_time,
    gender=taiyin_bazi.BaziGender.male,
)
```

`BaziContext` includes Ten-God, hidden-stem, life-stage, stem/branch relation,
flow-pillar, Xiao-Yun, Da-Yun, Qi-Yun, Renyuan-Siling, chart-relation, and
Shen-Sha operations. `bazi()` inherits the base runtime's configured
data paths, and `bazi.chinese_calendar` is the same calendar context used by
Qi-Yun and Renyuan-Siling. Calendar offset and day-boundary rules therefore
have one source of truth. `calculate_local(civil_time, gender=...)` derives
UTC from that configuration; `calculate_instant(instant_utc, gender=...)`
derives the local civil time instead. Neither high-level form accepts two
representations of the same birth event.

## Errors and cleanup

Python input validation raises `ValueError` or `TypeError`. Native failures
are surfaced as `RuntimeError`. Use an `inspect_*` method when an operation
offers one and route/coverage diagnostics are needed for troubleshooting.

Contexts and BaZi contexts support deterministic cleanup:

```python
with taiyin.Ephemeris().create_context() as context:
    result = context.position.at_ut1(taiyin.Body.sun, jd)
```

See [bundled data](bundled-data.md) for package contents and
[`examples/default_data.py`](../examples/default_data.py) for a complete
default-data example.
