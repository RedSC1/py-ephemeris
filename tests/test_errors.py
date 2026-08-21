import pytest

import taiyin
import taiyin.errors as errors


STATUS_CASES = (
    (taiyin.StatusCode.invalidArgument, taiyin.StatusCategory.generic, taiyin.InvalidArgumentError),
    (taiyin.StatusCode.outOfMemory, taiyin.StatusCategory.generic, taiyin.OutOfMemoryError),
    (taiyin.StatusCode.internal, taiyin.StatusCategory.generic, taiyin.InternalCalculationError),
    (taiyin.StatusCode.unsupported, taiyin.StatusCategory.generic, taiyin.UnsupportedOperationError),
    (taiyin.StatusCode.ephemerisNoRoute, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.ephemerisCoverageGap, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.ephemerisLoadFailed, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.ephemerisEvaluationFailed, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.compositeMissingComponent, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.compositeCoverageGap, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.compositeMethodMismatch, taiyin.StatusCategory.ephemeris, taiyin.EphemerisRouteError),
    (taiyin.StatusCode.fileNotFound, taiyin.StatusCategory.file, taiyin.DataFileError),
    (taiyin.StatusCode.badFileFormat, taiyin.StatusCategory.file, taiyin.DataFileError),
    (taiyin.StatusCode.unsupportedFileFormat, taiyin.StatusCategory.file, taiyin.DataFileError),
    (taiyin.StatusCode.fileDiscoveryFailed, taiyin.StatusCategory.file, taiyin.DataFileError),
    (taiyin.StatusCode.eopOutOfRange, taiyin.StatusCategory.time, taiyin.TimeScaleError),
    (taiyin.StatusCode.leapSecondUnavailable, taiyin.StatusCategory.time, taiyin.TimeScaleError),
    (taiyin.StatusCode.eventNotFound, taiyin.StatusCategory.event, taiyin.EventSearchError),
    (taiyin.StatusCode.runtimeNotInitialized, taiyin.StatusCategory.runtime, taiyin.RuntimeServiceError),
    (taiyin.StatusCode.runtimeCacheInsertFailed, taiyin.StatusCategory.runtime, taiyin.RuntimeServiceError),
    (taiyin.StatusCode.runtimeRegistryFailed, taiyin.StatusCategory.runtime, taiyin.RuntimeServiceError),
)


@pytest.mark.parametrize("status, category, error_type", STATUS_CASES)
def test_every_native_status_maps_to_a_structured_exception(status, category, error_type):
    raise_for_status = getattr(errors, "_raise_for_status")
    with pytest.raises(error_type) as caught:
        raise_for_status("example.operation", status, status.name, "example detail", category)

    error = caught.value
    assert isinstance(error, taiyin.EphemerisError)
    assert isinstance(error, RuntimeError)
    assert error.operation == "example.operation"
    assert error.status is status
    assert error.status_code == int(status)
    assert error.status_name == status.name
    assert error.detail == "example detail"
    assert error.category is category
    assert "example.operation" in str(error)
    assert str(int(status)) in str(error)


def test_unknown_native_status_preserves_raw_values():
    raise_for_status = getattr(errors, "_raise_for_status")
    with pytest.raises(taiyin.UnknownNativeError) as caught:
        raise_for_status("future.operation", -7001, "FUTURE_STATUS", "future detail", 700)

    error = caught.value
    assert error.status == -7001
    assert error.status_code == -7001
    assert error.category == 700


def test_ok_status_does_not_raise():
    raise_for_status = getattr(errors, "_raise_for_status")
    assert raise_for_status(
        "example.operation", taiyin.StatusCode.ok, "OK", "ok", taiyin.StatusCategory.ok
    ) is None


def test_native_time_error_reaches_python_with_exact_status():
    context = taiyin.Ephemeris(load_builtin_eop=False).create_context()
    with pytest.raises(taiyin.TimeScaleError) as caught:
        context.position.at_utc(taiyin.Body.mars, taiyin.AstroDateTime(2024, 1, 1))

    error = caught.value
    assert error.status is taiyin.StatusCode.eopOutOfRange
    assert error.status_code == -3001
    assert error.category is taiyin.StatusCategory.time
    assert error.status_name == "TAIYIN_TIME_ERROR_EOP_OUT_OF_RANGE"
    assert "earth orientation data" in error.detail


def test_native_file_error_reaches_python_with_exact_status(tmp_path):
    ephemeris = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    missing = tmp_path / "missing-eop.txt"

    with pytest.raises(taiyin.DataFileError) as caught:
        ephemeris.load_eop_table(str(missing))

    error = caught.value
    assert error.status is taiyin.StatusCode.fileNotFound
    assert error.status_code == -2001
    assert error.category is taiyin.StatusCategory.file


def test_tracked_failure_snapshot_uses_the_exception_status():
    context = taiyin.Ephemeris().create_context()
    jd = taiyin.JulianDate.from_double(2460409.0)

    with pytest.raises(taiyin.DataFileError) as caught:
        context.stars.at_tt("definitely-not-a-star", jd)

    assert caught.value.status is taiyin.StatusCode.fileNotFound
    assert context.last_status == taiyin.StatusCode.fileNotFound
    assert context.last_operation == "Stars.star_at_tt"
    assert context.has_last_diagnostic
    assert context.last_diagnostic is not None
    assert context.last_diagnostic.status == taiyin.StatusCode.fileNotFound
