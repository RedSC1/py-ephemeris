"""Events regression suite ported from legacy Python and C++ event-search oracles."""

import math
import os
from pathlib import Path

import pytest
import taiyin


@pytest.fixture()
def ctx():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run event-search integration tests")
    source_path = Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    context = taiyin.Ephemeris(source_paths=[str(source_path)], load_packaged_data=False).create_context()
    context.configuration.set_geocentric_observer(observer_id=taiyin.Body.earth.id, center_id=taiyin.Body.earth.id)
    context.configuration.set_standard_atmosphere()
    context.configuration.use_solar_deflector()
    context.configuration.set_apparent_config(taiyin.ApparentConfig(frozenset({
        taiyin.ApparentFlag.spherical, taiyin.ApparentFlag.lightTime,
        taiyin.ApparentFlag.aberration, taiyin.ApparentFlag.deflection,
    })))
    context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield context
    context.close()


def test_scalar_solar_and_lunar_longitude_searches(ctx):
    estimate = taiyin.JulianDate.from_double(2460380.5)
    solar, solar_flags = ctx.events.solar_longitude_at_ut1(0.0, estimate)
    assert solar_flags == taiyin.ResultFlag.none
    assert ctx.last_operation == "Events.solar_longitude_at_ut1"
    assert ctx.last_status == 0
    assert ctx.last_diagnostic is not None
    reverse, reverse_flags = ctx.events.solar_longitude_at_ut1(
        0.0, taiyin.JulianDate.from_double(2460395.0), options=(taiyin.EventSearchOption.reverse,))
    solar_tt, solar_tt_flags = ctx.events.solar_longitude_at_tt(0.0, estimate)
    moon, moon_flags = ctx.events.moon_longitude_at_ut1(math.pi / 2.0, estimate)
    moon_tt, moon_tt_flags = ctx.events.moon_longitude_at_tt(math.pi / 2.0, estimate)
    assert (reverse_flags | solar_tt_flags | moon_flags | moon_tt_flags) == taiyin.ResultFlag.none

    assert abs(solar.to_double() - 2460389.6294463626) < 5e-8
    assert abs(reverse.to_double() - solar.to_double()) < 5e-8
    assert solar_tt.to_double() > estimate.to_double()
    assert moon.to_double() > estimate.to_double()
    assert moon_tt.to_double() > estimate.to_double()
    assert ctx.events.recommended_longitude_search_step_days(taiyin.Body.mercury) > 0
    assert ctx.events.recommended_aspect_search_step_days(taiyin.Body.moon, taiyin.Body.sun) > 0


def test_bounded_longitude_station_aspect_and_phase_searches(ctx):
    start = taiyin.JulianDate.from_double(2460380.5)
    end = taiyin.JulianDate.from_double(2460420.5)
    longitude, longitude_flags = ctx.events.longitude_crossings_at_ut1(
        taiyin.Body.sun, 0.0, start, taiyin.JulianDate.from_double(2460395.0), max_step_days=2.0)
    stations, station_flags = ctx.events.longitude_stations_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate.from_double(2452878.5),
        taiyin.JulianDate.from_double(2452882.5), max_step_days=0.25)
    aspects, aspect_flags = ctx.events.aspect_crossings_at_ut1(
        taiyin.Body.moon, taiyin.Body.sun, 0.0, start, end, max_step_days=1.0)
    exact, exact_flags = ctx.events.exact_aspects_at_ut1(
        taiyin.Body.moon, taiyin.Body.sun, [math.pi / 2.0], start, end, max_step_days=0.5)
    phases, phase_flags = ctx.events.lunar_phase_crossings_at_ut1(0.0, start, end, max_step_days=1.0)
    assert (longitude_flags | station_flags | aspect_flags | exact_flags | phase_flags) == taiyin.ResultFlag.none

    assert len(longitude) == 1
    assert abs(longitude[0].to_double() - 2460389.6294463626) < 5e-8
    assert len(stations) == 1
    assert abs(stations[0].coordinate.to_double() - 2452880.070395550) < 2.0 / 86400.0
    assert len(aspects) == 1
    assert len(exact) >= 2
    assert [item.coordinate.to_double() for item in exact] == sorted(
        item.coordinate.to_double() for item in exact)
    assert len(phases) == 1
    assert abs(phases[0].to_double() - aspects[0].to_double()) < 5e-8


