"""Offline regression checks for CI's native dependency selection."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("core_pin", ROOT / ".github/scripts/core_pin.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_tree(tmp_path: Path) -> Path:
    for relative in ("CMakeLists.txt", "packages/taiyin-bazi/CMakeLists.txt",
                     "packages/taiyin-ziwei/CMakeLists.txt"):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_current_pin():
    assert MODULE.read_core_pin(ROOT).startswith("v1.")


@pytest.mark.parametrize("replacement", ["v1.0.0-beta.8", "main", "${SOME_VARIABLE}"])
def test_reject_mismatched_or_unpinned_revision(tmp_path, replacement):
    root = fixture_tree(tmp_path)
    current = MODULE.read_core_pin(root)
    path = root / "packages/taiyin-ziwei/CMakeLists.txt"
    path.write_text(path.read_text().replace(current, replacement))
    with pytest.raises(ValueError):
        MODULE.read_core_pin(root)


def test_reject_checksum_mismatch(tmp_path):
    root = fixture_tree(tmp_path)
    path = root / "packages/taiyin-bazi/CMakeLists.txt"
    import re
    path.write_text(re.sub(r'"[0-9a-f]{64}"', '"' + '0' * 64 + '"', path.read_text()))
    with pytest.raises(ValueError, match="pins differ"):
        MODULE.read_core_pin(root)


def test_workflows_use_resolved_pin():
    for name in ("release-pypi.yml", "build-distributions.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text()
        assert "run: python .github/scripts/core_pin.py" in workflow
        assert "ref: ${{ steps.core-pin.outputs.revision }}" in workflow
        assert "ref: v1." not in workflow
