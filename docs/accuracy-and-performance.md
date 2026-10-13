# Accuracy and performance

This document describes the installed **Python binding**, not bare C++ calls.
Unless a paragraph explicitly identifies an OPM2 or native-model report, all
validation and performance measurements below call Taiyin's public Python API.
The timings therefore include Python-to-pybind dispatch and construction of the
documented Python result object. The performance tables contain no raw C++
timings or cross-library speed comparisons.

`py-ephemeris` is a direct binding to Taiyin's native C++ runtime. Its numerical
behavior is determined by the selected route, data product, time scale,
observer model, and calculation options—not by Python alone.

Version 1.0.0 is stable. The measurements below identify the validated data,
models, intervals, and sampling; they are not a blanket error bound for every
body, epoch, or derived event.

## Accuracy scope

| Route or feature | Current statement | Important boundary |
| --- | --- | --- |
| Bundled DE442-derived major-body OPM2 | Typical reconstruction difference from its DE442 source is on the order of **0.001 arcsec** | This is state-compression error only, not a final apparent or topocentric error. |
| External JPL BSP/SPK | The native runtime evaluates the supplied source directly | Results inherit the product's coverage, model, and time-scale limits. |
| Built-in semi-analytical route | Data-free main-body fallback over approximately astronomical years -6000 through +10000 | Satellite/COB routes have narrower intervals; numerical accuracy depends on body and epoch. |
| Bundled small-body OPM2 | Direct precise route within each file's declared coverage | Do not extrapolate a product beyond its manifest interval. |
| TKC1 Kepler tiers | Compact approximate fallback for supported minor bodies | Use OPM2 or SPK data for precision astrometry, close approaches, or occultations. |
| Compact satellite fallback | Supports selected systems without an external satellite kernel | It is not a precision satellite ephemeris; relative-position errors can range from tens to several hundred kilometres depending on system and interval. |
| Fixed stars | Propagated from the selected TSC1/TSF1 catalog record | Accuracy depends on the catalog, epoch, proper motion, parallax, radial velocity, and observer model. |

The bundled DE442 OPM2 product covers approximately 1550–2650. Outside that
interval, inspect the selected route through diagnostics and add a suitable
SPK/OPM source when precision matters. The wheel intentionally does not bundle
large satellite SPKs, external EOP updates, full star catalogs, or lunar-limb
topography. The native core provides a built-in EOP snapshot; supply updated
EOP data or explicitly allow estimates outside its coverage when appropriate.

### Data-free model accuracy

The native model's DE441 comparisons give the following geometric angular
RMS values. These are C++ model-validation results, distinct from the Python
OPM2/SPK comparison below:

| Model | 1600–2200 RMS | Full -6000–+10000 RMS |
| --- | ---: | ---: |
| Mercury–Neptune, including Earth (heliocentric directions) | 0.0132–0.0364″ across bodies | 0.0911–1.0124″ across bodies |
| Moon (geocentric direction) | 0.129″ | 1.173″ |
| Pluto (native geometric state model) | 0.025″ | 25.5″ |