def test_tt_variants_match_legacy_event_search_shapes(ctx):
    start = taiyin.JulianDate.from_double(2460380.5)
    end = taiyin.JulianDate.from_double(2460420.5)
    longitude, longitude_flags = ctx.events.longitude_crossings_at_tt(
        taiyin.Body.sun, 0.0, start, taiyin.JulianDate.from_double(2460395.0), max_step_days=2.0)
    stations, station_flags = ctx.events.longitude_stations_at_tt(
        taiyin.Body.mercury, taiyin.JulianDate.from_double(2452878.5),
        taiyin.JulianDate.from_double(2452882.5), max_step_days=0.25)
    aspects, aspect_flags = ctx.events.aspect_crossings_at_tt(
        taiyin.Body.moon, taiyin.Body.sun, math.pi / 2.0, start,
        taiyin.JulianDate.from_double(2460395.5), max_step_days=0.5)
    exact, exact_flags = ctx.events.exact_aspects_at_tt(
        taiyin.Body.moon, taiyin.Body.sun, [math.pi / 2.0], start, end,
        max_step_days=0.5)
    phases, phase_flags = ctx.events.lunar_phase_crossings_at_tt(
        math.pi / 2.0, start, taiyin.JulianDate.from_double(2460395.5),
        max_step_days=0.5)
    assert (longitude_flags | station_flags | aspect_flags | exact_flags | phase_flags) == taiyin.ResultFlag.none
    assert len(longitude) == 1
    assert len(stations) > 0
    assert len(aspects) == 1
    assert len(exact) >= 2
    assert len(phases) == 1


def test_extrema_and_global_and_local_solar_transits(ctx):
    elongation, elongation_flags = ctx.events.greatest_elongation_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate.from_double(2460369.5),
        taiyin.JulianDate.from_double(2460414.5))
    minimum_ut1, minimum_ut1_flags = ctx.events.minimum_angular_separation_at_ut1(
        taiyin.Body.moon, taiyin.Body.sun, taiyin.JulianDate.from_double(2460408.5),
        taiyin.JulianDate.from_double(2460410.0), max_step_days=0.05)
    minimum_tt, minimum_tt_flags = ctx.events.minimum_angular_separation_at_tt(
        taiyin.Body.moon, taiyin.Body.sun, taiyin.JulianDate.from_double(2460408.5),
        taiyin.JulianDate.from_double(2460410.0), max_step_days=0.05)
    transit, transit_flags = ctx.events.next_solar_transit_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate.from_double(2458799.0))
    observer = taiyin.ObserverLocation(-74.0060, 40.7128, 10.0)
    local_from_global, local_global_flags = ctx.events.local_solar_transit_at_ut1(
        transit, observer)
    local_search, local_search_flags = ctx.events.next_local_solar_transit_at_ut1(
        taiyin.Body.mercury, taiyin.JulianDate.from_double(2458799.0), observer)
    assert (elongation_flags | minimum_ut1_flags | minimum_tt_flags | transit_flags |
            local_global_flags | local_search_flags) == taiyin.ResultFlag.none

    assert elongation.kind is taiyin.GreatestElongationKind.eastern
    assert abs(elongation.coordinate.to_double() - 2460394.440334700048) < 0.02
    assert 15 * math.pi / 180 <= elongation.elongationRadians <= 30 * math.pi / 180
    assert abs(minimum_ut1.coordinate.to_double() - 2460409.262042756) < 2.0 / 86400.0
    assert minimum_tt.separationRadians < 0.02
    assert abs(transit.greatest.to_double() - 2458799.138751322404) < 1.0 / 86400.0
    assert taiyin.SolarTransitKind.fullDisk in transit.kinds
    assert transit.t1 is not None and transit.t4 is not None
    assert transit.t1.to_double() < transit.greatest.to_double() < transit.t4.to_double()
    assert abs(local_from_global.topocentric.greatest.to_double() - transit.greatest.to_double()) > 0.05 / 86400.0
    assert taiyin.SolarTransitVisibilityFlag.visibleAtObserver in local_search.visibilityFlags
    assert all(math.isfinite(item) for item in local_search.contactSunAltitudeDegrees)
    assert all(math.isfinite(item) for item in local_search.contactSunAzimuthDegrees)


def test_event_search_input_validation_and_close(ctx):
    start = taiyin.JulianDate.from_double(2460380.5)
    end = taiyin.JulianDate.from_double(2460390.5)
    with pytest.raises(ValueError):
        ctx.events.solar_longitude_at_ut1(0.0, start, position_flags=(taiyin.PositionFlag.xyz,))
    with pytest.raises(ValueError):
        ctx.events.aspect_crossings_at_ut1(taiyin.Body.sun, taiyin.Body.sun, 0.0, start, end, max_step_days=1.0)
    with pytest.raises(ValueError):
        ctx.events.exact_aspects_at_ut1(taiyin.Body.moon, taiyin.Body.sun, [], start, end, max_step_days=1.0)
    with pytest.raises(ValueError):
        ctx.events.lunar_phase_crossings_at_ut1(0.0, start, end, max_step_days=1.0, max_results=0)
    with pytest.raises(ValueError):
        ctx.events.next_solar_transit_at_ut1(taiyin.Body.mars, start)
    with pytest.raises(ValueError):
        ctx.events.next_local_solar_transit_at_ut1(
            taiyin.Body.mercury, start, taiyin.ObserverLocation(0.0, 0.0),
            options=(taiyin.EventSearchOption.refraction, taiyin.EventSearchOption.noRefraction))
    ctx.close()
    with pytest.raises(RuntimeError):
        ctx.events.solar_longitude_at_ut1(0.0, start)
