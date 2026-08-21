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
Python's GIL while the C++ core is running. A configured `EphemerisContext` may be
shared by multiple threads for concurrent read-only calculations:

```python
from concurrent.futures import ThreadPoolExecutor
import taiyin

eph = taiyin.Ephemeris()
context = eph.create_context()
instant = taiyin.JulianDate.from_double(2460310.5)
epochs = [
    taiyin.JulianDate.from_double(2460310.5 + index * 0.125)
    for index in range(4)
]

with ThreadPoolExecutor(max_workers=4) as pool:
    positions = list(pool.map(
        lambda epoch: context.position.at_ut1(taiyin.Body.mars, epoch), epochs
    ))
```

The native calculation state and caches are synchronized for this use. Complete
configuration before starting workers. Configuration changes, observer/apparent
model changes, calendar or chart mutation, custom callback registration or
replacement, and `close()` must not overlap an active calculation on that
context. Python-backed custom targets, house systems, and ayanamsha models still
execute their callbacks under the GIL.

Thread safety does not imply that every workload becomes faster. In particular,
small scalar position calls using the bundled OPM2 data currently contend on
process-wide ephemeris cache metadata and are normally faster when executed
sequentially or through a batch method. Use threads for coarse independent work,
such as substantial searches, and benchmark the selected provider on the target
machine. Separate contexts isolate mutable calculation state, but they still
share the process-wide ephemeris data caches.

`last_status`, `last_operation`, `last_diagnostic`, and `last_result_flags` are
latest-call debugging snapshots. Concurrent operations may overwrite them in any
order, and separate property reads are not a per-call result channel. Use the
returned value and `ResultFlag` for per-call correctness; inspect a snapshot only
after a call when approximate latest-call provenance is sufficient.

## Common value types

`JulianDate` stores a split Julian date. Use `JulianDate.from_double(value)`
and `value.to_double()` at API boundaries. `AstroDateTime` represents a civil
calendar date/time.

Ephemeris, time, calendar, and search operations return `(value, result_flags)`.
The first item is the documented domain value; `result_flags` is a
`taiyin.ResultFlag` that records nonfatal execution facts such as fallback
routes, numerical derivatives, barycenter approximations, time-scale fallback,
and historical calendar rules. Failures raise `taiyin.EphemerisError`; they
never become `(None, flags)`. It remains a `RuntimeError` subclass for broad
backward-compatible catches, while category subclasses such as
`EphemerisRouteError`, `DataFileError`, `TimeScaleError`, `EventSearchError`,
and `RuntimeServiceError` support focused recovery. Pure Ganzhi and
configuration/model-query operations remain single-valued.

Every native-status exception exposes the original failure without relying on
the context's latest-call diagnostic snapshot:

```python
try:
    position, result_flags = context.position.at_utc(taiyin.Body.mars, utc)
except taiyin.TimeScaleError as error:
    print(error.operation)
    print(error.status)       # taiyin.StatusCode.eopOutOfRange
    print(error.status_code)  # -3001
    print(error.status_name)  # TAIYIN_TIME_ERROR_EOP_OUT_OF_RANGE
    print(error.detail)
    print(error.category)     # taiyin.StatusCategory.time
```

`StatusCode` mirrors every status currently published by the native ABI.
Unknown future native values are retained as plain integers and raised as
`UnknownNativeError`, so an older Python wrapper does not discard their codes.

Diagnostic information includes status, target/center, selected route, coverage,
and time-scale fallback; it is retained in the owning context's native snapshot
and is only materialized when read:

```python
coordinates, result_flags = context.position.at_ut1(taiyin.Body.mars, jd)
assert context.last_status == 0
assert result_flags == taiyin.ResultFlag.none
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
position, position_flags = context.position.at_ut1(taiyin.Body.mars, jd)
state, state_flags = context.position.state_at_ut1(taiyin.Body.mars, jd)
batch, batch_flags = context.position.batch_at_ut1(
    [taiyin.Body.sun, taiyin.Body.moon, taiyin.Body.mars], jd
)
```

`context.position` provides `at_tdb`, `at_tt`, `at_ut1`,
`at_ut1_with_delta_t`, `at_utc`, `batch_at_tt`, `batch_at_ut1`,
`state_at_tdb`, `state_at_tt`, and `state_at_ut1`. Position `at_*` methods
return `(coordinates, result_flags)`, while state methods return
`(state, result_flags)`; both raise on native failure. `coordinates` remains
the compact coordinate tuple documented by the position guide.

### Observed positions and configuration

`context.observed` provides `at_ut1`, `at_utc`, `batch_at_ut1`, and
`batch_at_utc`. Combine `ObservedFlag` values for horizontal coordinates,
topocentric output, rates, and refraction:

