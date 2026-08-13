# Eclipse and visibility search

Script: [`examples/eclipse_and_visibility.py`](../../examples/eclipse_and_visibility.py)

```bash
python examples/eclipse_and_visibility.py
```

The script configures an Earth observer at 118.582° E, 37.449° N and performs
two searches against the bundled ephemeris data:

- A sunrise search in the two-day interval beginning at 2024-01-01 00:00
  UTC+08:00.
- The next local solar eclipse at that observer after the same start time.

Observer location is context configuration. Once it is set with
`context.configuration.set_observer_location(...)`, both visibility searches
and local eclipse searches use it. The returned local eclipse result exposes
its kinds, maximum time, magnitude, contact data, and visibility flags.

The search start is converted from UTC+08:00 to UTC. The returned timestamps
are Julian-date values; applications can format them with the time conversion
methods on `context.time` or their own civil-time layer. For global eclipse
paths, Besselian elements, and map/route products, see the eclipse section of
the [API reference](../api.md).
