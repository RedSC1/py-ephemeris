import taiyin
import math
import os
from pathlib import Path
from threading import Event, Thread
import pytest


def test_native_module_imports() -> None:
    assert taiyin.__version__ == "1.0.0b5"
    assert taiyin.binding_backend() == "pybind11"
    assert taiyin.Body.phobos.id == 401
    assert taiyin.Body.io.id == 501
    assert taiyin.Body.triton.id == 801
    assert taiyin.Body.charon.id == 901
    assert taiyin.ObservedFlag.topocentric.mask == taiyin.PositionFlag.topocentric.mask
    assert taiyin.ObservedFlag.horizontal.mask == 1 << 32
    assert taiyin.ObservedFlag.refraction.mask == 1 << 33


def test_result_flag_preserves_unknown_bits() -> None:
    unknown = taiyin.ResultFlag(1 << 31)
    assert int(unknown) == 1 << 31
    assert unknown | taiyin.ResultFlag.numericalDerivative == unknown | 2


@pytest.mark.parametrize(
    "text,month,is_leap,month_name",
    [
        ("正", 1, False, taiyin.ChineseCalendarMonthName.normal),
        ("九月", 9, False, taiyin.ChineseCalendarMonthName.normal),
        ("闰五月", 5, True, taiyin.ChineseCalendarMonthName.normal),
        ("閏五", 5, True, taiyin.ChineseCalendarMonthName.normal),
        ("冬月", 11, False, taiyin.ChineseCalendarMonthName.normal),
        ("腊月", 12, False, taiyin.ChineseCalendarMonthName.normal),
        ("后九月", 9, True, taiyin.ChineseCalendarMonthName.laterNine),
        ("十三月", 13, True, taiyin.ChineseCalendarMonthName.thirteen),
        ("拾贰", 12, False, taiyin.ChineseCalendarMonthName.altTwelve),
    ],
)
def test_lunar_date_from_string_month_names(text, month, is_leap, month_name):
    value = taiyin.LunarDate.from_string(2003, text, 1)
    assert value == taiyin.LunarDate(2003, month, 1, is_leap, 0, month_name)


def test_lunar_date_from_string_validates_user_input():
    with pytest.raises(ValueError, match="unknown Chinese lunar month"):
        taiyin.LunarDate.from_string(2003, "水果月", 1)
    with pytest.raises(ValueError, match="lunar day"):
        taiyin.LunarDate.from_string(2003, "九月", 31)


def test_public_runtime_facade_creates_context() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    assert isinstance(context, taiyin.EphemerisContext)
    assert taiyin.JulianDate.from_double(2451545.25).to_double() == 2451545.25
    tdb, tdb_flags = context.time.tt_to_tdb(taiyin.JulianDate(2451545, 0.0))
    tt, tt_flags = context.time.tdb_to_tt(tdb)
    assert tdb_flags | tt_flags == taiyin.ResultFlag.none
    assert tt.to_double() == 2451545.0


def test_runtime_data_inventory_and_source_priority_controls() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    sources = eph.registered_data_sources
    assert isinstance(sources, tuple)
    assert all(isinstance(source, taiyin.RuntimeDataSource) for source in sources)
    eph.set_ephemeris_source_priority("de442.bsp", -10)
    eph.clear_ephemeris_source_priority("de442.bsp")
    eph.set_ephemeris_source_priority("custom.bsp", 1000)
    eph.clear_all_ephemeris_source_priorities()
    with pytest.raises(ValueError):
        eph.set_ephemeris_source_priority("", 1)
    with pytest.raises(TypeError):
        eph.set_ephemeris_source_priority("de442.bsp", 1.0)


