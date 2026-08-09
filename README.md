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
```

The package is being rebuilt as a direct pybind11 binding over the Taiyin C++
API. Python users will import native extension modules normally; they will not
locate or load Taiyin DLLs manually.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[test]"
python -m pytest
```