Planet grids contain 401 modern / 1,201 full-range epochs per body; the Moon
and Pluto use 601 modern / 2,001 full-range epochs. These sparse grids are not
worst-case bounds. In particular, broad Pluto coverage is a computable
fallback, not precision astrometry. See the
[native model report](https://github.com/RedSC1/taiyin-ephemeris/blob/v1.0.0/docs/semi_analytic_ephemeris.md)
for per-body results, reference frames, and satellite/COB limits.

### Derived calculations

An event time, observed altitude, lunar date, or eclipse contact is a derived
result. It can be more sensitive than a Cartesian state to:

- UTC/UT1/TT/TDB conversion, including the available EOP and Delta-T model;
- terrestrial observer location, polar motion, atmosphere, and refraction;
- physical-body versus barycenter routes and center-of-body corrections;
- lunar-limb or local-horizon options; and
- shallow and grazing geometry, which amplifies small position differences.

For a reproducible result, record the package version, native core revision,
input filenames/product identities, route, `taiyin.ResultFlag` value, observer
configuration, and requested time scale. Use explicit `data_root`,
`source_paths`, or provider priority when AUTO selection must not change as data
are added.

## Python-facing validation status

On 2026-10-13 the installed 1.0.0 Release binding completed **235 tests** across
the base, BaZi, and Ziwei suites, using the C++ source data for integration
fixtures. Most tests use the public facade; a small binding/callback subset
deliberately reaches `_native` to verify the extension boundary itself. The
suite covers time conversion, positions and states, observer configuration,
fixed stars, events and visibility, eclipses and occultations, orbital results,
astrology, Chinese-calendar behavior, BaZi, and Ziwei extension integration.
Fixed numeric integration cases commonly select the C++ source tree's DE441
600-year fixture so their route cannot change when packaged priorities evolve;
packaged-data tests and the accuracy driver below exercise the wheel's bundled
DE442 product explicitly.

These are behavioral regression tests, not independent claims of absolute
astrometric accuracy. The current validation layers are:

1. OPM2 generation validates reconstructed states against the source ephemeris;
2. the installed Python package exercises those routes through public APIs;
3. stored event, eclipse, calendar, star, and observer cases detect behavioral
   changes in the binding and core; and
4. every reproducible report identifies its data product and route.

The typical `0.001 arcsec` figure is an OPM2 source-reconstruction metric. It is
reported here because the Python package ships that product, but it is not a
measurement of Python wrapper error and must not be read as a bound on every
apparent, topocentric, or derived output.

### Packaged OPM2 versus DE442 through Python

Rechecked on 2026-10-13 with Python 1.0.0 (`b71f795`) and Taiyin C++ `v1.0.0`,
through an installed local Release build. The angular figures below agree
with the earlier report at the displayed precision. The performance baseline
later in this document remains the separately dated Linux-wheel measurement.

[`benchmarks/python_accuracy.py`](../benchmarks/python_accuracy.py) loaded the
wheel's packaged OPM2 files and an original `de442.bsp` into the same
`Ephemeris`, then forced two public Python contexts to use OPM2 and SPK routes.
The comparison used 128 evenly spaced epochs from JD 2,300,000 to 2,680,000
for each target. Values are geocentric Cartesian equatorial positions requested
with `truepos` and `nonut`; angular error is the separation of their
Earth-to-target vectors.

| Target | Angular RMS / max | Vector RMS / max |
| --- | ---: | ---: |
| Sun | 0.0001335″ / 0.0004594″ | 0.136 / 0.412 km |
| Moon | 0.0000987″ / 0.0001847″ | 0.000232 / 0.000376 km |
| Mercury barycenter | 0.0001529″ / 0.0004590″ | 0.149 / 0.432 km |
| Venus barycenter | 0.0003457″ / 0.0014758″ | 0.179 / 0.490 km |
| Mars barycenter | 0.0002420″ / 0.0014786″ | 0.307 / 0.744 km |
| Jupiter barycenter | 0.0001959″ / 0.0004367″ | 0.958 / 1.725 km |
| Saturn barycenter | 0.0002002″ / 0.0004478″ | 1.731 / 3.197 km |
| Uranus barycenter | 0.0001472″ / 0.0002876″ | 2.680 / 4.490 km |
| Neptune barycenter | 0.0001541″ / 0.0002772″ | 4.446 / 6.782 km |
| Pluto barycenter | 0.0001315″ / 0.0002818″ | 4.416 / 6.589 km |
| **All 1,280 samples** | **0.0001924″ / 0.0014786″** | **2.248 / 6.782 km** |

The increasing kilometre difference for distant planets reflects their much
larger vector length; their directional errors remain at roughly the
milliarcsecond scale.
This test isolates route reconstruction and does not include refraction,
topocentric geometry, or physical-planet center-of-body reconstruction.

### Derived-event check through Python

The same script runs without external files and compares the packaged route's
2024-04-08 global solar eclipse with the [Purple Mountain Observatory rounded
almanac table](https://www.pmo.cas.cn/xwdt2019/kpdt2019/202312/P020240201511299456727.txt):

| Event | Taiyin − PMO |
| --- | ---: |
| P1 | +1.785 s |
| C1 | +1.211 s |
| Greatest | +0.241 s |
| C4 | +0.872 s |
| P4 | −0.413 s |

PMO publishes whole-second contact times and a greatest location rounded to
0.1 arcminute. Against that rounded location, the Python result differs by
+16.594″ latitude and −16.916″ longitude in the 1.0.0 recheck. This is an
event-level regression, not an absolute error bound for other eclipses or
grazing contacts.

## Performance

The baseline below measures the installed wheel exclusively through public
Python methods. It uses the packaged DE442-derived OPM2 product through the
default AUTO route, including any required center-of-body fallback. Every
number includes pybind dispatch and Python-visible result construction.

### Linux Python baseline — 2026-08-13

| Environment item | Value |
| --- | --- |
| Host | `VM-0-14-ubuntu` (KVM virtual machine) |
| CPU | 4 vCPU, Intel Xeon Platinum 8255C at 2.50 GHz |
| OS | Ubuntu, Linux 6.8.0-101-generic, x86_64 |
| Memory | 3.6 GiB |
| Python | CPython 3.12.3 |
| Compiler / build | GCC 13.3.0, scikit-build-core Release wheel |
| Data | bundled DE442-derived OPM2, packaged OPC, lite TSC1 catalog |
| Revisions | Python `b8fee41`; Taiyin C++ `06ea3f06` |

Position workloads use 8,000 pre-created, changing epochs per round
(`JD + n * 0.0125 d`). Eclipse map/circumstance calls use their fixed event
epoch; searches repeat a fixed start epoch because each call performs the full
search. Every result is the median of seven warm rounds with cyclic garbage
collection disabled only during the timed loop.

| Workload | Data / options | Metric | Result |
| --- | --- | --- | --- |
| Mars `position.at_ut1` | physical Mars (`499`), default apparent ecliptic | 7 × 8,000 calls | **45.22 µs/call** |
| Mars `position.at_ut1` with speed | physical Mars, default apparent ecliptic | 7 × 8,000 calls | **60.39 µs/call** |
| Mars `state_at_ut1` | physical Mars, position, velocity, and acceleration | 7 × 8,000 calls | **82.62 µs/call** |
| Mars barycenter `position.at_ut1` | direct barycenter (`4`) | 7 × 8,000 calls | **27.79 µs/call** |
| Eight physical planets, scalar loop | per-body cost | 7 × 8,000 epochs | **133.87 µs/body** |
| Eight physical planets, `batch_at_ut1` | per-body cost | 7 × 8,000 epochs | **132.13 µs/body** |
| `solar_eclipse_where_at_ut1` | fixed global geometry at the 2024-04-08 eclipse | 7 × 3,000 calls | **39.75 µs/call** |
| `local_solar_circumstances_at_ut1` | Dallas observer, fixed event epoch | 7 × 2,000 calls | **30.81 µs/call** |
| `next_solar_at_ut1` | next global eclipse search | 7 × 80 calls | **1,002.67 µs/call** |
| `next_local_solar_at_ut1` | next local eclipse search for Dallas | 7 × 50 calls | **1,850.34 µs/call** |

These values are a regression baseline for this particular virtual machine,
not portable throughput guarantees. The physical-Mars rows include the
center-of-body route and normal apparent-position pipeline; the barycenter row
does not require that physical-body reconstruction. For this eight-planet
workload the native calculation dominates, so `batch_at_ut1` saves only about
1.3% per body; batch remains useful for a compact multi-result call, but is not
advertised here as an order-of-magnitude shortcut.

The threaded section below measures a different property: throughput when several
workers share one already-configured `EphemerisContext`. It uses one fixed list of
position epochs, runs the same total number of public `position.at_ut1` calls for
1, 2, 4, 6, and 8 workers, and consumes both coordinates and `ResultFlag` from
every call. Configuration is completed before timing and the context is closed
after all workers finish. For each worker count, report the median per-call time
and calculate:

```text
speedup = one_thread_time / thread_count_time
```

The position path measured here releases the GIL, but speedup depends on CPU
capacity, data-cache state, Python version, workload, and other system activity.
Values above one are not guaranteed, and a result below one is useful
information about that machine's parallel overhead. The benchmark prints the
worker count and fixed-workload size so runs remain comparable:

```bash
python benchmarks/python_api.py --threaded-iterations 8000 --threaded-rounds 7
```

In a representative local run using the bundled OPM2 data, scalar
`position.at_ut1` calls did **not** benefit from Python threads. The same fixed
8,000-call workload produced the following median throughput ratios relative to
one worker:

| Context layout | 2 workers | 4 workers | 8 workers |
|---|---:|---:|---:|
| One shared context | 0.73x | 0.54x | 0.47x |
| One cloned context per worker | 0.75x | 0.55x | 0.48x |

The near-identical rows show that the context's diagnostic snapshot is not the
bottleneck. OPM2 state evaluation is sufficiently fast that Python scheduling
and contention in the process-wide ephemeris catalog/segment cache outweigh the
parallel work. Prefer sequential scalar calls or the batch API for this workload.

Threads remain useful for coarse, independent calculations whose native work is
large enough. As a diagnostic experiment, repeated next-solar-eclipse searches
using the semi-analytic provider reached about 1.79x, 2.69x, and 3.60x at 2, 4,
and 8 workers respectively. The same search using the bundled OPM2 route slowed
down as workers were added because it repeatedly hits the shared OPM2 cache.
These figures demonstrate that the benchmarked next-solar-eclipse path releases
the GIL; they are not portable performance guarantees.

The audited calculation families now release the GIL around their pure-C++
segments: positions and stars, observed coordinates, events and visibility,
orbits, occultations, eclipses, heliacal searches, astrology, Chinese calendar,
BaZi, and Ziwei chart construction. Python-backed custom targets, house systems,
and ayanamsha models reacquire the GIL only while executing Python code. Runtime
and catalog mutation, context configuration, cleanup, and tiny table helpers do
not release it. Separate mutable Ziwei charts per worker; do not change runtime
or context configuration while calculations are active.

All worker calls in this section use the same configured context. Do not overlap
benchmark timing with configuration mutation, callback registration, calendar or
chart mutation, or context shutdown.

### Benchmark protocol

The reproducible driver is [`benchmarks/python_api.py`](../benchmarks/python_api.py):

```bash
python benchmarks/python_api.py --batch-iterations 8000
python benchmarks/python_accuracy.py
python benchmarks/python_accuracy.py --de442-bsp /path/to/de442.bsp
```

It intentionally imports only `taiyin` and calls public APIs. Future published
results should retain the environment, data product, AUTO/provider policy,
warm-up, iteration counts, and result-object policy shown above. Scalar and
batch calls must be reported separately.

For now, profile the workload that matters to an application. Reuse an
`Ephemeris` and its calculation contexts, keep an OPC catalog beside external
data directories, and prefer batch APIs when many epochs share a configuration.
