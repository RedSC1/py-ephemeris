# Fixed stars

The default wheel loads a lite TSC1 catalog once per process. It includes bright
stars, common aliases, the 28 Chinese mansion determinative stars, and western
zodiac representative stars.

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

antares = ctx.stars.at_ut1("antares", ut1)
print(antares.value.coordinates)
print(eph.star_catalog.magnitude_of("角宿一"))
```

Star catalog registration is process-wide. Add additional TSC1 or TSF1 files
through `eph.star_catalog.add_tsc1(path)` or `add_tsf1(path)` before querying
their names. If duplicate aliases exist, catalog order determines which entry
is found first; use curated source files for reproducible naming.

Observed stars use the same Earth-observer configuration as solar-system
bodies:

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
observed = ctx.stars.observed_at_ut1(
    "antares",
    ut1,
    flags=(taiyin.ObservedFlag.topocentric, taiyin.ObservedFlag.horizontal),
)
print(observed.horizontal)
```

See [bundled data](../bundled-data.md) for catalog paths and manual reload
behavior after clearing the process-wide catalog.
