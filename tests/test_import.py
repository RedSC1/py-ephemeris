import taiyin


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
    assert context.position.at_tdb(-100, jd, jd) == [
        -100.0,
        2451545.0,
        2451545.0,
        0.0,
        5.0,
        6.0,
    ]
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
    assert context.position.state_at_tdb(-101, jd, jd) == {
        "position_au": (-101.0, 2.0, 3.0),
        "velocity_au_per_day": (4.0, 5.0, 6.0),
        "acceleration_au_per_day2": (7.0, 8.0, 9.0),
    }
    registration.close()


def test_custom_ayanamsha_callback_round_trip() -> None:
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    jd = taiyin.JulianDate(2451545, 0.25)
    registration = eph.register_custom_ayanamsha_model(
        10000,
        lambda request: request["jd_tt"].day_fraction,
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
        lambda request: [request["armc_radians"] + number for number in range(12)],
    )
    assert taiyin._native.houses_from_armc(0.1, 0.5, 0.4, 10000) == [
        0.1 + number for number in range(12)
    ]
    registration.close()
