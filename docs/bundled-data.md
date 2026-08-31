# Bundled runtime data

The `py-ephemeris` wheel installs its default runtime data under
`taiyin/data/`. A normal `taiyin.Ephemeris()` passes that directory to the
native runtime, which reads the prebuilt `index.opc` catalog instead of
rescanning its files on first use.

## Contents

| Product | Default behavior | Scope |
| --- | --- | --- |
| DE442 major-body OPM2 | Default AUTO route | Sun, Moon, planetary barycenters and Earth-Moon barycenter; approximately 1550–2650 |
| Selected asteroid OPM2 | Direct high-precision route | Ceres, Pallas, Juno, Vesta, Eros, Chiron, Pholus, Nessus, and Lilith (1181) over their declared 600-year coverage |
| Saturn and Uranus COB OPM2 | Physical-planet correction | Used where those satellite-system corrections cover the request; their satellite theories are not bundled yet |
| SBDB TKC1 Kepler tiers | Approximate fallback | Core objects, first 1,000 numbered asteroids, and potentially hazardous asteroids; use SPK/OPM data for precision work |
| Lite TSC1 fixed-star catalog | Loaded by default | 2,057 stars and 12,242 aliases; complete HIP membership of Stellarium's Chinese and western-zodiac line figures |

The OPM2 and TKC1 files are ordinary packaged data, not code. Their manifests
retain source and coverage metadata. The package does not include large SPK
kernels, the full fixed-star catalogs, precision satellite SPKs, EOP tables,
or lunar-limb topography; provide those as an additional `source_paths` entry
or select another `data_root` when needed.

The Python wheel does not currently bundle DE441. A separate optional
approximately 30,000-year DE441 package may be published later, but has not
been released yet. The C++ source repository also contains DE441-derived test
data for comparison and reproducibility. Users can supply NASA/JPL's original
BSP/SPK files themselves, including DE441, planetary-satellite, and small-body
kernels.

## Star catalog loading

Fixed-star catalog registration is process-wide in the native runtime. The
Python `Ephemeris()` facade loads the bundled lite catalog once when packaged
data are enabled; repeated `Ephemeris()` instances do not duplicate it. A
manual `clear()` resets that state, so it can be loaded again by the next
`Ephemeris()` instance:

```python
from pathlib import Path
import taiyin

eph = taiyin.Ephemeris()
eph.star_catalog.clear()  # optional: reset the process-wide catalog
star_file = Path(taiyin.__file__).resolve().parent / "data" / "stars" / "catalogs" / "lite" / "stars-bright-v5.tsc1"
eph.star_catalog.add_tsc1(str(star_file))
```

The lite profile guarantees aliases such as `antares`, `角宿一`, `织女一`, and
`jiao_xiu_1`. It includes the complete line-star membership of the pinned
Stellarium Chinese sky culture, but it is not a complete historical overlay:
different historical Chinese sky maps can use different members or names for
a given asterism.

## Selecting other data

An explicit `data_root` replaces the default package root. Additional paths
can be appended without replacing it:

```python
eph = taiyin.Ephemeris(source_paths=["/path/to/de442.bsp"])
# or
eph = taiyin.Ephemeris(data_root="/path/to/another/taiyin-data")
```

Provider-local source priorities can be changed with
`Ephemeris.set_ephemeris_source_priority()` when a reproducible input product
must win over the normal AUTO selection.

## Data roots, extra paths, and OPC files

`data_root` selects one primary data directory. If it is omitted, the Python
package's own `taiyin/data` directory is used. An existing valid catalog is
read from:

```text
<data_root>/index.opc
```

When a directory has no usable `index.opc`, the native runtime scans that
directory and may write a newly generated `index.opc` there when the directory
is writable. The packaged wheel already includes its pre-generated
`taiyin/data/index.opc`.

Additional sources can be supplied through `source_paths`. This accepts any
number of files and directories and can be mixed with `data_root`:

```python
eph = taiyin.Ephemeris(
    data_root="/data/main",
    source_paths=[
        "/data/satellites",
        "/data/asteroids",
        "/data/custom/de442.bsp",
        "/data/custom/extra.opm2",
    ],
)
```

Each additional directory is discovered independently and may have its own
`<directory>/index.opc`. A single file is loaded directly and does not receive
an OPC file. Use `source_paths` for several external directories; do not try to
pass several directories as `data_root`.
