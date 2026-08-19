# Events and visibility

Event searches take an interval or an estimate and return
`(result, result_flags)`. Keep the requested step size appropriate for the body
and event; the API can provide recommended longitude/aspect steps.

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
start = taiyin.JulianDate.from_double(2460400.5)
end = taiyin.JulianDate.from_double(2460420.5)

phases, phase_flags = ctx.events.lunar_phase_crossings_at_ut1(
    0.0, start, end, max_step_days=1.0
)
print(phases, phase_flags)

stations, station_flags = ctx.events.longitude_stations_at_ut1(
    taiyin.Body.mercury, start, end, max_step_days=0.25
)
print(stations, station_flags)
```

`context.events` also searches longitude/aspect crossings, exact aspects,
greatest elongations, minimum angular separations, and Mercury/Venus solar
transits. `context.phenomena` calculates the physical properties at a known
time rather than searching for an event.

## Rise, set, transit, and twilight

Visibility searches use the configured observer:

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)

sunrise, sunrise_flags = ctx.visibility.solar_rise_set_at_ut1(
    start, end, event=taiyin.VisibilityEventKind.rise
)
twilight, twilight_flags = ctx.visibility.solar_twilight_at_ut1(
    start,
    end,
    event=taiyin.VisibilityEventKind.set,
    twilight=taiyin.TwilightKind.civil,
)
print(sunrise.coordinate, twilight.coordinate)
print(sunrise_flags | twilight_flags)
```

The same service searches Moon, planet, and fixed-star rise/set and upper/lower
transits. `context.heliacal` evaluates or searches first/last morning/evening
visibility using a configurable extinction and sky-brightness model.
