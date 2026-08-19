"""Visibility API regressions against the OPM2 source fixture."""

import os
from pathlib import Path

import pytest
import taiyin


@pytest.fixture()
def ctx():
    root = os.environ.get("TAIYIN_SOURCE_DIR")
    if root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run visibility integration tests")
    source = Path(root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    context = taiyin.Ephemeris(source_paths=[str(source)], load_packaged_data=False).create_context()
    context.configuration.set_geocentric_observer(observer_id=taiyin.Body.earth.id, center_id=taiyin.Body.earth.id)
    context.configuration.set_observer_location(taiyin.ObserverLocation(116.3833, 39.9167, 50.0))
    context.configuration.set_standard_atmosphere()
    context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield context
    context.close()


def test_lunar_planet_and_solar_visibility_searches(ctx):
    start = taiyin.JulianDate.from_double(2460311.0)
    end = taiyin.JulianDate.from_double(2460312.0)
    rise = taiyin.VisibilityEventKind.rise
    upper = taiyin.VisibilityEventKind.upperTransit
    moon_rise, moon_rise_flags = ctx.visibility.moon_rise_set_at_ut1(start, end, event=rise)
    moon_transit, moon_transit_flags = ctx.visibility.moon_transit_at_ut1(start, end, event=upper)
    planet_rise, planet_rise_flags = ctx.visibility.planet_rise_set_at_ut1(
        taiyin.Body.venus, start, end, event=rise)
    planet_transit, planet_transit_flags = ctx.visibility.planet_transit_at_ut1(
        taiyin.Body.venus, start, end, event=upper)
    solar_rise, solar_rise_flags = ctx.visibility.solar_rise_set_at_ut1(start, end, event=rise)
    solar_twilight, solar_twilight_flags = ctx.visibility.solar_twilight_at_ut1(
        start, end, event=rise, twilight=taiyin.TwilightKind.civil)
    solar_transit, solar_transit_flags = ctx.visibility.solar_transit_at_ut1(start, end, event=upper)
    results = (
        moon_rise, moon_transit, planet_rise, planet_transit, solar_rise, solar_twilight, solar_transit,
    )
    assert (moon_rise_flags | moon_transit_flags | planet_rise_flags | planet_transit_flags |
            solar_rise_flags | solar_twilight_flags | solar_transit_flags) == taiyin.ResultFlag.none
    for result in results:
        assert result.coordinate is not None
        assert result.is_found
    assert ctx.last_status == 0
    assert ctx.last_operation == "Visibility.solar_transit_at_ut1"
    assert ctx.last_status == 0
    assert ctx.last_diagnostic is not None


def test_fast_solar_routes_and_custom_horizon(ctx):
    center = taiyin.JulianDate.from_double(2460311.0)
    observer = taiyin.ObserverLocation(116.3833, 39.9167, 50.0)
    fast, fast_flags = ctx.visibility.solar_rise_set_fast_at_tt(center, observer)
    transit, transit_flags = ctx.visibility.solar_transit_fast_at_tt(center, observer)
    assert fast_flags | transit_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert fast.rise is not None and fast.set is not None
    assert transit.coordinate is not None
    custom, custom_flags = ctx.visibility.solar_rise_set_at_ut1(
        center, taiyin.JulianDate.from_double(2460312.0), event=taiyin.VisibilityEventKind.rise,
        horizon_altitude_radians=0.0, flags=(taiyin.VisibilityFlag.noRefraction,))
    assert custom_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0


def test_visibility_input_validation_and_closed_context(ctx):
    start = taiyin.JulianDate.from_double(2460311.0)
    end = taiyin.JulianDate.from_double(2460312.0)
    with pytest.raises(ValueError):
        ctx.visibility.solar_rise_set_at_ut1(end, start, event=taiyin.VisibilityEventKind.rise)
    with pytest.raises(ValueError):
        ctx.visibility.solar_rise_set_at_ut1(start, end, event=taiyin.VisibilityEventKind.upperTransit)
    with pytest.raises(ValueError):
        ctx.visibility.planet_rise_set_at_ut1(taiyin.Body.sun, start, end, event=taiyin.VisibilityEventKind.rise)
    with pytest.raises(ValueError):
        ctx.visibility.moon_rise_set_at_ut1(start, end, event=taiyin.VisibilityEventKind.rise,
            flags=(taiyin.VisibilityFlag.refraction, taiyin.VisibilityFlag.noRefraction))
    ctx.close()
    with pytest.raises(RuntimeError):
        ctx.visibility.solar_transit_at_ut1(start, end, event=taiyin.VisibilityEventKind.upperTransit)