def test_time_api_matches_cpp_julian_date_oracles() -> None:
    context = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False).create_context()
    date = taiyin.AstroDateTime(2024, 4, 8, 18, 17, 20.0)
    jd, jd_flags = context.time.julian_day(date)
    assert jd_flags == taiyin.ResultFlag.none
    assert jd.to_double() == 2460409.262037037
    reversed_date, reversed_flags = context.time.reverse_julian_day(jd)
    assert reversed_flags == taiyin.ResultFlag.none
    assert reversed_date.year == 2024
    decimal_year, decimal_year_flags = context.time.decimal_year(jd)
    assert decimal_year_flags == taiyin.ResultFlag.none
    assert abs(decimal_year - 2024.2698416312485) < 1e-12
    centuries, centuries_flags = context.time.julian_centuries_since_j2000(
        taiyin.JulianDate(2488070, 0.0)
    )
    assert centuries_flags == taiyin.ResultFlag.none
    assert centuries == 1.0
    tt, tt_flags = context.time.utc_to_tt(taiyin.JulianDate(2451545, 0.25), 37.0)
    assert tt_flags == taiyin.ResultFlag.none
    assert abs(tt.seconds_difference(taiyin.JulianDate(2451545, 0.25)) - 69.184) < 1e-10
    tai_minus_utc, tai_minus_utc_flags = context.time.tai_minus_utc(date)
    assert tai_minus_utc_flags == taiyin.ResultFlag.none
    assert tai_minus_utc == 37.0
    delta_t, delta_t_flags = context.time.delta_t(37.0, -0.1)
    assert delta_t_flags == taiyin.ResultFlag.none
    assert abs(delta_t - 69.284) < 1e-12
    precise, precise_flags = context.time.precise_scales_from_utc(date, 37.0, -0.1)
    assert precise_flags == taiyin.ResultFlag.none
    assert abs(precise.tt.seconds_difference(precise.utc) - 69.184) < 1e-10
    estimated, estimated_flags = context.time.estimated_scales_from_ut1(
        date, delta_t_seconds=69.17035296181177
    )
    assert estimated_flags == taiyin.ResultFlag.none
    assert abs(estimated.tt.seconds_difference(estimated.ut1) - 69.17035296181177) < 1e-10


def test_native_position_matches_cartesian_state_oracle() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")
    source_path = (
        Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    )
    eph=taiyin.Ephemeris(source_paths=[str(source_path)],load_packaged_data=False)
    context=eph.create_context()
    context.configuration.set_deflectors(
        [taiyin.ApparentDeflector(body_id=10,schwarzschild_radius_au=1e-8)],
        solar_deflector_index=0)
    clone=eph.clone_context(context)
    context.configuration.clear_deflectors()
    context.configuration.use_solar_deflector()
    ut1 = taiyin.JulianDate(2460310, 0.5)
    flags = (taiyin.PositionFlag.speed, taiyin.PositionFlag.xyz)
    position, position_flags = context.position.at_ut1(
        taiyin.Body.mercury, ut1, flags
    )
    diagnostic = context.last_diagnostic
    state, state_flags = context.position.state_at_ut1(taiyin.Body.mercury, ut1)
    cloned_position, cloned_position_flags = clone.position.at_ut1(
        taiyin.Body.mercury, ut1
    )
    assert position_flags == taiyin.ResultFlag.none
    assert state_flags == taiyin.ResultFlag.none
    assert cloned_position_flags == taiyin.ResultFlag.none
    assert diagnostic is not None and diagnostic.status == 0
    assert len(position) == 6
    assert tuple(position[:3]) == tuple(state.position_au)
    assert tuple(position[3:]) == tuple(state.velocity_au_per_day)
    assert all(value==value for value in cloned_position)
    formatted=eph.format_ephemeris_diagnostic(diagnostic)
    assert "TAIYIN_STATUS_OK" in formatted and "target=199" in formatted


