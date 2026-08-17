"""Threading behavior for the direct native binding."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier

import pytest
import taiyin


@pytest.fixture()
def runtime():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run native concurrency integration tests")
    data_path = (
        Path(source_root) / "data" / "ephemerides" / "opm2" /
        "major-bodies" / "de442-full"
    )
    if not data_path.is_dir():
        pytest.skip("DE442 OPM2 test data is unavailable")
    return taiyin.Ephemeris(
        source_paths=[str(data_path)],
        load_packaged_data=False,
        load_builtin_eop=False,
    )


def test_independent_contexts_release_the_gil_for_native_calculations(runtime):
    """Independent contexts must make native work concurrently executable.

    The test checks both result correctness and that independent native
    contexts can be entered from two Python worker threads at the same time.
    It deliberately does not assert a wall-clock speedup: very short scalar
    calls can be dominated by Python/GIL transition overhead and shared
    read-only ephemeris-cache synchronization.
    """
    jd = taiyin.JulianDate.from_double(2460310.5)
    iterations = 2000
    barrier = Barrier(2)

    def calculate(context):
        barrier.wait()
        result = None
        for _ in range(iterations):
            result = context.position.at_ut1(taiyin.Body.sun, jd)
        return result

    first = runtime.create_context()
    second = runtime.create_context()

    with ThreadPoolExecutor(max_workers=2) as executor:
        parallel_first, parallel_second = executor.map(calculate, (first, second))

    expected = first.position.at_ut1(taiyin.Body.sun, jd)
    assert parallel_first == pytest.approx(expected)
    assert parallel_second == pytest.approx(expected)
