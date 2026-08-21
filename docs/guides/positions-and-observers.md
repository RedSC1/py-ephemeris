# Positions and observers

Start every calculation with a runtime, a context, and a time coordinate. The
default route uses the wheel's bundled data automatically:

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

state, state_flags = ctx.position.state_at_ut1(taiyin.Body.mars, ut1)
assert ctx.last_status == 0
print(state.position_au)
print(state_flags)
```

`context.position.at_ut1(...)` returns `(coordinates, result_flags)`, where
`coordinates` is a compact coordinate tuple: `(longitude, latitude, distance)`,
with three rates appended when `PositionFlag.speed` is set. `state_at_ut1(...)`
returns `(state, result_flags)`, where `state` contains Cartesian position,
velocity, and acceleration in AU-based units.
Use the TT or TDB variants when the input time scale is already known; do not
silently relabel a UTC civil time as UT1.

## Apparent corrections

New contexts use the ordinary apparent-position convention by default:
light-time, annual aberration, and gravitational deflection by the Sun are
enabled. The default deflector list contains the Sun only; Shapiro delay is not
enabled by default.

No setup call is required. To restore the recommended configuration after
customizing or clearing it, enable the three flags and restore the built-in
solar deflector explicitly:

```python
ctx.configuration.set_apparent_config(taiyin.ApparentConfig(
    flags=frozenset((
        taiyin.ApparentFlag.lightTime,
        taiyin.ApparentFlag.aberration,
        taiyin.ApparentFlag.deflection,
    )),
))
ctx.configuration.use_solar_deflector()
```

The `speed` output flag is compatible with these corrections. It requests the
three coordinate rates in addition to the corrected position:

```python
jupiter, jupiter_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.speed,),
)
lon, lat, distance, lon_rate, lat_rate, distance_rate = jupiter
```

Disable one correction for a particular call with `no_aberr` or `no_gdefl`:

```python
without_aberration, aberration_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.no_aberr,),
)
without_deflection, deflection_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.no_gdefl,),
)
```

`PositionFlag.astrometric` keeps light-time but disables aberration,
deflection, and Shapiro delay. `PositionFlag.truepos` selects geometric
positions and disables all of those apparent corrections, including
light-time.

To replace the default Sun-only deflector list, pass any iterable of
`ApparentDeflector` values. `solar_deflector_index` identifies which list item
is the Sun used by annual aberration and solar-specific correction terms:

```python
solar_rs_au = 1.97412574336e-8
ctx.configuration.set_deflectors(
    [
        taiyin.ApparentDeflector(
            body_id=taiyin.Body.sun.id,
            schwarzschild_radius_au=solar_rs_au,
        ),
        taiyin.ApparentDeflector(
            body_id=taiyin.Body.jupiter.id,
            schwarzschild_radius_au=solar_rs_au * 0.0009547919,
        ),
    ],
    solar_deflector_index=0,
)
```

`set_deflectors()` replaces the whole list; it does not append. Use
`use_solar_deflector()` to restore the built-in Sun-only configuration. If
aberration or deflection remains enabled, do not leave the deflector list empty.

## Dense position scans

The regular `at_*` methods are already compact and raise on a native
calculation failure. They return `(coordinates, result_flags)`, where
`coordinates` is `(longitude, latitude, distance)` with three rate values
appended when `PositionFlag.speed` is set:

```python
flags = (
    taiyin.PositionFlag.radians,
    taiyin.PositionFlag.truepos,
    taiyin.PositionFlag.nonut,
    taiyin.PositionFlag.speed,
)
values, result_flags = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
lon, lat, distance, lon_rate, lat_rate, distance_rate = values
```

`batch_at_tt()` and `batch_at_ut1()` apply the same compact return convention
to a sequence of bodies. Pass an already-combined integer flag mask in a hot
Python loop to avoid rebuilding the mask on every call.

For scalar calls, route selection, coverage, and time-scale fallback are
available immediately in `result_flags`. The context's lazy diagnostic snapshot
adds route details when they are needed.

For a one-off check after a compact scalar call, inspect the context snapshot
instead. It lives in native context-owned storage and is converted to a Python
`EphemerisDiagnostic` only when accessed:

```python
mars, result_flags = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
assert ctx.last_status == 0
print(result_flags)
diagnostic = ctx.last_diagnostic
print(diagnostic.component_method_id)
```

The next calculation on `ctx` replaces this snapshot. Compact batch calls set
`last_status` but leave `last_diagnostic` as `None`, because one batch can have
several independent route choices.

A configured context may be shared by threads for concurrent read-only position,
state, and search calculations. Each returned value and `result_flags` belongs to
that call; the context snapshot is only a latest-call debugging view and may be
overwritten by another worker in any order. Finish configuration first, and do
not mutate configuration, calendars or charts, register callbacks, or call
`close()` while calculations are active.

This is a safety guarantee, not a promise of linear speedup. Scalar OPM2 position
evaluation is already very short and currently contends on process-wide cache
metadata under multiple workers. Prefer sequential or batch position calls;
reserve threads for larger independent searches and measure the actual route in
your deployment.

Search APIs use the same context slot for the outer operation. For example,
after `ctx.eclipses.solve_solar_at_ut1(...)`, `ctx.last_operation` names the
solar-eclipse solve and `ctx.last_diagnostic` describes that solve—not one of
the internal Sun or Moon position evaluations used by its iteration.

## Earth observers

Set an observer before requesting horizontal or topocentric output:

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
ctx.configuration.set_standard_atmosphere()

moon, moon_flags = ctx.observed.at_ut1(
    taiyin.Body.moon,
    ut1,
    flags=(
        taiyin.ObservedFlag.topocentric,
        taiyin.ObservedFlag.horizontal,
        taiyin.ObservedFlag.refraction,
    ),
)
print(moon.horizontal)
print(moon.refractedHorizontal)
print(moon_flags)
```

Longitude is east-positive and latitude is north-positive. Horizontal and
atmospheric calculations currently support Earth observers only.

## Physical phenomena

`context.phenomena` supplies phase angle, illumination, elongation, apparent
diameter, magnitude, and parallax for the Sun, Moon, and physical planets:

```python
venus, venus_flags = ctx.phenomena.at_ut1(taiyin.Body.venus, ut1)
print(venus.illuminatedFraction)
print(venus.apparentMagnitude)
print(venus_flags)
```

Phenomena methods return `(result, result_flags)` and raise on failure.
Inspect `ctx.last_status` and `ctx.last_diagnostic` immediately after a call
when using external or partial-coverage data and route provenance matters.
