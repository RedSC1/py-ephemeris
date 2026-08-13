# BaZi extension

Script: [`examples/bazi_extension.py`](../../examples/bazi_extension.py)

Install both distributions, then run it:

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
python examples/bazi_extension.py
```

The example uses the following fixed input:

```text
Civil time: 2003-03-13 14:15 (UTC+08:00)
```

It converts the civil time to UTC, calculates the four pillars with the base
`taiyin` package, then imports `taiyin_bazi` for its enums. `ctx.bazi()` loads
the installed extension on demand, and the returned context inherits the base runtime's data
configuration.

The script demonstrates chart construction, Qi-Yun, and a Ten-God lookup.
Gender is only needed for the Qi-Yun direction convention; the four pillars
and the chart themselves are gender-neutral.
