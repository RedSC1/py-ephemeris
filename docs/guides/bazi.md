# BaZi

BaZi is distributed separately so users who only need astronomy, calendars,
Ganzhi, houses, or eclipses do not install its native extension:

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

Importing `taiyin_bazi` registers `create_bazi()` on the base runtime. The
BaZi context inherits the base runtime's data configuration.

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

bazi = eph.create_bazi()
chart = bazi.calc_chart(pillars)
print(chart.hiddenStems, chart.visibleTenGods, chart.nayinIds)
```

## Qi-Yun and Da-Yun

Qi-Yun adds a direction convention, so it requires a gender value:

```python
qiyun = bazi.calc_qiyun(
    instant_utc,
    local_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
dayun = bazi.fill_dayun(local_time, chart, qiyun, 10)
print(qiyun.startCivilTime, dayun)
```

The four pillars and `BaziChart` themselves are gender-neutral. The configured
`BaziContextConfig` selects the Qi-Yun time model, direction model, and Da-Yun
boundary convention.

## Rule and analysis APIs

`BaziContext` exposes Ten Gods, hidden stems, life stages, stem/branch
relations, flow year/month/day/hour, Xiao-Yun, Renyuan-Siling, chart relations,
and Shen Sha queries. For example:

```python
year_ten_god = bazi.get_ten_god(
    pillars.day.stem_id, pillars.year.stem_id
)
relations = bazi.collect_chart_relations(chart)
print(year_ten_god, relations)
```

See the runnable [BaZi extension example](../examples/bazi_extension.md) and
the [API reference](../api.md) for the full surface.
