import pytest

import taiyin


def assert_close_instant(left, right, tolerance_seconds: float = 5e-7) -> None:
    assert abs(left.seconds_difference(right)) < tolerance_seconds


def test_round_trips_all_physical_scales_to_utc_and_ut1() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    utc = taiyin.JulianDate.from_timestamp(946684800.0)
    scales, scale_flags = context.time.scales_from_utc(utc)

    assert scale_flags == taiyin.ResultFlag.none
    for converted, flags in (
        context.time.tai_to_utc(scales.tai),
        context.time.tt_to_utc(scales.tt),
        context.time.ut1_to_utc(scales.ut1),
        context.time.tdb_to_utc(scales.tdb),
    ):
        assert_close_instant(converted, scales.utc)
        assert flags == taiyin.ResultFlag.none

    for converted, flags in (
        context.time.utc_to_ut1(scales.utc),
        context.time.tai_to_ut1(scales.tai),
        context.time.tt_to_ut1(scales.tt),
        context.time.tdb_to_ut1(scales.tdb),
    ):
        assert_close_instant(converted, scales.ut1)
        assert flags == taiyin.ResultFlag.none

    ut1_clock, ut1_clock_flags = context.time.calendar_from_ut1(scales.ut1)
    utc_clock, utc_clock_flags = context.time.utc_calendar_from_ut1(scales.ut1)
    assert ut1_clock_flags | utc_clock_flags == taiyin.ResultFlag.none
    assert ut1_clock.year == 2000
    utc_round_trip = utc_clock.to_julian_date()
    assert_close_instant(utc_round_trip, scales.utc)


def test_rejects_inserted_leap_second_as_uniform_utc_julian_date() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    scales, _ = context.time.scales_from_utc(
        taiyin.AstroDateTime(2016, 12, 31, 23, 59, 60)
    )

    with pytest.raises(taiyin.UtcLeapSecondRepresentationError):
        context.time.tai_to_utc(scales.tai)
    with pytest.raises(taiyin.UtcLeapSecondRepresentationError):
        context.time.tt_to_utc(scales.tt)
    with pytest.raises(taiyin.UtcLeapSecondRepresentationError):
        context.time.tdb_to_utc(scales.tdb)
    post_leap_utc, post_leap_flags = context.time.ut1_to_utc(scales.ut1)
    post_leap = taiyin.AstroDateTime(2017, 1, 1).to_julian_date()
    assert_close_instant(post_leap_utc, post_leap)
    assert post_leap_flags == taiyin.ResultFlag.none

    for converted, flags in (
        context.time.tai_to_ut1(scales.tai),
        context.time.tt_to_ut1(scales.tt),
        context.time.tdb_to_ut1(scales.tdb),
    ):
        assert_close_instant(converted, scales.ut1)
        assert flags == taiyin.ResultFlag.none


def test_automatic_tdb_reverse_uses_the_context_model() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    context.time.set_tdb_model(taiyin.TdbModel.sofaFull)
    utc = taiyin.JulianDate.from_timestamp(946684800.0)
    scales, _ = context.time.scales_from_utc(utc)

    converted_utc, _ = context.time.tdb_to_utc(scales.tdb)
    converted_ut1, _ = context.time.tdb_to_ut1(scales.tdb)
    assert_close_instant(converted_utc, scales.utc)
    assert_close_instant(converted_ut1, scales.ut1)

    cloned = ephemeris.clone_context(context)
    cloned_scales, _ = cloned.time.scales_from_utc(utc)
    cloned_utc, _ = cloned.time.tdb_to_utc(cloned_scales.tdb)
    assert_close_instant(cloned_utc, cloned_scales.utc)


def test_configuration_api_keeps_tdb_model_in_sync() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    utc = taiyin.JulianDate.from_timestamp(946684800.0)

    context.configuration.set_astro_models(
        taiyin.AstroModelConfig(tdb_model_id=taiyin.TdbModel.sofaFull.value)
    )
    assert context.time.configured_tdb_model is taiyin.TdbModel.sofaFull
    sofa_scales, _ = context.time.scales_from_utc(utc)
    sofa_round_trip, _ = context.time.tdb_to_utc(sofa_scales.tdb)
    assert_close_instant(sofa_round_trip, sofa_scales.utc)
    explicit_scales, _ = context.time.precise_scales_from_utc(
        taiyin.AstroDateTime(2000, 1, 1), 32.0, 0.25
    )
    estimated_scales, _ = context.time.estimated_scales_from_ut1(
        taiyin.AstroDateTime(2000, 1, 1),
        delta_t_seconds=explicit_scales.delta_t_seconds,
    )
    expected_precise_tdb, _ = context.time.tt_to_tdb(
        explicit_scales.tt, taiyin.TdbModel.sofaFull
    )
    expected_estimated_tdb, _ = context.time.tt_to_tdb(
        estimated_scales.tt, taiyin.TdbModel.sofaFull
    )
    assert_close_instant(explicit_scales.tdb, expected_precise_tdb, 1e-10)
    assert_close_instant(estimated_scales.tdb, expected_estimated_tdb, 1e-10)
    clone = ephemeris.clone_context(context)
    assert clone.time.configured_tdb_model is taiyin.TdbModel.sofaFull

    context.configuration.reset()
    assert context.time.configured_tdb_model is taiyin.TdbModel.fastPeriodic
    fast_scales, _ = context.time.scales_from_utc(utc)
    fast_round_trip, _ = context.time.tdb_to_utc(fast_scales.tdb)
    assert_close_instant(fast_round_trip, fast_scales.utc)


