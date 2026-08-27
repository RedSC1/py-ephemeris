# Ziwei Doushu

Ziwei Doushu is an optional native extension. It is separate from both the
base astronomy/calendar package and the BaZi package:

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
```

Import `taiyin_ziwei` only after installation. A Ziwei context is created from
an existing `EphemerisContext`, not from a second ephemeris runtime:

```python
import taiyin
import taiyin_ziwei

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ziwei = ctx.ziwei()
```

That ownership is intentional: Chinese calendar mode, local day boundary,
historical reform data, and all loaded ephemeris sources stay a single source
of truth for the chart.

The default uses the cached `ctx.chinese_calendar`. To calculate an alternate
calendar policy without constructing a second ephemeris context, create a
calendar child and pass it explicitly:

```python
calendar = ctx.create_chinese_calendar(
    taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(0)
)
ziwei = ctx.ziwei(calendar=calendar)
```

An explicit calendar must belong to the same `ctx`.

## Natal charts

Use one time source per call. `calculate_local()` receives local civil time and
derives the UTC instant from the attached Chinese calendar configuration;
`calculate_instant()` does the reverse.

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
chart, chart_flags = ziwei.calculate_local(
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)

print(chart.anchors.ziwei)
print(chart_flags)
life = chart.palace(taiyin_ziwei.ZiweiPalace.life)
print(life.branchId, life.stemId, [star.key for star in life.stars])
```

## Local apparent ("true") solar time

To use local apparent solar time, derive it from the one physical UTC instant
and the birthplace longitude. Then call the lower-level `create_chart()` with
the physical instant and its derived virtual clock. Do **not** pass the
corrected clock to `calculate_local()`, which would interpret it as ordinary
civil time and apply the configured offset again.

```python
import math

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
solar_ut1 = instant_utc  # UTC−UT1 is sub-second; use utc_to_ut1() if DUT1 is known.

local_mean = taiyin.LocalMeanSolarTime.from_ut1(
    solar_ut1,
    longitudeRadians=math.radians(118.582),
)
local_apparent, solar_flags = ctx.solar_time.mean_to_apparent(local_mean)
true_solar_time, clock_flags = ctx.time.reverse_julian_day(
    local_apparent.coordinate
)

chart, chart_flags = ziwei.create_chart(
    instant_utc,
    true_solar_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)
result_flags = solar_flags | clock_flags | chart_flags
print(true_solar_time, chart.anchors.ziwei, result_flags)
```

`create_chart()` still obtains the lunar date from the attached
`ChineseCalendarContext` at the physical instant. The apparent-solar clock
controls the virtual clock, four pillars, Rat-hour handling, and related solar
day calculations. If the correction crosses midnight and a school also wants
the lunar date to change at apparent-solar midnight, that separate calendar
day-boundary convention is not currently implemented.

`ChineseCalendarConfig.local_astronomical_meridian()` uses a local mean-solar
day boundary while retaining its separate `utc_offset_minutes` for the civil
birth clock. It is not equivalent to applying the equation of time.

`chart.anchors` is a `ZiweiAnchors` object. Access stable slots with
`ZiweiAnchorSlot`, for example
`chart.anchors[ZiweiAnchorSlot.palaceCareer]`; named conveniences include
`anchors.ziwei`, `anchors.tianfu`, and `anchors.palace_position(...)`.

`chart.palaces` returns the twelve named `ZiweiPalaceState` values in Life
through Parents order. Each has its physical branch, palace stem, and placed
stars. `chart.star_position(star)` and `chart.star_palace(star)` provide the
inverse lookup.

## Rules and options

The package ships its default TOML catalog. `ZiweiDataCatalog()` loads it once;
contexts select immutable rule snapshots, so reloading a catalog never changes
an existing chart or context.

```python
catalog = taiyin_ziwei.ZiweiDataCatalog("/path/to/profile.toml")
selection = taiyin_ziwei.ZiweiOptionSelection(
    placementDefault="option1",
    longevity="option2",  # fire/earth-shared twelve-life-stage convention
    brightness={"ziwei": "option2"},
    sihua={"geng": "option3"},
)
ziwei = ctx.ziwei(catalog, selection)

# Future contexts see the new file snapshot; existing ones retain theirs.
catalog.reload()
```

`ZiweiBirthOptions` independently selects early/late-Rat-hour behavior, leap
month strategy, Tian/Di/Ren chart mode, and the solar-term/lunar boundary used
for Wu-Hu-Dun, Si-Hua, and body master.

## Flow charts and navigation

`set_flow()` replaces the chart's optional contiguous overlay stack. By default
it installs Decade, Year, Month, Day, and Hour; use `deepest_level` when a
shallower result is sufficient.

```python
target_local = taiyin.AstroDateTime(2025, 3, 13, 14, 15)
target_utc = target_local.to_julian_date().add_seconds(-8 * 3600)
flow, flow_flags = chart.set_flow(target_utc, target_local)
print(flow.decade)
print(flow_flags)

year = chart.flow_layer_summary(taiyin_ziwei.ZiweiFlowLevel.year)
print(year["life_palace"], year["transforms"])
```

For lunar-month flow, `ZiweiFlowResolution` exposes the written
`targetMonth`, selected `targetEffectiveMonth`, physical
`targetMonthSequence`, `targetMonthName`, `targetMonthBuildingBranch`
(`0 = Zi` through `11 = Hai`), and `targetPalaceMonthIndex` independently.
These come from the attached Chinese calendar rather than a guessed ordinal,
so leap months and historical reforms retain their physical structure.

The default `ZiweiFlowMonthPalaceStrategy.physicalSequence` advances the
Liu-Nian Dou-Jun palace once for every physical lunation. Pass
`ZiweiFlowOptions(flowMonthPalaceStrategy=ZiweiFlowMonthPalaceStrategy.effectiveMonth)`
for a school that follows the leap segment's effective month instead. This
selection changes the palace rule, not the underlying calendar facts.

Use `next_flow_hour_target()` / `previous_flow_hour_target()` rather than
adding two clock hours manually. They preserve the 13-slot Early-Zi through
Late-Zi ordering under split-Rat-hour modes. `next_flow_day_target()` and its
previous counterpart retain wall-clock fields while moving one local civil day.

## Reverse lookup

Tier-1 reverse lookup enumerates finite logical birth-time slots and verifies
each with the same forward chart rules. It does not claim minute-level birth
time reconstruction.

```python
ziwei_star = ziwei.find_star("ziwei")
query = taiyin_ziwei.ZiweiTier1ReverseQuery(
    ziweiBranch=chart.star_position(ziwei_star),
)
candidates, candidate_flags = ziwei.reverse_lookup_tier1(
    target_utc,
    target_utc.add_seconds(24 * 3600),
    target_local,
    gender=taiyin_ziwei.ZiweiGender.male,
    query=query,
)
```

`ZiweiTier1ReverseQuery` can constrain Lu Cun, Hong Luan, Zuo Fu, You Bi, Wen
Chang, Wen Qu, San Tai, Ba Zuo, and Ziwei. Every supplied value is a physical
branch ID from 0 (Zi) through 11 (Hai); at least one constraint is required.
