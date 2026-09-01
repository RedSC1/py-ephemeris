# py-ephemeris-ziwei (Taiyin Ziwei Doushu)

Optional Ziwei Doushu bindings for
[py-ephemeris](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
```

The extension shares a caller-owned `taiyin.EphemerisContext` and its Chinese
calendar configuration.  Its bundled TOML rule catalog is parsed once per
`ZiweiDataCatalog`; contexts select immutable option views without reparsing.

The beta API remains under stabilization. Source builds prefer the adjacent
C++ checkout and isolated builds pin Taiyin `v1.0.0-beta.8`.

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

## Removable JSON option modules

Use JSON modules for application- or school-specific options without replacing
the bundled TOML catalog:

```python
ruleset = taiyin_ziwei.ZiweiRuleset().add_module(
    taiyin_ziwei.ZiweiJsonRuleModule(
        label="school-a",
        starsJson='[{"key":"ziwei","rule":{"type":"constant","value":5}}]',
    )
)
selection = taiyin_ziwei.ZiweiOptionSelection(
    placement={"ziwei": "school-a"},
)
ziwei = context.ziwei(selection=selection, ruleset=ruleset)

# Removes every option and new star contributed by this user module.
ruleset = ruleset.remove_module("school-a")
```

The module label is its option name across placement, brightness, Si-Hua,
flow-star, and master tables. A module cannot overwrite or remove a bundled
TOML option, and duplicate labels are rejected. Removing a module clears all
of its contributions but does not mutate an existing context snapshot.
`ZiweiStar.isNatal` distinguishes natal registry entries from flow-only stars.

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

`ZiweiFlowResolution` keeps the written month, effective month, physical month
sequence, month-building branch, and palace month index separate. The default
`ZiweiFlowMonthPalaceStrategy.physicalSequence` advances the flow palace for
every physical lunation; select `effectiveMonth` through `ZiweiFlowOptions`
when following a school that assigns a leap segment to its effective month.
