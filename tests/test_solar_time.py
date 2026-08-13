"""Solar-time regression tests ported from the legacy Python wrapper and C++ oracles."""

import math
import os
from pathlib import Path

import pytest
import taiyin


@pytest.fixture()
def ctx():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run solar-time integration tests")
    source_path = Path(source_root) / "data" / "ephemerides" / "opm2" / "major-bodies" / "600y"
    context = taiyin.Ephemeris(source_paths=[str(source_path)], load_packaged_data=False).create_context()
    yield context
    context.close()


def test_calculates_equation_of_time_from_ut1_and_tt(ctx):
    ut1 = taiyin.JulianDate.from_double(2460311.0)
    from_ut1 = ctx.solar_time.equation_of_time_at_ut1(ut1)
    equation = from_ut1
    from_tt = ctx.solar_time.equation_of_time_at_tt(equation.tt)

    assert -250.0 < equation.equationSeconds < -150.0
    assert math.isclose(equation.equationSeconds, -198.9342282623329, abs_tol=2.0)
    assert math.isclose(equation.equationDays * 86400.0, equation.equationSeconds, abs_tol=1e-12)
    assert math.isclose(from_tt.equationSeconds, equation.equationSeconds, abs_tol=2e-5)
    assert abs(equation.ut1.seconds_difference(ut1)) < 5e-12
    assert math.isfinite(equation.apparentSunRightAscensionRadians)
    assert math.isfinite(equation.greenwichApparentSiderealTimeRadians)
    assert ctx.last_status == 0


@pytest.mark.parametrize("ut1, expected_seconds", [
    (2451545.0, -197.11531440430917),
    (2460409.0, -102.17101941988405),
    (2460676.5, -206.5203796885362),
])
def test_equation_of_time_cpp_multi_epoch_oracles(ctx, ut1, expected_seconds):
    result = ctx.solar_time.equation_of_time_at_ut1(taiyin.JulianDate.from_double(ut1))
    assert math.isclose(result.equationSeconds, expected_seconds, abs_tol=2.0)


def test_round_trips_local_mean_and_apparent_solar_time(ctx):
    ut1 = taiyin.JulianDate.from_double(2460311.0)
    longitude_radians = 116.3833 * math.pi / 180.0
    equation = ctx.solar_time.equation_of_time_at_ut1(ut1)
    local_mean = taiyin.LocalMeanSolarTime.from_ut1(ut1, longitudeRadians=longitude_radians)
    apparent = ctx.solar_time.mean_to_apparent(local_mean)
    round_trip = ctx.solar_time.apparent_to_mean(apparent)

    assert abs(apparent.coordinate.seconds_difference(local_mean.coordinate) - equation.equationSeconds) < 1e-4
    assert abs(round_trip.coordinate.seconds_difference(local_mean.coordinate)) < 1e-4
    assert round_trip.longitudeRadians == longitude_radians
    assert ctx.last_status == 0


def test_rejects_invalid_longitude_and_use_after_close(ctx):
    ut1 = taiyin.JulianDate.from_double(2460311.0)
    local_mean = taiyin.LocalMeanSolarTime.from_ut1(ut1, longitudeRadians=0)
    with pytest.raises(ValueError):
        taiyin.LocalMeanSolarTime.from_ut1(ut1, longitudeRadians=float("nan"))
    with pytest.raises(ValueError):
        taiyin.LocalMeanSolarTime.from_ut1(ut1, longitudeRadians=math.pi + 0.01)
    ctx.close()
    with pytest.raises(RuntimeError):
        ctx.solar_time.equation_of_time_at_ut1(ut1)
    with pytest.raises(RuntimeError):
        ctx.solar_time.mean_to_apparent(local_mean)
