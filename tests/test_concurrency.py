"""Threading behavior for the direct native binding."""

import os
from pathlib import Path
from threading import Event, Thread

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


def test_event_search_releases_the_gil(runtime):
    """A long native event search lets another Python thread run.

    A custom target marks the point at which the native search is already in
    progress. It executes under the GIL. Once that callback returns, a binding
    that retained the GIL cannot schedule the observer until the complete
    search returns, whereas a binding that releases it lets the observer run
    during the remaining native search.
    """
    start = taiyin.JulianDate.from_double(2460300.5)
    end = taiyin.JulianDate.from_double(2460330.5)
    observer_ready = Event()
    observer_stop = Event()
    native_search_started = Event()
    iterations = [0]

    def custom_moon(request):
        native_search_started.set()
        return request.position_of(taiyin.Body.moon.id)

    def observe():
        observer_ready.set()
        assert native_search_started.wait(timeout=5.0)
        while not observer_stop.is_set():
            iterations[0] += 1

    registration = runtime.register_custom_target(
        -200, position_evaluator=custom_moon)
    observer = Thread(target=observe)
    observer.start()
    assert observer_ready.wait(timeout=1.0)
    try:
        result, result_flags = runtime.create_context().events.minimum_angular_separation_at_ut1(
            -200, taiyin.Body.sun.id, start, end, max_step_days=0.02)
    finally:
        observer_stop.set()
        observer.join(timeout=1.0)
        registration.close()

    assert result_flags & taiyin.ResultFlag.numericalDerivative
    assert result.bodyAId == -200
    assert result.bodyBId == taiyin.Body.sun.id
    assert native_search_started.is_set()
    assert iterations[0] > 1000