def test_default_apparent_corrections_support_speed_and_multiple_deflectors() -> None:
    default_flags = taiyin.ApparentConfig().flags
    assert taiyin.ApparentFlag.lightTime in default_flags
    assert taiyin.ApparentFlag.aberration in default_flags
    assert taiyin.ApparentFlag.deflection in default_flags
    assert taiyin.ApparentFlag.shapiroDelay not in default_flags

    context = taiyin.Ephemeris().create_context()
    ut1 = taiyin.JulianDate.from_double(2460310.5)
    values, values_flags = context.position.at_ut1(
        taiyin.Body.jupiter,
        ut1,
        flags=(taiyin.PositionFlag.speed,),
    )
    assert values_flags == taiyin.ResultFlag.none
    assert len(values) == 6
    assert all(math.isfinite(value) for value in values)
    sidereal, sidereal_flags = context.astrology.sidereal_position_at_ut1(
        taiyin.Body.jupiter,
        ut1,
        flags=(taiyin.PositionFlag.speed,),
    )
    assert sidereal_flags == taiyin.ResultFlag.none
    assert math.isfinite(sidereal.siderealLongitudeRadians)
    assert math.isfinite(sidereal.siderealLongitudeRateRadiansPerDay)

    solar_rs_au = 1.97412574336e-8
    context.configuration.set_deflectors(
        [
            taiyin.ApparentDeflector(taiyin.Body.sun.id, solar_rs_au),
            taiyin.ApparentDeflector(
                taiyin.Body.jupiter.id,
                solar_rs_au * 0.0009547919,
            ),
        ],
        solar_deflector_index=0,
    )
    custom_values, custom_values_flags = context.position.at_ut1(
        taiyin.Body.mars,
        ut1,
        flags=(taiyin.PositionFlag.speed,),
    )
    assert custom_values_flags == taiyin.ResultFlag.none
    assert len(custom_values) == 6
    assert all(math.isfinite(value) for value in custom_values)

    context.configuration.reset()
    reset_values, reset_values_flags = context.position.at_ut1(
        taiyin.Body.jupiter,
        ut1,
        flags=(taiyin.PositionFlag.speed,),
    )
    assert reset_values_flags == taiyin.ResultFlag.none
    assert len(reset_values) == 6
    assert all(math.isfinite(value) for value in reset_values)


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
    result, result_flags = context.position.state_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate(2460310, 0.5)
    )
    assert result_flags == taiyin.ResultFlag.none
    assert context.last_status == 0
    assert all(value == value for value in result.position_au)


def test_default_runtime_uses_the_installed_package_data() -> None:
    package_data = Path(taiyin.__file__).resolve().parent / "data"
    if not (package_data / "index.opc").is_file():
        pytest.skip("installed package data is unavailable")

    eph = taiyin.Ephemeris()
    assert eph.catalog_size >= 13
    assert any(source.kind is taiyin.RuntimeDataSourceKind.ephemeris
               for source in eph.registered_data_sources)
    assert eph.star_catalog.magnitude_of("antares") == pytest.approx(0.96, abs=0.1)
    eph.star_catalog.clear()


def test_runtime_eop_and_lunar_limb_data_controls() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")
    limb_path = (
        Path(source_root) / "data/lunar-limb/kaguya_lalt_16ppd.tll1"
    )
    if not limb_path.is_file():
        pytest.skip("Taiyin lunar-limb fixture is unavailable")

    eph = taiyin.Ephemeris(
        load_packaged_data=False,
        load_builtin_eop=False,
        lunar_limb_path=str(limb_path),
    )
    assert eph.has_eop_table is False
    assert eph.has_lunar_limb_model is True

    eph.load_builtin_eop_table()
    assert eph.has_eop_table is True
    eph.clear_eop_table()
    assert eph.has_eop_table is False

    eph.clear_lunar_limb_model()
    assert eph.has_lunar_limb_model is False
    eph.load_lunar_limb_model(str(limb_path))
    assert eph.has_lunar_limb_model is True

    with pytest.raises(RuntimeError):
        eph.load_eop_table(str(limb_path) + ".missing")
    with pytest.raises(RuntimeError):
        eph.load_lunar_limb_model(str(limb_path) + ".missing")


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
    assert calendar.config == taiyin.ChineseCalendarConfig.historical_china()
    assert context.create_chinese_calendar(
        taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(540)
    ).config.utcOffsetMinutes == 540


def test_context_owns_one_chinese_calendar_policy() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    config = taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(540)
    context = eph.create_context(chinese_calendar_config=config)
    assert context.chinese_calendar.config is config
    clone = eph.clone_context(context)
    assert clone.chinese_calendar.config is config

    historical = taiyin.ChineseCalendarConfig.historical_china()
    assert historical.mode is taiyin.ChineseCalendarMode.chinaStandardHistorical
    assert historical.utcOffsetMinutes == 480
    assert taiyin.ChineseCalendarConfig.historical_china(
        540
    ).utcOffsetMinutes == 540
    with pytest.raises(ValueError, match="-840 to 840"):
        taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(841)
    with pytest.raises(ValueError, match="-180 to 180"):
        taiyin.ChineseCalendarConfig.local_astronomical_meridian(181.0)

    vietnam = taiyin.ChineseCalendarConfig.local_astronomical_meridian(
        105.8,
        utc_offset_minutes=7 * 60,
    )
    assert (
        vietnam.dayBoundaryMode
        is taiyin.ChineseCalendarDayBoundaryMode.meanSolarMeridian
    )
    assert vietnam.utcOffsetMinutes == 7 * 60
    assert vietnam.calendarMeridianDegrees == 105.8
    with pytest.raises(ValueError, match="-840 to 840"):
        taiyin.ChineseCalendarConfig.local_astronomical_meridian(
            105.8,
            utc_offset_minutes=841,
        )


