# Positions and observers

Start every calculation with a runtime, a context, and a time coordinate. The
default route uses the wheel's bundled data automatically:

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

state = ctx.position.state_at_ut1(taiyin.Body.mars, ut1)
assert ctx.last_status == 0
print(state.position_au)
```

`context.position.at_ut1(...)` returns a compact coordinate tuple:
`(longitude, latitude, distance)`, with three rates appended when
`PositionFlag.speed` is set. `state_at_ut1(...)` returns Cartesian position,
velocity, and acceleration in AU-based units.
Use the TT or TDB variants when the input time scale is already known; do not
silently relabel a UTC civil time as UT1.

## Dense position scans

The regular `at_*` methods are already compact and raise on a native
calculation failure. They return `(longitude, latitude, distance)`, with three
rate values appended when `PositionFlag.speed` is set:

```python
flags = (
    taiyin.PositionFlag.radians,
    taiyin.PositionFlag.truepos,
    taiyin.PositionFlag.nonut,
    taiyin.PositionFlag.speed,
)
values = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
lon, lat, distance, lon_rate, lat_rate, distance_rate = values
```

`batch_at_tt()` and `batch_at_ut1()` apply the same compact return convention
to a sequence of bodies. Pass an already-combined integer flag mask in a hot
Python loop to avoid rebuilding the mask on every call.

For scalar calls, route selection, coverage, and time-scale fallback are
available from the context's lazy diagnostic snapshot; diagnostics are
deliberately not on the normal success path.

For a one-off check after a compact scalar call, inspect the context snapshot
instead. It lives in native context-owned storage and is converted to a Python
`EphemerisDiagnostic` only when accessed:

```python
mars = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
assert ctx.last_status == 0
diagnostic = ctx.last_diagnostic
print(diagnostic.component_method_id)
```

The next calculation on `ctx` replaces this snapshot. Compact batch calls set
`last_status` but leave `last_diagnostic` as `None`, because one batch can have
several independent route choices.

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

moon = ctx.observed.at_ut1(
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
```

Longitude is east-positive and latitude is north-positive. Horizontal and
atmospheric calculations currently support Earth observers only.

## Physical phenomena

`context.phenomena` supplies phase angle, illumination, elongation, apparent
diameter, magnitude, and parallax for the Sun, Moon, and physical planets:

```python
venus = ctx.phenomena.at_ut1(taiyin.Body.venus, ut1)
print(venus.illuminatedFraction)
print(venus.apparentMagnitude)
```

Phenomena methods return their result object directly and raise on failure.
Inspect `ctx.last_status` and `ctx.last_diagnostic` immediately after a call
when using external or partial-coverage data and route provenance matters.
