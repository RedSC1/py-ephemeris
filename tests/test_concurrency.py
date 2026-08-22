"""Threading behavior for the direct native binding."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier, Event, Thread

import pytest
import taiyin


@pytest.fixture()
def runtime():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run native concurrency integration tests")
    data_path = (
        Path(source_root) / "data" / "ephemerides" / "opm2" /
        "major-bodies" / "600y"
    )
    if not data_path.is_dir():
        pytest.skip("600-year OPM2 test data is unavailable")
    return taiyin.Ephemeris(
        source_paths=[str(data_path)],
        load_packaged_data=False,
        load_builtin_eop=False,
    )


def test_same_context_positions_are_reentrant(runtime):
    """Read-only position calls may share one configured context."""
    context = runtime.create_context()
    epochs = tuple(
        taiyin.JulianDate.from_double(2460310.5 + index * 0.125)
        for index in range(32)
    )
    bodies = (taiyin.Body.mercury, taiyin.Body.venus, taiyin.Body.moon, taiyin.Body.sun)
    requests = tuple((bodies[index % len(bodies)], epochs[index]) for index in range(len(epochs)))

    references = [
        (
            context.position.at_ut1(body, epoch, (taiyin.PositionFlag.speed,)),
            context.position.state_at_ut1(body, epoch),
        )
        for body, epoch in requests
    ]

    def calculate(indexed_request):
        index, (body, epoch) = indexed_request
        value, flags = context.position.at_ut1(
            body, epoch, (taiyin.PositionFlag.speed,)
        )
        state, state_flags = context.position.state_at_ut1(body, epoch)
        direct = context._native_context.position_at_ut1(
            body.id, epoch, taiyin.PositionFlag.speed.mask
        )
        return index, value, flags, state, state_flags, direct

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(calculate, enumerate(requests)))

    for index, value, flags, state, state_flags, direct in results:
        (expected_value, expected_flags), (expected_state, expected_state_flags) = (
            references[index]
        )
        body, _ = requests[index]
        assert value == expected_value
        assert flags == expected_flags
        assert state == expected_state
        assert state_flags == expected_state_flags
        assert direct["diagnostic"]["status"] == 0
        assert direct["diagnostic"]["target_id"] == body.id
        assert direct["result_flags"] == int(flags)

    completed_direct_snapshots = {
        (requests[index][0].id, direct["result_flags"])
        for index, _, _, _, _, direct in results
    }
    final_operation = context.last_operation
    final_status = context.last_status
    final_flags = context.last_result_flags
    final_diagnostic = context.last_diagnostic
    assert final_operation == "EphemerisContext.position_at_ut1"
    assert final_status == 0
    assert final_diagnostic is not None
    assert final_diagnostic.status == 0
    assert (final_diagnostic.target_id, int(final_flags)) in completed_direct_snapshots


def test_same_context_event_result_flags_are_call_scoped(runtime):
    """Concurrent searches return their own flags instead of sharing a tracker."""
    context = runtime.create_context()
    start = taiyin.JulianDate.from_double(2460300.5)
    end = taiyin.JulianDate.from_double(2460330.5)
    ready = Barrier(2)

    def custom_moon(request):
        return request.position_of(taiyin.Body.moon.id)

    def search_custom():
        ready.wait(timeout=5.0)
        return context.events.minimum_angular_separation_at_ut1(
            -201, taiyin.Body.sun.id, start, end, max_step_days=0.02
        )

    def search_native():
        ready.wait(timeout=5.0)
        return context.events.minimum_angular_separation_at_ut1(
            taiyin.Body.moon.id,
            taiyin.Body.sun.id,
            start,
            end,
            max_step_days=0.02,
        )

    registration = runtime.register_custom_target(
        -201, position_evaluator=custom_moon
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            custom_future = pool.submit(search_custom)
            native_future = pool.submit(search_native)
            custom_result, custom_flags = custom_future.result(timeout=30.0)
            native_result, native_flags = native_future.result(timeout=30.0)
    finally:
        registration.close()

    assert custom_result.bodyAId == -201
    assert native_result.bodyAId == taiyin.Body.moon.id
    assert custom_flags & taiyin.ResultFlag.numericalDerivative
    assert not (native_flags & taiyin.ResultFlag.numericalDerivative)


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


def test_heavy_read_only_modules_share_a_context(runtime):
    """Independent read-only services may execute on one configured context."""
    context = runtime.create_context()
    orbit_start = taiyin.JulianDate.from_double(2460409.0)
    eclipse_estimate = taiyin.JulianDate.from_double(2460926.25)
    sidereal_epoch = taiyin.JulianDate.from_double(2460311.0)

    def orbit_value():
        event, _ = context.orbits.search_apsis_from_ut1(
            taiyin.Body.moon, taiyin.ApsisKind.pericenter, orbit_start
        )
        return event.coordinate.to_double()

    def eclipse_value():
        eclipse, _ = context.eclipses.solve_lunar_at_ut1(
            eclipse_estimate,
            options=(taiyin.LunarEclipseSolveOption.includeContacts,),
        )
        return eclipse.maximum.to_double()

    def calendar_value():
        date, _ = context.chinese_calendar.from_solar(
            taiyin.SolarDate(year=2024, month=2, day=10)
        )
        return date.year, date.month, date.day, date.isLeap

    def astrology_value():
        position, _ = context.astrology.sidereal_position_at_tt(
            taiyin.Body.sun,
            sidereal_epoch,
            ayanamsha=taiyin.Ayanamsha.lahiri,
        )
        return position.siderealLongitudeRadians

    operations = (orbit_value, eclipse_value, calendar_value, astrology_value)
    expected = tuple(operation() for operation in operations)
    requests = tuple(operations[index % len(operations)] for index in range(32))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda operation: operation(), requests))

    for index, result in enumerate(results):
        assert result == expected[index % len(expected)]
