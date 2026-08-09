# py-ephemeris

Python bindings for Taiyin Ephemeris.

- GitHub repository: `py-ephemeris`
- PyPI distribution: `py-ephemeris`
- Python import package: `taiyin`

```bash
python -m pip install py-ephemeris
```

```python
import taiyin

assert taiyin.binding_backend() == "pybind11"

eph = taiyin.Ephemeris()
context = eph.create_context()
```

The package is being rebuilt as a direct pybind11 binding over the Taiyin C++
API. Python users will import native extension modules normally; they will not
locate or load Taiyin DLLs manually.

The first implementation slice is the callback bridge: custom calculation
targets, ayanamsha models and house systems use Python callables directly from
the C++ registries. See [the migration inventory](docs/migration-inventory.md)
for the measured legacy surface and port order, and the
[binding manifest](docs/binding-manifest.md) for the concrete function list.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[test]" \
  --config-settings=cmake.define.TAIYIN_SOURCE_DIR=../taiyin-ephemeris
TAIYIN_SOURCE_DIR=../taiyin-ephemeris python -m pytest
```

For normal use, point `data_root` at the complete Taiyin `data` directory. The
native runtime uses a valid `index.opc` automatically and falls back to
discovering OPM2, SPK, TKE1, and TKC1 sources below that directory when the
index is missing or stale:

```python
import taiyin

eph = taiyin.Ephemeris(data_root="/path/to/taiyin/data")
context = eph.create_context()
```

Optional or user-provided solar-system shards can additionally be supplied as
files or directories through `source_paths=[...]`. Numerical integration tests
may deliberately select the `600y` OPM2 fixture to keep their expected values
independent of the set and priority of installed optional shards; a separate
integration test exercises complete-`data` discovery.

## Chinese lunar month strings

Traditional month names are normalized in Python and then validated by the
configured native calendar during conversion:

```python
lunar = taiyin.LunarDate.from_string(2003, "九月", 1)
solar = context.chinese_calendar.from_lunar(lunar)

leap_month = taiyin.LunarDate.from_string(2023, "闰二月", 15)
historical = taiyin.LunarDate.from_string(-209, "后九月", 15)
```

The parser accepts `正`/`正月`, `一` through `十二`, `冬`, `腊`, `闰五`,
`后九`, `拾贰`, and `十三`; a trailing `月` is optional. The Python parser
only creates a structured `LunarDate`. Month existence and the actual 29/30-day
limit remain native Chinese-calendar responsibilities. Invalid names, absent
leap months, and days outside the selected month's length raise `ValueError`;
ephemeris coverage and runtime failures remain runtime errors.
