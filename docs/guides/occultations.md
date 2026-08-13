# Lunar occultations

The occultation service searches when the Moon covers a fixed star or a body.
Fixed stars need an installed catalog; the bundled lite catalog is loaded by
default.

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
start = taiyin.JulianDate.from_double(2460400.5)

event = ctx.occultation.next_geocentric_star_at_ut1("antares", start)
print(event.kind, event.coordinate)
print(event.firstContact, event.fourthContact)
```

For an observer-specific event, configure location and call
`next_local_star_at_ut1(...)`. Body variants accept a physical target and an
optional target radius. They are useful for lunar occultations of planets or
other modeled bodies.

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
local = ctx.occultation.next_local_body_at_ut1(taiyin.Body.mars, start)
print(local.begin, local.end, local.types)
```

After a search, `local_star_visibility_at_ut1()` / `local_body_visibility_at_ut1()`
provide visibility intervals and samples. `star_where_at_ut1()` and
`body_where_at_ut1()` produce path/visible-region data for mapping.
