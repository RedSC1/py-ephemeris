# Orbits

`context.orbits` derives osculating elements and searches orbital events from
the selected ephemeris route.

```python
import taiyin

ctx = taiyin.Ephemeris().create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

# Calculate Mars's instantaneous osculating orbital elements at this epoch.
orbit = ctx.orbits.osculating_at_ut1(taiyin.Body.mars, ut1)
print("Semi-major axis:", orbit.semiMajorAxisAu, "AU")
print("Eccentricity:", orbit.eccentricity)

# Search forward from this epoch for Mars's next perihelion.
perihelion = ctx.orbits.search_apsis_from_ut1(
    taiyin.Body.mars,
    taiyin.ApsisKind.pericenter,
    ut1,
)
print("Next perihelion:", perihelion.coordinate)
print("Distance at perihelion:", perihelion.distanceAu, "AU")
```

Reference-point methods return periapsis/apoapsis, ascending/descending nodes,
and related orbital geometry for a chosen frame. Plane-node searches accept a
reference frame and search direction.

Some body routes may only expose barycenter data. Set
`allow_barycenter_approximation=True` only when that approximation is suitable
for the task; result objects preserve whether it was allowed.
