import os
from pathlib import Path

import pytest

import taiyin


START_UT1 = taiyin.JulianDate.from_double(2460409.0)


@pytest.fixture()
def context():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run orbital integration tests")
    source = (
        Path(source_root)
        / "data"
        / "ephemerides"
        / "opm2"
        / "major-bodies"
        / "600y"
    )
    return taiyin.Ephemeris(
        source_paths=[str(source)], load_packaged_data=False
    ).create_context()


def _tt_for(context, ut1):
    delta_t, _ = context.time.estimated_delta_t_from_ut1(ut1)
    tt, _ = context.time.ut1_to_tt(ut1, delta_t)
    return tt


def test_moon_osculating_orbit_and_reference_point_geometry(context):
    orbit, orbit_flags = context.orbits.osculating_at_ut1(
        taiyin.Body.moon, START_UT1
    )
    points, points_flags = context.orbits.reference_points_at_ut1(
        taiyin.Body.moon, START_UT1
    )

    assert (orbit_flags | points_flags) == taiyin.ResultFlag.none

    assert orbit.body is taiyin.Body.moon
    assert orbit.center is taiyin.Body.earth
    assert orbit.referenceFrame is taiyin.ApparentFrame.j2000_ecliptic
    assert 0.01 <= orbit.eccentricity <= 0.2
    assert 20.0 <= orbit.osculatingPeriodDays <= 35.0
    assert orbit.periapsisDistanceAu < orbit.currentDistanceAu
    assert orbit.currentDistanceAu < orbit.apoapsisDistanceAu
    assert orbit.gravitationalParameterAu3PerDay2 > 0.0
    assert context.last_status == 0

    assert points.model is taiyin.OrbitReferencePointModel.osculating
    assert points.ascendingNode.positionAu.z == 0.0
    assert points.descendingNode.positionAu.z == 0.0
    assert abs(
        points.ascendingNode.longitudeRadians
        - orbit.longitudeOfAscendingNodeRadians
    ) <= 1e-12
    assert abs(points.periapsis.distanceAu - orbit.periapsisDistanceAu) <= 1e-15
    assert abs(points.apoapsis.distanceAu - orbit.apoapsisDistanceAu) <= 1e-15
    assert abs(
        points.secondFocus.distanceAu
        - 2.0 * orbit.semiMajorAxisAu * orbit.eccentricity
    ) <= 1e-15
    assert sum(
        left * right
        for left, right in zip(
            points.periapsis.positionAu, points.apoapsis.positionAu
        )
    ) < 0.0


def test_tt_and_ut1_routes_agree(context):
    tt = _tt_for(context, START_UT1)
    ut_orbit, ut_orbit_flags = context.orbits.osculating_at_ut1(
        taiyin.Body.moon, START_UT1
    )
    tt_orbit, tt_orbit_flags = context.orbits.osculating_at_tt(
        taiyin.Body.moon, tt
    )
    ut_points, ut_points_flags = context.orbits.reference_points_at_ut1(
        taiyin.Body.moon, START_UT1
    )
    tt_points, tt_points_flags = context.orbits.reference_points_at_tt(
        taiyin.Body.moon, tt
    )

    assert (
        ut_orbit_flags
        | tt_orbit_flags
        | ut_points_flags
        | tt_points_flags
    ) == taiyin.ResultFlag.none
    assert abs(tt_orbit.currentDistanceAu - ut_orbit.currentDistanceAu) <= 1e-13
    assert abs(tt_orbit.eccentricity - ut_orbit.eccentricity) <= 1e-13
    assert abs(
        tt_points.periapsis.longitudeRadians
        - ut_points.periapsis.longitudeRadians
    ) <= 1e-12


def test_every_native_orbital_reference_frame(context):
    for frame in taiyin.ApparentFrame:
        if frame is taiyin.ApparentFrame.unknown:
            continue
        orbit, orbit_flags = context.orbits.osculating_at_ut1(
            taiyin.Body.moon, START_UT1, reference_frame=frame
        )
        assert orbit_flags == taiyin.ResultFlag.none
        assert orbit.referenceFrame is frame
        assert orbit.rawReferenceFrameId == frame.value


