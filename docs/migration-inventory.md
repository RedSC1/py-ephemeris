# Python binding migration inventory

`taiyin-python` is a ctypes wrapper over the stable C ABI. `py-ephemeris`
will bind the public C++ API directly with pybind11, so a declaration-for-
declaration port is specifically not the goal.

## Measured legacy surface

| Area | Raw C ABI declarations |
| --- | ---: |
| `taiyin.core._bindings` | 329 |
| `taiyin_bazi.core._bindings` | 31 |
| Total | 360 |

Those 360 calls are a lower-level transport layer, not 360 user-facing Python
methods. They include allocation/destruction, C struct initializers, status
formatters, buffer-fill variants, and duplicated time-scale entry points.

The old high-level package contains 18 service modules plus the optional BaZi
package. The new API should retain Python-friendly value objects and combine
the repeated C transport helpers behind C++ overloads and pybind converters.

## Callback work: the hard boundary

There are four ctypes callback signatures, grouped into three native
registries:

| Registry | Python callback input | Required result | Scope |
| --- | --- | --- | --- |
| Custom calculation target: position | target ID, TDB/TT, flags; can recursively request another position | six finite coordinate/rate values | process-wide |
| Custom calculation target: state | target ID, TDB/TT, flags | finite position, velocity, acceleration vectors | process-wide |
| Custom ayanamsha | TT and native position flags | one finite angle in radians | process-wide |
| Custom house system | ARMC, latitude, obliquity, ascendant, midheaven | twelve finite cusp longitudes | process-wide |

The first native binding spike implements all three registrations directly
against C++ registry APIs. Each Python registration object owns a C++ bridge
that holds the Python callable, acquires the GIL in the non-throwing native
trampoline, converts exceptions to Taiyin errors, validates numeric output,
and unregisters before releasing the callable.

The native registries explicitly define registration/removal as setup-time
operations: callers must not close a registration while calculations can still
invoke it. That contract cannot be made safe merely by Python finalizers.

## Port order

1. Value types and direct context: split Julian dates, vectors/states, native
   context configuration, status-to-exception conversion.
2. Position/time services, plus the three callback registries in the first
   native module. This establishes the tricky GIL, ownership and re-entrancy
   policy before the broad API port.
3. Chinese calendar and Ganzhi in the base `taiyin` package.
4. Search/phenomena services (visibility, eclipse, occultation, events,
   heliacal and orbital).
5. Optional `taiyin_bazi` package. Its Python facade is created from the
   base ephemeris object; the native BaZi context remains configuration-only
   and does not own a base context.

The first three callback families are intentionally tested without ephemeris
data files: custom targets can calculate analytically, custom ayanamsha is a
direct dispatch, and houses-from-ARMC is pure geometry.
