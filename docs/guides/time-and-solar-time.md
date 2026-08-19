# Time and solar time

`AstroDateTime` represents a civil calendar value. Convert it explicitly to
the time scale a calculation expects. For a UTC+08:00 civil input:

```python
import taiyin

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
utc = local_time.to_julian_date().add_seconds(-8 * 3600)
```

The `-8 * 3600` conversion is only appropriate when the caller has already
chosen a fixed UTC+08:00 offset. Applications accepting arbitrary places and
historical dates should resolve their civil time zone first, then pass the
corresponding UTC value to Taiyin.

`context.time` provides UTC/TAI/TT/UT1/TDB conversion and Delta-T helpers.
For example:

```python
eph = taiyin.Ephemeris()
ctx = eph.create_context()
scales, scale_flags = ctx.time.precise_scales_from_utc(utc)
print(scales.tt, scales.ut1, scales.tdb)
print(scale_flags)
```

The precise conversion uses available Earth-orientation data. Position and
event result diagnostics record the selected time-scale route and fallback
information for downstream calculations.

`at_utc()` calculations are strict by default: unavailable leap-second or EOP
data raise an error. A caller that deliberately accepts lower precision may
enable the explicit fallback:

```python
ctx.time.set_allow_utc_out_of_range_estimate(True)
```

The fallback approximates the supplied UTC civil value as UT1 and uses the
configured Delta-T model. It does not affect any `*_at_ut1()` method; those
methods always interpret their input as UT1.

## Equation of time

Use `context.solar_time` for mean/apparent solar-time conversion:

```python
equation, equation_flags = ctx.solar_time.equation_of_time_at_ut1(scales.ut1)
print(equation.equationSeconds)

mean = taiyin.LocalMeanSolarTime.from_ut1(
    scales.ut1, longitudeRadians=118.582 * 3.141592653589793 / 180.0
)
apparent, apparent_flags = ctx.solar_time.mean_to_apparent(mean)
print(apparent)
print(equation_flags | apparent_flags)
```