def test_lunar_apsis_and_node_swiss_oracles(context):
    perigee, perigee_flags = context.orbits.search_apsis_from_ut1(
        taiyin.Body.moon, taiyin.ApsisKind.pericenter, START_UT1
    )
    previous_apogee, previous_apogee_flags = context.orbits.search_apsis_from_ut1(
        taiyin.Body.moon,
        taiyin.ApsisKind.apocenter,
        START_UT1,
        direction=taiyin.OrbitalSearchDirection.reverse,
    )
    ascending_node, ascending_node_flags = context.orbits.search_plane_node_from_ut1(
        taiyin.Body.moon, taiyin.PlaneNodeKind.ascending, START_UT1
    )
    previous_node, previous_node_flags = context.orbits.search_plane_node_from_ut1(
        taiyin.Body.moon,
        taiyin.PlaneNodeKind.ascending,
        START_UT1,
        direction=taiyin.OrbitalSearchDirection.reverse,
    )

    assert (
        perigee_flags
        | previous_apogee_flags
        | ascending_node_flags
        | previous_node_flags
    ) == taiyin.ResultFlag.none

    assert abs(perigee.coordinate.to_double() - 2460436.4196451753) <= 1e-4
    assert abs(perigee.radialVelocityAuPerDay) < 1e-8
    assert perigee.kind is taiyin.ApsisKind.pericenter
    assert perigee.direction is taiyin.OrbitalSearchDirection.forward
    assert perigee.iterationCount > 0
    assert perigee.evaluationCount > 0

    assert abs(previous_apogee.coordinate.to_double() - 2460393.1562406393) <= 1e-4
    assert previous_apogee.coordinate.to_double() < START_UT1.to_double()
    assert previous_apogee.direction is taiyin.OrbitalSearchDirection.reverse

    assert abs(ascending_node.coordinate.to_double() - 2460409.0138973210) <= 1e-4
    assert ascending_node.kind is taiyin.PlaneNodeKind.ascending
    assert ascending_node.referenceFrame is taiyin.ApparentFrame.j2000_ecliptic
    assert ascending_node.referencePlaneAngleRadians == ascending_node.referencePlaneAngleRadians
    assert previous_node.coordinate.to_double() < START_UT1.to_double()
    assert previous_node.direction is taiyin.OrbitalSearchDirection.reverse


def test_tt_and_ut1_searches_represent_the_same_events(context):
    perigee_ut1, perigee_ut1_flags = context.orbits.search_apsis_from_ut1(
        taiyin.Body.moon, taiyin.ApsisKind.pericenter, START_UT1
    )
    perigee_tt, perigee_tt_flags = context.orbits.search_apsis_from_tt(
        taiyin.Body.moon,
        taiyin.ApsisKind.pericenter,
        _tt_for(context, START_UT1),
    )
    expected_tt = _tt_for(context, perigee_ut1.coordinate)

    assert (perigee_ut1_flags | perigee_tt_flags) == taiyin.ResultFlag.none
    assert abs(perigee_tt.coordinate.to_double() - expected_tt.to_double()) <= 1e-10
    _, node_tt_flags = context.orbits.search_plane_node_from_tt(
        taiyin.Body.moon,
        taiyin.PlaneNodeKind.ascending,
        _tt_for(context, START_UT1),
    )
    assert node_tt_flags == taiyin.ResultFlag.none
    assert context.last_status == 0


def test_barycenter_approximation_policy(context):
    venus, venus_flags = context.orbits.osculating_at_ut1(
        taiyin.Body.venus_barycenter,
        START_UT1,
        allow_barycenter_approximation=True,
    )

    assert venus_flags == taiyin.ResultFlag.none
    assert venus.center is taiyin.Body.sun
    assert 0.6 <= venus.semiMajorAxisAu <= 0.85
    assert 0.0 <= venus.eccentricity <= 0.05
    assert venus.allowBarycenterApproximation is True


def test_rejects_unsupported_inputs_and_use_after_close(context):
    with pytest.raises(ValueError):
        context.orbits.osculating_at_ut1(taiyin.Body.sun, START_UT1)
    with pytest.raises(ValueError):
        context.orbits.osculating_at_ut1(
            taiyin.Body.moon,
            START_UT1,
            reference_frame=taiyin.ApparentFrame.unknown,
        )

    context.close()
    with pytest.raises(RuntimeError):
        context.orbits.osculating_at_ut1(taiyin.Body.moon, START_UT1)
