# BaZi

BaZi is distributed separately so users who only need astronomy, calendars,
Ganzhi, houses, or eclipses do not install its native extension:

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

`EphemerisContext.bazi()` loads the installed `taiyin_bazi` extension on
demand. The BaZi context inherits that calculation context's data and calendar
policy.

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

bazi = ctx.bazi()
result = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
print(result.pillars)
print(result.chart.hiddenStems, result.chart.visibleTenGods, result.chart.nayinIds)
```

## Qi-Yun and Da-Yun

Qi-Yun adds a direction convention, so it requires a gender value:

```python
dayun = bazi.fill_dayun(local_time, result.chart, result.qiyun, 10)
print(result.qiyun.startCivilTime, dayun)
```

The four pillars and `BaziChart` themselves are gender-neutral. The configured
`BaziContextConfig` selects the Qi-Yun time model, direction model, and Da-Yun
boundary convention. Calendar-dependent BaZi calculations share one
`ChineseCalendarContext` with four-pillar calculations, so the civil-time
offset is configured only once. The default is UTC+08:00; for example,
UTC-05:00 can be selected with:

```python
calendar_config = taiyin.ChineseCalendarConfig.utc_offset(-5 * 60)
ctx = eph.create_context(chinese_calendar_config=calendar_config)
bazi = ctx.bazi()
result = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
```

Four pillars, Qi-Yun, and Renyuan-Siling all use `ctx.chinese_calendar`; a
different calendar policy therefore requires a different calculation context.

`calculate_local()` accepts one local civil time and derives UTC from that
configuration. If the input is already a UTC Julian instant, use the equally
single-source form `bazi.calculate_instant(instant_utc, gender=...)`; it
derives local civil time internally.

## Rule and analysis APIs

`BaziContext` exposes Ten Gods, hidden stems, life stages, stem/branch
relations, flow year/month/day/hour, Xiao-Yun, Renyuan-Siling, chart relations,
and Shen Sha queries. For example:

```python
year_ten_god = bazi.get_ten_god(
    result.pillars.day.stem_id, result.pillars.year.stem_id
)
relations = bazi.collect_chart_relations(result.chart)
print(year_ten_god, relations)
```

See the runnable [BaZi extension example](../examples/bazi_extension.md) and
the [API reference](../api.md) for the full surface.
