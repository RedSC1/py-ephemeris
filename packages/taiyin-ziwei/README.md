# py-ephemeris-ziwei (Taiyin Ziwei Doushu)

Optional Ziwei Doushu bindings for
[py-ephemeris](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
```

The extension shares a caller-owned `taiyin.EphemerisContext` and its Chinese
calendar configuration.  Its bundled TOML rule catalog is parsed once per
`ZiweiDataCatalog`; contexts select immutable option views without reparsing.

The first release is still under active API stabilization and is not yet
published.  Source builds in this monorepo use the adjacent C++ checkout.

## Create a natal chart

```python
import taiyin
import taiyin_ziwei

context = taiyin.Ephemeris().create_context()
ziwei = context.ziwei()

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
chart, chart_flags = ziwei.calculate_local(
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)

ziwei_star = ziwei.find_star("ziwei")
print(chart.star_position(ziwei_star))
print(chart.summary.transforms)
print("Execution flags:", chart_flags)
```

`calculate_local()` converts the local civil clock using the attached Chinese
calendar context's configured day-boundary policy.  Use `calculate_instant()`
when the physical UTC Julian date is already the source of truth.

## Flow targets and Tier-1 reverse lookup

```python
# Logical slots understand the selected early/late-Rat-hour policy.
birth_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
next_hour = ziwei.next_flow_hour_target(
    birth_utc,
    local_time,
    rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan,
)

# Tier-1 reverse lookup returns matching logical birth-time slots, rather than
# claiming a fictitious minute-precise reconstruction.
candidates, reverse_flags = ziwei.reverse_lookup_tier1(
    birth_utc,
    birth_utc.add_seconds(24 * 3600),
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
    query=taiyin_ziwei.ZiweiTier1ReverseQuery(
        ziweiBranch=chart.star_position(ziwei.find_star("ziwei")),
        lucunBranch=chart.star_position(ziwei.find_star("lucun")),
    ),
)
print(candidates, reverse_flags)
```

For annual through hourly overlays, call:

```python
resolution, flow_flags = chart.set_flow(target_utc, target_local)
```

`deepest_level` can stop at `decade`, `year`, `month`, or `day`; the default
includes all five levels. Lunar-month overlays use the month-building branch
resolved by the attached Chinese calendar, including leap months and historical
calendar reforms.