```python
context.configuration.set_observer_location(
    taiyin.ObserverLocation(116.391, 39.907, 50.0)
)
observed, observed_flags = context.observed.at_ut1(
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
solar_longitude, solar_longitude_flags = context.events.solar_longitude_at_ut1(0.0, jd)
stations, station_flags = context.events.longitude_stations_at_ut1(
    taiyin.Body.mercury, start, end, max_step_days=0.25
)
minimum_separation, separation_flags = context.events.minimum_angular_separation_at_ut1(
    taiyin.Body.moon, taiyin.Body.sun, start, end, max_step_days=0.05
)
transit, transit_flags = context.events.next_solar_transit_at_ut1(
    taiyin.Body.mercury, start
)
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
lunar, lunar_flags = context.eclipses.next_lunar_at_ut1(start)
solar, solar_flags = context.eclipses.solve_solar_at_ut1(estimate)
where, where_flags = context.eclipses.solar_eclipse_where_at_ut1(solar.maximum)
route, route_flags = context.eclipses.solar_eclipse_route_product_at_ut1(
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

star, star_flags = context.stars.at_ut1("antares", jd)
observed_star, observed_star_flags = context.stars.observed_at_ut1("antares", jd)
```

`context.stars` also provides TDB/TT/UT1 single and batch routes, including
`at_tdb`, `at_tt`, `at_ut1`, `at_ut1_with_delta_t`,
`batch_at_tdb`, `batch_at_tt`, `batch_at_ut1`,
`batch_at_ut1_with_delta_t`, and `observed_batch_at_ut1`.

### Sidereal astrology and houses

`context.astrology` provides ayanamsha, sidereal position/coordinates, lunar
nodes and apsides, houses, and house positions:

```python
sidereal, sidereal_flags = context.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun, jd, ayanamsha=taiyin.Ayanamsha.lahiri
)
houses, houses_flags = context.astrology.houses_at_ut1(
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
lunar, lunar_flags = calendar.from_solar(taiyin.SolarDate(2024, 4, 8))
solar, solar_flags = calendar.from_lunar(taiyin.LunarDate.from_string(2024, "二月", 30))
civil_time = taiyin.AstroDateTime(2024, 4, 8, 18, 17)
instant_utc = civil_time.to_julian_date().add_seconds(-8 * 3600)
pillars, pillar_flags = calendar.four_pillars(instant_utc, civil_time)
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
result, result_flags = bazi.calculate_local(
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

For an alternate calendar policy within the same ephemeris context, create a
calendar explicitly and pass it by keyword: `context.bazi(calendar=calendar)`.
The calendar must belong to `context`; a calendar from another calculation
context is rejected.

## Ziwei Doushu module

Ziwei Doushu is provided by `py-ephemeris-ziwei` and imported as
`taiyin_ziwei`. `EphemerisContext.ziwei()` loads the installed extension on
demand and shares exactly the caller's `ChineseCalendarContext`:

```python
# python -m pip install py-ephemeris-ziwei
import taiyin_ziwei

ziwei = context.ziwei()
chart, chart_flags = ziwei.calculate_local(
    civil_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)
```

`ZiweiDataCatalog(profilePath=None)` owns a reloadable TOML catalog;
`ZiweiOptionSelection` independently selects placement, brightness, Si-Hua,
master-table, and twelve-life-stage (`longevity`) options. The bundled
`longevity="option1"` keeps water and earth-five at Shen; `option2` uses the
fire/earth-shared convention and starts earth-five at Yin. `ZiweiContext` provides `calculate_local`,
`calculate_instant`, `create_chart`, star lookup, Tier-1 reverse lookup, and
logical flow day/hour target navigation.

`ZiweiChart` provides `anchors` (`ZiweiAnchors` plus `ZiweiAnchorSlot`),
semantic `palaces`/`palace()`, star/palace and brightness queries, transform
queries, `set_flow`, `truncate_flow`, and per-layer flow star/palace access.
Flow levels are `decade`, `year`, `month`, `day`, and `hour`.

`calculate_local()` and `calculate_instant()` keep a single time source, just
as in BaZi. `reverse_lookup_tier1()` returns finite logical time slots; it is
not a claim of minute-precise birth-time reconstruction. See the task-oriented
[Ziwei guide](guides/ziwei.md).

## Errors and cleanup

Python input validation raises `ValueError` or `TypeError`. Native failures
raise `EphemerisError` or one of its category subclasses. The exception carries
the exact `StatusCode`, integer `status_code`, native `status_name`, operation,
detail, and `StatusCategory`; it is also a `RuntimeError` for broad catches.
Use the context diagnostic snapshot when route/coverage provenance beyond the
failure itself is needed for troubleshooting.

Contexts and optional BaZi/Ziwei contexts support deterministic cleanup:

```python
with taiyin.Ephemeris().create_context() as context:
    result, result_flags = context.position.at_ut1(taiyin.Body.sun, jd)
```

See [bundled data](bundled-data.md) for package contents and
[`examples/default_data.py`](../examples/default_data.py) for a complete
default-data example.