def test_inverse_seed_stays_inside_the_eop_coverage_edge() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    scales, _ = context.time.scales_from_utc(
        taiyin.AstroDateTime(2026, 5, 20, 0, 0, 0)
    )

    converted_from_tt, _ = context.time.tt_to_ut1(scales.tt)
    converted_from_ut1, _ = context.time.ut1_to_utc(scales.ut1)
    assert_close_instant(converted_from_tt, scales.ut1)
    assert_close_instant(converted_from_ut1, scales.utc)


def test_scales_from_utc_rejects_malformed_calendar_fields() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    malformed = taiyin.AstroDateTime(2024, 13, 1)

    with pytest.raises(taiyin.InvalidArgumentError) as error:
        context.time.scales_from_utc(malformed)
    assert error.value.status == taiyin.StatusCode.invalidArgument


def test_strict_automatic_conversion_requires_eop_coverage() -> None:
    ephemeris = taiyin.Ephemeris(load_builtin_eop=False)
    context = ephemeris.create_context()
    utc = taiyin.JulianDate.from_timestamp(946684800.0)

    with pytest.raises(taiyin.TimeScaleError) as error:
        context.time.scales_from_utc(utc)
    assert error.value.status == taiyin.StatusCode.eopOutOfRange

    tai, _ = context.time.utc_to_tai(utc, 32.0)
    tt, _ = context.time.tai_to_tt(tai)
    tdb, _ = context.time.tt_to_tdb(tt)
    for converted, flags in (
        context.time.tai_to_utc(tai),
        context.time.tt_to_utc(tt),
        context.time.tdb_to_utc(tdb),
    ):
        assert_close_instant(converted, utc)
        assert flags == taiyin.ResultFlag.none


def test_strict_historical_reverse_conversion_requires_leap_seconds() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()
    historical_tt = taiyin.AstroDateTime(1900, 1, 1).to_julian_date()

    with pytest.raises(taiyin.TimeScaleError) as utc_error:
        context.time.tt_to_utc(historical_tt)
    with pytest.raises(taiyin.TimeScaleError) as ut1_error:
        context.time.tt_to_ut1(historical_tt)
    assert utc_error.value.status == taiyin.StatusCode.leapSecondUnavailable
    assert ut1_error.value.status == taiyin.StatusCode.leapSecondUnavailable


def test_allowed_estimate_propagates_fallback_flags_to_reverse_routes() -> None:
    ephemeris = taiyin.Ephemeris(load_builtin_eop=False)
    context = ephemeris.create_context()
    context.time.set_allow_utc_out_of_range_estimate(True)
    context.time.set_delta_t_model(
        taiyin.DeltaTModel.estimatedDefault,
        taiyin.EphemerisFamily.de441,
    )
    utc = taiyin.JulianDate.from_timestamp(946684800.0)

    scales, scale_flags = context.time.scales_from_utc(utc)
    assert scale_flags & taiyin.ResultFlag.timeScaleFallback

    converted_utc, utc_flags = context.time.ut1_to_utc(scales.ut1)
    converted_ut1, ut1_flags = context.time.tt_to_ut1(scales.tt)
    assert_close_instant(converted_utc, scales.utc)
    assert_close_instant(converted_ut1, scales.ut1)
    assert utc_flags & taiyin.ResultFlag.timeScaleFallback
    assert ut1_flags & taiyin.ResultFlag.timeScaleFallback


def test_historical_tdb_to_ut1_fallback_does_not_require_leap_seconds() -> None:
    ephemeris = taiyin.Ephemeris(load_builtin_eop=False)
    context = ephemeris.create_context()
    context.time.set_allow_utc_out_of_range_estimate(True)
    historical_tt = taiyin.AstroDateTime(1900, 1, 1).to_julian_date()
    historical_tdb, _ = context.time.tt_to_tdb(historical_tt)

    ut1_from_tt, tt_flags = context.time.tt_to_ut1(historical_tt)
    ut1_from_tdb, tdb_flags = context.time.tdb_to_ut1(historical_tdb)
    assert_close_instant(ut1_from_tdb, ut1_from_tt)
    assert tt_flags & taiyin.ResultFlag.timeScaleFallback
    assert tdb_flags & taiyin.ResultFlag.timeScaleFallback


def test_historical_uniform_scales_round_trip_to_estimated_utc() -> None:
    ephemeris = taiyin.Ephemeris(load_builtin_eop=False)
    context = ephemeris.create_context()
    context.time.set_allow_utc_out_of_range_estimate(True)
    historical_utc = taiyin.AstroDateTime(1900, 1, 1)

    scales, scale_flags = context.time.scales_from_utc(historical_utc)
    historical_tai = taiyin.JulianDate(
        scales.tt.day_number, scales.tt.day_fraction
    ).add_seconds(-32.184)
    from_tai, tai_flags = context.time.tai_to_utc(historical_tai)
    from_tt, tt_flags = context.time.tt_to_utc(scales.tt)
    from_tdb, tdb_flags = context.time.tdb_to_utc(scales.tdb)

    assert_close_instant(from_tai, scales.utc)
    assert_close_instant(from_tt, scales.utc)
    assert_close_instant(from_tdb, scales.utc)
    for flags in (scale_flags, tai_flags, tt_flags, tdb_flags):
        assert flags & taiyin.ResultFlag.timeScaleFallback


def test_invalid_tdb_model_does_not_mutate_native_configuration() -> None:
    ephemeris = taiyin.Ephemeris()
    context = ephemeris.create_context()

    with pytest.raises(ValueError):
        context.configuration.set_astro_models(
            taiyin.AstroModelConfig(tdb_model_id=99)
        )

    assert context.time.configured_tdb_model is taiyin.TdbModel.fastPeriodic
    context.time.scales_from_utc(taiyin.AstroDateTime(2000, 1, 1))
