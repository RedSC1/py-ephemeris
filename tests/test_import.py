import taiyin


def test_native_module_imports() -> None:
    assert taiyin.__version__ == "0.1.0a0"
    assert taiyin.binding_backend() == "pybind11"

