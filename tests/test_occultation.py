import os
from pathlib import Path

import pytest

import taiyin


ANTARES_LOCATION = taiyin.ObserverLocation(-78.709289952229, 24.897937227562)
MERCURY_LOCATION = taiyin.ObserverLocation(-144.104686755054, -10.079501905368)


@pytest.fixture()
def engine_and_context():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run occultation integration tests")
    root = Path(source_root)
    engine = taiyin.Ephemeris(
        source_paths=[
            str(root / "data/ephemerides/opm2/major-bodies/600y")
        ],
        load_packaged_data=False,
    )
    engine.star_catalog.clear()
    engine.star_catalog.add_tsc1(
        str(root / "data/stars/catalogs/stars-fixed-traditional.tsc1")
    )
    context = engine.create_context()
    context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id, center_id=taiyin.Body.earth.id
    )
    context.configuration.set_observer_location(ANTARES_LOCATION)
    context.configuration.set_standard_atmosphere()
    context.configuration.use_solar_deflector()
    context.configuration.set_apparent_config(
        taiyin.ApparentConfig(
            frozenset(
                {
                    taiyin.ApparentFlag.spherical,
                    taiyin.ApparentFlag.lightTime,
                    taiyin.ApparentFlag.aberration,
                    taiyin.ApparentFlag.deflection,
                }
            ),
            2,
        )
    )
    context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield engine, context
    engine.star_catalog.clear()


def test_star_search_visibility_and_global_where(engine_and_context):
    _, context = engine_and_context
    start = taiyin.JulianDate.from_double(2460310.5)
    geocentric = context.occultation.next_geocentric_star_at_ut1(
        "antares", start, position_flags=(taiyin.PositionFlag.truepos,)
    )
    local = context.occultation.next_local_star_at_ut1(
        "antares",
        start,
        options=(taiyin.OccultationSearchOption.oneCandidate,),
    )
    visibility = context.occultation.local_star_visibility_at_ut1(
        "antares",
        local.value,
        options=(taiyin.OccultationVisibilityOption.refraction,),
    )
    where = context.occultation.star_where_at_ut1(
        "antares",
        geocentric.value,
        visibility_options=(taiyin.OccultationVisibilityOption.refraction,),
    )

    assert geocentric.value.kind is taiyin.LunarOccultationKind.lunarStar
    assert geocentric.value.begin.to_double() < geocentric.value.coordinate.to_double()
    assert geocentric.value.end.to_double() > geocentric.value.coordinate.to_double()
    assert abs(local.value.coordinate.to_double() - 2460318.136560418177) <= 3 / 86400
    assert visibility.value.firstContact is not None
    assert visibility.value.maximum is not None
    assert visibility.value.fourthContact is not None
    assert visibility.value.secondContact is None
    assert visibility.value.thirdContact is None
    assert len(visibility.value.visibleIntervals) == 1
    assert visibility.value.visibleIntervals[0].begin.to_double() < local.value.coordinate.to_double()
    assert where.value.centerLineHitsEarth is True
    assert taiyin.OccultationType.central in where.value.types
    assert -180.0 <= where.value.maximumLocation.longitudeDegrees <= 180.0
    assert -90.0 <= where.value.maximumLocation.latitudeDegrees <= 90.0
    assert where.value.centerLinePath
    assert where.value.visibleRegionPolygon


def test_body_searches_standard_and_custom_radii(engine_and_context):
    _, context = engine_and_context
    start = taiyin.JulianDate.from_double(2460900.5)
    geocentric = context.occultation.next_geocentric_body_at_ut1(
        taiyin.Body.mercury, start
    )
    enlarged = context.occultation.next_geocentric_body_at_ut1(
        taiyin.Body.mercury,
        start,
        target_radius_kilometers=2 * 2439.7,
        options=(taiyin.OccultationSearchOption.filterTotal,),
    )

    context.configuration.set_observer_location(MERCURY_LOCATION)
    local = context.occultation.next_local_body_at_ut1(taiyin.Body.mercury, start)
    local_with_radius = context.occultation.next_local_body_at_ut1(
        taiyin.Body.mercury, start, target_radius_kilometers=2 * 2439.7
    )
    visibility = context.occultation.local_body_visibility_at_ut1(
        taiyin.Body.mercury, local.value
    )
    where = context.occultation.body_where_at_ut1(
        taiyin.Body.mercury, geocentric.value
    )
    where_with_radius = context.occultation.body_where_at_ut1(
        taiyin.Body.mercury,
        enlarged.value,
        target_radius_kilometers=2 * 2439.7,
    )

    assert geocentric.value.kind is taiyin.LunarOccultationKind.lunarBody
    assert abs(geocentric.value.coordinate.to_double() - 2461090.465108) <= 10 / 86400
    assert enlarged.value.targetRadiusRadians > geocentric.value.targetRadiusRadians
    assert enlarged.value.firstContact.to_double() < geocentric.value.firstContact.to_double()
    assert enlarged.value.fourthContact.to_double() > geocentric.value.fourthContact.to_double()
    assert local.value.secondContact is not None
    assert local.value.thirdContact is not None
    assert local_with_radius.value.targetRadiusRadians > local.value.targetRadiusRadians
    assert visibility.value.firstContact is not None
    assert visibility.value.secondContact is not None
    assert visibility.value.thirdContact is not None
    assert visibility.value.fourthContact is not None
    assert visibility.value.visibleIntervals
    assert where.value.maximumLocation is not None
    assert taiyin.OccultationType.central in where.value.types
    assert where_with_radius.value.targetRadiusRadians > where.value.targetRadiusRadians


def test_invalid_inputs_and_use_after_close(engine_and_context):
    _, context = engine_and_context
    start = taiyin.JulianDate.from_double(2460900.5)
    with pytest.raises(ValueError):
        context.occultation.next_geocentric_body_at_ut1(taiyin.Body.moon, start)
    with pytest.raises(ValueError):
        context.occultation.next_geocentric_body_at_ut1(taiyin.Body.ssb, start)
    with pytest.raises(ValueError):
        context.occultation.next_geocentric_body_at_ut1(
            taiyin.Body.mercury, start, target_radius_kilometers=-1
        )
    with pytest.raises(ValueError):
        context.occultation.next_geocentric_star_at_ut1("", start)
    with pytest.raises(ValueError):
        context.occultation.next_geocentric_star_at_ut1(
            "antares", start, position_flags=(taiyin.PositionFlag.xyz,)
        )
    star = context.occultation.next_geocentric_star_at_ut1(
        "antares", taiyin.JulianDate.from_double(2460310.5)
    )
    with pytest.raises(ValueError):
        context.occultation.local_body_visibility_at_ut1(
            taiyin.Body.mercury, star.value
        )

    context.close()
    with pytest.raises(RuntimeError):
        context.occultation.next_geocentric_star_at_ut1("antares", start)
