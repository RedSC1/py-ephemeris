import os
from pathlib import Path

import pytest

import taiyin


@pytest.fixture()
def context():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run eclipse integration tests")
    source = Path(source_root) / "data/ephemerides/opm2/major-bodies/600y"
    context = taiyin.Ephemeris(
        source_paths=[str(source)], load_packaged_data=False
    ).create_context()
    context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id, center_id=taiyin.Body.earth.id
    )
    context.configuration.set_observer_location(
        taiyin.ObserverLocation(116.4074, 39.9042, 43.0)
    )
    context.configuration.set_standard_atmosphere()
    return context


def test_global_lunar_eclipse_solve_next_and_ranges(context):
    solved_ut = context.eclipses.solve_lunar_at_ut1(
        taiyin.JulianDate.from_double(2460926.25),
        options=(taiyin.LunarEclipseSolveOption.includeContacts,),
    )
    solved_tt = context.eclipses.solve_lunar_at_tt(
        taiyin.JulianDate.from_double(2460926.26),
        options=(taiyin.LunarEclipseSolveOption.includeContacts,),
    )
    next_ut = context.eclipses.next_lunar_at_ut1(
        taiyin.JulianDate.from_double(2460926.0),
        kinds=(taiyin.EclipseKind.total,),
        options=(taiyin.LunarEclipseSearchOption.includeContacts,),
    )
    previous = context.eclipses.next_lunar_at_ut1(
        taiyin.JulianDate.from_double(2460927.0),
        kinds=(taiyin.EclipseKind.total,),
        options=(
            taiyin.LunarEclipseSearchOption.includeContacts,
            taiyin.LunarEclipseSearchOption.backward,
        ),
    )
    range_ut = context.eclipses.lunar_eclipses_at_ut1(
        taiyin.JulianDate.from_double(2460926.0),
        taiyin.JulianDate.from_double(2460927.0),
        max_results=4,
        kinds=(taiyin.EclipseKind.total,),
        options=(taiyin.LunarEclipseSearchOption.includeContacts,),
    )
    range_tt = context.eclipses.lunar_eclipses_at_tt(
        taiyin.JulianDate.from_double(2451545.0),
        taiyin.JulianDate.from_double(2452275.0),
        max_results=8,
        options=(taiyin.LunarEclipseSearchOption.includeContacts,),
    )

    assert taiyin.EclipseKind.total in solved_ut.value.kinds
    assert taiyin.EclipseKind.total in solved_tt.value.kinds
    assert solved_ut.value.deltaTSeconds > 60
    assert abs(solved_ut.value.maximum.to_double() - 2460926.258194) <= 2 / 1440
    assert solved_ut.value.contacts[taiyin.LunarEclipseContact.totalBegin] is not None
    assert solved_ut.value.contacts[taiyin.LunarEclipseContact.totalEnd] is not None
    assert abs(next_ut.value.maximum.to_double() - solved_ut.value.maximum.to_double()) <= 2 / 1440
    assert abs(previous.value.maximum.to_double() - solved_ut.value.maximum.to_double()) <= 2 / 1440
    assert len(range_ut.value) == 1
    assert len(range_tt.value) == 5
    assert taiyin.EclipseKind.penumbral in range_tt.value[-1].kinds


def test_global_solar_eclipse_solve_next_and_ranges(context):
    solved_ut = context.eclipses.solve_solar_at_ut1(
        taiyin.JulianDate.from_double(2460409.25),
        options=(taiyin.SolarEclipseSolveOption.includeContacts,),
    )
    solved_tt = context.eclipses.solve_solar_at_tt(
        taiyin.JulianDate.from_double(2460409.263),
        options=(taiyin.SolarEclipseSolveOption.includeContacts,),
    )
    next_ut = context.eclipses.next_solar_at_ut1(
        taiyin.JulianDate.from_double(2460400.0),
        kinds=(taiyin.EclipseKind.total,),
        options=(taiyin.SolarEclipseSearchOption.includeContacts,),
    )
    previous = context.eclipses.next_solar_at_ut1(
        taiyin.JulianDate.from_double(2460410.0),
        kinds=(taiyin.EclipseKind.total,),
        options=(
            taiyin.SolarEclipseSearchOption.includeContacts,
            taiyin.SolarEclipseSearchOption.backward,
        ),
    )
    range_ut = context.eclipses.solar_eclipses_at_ut1(
        taiyin.JulianDate.from_double(2460300.0),
        taiyin.JulianDate.from_double(2460800.0),
        max_results=6,
        options=(taiyin.SolarEclipseSearchOption.includeContacts,),
    )
    range_tt = context.eclipses.solar_eclipses_at_tt(
        taiyin.JulianDate.from_double(2460300.0),
        taiyin.JulianDate.from_double(2460800.0),
        max_results=6,
        options=(taiyin.SolarEclipseSearchOption.includeContacts,),
    )

    assert taiyin.EclipseKind.total in solved_ut.value.kinds
    assert taiyin.EclipseKind.central in solved_ut.value.kinds
    assert taiyin.EclipseKind.total in solved_tt.value.kinds
    assert solved_ut.value.deltaTSeconds > 50
    assert abs(solved_ut.value.maximum.to_double() - 2460409.262039739) <= 2 / 86400
    assert solved_ut.value.coreRadiusKilometers > 0
    assert solved_ut.value.penumbralMarginKilometers < 0
    assert all(solved_ut.value.contacts[contact] is not None for contact in taiyin.SolarEclipseContact)
    assert abs(next_ut.value.maximum.to_double() - solved_ut.value.maximum.to_double()) <= 2 / 86400
    assert abs(previous.value.maximum.to_double() - solved_ut.value.maximum.to_double()) <= 2 / 86400
    assert len(range_ut.value) == 3
    assert taiyin.EclipseKind.annular in range_ut.value[1].kinds
    assert taiyin.EclipseKind.noncentral in range_ut.value[2].kinds
    assert len(range_tt.value) == 3


