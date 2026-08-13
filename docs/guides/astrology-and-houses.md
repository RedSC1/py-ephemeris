# Sidereal astrology and houses

Sidereal positions, ayanamsha, lunar points, and house systems belong to the
base `taiyin` package. They do not require `py-ephemeris-bazi`.

```python
import math
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)

sun = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    ut1,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
houses = ctx.astrology.houses_at_ut1(
    ut1,
    system=taiyin.HouseSystem.porphyry,
)

degrees = lambda radians: math.degrees(radians) % 360.0
print(degrees(sun.value.siderealLongitudeRadians))
print(degrees(houses.ascendantRadians))
```

Built-in ayanamshas include Fagan/Bradley, Lahiri, Raman, Krishnamurti,
Galactic Center 0 Sagittarius, and True Chitra. Built-in house systems include
whole sign, equal, Porphyry, Placidus, Koch, Regiomontanus, Campanus,
Alcabitius, Polich/Page, and Morinus.

The API returns radians and numerical house cusps. Sign formatting, aspect
interpretation, chart glyphs, and UI are intentionally left to the Python
caller. Custom ayanamsha and house models can be registered on `Ephemeris`
with Python callbacks; see the [API reference](../api.md).
