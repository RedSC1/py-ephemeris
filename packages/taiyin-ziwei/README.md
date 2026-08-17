# py-ephemeris-ziwei (Taiyin Ziwei Doushu)

Optional Ziwei Doushu bindings for
[py-ephemeris](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
```

The extension shares a caller-owned `taiyin.EphemerisContext` and its Chinese
calendar configuration.  Its bundled TOML rule catalog is parsed once per
`ZiweiDataCatalog`; contexts select immutable option views without reparsing.

The first release is still under active API stabilization and is not yet
published.  Source builds in this monorepo use the adjacent C++ checkout.
