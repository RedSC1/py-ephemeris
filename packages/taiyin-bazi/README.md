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
`packages/taiyin-bazi`. CMake prefers the sibling Taiyin C++ checkout. In an
isolated sdist build it instead downloads the public `v1.0.0-preview.1` source
archive and verifies its pinned SHA-256 before compiling it into the extension.
`TAIYIN_SOURCE_DIR` below is used by the integration tests to locate the C++
checkout's bundled test data; it can also be passed as a CMake define to build
against another local checkout.

```bash
python -m pip install -e ".[test]"
TAIYIN_SOURCE_DIR=../../../taiyin-ephemeris python -m pytest
```
