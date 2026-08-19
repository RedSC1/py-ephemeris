import math, os
from pathlib import Path
import pytest, taiyin

@pytest.fixture()
def ctx():
    root=os.environ.get("TAIYIN_SOURCE_DIR")
    if not root: pytest.skip("set TAIYIN_SOURCE_DIR")
    path=Path(root)/"data"/"ephemerides"/"opm2"/"major-bodies"/"600y"
    c=taiyin.Ephemeris(source_paths=[str(path)],load_packaged_data=False).create_context()
    c.configuration.set_geocentric_observer(observer_id=399,center_id=399); c.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield c; c.close()

def test_observed_ut1_single_batch_and_complete_state(ctx):
    jd=taiyin.JulianDate.from_double(2460409.0); flags=(taiyin.ObservedFlag.speed,taiyin.ObservedFlag.truePosition)
    rows, result_flags = ctx.observed.batch_at_ut1([taiyin.Body.sun,taiyin.Body.moon],jd,flags=flags)
    assert result_flags == taiyin.ResultFlag.none
    assert len(rows)==2 and all(row.status==0 for row in rows)
    assert rows[0].diagnostic.target_id==taiyin.Body.sun.id
    assert rows[0].apparent.bodyMaskBit==1 and rows[0].apparent.distanceAu>0
    assert all(math.isfinite(v) for v in rows[0].apparent.geometricState.position_au)
    row, row_flags = ctx.observed.at_ut1(taiyin.Body.sun,jd,flags=flags)
    assert row_flags == taiyin.ResultFlag.none
    assert row.apparent.longitudeRadians==rows[0].apparent.longitudeRadians

def test_observed_utc_and_horizontal_refraction(ctx):
    utc=taiyin.AstroDateTime(2024,4,8,18)
    utc_rows, utc_flags = ctx.observed.batch_at_utc([taiyin.Body.sun,taiyin.Body.moon],utc,flags=(taiyin.ObservedFlag.truePosition,))
    assert utc_flags == taiyin.ResultFlag.none
    assert len(utc_rows)==2
    ctx.configuration.set_observer_location(taiyin.ObserverLocation(116.391,39.907,50)); ctx.configuration.set_standard_atmosphere()
    row, row_flags = ctx.observed.at_ut1(taiyin.Body.sun,taiyin.JulianDate.from_double(2460409.0),flags=(taiyin.ObservedFlag.speed,taiyin.ObservedFlag.topocentric,taiyin.ObservedFlag.horizontal,taiyin.ObservedFlag.refraction,taiyin.ObservedFlag.truePosition))
    assert row_flags == taiyin.ResultFlag.none
    assert row.horizontal is not None and row.horizontalRates is not None
    assert row.refractedHorizontal is not None and row.refractedHorizontalRates is not None

def test_observed_validation_and_close(ctx):
    jd=taiyin.JulianDate.from_double(2460409.0)
    empty_rows, empty_flags = ctx.observed.batch_at_ut1([],jd)
    assert empty_rows == [] and empty_flags == taiyin.ResultFlag.none
    with pytest.raises(ValueError): ctx.observed.at_ut1(taiyin.Body.earth,jd)
    with pytest.raises(ValueError): ctx.observed.at_ut1(taiyin.Body.sun,jd,flags=(taiyin.ObservedFlag.horizontal,))
    with pytest.raises(ValueError): ctx.observed.batch_at_ut1([taiyin.Body.sun]*11,jd)
    ctx.close()
    with pytest.raises(RuntimeError): ctx.observed.at_ut1(taiyin.Body.sun,jd)
