"""Astrology API regressions ported from legacy Python and C++ oracle tests."""

import math
import os
from pathlib import Path

import pytest
import taiyin


@pytest.fixture()
def ctx():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run Astrology integration tests")
    source_path = Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    context = taiyin.Ephemeris(source_paths=[str(source_path)], load_packaged_data=False).create_context()
    context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id, center_id=taiyin.Body.earth.id)
    context.configuration.set_observer_location(taiyin.ObserverLocation(116.3833, 39.9167, 50.0))
    context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield context
    context.close()


def test_ayanamsha_and_sidereal_position_and_coordinates(ctx):
    tt = taiyin.JulianDate.from_double(2460311.0)
    assert ctx.astrology.has_ayanamsha_model(taiyin.Ayanamsha.lahiri)
    lahiri, lahiri_flags = ctx.astrology.ayanamsha_at_tt(
        tt, ayanamsha=taiyin.Ayanamsha.lahiri
    )
    fagan, fagan_flags = ctx.astrology.ayanamsha_at_tt(tt)
    assert lahiri_flags == fagan_flags == taiyin.ResultFlag.none
    assert 0.0 < lahiri < math.tau
    assert lahiri != fagan

    position, position_flags = ctx.astrology.sidereal_position_at_tt(
        taiyin.Body.sun, tt, ayanamsha=taiyin.Ayanamsha.lahiri,
        flags=(taiyin.PositionFlag.speed,))
    assert position_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert position.coordinateFrame is taiyin.SiderealCoordinateFrame.meanEclipticOfDate
    assert abs((position.tropicalLongitudeRadians - position.siderealLongitudeRadians) - lahiri) < 1e-9
    assert math.isfinite(position.siderealLongitudeRateRadiansPerDay)

    coordinates, coordinate_flags = ctx.astrology.sidereal_coordinates_at_tt(
        taiyin.Body.sun, tt, ayanamsha=taiyin.Ayanamsha.lahiri,
        flags=(taiyin.PositionFlag.speed, taiyin.PositionFlag.xyz))
    assert coordinate_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert coordinates.isCartesian
    assert len(coordinates.coordinates) == len(coordinates.rates) == 3

    epoch = taiyin.SiderealReferenceEpoch.tt(taiyin.JulianDate.from_double(2451545.0))
    fixed, fixed_flags = ctx.astrology.sidereal_position_at_tt(
        taiyin.Body.sun, tt, reference_plane=taiyin.SiderealReferencePlane.meanEclipticAtEpoch,
        reference_epoch=epoch)
    assert fixed_flags == taiyin.ResultFlag.none
    assert fixed.coordinateFrame is taiyin.SiderealCoordinateFrame.fixedMeanEclipticAtEpoch
    with pytest.raises(ValueError):
        ctx.astrology.sidereal_position_at_tt(
            taiyin.Body.sun, tt, reference_plane=taiyin.SiderealReferencePlane.meanEclipticAtEpoch)


def test_lunar_nodes_and_all_apogee_conventions(ctx):
    tt = taiyin.JulianDate.from_double(2460420.5913274437)
    ut1 = taiyin.JulianDate.from_double(2460420.5905)
    true_node, true_node_flags = ctx.astrology.lunar_true_node_at_tt(tt)
    mean_node, mean_node_flags = ctx.astrology.lunar_mean_node_at_ut1(
        ut1, kind=taiyin.LunarNodeKind.descending
    )
    assert (true_node_flags | mean_node_flags) == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert true_node.kind is taiyin.LunarNodeKind.ascending
    assert mean_node.kind is taiyin.LunarNodeKind.descending
    assert math.isfinite(true_node.longitudeRateRadiansPerDay)

    mean, mean_flags = ctx.astrology.lunar_mean_apogee_at_tt(tt)
    osculating, osculating_flags = ctx.astrology.lunar_osculating_apogee_at_tt(tt)
    fitted, fitted_flags = ctx.astrology.lunar_fitted_apogee_at_tt(tt)
    assert (mean_flags | osculating_flags | fitted_flags) == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert mean.definition is taiyin.LunarApsisDefinition.delaunayMean
    assert mean.distanceAu is None
    assert osculating.definition is taiyin.LunarApsisDefinition.osculatingTwoBody
    assert osculating.distanceAu > 0.0
    assert fitted.definition is taiyin.LunarApsisDefinition.de441FittedNatural
    assert fitted.distanceAu > 0.0
    assert not fitted.extrapolated

    _, mean_ut1_flags = ctx.astrology.lunar_mean_apogee_at_ut1(ut1)
    assert mean_ut1_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    _, osculating_ut1_flags = ctx.astrology.lunar_osculating_apogee_at_ut1(ut1)
    assert osculating_ut1_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    _, fitted_ut1_flags = ctx.astrology.lunar_fitted_apogee_at_ut1(ut1)
    assert fitted_ut1_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    with pytest.raises(ValueError):
        ctx.astrology.lunar_mean_node_at_tt(tt, flags=(taiyin.PositionFlag.speed,))


