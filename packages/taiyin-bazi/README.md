# py-ephemeris-bazi (Taiyin BaZi)

BaZi bindings for [`py-ephemeris`](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
bazi = eph.create_bazi()
```

Importing `taiyin_bazi` registers `Ephemeris.create_bazi()`. The BaZi context
inherits the base runtime's configured data roots and source paths.

For a source build from this monorepo, run the following from
`packages/taiyin-bazi`. The default CMake path already resolves the sibling
Taiyin C++ checkout; the environment variable is only used by the integration
tests to locate its bundled test data.

```bash
python -m pip install -e ".[test]"
TAIYIN_SOURCE_DIR=../../../taiyin-ephemeris python -m pytest
```
