# Default bundled data

Script: [`examples/default_data.py`](../../examples/default_data.py)

Run this after installing `py-ephemeris` to confirm that the package data are
available without passing a DLL path, ephemeris directory, or catalog path:

```bash
python examples/default_data.py
```

The script creates `taiyin.Ephemeris()` with its defaults. That loads the
wheel's `taiyin/data/index.opc`, then calculates three different data routes:

- Mars's Cartesian state, in AU and AU/day, from the default major-body route.
- Ceres's Cartesian state from a bundled precise asteroid OPM2 file.
- Antares's astrometric coordinates from the automatically loaded lite star
  catalog.

Scalar calculations return their documented result object directly and raise
on failure. The calling context retains a lazy status/diagnostic snapshot;
inspect `context.last_status` and `context.last_diagnostic` immediately after a
call when route provenance or fallback details are needed. The script keeps its
output deliberately raw so the result types and their units are visible.

See [bundled data](../bundled-data.md) for the exact products, coverage, and
how to add external BSP/SPK, OPM2, TSC1, or TKC1 files.