def test_context_configuration_sets_observer_location() -> None:
    context = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False).create_context()
    context.configuration.set_observer_location(taiyin.ObserverLocation(116.4074, 39.9042, 43.5))
    with pytest.raises(ValueError):
        context.configuration.set_observer_location(taiyin.ObserverLocation(0.0, 91.0))


def test_utc_out_of_range_estimate_is_explicit_and_diagnostic() -> None:
    context = taiyin.Ephemeris(
        load_builtin_eop=False,
    ).create_context()
    utc = taiyin.AstroDateTime(2024, 1, 1)

    with pytest.raises(taiyin.TimeScaleError, match="earth orientation data") as caught:
        context.position.at_utc(taiyin.Body.mars, utc)
    assert caught.value.status is taiyin.StatusCode.eopOutOfRange
    assert caught.value.status_code == -3001
    assert context.last_status == -3001
    strict_diagnostic = context.last_diagnostic
    assert strict_diagnostic is not None
    assert strict_diagnostic.raw_time_scale_fallback_reason_id == 1

    context.time.set_allow_utc_out_of_range_estimate(True)
    position, position_flags = context.position.at_utc(taiyin.Body.mars, utc)
    assert len(position) == 3
    assert position_flags & taiyin.ResultFlag.timeScaleFallback
    assert context.last_status == 0
    fallback_diagnostic = context.last_diagnostic
    assert fallback_diagnostic is not None
    assert fallback_diagnostic.raw_time_scale_route_id == 2
    assert fallback_diagnostic.raw_time_scale_fallback_reason_id == 1


def test_context_configuration_and_time_model_controls() -> None:
    eph=taiyin.Ephemeris(load_packaged_data=False,load_builtin_eop=True)
    context=eph.create_context()
    clone=eph.clone_context(context)
    location=taiyin.ObserverLocation(116.4074,39.9042,43.5)
    ut1=taiyin.JulianDate.from_double(2460409.25)
    tt=ut1.add_seconds(69.184)

    context.time.set_allow_utc_out_of_range_estimate(True)
    context.time.set_tdb_model(taiyin.TdbModel.sofaFull)
    context.time.set_delta_t_model(taiyin.DeltaTModel.estimatedDefault,taiyin.EphemerisFamily.de441)
    clone.time.set_allow_utc_out_of_range_estimate(False)
    context.configuration.set_simple_topocentric_observer(location,ut1=ut1,tt=tt)
    context.configuration.set_topocentric_observer_offset(taiyin.CartesianState(
        taiyin.Vector3(1e-5,2e-5,3e-5),taiyin.Vector3(1e-6,2e-6,3e-6),
        taiyin.Vector3(1e-7,2e-7,3e-7)))
    context.configuration.set_precise_topocentric_observer(location,utc=ut1,tt=tt)
    context.configuration.clear_observer_location()
    context.configuration.set_atmosphere(taiyin.Atmosphere(
        pressure_mbar=1000,temperature_celsius=20,relative_humidity_percent=45,
        wavelength_micrometer=0.55))
    context.configuration.set_meteorological_range_km(20)
    context.configuration.set_astro_models(taiyin.AstroModelConfig())
    context.configuration.set_celestial_pole_offset(dx_radians=1e-9,dy_radians=-1e-9)
    context.configuration.set_refraction_model(taiyin.RefractionModel.sofa)
    context.configuration.use_solar_deflector()
    context.configuration.clear_deflectors()
    context.configuration.set_light_time_iteration(max_iterations=8,tolerance_days=1e-13)
    context.configuration.enable_shapiro_delay()
    context.configuration.disable_shapiro_delay()
    context.configuration.set_eclipse_models(
        shadow=taiyin.EclipseShadowModel.nasaDanjon,
        moon_radius=taiyin.EclipseMoonRadiusModel.almanac)
    context.configuration.set_apparent_config(taiyin.ApparentConfig(
        flags=frozenset((taiyin.ApparentFlag.lightTime,taiyin.ApparentFlag.shapiroDelay))))
    context.configuration.reset()

    with pytest.raises(ValueError):
        context.configuration.set_meteorological_range_km(0.5)
    with pytest.raises(ValueError):
        context.configuration.set_light_time_iteration(max_iterations=-1,tolerance_days=0)
    with pytest.raises(ValueError):
        context.configuration.set_apparent_config(taiyin.ApparentConfig(
            flags=frozenset((taiyin.ApparentFlag.shapiroDelay,))))
    with pytest.raises(ValueError):
        context.configuration.set_apparent_config(taiyin.ApparentConfig(output_frame=-1))
    with pytest.raises(ValueError):
        context.configuration.set_deflectors(
            [taiyin.ApparentDeflector(10,-1)])
    with pytest.raises(ValueError):
        context.configuration.set_deflectors([],solar_deflector_index=0)


