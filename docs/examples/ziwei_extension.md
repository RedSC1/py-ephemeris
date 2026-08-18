# Ziwei Doushu extension

Script: [`examples/ziwei_extension.py`](../../examples/ziwei_extension.py)

Install the base package and the optional Ziwei native extension:

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
python examples/ziwei_extension.py
```

The script uses a fixed local civil time of `2003-03-13 14:15` under the
default UTC+08:00 Chinese-calendar policy. It demonstrates a natal chart,
named palace view, and annual flow overlay. The `ZiweiContext` comes from
`ctx.ziwei()`, so its calendar facts, historical-calendar profile, day
boundary, and ephemeris data all remain those of the owning calculation
context.
