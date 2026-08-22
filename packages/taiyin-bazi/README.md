# py-ephemeris-bazi (Taiyin BaZi)

BaZi bindings for [`py-ephemeris`](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
print(result.pillars, result.chart, result.qiyun)
print("Execution flags:", result_flags)
```

`EphemerisContext.bazi()` loads this installed extension on demand. The BaZi
context inherits the calculation context's configured data roots and source paths. Its
`chinese_calendar` property is shared by four-pillar, Qi-Yun, and
Renyuan-Siling calculations, so the calendar offset is configured once.

For concurrent chart work, create one `EphemerisContext` and its corresponding
BaZi facade per worker. Native chart, Qi-Yun, DaYun, and Renyuan-Siling work
releases the Python GIL; a single context/facade pair is not reentrant and must
not be used or reconfigured concurrently by multiple threads.

For a source build from this monorepo, run the following from
`packages/taiyin-bazi`. CMake prefers the sibling Taiyin C++ checkout. In an
isolated sdist build it instead downloads the public `v1.0.0-beta.2` source
archive and verifies its pinned SHA-256 before compiling it into the extension.
`TAIYIN_SOURCE_DIR` below is used by the integration tests to locate the C++
checkout's bundled test data; it can also be passed as a CMake define to build
against another local checkout.

```bash
python -m pip install -e ".[test]"
TAIYIN_SOURCE_DIR=../../../taiyin-ephemeris python -m pytest
```