def test_four_pillars_with_explicit_ephemeris_source_path() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
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
        pytest.skip("Taiyin source-tree ephemeris fixture is unavailable")
    eph = taiyin.Ephemeris(
        source_paths=[str(source_path)],
        load_packaged_data=False,
    )
    context = eph.create_context()
    local_time = taiyin.AstroDateTime(1990, 5, 15, 14, 30)
    pillars, pillar_flags = context.chinese_calendar.four_pillars(
        local_time.to_julian_date().add_seconds(-8 * 3600), local_time
    )
    assert pillar_flags == taiyin.ResultFlag.none
    assert pillars == taiyin.GanzhiFourPillars(
        taiyin.Ganzhi.from_native(0x66),
        taiyin.Ganzhi.from_native(0x75),
        taiyin.Ganzhi.from_native(0x64),
        taiyin.Ganzhi.from_native(0x97),
    )
    lunar, lunar_flags = context.chinese_calendar.from_solar(
        taiyin.SolarDate(2025, 1, 29)
    )
    assert lunar_flags == taiyin.ResultFlag.none
    assert lunar == taiyin.LunarDate(2025, 1, 1, False, 30)
    solar, solar_flags = context.chinese_calendar.from_lunar(lunar)
    assert solar_flags == taiyin.ResultFlag.none
    assert solar == taiyin.SolarDate(2025, 1, 29)
    named_lunar = taiyin.LunarDate.from_string(2003, "九月", 1)
    named_solar, named_solar_flags = context.chinese_calendar.from_lunar(named_lunar)
    assert named_solar_flags == taiyin.ResultFlag.none
    resolved_named, resolved_named_flags = context.chinese_calendar.from_solar(
        named_solar
    )
    assert resolved_named_flags == taiyin.ResultFlag.none
    assert (resolved_named.year, resolved_named.month, resolved_named.day) == (
        2003,
        9,
        1,
    )
    assert resolved_named.isLeap is False
    with pytest.raises(ValueError, match="day exceeds"):
        context.chinese_calendar.from_lunar(
            taiyin.LunarDate.from_string(2024, "正月", 30)
        )
    with pytest.raises(ValueError, match="does not exist"):
        context.chinese_calendar.from_lunar(
            taiyin.LunarDate.from_string(2023, "闰五月", 1)
        )
    with pytest.raises(ValueError, match="Gregorian solar date"):
        context.chinese_calendar.from_solar(taiyin.SolarDate(2025, 2, 30))
    with pytest.raises(ValueError, match="does not exist"):
        context.chinese_calendar.get_month_days(2023, 5, True)
    month_days, month_days_flags = context.chinese_calendar.get_month_days(
        2026, 1, False
    )
    assert month_days_flags == taiyin.ResultFlag.none
    assert month_days == 30

    new_moon_probe = taiyin.AstroDateTime(
        2026, 8, 12, 17, 40
    ).to_julian_date()
    beijing_historical, beijing_historical_flags = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china(
            8 * 60
        )
    ).chinese_calendar.from_instant_ut(new_moon_probe)
    india_historical, india_historical_flags = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china(
            5 * 60 + 30
        )
    ).chinese_calendar.from_instant_ut(new_moon_probe)
    india_china_astronomical, india_china_astronomical_flags = eph.create_context(
        chinese_calendar_config=(
            taiyin.ChineseCalendarConfig.china_standard_astronomical(
                5 * 60 + 30
            )
        )
    ).chinese_calendar.from_instant_ut(new_moon_probe)
    india_local_astronomical, india_local_astronomical_flags = eph.create_context(
        chinese_calendar_config=(
            taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(
                5 * 60 + 30
            )
        )
    ).chinese_calendar.from_instant_ut(new_moon_probe)
    assert beijing_historical_flags == taiyin.ResultFlag.none
    assert india_historical_flags == taiyin.ResultFlag.none
    assert india_china_astronomical_flags == taiyin.ResultFlag.none
    assert india_local_astronomical_flags == taiyin.ResultFlag.none
    assert (beijing_historical.month, beijing_historical.day) == (7, 1)
    assert (india_historical.month, india_historical.day) == (6, 30)
    assert (
        india_china_astronomical.month,
        india_china_astronomical.day,
    ) == (6, 30)
    assert (
        india_local_astronomical.month,
        india_local_astronomical.day,
    ) == (7, 1)

    march_probe = taiyin.AstroDateTime(2025, 3, 1, 12).to_julian_date().add_seconds(
        -8 * 3600
    )
    calendar = context.chinese_calendar
    previous_jie_qi, previous_jie_qi_flags = calendar.get_prev_jie_qi_ut(
        march_probe
    )
    next_jie_qi, next_jie_qi_flags = calendar.get_next_jie_qi_ut(march_probe)
    previous_jie, previous_jie_flags = calendar.get_prev_jie_ut(march_probe)
    next_qi, next_qi_flags = calendar.get_next_qi_ut(march_probe)
    assert previous_jie_qi_flags == taiyin.ResultFlag.none
    assert next_jie_qi_flags == taiyin.ResultFlag.none
    assert previous_jie_flags == taiyin.ResultFlag.none
    assert next_qi_flags == taiyin.ResultFlag.none
    assert previous_jie_qi.indexFromWinterSolstice == 4
    assert next_jie_qi.indexFromWinterSolstice == 5
    assert previous_jie.indexFromWinterSolstice == 3
    assert next_qi.indexFromWinterSolstice == 6
    year, year_flags = calendar.calc_year_ut(
        taiyin.AstroDateTime(2034, 1, 15, 12).to_julian_date()
    )
    assert year_flags == taiyin.ResultFlag.none
    assert year.leapMonthIndex == 1
    assert (year.months[0].month, year.months[0].isLeap) == (11, False)
    assert (year.months[1].month, year.months[1].isLeap) == (11, True)
    # The physical month building is resolved by the native calendar.  A leap
    # month repeats its predecessor's building rather than advancing it.
    assert year.months[0].monthBuildingBranch == 0  # Zi
    assert year.months[1].monthBuildingBranch == 0  # Leap 11 remains Zi


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
    result, result_flags = context.position.at_tdb(
        -100, jd, jd, flags=(taiyin.PositionFlag.speed,)
    )
    assert result_flags == taiyin.ResultFlag.none
    assert result == (-100.0, 2451545.0, 2451545.0, 1.0, 5.0, 6.0)
    assert context.last_status == 0
    batch, batch_flags = context.position.batch_at_tt(
        [-100, -100], jd, flags=(taiyin.PositionFlag.speed,)
    )
    assert batch_flags == taiyin.ResultFlag.none
    assert [row[0] for row in batch] == [-100.0, -100.0]
    assert all(0.0 < jd.to_double() - row[1] < 1e-7 for row in batch)
    assert [row[2:] for row in batch] == [
        (2451545.0, 1.0, 5.0, 6.0)
    ] * 2
    eph.clear_custom_targets()
    assert registration.is_closed
    replacement=eph.register_custom_target(
        -100,position_evaluator=lambda request:[1,2,3,4,5,6])
    registration.close()
    reset_values, reset_values_flags = context.position.at_tdb(-100, jd, jd)
    assert reset_values_flags == taiyin.ResultFlag.none
    assert reset_values == (1.0, 2.0, 3.0)
    replacement.close()


