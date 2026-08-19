# Eclipses

`context.eclipses` searches global lunar/solar eclipses and calculates local
circumstances for the observer configured on the context.

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
start = taiyin.JulianDate.from_double(2460400.5)

global_solar, global_flags = ctx.eclipses.next_solar_at_ut1(start)
print(global_solar.kinds, global_solar.maximum, global_flags)

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
local_solar, local_flags = ctx.eclipses.next_local_solar_at_ut1(start)
print(local_solar.kinds, local_solar.magnitude, local_flags)
```

The global result reports event kinds, contacts, greatest time, shadow
geometry, and maximum location. The local result reports local contact times,
Sun altitude/azimuth, magnitude, obscuration, and visibility flags.

## Ranges, paths, and Besselian output

Use `solar_eclipses_at_ut1()` / `lunar_eclipses_at_ut1()` for a date range.
For a known solar-eclipse estimate, the same service provides:

- local circumstances and local boundary queries;
- Besselian elements and fitted Besselian polynomials;
- lightweight one-epoch global geometry (`solar_eclipse_where_at_tt()` / `_at_ut1()`);
- route rows, curves, and map products for global path rendering.

Use the lightweight geometry call when a map needs only one instant's center
line plus core and penumbral north/south limits. It intentionally omits the
half-magnitude limits, path width, duration, and center-line refinement that a
full route row calculates:

```python
where, where_flags = ctx.eclipses.solar_eclipse_where_at_ut1(
    global_solar.maximum
)
print(where.centerLine.latitudeDegrees, where.centerLine.longitudeDegrees)
print(where_flags)
```

These are numerical geometry APIs. They return coordinates and map points;
projection, labeling, and visual map rendering remain the caller's job. The
[eclipse and visibility example](../examples/eclipse_and_visibility.md) shows
the basic local-search setup.