def test_eclipse_validation_no_event_and_lifecycle(context):
    none = context.eclipses.solve_lunar_at_tt(
        taiyin.JulianDate.from_double(2451594.0)
    )
    assert not none.value.has_eclipse
    assert none.value.maximum is None
    with pytest.raises(ValueError):
        context.eclipses.next_lunar_at_ut1(
            taiyin.JulianDate.from_double(2460926.0),
            kinds=(taiyin.EclipseKind.annular,),
        )
    with pytest.raises(ValueError):
        context.eclipses.lunar_eclipses_at_ut1(
            taiyin.JulianDate.from_double(2.0),
            taiyin.JulianDate.from_double(1.0),
        )
    with pytest.raises(ValueError):
        context.eclipses.solar_eclipses_at_ut1(
            taiyin.JulianDate.from_double(1.0),
            taiyin.JulianDate.from_double(2.0),
            max_results=0,
        )
    with pytest.raises(ValueError):
        context.eclipses.next_solar_at_ut1(
            taiyin.JulianDate.from_double(2460400.0),
            position_flags=(taiyin.PositionFlag.xyz,),
        )
    context.close()
    with pytest.raises(RuntimeError):
        context.eclipses.solve_solar_at_ut1(
            taiyin.JulianDate.from_double(2460409.25)
        )


def test_local_lunar_visibility_and_searches(context):
    global_result = context.eclipses.next_lunar_at_ut1(
        taiyin.JulianDate.from_double(2460926.0),
        kinds=(taiyin.EclipseKind.total,),
        options=(taiyin.LunarEclipseSearchOption.includeContacts,),
    )
    local = context.eclipses.local_lunar_visibility_at_ut1(global_result.value)
    refracted = context.eclipses.local_lunar_visibility_at_ut1(
        global_result.value,
        options=(taiyin.LocalLunarEclipseVisibilityOption.refraction,),
    )
    searched_ut = context.eclipses.next_local_lunar_at_ut1(
        taiyin.JulianDate.from_double(2460926.0),
        kinds=(taiyin.EclipseKind.total,),
        visibility_options=(taiyin.LocalLunarEclipseVisibilityOption.refraction,),
    )
    global_tt = context.eclipses.next_lunar_at_tt(
        taiyin.JulianDate.from_double(2460926.25),
        kinds=(taiyin.EclipseKind.total,),
        options=(taiyin.LunarEclipseSearchOption.includeContacts,),
    )
    local_tt = context.eclipses.local_lunar_visibility_at_tt(global_tt.value)
    searched_tt = context.eclipses.next_local_lunar_at_tt(
        taiyin.JulianDate.from_double(2460926.25),
        kinds=(taiyin.EclipseKind.total,),
    )

    greatest = taiyin.LunarEclipseContact.greatest
    assert taiyin.LocalLunarEclipseVisibilityFlag.maximumVisible in local.value.visibility
    assert local.value.contacts[greatest].moonAltitudeDegrees > 0
    assert refracted.value.contacts[greatest].moonAltitudeDegrees > local.value.contacts[greatest].moonAltitudeDegrees
    assert abs(searched_ut.value.maximum.to_double() - global_result.value.maximum.to_double()) < 1e-12
    assert local_tt.value.contacts[greatest].moonAltitudeDegrees > 0
    assert taiyin.LocalLunarEclipseVisibilityFlag.maximumVisible in searched_tt.value.visibility


def test_local_solar_solve_and_search_tt_ut1(context):
    context.configuration.set_observer_location(
        taiyin.ObserverLocation(-106.4, 23.2, 0.0)
    )
    estimate = taiyin.JulianDate.from_double(2460409.262231433)
    local_ut = context.eclipses.solve_local_solar_at_ut1(estimate)
    refracted = context.eclipses.solve_local_solar_at_ut1(
        estimate,
        visibility_options=(taiyin.LocalSolarEclipseVisibilityOption.refraction,),
    )
    local_tt = context.eclipses.solve_local_solar_at_tt(
        context.time.ut1_to_tt(estimate, context.time.estimated_delta_t_from_ut1(estimate))
    )
    searched_ut = context.eclipses.next_local_solar_at_ut1(
        taiyin.JulianDate.from_double(2460400.0),
        kinds=(taiyin.EclipseKind.total,),
    )
    searched_tt = context.eclipses.next_local_solar_at_tt(
        taiyin.JulianDate.from_double(2460400.0),
        kinds=(taiyin.EclipseKind.total,),
    )
    circumstances_ut = context.eclipses.local_solar_circumstances_at_ut1(estimate)
    circumstances_tt = context.eclipses.local_solar_circumstances_at_tt(
        context.time.ut1_to_tt(estimate, context.time.estimated_delta_t_from_ut1(estimate))
    )

    assert taiyin.EclipseKind.total in local_ut.value.kinds
    assert local_ut.value.magnitude > 0.9
    assert local_ut.value.contacts[taiyin.LocalSolarEclipseContact.partialBegin] is not None
    assert local_ut.value.contacts[taiyin.LocalSolarEclipseContact.partialEnd] is not None
    assert local_ut.value.durationSeconds > 0
    assert refracted.value.has_eclipse
    assert taiyin.EclipseKind.total in local_tt.value.kinds
    assert searched_ut.value.has_eclipse
    assert searched_tt.value.has_eclipse
    assert circumstances_ut.value.magnitude > 0.9
    assert circumstances_ut.value.deltaTSeconds > 50
    assert circumstances_tt.value.magnitude > 0.9
    assert circumstances_tt.value.deltaTSeconds is None