def test_context_diagnostics_are_owned_per_context() -> None:
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run the source-data integration test")
    source_path = (
        Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    )
    eph = taiyin.Ephemeris(source_paths=[str(source_path)], load_packaged_data=False)
    first = eph.create_context()
    second = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.0)

    assert first.has_last_diagnostic is False
    assert first.last_diagnostic is None
    position, position_flags = first.position.at_tdb(taiyin.Body.mercury, jd, jd)
    assert position_flags == taiyin.ResultFlag.none
    assert len(position) == 3
    first_diagnostic = first.last_diagnostic
    assert first_diagnostic is not None
    assert first.last_status == 0
    assert first.last_operation == "EphemerisContext.position_values_at_tdb"
    assert first_diagnostic.target_id == taiyin.Body.mercury.id

    cloned_position, cloned_position_flags = second.position.at_tdb(
        taiyin.Body.venus, jd, jd
    )
    assert cloned_position_flags == taiyin.ResultFlag.none
    assert len(cloned_position) == 3
    assert second.last_status == 0
    second_diagnostic = second.last_diagnostic
    first_diagnostic = first.last_diagnostic
    assert second_diagnostic is not None
    assert first_diagnostic is not None
    assert second_diagnostic.target_id == taiyin.Body.venus.id
    assert first_diagnostic.target_id == taiyin.Body.mercury.id

    rows, rows_flags = first.position.batch_at_tt(
        [taiyin.Body.mercury, taiyin.Body.venus], jd
    )
    assert rows_flags == taiyin.ResultFlag.none
    assert len(rows) == 2
    assert first.last_status == 0
    assert first.last_operation == "EphemerisContext.position_values_at_tt"
    # A compact batch deliberately avoids one diagnostic allocation per body,
    # so there is no misleading single-target snapshot to expose here.
    assert first.last_diagnostic is None

    with pytest.raises(RuntimeError):
        first.position.at_tt(987654, jd)
    assert first.last_status != 0
    failure_diagnostic = first.last_diagnostic
    assert failure_diagnostic is not None
    assert failure_diagnostic.target_id == 987654


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
    result, result_flags = context.position.state_at_tdb(-101, jd, jd)
    assert result_flags == taiyin.ResultFlag.none
    assert tuple(result.position_au) == (-101.0, 2.0, 3.0)
    assert tuple(result.velocity_au_per_day) == (4.0, 5.0, 6.0)
    assert tuple(result.acceleration_au_per_day2) == (7.0, 8.0, 9.0)
    assert context.last_status == 0
    registration.close()


