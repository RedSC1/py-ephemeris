# Ziwei chart clocks

`ZiweiClock` selects the **chart's virtual clock**, independently of the
Chinese calendar's month-structure/day-boundary settings. The choices are
`fixedOffset`, `meanSolar`, and `apparentSolar`. Solar longitude is east-positive
in radians. `fixedOffset` applies the attached calendar's offset to **UT1**;
it is not UTC conversion and does not implement time zones or DST.

For normal birth input, pass the policy directly to a high-level factory:

```python
chart, flags = ziwei.calculate_local(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15),
    gender=zw.ZiweiGender.male,
    clock=clock,
)
```

The input remains the original civil clock. Use the explicit UT1 methods below
when the input itself is a chart-clock coordinate or when navigating flows.

```python
import math
import taiyin
import taiyin_ziwei as zw

ctx = taiyin.Ephemeris().create_context()
ziwei = ctx.ziwei()
clock = zw.ZiweiClock(zw.ZiweiClockMode.apparentSolar, math.radians(118.582))
# These fields explicitly describe apparent solar time, not civil UTC+8.
instant, flags = ziwei.chart_time_to_ut1(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15), clock=clock)
chart, flags = ziwei.create_chart_at_ut1(
    instant, gender=zw.ZiweiGender.male, clock=clock)
target, flags = ziwei.step_flow_hour_at_ut1(instant, clock=clock)
flow, flags = chart.set_flow_at_ut1(target.instantUt1, clock=clock)
wall, flags = ziwei.chart_time_from_ut1(target.instantUt1, clock=clock)
```

For a physical UT1 instant, start directly at `create_chart_at_ut1`; callers
starting with UTC must first use the base time-conversion API and explicitly
choose whether missing EOP may be estimated. Do not reinterpret UTC as UT1.

| Task | API |
| --- | --- |
| Physical instant → virtual clock | `chart_time_from_ut1` |
| Virtual clock → physical instant | `chart_time_to_ut1` |
| Natal chart | `create_chart_at_ut1` |
| Flow stack | `chart.set_flow_at_ut1` |
| Next/previous hour or day | `step_flow_hour_at_ut1`, `step_flow_day_at_ut1` (`direction=1/-1`) |
| Reverse lookup | `reverse_lookup_tier1_at_ut1(start, end, gender=..., query=..., clock=...)` |

All return `(value, result_flags)` and raise on fatal errors. New navigation
and reverse results expose `instantUt1`. Existing dual-time methods remain
available with their existing fixed-offset interpretation.

Navigation retains virtual minutes/seconds. Split-Rat modes use one-hour
forward steps at 22:00–01:00 and backward steps at 23:00–02:00 (wrapping across
midnight); otherwise they use two hours. Day navigation advances one virtual
calendar day. Apparent-solar targets are solved nonlinearly, so a day step need
not be exactly 86400 physical seconds. Solver failures do not silently fall back.

Year/month Jie comparisons use the physical instant. Only the Ziwei lunar
date/day/hour labels use the virtual clock and Rat-hour rule. Each previous
Jie is mapped using the clock at that Jie instant, not today's fixed correction.
Reverse lookup visits actual hour and effective Jie boundaries, including
historical assigned boundaries; results are matching slots, not exact birth
times. Use the same clock explicitly for subsequent operations.

Install matching base and Ziwei builds. The Python layer only converts
arguments/results. Birth, flow, navigation and
reverse search execute the same C++ adapters as the core library, using the
base package's existing calendar and ephemeris runtime through a checked private
bridge. No independent Python calendar algorithm or second runtime is used.
For deterministic cleanup, use context managers or close the owning context.
