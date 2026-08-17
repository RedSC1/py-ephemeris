"""Threading behavior for the direct native binding."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier
from time import perf_counter

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


def test_independent_contexts_release_the_gil_for_event_searches(runtime):
    """A long native event search overlaps on independent contexts.

    Unlike a scalar position call, this search remains in one C++ invocation
    long enough to distinguish a released GIL from two workers serializing on
    it. The generous ratio allows normal shared read-only catalog/cache cost.
    """
    if (os.cpu_count() or 1) < 2:
        pytest.skip("requires two logical CPUs to verify native overlap")
    start = taiyin.JulianDate.from_double(2460300.5)
    end = taiyin.JulianDate.from_double(2460330.5)
    barrier = Barrier(2)

    def calculate(context):
        barrier.wait()
        return calculate_without_barrier(context)

    def calculate_without_barrier(context):
        return context.events.minimum_angular_separation_at_ut1(
            taiyin.Body.moon, taiyin.Body.sun, start, end,
            max_step_days=0.002)

    first = runtime.create_context()
    second = runtime.create_context()

    # Warm both independent contexts, then establish the serialized cost using
    # the same work. This fails on the pre-fix binding, whose event search holds
    # the GIL for the entire native call.
    calculate_without_barrier(first)
    calculate_without_barrier(second)
    serial_start = perf_counter()
    expected_first = calculate_without_barrier(first)
    expected_second = calculate_without_barrier(second)
    serial_elapsed = perf_counter() - serial_start

    parallel_start = perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        parallel_first, parallel_second = executor.map(calculate, (first, second))
    parallel_elapsed = perf_counter() - parallel_start

    for actual, expected in ((parallel_first, expected_first),
                             (parallel_second, expected_second)):
        assert actual.bodyAId == expected.bodyAId
        assert actual.bodyBId == expected.bodyBId
        assert actual.coordinate.to_double() == pytest.approx(
            expected.coordinate.to_double())
        assert actual.separationRadians == pytest.approx(expected.separationRadians)
        assert actual.separationRateRadiansPerDay == pytest.approx(
            expected.separationRateRadiansPerDay)
    assert parallel_elapsed < serial_elapsed * 1.6