def test_custom_target_callback_can_outlive_closed_registration() -> None:
    """A running callback remains safe when its registration is destroyed."""
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.0)
    entered = Event()
    allow_return = Event()
    failures = []

    def evaluator(request):
        entered.set()
        assert allow_return.wait(timeout=2.0)
        return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    registration = eph.register_custom_target(
        -102, position_evaluator=evaluator)

    def call_target():
        try:
            values, value_flags = context.position.at_tdb(-102, jd, jd)
            assert value_flags == taiyin.ResultFlag.none
            assert values == (1.0, 2.0, 3.0)
        except BaseException as error:  # Report worker failures to pytest.
            failures.append(error)

    worker = Thread(target=call_target)
    worker.start()
    assert entered.wait(timeout=2.0)
    registration.close()
    del registration
    allow_return.set()
    worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert failures == []


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
    eph.clear_custom_ayanamsha_models()
    assert registration.is_closed
    replacement=eph.register_custom_ayanamsha_model(10000,lambda request:0.5)
    registration.close()
    assert taiyin._native.ayanamsha_at_tt(
        context._native_context,10000,jd,taiyin._native.POSITION_NONUT)==0.5
    replacement.close()


def test_custom_house_system_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    registration = eph.register_custom_house_system_model(
        10000,
        lambda request: [request.armc_radians + number for number in range(12)],
    )
    assert taiyin._native.houses_from_armc(0.1, 0.5, 0.4, 10000) == [
        0.1 + number for number in range(12)
    ]
    dependent=eph.register_custom_house_system_model(
        10001,lambda request:(_ for _ in ()).throw(RuntimeError("fallback")),
        fallback=registration.model)
    eph.clear_custom_house_system_models()
    assert registration.is_closed and dependent.is_closed
    replacement=eph.register_custom_house_system_model(
        10000,lambda request:[request.armc_radians+number for number in range(12)])
    registration.close()
    assert taiyin._native.houses_from_armc(0.2,0.5,0.4,10000)[0]==0.2
    replacement.close()


def test_registers_builtin_astrology_targets() -> None:
    eph=taiyin.Ephemeris(load_packaged_data=False,load_builtin_eop=False)
    eph.register_builtin_astrology_targets()
