import taiyin
import os
from pathlib import Path
import pytest


def test_native_module_imports() -> None:
    assert taiyin.__version__ == "0.1.0a0"
    assert taiyin.binding_backend() == "pybind11"


def test_public_runtime_facade_creates_context() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    assert isinstance(context, taiyin.EphemerisContext)
    assert taiyin.JulianDate.from_double(2451545.25).to_double() == 2451545.25
    assert (
        context.time.tdb_to_tt(
            context.time.tt_to_tdb(taiyin.JulianDate(2451545, 0.0))
        ).to_double()
        == 2451545.0
    )


def test_time_api_matches_cpp_julian_date_oracles() -> None:
    context = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False).create_context()
    date = taiyin.AstroDateTime(2024, 4, 8, 18, 17, 20.0)
    jd = context.time.julian_day(date)
    assert jd.to_double() == 2460409.262037037
    assert context.time.reverse_julian_day(jd).year == 2024
    assert abs(context.time.decimal_year(jd) - 2024.2698416312485) < 1e-12
    assert context.time.julian_centuries_since_j2000(taiyin.JulianDate(2488070, 0.0)) == 1.0
    assert abs(
        context.time.utc_to_tt(taiyin.JulianDate(2451545, 0.25), 37.0).seconds_difference(
            taiyin.JulianDate(2451545, 0.25)
        )
        - 69.184
    ) < 1e-10
    assert context.time.tai_minus_utc(date) == 37.0
    assert abs(context.time.delta_t(37.0, -0.1) - 69.284) < 1e-12
    precise = context.time.precise_scales_from_utc(date, 37.0, -0.1)
    assert abs(precise.tt.seconds_difference(precise.utc) - 69.184) < 1e-10
    estimated = context.time.estimated_scales_from_ut1(date, delta_t_seconds=69.17035296181177)
    assert abs(estimated.tt.seconds_difference(estimated.ut1) - 69.17035296181177) < 1e-10


def test_native_position_matches_cartesian_state_oracle() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        import pytest

        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")
    source_path = (
        Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    )
    context = taiyin.Ephemeris(
        source_paths=[str(source_path)], load_packaged_data=False
    ).create_context()
    ut1 = taiyin.JulianDate(2460310, 0.5)
    flags = (taiyin.PositionFlag.speed, taiyin.PositionFlag.xyz)
    position = context.position.at_ut1(taiyin.Body.mercury, ut1, flags)
    state = context.position.state_at_ut1(taiyin.Body.mercury, ut1)
    assert position.diagnostic.status == 0
    assert position.value.rates is not None
    assert tuple(position.value.coordinates) == tuple(state.value.position_au)
    assert tuple(position.value.rates) == tuple(state.value.velocity_au_per_day)


def test_data_root_discovers_the_complete_packaged_catalog() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")

    data_root = Path(source_root) / "data"
    if not data_root.is_dir():
        pytest.skip("Taiyin source-tree data directory is unavailable")

    eph = taiyin.Ephemeris(data_root=str(data_root))

    # Passing the package data root must discover the solar-system sources as
    # one catalog.  The native runtime will use data/index.opc when it is valid
    # and otherwise scan OPM2/SPK/TKE1/TKC1 sources below the directory.
    assert eph.catalog_size > 0

    context = eph.create_context()
    result = context.position.state_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate(2460310, 0.5)
    )
    assert result.diagnostic.status == 0
    assert all(value == value for value in result.value.position_au)


def test_ganzhi_api_uses_native_calendar_rules() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jia_zi = context.ganzhi.make(0, 0)
    assert jia_zi == taiyin.Ganzhi(0, 0)
    assert context.ganzhi.advance(jia_zi, 1) == taiyin.Ganzhi(1, 1)
    assert context.ganzhi.month_pillar(0, 0) == taiyin.Ganzhi(2, 2)
    assert context.ganzhi.hour_pillar(0, 0) == taiyin.Ganzhi(0, 0)
    assert context.ganzhi.nayin_id(jia_zi) == 0
    assert context.ganzhi.nayin_element(jia_zi) is taiyin.GanzhiWuxing.metal


def test_chinese_calendar_context_has_legacy_parent_shape() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    calendar = context.chinese_calendar
    assert calendar is context.chinese_calendar
    assert calendar.config == taiyin.ChineseCalendarConfig.astronomical()
    assert context.create_chinese_calendar(
        taiyin.ChineseCalendarConfig.utc_offset(540)
    ).config.utcOffsetMinutes == 540


def test_context_configuration_sets_observer_location() -> None:
    context = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False).create_context()
    context.configuration.set_observer_location(taiyin.ObserverLocation(116.4074, 39.9042, 43.5))
    with pytest.raises(ValueError):
        context.configuration.set_observer_location(taiyin.ObserverLocation(0.0, 91.0))


