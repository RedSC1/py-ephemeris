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

    This checks GIL release directly instead of comparing native throughput:
    two searches can contend for CPU or runtime caches even when both run
    concurrently.  Before the search starts, the observer is ready to count
    Python iterations.  A binding that holds the GIL throughout the search
    prevents that observer from running; a released-GIL native search does not.
    """
    start = taiyin.JulianDate.from_double(2460300.5)
    end = taiyin.JulianDate.from_double(2460330.5)
    observer_ready = Event()
    observer_stop = Event()
    iterations = [0]

    def observe():
        observer_ready.set()
        while not observer_stop.is_set():
            iterations[0] += 1

    observer = Thread(target=observe)
    observer.start()
    assert observer_ready.wait(timeout=1.0)
    try:
        result = runtime.create_context().events.minimum_angular_separation_at_ut1(
            taiyin.Body.moon, taiyin.Body.sun, start, end,
            max_step_days=0.002)
    finally:
        observer_stop.set()
        observer.join(timeout=1.0)

    assert result.bodyAId == taiyin.Body.moon.id
    assert result.bodyBId == taiyin.Body.sun.id
    assert iterations[0] > 1000
