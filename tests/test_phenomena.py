import math
import os
from pathlib import Path
import pytest
import taiyin

@pytest.fixture()
def ctx():
    root=os.environ.get("TAIYIN_SOURCE_DIR")
    if not root: pytest.skip("set TAIYIN_SOURCE_DIR")
    path=Path(root)/"data"/"ephemerides"/"opm2"/"major-bodies"/"600y"
    c=taiyin.Ephemeris(source_paths=[str(path)],load_packaged_data=False).create_context()
    c.configuration.set_geocentric_observer(observer_id=399,center_id=399); c.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield c; c.close()

def test_phenomena_tt_and_ut1(ctx):
    jd=taiyin.JulianDate.from_double(2460311.0)
    moon,moon_flags=ctx.phenomena.at_tt(taiyin.Body.moon,jd)
    venus,venus_flags=ctx.phenomena.at_ut1(taiyin.Body.venus,jd)
    assert moon_flags | venus_flags == taiyin.ResultFlag.none
    assert ctx.last_status == 0
    assert 0 <= moon.illuminatedFraction <= 1
    assert moon.geocentricHorizontalParallaxRadians is not None
    assert venus.geocentricHorizontalParallaxRadians is None
    assert all(math.isfinite(x) for x in (venus.phaseAngleRadians,venus.apparentMagnitude))

def test_phenomena_validation(ctx):
    jd=taiyin.JulianDate.from_double(2460311.0)
    with pytest.raises(ValueError): ctx.phenomena.at_tt(taiyin.Body.earth,jd)
    with pytest.raises(ValueError): ctx.phenomena.at_tt(taiyin.Body.moon,jd,flags=(taiyin.PositionFlag.topocentric,))
