# Feature guides

These guides are organized by task. They complement the complete
[API reference](../api.md), which is the place to look up every method and
argument.

| Guide | Main API |
| --- | --- |
| [Positions and observers](positions-and-observers.md) | `context.position`, `context.observed`, `context.phenomena` |
| [Time and solar time](time-and-solar-time.md) | `context.time`, `context.solar_time` |
| [Events and visibility](events-and-visibility.md) | `context.events`, `context.visibility`, `context.heliacal` |
| [Eclipses](eclipses.md) | `context.eclipses` |
| [Occultations](occultations.md) | `context.occultation` |
| [Fixed stars](fixed-stars.md) | `eph.star_catalog`, `context.stars` |
| [Sidereal astrology and houses](astrology-and-houses.md) | `context.astrology` |
| [Chinese calendar and Ganzhi](chinese-calendar-and-ganzhi.md) | `context.chinese_calendar`, `context.ganzhi` |
| [BaZi](bazi.md) | `taiyin_bazi`, `ctx.bazi()` |
| [Ziwei Doushu](ziwei.md) | `taiyin_ziwei`, `ctx.ziwei()` |
| [Orbits](orbits.md) | `context.orbits` |
| [Bundled and external data](../bundled-data.md) | `Ephemeris(...)`, catalog and source paths |
| [Accuracy and performance](../accuracy-and-performance.md) | Data/route scope and reproducible benchmarks |

Runnable examples with their input/output notes are under
[`docs/examples/`](../examples/).
