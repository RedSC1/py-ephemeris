# Accuracy and performance

`py-ephemeris` is a direct binding to Taiyin's native C++ runtime. Its numerical
behavior is determined by the selected route, data product, time scale,
observer model, and calculation options—not by Python alone.

This is a preview package. These statements identify current scope and pending
validation; they are not a blanket accuracy guarantee for every body, epoch,
or derived event.

## Accuracy scope

| Route or feature | Current statement | Important boundary |
| --- | --- | --- |
| Bundled DE442-derived major-body OPM2 | Typical reconstruction difference from its DE442 source is on the order of **0.001 arcsec** | This is state-compression error only, not a final apparent or topocentric error. |
| External JPL BSP/SPK | The native runtime evaluates the supplied source directly | Results inherit the product's coverage, model, and time-scale limits. |
| Built-in semi-analytical route | Data-free fallback over roughly calendar years -3000 through +3000 | It is a fallback, not a replacement for an in-range OPM2 or SPK product. |
| Bundled small-body OPM2 | Direct precise route within each file's declared coverage | Do not extrapolate a product beyond its manifest interval. |
| TKC1 Kepler tiers | Compact approximate fallback for supported minor bodies | Use OPM2 or SPK data for precision astrometry, close approaches, or occultations. |
| Compact satellite fallback | Supports selected systems without an external satellite kernel | It is not a precision satellite ephemeris; relative-position errors can range from tens to several hundred kilometres depending on system and interval. |
| Fixed stars | Propagated from the selected TSC1/TSF1 catalog record | Accuracy depends on the catalog, epoch, proper motion, parallax, radial velocity, and observer model. |

The bundled DE442 OPM2 product covers approximately 1550–2650. Outside that
interval, inspect the selected route through diagnostics and add a suitable
SPK/OPM source when precision matters. The wheel intentionally does not bundle
large satellite SPKs, EOP tables, full star catalogs, or lunar-limb topography.

### Derived calculations

An event time, observed altitude, lunar date, or eclipse contact is a derived
result. It can be more sensitive than a Cartesian state to:

- UTC/UT1/TT/TDB conversion, including the available EOP and Delta-T model;
- terrestrial observer location, polar motion, atmosphere, and refraction;
- physical-body versus barycenter routes and center-of-body corrections;
- lunar-limb or local-horizon options; and
- shallow and grazing geometry, which amplifies small position differences.

For a reproducible result, record the package version, native core revision,
input filenames/product identities, route/flags, observer configuration, and
requested time scale. Use explicit `data_root`, `source_paths`, or provider
priority when AUTO selection must not change as data are added.

## Validation plan

The core repository validates OPM2 reconstruction against its source
ephemeris. Before the first stable Python release, this binding will publish a
matching Python-facing report covering:

1. state and apparent-position differences against the selected source;
2. event-time differences for phases, rise/set, and representative eclipses;
3. fixed-star and observer-coordinate regression cases; and
4. the data files, epoch grids, metrics, and worst-case samples used.

Until then, treat `0.001 arcsec` strictly as the documented typical OPM2
reconstruction scale—not as a claim about every output.

## Performance

Python call overhead and native calculation cost must be measured together.
The baseline below uses the installed wheel's bundled DE442-derived OPM2 data,
not the built-in semi-analytical fallback. It includes wrapper and result
object construction wherever a Python API is named.

### Linux baseline — 2026-08-13

| Environment item | Value |
| --- | --- |
| Host | `grapefanta` |
| CPU | Intel Core i7-4785T, 4 cores / 8 threads, nominal 2.20 GHz (3.2 GHz maximum) |
| OS | Arch Linux, kernel 7.0.10-arch1-1, x86_64 |
| CPU policy during run | `schedutil`; sampled frequency 3.12 GHz |
| Memory | 11 GiB |
| Python | CPython 3.14.5 |
| Compiler / build | GCC 16.1.1, scikit-build-core Release wheel |
| Data | bundled DE442-derived OPM2, packaged OPC, lite TSC1 catalog |

Each Python result is the median of seven warm rounds at changing epochs
(`JD + n * 0.0125 d`), after a warm-up. This avoids presenting one cache-hot
epoch as representative throughput.

| Workload | Data / options | Metric | Result |
| --- | --- | --- | --- |
| Mars `position.at_ut1` | physical Mars (`499`), default apparent ecliptic | 7 × 8,000 calls | **50.59 µs/call** (19,768 calls/s) |
| Mars `position.at_ut1` with speed | physical Mars, default apparent ecliptic | 7 × 8,000 calls | **63.82 µs/call** (15,668 calls/s) |
| Mars raw native binding | physical Mars, same flags, before Python result objects | 7 × 8,000 calls | **39.10 µs/call** |
| Mars `state_at_ut1` | physical Mars, position, velocity, and acceleration | 7 × 8,000 calls | **71.26 µs/call** (14,034 calls/s) |
| Mars barycenter `position.at_ut1` | DE442 direct barycenter (`4`) | 5,000 calls | **about 34.5 µs/call** |
| OPM2 bare ICRF state | Mars barycenter, native C++ probe | 20,000 calls | **1.45 µs/call** |
| OPM2 apparent position | Mars barycenter, native C++ probe | 20,000 calls | **17.52 µs/call** |
| OPM2 apparent position | physical Mars, native C++ probe | 20,000 calls | **32.23 µs/call** |

For orientation only, the same interpreter and changing-epoch loop measured
`pyswisseph 2.10.3.2` / Swiss Ephemeris 20230604 at **13.03 µs/call** for
`calc_ut(Mars, FLG_SWIEPH | FLG_SPEED)` and **13.13 µs/call** for its
equatorial XYZ variant. This is not an accuracy equivalence claim: each
library retains its own data products and apparent-position conventions.

The decomposition is intentional: direct OPM2 evaluation is fast, while the
public physical-Mars result additionally applies a compact Phobos/Deimos
center-of-body correction and the standard apparent-position pipeline.
Python then creates diagnostic and result objects. These are a low-power
Haswell-era machine's regression baseline, not portable throughput claims.

### Benchmark protocol

Future published results will state CPU, operating system, Python version,
compiler/build type, package and core revisions, input data product, warm-up
policy, loop count, and whether Python object creation is included. Scalar and
batch calls will be reported separately. This prevents a cached native loop
and a Python-level loop from being presented as the same measurement.

For now, profile the workload that matters to an application. Reuse an
`Ephemeris` and its calculation contexts, keep an OPC catalog beside external
data directories, and prefer batch APIs when many epochs share a configuration.
