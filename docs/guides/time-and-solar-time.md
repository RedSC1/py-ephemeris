# Time and solar time

Use a timezone-aware standard-library `datetime` when the physical instant is
known:

```python
from datetime import datetime, timedelta, timezone
import taiyin

instant = datetime(
    2003, 3, 13, 14, 15,
    tzinfo=timezone(timedelta(hours=8)),
)
utc = taiyin.JulianDate.from_datetime(instant)
unix_utc = taiyin.JulianDate.from_timestamp(instant.timestamp())

# A separate wall-clock value is useful when a calendar or divination API
# needs both the instant and the displayed local fields.
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
```

`JulianDate.from_datetime()` rejects naive values instead of silently using
the host machine's timezone. It converts the aware value exactly at Python's
microsecond resolution without first reducing it through the floating-point
result of `datetime.timestamp()`. `JulianDate.from_timestamp()` follows Python
convention and accepts Unix **seconds** as an `int` or `float`. These adapters
identify an instant; they do not read or override a Chinese-calendar context.

`context.time` provides UTC/TAI/TT/UT1/TDB conversion and Delta-T helpers.
The context-managed route reads its configured leap-second, EOP, Delta-T, and
TDB policies:

```python
eph = taiyin.Ephemeris()
ctx = eph.create_context()
scales, scale_flags = ctx.time.scales_from_utc(utc)
print(scales.tt, scales.ut1, scales.tdb)
print(scale_flags)

utc_again, utc_flags = ctx.time.tdb_to_utc(scales.tdb)
ut1_again, ut1_flags = ctx.time.tdb_to_ut1(scales.tdb)
utc_clock, clock_flags = ctx.time.utc_calendar_from_ut1(scales.ut1)
```

Automatic reverse routes are available through `tai_to_utc()`, `tt_to_utc()`,
`ut1_to_utc()`, and `tdb_to_utc()`. Automatic UT1 routes are
`utc_to_ut1()`, `tai_to_ut1()`, `tt_to_ut1()`, and `tdb_to_ut1()`; passing an
explicit `dut1_seconds` or `delta_t_seconds` retains the low-level offset
route. `calendar_from_ut1()` formats UT1 without conversion, whereas
`utc_calendar_from_ut1()` first performs the physical UT1-to-UTC conversion.
An inserted leap second reached from TAI, TT, or TDB cannot be represented by
the uniform split UTC coordinate and raises `UtcLeapSecondRepresentationError`.
UT1 alone cannot distinguish that label from the following representable
midnight in the bundled model, so `ut1_to_utc()` resolves the ambiguous
coordinate to midnight.

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
configured Delta-T model. It also applies to automatic reverse conversions and
is reported by `ResultFlag.timeScaleFallback`. It does not affect any
`*_at_ut1()` method; those methods always interpret their input as UT1.

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

`apparent.coordinate` is a Julian coordinate whose calendar fields represent
the local apparent-solar clock. Convert those fields with
`clock, clock_flags = ctx.time.reverse_julian_day(apparent.coordinate)`.
When using that clock for divination, keep the original physical instant as
the calculation instant rather than feeding the corrected clock back through
a civil-time-to-UTC conversion. Complete examples are provided for
[BaZi](bazi.md#local-apparent-true-solar-time) and
[Ziwei Doushu](ziwei.md#local-apparent-true-solar-time).