def test_four_pillars_with_explicit_ephemeris_source_path() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        import pytest

        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")
    source_path = (
        Path(source_root)
        / "data"
        / "ephemerides"
        / "opm2"
        / "major-bodies"
        / "600y"
    )
    if not source_path.is_dir():
        import pytest

        pytest.skip("Taiyin source-tree ephemeris fixture is unavailable")
    eph = taiyin.Ephemeris(
        source_paths=[str(source_path)],
        load_packaged_data=False,
    )
    context = eph.create_context()
    local_time = taiyin.AstroDateTime(1990, 5, 15, 14, 30)
    pillars = context.chinese_calendar.four_pillars(
        local_time.to_julian_date().add_seconds(-8 * 3600), local_time
    )
    assert pillars == taiyin.GanzhiFourPillars(
        taiyin.Ganzhi.from_native(0x66),
        taiyin.Ganzhi.from_native(0x75),
        taiyin.Ganzhi.from_native(0x64),
        taiyin.Ganzhi.from_native(0x97),
    )
    lunar = context.chinese_calendar.from_solar(taiyin.SolarDate(2025, 1, 29))
    assert lunar == taiyin.LunarDate(2025, 1, 1, False, 30)
    assert context.chinese_calendar.from_lunar(lunar) == taiyin.SolarDate(2025, 1, 29)
    assert context.chinese_calendar.get_month_days(2026, 1, False) == 30
    march_probe = taiyin.AstroDateTime(2025, 3, 1, 12).to_julian_date().add_seconds(
        -8 * 3600
    )
    calendar = context.chinese_calendar
    assert calendar.get_prev_jie_qi_ut(march_probe).indexFromWinterSolstice == 4
    assert calendar.get_next_jie_qi_ut(march_probe).indexFromWinterSolstice == 5
    assert calendar.get_prev_jie_ut(march_probe).indexFromWinterSolstice == 3
    assert calendar.get_next_qi_ut(march_probe).indexFromWinterSolstice == 6
    year = calendar.calc_year_ut(taiyin.AstroDateTime(2034, 1, 15, 12).to_julian_date())
    assert year.leapMonthIndex == 1
    assert (year.months[0].month, year.months[0].isLeap) == (11, False)
    assert (year.months[1].month, year.months[1].isLeap) == (11, True)


def test_custom_target_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.0)
    registration = eph.register_custom_target(
        -100,
        position_evaluator=lambda request: [
            request.target_id,
            request.jd_tdb.to_double(),
            request.jd_tt.to_double(),
            request.flags,
            5.0,
            6.0,
        ],
    )
    result = context.position.at_tdb(-100, jd, jd, flags=(taiyin.PositionFlag.speed,))
    assert result.value.coordinates == (-100.0, 2451545.0, 2451545.0)
    assert result.value.rates == (1.0, 5.0, 6.0)
    assert result.diagnostic.status == 0
    batch = context.position.batch_at_tt(
        [-100, -100], jd, flags=(taiyin.PositionFlag.speed,)
    )
    assert [row.value.coordinates[0] for row in batch] == [-100.0, -100.0]
    assert all(0.0 < jd.to_double() - row.value.coordinates[1] < 1e-7 for row in batch)
    assert [row.value.coordinates[2:] + row.value.rates for row in batch] == [
        (2451545.0, 1.0, 5.0, 6.0)
    ] * 2
    registration.close()


def test_custom_target_state_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.0)
    registration = eph.register_custom_target(
        -101,
        position_evaluator=lambda request: [0.0] * 6,
        state_evaluator=lambda request: {
            "position_au": [request.target_id, 2.0, 3.0],
            "velocity_au_per_day": [4.0, 5.0, 6.0],
            "acceleration_au_per_day2": [7.0, 8.0, 9.0],
        },
    )
    result = context.position.state_at_tdb(-101, jd, jd)
    assert tuple(result.value.position_au) == (-101.0, 2.0, 3.0)
    assert tuple(result.value.velocity_au_per_day) == (4.0, 5.0, 6.0)
    assert tuple(result.value.acceleration_au_per_day2) == (7.0, 8.0, 9.0)
    assert result.diagnostic.status == 0
    registration.close()


def test_custom_ayanamsha_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.25)
    registration = eph.register_custom_ayanamsha_model(
        10000,
        lambda request: request.julian_date_tt.day_fraction,
    )
    assert (
        taiyin._native.ayanamsha_at_tt(
            context._native_context, 10000, jd, taiyin._native.POSITION_NONUT
        )
        == 0.25
    )
    registration.close()


def test_custom_house_system_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    registration = eph.register_custom_house_system_model(
        10000,
        lambda request: [request.armc_radians + number for number in range(12)],
    )
    assert taiyin._native.houses_from_armc(0.1, 0.5, 0.4, 10000) == [
        0.1 + number for number in range(12)
    ]
    registration.close()
