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

## Natal charts

Use one time source per call. `calculate_local()` receives local civil time and
derives the UTC instant from the attached Chinese calendar configuration;
`calculate_instant()` does the reverse.

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
chart = ziwei.calculate_local(
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)

print(chart.anchors.ziwei)
life = chart.palace(taiyin_ziwei.ZiweiPalace.life)
print(life.branchId, life.stemId, [star.key for star in life.stars])
```

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
chart.set_flow(target_utc, target_local)

year = chart.flow_layer_summary(taiyin_ziwei.ZiweiFlowLevel.year)
print(year["life_palace"], year["transforms"])
```

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
candidates = ziwei.reverse_lookup_tier1(
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