def test_houses_match_cpp_swiss_oracle_and_house_placement(ctx):
    jd = taiyin.JulianDate.from_double(2460311.0)
    porphyry, porphyry_flags = ctx.astrology.houses_at_ut1(
        jd, system=taiyin.HouseSystem.porphyry
    )
    placidus, placidus_flags = ctx.astrology.houses_at_ut1(
        jd, system=taiyin.HouseSystem.placidus
    )
    assert porphyry_flags | placidus_flags == taiyin.ResultFlag.none
    degrees = 180.0 / math.pi
    # test_houses_astrology.cpp: kSwissCases[0], 0.01 arcsec tolerance there.
    assert abs(porphyry.ascendantRadians * degrees - 137.955986373727) < 3e-6
    assert abs(porphyry.midheavenRadians * degrees - 39.424973002554) < 3e-6
    assert abs(porphyry.cuspLongitudesRadians[1] * degrees - 165.112315250003) < 3e-6
    # test_houses_astrology.cpp: kSwissPlacidusCases[0].
    assert abs(placidus.cuspLongitudesRadians[1] * degrees - 159.905715838579) < 3e-6
    assert all(math.isfinite(rate) for rate in porphyry.cuspLongitudeRatesRadiansPerDay)
    houses_at_tt, houses_at_tt_flags = ctx.astrology.houses_at_tt(
        jd, system=taiyin.HouseSystem.porphyry
    )
    assert houses_at_tt_flags == taiyin.ResultFlag.none
    assert houses_at_tt.requestedSystem is taiyin.HouseSystem.porphyry
    placement, placement_flags = ctx.astrology.house_position_of(
        porphyry, porphyry.cuspLongitudesRadians[0]
    )
    assert placement_flags == taiyin.ResultFlag.none
    assert placement.houseNumber == 1
    assert placement.fraction == 0.0

    direct, direct_flags = ctx.astrology.houses_from_armc(
        armc_radians=123.456 / degrees, observer_latitude_radians=39.9167 / degrees,
        true_obliquity_radians=23.436 / degrees, system=taiyin.HouseSystem.placidus)
    # test_houses_astrology.cpp: kSwissPlacidusGeometryCases[0].
    assert abs(direct.cuspLongitudesRadians[0] * degrees - 206.656040425304212) < 3e-6
    assert math.isnan(direct.armcRateRadiansPerDay)
    assert ctx.astrology.has_house_system_model(taiyin.HouseSystem.porphyry)


def test_astrology_validates_context_and_input_contract(ctx):
    tt = taiyin.JulianDate.from_double(2460311.0)
    with pytest.raises(ValueError):
        ctx.astrology.sidereal_position_at_tt(taiyin.Body.sun, tt, flags=(taiyin.PositionFlag.xyz,))
    with pytest.raises(ValueError):
        ctx.astrology.houses_from_armc(
            armc_radians=0.0, observer_latitude_radians=math.pi / 2,
            true_obliquity_radians=0.4)
    ctx.close()
    with pytest.raises(RuntimeError):
        ctx.astrology.ayanamsha_at_tt(tt)


def test_custom_astrology_callbacks_keep_legacy_registration_shape():
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    ayanamsha = eph.register_custom_ayanamsha_model(
        100100, lambda request: request.julian_date_tt.day_fraction,
        reference_precession_model=taiyin.PrecessionModel.iau2006)
    houses = eph.register_custom_house_system_model(
        100100, lambda request: [request.ascendant_radians + index for index in range(12)])
    try:
        assert context.astrology.has_ayanamsha_model(ayanamsha.model)
        # The default public ayanamsha path includes longitude nutation, so
        # it is close to (rather than bit-identical with) the callback value.
        value, result_flags = context.astrology.ayanamsha_at_tt(
            taiyin.JulianDate(2451545, 0.25), ayanamsha=ayanamsha.model
        )
        assert result_flags == taiyin.ResultFlag.none
        assert abs(value - 0.25) < 1e-3
        direct, direct_flags = context.astrology.houses_from_armc(
            armc_radians=1.0, observer_latitude_radians=0.5,
            true_obliquity_radians=0.4, system=houses.model)
        assert direct_flags == taiyin.ResultFlag.none
        assert direct.requestedSystem == houses.model
        assert direct.cuspLongitudesRadians[0] == pytest.approx(
            (direct.ascendantRadians + 0.0) % math.tau)
    finally:
        houses.close()
        ayanamsha.close()
    assert houses.is_closed and ayanamsha.is_closed
